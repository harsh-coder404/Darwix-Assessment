"""
ingest_all.py — Master ingestion runner
Runs the full Q2 data pipeline in order:
  1. scraper.py  → fetches web pages → data/raw/*.json
  2. pdf_parser.py → parses PDF/text documents → data/raw/*.json
  3. cleaner.py  → cleans, deduplicates, segments → data/processed/cleaned_records.jsonl

Usage (inside Docker container or locally):
  python q2_knowledge_base/ingestion/ingest_all.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from q2_knowledge_base.ingestion.scraper import run_scraper
from q2_knowledge_base.ingestion.pdf_parser import run_pdf_parser
from q2_knowledge_base.ingestion.cleaner import run_cleaner


def main():
    print("=" * 60)
    print("  Q2 Data Ingestion Pipeline — Health Insurance KB")
    print("=" * 60)

    # Step 1: Scrape web sources
    print("\n[STEP 1/3] Web Scraping")
    web_records = run_scraper()
    print(f"  → {sum(1 for r in web_records if not r.get('error'))} sources scraped OK")

    # Step 2: Parse PDF / text documents
    print("\n[STEP 2/3] Document Parsing")
    pdf_records = run_pdf_parser()
    print(f"  → {sum(1 for r in pdf_records if not r.get('error'))} documents parsed OK")

    # Step 3: Clean, deduplicate, and segment
    print("\n[STEP 3/3] Cleaning & Processing")
    clean_records = run_cleaner()

    print("\n" + "=" * 60)
    print(f"  PIPELINE COMPLETE")
    print(f"  Total KB records ready for embedding: {len(clean_records)}")
    print(f"  Output: q2_knowledge_base/data/processed/cleaned_records.jsonl")
    print("=" * 60)


if __name__ == "__main__":
    main()
