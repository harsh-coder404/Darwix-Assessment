# AI Voice Agent Assessment: Comprehensive Solution

This repository contains the complete implementation for the Darwix AI Engineer Assessment. It implements a 4-part asynchronous, intelligent voice system tailored for **Health Insurance Lead Qualification & Consumer Finance**.

## Repository Structure

```text
darwix-ai-assessment/
├── README.md                      # This documentation
├── .env.example                   # API Key template
├── docker-compose.yml             # Single-command environment orchestration
├── architecture.md                # System Architecture Diagram (Mermaid)
│
├── q1_voice_agent/                # Phase 2: Knowledge-Grounded Voice Agent
│   ├── vapi_config.json
│   ├── system_prompt.md
│   ├── kb_webhook.py              # Connects Vapi agent to Q2 KB
│   └── test_results/              # Simulated call transcripts & evaluation
│
├── q2_knowledge_base/             # Phase 1: Production-Ready KB Pipeline
│   ├── ingestion/                 # Web scraper, PDF parser, Text cleaner+PII Filter
│   ├── embedder.py                # OpenAI chunking & ChromaDB upsert
│   ├── retrieval_api.py           # FastAPI endpoint for Q1
│   └── test_retrieval.py          # E2E metric tests
│
├── q3_multilingual_bots/          # Phase 3: Native-Language Voice Bots
│   ├── philippines/               # Taglish Bancassurance Agent
│   └── indonesia/                 # Bahasa Indonesia Multifinance Agent
│       └── localization_examples.md # Context explanations for code-switching
│
├── q4_realtime_nudges/            # Phase 4: Live Audio Insights
│   ├── pipeline.py                # Async Deepgram + LLM Engine
│   ├── dashboard.py               # Live Streamlit UI via WebSockets
│   ├── nudge_engine.py            # Cooldown, severity, dedup logic
│   ├── simulate_call.py           # Real-time audio TCP streamer
│   └── latency_report.md          # Constraints & P50/P95 reporting
│
└── submission/                    # Evaluation Deliverables
    ├── final_checklist.md
    └── video_walkthrough_link.md
```

## How to Run This Project

The entire system is containerized via Docker for guaranteed cross-platform reproducibility.

### Prerequisites
1. Clone this repository.
2. Ensure you have Docker and Docker Compose installed.
3. Copy `.env.example` to `.env` and fill in your API keys:
   `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `VAPI_PRIVATE_API_KEY`, `ELEVENLABS_API_KEY`

### 1. Build and Start Services
```bash
docker compose up --build -d
```
*This starts three services:*
1. `kb_api` (Port 8001) - Q2 Knowledge Base
2. `webhook` (Port 8002) - Q1 Agent Webhook
3. `nudge_dashboard` (Port 8501) - Q4 Real-Time Dashboard

### 2. Run the KB Ingestion Pipeline (Q2)
Generate the records, populate ChromaDB, and run vector tests:
```bash
# Scrape, parse mock PDF, and clean/redact PII
docker compose exec kb_api python q2_knowledge_base/ingestion/ingest_all.py

# Chunk, embed (OpenAI), and index in ChromaDB
docker compose exec kb_api python q2_knowledge_base/embedder.py

# Run the 5 mandated semantic search tests
docker compose exec kb_api python q2_knowledge_base/test_retrieval.py
```

### 3. Start the Q4 Real-Time Nudge Pipeline
Start the background async engine:
```bash
docker compose exec nudge_dashboard python q4_realtime_nudges/pipeline.py
```
Open the Dashboard in your browser: `http://localhost:8501`

To simulate a live call audio stream hitting the pipeline:
*(Note: Requires a generic `.wav` file in the directory)*
```bash
docker compose exec nudge_dashboard python q4_realtime_nudges/simulate_call.py path/to/your/audio.wav
```

## Highlights & Technical Decisions
* **Strict Grounding:** Q1's `system_prompt.md` is strictly engineered to forbid hallucination, forcing a human escalation (Call 3 transcript) when out-of-scope.
* **Idempotent Upserts:** The ChromaDB pipeline is stable and uses hashing to `upsert`, meaning you can run it multiple times safely.
* **Code-Switching over Translation:** The Q3 bots rely on sophisticated cultural prompts showing actual local finance vernacular instead of raw translations.
* **Nudge Suppression Engine:** The Q4 LLM pipeline sits behind a time-based cooldown engine to prevent Streamlit UI spam during prolonged negative customer engagements.
