"""Capture comparable PostgreSQL/OpenSearch document + index storage statistics.

Usage: python -m src.resource_metrics --output results/.../resources.json
Container memory samples should be captured separately with docker stats.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from opensearchpy import OpenSearch

from .common import env

PG_DSN = env("PG_DSN", "postgresql://benchmark:local_dev_only_change_me@127.0.0.1:5432/searchbench")
OS_URL = env("OPENSEARCH_URL", "http://127.0.0.1:9200")
INDEX = env("OPENSEARCH_INDEX", "jagovfaqs")


def collect() -> dict:
    with psycopg.connect(PG_DSN) as pg:
        row = pg.execute("""
            SELECT count(*)::bigint,
                   pg_table_size('documents'::regclass)::bigint,
                   pg_indexes_size('documents'::regclass)::bigint,
                   pg_total_relation_size('documents'::regclass)::bigint,
                   pg_relation_size('documents_embedding_hnsw'::regclass)::bigint
            FROM documents
        """).fetchone()
        # The aggregate expressions above return a single row, even when table is empty.
        pg_stats = dict(zip(("document_count", "table_bytes", "all_indexes_bytes",
                             "table_plus_indexes_bytes", "hnsw_index_bytes"), row))
        pg_stats["index_details"] = [
            {"name": name, "size_bytes": size}
            for name, size in pg.execute("""
                SELECT indexrelid::regclass::text, pg_relation_size(indexrelid)::bigint
                FROM pg_index WHERE indrelid = 'documents'::regclass
                ORDER BY 1
            """).fetchall()
        ]

    os_client = OpenSearch(hosts=[OS_URL], timeout=60)
    stats = os_client.indices.stats(index=INDEX)
    idx = stats["indices"][INDEX]
    os_stats = {
        "index": INDEX,
        "document_count": os_client.count(index=INDEX)["count"],
        "primary_store_bytes": idx["primaries"]["store"]["size_in_bytes"],
        "total_store_bytes": idx["total"]["store"]["size_in_bytes"],
    }
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "postgresql": pg_stats,
        "opensearch": os_stats,
        "warning": "PostgreSQL HNSW index bytes and OpenSearch primary store bytes measure different components; compare each engine's size curve, not these values as equivalent index-only sizes.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = collect()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
