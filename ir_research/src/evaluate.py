import argparse
import datetime
import json
import platform
import sys
import csv
import math
import statistics
import time

import numpy as np
import psycopg
from opensearchpy import OpenSearch
from pgvector.psycopg import register_vector

from .common import DATA, RESULTS, env, load_qrels, read_jsonl

PG_DSN = env("PG_DSN", "postgresql://benchmark:local_dev_only_change_me@127.0.0.1:5432/searchbench")
OS_URL = env("OPENSEARCH_URL", "http://127.0.0.1:9200")
INDEX = env("OPENSEARCH_INDEX", "jagovfaqs")


def scores(top_doc_ids, relevant, k):
    hits = [float(relevant.get(docid, 0)) for docid in top_doc_ids[:k]]
    positives = [float(v) for v in relevant.values() if v > 0]
    if not positives:
        raise ValueError("A query has no qrels positive documents")
    recall = sum(v > 0 for v in hits) / len(positives)
    mrr = next((1.0 / (i+1) for i, v in enumerate(hits) if v > 0), 0.0)
    dcg = sum((2**v - 1) / math.log2(i+2) for i, v in enumerate(hits))
    ideal = sorted(positives, reverse=True)[:k]
    idcg = sum((2**v - 1) / math.log2(i+2) for i, v in enumerate(ideal))
    return {"recall": recall, "mrr": mrr, "ndcg": dcg/idcg}


def percentile(vals, p):
    vals = sorted(vals)
    x = (len(vals)-1)*p
    low = int(math.floor(x))
    high = int(math.ceil(x))
    return vals[low] + (vals[high]-vals[low])*(x-low)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--hnsw-ef-search", type=int, default=40)
    args = parser.parse_args()
    if args.k <= 0 or args.hnsw_ef_search <= 0:
        parser.error("k and hnsw-ef-search must be positive")
    queries = list(read_jsonl(DATA / "queries.jsonl"))
    qvec = {r["query_id"]: np.asarray(r["embedding"], dtype=np.float32)
            for r in read_jsonl(DATA / "query_vectors.jsonl")}
    qrels = load_qrels()
    valid = [q for q in queries if q["query_id"] in qrels and q["query_id"] in qvec]
    if not valid or len(valid) != len(queries):
        raise RuntimeError("Query embeddings or qrels incomplete")
    os_client = OpenSearch(hosts=[OS_URL], timeout=60)
    details, measurements = [], {name: [] for name in ["bm25", "pg_exact", "pg_hnsw"]}
    with psycopg.connect(PG_DSN) as pg:
        pg_version = pg.execute("SELECT version()").fetchone()[0]
        register_vector(pg)
        pg.execute("SELECT set_config('hnsw.ef_search', %s, false)", (str(args.hnsw_ef_search),))
        pg.commit()

        def retrieve(name, q):
            start = time.perf_counter()
            if name == "bm25":
                result = os_client.search(index=INDEX, body={"size": args.k,
                    "query": {"match": {"text": {"query": q["text"]}}}, "_source": False})
                doc_ids = [h["_id"] for h in result["hits"]["hits"]]
            else:
                # PG exact: disabling index scans suppresses HNSW; HNSW path allows index scans
                with pg.cursor() as cur:
                    if name == "pg_hnsw":
                        cur.execute("SET LOCAL enable_seqscan = off")
                    else:
                        cur.execute("SET LOCAL enable_indexscan = off")
                        cur.execute("SET LOCAL enable_bitmapscan = off")
                    cur.execute("SELECT doc_id FROM documents ORDER BY embedding <=> %s LIMIT %s",
                                (qvec[q["query_id"]], args.k))
                    doc_ids = [row[0] for row in cur.fetchall()]
                pg.commit()
            elapsed = (time.perf_counter() - start) * 1000
            return doc_ids, elapsed

        # Warmup is excluded from metrics and timings.
        for q in valid[:min(5, len(valid))]:
            for name in measurements:
                retrieve(name, q)
        for i, q in enumerate(valid, start=1):
            for name in measurements:
                doc_ids, elapsed = retrieve(name, q)
                measurements[name].append(elapsed)
                metric = scores(doc_ids, qrels[q["query_id"]], args.k)
                details.append({"query_id": q["query_id"], "engine": name,
                                "recall": metric["recall"], "mrr": metric["mrr"],
                                "ndcg": metric["ndcg"], "latency_ms": elapsed,
                                "top_doc_ids": ",".join(doc_ids)})
            if i % 20 == 0:
                print(f"Evaluated {i}/{len(valid)} queries")
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "per_query.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)
    report = []
    for name, times in measurements.items():
        group = [r for r in details if r["engine"] == name]
        report.append({"engine": name, "queries": len(group), "k": args.k,
            "mean_recall": statistics.mean(r["recall"] for r in group),
            "mean_mrr": statistics.mean(r["mrr"] for r in group),
            "mean_ndcg": statistics.mean(r["ndcg"] for r in group),
            "p50_ms": percentile(times, 0.50), "p95_ms": percentile(times, 0.95),
            "p99_ms": percentile(times, 0.99), "sequential_qps_estimate": len(times)/(sum(times)/1000)})
    with (RESULTS / "summary.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(report[0]))
        writer.writeheader()
        writer.writerows(report)
    metadata = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "postgres_version": pg_version,
        "opensearch_version": os_client.info()["version"]["number"],
        "embedding_model": env("BEDROCK_MODEL_ID", "cohere.embed-multilingual-v3"),
        "embedding_region": env("AWS_REGION", "ap-northeast-1"),
        "k": args.k,
        "hnsw_ef_search": args.hnsw_ef_search,
        "dataset": json.loads((DATA / "dataset_metadata.json").read_text(encoding="utf-8")),
        "note": "Sequential per-request retrieval latency without query embedding generation",
    }
    (RESULTS / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for r in report:
        print(r)
    print("See results/summary.csv and results/per_query.csv")


if __name__ == "__main__":
    main()
