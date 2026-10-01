"""
signal_extractor.py — Q4 Real-Time Nudges
Takes a conversational transcript chunk, sends it to GPT-4o, and looks
for specific signals (compliance gap, cross-sell, frustration, etc.).
"""

import sys
import json
import asyncio
from pathlib import Path
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OPENAI_API_KEY, LLM_MODEL, NUDGE_CONFIDENCE_THRESHOLD

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

class SignalMatch(BaseModel):
    signal_type: str = Field(description="One of: cross_sell, compliance_gap, frustration, churn_risk, NONE")
    reasoning: str = Field(description="Brief explanation of why this signal was detected")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")
    recommended_nudge: Optional[str] = Field(description="The exact text to show the agent on the dashboard")


EXTRACTION_PROMPT = """
You are a real-time call analysis engine for a health insurance call center.
You are given a short transcript chunk from an ongoing call (with speaker labels).

Your job is to detect if ANY of the following specific signals are present in this chunk.
If they are, generate a nudge for the AGENT.

Available Signals:
1. "cross_sell": The customer mentions a need for additional coverage (e.g. dental, vision, life insurance, adding a spouse).
   - Nudge: Suggest quoting the corresponding add-on.
2. "compliance_gap": The agent is finalizing a policy BUT forgot to state the mandatory "Terms and conditions apply" or "Recording consent".
   - Nudge: Remind the agent to state the required compliance phrase.
3. "frustration": The customer uses angry words, sighs, cuts the agent off, or complains about price/process.
   - Nudge: Suggest an empathy phrase ("I understand your frustration...") or a supervisor escalation.
4. "churn_risk": Customer threatens to cancel or move to a competitor.
   - Nudge: Mention retention offers or ask to escalate.
5. "NONE": Normal conversation. No urgent nudge needed.

Rules:
- Be strict. Do not emit a signal if the conversation is just standard Q&A. Return "NONE".
- Confidence must be > 0.7 to be considered valid.
"""

async def extract_signals(transcript_chunk: str) -> Optional[SignalMatch]:
    """Runs a quick LLM analysis over a 5-10 second transcript chunk."""
    if not transcript_chunk.strip():
        return None

    try:
        response = await client.beta.chat.completions.parse(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": f"Transcript Chunk:\n{transcript_chunk}"}
            ],
            response_format=SignalMatch,
            temperature=0.0
        )
        match = response.choices[0].message.parsed
        
        # Filter noise & low confidence
        if match.signal_type == "NONE" or match.confidence < NUDGE_CONFIDENCE_THRESHOLD:
            return None
            
        return match

    except Exception as exc:
        print(f"[SignalExtractor] LLM Error: {exc}")
        return None
