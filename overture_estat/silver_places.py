#!/usr/bin/env python
"""
Silver: Bronze の Overture places を、上流の変化から隔離した形に整える。

方針
----
  * 行は落とさない。品質判断は列（フラグ）にして Gold に委ねる。
    -> 自販機も confidence 低も残す。除外基準を後から変えられるようにするため。
  * カテゴリは自前の統制語彙 category_group に正規化する。
    -> categories.primary が 2026-09 に消えても Gold は無傷。
  * 名前は names.primary を正とする。names.common は全件 NULL で使えない。

  python silver_places.py
  python silver_places.py --report-unmapped   # 未マッピングのカテゴリを確認
"""

from __future__ import annotations

import argparse
import os
import sys

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F

from categories import (
    BASIC_CATEGORY_FALLBACK,
    BRAND_TO_GROUP,
    CATEGORY_TO_GROUP,
    LIQUOR_HOTEL_FIX,
    NAME_PATTERN_RULES,
)
from spark_session import build_spark

BRONZE = os.path.expanduser("~/develop/lakehouse/bronze/overture_places")
SILVER = os.path.expanduser("~/develop/lakehouse/silver/places")

# Delta が data skipping 統計を取れるのは 数値 / 文字列 / 日付・時刻 のみ。
# BooleanType, BinaryType, 複合型は指定するとエラーになる。
# is_vending_machine(Boolean) は category_group='vending_machine' と等価なので
# 文字列側で統計が効けば同じ効果が得られる。
STATS_COLS = "place_id,mesh1,mesh2,mesh3,mesh4,lon,lat,confidence,category_group"


# --------------------------------------------------------------------------
def _map_col(mapping: dict[str, str], key: Column) -> Column:
    """Python の dict を Spark の CASE WHEN に展開する。

    broadcast join より軽く、マッピングがコードに残るので追跡しやすい。
    """
    expr = F.lit(None).cast("string")
    for k, v in mapping.items():
        expr = F.when(key == F.lit(k), F.lit(v)).otherwise(expr)
    return expr


def _rule_name(lang: str) -> Column:
    """names.rules から指定言語の表記を取り出す。7.7% しか埋まっていない。"""
    return F.expr(
        f"element_at(filter(names.rules, x -> x.language = '{lang}' "
        f"AND x.variant = 'language'), 1).value"
    )


def _brand_override(brand: Column, name: Column) -> Column:
    """ブランド名で category_group を確定させる。

    brand 列だけでなく name 列も見るのは、brand が NULL でも店名に
    チェーン名が入っているケースが多いため（「万代 ○○店」等）。
    長いブランド名から順に評価して、部分一致の取り違えを防ぐ。
    """
    expr = F.lit(None).cast("string")
    for b in sorted(BRAND_TO_GROUP, key=len):  # 短い順に評価 -> 長い方が後勝ち
        hit = F.coalesce(brand, F.lit("")).contains(b) | F.coalesce(name, F.lit("")).contains(b)
        expr = F.when(hit, F.lit(BRAND_TO_GROUP[b])).otherwise(expr)
    return expr


def _name_pattern_override(name: Column, current: Column) -> Column:
    """店名の語からカテゴリを補正する。

    ★ 「○○酒店」が hotel に分類される不具合があるため、
      other 以外からの上書きも許可している（LIQUOR_HOTEL_FIX）。
    """
    expr = current
    for pattern, group, replaceable in NAME_PATTERN_RULES:
        cond = F.coalesce(name, F.lit("")).rlike(pattern)
        if replaceable is not None:
            cond = cond & current.isin(replaceable)
        expr = F.when(cond, F.lit(group)).otherwise(expr)

    # hotel 誤分類の救済は既存 group を問わず適用する
    expr = F.when(
        F.coalesce(name, F.lit("")).rlike(LIQUOR_HOTEL_FIX), F.lit("food_specialty")
    ).otherwise(expr)
    return expr


