#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 実験日時
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"

read -r DOCS QUERIES < <(
  python -c '
import json
with open("data/dataset_metadata.json") as f:
    d = json.load(f)
print(d["documents"], d["queries"])
'
)

DATASET_NAME="jagovfaqs_${DOCS}docs_${QUERIES}q"

for ef in 40 100 200; do
  OUT_DIR="results/runs/jagovfaqs_5k_500q/${RUN_ID}/ef${ef}"
  mkdir -p "$OUT_DIR"

  echo "=== ef_search=${ef} ==="

  python -m src.evaluate \
    --k 10 \
    --hnsw-ef-search "$ef" \
    | tee "$OUT_DIR/evaluate.log"

  cp results/summary.csv \
     results/per_query.csv \
     results/run_metadata.json \
     "$OUT_DIR/"

  cp data/dataset_metadata.json "$OUT_DIR/"
done