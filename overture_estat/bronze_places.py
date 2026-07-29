#!/usr/bin/env python
"""
Bronze: Overture places -> Delta

方針
----
  * Overture の列は加工しない（categories の非推奨化のような上流変更を
    Silver 以降に閉じ込めるため）
  * 足すのは 3 種類だけ
      - 結合キー: mesh1/mesh2/mesh3/mesh4 と lon/lat
      - 来歴:     release, ingested_at
  * 同じ release を再実行しても二重にならない（replaceWhere で冪等）

使い方
------
  python bronze_places.py --bbox osaka
  python bronze_places.py --bbox japan --release 2026-07-22.0
  python bronze_places.py --bbox osaka --profile-only
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from mesh import mesh_code_expr
from spark_session import (
    JAPAN_BBOX,
    KEIHANSHIN_BBOX,
    OSAKA_BBOX,
    OVERTURE_BUCKET,
    bbox_filter,
    build_spark,
    overture_path,
)

BBOXES = {"osaka": OSAKA_BBOX, "keihanshin": KEIHANSHIN_BBOX, "japan": JAPAN_BBOX}
DEFAULT_OUT = os.path.expanduser("~/develop/lakehouse/bronze/overture_places")

# Delta は既定で「先頭 32 列」しか統計(min/max)を集めない。
# 派生列を末尾に足すと境界を越えて統計対象から漏れ、Z-ORDER が無効になる。
# 対策は 2 つ、両方やる。
#   (1) キー列を先頭に並べ替える
#   (2) 統計対象を列名で明示する（delta.dataSkippingStatsColumns）
FRONT_COLS = [
    "id", "mesh1", "mesh2", "mesh3", "mesh4",
    "lon", "lat", "confidence", "release", "ingested_at",
]
STATS_COLS = "id,mesh1,mesh2,mesh3,mesh4,lon,lat,confidence,release"


# --------------------------------------------------------------------------
def resolve_latest_release() -> str:
    """S3 のプレフィックスを匿名で列挙して最新リリースを得る。

    STAC カタログを引く方法もあるが、こちらは追加の URL 知識が要らず、
    バケット構造が変わらない限り壊れない。
    """
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config

    s3 = boto3.client("s3", region_name="us-west-2", config=Config(signature_version=UNSIGNED))
    paginator = s3.get_paginator("list_objects_v2")
    releases = []
    for page in paginator.paginate(Bucket=OVERTURE_BUCKET, Prefix="release/", Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            releases.append(cp["Prefix"].split("/")[1])
    if not releases:
        raise RuntimeError("リリースが列挙できませんでした")
    return sorted(releases)[-1]


# --------------------------------------------------------------------------
def read_places(spark: SparkSession, release: str, bbox: dict) -> DataFrame:
    raw = spark.read.parquet(overture_path(release, "places", "place"))

    # ★ ST_ 関数より先に bbox の数値比較で落とす。
    #    こう書くと Parquet の row-group 統計でファイル/行群がスキップされ、
    #    WKB のデシリアライズ自体が発生しない。
    df = raw.where(bbox_filter(bbox))

    # 座標の取り出し。
    # bbox.xmin をそのまま経度に使う手もあるが、Overture の bbox は
    # ファイルサイズ削減のため float32 で、度あたり 1e-5 程度（≒1m）の
    # 誤差が乗る。1km メッシュなら実害はないが、境界上の点の帰属が
    # 揺れるので geometry から取り直しておく。
    df = df.withColumn("_geom", F.expr("ST_GeomFromWKB(geometry)"))
    df = df.withColumn("lon", F.expr("ST_X(_geom)")).withColumn("lat", F.expr("ST_Y(_geom)"))
    df = df.drop("_geom")

    lon, lat = F.col("lon"), F.col("lat")
    df = (
        df.withColumn("mesh1", mesh_code_expr(lat, lon, 1))
        .withColumn("mesh2", mesh_code_expr(lat, lon, 2))
        .withColumn("mesh3", mesh_code_expr(lat, lon, 3))
        .withColumn("mesh4", mesh_code_expr(lat, lon, 4))
        .withColumn("release", F.lit(release))
        .withColumn("ingested_at", F.current_timestamp())
    )

    # キー列を先頭へ。統計収集の 32 列制限に確実に収めるためと、
    # select * で覗いたときに読みやすくするため。
    front = [c for c in FRONT_COLS if c in df.columns]
    return df.select(*front, *[c for c in df.columns if c not in front])


def write_bronze(df: DataFrame, out_path: str, release: str) -> None:
    """replaceWhere で「このリリース分だけ」を差し替える。

    初回は対象行がないので単なる追記として振る舞う。
    2 回目以降の同一リリース再実行でも件数が二重にならない。
    """
    exists = os.path.exists(os.path.join(out_path, "_delta_log")) or out_path.startswith("s3a://")
    writer = (
        df.write.format("delta")
        .option("mergeSchema", "true")
        # 統計を集める列を明示。指定するとこちらが優先され、
        # 「先頭 N 列」ルールは使われなくなる。
        .option("delta.dataSkippingStatsColumns", STATS_COLS)
    )
    if exists:
        writer = writer.mode("overwrite").option("replaceWhere", f"release = '{release}'")
    else:
        writer = writer.mode("overwrite")
    writer.save(out_path)


def ensure_stats_columns(spark: SparkSession, out_path: str) -> None:
    """既存テーブルにも統計対象を設定する（writer option が効かない版への保険）。

    注意: この設定は「以降に書かれるファイル」にしか適用されない。
    既存ファイルに統計を付けるには OPTIMIZE などで書き直す必要がある。
    """
    spark.sql(
        f"ALTER TABLE delta.`{out_path}` "
        f"SET TBLPROPERTIES ('delta.dataSkippingStatsColumns' = '{STATS_COLS}')"
    )


def optimize(spark: SparkSession, out_path: str) -> None:
    """mesh3 で Z-ORDER する。

    メッシュコードは空間的な局所性をそのまま持つ（近い場所は近いコード）ので、
    地域で絞る後続クエリのファイルスキップが強く効く。

    mesh2 は mesh3 の接頭辞なので、両方を Z-ORDER キーにするのは冗長。
    ビット列を食い合って効きが落ちるだけなので mesh3 単独にする。
    """
    spark.sql(f"OPTIMIZE delta.`{out_path}` ZORDER BY (mesh3)")


# --------------------------------------------------------------------------
def profile(spark: SparkSession, out_path: str) -> None:
    """Silver の設計判断に必要な情報を出す。"""
    df = spark.read.format("delta").load(out_path)
    n = df.count()
    print(f"\n=== {out_path}")
    print(f"件数: {n:,}")

    print("\n--- カテゴリ列の在り方（release で変わる） ---")
    cols = set(df.columns)
    print(f"  categories: {'あり' if 'categories' in cols else 'なし'}")
    print(f"  basic_category: {'あり' if 'basic_category' in cols else 'なし'}")

    if "categories" in cols:
        print("\n--- primary カテゴリ 上位20 ---")
        (
            df.select(F.col("categories.primary").alias("cat"))
            .groupBy("cat").count().orderBy(F.desc("count")).limit(20)
            .show(20, truncate=False)
        )

    print("--- confidence 分布 ---")
    df.selectExpr(
        "min(confidence) lo", "percentile_approx(confidence, 0.5) med",
        "max(confidence) hi", "sum(case when confidence < 0.5 then 1 else 0 end) low_conf",
    ).show()

    print("--- 名前の言語 ---")
    df.selectExpr("map_keys(names.common) AS langs").selectExpr(
        "explode(langs) AS lang"
    ).groupBy("lang").count().orderBy(F.desc("count")).show(10)

    print("--- メッシュ密度（3次メッシュあたりの POI 数） ---")
    per = df.groupBy("mesh3").count()
    print(f"  非空メッシュ数: {per.count():,}")
    per.selectExpr(
        "percentile_approx(count, 0.5) p50", "percentile_approx(count, 0.9) p90",
        "max(count) max",
    ).show()

    print("--- POI が多い3次メッシュ 上位10 ---")
    per.orderBy(F.desc("count")).limit(10).show()


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", choices=list(BBOXES), default="keihanshin")
    ap.add_argument("--release", default=None, help="未指定なら S3 から最新を解決")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--profile-only", action="store_true")
    ap.add_argument("--driver-memory", default="8g")
    args = ap.parse_args()

    spark = build_spark("bronze-places", driver_memory=args.driver_memory)

    try:
        if args.profile_only:
            profile(spark, args.out)
            return 0

        release = args.release or resolve_latest_release()
        bbox = BBOXES[args.bbox]
        print(f"release = {release}\nbbox    = {args.bbox} {bbox}\nout     = {args.out}\n")

        t0 = time.time()
        df = read_places(spark, release, bbox)
        write_bronze(df, args.out, release)
        print(f"write: {time.time() - t0:.1f}s")

        ensure_stats_columns(spark, args.out)

        t0 = time.time()
        optimize(spark, args.out)
        print(f"optimize: {time.time() - t0:.1f}s")

        profile(spark, args.out)
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())