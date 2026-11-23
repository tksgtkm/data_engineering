from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = PROJECT_ROOT / "results" / "runs"
DEFAULT_ANALYSIS_DIR = PROJECT_ROOT / "results" / "analysis"
ENGINES = ("bm25", "pg_exact", "pg_hnsw")
METRICS = ("mean_recall", "mean_mrr", "mean_ndcg", "p50_ms", "p95_ms", "p99_ms", "sequential_qps_estimate")

def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"CSV contains noo data: {path}")
    return rows

def save_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def find_runs(runs_dir: Path, dataset: str | None) -> list[Path]:
    if not runs_dir.is_dir():
        raise ValueError(f"Run directory not found: {runs_dir}")
    candidates = []
    dataset_dirs = [runs_dir / dataset] if dataset else sorted(runs_dir.iterdir())
    for dataset_dir in dataset_dirs:
        if dataset_dir.is_dir():
            for run_dir in dataset_dir.iterdir():
                if run_dir.is_dir() and any(run_dir.glob("ef*/summary.csv")):
                    candidates.append(run_dir)
    return sorted(candidates, key=lambda p: (p.name, p.parent.name))


def docs_from_csv(value: str, k: int) -> list[str]:
    # evaluate.py stores document IDs joined with commas.
    # JaGovFaqs IDs do not contain commas.
    return [x.strip() for x in (value or "").split(",") if x.strip()][:k]


def per_query_index(rows: list[dict[str, str]], engine: str) -> dict[str, dict]:
    indexed = {}
    for row in rows:
        if row["engine"] != engine:
            continue
        qid = row["query_id"]
        if qid in indexed:
            raise ValueError(f"Duplicate query_id={qid!r} for engine={engine}")
        indexed[qid] = row
    if not indexed:
        raise ValueError(f"No per-query rows for engine={engine}")
    return indexed

def examine_condition(ef_dir: Path) -> tuple[list[dict], dict, list[dict], dict]:
    match = re.fullmatch(r"ef(\d+)", ef_dir.name)
    if match is None:
        raise ValueError(f"Expected ef<number> directory: {ef_dir}")
    ef = int(match.group(1))
    meta_path = ef_dir / "run_metadata.json"
    if not meta_path.is_file():
        raise ValueError(f"Metadata not found: {meta_path}")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    if int(metadata["hnsw_ef_search"]) != ef:
        raise ValueError(f"Directory {ef_dir.name} disagrees with run_metadata.json")

    summary_rows = read_csv(ef_dir / "summary.csv", {"engine", "queries", "k", *METRICS})
    summary = {r["engine"]: r for r in summary_rows}
    if any(name not in summary for name in ENGINES):
        raise ValueError(f"Missing search engine in {ef_dir}/summary.csv; expected {ENGINES}")
    k = int(summary["pg_exact"]["k"])
    if k <= 0 or int(metadata["k"]) != k:
        raise ValueError(f"Inconsistent k in {ef_dir}")
    n_queries = int(summary["pg_exact"]["queries"])
    for name in ENGINES:
        if int(summary[name]["queries"]) != n_queries or int(summary[name]["k"]) != k:
            raise ValueError(f"Inconsistent query count or k across engines in {ef_dir}")

    per_query = read_csv(
        ef_dir / "per_query.csv",
        {"query_id", "engine", "recall", "mrr", "ndcg", "latency_ms", "top_doc_ids"},
    )
    exact = per_query_index(per_query, "pg_exact")
    hnsw = per_query_index(per_query, "pg_hnsw")
    bm25 = per_query_index(per_query, "bm25")
    if set(exact) != set(hnsw) or set(exact) != set(bm25) or len(exact) != n_queries:
        raise ValueError(f"Mismatched query IDs/count across engines in {ef_dir}")

    run_fields = {"dataset": ef_dir.parent.parent.name, "run_id": ef_dir.parent.name,
                  "ef_search": ef, "k": k, "queries": n_queries}
    metric_rows = [
        {**run_fields, "engine": name,
         **{key: float(summary[name][key]) for key in METRICS}}
        for name in ENGINES
    ]

    differences = []
    for qid in sorted(exact):
        a, b = exact[qid], hnsw[qid]
        exact_ids = docs_from_csv(a["top_doc_ids"], k)
        hnsw_ids = docs_from_csv(b["top_doc_ids"], k)
        if not exact_ids:
            raise ValueError(f"Exact Search returned no documents for query {qid!r}")
        n_common = len(set(exact_ids) & set(hnsw_ids))
        exact_recall, hnsw_recall = float(a["recall"]), float(b["recall"])
        differences.append({
            **run_fields, "query_id": qid,
            # ANN Recall: reproduction of the exact nearest-neighbor Top-k set.
            "ann_recall_at_k": n_common / len(set(exact_ids)),
            "common_docs": n_common,
            "same_order": int(exact_ids == hnsw_ids),
            "same_top1": int(bool(hnsw_ids) and exact_ids[0] == hnsw_ids[0]),
            "exact_top_doc_ids": ",".join(exact_ids),
            "hnsw_top_doc_ids": ",".join(hnsw_ids),
            "exact_recall": exact_recall,
            "hnsw_recall": hnsw_recall,
            "recall_delta_hnsw_minus_exact": hnsw_recall - exact_recall,
            "exact_latency_ms": float(a["latency_ms"]),
            "hnsw_latency_ms": float(b["latency_ms"]),
        })

    overlaps = {
        **run_fields,
        "ann_recall_at_k": statistics.mean(r["ann_recall_at_k"] for r in differences),
        "same_order_rate": statistics.mean(r["same_order"] for r in differences),
        "same_top1_rate": statistics.mean(r["same_top1"] for r in differences),
        "exact_better_queries": sum(r["recall_delta_hnsw_minus_exact"] < -1e-12 for r in differences),
        "hnsw_better_queries": sum(r["recall_delta_hnsw_minus_exact"] > 1e-12 for r in differences),
        "same_recall_queries": sum(abs(r["recall_delta_hnsw_minus_exact"]) <= 1e-12 for r in differences),
        "pg_exact_mean_recall": float(summary["pg_exact"]["mean_recall"]),
        "pg_hnsw_mean_recall": float(summary["pg_hnsw"]["mean_recall"]),
        "pg_hnsw_p50_ms": float(summary["pg_hnsw"]["p50_ms"]),
        "pg_hnsw_p95_ms": float(summary["pg_hnsw"]["p95_ms"]),
    }
    return metric_rows, overlaps, differences, metadata
     
