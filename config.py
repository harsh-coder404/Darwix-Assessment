"""
Shared configuration for the AI Engineer Assessment project.
All modules import from here so keys are loaded in one place.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (one level above any sub-package)
_ROOT = Path(__file__).parent
load_dotenv(dotenv_path=_ROOT / ".env", override=False)

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
VAPI_PRIVATE_API_KEY: str = os.environ.get("VAPI_PRIVATE_API_KEY", "")
VAPI_PUBLIC_KEY: str = os.environ.get("VAPI_PUBLIC_KEY", "")
DEEPGRAM_API_KEY: str = os.environ.get("DEEPGRAM_API_KEY", "")
ELEVENLABS_API_KEY: str = os.environ.get("ELEVENLABS_API_KEY", "")

# ── Internal Service URLs ─────────────────────────────────────────────────────
KB_RETRIEVAL_URL: str = os.environ.get("KB_RETRIEVAL_URL", "http://localhost:8001")
KB_WEBHOOK_URL: str = os.environ.get("KB_WEBHOOK_URL", "http://localhost:8002")

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_RAW_DIR = _ROOT / "q2_knowledge_base" / "data" / "raw"
DATA_PROCESSED_DIR = _ROOT / "q2_knowledge_base" / "data" / "processed"
CHROMA_DB_DIR = _ROOT / "q2_knowledge_base" / "chroma_db"

# ── KB / Embedding Settings ───────────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
CHUNK_SIZE_TOKENS = 400          # target tokens per chunk
CHUNK_OVERLAP_TOKENS = 50        # overlap between adjacent chunks
TOP_K_RESULTS = 5                # how many KB records to retrieve per query
COLLECTION_NAME = "health_insurance_kb"

# ── LLM Settings ─────────────────────────────────────────────────────────────
LLM_MODEL = "gpt-4o"
LLM_TEMPERATURE = 0.0            # deterministic for KB-grounded answers
MAX_TOKENS_RESPONSE = 512

# ── Q4: Real-Time Nudge Settings ─────────────────────────────────────────────
NUDGE_COOLDOWN_SECONDS = 30      # same nudge type cannot fire again within this window
NUDGE_CONFIDENCE_THRESHOLD = 0.7 # minimum confidence to emit a nudge
CHUNK_DURATION_SECONDS = 5       # audio chunk size for streaming

def validate_keys() -> None:
    """Warn at startup if critical keys are missing."""
    missing = []
    for name, val in [
        ("OPENAI_API_KEY", OPENAI_API_KEY),
        ("DEEPGRAM_API_KEY", DEEPGRAM_API_KEY),
        ("VAPI_PRIVATE_API_KEY", VAPI_PRIVATE_API_KEY),
    ]:
        if not val:
            missing.append(name)
    if missing:
        print(f"[config] WARNING: Missing env vars: {', '.join(missing)}")
        print("[config] Copy .env.example → .env and fill in your keys.")

validate_keys()
