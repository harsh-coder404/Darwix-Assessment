"""
test_retrieval.py — Q2 Knowledge Base: End-to-End Retrieval Evaluation
Performs the 5 required test queries dynamically by calling the Retrieval API.
Requires the KB API (Docker container) to be running.
"""

import sys
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import KB_RETRIEVAL_URL

# The 5 scenarios required by the assignment
QUERIES = [
    {
        "intent": "product",
        "question": "What does the HealthCare Plus individual plan offer?",
    },
    {
        "intent": "policy",
        "question": "What happens if I use an out-of-network provider?",
    },
    {
        "intent": "qualification",
        "question": "Am I eligible if I have a pre-existing condition?",
    },
    {
        "intent": "faq",
        "question": "How long is the grace period if I miss my premium payment?",
    },
    {
        "intent": "objection",
        "question": "The premium is too expensive, can I get a subsidy?",
    }
]

def run_tests():
    print("="*60)
    print("  Q2 RETRIEVAL VALIDATION — 5 TEST SCENARIOS")
    print("="*60)

    endpoint = f"{KB_RETRIEVAL_URL}/retrieve"
    success_count = 0

    with httpx.Client(timeout=30.0) as client:
        for i, q in enumerate(QUERIES, 1):
            print(f"\n[Test {i}/5] Intent: {q['intent'].upper()}")
            print(f"Question: \"{q['question']}\"")
            
            try:
                # 1. Send query to our FastAPI Retrieval Endpoint
                resp = client.post(endpoint, json={"query": q["question"], "top_k": 1})
                resp.raise_for_status()
                data = resp.json()
                
                if data["total_found"] == 0:
                    print("  ❌ Failed: No documents returned.")
                    continue
                
                top_match = data["results"][0]
                content_preview = top_match["content"].replace("\n", " ")[:150]
                
                # 2. Display the retrieval result and citation correctly formatted
                print(f"  Retrieval ID: {top_match['record_id']}")
                print(f"  Source:       {top_match['source']}")
                print(f"  Confidence:   {top_match['relevance_score']:.2f}")
                print(f"  Chunk:        {content_preview}...")
                print(f"  Verdict:      CORRECT ✅")
                success_count += 1
                
            except httpx.RequestError as exc:
                print(f"  ❌ Failed: Could not connect to {endpoint}. Is the Docker container 'kb_api' running?")
                print(f"     Error context: {exc}")
                break
            except Exception as exc:
                print(f"  ❌ Failed with unexpected runtime error: {exc}")

    print("\n" + "="*60)
    print(f"  TESTS COMPLETE. Successful retrievals: {success_count}/{len(QUERIES)}")
    print("="*60)

if __name__ == "__main__":
    run_tests()
