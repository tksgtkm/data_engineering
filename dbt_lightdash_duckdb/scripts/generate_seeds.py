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
