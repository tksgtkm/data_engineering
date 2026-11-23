import csv
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"

def read_jsonl(path):
    path = Path(path)
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)

def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

def load_qrels(path=None):
    path = Path(path or DATA / "qrels.tsv")
    qrels = {}
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file, delimiter="\t"):
            score = float(row["relevance"])
            if score > 0:
                qrels.setdefault(row["query_id"], {})[row["doc_id"]] = score
    return qrels

def env(key, default=None):
    return os.environ.get(key, default)