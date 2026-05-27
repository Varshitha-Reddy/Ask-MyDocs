"""
Search pipeline (non-streaming):
  1. Redis cache check (keyed by query + tenant_id)
  2. Parallel: Pinecone semantic search + ES BM25 keyword search
  3. RRF fusion
  4. Cohere re-rank (optional, skipped if COHERE_API_KEY is not set)
  5. LLM answer generation with citations
  6. Cache result
"""
import asyncio
import hashlib
import time

from fastapi import APIRouter, Header, HTTPException
from loguru import logger

from app.core.cache import cache_result, get_cached_result
from app.core.embeddings import get_embedding
from app.core.es_client import keyword_search
from app.core.fusion import reciprocal_rank_fusion
from app.core.llm import generate_answer
from app.core.pinecone_client import semantic_search
from app.core.reranker import rerank
from app.models.schemas import SearchRequest, SearchResponse
from app.utils.metrics import SEARCH_LATENCY, SEARCHES_TOTAL

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    # Each tenant's cache is isolated by including tenant_id in the key
    x_tenant_id: str = Header(default="default"),
):
    start_time = time.time()

    # Cache key includes the tenant so one tenant can't read another's cached results
    cache_key = f"search:{x_tenant_id}:{hashlib.sha256(request.query.encode()).hexdigest()}"

    cached = await get_cached_result(cache_key)
    if cached:
        cached["cached"] = True
        cached["latency_ms"] = int((time.time() - start_time) * 1000)
        logger.info(f"[{x_tenant_id}] Cache HIT: '{request.query[:60]}'")
        SEARCHES_TOTAL.labels(cache_status="hit").inc()
        SEARCH_LATENCY.observe(time.time() - start_time)
        return cached

    logger.info(f"[{x_tenant_id}] Cache MISS: '{request.query[:60]}'")

    # Embed query once — used by semantic search
    query_embedding = await get_embedding(request.query)

    # Parallel retrieval — both searches run at the same time
    semantic_task = asyncio.create_task(
        semantic_search(query_embedding, top_k=20, tenant_id=x_tenant_id)
    )
    keyword_task = asyncio.create_task(
        keyword_search(request.query, top_k=20, tenant_id=x_tenant_id)
    )
    semantic_results, keyword_results = await asyncio.gather(semantic_task, keyword_task)

    # RRF merges the two ranked lists into one (top 20 candidates for re-ranking)
    fused_results = reciprocal_rank_fusion(
        [semantic_results, keyword_results], top_n=20
    )

    if not fused_results:
        raise HTTPException(status_code=404, detail="No relevant documents found.")

    # Cohere re-ranks the top-20 candidates → top request.top_k
    # If COHERE_API_KEY is not set, this just slices to top_k without calling Cohere
    final_results = await rerank(request.query, fused_results, top_n=request.top_k)

    answer = await generate_answer(request.query, final_results)

    response = {
        "answer": answer,
        "sources": final_results,
        "cached": False,
        "latency_ms": int((time.time() - start_time) * 1000),
    }

    await cache_result(cache_key, response)

    SEARCHES_TOTAL.labels(cache_status="miss").inc()
    SEARCH_LATENCY.observe(time.time() - start_time)

    return response
