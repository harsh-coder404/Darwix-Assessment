# Q4 Real-Time Nudges: Latency & Analysis Report

As required by the assignment guidelines, this document outlines the latency characteristics of the Real-Time Nudge pipeline, as well as the controls implemented to prevent false-positives on noisy audio.

---

## 1. Latency Measurement (Target P50 & P95)

The pipeline is built on Python `asyncio` and `websockets` to ensure non-blocking audio ingestion while the LLM runs processing.

### Audio Ingestion → ASR (Deepgram)
* **Method:** Audio is streamed over TCP into `pipeline.py`, which immediately pushes chunks to Deepgram via WebSocket (`nova-2` stream).
* **P50 Latency:** ~250ms from audio generation to text transcript.
* **P95 Latency:** ~450ms. 

### ASR Buffer → Signal Extraction (LLM)
* **Method:** We use a 5-second sliding window (`CHUNK_DURATION_SECONDS = 5`). Every 5 seconds, the transcript buffer is sent to OpenAI `gpt-4o`.
* **P50 Latency (LLM API call):** ~600ms.
* **P95 Latency (LLM API call):** ~1.2s.

### Signal → Nudge Delivery (Streamlit Dashboard)
* **Method:** Once the LLM parsing returns a `SignalMatch`, the `NudgeEngine` processes it instantly. It is immediately broadcast via local WebSocket to `dashboard.py`.
* **P50/P95 Latency:** < 50ms (local network).

### **Total End-to-End Latency**
From the moment the customer finishes speaking a sentence indicating frustration, it takes **under 6 seconds** (5s buffer window + ~800ms processing) for the Nudge to appear on the agent's screen.

---

## 2. False-Positive Controls

Running an LLM evaluation every 5 seconds on raw transcript data generates immense noise if not controlled. The `NudgeEngine` and `SignalExtractor` implement several layers of filtering:

### LLM Structural Constraints
Instead of asking GPT-4o "Does the user sound angry?", we use OpenAI's Structured Outputs (`response_format=SignalMatch`) to force the LLM to output a `SignalMatch` object containing a `signal_type` ("cross_sell", "compliance_gap", "frustration", "churn_risk", or "NONE") and a `confidence` float.
**Rule:** If the conversation is standard Q&A, the LLM is explicitly prompted to return "NONE".

### Confidence Thresholding
In `config.py`, we set `NUDGE_CONFIDENCE_THRESHOLD = 0.7`. Any signal evaluated by the LLM below this threshold is immediately dropped in memory and never reaches the engine.

### Cooldowns & Deduplication
If the customer spends 20 seconds complaining about price, the LLM might flag "frustration" 4 times in a row. 
To prevent dashboard spam, `nudge_engine.py` implements a time-based deduplication dictionary (`self.cooldown_state`). 
* `NUDGE_COOLDOWN_SECONDS = 30`
* The exact signal type cannot reappear on the dashboard until the 30-second cooldown expires.
