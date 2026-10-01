"""
embedder.py — Q2 Knowledge Base: Chunking + Embedding + Indexing
Reads cleaned_records.jsonl, chunks records that are too large,
calls OpenAI Embeddings API, and upserts into ChromaDB.
"""

import json
import sys
import time
from pathlib import Path
from typing import Generator

import tiktoken
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
    CHUNK_SIZE_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    DATA_PROCESSED_DIR,
)
from q2_knowledge_base.vector_store import add_records, count_records, delete_collection

# ── Setup ─────────────────────────────────────────────────────────────────────
client = OpenAI(api_key=OPENAI_API_KEY)
tokenizer = tiktoken.get_encoding("cl100k_base")  # used by text-embedding-3-small

PROCESSED_JSONL = DATA_PROCESSED_DIR / "cleaned_records.jsonl"
EMBED_BATCH_SIZE = 50   # OpenAI allows up to 2048 inputs per call; 50 is safe


# ── Chunking ──────────────────────────────────────────────────────────────────

def count_tokens(text: str) -> int:
    return len(tokenizer.encode(text))


def chunk_text(text: str, max_tokens: int = CHUNK_SIZE_TOKENS,
               overlap: int = CHUNK_OVERLAP_TOKENS) -> list[str]:
    """
    Split text into overlapping token windows.
    Returns a list of string chunks, each ≤ max_tokens tokens.
    """
    tokens = tokenizer.encode(text)
    if len(tokens) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(tokenizer.decode(chunk_tokens))
        if end == len(tokens):
            break
        start += max_tokens - overlap   # slide window with overlap

    return chunks


def expand_record(record: dict) -> list[dict]:
    """
    If a record's content exceeds CHUNK_SIZE_TOKENS, split it into
    multiple sub-records with indexed IDs (e.g. kb_x_000 → kb_x_000_c0, _c1 …).
    Returns list of records (usually just the original, unchanged).
    """
    chunks = chunk_text(record["content"])
    if len(chunks) == 1:
        return [record]

    expanded = []
    for i, chunk in enumerate(chunks):
        new_rec = record.copy()
        new_rec["record_id"] = f"{record['record_id']}_c{i}"
        new_rec["content"] = chunk
        new_rec["content_hash"] = f"{record['content_hash']}_c{i}"
        new_rec["word_count"] = len(chunk.split())
        expanded.append(new_rec)

    return expanded


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_batch(texts: list[str], retries: int = 3) -> list[list[float]]:
    """Call OpenAI Embeddings API for a batch of texts. Retries on rate-limit."""
    for attempt in range(retries):
        try:
            response = client.embeddings.create(
                input=texts,
                model=EMBEDDING_MODEL,
            )
            return [item.embedding for item in response.data]
        except Exception as exc:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"  [embedder] Retry {attempt+1} after error: {exc}. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


def embed_records(records: list[dict]) -> list[list[float]]:
    """
    Embed all records in batches, return list of embedding vectors
    in the same order as records.
    """
    all_embeddings = []
    total = len(records)
    for i in range(0, total, EMBED_BATCH_SIZE):
        batch = records[i: i + EMBED_BATCH_SIZE]
        texts = [r["content"] for r in batch]
        print(f"  [embedder] Embedding batch {i//EMBED_BATCH_SIZE + 1}"
              f" ({len(batch)} records, {i+1}–{min(i+len(batch), total)}/{total})...")
        embeddings = embed_batch(texts)
        all_embeddings.extend(embeddings)
        time.sleep(0.3)  # gentle pacing for free-tier rate limits

    return all_embeddings


# ── Main indexing pipeline ────────────────────────────────────────────────────

def load_processed_records() -> list[dict]:
    """Load all records from the cleaned JSONL file."""
    if not PROCESSED_JSONL.exists():
        raise FileNotFoundError(
            f"Processed JSONL not found: {PROCESSED_JSONL}\n"
            "Run ingestion/ingest_all.py first."
        )
    records = []
    with open(PROCESSED_JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def run_embedder(force_reindex: bool = False) -> int:
    """
    Full embedding + indexing pipeline.
    - Loads cleaned records
    - Chunks any oversized records
    - Embeds via OpenAI
    - Upserts into ChromaDB
    Returns total records indexed.
    """
    print("\n[embedder] Starting embedding + indexing pipeline...")

    # Optionally wipe and re-index from scratch
    if force_reindex:
        print("  [embedder] force_reindex=True → deleting existing collection...")
        delete_collection()

    # Load records
    raw_records = load_processed_records()
    print(f"  [embedder] Loaded {len(raw_records)} cleaned records from JSONL.")

    # Expand (chunk) oversized records
    all_records = []
    for rec in raw_records:
        all_records.extend(expand_record(rec))

    expanded_count = len(all_records) - len(raw_records)
    print(f"  [embedder] {len(all_records)} records after chunking "
          f"({expanded_count} additional chunks from oversized records).")

    # Embed
    embeddings = embed_records(all_records)

    # Upsert into ChromaDB
    print(f"  [embedder] Upserting {len(all_records)} records into ChromaDB...")
    upserted = add_records(all_records, embeddings)

    total_in_db = count_records()
    print(f"\n[embedder] Done. Upserted: {upserted} | Total in DB: {total_in_db}")
    return upserted


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Embed and index KB records into ChromaDB")
    parser.add_argument("--force-reindex", action="store_true",
                        help="Wipe ChromaDB and re-index from scratch")
    args = parser.parse_args()
    run_embedder(force_reindex=args.force_reindex)
