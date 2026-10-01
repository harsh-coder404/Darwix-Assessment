"""
kb_webhook.py — Q1 Voice Agent: Vapi.ai Webhook Integration
Exposes an endpoint that Vapi calls mid-conversation to query our Knowledge Base.
Vapi expects specific JSON responses for Tool Calls.
"""

import sys
import httpx
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import KB_RETRIEVAL_URL

app = FastAPI(title="Q1 Voice Agent Webhook")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "vapi_webhook"}


@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    """
    Handles Vapi Server URL webhooks (specifically Tool Calls).
    When the Voice Agent triggers the 'query_knowledge_base' tool, Vapi POSTs here.
    """
    payload = await request.json()
    message_type = payload.get("message", {}).get("type")

    # We only care about tool calls for the KB
    if message_type == "tool-calls":
        tool_calls = payload["message"].get("toolCalls", [])
        responses = []

        for call in tool_calls:
            if call["type"] == "function" and call["function"]["name"] == "query_knowledge_base":
                args = call["function"].get("arguments", {})
                query = args.get("query", "")
                
                # Hit the Q2 Retrieval API
                kb_answer = await query_q2_kb(query)

                responses.append({
                    "toolCallId": call["id"],
                    "result": kb_answer
                })

        return {"results": responses}

    # Acknowledge other webhook types (status updates, transcripts, etc.)
    return {"status": "ignored"}


async def query_q2_kb(query: str) -> str:
    """Helper to query the local Q2 Retrieval API and format the response."""
    if not query:
        return "Error: No query provided."

    endpoint = f"{KB_RETRIEVAL_URL}/retrieve"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(endpoint, json={"query": query, "top_k": 3}, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

            if data["total_found"] == 0:
                return "The knowledge base did not return any relevant information for this query. Inform the user that you don't have that information."

            # Construct a clear, factual context for the LLM
            context_parts = []
            for res in data["results"]:
                context_parts.append(
                    f"SOURCE: {res['title']}\n"
                    f"CONTENT: {res['content']}\n"
                )
            
            return "KNOWLEDGE BASE RESULTS:\n" + "\n---\n".join(context_parts)

    except Exception as exc:
        print(f"[Webhook] KB Query Error: {exc}")
        return "Internal error accessing knowledge base. Politely inform the caller there is a temporary system issue."


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
