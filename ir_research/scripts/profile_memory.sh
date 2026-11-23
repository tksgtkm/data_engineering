#!/usr/bin/env bash
set -euo pipefail

# Run a SECOND, instrumented evaluation so monitoring does not alter archived
# uninstrumented latency measurements. Docker stats samples are approximations.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="${1:?Usage: profile_memory.sh <output_dir> [ef_search]}"
EF="${2:-200}"
mkdir -p "$OUT"
PG_ID="$(docker compose ps -q postgres)"
OS_ID="$(docker compose ps -q opensearch)"
if [[ -z "$PG_ID" || -z "$OS_ID" ]]; then
  echo 'ERROR: postgres/opensearch containers must be running' >&2; exit 1
fi

sampler_pid=''
cleanup() {
  if [[ -n "$sampler_pid" ]]; then
    kill "$sampler_pid" 2>/dev/null || true
    wait "$sampler_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

(
  while true; do
    timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    while IFS= read -r stats_json; do
      [[ -z "$stats_json" ]] && continue
      printf '{"timestamp_utc":"%s","stats":%s}\n' "$timestamp" "$stats_json"
    done < <(docker stats --no-stream --format '{{json .}}' "$PG_ID" "$OS_ID")
    sleep 2
  done
) > "$OUT/memory_samples.jsonl" &
sampler_pid=$!

python -m src.evaluate --k 10 --hnsw-ef-search "$EF" > "$OUT/memory_profile_evaluate.log"
cp results/summary.csv "$OUT/memory_profile_summary.csv"
cleanup
sampler_pid=''

python - "$OUT/memory_samples.jsonl" "$OUT/memory_peaks.csv" <<'PY'
import csv, json, re, sys
from collections import defaultdict

units = {"B": 1, "kB": 1000, "MB": 1000**2, "GB": 1000**3,
         "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}
def parse_usage(value):
    raw = value.split('/')[0].strip()
    m = re.fullmatch(r'([0-9.]+)\s*([A-Za-z]+)', raw)
    if m is None or m.group(2) not in units:
        raise ValueError(f'Unknown Docker memory format: {value!r}')
    return float(m.group(1))*units[m.group(2)]

by_name=defaultdict(list)
for line in open(sys.argv[1], encoding='utf-8'):
    if line.strip():
        entry=json.loads(line)
        s=entry['stats']
        name=s.get('Name') or s.get('Container') or s.get('ID') or 'unknown'
        by_name[name].append(parse_usage(s['MemUsage']))
with open(sys.argv[2], 'w', encoding='utf-8', newline='') as f:
    out=csv.DictWriter(f, fieldnames=['container','sample_count','max_sampled_mib','min_sampled_mib'])
    out.writeheader()
    for name, vals in sorted(by_name.items()):
        out.writerow({'container':name, 'sample_count':len(vals),
                      'max_sampled_mib':round(max(vals)/1024**2,2),
                      'min_sampled_mib':round(min(vals)/1024**2,2)})
print('Sampled memory peaks:', sys.argv[2])
PY
