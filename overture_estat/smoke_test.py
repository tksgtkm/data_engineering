#!/usr/bin/env python
"""
段階的スモークテスト。

「全部入りの SparkSession が起動しない」は原因の切り分けが難しいので、
レイヤごとに独立して PASS/FAIL を出す。落ちた段の直前までは信頼できる。

    python smoke_test.py              # 1-4（ローカル完結 + Overture のスキーマ読みまで）
    HEAVY=1 python smoke_test.py      # 5 も実行（Overture 実データの集計。数分かかる）
    MINIO_ENDPOINT=http://localhost:9000 python smoke_test.py   # 6 も実行
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import traceback

from pyspark.sql import functions as F

from spark_session import (
    OSAKA_BBOX,
    bbox_filter,
    build_spark,
    overture_path,
)

RELEASE = os.environ.get("OVERTURE_RELEASE", "2026-07-22.0")

_results: list[tuple[str, bool, str]] = []


def stage(name: str):
    def deco(fn):
        def wrapper(*a, **kw):
            try:
                fn(*a, **kw)
                _results.append((name, True, ""))
                print(f"  ✅ {name}")
            except Exception as e:  # noqa: BLE001
                _results.append((name, False, f"{type(e).__name__}: {e}"))
                print(f"  ❌ {name}")
                traceback.print_exc(limit=3)
            return None
        return wrapper
    return deco


# --------------------------------------------------------------------------
@stage("1. SparkSession 起動 / JAR 解決")
def s1_session(spark):
    assert spark.range(10).count() == 10
    print(f"     Spark {spark.version}")
    print(f"     Hadoop {spark.sparkContext._jvm.org.apache.hadoop.util.VersionInfo.getVersion()}")


@stage("2. Delta 書き込み / 読み出し / MERGE")
def s2_delta(spark, tmpdir):
    path = os.path.join(tmpdir, "delta_check")
    spark.range(100).withColumn("v", F.col("id") * 2).write.format("delta").save(path)
    assert spark.read.format("delta").load(path).count() == 100

    # MERGE（増分取り込みで必ず使う）が通るかまで確認する
    from delta.tables import DeltaTable

    tgt = DeltaTable.forPath(spark, path)
    src = spark.range(95, 105).withColumn("v", F.lit(-1))
    (
        tgt.alias("t")
        .merge(src.alias("s"), "t.id = s.id")
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
    assert spark.read.format("delta").load(path).count() == 105
    hist = spark.sql(f"DESCRIBE HISTORY delta.`{path}`").count()
    print(f"     commits: {hist}")


@stage("3. Sedona SQL 関数")
def s3_sedona(spark):
    df = spark.sql(
        "SELECT ST_AsText(ST_Point(135.5023, 34.6937)) AS wkt, "
        "       ST_Distance(ST_Point(0,0), ST_Point(3,4)) AS d"
    )
    row = df.first()
    assert row["d"] == 5.0, row
    print(f"     {row['wkt']}")


@stage("4. Delta × Sedona 併用（両方の extension が生きているか）")
def s4_combined(spark, tmpdir):
    """spark.sql.extensions を片方しか書いていないと、ここで初めて落ちる。"""
    path = os.path.join(tmpdir, "delta_geo")
    df = (
        spark.range(5)
        .withColumn("lon", F.lit(135.5) + F.col("id") * 0.01)
        .withColumn("lat", F.lit(34.7) + F.col("id") * 0.01)
        .withColumn("geom_wkb", F.expr("ST_AsBinary(ST_Point(lon, lat))"))
    )
    df.write.format("delta").save(path)
    back = spark.read.format("delta").load(path).withColumn(
        "geom", F.expr("ST_GeomFromWKB(geom_wkb)")
    )
    assert back.selectExpr("ST_X(geom) AS x").first()["x"] is not None
    print("     WKB round-trip OK")


@stage("5a. Overture 匿名 S3 アクセス（スキーマのみ）")
def s5a_overture_schema(spark):
    df = spark.read.parquet(overture_path(RELEASE, "places", "place"))
    cols = set(df.columns)
    assert {"id", "bbox", "geometry"} <= cols, sorted(cols)
    print(f"     columns: {len(cols)} / has 'categories': {'categories' in cols}")


@stage("5b. Overture 実データ集計（大阪 bbox・重い）")
def s5b_overture_count(spark):
    df = (
        spark.read.parquet(overture_path(RELEASE, "places", "place"))
        .where(bbox_filter(OSAKA_BBOX))
    )
    n = df.count()
    print(f"     大阪 bbox の places: {n:,}")
    assert n > 0


@stage("6. MinIO 書き込み")
def s6_minio(spark):
    bucket = os.environ.get("MINIO_BUCKET", "lakehouse")
    path = f"s3a://{bucket}/_smoke/delta_check"
    spark.range(10).write.format("delta").mode("overwrite").save(path)
    assert spark.read.format("delta").load(path).count() == 10


# --------------------------------------------------------------------------
def main() -> int:
    minio_endpoint = os.environ.get("MINIO_ENDPOINT")
    spark = build_spark(
        "smoke-test",
        minio_endpoint=minio_endpoint,
        minio_access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
    )
    tmpdir = tempfile.mkdtemp(prefix="spark_smoke_")
    print(f"\nscratch: {tmpdir}\nrelease: {RELEASE}\n")

    try:
        s1_session(spark)
        s2_delta(spark, tmpdir)
        s3_sedona(spark)
        s4_combined(spark, tmpdir)
        s5a_overture_schema(spark)
        if os.environ.get("HEAVY"):
            s5b_overture_count(spark)
        if minio_endpoint:
            s6_minio(spark)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        spark.stop()

    print("\n--- summary ---")
    for name, ok, err in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {err}" if err else ""))
    return 0 if all(ok for _, ok, _ in _results) else 1


if __name__ == "__main__":
    sys.exit(main())