"""ZakkaMall の OLTP ソースデータを DuckDB ファイルに作成する。

Docker 版で PostgreSQL の初期化スクリプト（docker-entrypoint-initdb.d）が
担っていた処理の置き換え。../init-scripts/*.sql をファイル名順に実行する。

使い方（dbt_project ディレクトリで実行）:
    uv run python init_db.py           # dbt_demo.duckdb を作り直す（既存ファイルは削除）
    uv run python init_db.py --db x.duckdb
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
INIT_SCRIPT_DIR = HERE / "init-scripts"
DEFAULT_DB = HERE / "dbt_demo.duckdb"

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    db_path: Path = args.db.resolve()
    for p in (db_path, db_path.with_name(db_path.name + ".wal")):
        if p.exists():
            p.unlink()
            print(f"removed {p}")

    scripts = sorted(INIT_SCRIPT_DIR.glob("*.sql"))
    if not scripts:
        raise SystemExit(f"SQL file not found: {INIT_SCRIPT_DIR}")

    with duckdb.connect(str(db_path)) as con:
        for script in scripts:
            print(f"running {script.name} ...")
            con.execute(script.read_text(encoding="utf-8"))

        print("\nテーブル件数:")
        rows = con.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'zakka_mall'
            ORDER BY table_name
            """
        ).fetchall()
        for (table,) in rows:
            (count,) = con.execute(f'SELECT COUNT(*) FROM zakka_mall."{table}"').fetchone()
            print(f"  {table:<18} {count:>5}")

    print(f"\ncreated {db_path}")

if __name__ == "__main__":
    main()