#!/usr/bin/env python
"""
Silver の妥当性検証と、判断保留カテゴリの中身確認。

いちばん重要なのは Q1: Overture が日本の個人商店を捉えているか。
ここが弱いと「買い物難民マップ」ではなく「Overture 収録率マップ」になる。

  python validate_coverage.py
"""

from __future__ import annotations

import os

from pyspark.sql import functions as F

from spark_session import build_spark

SILVER = os.path.expanduser("~/develop/lakehouse/silver/places")

# 関西の主要スーパーチェーン。実店舗数が公知なので、収録率の物差しになる。
KANSAI_CHAINS = [
    "ライフ", "万代", "イズミヤ", "関西スーパー", "コーヨー", "阪急オアシス",
    "業務スーパー", "サンディ", "玉出", "マツゲン", "オークワ", "平和堂",
    "イオン", "ダイエー", "コノミヤ", "フレスコ", "食品館アプロ",
]

# 個人商店に典型的な屋号の語
SMALL_SHOP_WORDS = ["精肉", "鮮魚", "青果", "八百屋", "米穀", "米店", "酒店", "食料品", "商店"]


def main() -> None:
    spark = build_spark("validate-coverage", driver_memory="6g")
    df = spark.read.format("delta").load(SILVER)
    df.cache()

    # ==================================================================
    print("\n" + "=" * 70)
    print("Q1. 個人商店らしき屋号は、どの category_group に落ちているか")
    print("=" * 70)
    pat = "|".join(SMALL_SHOP_WORDS)
    small = df.where(F.col("name").rlike(pat))
    print(f"該当する屋号: {small.count():,} 件")
    (
        small.groupBy("category_group", "category_raw").count()
        .orderBy(F.desc("count")).show(30, truncate=False)
    )

    print("--- other に落ちた個人商店らしき店の名前サンプル ---")
    (
        small.where("category_group = 'other'")
        .select("name", "category_raw", "confidence")
        .limit(25).show(25, truncate=False)
    )

    # ==================================================================
    print("\n" + "=" * 70)
    print("Q2. 主要チェーンの収録件数（実店舗数と突き合わせる）")
    print("=" * 70)
    for chain in KANSAI_CHAINS:
        hit = df.where(
            F.col("name").contains(chain) | F.col("brand").contains(chain)
        )
        n = hit.count()
        if n == 0:
            print(f"  {chain:12s} : 0 件  ★収録なし")
            continue
        groups = (
            hit.groupBy("category_group").count().orderBy(F.desc("count")).collect()
        )
        g = ", ".join(f"{r['category_group']}={r['count']}" for r in groups[:3])
        print(f"  {chain:12s} : {n:5,d} 件   [{g}]")

    # ==================================================================
    print("\n" + "=" * 70)
    print("Q3. 判断保留カテゴリの正体（ブランド上位で見る）")
    print("=" * 70)
    for cat in ["shopping", "retail", "discount_store", "wholesale_store"]:
        print(f"\n--- {cat} ---")
        sub = df.where(F.col("category_raw") == cat)
        (
            sub.selectExpr("coalesce(brand, '(ブランドなし)') AS brand")
            .groupBy("brand").count().orderBy(F.desc("count")).show(10, truncate=False)
        )
        print("  名前サンプル:")
        sub.select("name").limit(8).show(8, truncate=False)

    # ==================================================================
    print("\n" + "=" * 70)
    print("Q4. category が NULL の 10,673 件は救えるか")
    print("=" * 70)
    nul = df.where("category_raw is null AND basic_category_raw is null")
    print(f"両方 NULL: {nul.count():,} 件")
    nul.select("name", "confidence").limit(20).show(20, truncate=False)

    # ==================================================================
    print("\n" + "=" * 70)
    print("Q5. 生鮮食料品店のメッシュ被覆（本番指標の素）")
    print("=" * 70)
    fresh = df.where("category_group = 'food_fresh' AND NOT is_low_confidence")
    all_mesh = df.select("mesh3").distinct().count()
    fresh_mesh = fresh.select("mesh3").distinct().count()
    print(f"  POI がある 3次メッシュ : {all_mesh:,}")
    print(f"  生鮮食料品店があるメッシュ: {fresh_mesh:,}  ({fresh_mesh / all_mesh * 100:.1f}%)")
    print("  -> 残り {:.1f}% が『店がない』候補。ここに人口を重ねる。".format(
        100 - fresh_mesh / all_mesh * 100))

    print("\n--- データソース別に見た生鮮食料品店（収録の偏り確認）---")
    (
        fresh.selectExpr("explode(source_datasets) AS ds")
        .groupBy("ds").count().orderBy(F.desc("count")).show(10, truncate=False)
    )

    spark.stop()


if __name__ == "__main__":
    main()