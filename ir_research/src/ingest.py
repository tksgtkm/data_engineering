import time

import numpy as np
import psycopg
from opensearchpy import OpenSearch, helpers
from pgvector.psycopg import register_vector

from .common import DATA, RESULTS, env, read_jsonl

PG_DSN = env("PG_DSN", "postgresql://benchmark:local_dev_only_change_me@127.0.0.1:5432/searchbench")
OS_URL = env("OPENSEARCH_URL", "http://127.0.0.1:9200")
INDEX = env("OPENSEARCH_INDEX", "jagovfaqs")


def main():
    docs = list(read_jsonl(DATA / "documents.jsonl"))
    vecs = {r["doc_id"]: r["embedding"] for r in read_jsonl(DATA / "doc_vectors.jsonl")}
    missing = [
        d["doc_id"]
        for d in docs
        if d["doc_id"] not in vecs
    ]

    if missing:
        raise RuntimeError(
            f"Incomplete doc embeddings: "
            f"{len(missing)} missing. "
            f"Examples: {missing[:5]}"
        )

    print(
        f"Documents={len(docs)}, "
        f"Cached embeddings={len(vecs)}, "
        f"Missing={len(missing)}"
    )

    RESULTS.mkdir(exist_ok=True)
    timings = {}

    with psycopg.connect(PG_DSN) as pg:
        pg.execute("CREATE EXTENSION IF NOT EXISTS vector")
        pg.execute("CREATE TABLE IF NOT EXISTS documents (doc_id TEXT PRIMARY KEY, body TEXT NOT NULL, embedding VECTOR(1024) NOT NULL)")
        pg.execute("DROP INDEX IF EXISTS documents_embedding_hnsw")
        pg.execute("TRUNCATE TABLE documents")
        register_vector(pg)
        start = time.perf_counter()
        with pg.cursor() as cur:
            for doc in docs:
                cur.execute("INSERT INTO documents(doc_id,body,embedding) VALUES (%s,%s,%s)",
                            (doc["doc_id"], doc["text"], np.asarray(vecs[doc["doc_id"]], dtype=np.float32)))
        pg.commit()
        timings["pg_insert_seconds"] = time.perf_counter() - start
        start = time.perf_counter()
        pg.execute("CREATE INDEX documents_embedding_hnsw ON documents USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")
        pg.commit()
        timings["pg_hnsw_build_seconds"] = time.perf_counter() - start
        pg.execute("ANALYZE documents")
        count = pg.execute("SELECT count(*) FROM documents").fetchone()[0]
        assert count == len(docs), "PostgreSQL document count mismatch"

    os_client = OpenSearch(hosts=[OS_URL], timeout=90, max_retries=3, retry_on_timeout=True)
    if os_client.indices.exists(index=INDEX):
        os_client.indices.delete(index=INDEX)
    start = time.perf_counter()
    os_client.indices.create(index=INDEX, body={
        "settings": {"number_of_shards": 1, "number_of_replicas": 0,
                     "refresh_interval": "-1",
                     "analysis": {"analyzer": {"ja_bm25": {"type": "custom", "tokenizer": "kuromoji_tokenizer",
                                                        "filter": ["kuromoji_baseform", "cjk_width", "lowercase"]}}}},
        "mappings": {"properties": {"doc_id": {"type": "keyword"},
                                    "text": {"type": "text", "analyzer": "ja_bm25", "similarity": "BM25"}}}
    })
    actions = ({"_index": INDEX, "_id": d["doc_id"], "_source": d} for d in docs)
    success, _ = helpers.bulk(os_client, actions, chunk_size=250, request_timeout=90, stats_only=True)
    os_client.indices.put_settings(index=INDEX, body={"index": {"refresh_interval": "1s"}})
    os_client.indices.refresh(index=INDEX)
    timings["opensearch_build_seconds"] = time.perf_counter() - start
    os_count = os_client.count(index=INDEX)["count"]
    assert os_count == len(docs) and success == len(docs), "OpenSearch document count mismatch"
    (RESULTS / "ingest_timings.json").write_text(__import__("json").dumps(timings, indent=2) + "\n")
    print("Indexed documents:", len(docs), "timings:", timings)


if __name__ == "__main__":
    main()
