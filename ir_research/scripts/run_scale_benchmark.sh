#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# This script assumes the full-corpus embedding cache was generated first.
# It re-creates BOTH search indexes at each document-count condition.
SIZES=(1000 5000 10000 22794)
FIXED_QUERIES=500
EF_SEARCH=200
MAX_CHARS=400
STAMP="$(date -u +%Y%m%dT%H%M%S%NZ)"
BATCH="results/scale_runs/${STAMP}"
mkdir -p "$BATCH"

ref_query_hash=''
ref_qrels_hash=''

for docs in "${SIZES[@]}"; do
  echo "=== documents=${docs}; queries=${FIXED_QUERIES}; ef=${EF_SEARCH} ==="
  python -m src.prepare \
    --max-docs "$docs" \
    --max-queries "$FIXED_QUERIES" \
    --max-chars "$MAX_CHARS"

  query_hash="$(sha256sum data/queries.jsonl | cut -d' ' -f1)"
  qrels_hash="$(sha256sum data/qrels.tsv | cut -d' ' -f1)"
  if [[ -n "$ref_query_hash" && ( "$ref_query_hash" != "$query_hash" || "$ref_qrels_hash" != "$qrels_hash" ) ]]; then
    echo 'ERROR: queries/qrels changed across dataset sizes. Stop and investigate.' >&2
    exit 1
  fi
  ref_query_hash="$query_hash"
  ref_qrels_hash="$qrels_hash"

  # Runs should be no-op cache hits after run_full_corpus.sh (same model/text settings).
  python -m src.embed --batch-size 16
  python -m src.ingest

  # OpenSearchの投入データを検索可能にする
curl -fsS -X POST \
  http://127.0.0.1:9200/jagovfaqs/_refresh > /dev/null

# インデックスをフラッシュ
curl -fsS -X POST \
  http://127.0.0.1:9200/jagovfaqs/_flush > /dev/null

# 文書数が一致しているか確認
EXPECTED=$(python -c '
import json
with open("data/dataset_metadata.json") as f:
    print(json.load(f)["documents"])
')

ACTUAL=$(curl -fsS \
  http://127.0.0.1:9200/jagovfaqs/_count \
  | python -c 'import json,sys; print(json.load(sys.stdin)["count"])')

if [ "$EXPECTED" -ne "$ACTUAL" ]; then
  echo "ERROR: expected=$EXPECTED actual=$ACTUAL" >&2
  exit 1
fi

echo "OpenSearch documents verified: $ACTUAL"

  DATASET="jagovfaqs_${docs}docs_${FIXED_QUERIES}q"
  OUT="${BATCH}/${DATASET}/trial01/ef${EF_SEARCH}"
  mkdir -p "$OUT"
  cp data/dataset_metadata.json "$OUT/"
  cp results/ingest_timings.json "$OUT/"
  sha256sum data/documents.jsonl data/queries.jsonl data/qrels.tsv > "$OUT/input_sha256.txt"

  python -m src.resource_metrics --output "$OUT/resources_after_ingest.json" > /dev/null

  # Idle snapshot: NOT the peak during search. On-demand memory sampling is documented in README.
  PG_ID="$(docker compose ps -q postgres)"
  OS_ID="$(docker compose ps -q opensearch)"
  docker stats --no-stream --format '{{json .}}' "$PG_ID" "$OS_ID" > "$OUT/docker_memory_idle.jsonl"

  python -m src.evaluate --k 10 --hnsw-ef-search "$EF_SEARCH" | tee "$OUT/evaluate.log"
  cp results/summary.csv results/per_query.csv results/run_metadata.json "$OUT/"
  docker stats --no-stream --format '{{json .}}' "$PG_ID" "$OS_ID" > "$OUT/docker_memory_after.jsonl"
  if [[ "${PROFILE_MEMORY:-0}" == '1' ]]; then
    ./scripts/profile_memory.sh "$OUT" "$EF_SEARCH"
  fi
  python -m src.analyze --run-dir "${BATCH}/${DATASET}/trial01" \
    --output-dir "${BATCH}/${DATASET}/analysis" > "$OUT/analyze.log"
done

printf 'Fixed queries.sha256=%s\nFixed qrels.sha256=%s\n' \
  "$ref_query_hash" "$ref_qrels_hash" > "${BATCH}/fixed_query_hashes.txt"
echo "Scale results: ${BATCH}"
