#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STAMP="$(date -u +%Y%m%dT%H%M%S%NZ)"
SNAPSHOT="results/snapshots/before_full_${STAMP}"
mkdir -p "$SNAPSHOT"
for f in documents.jsonl queries.jsonl qrels.tsv dataset_metadata.json; do
  [[ ! -f "data/$f" ]] || cp "data/$f" "$SNAPSHOT/"
done

echo '=== Prepare complete JaGovFaqs corpus and qrels ==='
echo 'WARNING: src.prepare replaces data/documents.jsonl, queries.jsonl, qrels.tsv and dataset_metadata.json.'
python -m src.prepare --max-docs 0 --max-queries 0 --max-chars 400

python - <<'PY'
import json
from pathlib import Path
m = json.loads(Path('data/dataset_metadata.json').read_text())
assert (m['documents'],m['queries']) == (22794,2048), f'Unexpected dataset cardinality: {m}'
print('Verified all documents and queries:', m)
PY

# This cache is valid only while embedding model, corpus text and input_type are unchanged.
# Existing document/query vectors are reused by ID; only missing IDs are embedded.
echo '=== Generate missing embeddings (AWS Bedrock: billable) ==='
python -m src.embed --batch-size 16

# src.ingest TRUNCATES the PostgreSQL documents table, rebuilds HNSW and
# DELETES/RECREATES the OpenSearch index. Archived results stay untouched.
echo '=== Rebuild both search indexes ==='
python -m src.ingest

mkdir -p "results/full_runs/${STAMP}"
python -m src.resource_metrics --output "results/full_runs/${STAMP}/resources_after_ingest.json"
cp results/ingest_timings.json "results/full_runs/${STAMP}/ingest_timings.json"

echo '=== Evaluate all 2048 queries for ef 40/100/200 ==='
./scripts/benchmark_hnsw.sh
python -m src.analyze --dataset jagovfaqs_22794docs_2048q

echo 'Full-corpus evaluation complete. See results/runs/jagovfaqs_22794docs_2048q/ and results/analysis/.'
