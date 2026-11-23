import argparse
import json
import time

import boto3
from botocore.config import Config

from .common import DATA, env, read_jsonl

MODEL = env("BEDROCK_MODEL_ID", "cohere.embed-multilingual-v3")
REGION = env("AWS_REGION", "ap-northeast-1")
DIM = 1024

def call_embed(client, texts, input_type):
    req = {"texts": texts, "input_type": input_type, "truncate": "END"}
    resp = client.invoke_model(
        modelId=MODEL,
        body=json.dumps(req, ensure_ascii=False),
        contentType="application/json",
        accept="application/json"
    )
    parsed = json.loads(resp["body"].read())
    vectors = parsed["embeddings"]
    if len(vectors) != len(texts) or any(len(v) != DIM for v in vectors):
        raise RuntimeError("Unexpected embedding shape. Expected 1024 floats per text.")
    return vectors

def build_vectors(client, source, target, key, input_type, batch_size):
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = {r[key] for r in read_jsonl(target)} if target.exists() else set()
    rows = [r for r in read_jsonl(source) if r[key] not in existing]
    print(f"{input_type}: cached={len(existing)}, remaining={len(rows)}")
    with target.open("a", encoding="utf-8") as file:
        for idx in range(0, len(rows), batch_size):
            chunk = rows[idx:idx + batch_size]
            vectors = call_embed(client, [r["text"] for r in chunk], input_type)
            for row, vec in zip(chunk, vectors):
                file.write(json.dumps({key: row[key], "embedding": vec}, ensure_ascii=False) + "\n")
            file.flush()
            print(f"  {min(idx + batch_size, len(rows))}/{len(rows)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 96:
        parser.error("--batch-size must be between 1 and 96")
    client = boto3.client(
        "bedrock-runtime",
        region_name=REGION,
        config=Config(retries={"max_attempts": 10, "mode": "standard"})
    )
    build_vectors(
        client,
        DATA / "documents.jsonl",
        DATA / "doc_vectors.jsonl",
        "doc_id",
        "search_document",
        args.batch_size
    )
    build_vectors(
        client,
        DATA / "queries.jsonl",
        DATA / "query_vectors.jsonl",
        "query_id",
        "search_query",
        args.batch_size
    )
    print("Embedding cache complete. Do not regenerate unless the model/text changes.")

if __name__ == "__main__":
    main()