"""
cleaner.py — Q2 Data Ingestion: Cleaner
Reads raw JSON records from data/raw/, applies:
  - Deduplication (content hash)
  - PII detection and redaction
  - Text normalization (whitespace, dates, terminology)
  - Section segmentation
  - Filtered output to data/processed/ as JSONL
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import DATA_RAW_DIR, DATA_PROCESSED_DIR

RAW_DIR = DATA_RAW_DIR
PROCESSED_DIR = DATA_PROCESSED_DIR
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = PROCESSED_DIR / "cleaned_records.jsonl"

# ── PII patterns to detect and redact ────────────────────────────────────────
PII_PATTERNS = [
    # US SSN: 123-45-6789
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
    # Credit card: 16 digits (various formats)
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"), "[CARD_REDACTED]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL_REDACTED]"),
    # US phone numbers
    (re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"), "[PHONE_REDACTED]"),
    # Date of birth patterns like "DOB: 01/01/1980"
    (re.compile(r"(?:DOB|Date of Birth|born)[:\s]+\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}", re.IGNORECASE), "[DOB_REDACTED]"),
]

# ── Terminology standardisation ───────────────────────────────────────────────
TERM_MAP = {
    r"\bco[-\s]?pay\b": "copay",
    r"\bco[-\s]?insurance\b": "coinsurance",
    r"\bout[-\s]of[-\s]pocket\b": "out-of-pocket",
    r"\bpre[-\s]existing\b": "pre-existing",
    r"\bopen[-\s]enrollment\b": "open enrollment",
    r"\bhealth(?:care)? plan\b": "health insurance plan",
    r"\bdeductable\b": "deductible",   # common misspelling
    r"\bpremium payment\b": "premium",
}

# ── Lines to strip (navigation / boilerplate) ─────────────────────────────────
NOISE_PATTERNS = [
    re.compile(r"^(menu|home|about|contact|login|sign[\s-]?in|subscribe|newsletter)$", re.IGNORECASE),
    re.compile(r"^(skip to|jump to|back to top|read more|learn more|click here|advertisement)$", re.IGNORECASE),
    re.compile(r"^copyright\s*©", re.IGNORECASE),
    re.compile(r"^all rights reserved", re.IGNORECASE),
    re.compile(r"^\s*\|\s*$"),          # lone pipe separators
    re.compile(r"^\s*[\-_=]{3,}\s*$"),  # divider lines
]


def detect_pii(text: str) -> bool:
    """Return True if any PII pattern is found in the text."""
    return any(p.search(text) for p, _ in PII_PATTERNS)


def redact_pii(text: str) -> tuple[str, bool]:
    """Redact PII from text; return (cleaned_text, pii_found_flag)."""
    pii_found = False
    for pattern, replacement in PII_PATTERNS:
        new_text, count = pattern.subn(replacement, text)
        if count > 0:
            pii_found = True
            text = new_text
    return text, pii_found


def normalise_text(text: str) -> str:
    """Apply whitespace normalisation and terminology standardisation."""
    # Normalise whitespace
    text = re.sub(r"\r\n|\r", "\n", text)                # CRLF → LF
    text = re.sub(r"[ \t]+", " ", text)                  # multiple spaces → one
    text = re.sub(r"\n{3,}", "\n\n", text)               # 3+ blank lines → 2

    # Standardise terminology
    for pattern_str, replacement in TERM_MAP.items():
        text = re.sub(pattern_str, replacement, text, flags=re.IGNORECASE)

    return text.strip()


def is_noise_line(line: str) -> bool:
    """Return True if this line is navigational/boilerplate noise."""
    stripped = line.strip()
    if not stripped:
        return False  # blank lines are handled separately
    return any(p.match(stripped) for p in NOISE_PATTERNS)


def remove_noise_lines(text: str) -> str:
    """Filter out noise lines from raw text."""
    lines = text.splitlines()
    cleaned = [line for line in lines if not is_noise_line(line)]
    return "\n".join(cleaned)


def segment_into_sections(text: str, source_id: str, title: str, category: str,
                           source_name: str, url: str, pii: bool,
                           content_hash: str) -> list[dict]:
    """
    Split text into logical sections based on headings or paragraph breaks.
    Each section becomes one processed record.
    """
    # Split on double newlines (paragraphs) or lines that look like headings
    heading_re = re.compile(r"^(SECTION\s+\d+.*|[A-Z][A-Z\s&/]{5,}:?)$", re.MULTILINE)

    records = []
    chunks = heading_re.split(text)

    # heading_re.split() returns [before, heading, chunk, heading, chunk, ...]
    # Group them into (heading, body) pairs
    current_heading = title
    buffer_parts = []

    i = 0
    while i < len(chunks):
        chunk = chunks[i].strip()
        if not chunk:
            i += 1
            continue
        # Check if this chunk looks like a heading (came from the split group)
        if heading_re.match(chunk) and len(chunk) < 120:
            # Flush previous buffer
            if buffer_parts:
                body = normalise_text(" ".join(buffer_parts))
                if len(body) > 50:  # skip tiny fragments
                    records.append(_make_record(
                        source_id, source_name, url, category,
                        current_heading, body, pii, content_hash, len(records)
                    ))
            current_heading = chunk
            buffer_parts = []
        else:
            buffer_parts.append(chunk)
        i += 1

    # Flush remainder
    if buffer_parts:
        body = normalise_text(" ".join(buffer_parts))
        if len(body) > 50:
            records.append(_make_record(
                source_id, source_name, url, category,
                current_heading, body, pii, content_hash, len(records)
            ))

    # Fallback: if no sections found, use the full text as one record
    if not records:
        body = normalise_text(text)
        if len(body) > 50:
            records.append(_make_record(
                source_id, source_name, url, category,
                title, body, pii, content_hash, 0
            ))

    return records


def _make_record(source_id: str, source_name: str, url: str, category: str,
                 section_title: str, content: str, pii: bool,
                 content_hash: str, idx: int) -> dict:
    return {
        "record_id": f"kb_{source_id}_{idx:03d}",
        "title": section_title.strip(),
        "content": content,
        "category": category,
        "source": source_name,
        "source_url": url,
        "version": "1.0",
        "pii": pii,
        "content_hash": f"{content_hash}_{idx}",
        "processed_at": datetime.utcnow().isoformat() + "Z",
        "word_count": len(content.split()),
    }


def clean_record(raw: dict) -> list[dict]:
    """Process one raw record into one or more cleaned KB records."""
    if raw.get("error") or not raw.get("raw_text"):
        print(f"  [cleaner] SKIP {raw['source_id']} — no content (error: {raw.get('error')})")
        return []

    text = raw["raw_text"]

    # 1. Remove noise lines
    text = remove_noise_lines(text)

    # 2. Detect and redact PII
    text, pii_found = redact_pii(text)

    # 3. Normalise whitespace and terminology
    text = normalise_text(text)

    # 4. Segment into sections
    sections = segment_into_sections(
        text=text,
        source_id=raw["source_id"],
        title=raw.get("title", raw["source_id"]),
        category=raw.get("category", "general"),
        source_name=raw.get("source_name", raw["source_id"]),
        url=raw.get("url", ""),
        pii=pii_found,
        content_hash=raw.get("content_hash", ""),
    )

    return sections


def run_cleaner() -> list[dict]:
    """Read all raw records, clean them, deduplicate, and write JSONL output."""
    print("\n[cleaner] Starting data cleaning pipeline...")

    raw_files = sorted(RAW_DIR.glob("*.json"))
    print(f"  [cleaner] Found {len(raw_files)} raw record files.")

    all_records: list[dict] = []
    seen_hashes: set[str] = set()

    for raw_file in raw_files:
        with open(raw_file, encoding="utf-8") as f:
            raw = json.load(f)

        cleaned = clean_record(raw)
        deduped = []
        for rec in cleaned:
            if rec["content_hash"] not in seen_hashes:
                seen_hashes.add(rec["content_hash"])
                deduped.append(rec)

        skipped = len(cleaned) - len(deduped)
        print(f"  [cleaner] {raw_file.name}: {len(deduped)} sections "
              f"(+{skipped} duplicates removed, PII={'yes' if any(r['pii'] for r in deduped) else 'no'})")
        all_records.extend(deduped)

    # Write final JSONL
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n[cleaner] Done: {len(all_records)} clean records → {OUTPUT_FILE}")
    return all_records


if __name__ == "__main__":
    records = run_cleaner()
    print(f"[cleaner] Total words across all records: {sum(r['word_count'] for r in records):,}")
