"""
schema.py — Q2 Knowledge Base: Record Schema
Pydantic model for a single KB record.
All records in ChromaDB and the JSONL file follow this schema.
"""

from pydantic import BaseModel, Field
from typing import Optional


class KBRecord(BaseModel):
    """A single knowledge base record — one logical section of content."""

    record_id: str = Field(..., description="Unique record ID, e.g. kb_src_pdf_001_003")
    title: str = Field(..., description="Section heading or document title")
    content: str = Field(..., description="The cleaned, readable text content")
    category: str = Field(..., description="Type: policy_document, faq, product_overview, policy_rules, glossary")
    source: str = Field(..., description="Human-readable source name")
    source_url: str = Field("", description="Original URL or file path")
    version: str = Field("1.0", description="Content version")
    pii: bool = Field(False, description="True if PII was detected (and redacted) in this record")
    content_hash: str = Field(..., description="MD5 hash for deduplication")
    processed_at: str = Field(..., description="ISO timestamp of when record was cleaned")
    word_count: int = Field(..., description="Word count of content field")

    class Config:
        extra = "allow"   # allow extra fields without error


class RetrievalResult(BaseModel):
    """A single result returned by the retrieval API."""

    record_id: str
    title: str
    content: str
    category: str
    source: str
    source_url: str
    distance: float = Field(..., description="Cosine distance (lower = more similar)")
    relevance_score: float = Field(..., description="1 - distance, normalised to [0,1]")


class RetrievalResponse(BaseModel):
    """Full response from POST /retrieve."""

    query: str
    results: list[RetrievalResult]
    total_found: int
    retrieval_time_ms: float
