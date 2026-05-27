"""
Streaming search endpoint — POST /search/stream

SSE event sequence:
  data: {"type": "sources", "sources": [...]}  ← sent immediately after retrieval
  data: {"type": "token", "token": "..."}       ← one event per LLM token
  data: [DONE]                                  ← stream end sentinel

Multi-tenancy: reads X-Tenant-ID header (default "default").
Re-ranking: Cohere re-rank applied before streaming if COHERE_API_KEY is set.
"""
import asyncio
import json

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from loguru import logger

from app.core.embeddings import get_embedding
from app.core.es_client import keyword_search
from app.core.fusion import reciprocal_rank_fusion
from app.core.llm import stream_answer
from app.core.pinecone_client import semantic_search
from app.core.reranker import rerank
from app.models.schemas import SearchRequest

router = APIRouter()


@router.post("/stream")
async def search_stream(
    request: SearchRequest,
    x_tenant_id: str = Header(default="default"),
):
    logger.info(f"[{x_tenant_id}] Stream request: '{request.query[:60]}'")

    query_embedding = await get_embedding(request.query)

    semantic_task = asyncio.create_task(
        semantic_search(query_embedding, top_k=20, tenant_id=x_tenant_id)
    )
    keyword_task = asyncio.create_task(
        keyword_search(request.query, top_k=20, tenant_id=x_tenant_id)
    )
    semantic_results, keyword_results = await asyncio.gather(semantic_task, keyword_task)

    fused_results = reciprocal_rank_fusion(
        [semantic_results, keyword_results], top_n=20
    )

    # Re-rank before streaming so sources sent in the first event are already ranked best-first
    final_results = await rerank(request.query, fused_results, top_n=request.top_k)

    async def event_generator():
        # Send sources right away — the UI shows them while the LLM is still generating
        sources_event = json.dumps({"type": "sources", "sources": final_results})
        yield f"data: {sources_event}\n\n"

        async for token in stream_answer(request.query, final_results):
            token_event = json.dumps({"type": "token", "token": token})
            yield f"data: {token_event}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
