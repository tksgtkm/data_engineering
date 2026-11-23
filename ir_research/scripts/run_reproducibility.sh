#!/usr/bin/env bash
set -euo pipefail

# ir_research: repeat each HNSW search condition five times.
# The output layout is compatible with src.analyze --all-runs.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TRIALS="${TRIALS:-5}"
if ! [[ "$TRIALS" =~ ^[1-9][0-9]*$ ]]; then
  echo 'TRIALS must be a positive integer' >&2; exit 2
fi
[[ -f data/dataset_metadata.json ]] || { echo 'Run src.prepare first' >&2; exit 1; }

DATASET="$(python - <<'PY'
import json
from pathlib import Path
m=json.loads(Path('data/dataset_metadata.json').read_text())
print(f"jagovfaqs_{m['documents']}docs_{m['queries']}q")
PY
)"

# Separate this batch from earlier exploratory runs; each batch is independently analyzable.
STAMP="$(date -u +%Y%m%dT%H%M%S%NZ)"
BATCH_ROOT="results/repro_runs/${STAMP}"
OUT_BASE="${BATCH_ROOT}/${DATASET}"
mkdir -p "$OUT_BASE"
sha256sum data/documents.jsonl data/queries.jsonl data/qrels.tsv data/dataset_metadata.json > "${BATCH_ROOT}/input_sha256.txt"

echo "Data: ${DATASET}"
echo "Trials: ${TRIALS}"
echo "Output: ${BATCH_ROOT}"

for (( trial=1; trial<=TRIALS; trial++ )); do
  printf -v trial_name 'trial%02d' "$trial"
  case $(( (trial-1) % 3 )) in
    0) order=(40 100 200);;
    1) order=(100 200 40);;
    2) order=(200 40 100);;
  esac
  echo "=== ${trial_name}: ef_search ${order[*]} ==="
  for ef in "${order[@]}"; do
    OUT="${OUT_BASE}/${trial_name}/ef${ef}"
    mkdir -p "$OUT"
    python -m src.evaluate --k 10 --hnsw-ef-search "$ef" | tee "${OUT}/evaluate.log"
    cp results/summary.csv results/per_query.csv results/run_metadata.json "$OUT/"
    cp data/dataset_metadata.json "$OUT/"
  done
done

python -m src.analyze \
  --runs-dir "${BATCH_ROOT}" \
  --dataset "$DATASET" \
  --all-runs \
  --output-dir "${BATCH_ROOT}/analysis"

echo "Trial-level report: ${BATCH_ROOT}/analysis/trial_summary.csv"
echo "Summary report: ${BATCH_ROOT}/analysis/report.md"
