# AI Voice Agent Assessment: System Architecture

The following diagram illustrates the interactions between the 4 major architectural components of our solution (Q1, Q2, Q3, and Q4).

You can view this diagram gracefully rendered directly in GitHub, or by pasting the code below into [Mermaid Live Editor](https://mermaid.live).

```mermaid
graph TD
    %% Core Infrastructure Layer
    subgraph Data Layer & Knowledge Base Q2
        A[Web Scraper & PDF Parser] -->|Raw Data| B(Text Cleaner & PII Redactor)
        B -->|Cleaned jsonl| C[Embedder text-embedding-3]
        C -->|Vector Data| D[(ChromaDB)]
        D <--> E[FastAPI /retrieve Endpoint]
    end

    %% Vocal Agents Layer
    subgraph Voice Agents Q1 & Q3
        F[Vapi.ai Voice Agent Engine]
        G((Customer Call HTTP/SIP)) <--> F
        F -->|ASR Deepgram| H[Transcription]
        F -->|TTS ElevenLabs| I[Speech Gen]
        F -->|Tool Calls| E
        
        J[Q3 Philippines Taglish Bot] -.-> F
        K[Q3 Indonesia Bahasa Bot] -.-> F
        L[Q1 Health Insurance Qual. Bot] -.-> F
    end

    %% Real-Time Insights Layer
    subgraph Real-Time Nudge Pipeline Q4
        M((Live Audio Stream TCP)) --> N[Streaming ASR Client]
        N -->|Speaker Diarized Transcripts| O[Async LLM Signal Extractor]
        O -->|Raw Signals| P{Nudge Engine Rules}
        P -->|Cooldown/Dedup/Priority| Q[WebSockets Broadcast]
        Q --> R[Streamlit Dashboard React]
    end

    %% Inter-component relations
    E -.->|Answers & Citations| F
    G -.->|Live Tap or Siprec| M

    classDef db fill:#f9f,stroke:#333,stroke-width:2px;
    classDef api fill:#bbf,stroke:#333,stroke-width:2px;
    classDef agent fill:#bfb,stroke:#333,stroke-width:2px;
    
    class D db;
    class E,Q api;
    class F,O agent;
```
