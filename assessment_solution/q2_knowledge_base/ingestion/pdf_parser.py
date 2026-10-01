"""
pdf_parser.py — Q2 Data Ingestion: PDF Parser
Parses health-insurance policy PDFs (including a built-in mock policy document)
and saves structured raw records to data/raw/.
"""

import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

import pdfplumber

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import DATA_RAW_DIR

RAW_DIR = DATA_RAW_DIR
RAW_DIR.mkdir(parents=True, exist_ok=True)

MOCK_PDF_DIR = Path(__file__).parent.parent / "data" / "mock_pdfs"
MOCK_PDF_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Mock PDF generator (creates a realistic policy document if no real PDF exists)
# ─────────────────────────────────────────────────────────────────────────────

MOCK_POLICY_TEXT = """\
HEALTH INSURANCE POLICY DOCUMENT
HealthCare Plus — Individual & Family Plan
Policy Version: 2024-01 | Effective Date: January 1, 2024

SECTION 1: COVERAGE OVERVIEW
HealthCare Plus provides comprehensive health coverage for individuals and families.
Coverage includes: hospitalisation, outpatient consultations, prescription drugs,
preventive care, mental health services, and emergency care.

SECTION 2: ELIGIBILITY & ENROLLMENT
2.1 Age Eligibility
  - Individuals aged 18 to 65 are eligible for standard plans.
  - Children up to age 26 may be covered under a parent's plan.
2.2 Enrollment Periods
  - Open Enrollment: November 1 – January 15 each year.
  - Special Enrollment: Triggered by qualifying life events (marriage, birth, job loss).
2.3 Pre-existing Conditions
  - Pre-existing conditions are covered with NO waiting period under ACA-compliant plans.

SECTION 3: PREMIUMS, DEDUCTIBLES & COST-SHARING
3.1 Monthly Premium
  - Individual plan: $350/month (before subsidies).
  - Family plan: $950/month (before subsidies).
  - Subsidies available based on income (100%–400% Federal Poverty Level).
3.2 Annual Deductible
  - Individual: $1,500 per year.
  - Family: $3,000 per year.
  - Deductible resets on January 1 each year.
3.3 Copayments
  - Primary care visit: $30 copay after deductible.
  - Specialist visit: $60 copay after deductible.
  - Emergency room: $250 copay (waived if admitted).
3.4 Coinsurance
  - After deductible is met: plan pays 80%, member pays 20%.
3.5 Out-of-Pocket Maximum
  - Individual: $6,500 per year.
  - Family: $13,000 per year.
  - Once reached, plan covers 100% of covered services.

SECTION 4: NETWORK & PROVIDERS
4.1 In-Network
  - Using in-network providers results in lower cost-sharing.
  - Network includes 500,000+ providers nationwide.
4.2 Out-of-Network
  - Emergency out-of-network care is covered at in-network rates.
  - Non-emergency out-of-network care subject to higher deductible and coinsurance.
4.3 Primary Care Physician (PCP)
  - Selecting a PCP is recommended but not mandatory.
  - Referrals to specialists are not required.

SECTION 5: PRESCRIPTION DRUG COVERAGE
5.1 Formulary Tiers
  - Tier 1 (Generic): $10 copay.
  - Tier 2 (Preferred Brand): $40 copay.
  - Tier 3 (Non-Preferred Brand): $75 copay.
  - Tier 4 (Specialty): 25% coinsurance (max $250/month).
5.2 Mail-Order Pharmacy
  - 90-day supply available at 2.5x the 30-day copay (effective discount).

SECTION 6: PREVENTIVE CARE
  - Covered 100% with NO cost-sharing when using in-network providers.
  - Includes: annual physical, cancer screenings, immunisations, well-woman visits.

SECTION 7: MENTAL HEALTH & SUBSTANCE USE
  - Mental health benefits are equal to medical/surgical benefits (parity law).
  - Includes: therapy sessions, inpatient psychiatric care, substance use treatment.
  - Telehealth mental health: $0 copay for first 3 visits per year.

SECTION 8: EXCLUSIONS & LIMITATIONS
  - Cosmetic surgery (unless medically necessary).
  - Experimental treatments not approved by FDA.
  - Long-term custodial care.
  - Dental and vision (separate plans available).

SECTION 9: CLAIMS & APPEALS
9.1 Filing a Claim
  - In-network providers file claims directly.
  - Out-of-network: member submits claim within 180 days of service.
9.2 Appeals Process
  - Internal appeal: submit within 180 days of denial; decision within 30 days.
  - External review: available if internal appeal denied.

SECTION 10: GRACE PERIOD & CANCELLATION
  - Premium grace period: 30 days for subsidised plans; 31 days for unsubsidised.
  - Policy cancels if premium remains unpaid after grace period.
  - Qualifying life events allow mid-year special enrollment after cancellation.

SECTION 11: CONTACT & SUPPORT
  - Member Services: 1-800-555-HEALTH (available 24/7)
  - Online Portal: www.healthcareplus-example.com/member
  - Email: support@healthcareplus-example.com

END OF POLICY DOCUMENT
"""


