#!/usr/bin/env python
"""
Bronze の中身を詰める診断。Silver の設計判断に必要な事実だけを取りに行く。

  python investigate.py
"""

from __future__ import annotations

import os

from pyspark.sql import functions as F

from spark_session import build_spark

PATH = os.path.expanduser("~/develop/lakehouse/bronze/overture_places")


def main() -> None:
    spark = build_spark("investigate", driver_memory="6g")
    df = spark.read.format("delta").load(PATH)
    df.createOrReplaceTempView("places")

    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Q1. names の実態: primary / common / rules の充足率")
    print("=" * 70)
    df.selectExpr(
        "count(*) AS total",
        "sum(case when names.primary is not null then 1 else 0 end) AS has_primary",
        "sum(case when names.common is not null then 1 else 0 end) AS has_common",
        "sum(case when size(coalesce(names.common, map())) > 0 then 1 else 0 end) AS common_nonempty",
        "sum(case when names.rules is not null and size(names.rules) > 0 then 1 else 0 end) AS has_rules",
    ).show(truncate=False)

    print("--- names.primary のサンプル（日本語が入っているか）---")
    df.where("names.primary is not null").select("names.primary").limit(15).show(truncate=False)

    print("--- names.rules に言語別表記が逃げていないか ---")
    (
        df.where("size(coalesce(names.rules, array())) > 0")
        .selectExpr("explode(names.rules) AS r")
        .selectExpr("r.language AS lang", "r.variant AS variant")
        .groupBy("lang", "variant").count().orderBy(F.desc("count")).show(15)
    )

    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Q2. rental_kiosks は何者か")
    print("=" * 70)
    kiosk = df.where("categories.primary = 'rental_kiosks'")
    print(f"件数: {kiosk.count():,}")

    print("--- ブランド別 ---")
    (
        kiosk.selectExpr("coalesce(brand.names.primary, '(ブランドなし)') AS brand")
        .groupBy("brand").count().orderBy(F.desc("count")).show(15, truncate=False)
    )

    print("--- データソース別（一括インポートの痕跡）---")
    (
        kiosk.selectExpr("explode(sources) AS s")
        .selectExpr("s.dataset AS dataset")
        .groupBy("dataset").count().orderBy(F.desc("count")).show(10, truncate=False)
    )

    print("--- confidence 分布（低いなら機械的な一括投入の疑い）---")
    kiosk.selectExpr(
        "min(confidence) lo", "percentile_approx(confidence,0.5) med", "max(confidence) hi"
    ).show()

    print("--- 全体のソース別内訳（比較用）---")
    (
        df.selectExpr("explode(sources) AS s").selectExpr("s.dataset AS dataset")
        .groupBy("dataset").count().orderBy(F.desc("count")).show(10, truncate=False)
    )

    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Q3. categories と basic_category はどう違うか")
    print("=" * 70)
    print("--- basic_category のスキーマ ---")
    df.select("basic_category").printSchema()
    df.select("basic_category").limit(10).show(truncate=False)

    print("--- 充足率の比較 ---")
    df.selectExpr(
        "sum(case when categories.primary is not null then 1 else 0 end) AS cat_primary",
        "sum(case when basic_category is not null then 1 else 0 end) AS basic_cat",
        "count(*) AS total",
    ).show()

    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Q4. confidence を閾値で切るとどれだけ落ちるか")
    print("=" * 70)
    for th in (0.0, 0.3, 0.5, 0.7, 0.9):
        n = df.where(F.col("confidence") >= th).count()
        print(f"  confidence >= {th:.1f}:  {n:>8,d}  ({n / 387035 * 100:5.1f}%)")

    print("\n--- 主要カテゴリが閾値0.5でどれだけ残るか ---")
    (
        df.where("categories.primary in "
                 "('convenience_store','supermarket','pharmacy','japanese_restaurant','rental_kiosks')")
        .groupBy("categories.primary")
        .agg(
            F.count("*").alias("all"),
            F.sum(F.when(F.col("confidence") >= 0.5, 1).otherwise(0)).alias("conf_ge_05"),
            F.round(F.avg("confidence"), 3).alias("avg_conf"),
        )
        .orderBy(F.desc("all")).show(truncate=False)
    )

    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Q5. スーパー/コンビニは十分な件数があるか（Gold の分析対象候補）")
    print("=" * 70)
    (
        df.where("categories.primary rlike "
                 "'(supermarket|convenience|grocery|drugstore|pharmacy|department_store|shopping)'")
        .groupBy("categories.primary").count().orderBy(F.desc("count")).show(25, truncate=False)
    )

    spark.stop()


if __name__ == "__main__":
    main()