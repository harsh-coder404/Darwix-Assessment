"""
vector_store.py — Q2 Knowledge Base: ChromaDB Interface
Wraps ChromaDB for adding, querying, and managing KB records.
"""

import sys
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CHROMA_DB_DIR, COLLECTION_NAME, TOP_K_RESULTS


def get_client() -> chromadb.PersistentClient:
    """Return a persistent ChromaDB client pointed at our data directory."""
    CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(CHROMA_DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def get_or_create_collection(client: Optional[chromadb.PersistentClient] = None):
    """Get (or create) the health-insurance KB collection."""
    if client is None:
        client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},   # use cosine distance
    )


def add_records(records: list[dict], embeddings: list[list[float]]) -> int:
    """
    Upsert records + their embeddings into ChromaDB.
    Uses record_id as the ChromaDB document ID (safe to re-run).
    Returns the count of records upserted.
    """
    collection = get_or_create_collection()

    ids = [r["record_id"] for r in records]
    documents = [r["content"] for r in records]
    metadatas = [
        {
            "title": r["title"],
            "category": r["category"],
            "source": r["source"],
            "source_url": r.get("source_url", ""),
            "version": r.get("version", "1.0"),
            "pii": str(r.get("pii", False)),
            "word_count": str(r.get("word_count", 0)),
        }
        for r in records
    ]

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return len(ids)


def query(
    query_embedding: list[float],
    top_k: int = TOP_K_RESULTS,
    category_filter: Optional[str] = None,
) -> dict:
    """
    Query the KB with a pre-computed embedding vector.
    Returns the raw ChromaDB result dict.
    """
    collection = get_or_create_collection()

    where = {"category": category_filter} if category_filter else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    return results


def count_records() -> int:
    """Return the total number of records currently in the collection."""
    try:
        collection = get_or_create_collection()
        return collection.count()
    except Exception:
        return 0


def delete_collection() -> None:
    """Delete and recreate the collection (useful for re-indexing from scratch)."""
    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"[vector_store] Collection '{COLLECTION_NAME}' deleted.")
    except Exception:
        pass


if __name__ == "__main__":
    # Quick sanity check
    n = count_records()
    print(f"[vector_store] Current record count: {n}")
