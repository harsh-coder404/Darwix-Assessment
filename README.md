# AI Engineer Assessment — Health-Insurance Voice AI System

## Project Structure

```
assessment_solution/
├── .env                        ← your real credentials (never committed)
├── .env.example                ← template for credentials
├── requirements.txt
├── README.md
│
├── q2_knowledge_base/          ← Part 2 & 3: KB ingestion + retrieval
│   ├── ingestion/
│   │   ├── scraper.py          ← web scraping
│   │   ├── pdf_parser.py       ← PDF ingestion
│   │   └── cleaner.py          ← dedup, PII, normalization
│   ├── schema.py               ← KB record schema (Pydantic)
│   ├── embedder.py             ← chunking + embedding
│   ├── vector_store.py         ← ChromaDB interface
│   ├── retrieval_api.py        ← FastAPI app (POST /retrieve)
│   ├── test_retrieval.py       ← 5+ retrieval evaluations
│   └── data/
│       ├── raw/                ← source documents
│       └── processed/          ← cleaned JSONL records
│
├── q1_voice_agent/             ← Part 5 & 6: Vapi voice agent
│   ├── vapi_config.json        ← Vapi assistant config
│   ├── system_prompt.md        ← LLM prompt (references KB)
│   ├── kb_webhook.py           ← FastAPI webhook Vapi calls
│   ├── conversation_flow.md    ← flow logic + business rules
│   └── test_results/
│       ├── call_1_transcript.txt
│       ├── call_2_transcript.txt
│       ├── call_3_transcript.txt
│       └── results_summary.md
│
├── q3_multilingual_bots/       ← Part 7 & 8: Philippines + Indonesia
│   ├── philippines/
│   │   ├── vapi_config.json
│   │   ├── system_prompt.md
│   │   ├── localization_examples.md
│   │   └── test_results/
│   └── indonesia/
│       ├── vapi_config.json
│       ├── system_prompt.md
│       ├── localization_examples.md
│       └── test_results/
│
├── q4_realtime_nudges/         ← Part 9 & 10: Live nudge pipeline
│   ├── pipeline.py             ← main async pipeline controller
│   ├── asr_stream.py           ← Deepgram streaming client
│   ├── signal_extractor.py     ← LLM-based signal detection
│   ├── nudge_engine.py         ← nudge rules, cooldown, dedup
│   ├── dashboard.py            ← Streamlit real-time dashboard
│   ├── simulate_call.py        ← replay audio at real-time speed
│   ├── latency_report.md
│   └── test_results/
│
└── submission/
    ├── architecture.md
    └── final_checklist.md
```

## Quick Start

1. **Copy environment template**
   ```bash
   cp .env.example .env
   # Fill in your API keys in .env
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Q2 Knowledge Base ingestion**
   ```bash
   cd q2_knowledge_base
   python ingestion/scraper.py
   python ingestion/pdf_parser.py
   python embedder.py
   ```

4. **Start Q2 Retrieval API**
   ```bash
   cd q2_knowledge_base
   uvicorn retrieval_api:app --reload --port 8001
   ```

5. **Start Q1 Webhook Server** (Vapi calls this during voice calls)
   ```bash
   cd q1_voice_agent
   uvicorn kb_webhook:app --reload --port 8002
   ```

6. **Run Q4 Real-Time Nudge Pipeline**
   ```bash
   cd q4_realtime_nudges
   streamlit run dashboard.py
   ```

## Technology Stack

| Layer | Tool |
|---|---|
| Voice Platform | Vapi.ai |
| LLM | OpenAI GPT-4o |
| ASR (Streaming) | Deepgram |
| TTS | ElevenLabs / Google TTS |
| Embeddings | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB (local) |
| API Framework | FastAPI |
| Dashboard | Streamlit |

## Use Case

**Health-Insurance Lead Qualification** across all four questions.

## Credentials Required

| Service | Sign Up |
|---|---|
| OpenAI | https://platform.openai.com |
| Vapi.ai | https://vapi.ai |
| Deepgram | https://deepgram.com |
| ElevenLabs | https://elevenlabs.io |
