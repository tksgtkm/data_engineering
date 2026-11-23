import argparse
import csv
import json

from datasets import load_dataset

from .common import DATA, write_jsonl


REPO = "mteb/JaGovFaqsRetrieval"


def pick_id(row, keys):
    for key in keys:
        if row.get(key) is not None:
            return str(row[key])
    raise KeyError(f"No ID field among {keys}. Found {list(row)}")


def build_subset(corpus, queries, judgments, max_docs, max_queries, max_chars):
    docs = {}
    for row in corpus:
        did = pick_id(row, ["_id", "id", "doc_id"])
        title = str(row.get("title") or "").strip()
        body = str(row.get("text") or "").strip()
        text = (title + "\n" + body).strip()[:max_chars]
        if text:
            docs[did] = {"doc_id": did, "text": text}

    qs = {}
    for row in queries:
        qid = pick_id(row, ["_id", "id", "query_id"])
        text = str(row.get("text") or row.get("query") or "").strip()[:max_chars]
        if text:
            qs[qid] = {"query_id": qid, "text": text}

    positive = {}
    for row in judgments:
        qid = pick_id(row, ["query-id", "query_id", "qid"])
        did = pick_id(row, ["corpus-id", "corpus_id", "doc_id"])
        score = float(row.get("score", row.get("relevance", 0)))
        if score > 0 and qid in qs and did in docs:
            positive.setdefault(qid, {})[did] = max(score, positive.get(qid, {}).get(did, 0))

    eligible = sorted(positive)
    if max_queries > 0:
        eligible = eligible[:max_queries]
    mandatory = {did for qid in eligible for did in positive[qid]}
    if max_docs > 0 and len(mandatory) > max_docs:
        raise ValueError(
            f"{len(mandatory)} positives exceed --max-docs={max_docs}. "
            "Increase max-docs or reduce max-queries."
        )
    selected = set(mandatory)
    for did in sorted(docs):
        if max_docs > 0 and len(selected) >= max_docs:
            break
        selected.add(did)
    selected_queries = [qs[qid] for qid in eligible]
    selected_qrels = [
        {"query_id": qid, "doc_id": did, "relevance": score}
        for qid in eligible for did, score in sorted(positive[qid].items())
    ]
    return [docs[did] for did in sorted(selected)], selected_queries, selected_qrels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-docs", type=int, default=1000, help="0 = full corpus")
    parser.add_argument("--max-queries", type=int, default=100, help="0 = all evaluable queries")
    parser.add_argument("--max-chars", type=int, default=400, help="Same text slice in both search engines")
    args = parser.parse_args()
    print("Downloading JaGovFaqs configs: corpus, queries, qrels/test ...")
    corpus = load_dataset(REPO, "corpus", split="test")
    queries = load_dataset(REPO, "queries", split="test")
    judgments = load_dataset(REPO, "qrels", split="test")
    docs, qs, qrels = build_subset(corpus, queries, judgments, args.max_docs, args.max_queries, args.max_chars)
    if not docs or not qs or not qrels:
        raise RuntimeError("Empty dataset subset. Verify data configurations and qrel field names.")
    DATA.mkdir(parents=True, exist_ok=True)
    write_jsonl(DATA / "documents.jsonl", docs)
    write_jsonl(DATA / "queries.jsonl", qs)
    with (DATA / "qrels.tsv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["query_id", "doc_id", "relevance"], delimiter="\t")
        writer.writeheader()
        writer.writerows(qrels)
    (DATA / "dataset_metadata.json").write_text(
        json.dumps({"repo": REPO, "max_chars": args.max_chars, "documents": len(docs),
                    "queries": len(qs), "qrels": len(qrels)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Prepared documents={len(docs)} queries={len(qs)} positive_judgments={len(qrels)}")


if __name__ == "__main__":
    main()