def aggregate_trials(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["ef_search"], row["k"], row["engine"])].append(row)
    output = []
    for (dataset, ef, k, engine), samples in sorted(grouped.items()):
        record = {"dataset": dataset, "ef_search": ef, "k": k,
                  "engine": engine, "trials": len(samples)}
        for metric in METRICS:
            vals = [row[metric] for row in samples]
            record[f"{metric}_median"] = statistics.median(vals)
            record[f"{metric}_min"] = min(vals)
            record[f"{metric}_max"] = max(vals)
        output.append(record)
    return output


def report_markdown(metric_rows: list[dict], overlap_rows: list[dict], trials: list[dict], warnings: list[str]) -> str:
    lines = ["# ir_research 検索ベンチマーク分析", "",
             "## 検索精度・応答時間", "",
             "| run | ef_search | engine | Recall@K | nDCG@K | P50 (ms) | P95 (ms) |",
             "|---|---:|---|---:|---:|---:|---:|"]
    for r in sorted(metric_rows, key=lambda x: (x["run_id"], x["ef_search"], ENGINES.index(x["engine"]))):
        lines.append(f"| {r['run_id']} | {r['ef_search']} | {r['engine']} | "
                     f"{r['mean_recall']:.4f} | {r['mean_ndcg']:.4f} | {r['p50_ms']:.3f} | {r['p95_ms']:.3f} |")
    lines.extend(["", "## Exact Searchに対するHNSWの再現率", "",
                  "| run | ef_search | ANN Recall@K | Top 1一致率 | 順位まで完全一致率 | Exact優位クエリ | HNSW優位クエリ |",
                  "|---|---:|---:|---:|---:|---:|---:|"])
    for r in sorted(overlap_rows, key=lambda x: (x["run_id"], x["ef_search"])):
        lines.append(f"| {r['run_id']} | {r['ef_search']} | {r['ann_recall_at_k']:.4f} | "
                     f"{r['same_top1_rate']:.4f} | {r['same_order_rate']:.4f} | "
                     f"{r['exact_better_queries']} | {r['hnsw_better_queries']} |")
    if trials:
        lines.extend(["", "## 複数回測定：中央値・範囲", "",
                      "| ef_search | engine | 試行数 | P50 中央値 [最小, 最大] ms | P95 中央値 [最小, 最大] ms |",
                      "|---:|---|---:|---|---|"])
        for r in trials:
            lines.append(f"| {r['ef_search']} | {r['engine']} | {r['trials']} | "
                         f"{r['p50_ms_median']:.3f} [{r['p50_ms_min']:.3f}, {r['p50_ms_max']:.3f}] | "
                         f"{r['p95_ms_median']:.3f} [{r['p95_ms_min']:.3f}, {r['p95_ms_max']:.3f}] |")
    lines.extend(["", "## 注意事項", "",
                  "- ANN Recall@K は、pg_exact のTop Kを正解集合とした近似近傍の再現率です。Qrelsに対するRecall@Kとは異なります。",
                  "- nDCG/MRR/Recallなどの値が一致しても、Top K文書が同じとは限りません。",
                  "- レイテンシはEmbedding生成時間を含まない逐次計測です。QPSは並列負荷時の実測スループットではありません。",
                  "- 各efの実行順、OS負荷、キャッシュ状態が異なると、速度結果にばらつきが出ます。",
                  "- 文書数とクエリ集合を同時に変えた実験の差は、純粋なスケーラビリティ効果ではありません。"])
    if warnings:
        lines.append("")
        lines.append("## 互換性に関する警告")
        lines.append("")
        lines.extend(f"- {w}" for w in warnings)
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description="Analyze archived BM25/pgvector benchmarks without accessing AWS.")
    p.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR,
                   help="Directory containing <dataset>/<run_id>/ef*/")
    p.add_argument("--run-dir", type=Path, help="Analyze a specific run directory containing ef*/")
    p.add_argument("--dataset", help="Dataset directory name, e.g. jagovfaqs_5000docs_500q")
    p.add_argument("--all-runs", action="store_true", help="Aggregate every run for one dataset")
    p.add_argument("--output-dir", type=Path, help="Output directory (defaults under results/analysis)")
    args = p.parse_args()
    if args.all_runs and args.run_dir:
        p.error("--all-runs and --run-dir cannot be combined")
    if args.all_runs and not args.dataset:
        p.error("--all-runs requires --dataset to avoid mixing dataset scales")

    try:
        if args.run_dir:
            runs = [args.run_dir.expanduser().resolve()]
            if not any(runs[0].glob("ef*/summary.csv")):
                raise ValueError(f"No ef*/summary.csv found under {runs[0]}")
        else:
            candidates = find_runs(args.runs_dir.expanduser().resolve(), args.dataset)
            if not candidates:
                raise ValueError("No archived benchmark runs found. Run scripts/benchmark_hnsw.sh first.")
            runs = candidates if args.all_runs else [candidates[-1]]

        metrics, overlaps, diffs, metadata_signatures, warnings = [], [], [], set(), []
        for run in runs:
            ef_dirs = sorted([d for d in run.iterdir() if re.fullmatch(r"ef\d+", d.name)],
                             key=lambda d: int(d.name[2:]))
            if not ef_dirs:
                raise ValueError(f"No ef* subdirectories in {run}")
            for ef_dir in ef_dirs:
                m, o, d, meta = examine_condition(ef_dir)
                metrics.extend(m)
                overlaps.append(o)
                diffs.extend(d)
                dataset_meta = meta.get("dataset", {})
                metadata_signatures.add((json.dumps(dataset_meta, sort_keys=True),
                                         str(meta.get("embedding_model")), int(meta["k"])))
        if len(metadata_signatures) > 1:
            warnings.append("異なるデータセット設定・Embeddingモデル・Kの結果が混在しています。集約値を比較する前に条件を揃えてください。")
        ds_names = {r["dataset"] for r in overlaps}
        if len(ds_names) != 1:
            warnings.append("複数のデータセットディレクトリが混在しています。")
        run_label = "all_runs" if args.all_runs else runs[0].name
        output_dir = args.output_dir or (DEFAULT_ANALYSIS_DIR / runs[0].parent.name / run_label)
        output_dir = output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        trial_rows = aggregate_trials(metrics) if args.all_runs else []
        save_csv(output_dir / "metrics.csv", metrics)
        save_csv(output_dir / "ann_overlap.csv", overlaps)
        save_csv(output_dir / "per_query_differences.csv", diffs)
        if trial_rows:
            save_csv(output_dir / "trial_summary.csv", trial_rows)
        (output_dir / "report.md").write_text(
            report_markdown(metrics, overlaps, trial_rows, warnings), encoding="utf-8"
        )

        print(f"Analyzed {len(runs)} run(s) and {len(overlaps)} ef_search condition(s)")
        print(" ef | ANN Recall@K | pg_exact Recall@K | pg_hnsw Recall@K | HNSW P50 (ms)")
        for r in sorted(overlaps, key=lambda x: (x["run_id"], x["ef_search"])):
            print(f"{r['ef_search']:>3} | {r['ann_recall_at_k']:.4f}       | "
                  f"{r['pg_exact_mean_recall']:.4f}            | "
                  f"{r['pg_hnsw_mean_recall']:.4f}           | {r['pg_hnsw_p50_ms']:.3f}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        print(f"Reports written to: {output_dir}")
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        p.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
