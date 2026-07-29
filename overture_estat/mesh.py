"""
JIS X 0410 地域メッシュコード。

Overture(緯度経度) と e-Stat(メッシュ統計) を結合するためのキー生成。
空間結合を使わずに済むので、Sedona 抜きでも Bronze->Silver が組める。

  1次メッシュ  4桁  約80km   緯度40分  x 経度1度
  2次メッシュ  6桁  約10km   緯度 5分  x 経度7分30秒
  3次メッシュ  8桁  約 1km   緯度30秒  x 経度45秒
  4次メッシュ  9桁  約500m   3次を2x2分割
  5次メッシュ 10桁  約250m   4次を2x2分割

self-test:  python mesh.py
"""

from __future__ import annotations

from pyspark.sql import Column
from pyspark.sql import functions as F


# --------------------------------------------------------------------------
# Spark 版（UDF を使わないので Catalyst 最適化が効く。実運用はこちら）
# --------------------------------------------------------------------------
def mesh_code_expr(lat: Column, lon: Column, level: int = 3) -> Column:
    """緯度経度カラムからメッシュコード文字列カラムを生成する。

    >>> df.withColumn("mesh3", mesh_code_expr(F.col("lat"), F.col("lon"), 3))
    """
    if level not in (1, 2, 3, 4, 5):
        raise ValueError(f"level must be 1..5, got {level}")

    def s(c: Column) -> Column:
        return c.cast("int").cast("string")

    lat_min = lat * 60
    p = F.floor(lat_min / 40)
    a = lat_min - p * 40
    u = F.floor(lon - 100)
    f = lon - 100 - u

    parts = [s(p), s(u)]
    if level == 1:
        return F.concat(*parts)

    q = F.floor(a / 5)
    b = a - q * 5
    v = F.floor(f * 60 / 7.5)
    g = f * 60 - v * 7.5
    parts += [s(q), s(v)]
    if level == 2:
        return F.concat(*parts)

    r = F.floor(b * 60 / 30)
    c = b * 60 - r * 30
    w = F.floor(g * 60 / 45)
    d = g * 60 - w * 45
    parts += [s(r), s(w)]
    if level == 3:
        return F.concat(*parts)

    # 4次: 3次を 2x2 に分割し 1..4 を付す（南西=1, 南東=2, 北西=3, 北東=4）
    r4 = F.floor(c / 15)
    w4 = F.floor(d / 22.5)
    parts.append(s(r4 * 2 + w4 + 1))
    if level == 4:
        return F.concat(*parts)

    c5 = c - r4 * 15
    d5 = d - w4 * 22.5
    r5 = F.floor(c5 / 7.5)
    w5 = F.floor(d5 / 11.25)
    parts.append(s(r5 * 2 + w5 + 1))
    return F.concat(*parts)


def mesh3_bounds_expr(mesh: Column) -> tuple[Column, Column, Column, Column]:
    """3次メッシュコードから (lat_min, lat_max, lon_min, lon_max) を復元する。

    メッシュ集計結果を地図に出すときに使う。
    """
    p = F.substring(mesh, 1, 2).cast("double")
    u = F.substring(mesh, 3, 2).cast("double")
    q = F.substring(mesh, 5, 1).cast("double")
    v = F.substring(mesh, 6, 1).cast("double")
    r = F.substring(mesh, 7, 1).cast("double")
    w = F.substring(mesh, 8, 1).cast("double")

    lat0 = (p * 40 + q * 5 + r * 0.5) / 60
    lon0 = 100 + u + (v * 7.5 + w * 0.75) / 60
    return lat0, lat0 + 0.5 / 60, lon0, lon0 + 0.75 / 60


def mesh_prefix(mesh: Column, level: int) -> Column:
    """細かいメッシュコードから粗いメッシュコードを切り出す（集計の roll-up 用）。"""
    n = {1: 4, 2: 6, 3: 8, 4: 9, 5: 10}[level]
    return F.substring(mesh, 1, n)


# --------------------------------------------------------------------------
# 純 Python 版（テスト・小規模処理用）
# --------------------------------------------------------------------------
def mesh_code(lat: float, lon: float, level: int = 3) -> str:
    lat_min = lat * 60
    p = int(lat_min // 40)
    a = lat_min - p * 40
    u = int(lon - 100)
    f = lon - 100 - u
    code = f"{p}{u}"
    if level == 1:
        return code

    q = int(a // 5)
    b = a - q * 5
    v = int(f * 60 // 7.5)
    g = f * 60 - v * 7.5
    code += f"{q}{v}"
    if level == 2:
        return code

    r = int(b * 60 // 30)
    c = b * 60 - r * 30
    w = int(g * 60 // 45)
    d = g * 60 - w * 45
    code += f"{r}{w}"
    if level == 3:
        return code

    r4, w4 = int(c // 15), int(d // 22.5)
    code += str(r4 * 2 + w4 + 1)
    if level == 4:
        return code

    c5, d5 = c - r4 * 15, d - w4 * 22.5
    code += str(int(c5 // 7.5) * 2 + int(d5 // 11.25) + 1)
    return code


def mesh3_bounds(code: str) -> tuple[float, float, float, float]:
    p, u = int(code[0:2]), int(code[2:4])
    q, v = int(code[4]), int(code[5])
    r, w = int(code[6]), int(code[7])
    lat0 = (p * 40 + q * 5 + r * 0.5) / 60
    lon0 = 100 + u + (v * 7.5 + w * 0.75) / 60
    return lat0, lat0 + 0.5 / 60, lon0, lon0 + 0.75 / 60


# --------------------------------------------------------------------------
if __name__ == "__main__":
    # 参照値を記憶で持たず、コード->矩形の往復で検証する
    pts = [
        ("東京駅", 35.681236, 139.767125),
        ("大阪駅", 34.702485, 135.495951),
        ("名古屋駅", 35.170915, 136.881537),
        ("札幌駅", 43.068564, 141.350722),
        ("那覇市役所", 26.212401, 127.679010),
        ("稚内駅", 45.416944, 141.673611),
    ]
    ok = True
    for name, lat, lon in pts:
        m3 = mesh_code(lat, lon, 3)
        y0, y1, x0, x1 = mesh3_bounds(m3)
        inside = y0 <= lat < y1 and x0 <= lon < x1
        # 粗いレベルは細かいレベルの接頭辞になっているはず
        consistent = all(
            mesh_code(lat, lon, lv) == mesh_code(lat, lon, 5)[: {1: 4, 2: 6, 3: 8, 4: 9}[lv]]
            for lv in (1, 2, 3, 4)
        )
        ok &= inside and consistent
        print(
            f"{'OK' if inside and consistent else 'NG'}  {name:10s} "
            f"{mesh_code(lat, lon, 5)}  lat[{y0:.5f},{y1:.5f}) lon[{x0:.5f},{x1:.5f})"
        )
    print("ALL PASS" if ok else "FAILED")