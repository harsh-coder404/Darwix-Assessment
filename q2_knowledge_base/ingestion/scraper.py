"""
scraper.py — Q2 Data Ingestion: Web Scraper
Scrapes health-insurance content from public websites and saves raw HTML/text
to data/raw/ as structured JSON records.
"""

import json
import time
import hashlib
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import DATA_RAW_DIR

RAW_DIR = DATA_RAW_DIR
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── Target sources (public health-insurance FAQ / product pages) ────────────
SOURCES = [
    {
        "source_id": "src_001",
        "name": "HealthInsurance.org - How It Works",
        "url": "https://www.healthinsurance.org/obamacare/how-does-health-insurance-work/",
        "category": "product_overview",
    },
    {
        "source_id": "src_002",
        "name": "HealthInsurance.org - FAQ",
        "url": "https://www.healthinsurance.org/faqs/",
        "category": "faq",
    },
    {
        "source_id": "src_003",
        "name": "Healthcare.gov - Glossary",
        "url": "https://www.healthcare.gov/glossary/",
        "category": "glossary",
    },
    {
        "source_id": "src_004",
        "name": "HealthInsurance.org - Deductibles",
        "url": "https://www.healthinsurance.org/glossary/deductible/",
        "category": "policy_rules",
    },
    {
        "source_id": "src_005",
        "name": "HealthInsurance.org - Copay vs Coinsurance",
        "url": "https://www.healthinsurance.org/glossary/copay/",
        "category": "policy_rules",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_page(source: dict, timeout: int = 15) -> Optional[dict]:
    """Fetch and parse a single page; return a raw record dict or None on failure."""
    url = source["url"]
    try:
        print(f"  [scraper] Fetching: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [scraper] ERROR fetching {url}: {exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Remove noise elements ─────────────────────────────────────────────────
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "form", "noscript", "iframe", "svg"]):
        tag.decompose()

    # ── Extract main content ──────────────────────────────────────────────────
    # Try semantic tags first, then fall back to body
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(class_="content")
        or soup.body
    )
    raw_text = main.get_text(separator="\n", strip=True) if main else ""

    # ── Extract page title ────────────────────────────────────────────────────
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else source["name"]

    # ── Extract headings for section context ──────────────────────────────────
    headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]

    record = {
        "source_id": source["source_id"],
        "source_name": source["name"],
        "url": url,
        "category": source["category"],
        "title": title,
        "headings": headings[:20],       # keep top 20 headings
        "raw_text": raw_text,
        "char_count": len(raw_text),
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "content_hash": hashlib.md5(raw_text.encode()).hexdigest(),
        "error": None,
    }
    return record


def save_record(record: dict) -> Path:
    """Save a raw record to data/raw/<source_id>.json"""
    out_path = RAW_DIR / f"{record['source_id']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"  [scraper] Saved → {out_path.name}  ({record['char_count']} chars)")
    return out_path


def run_scraper() -> list[dict]:
    """Scrape all sources and return list of raw records."""
    print("\n[scraper] Starting web scrape of health-insurance sources...")
    records = []
    for source in SOURCES:
        record = scrape_page(source)
        if record is None:
            # Save a stub error record so we know which source failed
            record = {
                "source_id": source["source_id"],
                "source_name": source["name"],
                "url": source["url"],
                "category": source["category"],
                "title": "",
                "headings": [],
                "raw_text": "",
                "char_count": 0,
                "scraped_at": datetime.utcnow().isoformat() + "Z",
                "content_hash": "",
                "error": "fetch_failed",
            }
        save_record(record)
        records.append(record)
        time.sleep(1)   # polite delay between requests

    success = sum(1 for r in records if not r["error"])
    print(f"\n[scraper] Done: {success}/{len(SOURCES)} sources scraped successfully.")
    return records


if __name__ == "__main__":
    results = run_scraper()
    total_chars = sum(r["char_count"] for r in results)
    print(f"[scraper] Total content: {total_chars:,} characters across {len(results)} files.")
