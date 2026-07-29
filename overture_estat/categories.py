"""
統制語彙（category_group）の定義。

Overture の categories.primary は 2026年9月リリースで廃止予定、
basic_category は粒度が粗く充足率も低い（97.9% vs 93.9%）。
どちらにも直接依存しないよう、自前の語彙をここ 1 ファイルに閉じ込める。

上流が変わったときに直すのはこのファイルだけ。Gold は category_group しか見ない。
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# categories.primary -> category_group
# --------------------------------------------------------------------------
CATEGORY_GROUPS: dict[str, list[str]] = {
    # 生鮮食料品が買える店。買い物アクセス指標の中核。
    "food_fresh": [
        "supermarket",
        "grocery_store",
        "specialty_grocery_store",
        "organic_grocery_store",
        "asian_grocery_store",
        "japanese_grocery_store",
        "indian_grocery_store",
        "korean_grocery_store",
        "chinese_grocery_store",
        "international_grocery_store",
        "butcher",
        "meat_shop",
        "seafood_market",
        "fish_market",
        "fishmonger",
        "greengrocer",
        "produce_market",
        "farmers_market",
    ],
    # 生鮮は弱いが日常食料品は買える
    "food_convenience": [
        "convenience_store",
    ],
    # 食品も扱う大型店
    "food_retail_large": [
        "department_store",
        "shopping_center",
        "shopping_mall",
        "warehouse_club",
    ],
    # 医薬品。買い物難民の議論では食料品と並んで参照される
    "pharmacy": [
        "pharmacy",
        "drugstore",
    ],
    # 食料品ではあるが生鮮ではない。定義を切り替えられるよう別立てにする。
    # 農水省の食料品アクセス困難人口の定義は「生鮮食料品を扱う店舗」なので
    # これらは strict には含めない。
    "food_specialty": [
        "bakery",
        "candy_store",
        "ice_cream_shop",
        "liquor_store",
        "tea_shop",
        "coffee_roasters",
    ],
    # 外食。買い物アクセスの分子ではないが、地域の商業集積を測る副指標になる。
    # other を 45 万件も抱えたままだと内訳が読めないので分離しておく。
    "restaurant": [
        "restaurant", "japanese_restaurant", "sushi_restaurant", "ramen_restaurant",
        "chinese_restaurant", "italian_restaurant", "french_restaurant",
        "korean_restaurant", "indian_restaurant", "thai_restaurant",
        "barbecue_restaurant", "seafood_restaurant", "fast_food_restaurant",
        "izakaya", "cafe", "coffee_shop", "bar", "pub", "desserts",
        "steakhouse", "buffet_restaurant", "food_court", "diner",
    ],
    # ★ 自動販売機。ダイドー/サントリー等が AllThePlaces 経由で
    #   一括投入されている。confidence 0.8 固定なので閾値では除去不可。
    "vending_machine": [
        "rental_kiosks",
    ],
}

# --------------------------------------------------------------------------
# 判断保留。ブランド/店名を見ないと食料品を扱うか決められないもの。
# validate_coverage.py の Q3 で中身を確認してから振り分ける。
# --------------------------------------------------------------------------
PENDING_INVESTIGATION = {
    "shopping": 5594,          # 金物店・買取センター等が混在。other 据え置き
    "retail": 2246,            # 同様に雑多。other 据え置き
    "wholesale_store": 717,    # コンテナー/紙料/リース等の産業系。other 据え置き
}

# 実測で存在が確認され、あとから追加したカテゴリ
CATEGORY_GROUPS["food_fresh"] += [
    "butcher_shop",            # 実測 216（basic_category 経由で拾えていた）
    "fruits_and_vegetables",   # 実測 74
    "food",                    # 実測 29
    "delicatessen",            # 惣菜店
    "rice_shop",
]

CATEGORY_TO_GROUP = {cat: g for g, cats in CATEGORY_GROUPS.items() for cat in cats}


# ==========================================================================
# 上書き層 1: ブランド
#
# 同一チェーンでもカテゴリがばらつく（関西スーパー: food_fresh 63 / other 66）。
# カテゴリだけで絞ると系統的に半分取りこぼすため、ブランドで確定させる。
# 照合は brand 列と name 列の前方一致的な包含で行う。
# ==========================================================================
BRAND_TO_GROUP: dict[str, str] = {}


def _reg(group: str, brands: list[str]) -> None:
    for b in brands:
        BRAND_TO_GROUP[b] = group


# 生鮮を扱う食品スーパー
_reg("food_fresh", [
    "業務スーパー", "関西スーパー", "阪急オアシス", "阪急キッチンエール",
    "万代", "イズミヤ", "コーヨー", "サンディ", "マツゲン", "オークワ",
    "コノミヤ", "フレスコ", "食品館アプロ", "スーパー玉出", "ライフ",
    "平和堂", "フレンドマート", "ダイエー", "イオンスタイル",
    "マックスバリュ", "ザ・ビッグ", "サタケ", "ハーベス", "光洋",
    "グルメシティ", "デイリーカナート", "パントリー", "成城石井",
    "KOHYO", "トーホーストア", "コープこうべ", "生活協同組合コープ",
    "ラ・ムー", "ディオ", "TRIAL", "トライアル", "ロピア", "スーパーマーケットバロー",
    "近商ストア", "ハーベスト", "サンプラザ", "スーパーナカガワ",
])

# 大型店（食品売場あり）
_reg("food_retail_large", [
    "イオンモール", "アル・プラザ", "コストコ", "イトーヨーカドー",
    "近鉄百貨店", "阪急百貨店", "阪神百貨店", "大丸", "高島屋", "そごう",
])

# コンビニ
_reg("food_convenience", [
    "セブン-イレブン", "セブンイレブン", "ファミリーマート", "ローソン",
    "ミニストップ", "デイリーヤマザキ", "ポプラ", "セイコーマート",
])

# ドラッグストア
_reg("pharmacy", [
    "マツモトキヨシ", "スギ薬局", "ココカラファイン", "ドラッグストアモリ",
    "キリン堂", "ダイコクドラッグ", "サンドラッグ", "ウエルシア",
    "ツルハドラッグ", "コクミン", "クスリのアオキ",
])

# 100 円ショップ・雑貨（食品を主に扱わない）。discount_store から分離する。
_reg("other", [
    "ダイソー", "セリア", "キャンドゥ", "3COINS", "ワッツ", "ニトリ",
    "コメリ", "カインズ", "ドン・キホーテ",
])


# ==========================================================================
# 上書き層 2: 店名パターン
#
# ★ 「○○酒店」が category=hotel になる不具合がある。
#    中国語の「酒店」=ホテル として処理されたものと思われる。
#    誤カテゴリを上書きする必要があるため、other 以外にも適用する。
# ==========================================================================
# (正規表現, 付与する group, 上書きしてよい既存 group) の順
NAME_PATTERN_RULES: list[tuple[str, str, list[str] | None]] = [
    # 酒店。hotel 誤分類を明示的に救う
    (r"酒店$|酒店[ 　]|酒販|地酒|酒のやまや|リカー", "food_specialty", ["other", "restaurant"]),
    # 生鮮
    (r"精肉店|精肉|肉店$|ミートショップ", "food_fresh", ["other"]),
    (r"鮮魚店|鮮魚|魚店$|魚屋", "food_fresh", ["other"]),
    (r"青果店|青果|八百屋|果物店", "food_fresh", ["other"]),
    (r"米穀店|米穀|米店$|お米の", "food_fresh", ["other"]),
    (r"豆腐店|豆腐$", "food_fresh", ["other"]),
    (r"食料品店|食品店$|食品館|生鮮", "food_fresh", ["other"]),
    # パン・菓子
    (r"パン工房|ベーカリー|パン屋", "food_specialty", ["other"]),
    (r"和菓子|洋菓子|菓子店", "food_specialty", ["other"]),
]

# hotel 誤分類の救済だけは特別扱い（restaurant/other 以外からも上書きする）
LIQUOR_HOTEL_FIX = r"酒店$|酒店[ 　]"


# 逆引き
CATEGORY_TO_GROUP: dict[str, str] = {
    cat: group for group, cats in CATEGORY_GROUPS.items() for cat in cats
}

# 食料品アクセスの分子に数えるグループ（定義を切り替えられるようにしておく）
FOOD_ACCESS_STRICT = ["food_fresh"]                      # 生鮮のみ（農水省の定義に近い）
FOOD_ACCESS_BROAD = ["food_fresh", "food_convenience", "food_retail_large"]

# basic_category からのフォールバック（categories.primary が NULL の場合用）
BASIC_CATEGORY_FALLBACK: dict[str, str] = {
    "food_and_beverage_store": "food_fresh",
    "convenience_store": "food_convenience",
    "supermarket": "food_fresh",
    "grocery_store": "food_fresh",
    "department_store": "food_retail_large",
    "shopping_center": "food_retail_large",
    "pharmacy": "pharmacy",
    "drugstore": "pharmacy",
    "rental_service": "vending_machine",
}