def create_mock_pdf() -> Path:
    """
    Write the mock policy text as a .txt file (treated as a text-based PDF).
    In production, real PDF files would be placed in data/mock_pdfs/.
    """
    mock_path = MOCK_PDF_DIR / "policy_healthcareplus_2024.txt"
    mock_path.write_text(MOCK_POLICY_TEXT, encoding="utf-8")
    print(f"  [pdf_parser] Created mock policy document: {mock_path.name}")
    return mock_path


def parse_txt_as_document(file_path: Path, source_id: str, category: str) -> dict:
    """Parse a plain-text policy document into a raw record."""
    text = file_path.read_text(encoding="utf-8")
    lines = [l.strip() for l in text.splitlines()]
    headings = [l for l in lines if l.isupper() and len(l) > 5]
    return {
        "source_id": source_id,
        "source_name": file_path.stem,
        "url": f"file://{file_path}",
        "category": category,
        "title": lines[0] if lines else file_path.stem,
        "headings": headings[:20],
        "raw_text": text,
        "char_count": len(text),
        "page_count": 1,
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "content_hash": hashlib.md5(text.encode()).hexdigest(),
        "error": None,
    }


def parse_pdf(file_path: Path, source_id: str, category: str) -> Optional[dict]:
    """Parse a real PDF using pdfplumber and return a raw record."""
    try:
        all_text = []
        headings = []
        page_count = 0

        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

        full_text = "\n".join(all_text)
        # Heuristic: headings are short lines mostly in uppercase
        for line in full_text.splitlines():
            stripped = line.strip()
            if stripped and len(stripped) < 100 and stripped.isupper():
                headings.append(stripped)

        return {
            "source_id": source_id,
            "source_name": file_path.stem,
            "url": f"file://{file_path}",
            "category": category,
            "title": file_path.stem.replace("_", " ").title(),
            "headings": headings[:20],
            "raw_text": full_text,
            "char_count": len(full_text),
            "page_count": page_count,
            "scraped_at": datetime.utcnow().isoformat() + "Z",
            "content_hash": hashlib.md5(full_text.encode()).hexdigest(),
            "error": None,
        }

    except Exception as exc:
        print(f"  [pdf_parser] ERROR parsing {file_path.name}: {exc}")
        return {
            "source_id": source_id,
            "source_name": file_path.stem,
            "url": f"file://{file_path}",
            "category": category,
            "title": "",
            "headings": [],
            "raw_text": "",
            "char_count": 0,
            "page_count": 0,
            "scraped_at": datetime.utcnow().isoformat() + "Z",
            "content_hash": "",
            "error": str(exc),
        }


def save_record(record: dict) -> Path:
    out_path = RAW_DIR / f"{record['source_id']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"  [pdf_parser] Saved → {out_path.name}  ({record['char_count']} chars, {record.get('page_count',1)} page(s))")
    return out_path


def run_pdf_parser() -> list[dict]:
    """Parse all PDFs in mock_pdfs/ directory (plus the built-in mock document)."""
    print("\n[pdf_parser] Starting document parsing...")
    records = []

    # ── Always include the built-in mock policy document ─────────────────────
    mock_txt = create_mock_pdf()
    record = parse_txt_as_document(mock_txt, source_id="src_pdf_001", category="policy_document")
    save_record(record)
    records.append(record)

    # ── Parse any real .pdf files placed in mock_pdfs/ ────────────────────────
    pdf_files = list(MOCK_PDF_DIR.glob("*.pdf"))
    for i, pdf_file in enumerate(pdf_files, start=2):
        source_id = f"src_pdf_{i:03d}"
        print(f"  [pdf_parser] Parsing: {pdf_file.name}")
        record = parse_pdf(pdf_file, source_id=source_id, category="policy_document")
        save_record(record)
        records.append(record)

    success = sum(1 for r in records if not r["error"])
    print(f"\n[pdf_parser] Done: {success}/{len(records)} documents parsed successfully.")
    return records


if __name__ == "__main__":
    results = run_pdf_parser()
    total_chars = sum(r["char_count"] for r in results)
    print(f"[pdf_parser] Total content: {total_chars:,} characters.")
