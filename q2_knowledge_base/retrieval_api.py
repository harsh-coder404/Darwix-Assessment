"""
retrieval_api.py — Q2 Knowledge Base: FastAPI Retrieval Endpoint
Serves as the bridge between the Q1 Voice Agent (Vapi) and ChromaDB.
Exposes a POST /retrieve endpoint that takes a query, embeds it, and
returns semantic matches.
"""

import sys
import time
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OPENAI_API_KEY, EMBEDDING_MODEL, TOP_K_RESULTS
from q2_knowledge_base.vector_store import query, count_records
from q2_knowledge_base.schema import RetrievalResult, RetrievalResponse

# Initialize OpenAI client 
openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Q2 Knowledge Base Retrieval API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RetrieveRequest(BaseModel):
    query: str
    top_k: Optional[int] = TOP_K_RESULTS
    category: Optional[str] = None


@app.get("/health")
def health_check():
    """Docker health check endpoint."""
    return {"status": "ok", "records_in_db": count_records()}


@app.post("/retrieve", response_model=RetrievalResponse)
def retrieve_knowledge(req: RetrieveRequest):
    """
    1. Receives natural language query
    2. Embeds it using OpenAI via synchronous call
    3. Queries ChromaDB for top_k semantic matches
    4. Returns structured RetrievalResponse
    """
    start_time = time.time()

    # 1. Reject empty queries
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # 2. Embed the query
    try:
        embed_resp = openai_client.embeddings.create(
            input=[req.query],
            model=EMBEDDING_MODEL
        )
        query_vector = embed_resp.data[0].embedding
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding API error: {exc}")

    # 3. Query ChromaDB
    try:
        db_results = query(
            query_embedding=query_vector,
            top_k=req.top_k,
            category_filter=req.category
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ChromaDB query error: {exc}")

    # 4. Format Output
    output_results = []
    
    # Chroma returns lists of lists; since we just provided 1 query, it's at index 0
    ids_0 = db_results.get("ids", [[]])[0]
    docs_0 = db_results.get("documents", [[]])[0]
    metas_0 = db_results.get("metadatas", [[]])[0]
    dists_0 = db_results.get("distances", [[]])[0]

    for i in range(len(ids_0)):
        # Normalize distance into a pseudo-relevance score 
        # Cosine distance in Chroma: 0 is completely identical, 2 is diametrically opposed
        rel_score = max(0.0, 1.0 - (dists_0[i] / 2.0))
        
        output_results.append(
            RetrievalResult(
                record_id=ids_0[i],
                title=metas_0[i].get("title", ""),
                content=docs_0[i],
                category=metas_0[i].get("category", "general"),
                source=metas_0[i].get("source", ""),
                source_url=metas_0[i].get("source_url", ""),
                distance=dists_0[i],
                relevance_score=rel_score
            )
        )

    retrieval_time_ms = (time.time() - start_time) * 1000

    return RetrievalResponse(
        query=req.query,
        results=output_results,
        total_found=len(output_results),
        retrieval_time_ms=round(retrieval_time_ms, 2)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
