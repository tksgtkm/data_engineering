# ハンズオン: ゼロからコマンドで組み立てる

このサンプルプロジェクトを、空のディレクトリからコマンドだけで組み立てる手順です。
各ステップの終わりに「確認」のコマンドがあるので、層ごとに動くことを確かめながら進められます。

ファイルの中身は `cat > ファイル名 <<'EOF' … EOF` 形式で載せています。ブロックごとにターミナルに貼り付けて実行してください。
エディタで同じ内容を書いても構いません。

完成形のディレクトリ構成は次のとおりです。

```
dbt-metricflow-lightdash-duckdb/
├── pyproject.toml / uv.lock        ← uv が管理
├── scripts/generate_seeds.py
├── lake/                           ← DuckLake（dbt が書き込む。git 管理外）
├── dbt/                            ← dbt init で作る
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── seeds/*.csv
│   └── models/{staging,marts,utils,semantic}/
├── docker-compose.yml
├── docker/init-minio.sh
└── .env
```

## 前提

- Ubuntu または macOS
- [uv](https://docs.astral.sh/uv/)、Docker（Compose v2）、Node.js（Lightdash CLI 用。v24 推奨）
- インターネット接続（DuckDB の拡張機能 ducklake / sqlite を初回に自動ダウンロードします）

---

## Step 0. プロジェクトの土台と Python 環境（uv）

```bash
mkdir dbt-metricflow-lightdash-duckdb && cd dbt-metricflow-lightdash-duckdb
uv init --bare --python 3.12
uv add "dbt-metricflow[dbt-duckdb]>=0.15" "dbt-core>=1.10"
mkdir -p scripts docker lake/data
printf '.env\n.venv/\nlake/\ndbt/target/\ndbt/logs/\ndbt/dbt_packages/\n' > .gitignore
```

`dbt-metricflow[dbt-duckdb]` を入れると、dbt-core・dbt-duckdb・MetricFlow（`mf` コマンド）がまとめて入ります。

**確認**

```bash
uv run dbt --version
uv run mf --help | head -5
```

---

## Step 1. `dbt init`

`dbt init` はプロジェクト名でディレクトリを作るので、作成後に `dbt/` へリネームします。
`--skip-profile-setup` を付けるのは、対話式のセットアップでは DuckLake の `attach` 設定まで書けないためです。プロファイルは Step 2 で自分で書きます。

```bash
uv run dbt init shop_analytics --skip-profile-setup
mv shop_analytics dbt
rm -rf dbt/models/example dbt/analyses dbt/macros dbt/snapshots dbt/tests
ls dbt
```

生成された `dbt_project.yml` を、このサンプル用の内容で上書きします。

- staging は view、marts / utils は table として作ります。
- marts には `bi` タグを付けます。後で Lightdash に出すモデルの選択に使います。

```bash
cat > dbt/dbt_project.yml <<'EOF'
name: shop_analytics
version: "1.0.0"
config-version: 2

profile: shop_analytics

model-paths: ["models"]
seed-paths: ["seeds"]
target-path: "target"
clean-targets: ["target", "dbt_packages"]

seeds:
  shop_analytics:
    +schema: raw
    raw_orders:
      +column_types:
        order_date: date
    raw_customers:
      +column_types:
        signup_date: date
    raw_order_items:
      +column_types:
        discount_rate: numeric(4, 2)

models:
  shop_analytics:
    staging:
      +materialized: view
      +schema: staging
    marts:
      +materialized: table
      +schema: marts
      +tags: [bi]        # Lightdash に出すモデル（lightdash deploy -s tag:bi）
    utils:
      +materialized: table
      +schema: utils
EOF
```

---

## Step 2. DuckLake への接続（profiles.yml）

DuckDB はメモリ上で動かし、テーブルの実体は DuckLake に書きます。DuckLake は、カタログが `lake/catalog.sqlite`、データが `lake/data/*.parquet` という構成です。
`LAKE_DIR` は**絶対パス**で渡してください。後で Lightdash コンテナにも同じパスでマウントします。

```bash
cat > dbt/profiles.yml <<'EOF'
# DuckDB + DuckLake（カタログ = SQLite ファイル, データ = ローカルの Parquet）
#
# LAKE_DIR は「絶対パス」で渡す（Makefile が $(CURDIR)/lake を自動で設定する）。
# docker-compose.yml でも同じ絶対パスで Lightdash コンテナにマウントするので、
# ホストの dbt / MetricFlow とコンテナの Lightdash が同じファイルを同じパスで読める。
shop_analytics:
  target: dev
  outputs:
    dev:
      type: duckdb
      # セッション用 DB はメモリ上でよい（テーブル本体は下の DuckLake に書かれる）。
      # ファイルにすると dbt と mf を同時に動かしたときにロックで衝突する
      path: ":memory:"
      extensions:
        - ducklake
        - sqlite
      attach:
        - path: "ducklake:sqlite:{{ env_var('LAKE_DIR') }}/catalog.sqlite"
          alias: lake
          options:
            data_path: "{{ env_var('LAKE_DIR') }}/data/"
      database: lake
      schema: main
      threads: 1
EOF
```

環境変数を設定します。**ターミナルを開き直したら、毎回ここを再実行してください**（プロジェクトのルートで実行します）。

```bash
export LAKE_DIR=$PWD/lake
export DBT_PROFILES_DIR=$PWD/dbt
cd dbt
```

**確認**: `All checks passed!` が出れば OK です。ducklake / sqlite の拡張機能もここでインストールされます。

```bash
uv run dbt debug
```

---

## Step 3. 生データ（seeds）

サンプルデータを生成するスクリプトを置き、CSV を作ります。
乱数シードを固定しているので、何度実行しても同じデータになります。

```bash
cd ..   # プロジェクトルートへ
```

```bash
cat > scripts/generate_seeds.py <<'EOF'
"""サンプルEC データ（seed CSV）を決定的に生成するスクリプト。

    python scripts/generate_seeds.py

dbt/seeds/ 以下に raw_customers / raw_products / raw_orders / raw_order_items を書き出す。
乱数シード固定なので何度実行しても同じデータになる。
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "dbt" / "seeds"
rng = random.Random(42)

START = date(2025, 1, 1)
END = date(2026, 9, 30)
N_CUSTOMERS = 600

REGIONS = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州"]
REGION_WEIGHTS = [5, 6, 35, 15, 20, 6, 3, 10]
SEGMENTS = ["consumer", "business"]
CHANNELS = ["web", "app", "marketplace"]

PRODUCTS = [
    # (name, category, unit_price)
    ("ドリップコーヒー 10袋", "coffee", 980),
    ("コーヒー豆 200g", "coffee", 1680),
    ("コーヒー豆 1kg", "coffee", 6800),
    ("緑茶ティーバッグ 30包", "tea", 860),
    ("ほうじ茶 100g", "tea", 1200),
    ("抹茶 40g", "tea", 2400),
    ("ハンドドリッパー", "equipment", 2980),
    ("電動ミル", "equipment", 12800),
    ("ステンレスケトル", "equipment", 8900),
    ("焼き菓子アソート", "snacks", 1800),
    ("ナッツミックス 500g", "snacks", 1480),
    ("ギフトボックス", "gift", 5400),
]
STATUSES = ["completed", "completed", "completed", "completed", "completed",
            "completed", "completed", "shipped", "returned", "cancelled"]


def daterange_days() -> int:
    return (END - START).days


def main() -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)

    # customers
    customers = []
    for cid in range(1, N_CUSTOMERS + 1):
        signup = START + timedelta(days=rng.randint(0, daterange_days() - 30))
        customers.append({
            "id": cid,
            "region": rng.choices(REGIONS, REGION_WEIGHTS)[0],
            "segment": rng.choices(SEGMENTS, [85, 15])[0],
            "signup_date": signup.isoformat(),
        })

    # products
    products = [
        {"id": pid, "name": n, "category": c, "list_price": p}
        for pid, (n, c, p) in enumerate(PRODUCTS, start=1)
    ]

    # orders / order_items
    orders, items = [], []
    oid = iid = 0
    for c in customers:
        signup = date.fromisoformat(c["signup_date"])
        # business は注文頻度高め、さらに顧客ごとの活発度にばらつき
        activity = rng.expovariate(1.0) * (3 if c["segment"] == "business" else 1)
        n_orders = max(0, int(rng.gauss(4, 2) * activity))
        for _ in range(n_orders):
            span = (END - signup).days
            if span <= 0:
                break
            # 後半ほど注文が増えるように（成長トレンド）
            offset = int(span * (rng.random() ** 0.7))
            od = signup + timedelta(days=offset)
            # 12月は繁忙期
            if od.month != 12 and rng.random() < 0.08:
                continue
            oid += 1
            orders.append({
                "id": oid,
                "customer_id": c["id"],
                "order_date": od.isoformat(),
                "status": rng.choice(STATUSES),
                "channel": rng.choices(CHANNELS, [50, 35, 15])[0],
            })
            for p in rng.sample(products, k=rng.choices([1, 2, 3, 4], [50, 30, 15, 5])[0]):
                iid += 1
                qty = rng.choices([1, 2, 3, 5], [60, 25, 10, 5])[0]
                if c["segment"] == "business":
                    qty *= rng.choice([1, 2, 4])
                discount = rng.choices([0, 0.05, 0.1, 0.2], [70, 15, 10, 5])[0]
                items.append({
                    "id": iid,
                    "order_id": oid,
                    "product_id": p["id"],
                    "quantity": qty,
                    "unit_price": p["list_price"],
                    "discount_rate": discount,
                })

    orders.sort(key=lambda o: (o["order_date"], o["id"]))

    def dump(name: str, rows: list[dict]) -> None:
        path = SEED_DIR / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {path.relative_to(SEED_DIR.parent.parent)} ({len(rows)} rows)")

    dump("raw_customers", customers)
    dump("raw_products", products)
    dump("raw_orders", orders)
    dump("raw_order_items", items)


if __name__ == "__main__":
    main()
EOF
```

```bash
uv run python scripts/generate_seeds.py
cd dbt
uv run dbt seed
```

**確認**: Parquet ファイルが `lake/data/` 以下にできていれば OK です。

```bash
find $LAKE_DIR/data -name '*.parquet' | head
ls -la $LAKE_DIR
```

---

## Step 4. staging 層（view）

カラム名を揃え、明細金額を計算する層です。

```bash
cd .. && mkdir -p dbt/models/staging   # ファイル作成は常にプロジェクトルートから
```

```bash
cat > dbt/models/staging/stg_customers.sql <<'EOF'
select
    id            as customer_id,
    region,
    segment,
    signup_date   as signed_up_at
from {{ ref('raw_customers') }}
EOF

cat > dbt/models/staging/stg_products.sql <<'EOF'
select
    id          as product_id,
    name        as product_name,
    category,
    list_price
from {{ ref('raw_products') }}
EOF

cat > dbt/models/staging/stg_orders.sql <<'EOF'
select
    id            as order_id,
    customer_id,
    order_date    as ordered_at,
    status,
    channel
from {{ ref('raw_orders') }}
EOF

cat > dbt/models/staging/stg_order_items.sql <<'EOF'
select
    id                                              as order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount_rate,
    round(quantity * unit_price * (1 - discount_rate), 0) as line_amount
from {{ ref('raw_order_items') }}
EOF

cat > dbt/models/staging/_staging.yml <<'EOF'
models:
  - name: stg_customers
    columns:
      - name: customer_id
        data_tests: [unique, not_null]
  - name: stg_products
    columns:
      - name: product_id
        data_tests: [unique, not_null]
  - name: stg_orders
    columns:
      - name: order_id
        data_tests: [unique, not_null]
      - name: status
        data_tests:
          - accepted_values:
              arguments:
                values: [completed, shipped, returned, cancelled]
  - name: stg_order_items
    columns:
      - name: order_item_id
        data_tests: [unique, not_null]
      - name: order_id
        data_tests:
          - relationships:
              arguments:
                to: ref('stg_orders')
                field: order_id
EOF
```

**確認**

```bash
cd dbt && uv run dbt build -s staging
```

---

## Step 5. marts 層（table）

分析で使うファクトとディメンションです。

`_marts.yml` の `config.meta`（joins や表示形式）は、Lightdash 用の設定です。dbt 自体は使わないので、ここで書いておいても dbt の動作には影響しません。

```bash
cd .. && mkdir -p dbt/models/marts
```

```bash
cat > dbt/models/marts/fct_orders.sql <<'EOF'
-- 注文粒度のファクト。売上系メトリクスの主役。
with items as (
    select
        order_id,
        sum(line_amount)  as order_total,
        sum(quantity)     as item_quantity,
        count(*)          as line_count
    from {{ ref('stg_order_items') }}
    group by 1
),

orders as (
    select
        *,
        row_number() over (partition by customer_id order by ordered_at, order_id) as customer_order_seq
    from {{ ref('stg_orders') }}
)

select
    o.order_id,
    o.customer_id,
    o.ordered_at,
    o.status,
    o.channel,
    o.status = 'completed'          as is_completed,
    o.customer_order_seq = 1        as is_first_order,
    coalesce(i.order_total, 0)      as order_total,
    coalesce(i.item_quantity, 0)    as item_quantity,
    coalesce(i.line_count, 0)       as line_count
from orders o
left join items i using (order_id)
EOF

cat > dbt/models/marts/fct_order_items.sql <<'EOF'
-- 明細粒度のファクト。商品カテゴリ別の分析用。
select
    i.order_item_id,
    i.order_id,
    i.product_id,
    o.customer_id,
    o.ordered_at,
    o.status,
    i.quantity,
    i.unit_price,
    i.discount_rate,
    i.line_amount,
    i.discount_rate > 0 as is_discounted
from {{ ref('stg_order_items') }} i
join {{ ref('stg_orders') }} o using (order_id)
EOF

cat > dbt/models/marts/dim_customers.sql <<'EOF'
with order_stats as (
    select
        customer_id,
        min(ordered_at)    as first_ordered_at,
        max(ordered_at)    as last_ordered_at,
        count(*)           as order_count,
        sum(order_total)   as lifetime_value
    from {{ ref('fct_orders') }}
    where status <> 'cancelled'
    group by 1
)

select
    c.customer_id,
    c.region,
    c.segment,
    c.signed_up_at,
    s.first_ordered_at,
    s.last_ordered_at,
    coalesce(s.order_count, 0)     as order_count,
    coalesce(s.lifetime_value, 0)  as lifetime_value,
    case
        when s.order_count is null then 'no_orders'
        when s.order_count = 1     then 'one_time'
        when s.order_count < 5     then 'repeat'
        else 'loyal'
    end as customer_tier
from {{ ref('stg_customers') }} c
left join order_stats s using (customer_id)
EOF

cat > dbt/models/marts/dim_products.sql <<'EOF'
select * from {{ ref('stg_products') }}
EOF

cat > dbt/models/marts/_marts.yml <<'EOF'
# ここはモデル/カラム定義と「Lightdash 固有の設定」（joins・表示形式など）を置く場所。
# メトリクスの定義は models/semantic/ の MetricFlow 側に一本化している。
models:
  - name: fct_orders
    description: 注文粒度のファクト（1行=1注文）
    config:
      meta:
        label: 注文
        # Lightdash の join は明示的に書く（MetricFlow の entity join は Lightdash では読まれない）
        joins:
          - join: dim_customers
            sql_on: ${fct_orders.customer_id} = ${dim_customers.customer_id}
            type: left
            relationship: many-to-one
    columns:
      - name: order_id
        data_tests: [unique, not_null]
      - name: customer_id
        data_tests: [not_null]
      - name: ordered_at
        description: 注文日
        config:
          meta:
            dimension:
              type: date
              time_intervals: [DAY, WEEK, MONTH, QUARTER, YEAR]
      - name: status
      - name: channel
      - name: is_completed
      - name: is_first_order
      - name: order_total
        description: 注文合計（割引後, 円）
        config:
          meta:
            dimension:
              format: '¥#,##0'
      - name: item_quantity
      - name: line_count

  - name: fct_order_items
    description: 明細粒度のファクト（1行=1注文明細）
    config:
      meta:
        label: 注文明細
        joins:
          - join: dim_products
            sql_on: ${fct_order_items.product_id} = ${dim_products.product_id}
            type: left
            relationship: many-to-one
          - join: dim_customers
            sql_on: ${fct_order_items.customer_id} = ${dim_customers.customer_id}
            type: left
            relationship: many-to-one
    columns:
      - name: order_item_id
        data_tests: [unique, not_null]
      - name: order_id
      - name: product_id
      - name: customer_id
      - name: ordered_at
        config:
          meta:
            dimension:
              type: date
              time_intervals: [DAY, WEEK, MONTH, QUARTER, YEAR]
      - name: status
      - name: quantity
      - name: unit_price
      - name: discount_rate
      - name: line_amount
      - name: is_discounted

  - name: dim_customers
    description: 顧客ディメンション（1行=1顧客）
    config:
      meta:
        label: 顧客
    columns:
      - name: customer_id
        data_tests: [unique, not_null]
      - name: region
        description: 地方（北海道〜九州）
      - name: segment
        description: consumer / business
      - name: signed_up_at
        config:
          meta:
            dimension:
              type: date
              time_intervals: [DAY, WEEK, MONTH, QUARTER, YEAR]
      - name: first_ordered_at
      - name: last_ordered_at
      - name: order_count
      - name: lifetime_value
      - name: customer_tier

  - name: dim_products
    description: 商品ディメンション
    config:
      meta:
        label: 商品
    columns:
      - name: product_id
        data_tests: [unique, not_null]
      - name: product_name
      - name: category
      - name: list_price
EOF
```

**確認**

```bash
cd dbt
uv run dbt build -s marts
uv run dbt show --inline "select status, count(*) n, sum(order_total) revenue from {{ ref('fct_orders') }} group by 1"
```

---

## Step 6. MetricFlow 用タイムスパイン

累積メトリクスや前月比の計算に必要な日次カレンダーです。

```bash
cd .. && mkdir -p dbt/models/utils
```

```bash
cat > dbt/models/utils/metricflow_time_spine.sql <<'EOF'
-- MetricFlow が累積メトリクスや時系列の穴埋めに使う日次カレンダー。
{{ config(materialized='table') }}

select cast(d as date) as date_day
from unnest(
    generate_series(date '2024-01-01', date '2027-12-31', interval 1 day)
) as t(d)
EOF

cat > dbt/models/utils/_utils.yml <<'EOF'
models:
  - name: metricflow_time_spine
    description: MetricFlow 用の日次タイムスパイン（Lightdash には出さない）
    time_spine:
      standard_granularity_column: date_day
    columns:
      - name: date_day
        granularity: day
EOF
```

```bash
cd dbt && uv run dbt build -s utils
```

---

## Step 7. セマンティックモデルとメトリクス（MetricFlow）

ここが本題です。entity・dimension・measure を定義し、その上にメトリクスを定義します。

```bash
cd .. && mkdir -p dbt/models/semantic
```

```bash
cat > dbt/models/semantic/sem_orders.yml <<'EOF'
# MetricFlow セマンティックモデル（legacy spec: dbt Core 1.6+ で動く書き方）
semantic_models:
  - name: orders
    description: 注文（1行=1注文）
    model: ref('fct_orders')
    defaults:
      agg_time_dimension: ordered_at

    entities:
      - name: order
        type: primary
        expr: order_id
      - name: customer
        type: foreign
        expr: customer_id

    dimensions:
      - name: ordered_at
        type: time
        type_params:
          time_granularity: day
      - name: status
        type: categorical
      - name: channel
        type: categorical
      - name: is_first_order
        type: categorical

    measures:
      - name: order_count
        description: 注文件数
        agg: count
        expr: order_id
      - name: revenue
        description: 売上（割引後の注文合計）
        agg: sum
        expr: order_total
      - name: completed_orders
        description: 完了注文数
        agg: sum_boolean
        expr: is_completed
      - name: ordering_customers
        description: 注文した顧客のユニーク数
        agg: count_distinct
        expr: customer_id
      - name: median_order_total
        agg: median
        expr: order_total
      - name: p90_order_total
        agg: percentile
        expr: order_total
        agg_params:
          percentile: 0.9
          use_discrete_percentile: false
EOF

cat > dbt/models/semantic/sem_order_items.yml <<'EOF'
semantic_models:
  - name: order_items
    description: 注文明細（1行=1明細）
    model: ref('fct_order_items')
    defaults:
      agg_time_dimension: ordered_at

    entities:
      - name: order_item
        type: primary
        expr: order_item_id
      - name: order
        type: foreign
        expr: order_id
      - name: product
        type: foreign
        expr: product_id

    dimensions:
      - name: ordered_at
        type: time
        type_params:
          time_granularity: day
      - name: is_discounted
        type: categorical

    measures:
      - name: line_count
        agg: count
        expr: order_item_id
      - name: items_sold
        description: 販売点数
        agg: sum
        expr: quantity
      - name: item_revenue
        description: 明細ベースの売上
        agg: sum
        expr: line_amount
      - name: discounted_lines
        agg: sum_boolean
        expr: is_discounted
EOF

cat > dbt/models/semantic/sem_dimensions.yml <<'EOF'
# 顧客・商品のディメンション用セマンティックモデル。
# orders / order_items から entity（customer / product）経由で MetricFlow が自動 join する。
semantic_models:
  - name: customers
    description: 顧客
    model: ref('dim_customers')
    defaults:
      agg_time_dimension: signed_up_at

    entities:
      - name: customer
        type: primary
        expr: customer_id

    dimensions:
      - name: region
        type: categorical
      - name: segment
        type: categorical
      - name: customer_tier
        type: categorical
      - name: signed_up_at
        type: time
        type_params:
          time_granularity: day

    measures:
      - name: customers
        description: 顧客数（登録日基準）
        agg: count_distinct
        expr: customer_id
        create_metric: true

  - name: products
    description: 商品
    model: ref('dim_products')

    entities:
      - name: product
        type: primary
        expr: product_id

    dimensions:
      - name: category
        type: categorical
      - name: product_name
        type: categorical
EOF

cat > dbt/models/semantic/metrics.yml <<'EOF'
# メトリクス定義（Single Source of Truth）
#
# [MF+LD] … MetricFlow でも Lightdash でも使える（Lightdash が自動変換）
# [MF only] … MetricFlow（mf query / dbt Semantic Layer）でのみ使える。
#             Lightdash の deploy 時には warning を出してスキップされる。
metrics:
  # ---------- orders: simple ----------
  - name: revenue                       # [MF+LD]
    label: 売上
    description: 割引後の注文合計
    type: simple
    type_params:
      measure: revenue
    config:
      meta:
        group_label: 売上

  - name: order_count                   # [MF+LD]
    label: 注文数
    type: simple
    type_params:
      measure: order_count
    config:
      meta:
        group_label: 注文

  - name: completed_orders              # [MF+LD] sum_boolean
    label: 完了注文数
    type: simple
    type_params:
      measure: completed_orders
    config:
      meta:
        group_label: 注文

  - name: completed_revenue             # [MF+LD] 同一モデルの Dimension フィルタ → CASE WHEN
    label: 完了売上
    description: status = completed の注文だけの売上
    type: simple
    type_params:
      measure: revenue
    filter: |
      {{ Dimension('order__status') }} = 'completed'
    config:
      meta:
        group_label: 売上

  - name: ordering_customers            # [MF+LD]
    label: 注文顧客数
    type: simple
    type_params:
      measure: ordering_customers
    config:
      meta:
        group_label: 顧客

  - name: median_order_value            # [MF+LD]
    label: 注文単価（中央値）
    type: simple
    type_params:
      measure: median_order_total
    config:
      meta:
        group_label: 売上

  - name: p90_order_value               # [MF+LD] percentile（0-1 は Lightdash 側で 0-100 に正規化される）
    label: 注文単価（P90）
    type: simple
    type_params:
      measure: p90_order_total
    config:
      meta:
        group_label: 売上

  # ---------- orders: ratio / derived（同一モデル内なので Lightdash でも使える） ----------
  - name: average_order_value           # [MF+LD]
    label: 平均注文単価（AOV）
    type: ratio
    type_params:
      numerator: revenue
      denominator: order_count
    config:
      meta:
        group_label: 売上

  - name: completion_rate               # [MF+LD] フィルタ付き分子
    label: 注文完了率
    type: ratio
    type_params:
      numerator:
        name: order_count
        filter: |
          {{ Dimension('order__status') }} = 'completed'
        alias: completed_order_count
      denominator: order_count
    config:
      meta:
        group_label: 注文

  - name: revenue_per_customer          # [MF+LD]
    label: 顧客あたり売上
    type: derived
    type_params:
      expr: revenue / nullif(ordering_customers, 0)
      metrics:
        - name: revenue
        - name: ordering_customers
    config:
      meta:
        group_label: 顧客

  # ---------- order_items ----------
  - name: items_sold                    # [MF+LD]
    label: 販売点数
    type: simple
    type_params:
      measure: items_sold
    config:
      meta:
        group_label: 商品

  - name: item_revenue                  # [MF+LD]
    label: 明細売上
    type: simple
    type_params:
      measure: item_revenue
    config:
      meta:
        group_label: 商品

  - name: line_count                    # [MF+LD]
    label: 明細数
    type: simple
    type_params:
      measure: line_count
    config:
      meta:
        group_label: 商品

  - name: discounted_line_share         # [MF+LD]
    label: 割引明細比率
    type: ratio
    type_params:
      numerator: discounted_lines_metric
      denominator: line_count
    config:
      meta:
        group_label: 商品

  - name: discounted_lines_metric       # 上の ratio 用の補助メトリクス
    label: 割引明細数
    type: simple
    type_params:
      measure: discounted_lines
    config:
      meta:
        group_label: 商品
        hidden: true

  # ---------- MetricFlow でしか表現できないもの ----------
  - name: cumulative_revenue            # [MF only] cumulative
    label: 累積売上
    type: cumulative
    type_params:
      measure: revenue

  - name: revenue_mtd                   # [MF only] cumulative（月初来）
    label: 当月累計売上
    type: cumulative
    type_params:
      measure: revenue
      cumulative_type_params:
        grain_to_date: month

  - name: revenue_last_month            # [MF only] offset_window の補助
    label: 前月売上
    type: derived
    type_params:
      expr: revenue_prev
      metrics:
        - name: revenue
          offset_window: 1 month
          alias: revenue_prev

  - name: revenue_mom_growth            # [MF only] 前月比（offset_window）
    label: 売上 前月比
    type: derived
    type_params:
      expr: (revenue - revenue_prev) / nullif(revenue_prev, 0)
      metrics:
        - name: revenue
        - name: revenue
          offset_window: 1 month
          alias: revenue_prev

  - name: business_revenue              # [MF only] 別モデル（customers）の Dimension でフィルタ
    label: 法人売上
    type: simple
    type_params:
      measure: revenue
    filter: |
      {{ Dimension('customer__segment') }} = 'business'
EOF
```

**確認**: 定義をパースし、ウェアハウスに対して検証します。

`dbt parse` は `target/manifest.json` に semantic_models と metrics を書き出します。MetricFlow も Lightdash も、このファイルを読みます。

```bash
cd dbt
uv run dbt parse
uv run mf validate-configs
```

いろいろクエリしてみます。

```bash
# 一覧
uv run mf list metrics
uv run mf list dimensions --metrics revenue

# 月次: simple / ratio / derived(offset_window)
uv run mf query --metrics revenue,order_count,average_order_value,completion_rate,revenue_mom_growth \
  --group-by metric_time__month --order metric_time__month

# entity 経由の自動 join（orders → customers）と、別モデルの dimension でのフィルタ
uv run mf query --metrics revenue,business_revenue,revenue_per_customer \
  --group-by customer__region --order -revenue

# order_items → products の join
uv run mf query --metrics items_sold,item_revenue,discounted_line_share --group-by product__category

# cumulative（当月累計）
uv run mf query --metrics revenue_mtd,cumulative_revenue --group-by metric_time__day \
  --where "{{ TimeDimension('metric_time', 'day') }} >= '2026-09-25'"

# 生成 SQL を見る
uv run mf query --metrics revenue_mom_growth --group-by metric_time__month --explain
```

---

## Step 8. Lightdash への変換を確認（サーバー不要）

Lightdash CLI を入れて compile だけ実行し、MetricFlow の定義がどう変換されるかを確認します。
CLI は内部で `dbt` を呼ぶので、`uv run` 経由で実行します（venv の `bin` が PATH に入ります）。

```bash
npm install -g @lightdash/cli
uv run lightdash compile --project-dir . --profiles-dir . -s tag:bi --verbose
```

期待される出力:

```
> Skipped MetricFlow metric "cumulative_revenue": metric type "cumulative" is not supported yet.
> Skipped MetricFlow metric "revenue_mtd": metric type "cumulative" is not supported yet.
> Skipped MetricFlow metric "business_revenue": ... (cross-model filters are not supported).
> Skipped MetricFlow metric "revenue_last_month": ... offset_window/offset_to_grain, which is not supported.
> Skipped MetricFlow metric "revenue_mom_growth": ... offset_window/offset_to_grain, which is not supported.
> Translated 16 MetricFlow metric(s) into Lightdash metrics (skipped 5 unsupported, ...)
Compiled 4 explores, SUCCESS=4 ERRORS=0
```

スキップされた5つが、`metrics.yml` で `[MF only]` と書いたものと一致することを確認してください。

---

## Step 9. Lightdash を起動する（docker compose）

起動するコンテナは次の3つで、すべて `127.0.0.1` にだけ公開します。

- **Lightdash 本体**
- **lightdash-db**: Lightdash 自身のメタデータ用 Postgres
- **MinIO**: Lightdash は S3 互換ストレージがないと起動しない仕様のため、ローカルに立てます。AWS には接続しません。

```bash
cd ..   # プロジェクトルートへ
```

```bash
cat > docker-compose.yml <<'EOF'
# すべて localhost で完結する構成（外部クラウドへの接続なし）
#
# lightdash     : Lightdash 本体（http://localhost:8080）
# lightdash-db  : Lightdash 自身のメタデータ（ユーザー・チャート・ダッシュボード）用 Postgres
# minio         : Lightdash が起動に必須とする S3 互換ストレージ。ローカルのコンテナで、AWS には繋がない
#
# 分析データ（DuckLake = SQLite カタログ + Parquet）は ./lake にあり、
# ホストと「同じ絶対パス」で Lightdash コンテナにマウントする。
# LAKE_DIR は Makefile が自動で設定する（手動なら export LAKE_DIR=$PWD/lake）。
services:
  lightdash-db:
    image: pgvector/pgvector:pg15
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${PGPASSWORD}
      POSTGRES_DB: postgres
    volumes:
      - lightdash-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 10

  minio:
    image: coollabsio/minio:latest
    ports:
      - "127.0.0.1:9000:9000"
      - "127.0.0.1:9001:9001"   # MinIO console（任意）
    volumes:
      - ./docker/init-minio.sh:/init-minio.sh:ro
      - minio-data:/data
    entrypoint: ["/bin/sh", "/init-minio.sh"]
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
      MINIO_DEFAULT_BUCKETS: default

  lightdash:
    image: lightdash/lightdash:latest
    platform: linux/amd64     # Apple Silicon では Rosetta 経由で動く
    depends_on:
      lightdash-db:
        condition: service_healthy
      minio:
        condition: service_started
    volumes:
      # ホストと同じ絶対パスでマウントするのがポイント
      # （dbt の profiles.yml に書いたパスを Lightdash もそのまま使えるようにする）
      - ${LAKE_DIR:?LAKE_DIR is not set. Run via make, or export LAKE_DIR=$PWD/lake}:${LAKE_DIR}
    environment:
      PGHOST: lightdash-db
      PGPORT: 5432
      PGUSER: postgres
      PGPASSWORD: ${PGPASSWORD}
      PGDATABASE: postgres
      LIGHTDASH_SECRET: ${LIGHTDASH_SECRET}
      LIGHTDASH_MIGRATION_EXECUTION_MODE: compose
      SECURE_COOKIES: "false"
      TRUST_PROXY: "false"
      SITE_URL: http://localhost:8080
      PORT: 8080
      S3_ENDPOINT: http://minio:9000
      S3_REGION: us-east-1
      S3_BUCKET: default
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
      S3_FORCE_PATH_STYLE: "true"
      SCHEDULER_ENABLED: "true"
    ports:
      - "127.0.0.1:8080:8080"

volumes:
  lightdash-db-data:
  minio-data:
EOF

cat > docker/init-minio.sh <<'EOF'
#!/bin/sh
# MinIO を起動し、Lightdash 用のバケットを作成する
# （lightdash/lightdash リポジトリの docker/init-minio.sh を簡略化したもの）
set -e

minio server /data --console-address ":9001" &

until mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  sleep 1
done

IFS=','
for bucket in $MINIO_DEFAULT_BUCKETS; do
  [ -n "$bucket" ] || continue
  mc mb -p "local/$bucket" >/dev/null 2>&1 || echo "bucket '$bucket' already exists"
  # 結果ファイルは 1 日で自動削除
  mc ilm rule add --expire-days 1 "local/$bucket" >/dev/null 2>&1 || true
done

echo "MinIO ready"
wait
EOF
```

```bash
cat > .env <<EOF
PGPASSWORD=lightdash_password
LIGHTDASH_SECRET=$(openssl rand -hex 32)
EOF

docker compose up -d
docker compose logs -f lightdash     # 起動ログが落ち着いたら Ctrl-C
```

`docker-compose.yml` は、`./lake` を **`$LAKE_DIR` と同じ絶対パス**でコンテナにマウントします。
`LAKE_DIR` が未設定だとエラーで止まるので、その場合は Step 2 の `export` を再実行してください。

ブラウザで http://localhost:8080 を開き、管理者ユーザーを作成します。

---

## Step 10. Lightdash にデプロイ

```bash
cd dbt
lightdash login http://localhost:8080
uv run lightdash deploy --project-dir . --profiles-dir . -s tag:bi --create "Shop Analytics"
```

CLI は `profiles.yml` の DuckLake 設定をそのまま Lightdash の接続設定にします。

| 項目 | 値 |
| --- | --- |
| 接続タイプ | DuckLake |
| カタログ | SQLite: `$LAKE_DIR/catalog.sqlite` |
| データ | ローカル: `$LAKE_DIR/data/` |

コンテナにも同じパスでマウントしているので、追加の設定は不要です。

**確認**: Explore の「注文」で `ordered_at` の Month と `売上`・`注文完了率` を選びます。Step 7 の `mf query` と同じ数字になれば成功です。
さらに `顧客 > region` を足すと、`meta.joins` による join が使われます。

---

## Step 11. 変更サイクルを体験する

`dbt/models/semantic/metrics.yml` にメトリクスを追加してみましょう。例として、`order_count` の後ろあたりに次を足します。

```yaml
  - name: first_orders
    label: 初回注文数
    type: simple
    type_params:
      measure: order_count
    filter: |
      {{ Dimension('order__is_first_order') }} = true
```

追加したら、次の順に反映します。

```bash
uv run dbt parse
uv run mf validate-configs
uv run mf query --metrics first_orders,order_count --group-by metric_time__quarter --order metric_time__quarter
uv run lightdash deploy --project-dir . --profiles-dir . -s tag:bi      # 2回目以降は --create なし
```

deploy のログが `Translated 17 MetricFlow metric(s)` に増えていれば、Lightdash にも反映されています。
（同じ order モデル上の Dimension フィルタなので、Lightdash でも変換されます。）

本番プロジェクトを触らずに確認したいときは、`uv run lightdash preview --project-dir . --profiles-dir . -s tag:bi` を使います。

---

## 片付け

```bash
cd ..                      # プロジェクトルート
docker compose down -v     # Lightdash のメタデータと MinIO を削除
rm -rf lake dbt/target dbt/logs
```

## つまずいたとき

| 症状 | 対処 |
| --- | --- |
| `Env var required but not provided: 'LAKE_DIR'` | Step 2 の `export` を再実行する（絶対パスで） |
| `dbt debug` で拡張機能のダウンロードに失敗する | ネットワークやプロキシを確認する。DuckDB は `extensions.duckdb.org` から取得する |
| `mf` を実行中に別の `dbt` が動いていてエラー | 片方ずつ実行する（profiles は `:memory:` なので通常は衝突しない） |
| `docker compose up` で `LAKE_DIR is not set` | `export LAKE_DIR=$PWD/lake` をプロジェクトルートで実行してから起動する |
| Lightdash でテーブルが読めない | `chmod -R a+rX lake` を実行し、コンテナから読めるようにする |
| Lightdash CLI が dbt のバージョン非対応と言う | `uv add "dbt-core~=1.10.0"` で下げる |