def build_silver(spark: SparkSession) -> DataFrame:
    b = spark.read.format("delta").load(BRONZE)

    cat_primary = F.col("categories.primary")
    name = F.col("names.primary")
    brand = F.col("brand.names.primary")

    # 1. カテゴリ由来（categories.primary -> basic_category -> other）
    from_category = F.coalesce(
        _map_col(CATEGORY_TO_GROUP, cat_primary),
        _map_col(BASIC_CATEGORY_FALLBACK, F.col("basic_category")),
        F.lit("other"),
    )
    # 2. ブランドで上書き（同一チェーン内のばらつきを吸収）
    from_brand = _brand_override(brand, name)
    resolved = F.coalesce(from_brand, from_category)
    # 3. 店名パターンで補正（酒店の hotel 誤分類など）
    group = _name_pattern_override(name, resolved)

    # どの層で決まったかを残す。誤補正を後から追跡できるようにするため。
    resolved_by = (
        F.when(F.coalesce(name, F.lit("")).rlike(LIQUOR_HOTEL_FIX), F.lit("name_pattern"))
        .when(group != resolved, F.lit("name_pattern"))
        .when(from_brand.isNotNull(), F.lit("brand"))
        .when(_map_col(CATEGORY_TO_GROUP, cat_primary).isNotNull(), F.lit("category"))
        .when(_map_col(BASIC_CATEGORY_FALLBACK, F.col("basic_category")).isNotNull(),
              F.lit("basic_category"))
        .otherwise(F.lit("unresolved"))
    )

    s = b.select(
        # --- キー -----------------------------------------------------
        F.col("id").alias("place_id"),
        "mesh1", "mesh2", "mesh3", "mesh4",
        F.col("lon").cast("double").alias("lon"),
        F.col("lat").cast("double").alias("lat"),
        # --- 名前 -----------------------------------------------------
        F.col("names.primary").alias("name"),
        F.coalesce(_rule_name("ja"), F.col("names.primary")).alias("name_ja"),
        _rule_name("en").alias("name_en"),
        # --- カテゴリ（正規化済み + 出所も残す）------------------------
        group.alias("category_group"),
        resolved_by.alias("resolved_by"),
        cat_primary.alias("category_raw"),
        F.col("basic_category").alias("basic_category_raw"),
        # --- 品質判断のための材料 -------------------------------------
        F.col("confidence").cast("double").alias("confidence"),
        F.col("brand.names.primary").alias("brand"),
        F.expr("transform(sources, x -> x.dataset)").alias("source_datasets"),
        # --- 来歴 -----------------------------------------------------
        "release", "ingested_at",
    )

    # 自販機フラグ。confidence が 0.8 固定で閾値では落とせないため、
    # カテゴリで明示的に印を付ける。行自体は残す。
    s = s.withColumn("is_vending_machine", F.col("category_group") == F.lit("vending_machine"))

    # 名前が自販機ブランドそのもの（「サントリー」等）のものも拾えるようにしておく
    s = s.withColumn(
        "is_low_confidence", F.col("confidence") < F.lit(0.5)
    )

    return s


# --------------------------------------------------------------------------
def report_unmapped(spark: SparkSession) -> None:
    """other に落ちた件数の多いカテゴリを出す。

    マッピングを育てるための入力。件数が多いものから categories.py に足していく。
    """
    df = build_silver(spark)
    print("\n--- category_group の内訳 ---")
    df.groupBy("category_group").count().orderBy(F.desc("count")).show(20, truncate=False)

    print("--- other に落ちた categories.primary 上位40（食料品関連を探す）---")
    (
        df.where("category_group = 'other'")
        .groupBy("category_raw").count().orderBy(F.desc("count")).limit(40)
        .show(40, truncate=False)
    )

    print("--- 食料品らしき語を含むが other になっているもの ---")
    (
        df.where("category_group = 'other' AND category_raw rlike "
                 "'(food|grocer|market|shop|store|butcher|fish|meat|produce|bakery|liquor)'")
        .groupBy("category_raw").count().orderBy(F.desc("count")).show(30, truncate=False)
    )


def write_silver(df: DataFrame) -> None:
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .option("delta.dataSkippingStatsColumns", STATS_COLS)
        .save(SILVER)
    )


def summarize(spark: SparkSession) -> None:
    df = spark.read.format("delta").load(SILVER)
    print(f"\n=== Silver: {df.count():,} 件")

    print("--- どの層でカテゴリが決まったか ---")
    df.groupBy("resolved_by").count().orderBy(F.desc("count")).show(truncate=False)

    print("--- ブランド/店名で救済された件数（category 層では other だったもの）---")
    (
        df.where("resolved_by in ('brand','name_pattern') AND category_group <> 'other'")
        .groupBy("category_group", "resolved_by").count()
        .orderBy(F.desc("count")).show(truncate=False)
    )

    print("--- 酒店の hotel 誤分類の救済確認 ---")
    (
        df.where("name rlike '酒店$|酒店[ \u3000]'")
        .groupBy("category_group", "category_raw").count()
        .orderBy(F.desc("count")).show(10, truncate=False)
    )

    print("--- category_group 別（自販機を除いた実質件数）---")
    (
        df.groupBy("category_group")
        .agg(
            F.count("*").alias("all"),
            F.sum(F.when(~F.col("is_low_confidence"), 1).otherwise(0)).alias("conf_ge_05"),
        )
        .orderBy(F.desc("all")).show(20, truncate=False)
    )

    print("--- 重複の疑い: 同一メッシュ・同一名称・同一グループ ---")
    dup = (
        df.where("category_group <> 'vending_machine'")
        .groupBy("mesh4", "name", "category_group").count().where("count > 1")
    )
    print(f"  重複グループ数: {dup.count():,}")
    dup.orderBy(F.desc("count")).limit(10).show(truncate=False)

    print("--- 食料品店(生鮮)を含む3次メッシュ数 ---")
    fresh = df.where("category_group = 'food_fresh' AND NOT is_low_confidence")
    print(f"  生鮮食料品店: {fresh.count():,} 件 / {fresh.select('mesh3').distinct().count():,} メッシュ")


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-unmapped", action="store_true")
    args = ap.parse_args()

    spark = build_spark("silver-places", driver_memory="6g")
    try:
        if args.report_unmapped:
            report_unmapped(spark)
            return 0

        write_silver(build_silver(spark))
        spark.sql(f"OPTIMIZE delta.`{SILVER}` ZORDER BY (mesh3)")
        summarize(spark)
    finally:
        spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())