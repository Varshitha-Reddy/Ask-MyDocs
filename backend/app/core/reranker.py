"""
Cohere re-ranker (Phase 4.3)

After RRF gives us a merged list of ~20 candidates, we send the full text of each
chunk to Cohere's re-rank model. Cohere scores every chunk against the query using
a cross-encoder (reads query + chunk together), which is much more accurate than
the bi-encoder used for embedding search.

Why add re-ranking on top of RRF?
- Embedding models and BM25 both use independent scoring — they don't "read" query
  and document together.
- A cross-encoder sees both at the same time, like a human reading a passage to
  decide if it answers a question. This is more accurate but too slow to run over
  the entire corpus, so we use it only on the top-N candidates from RRF.
- Typical gain: +5-10% precision on top of hybrid search alone.

Usage:
- Set COHERE_API_KEY in .env to enable re-ranking.
- If the key is missing, this module returns the input list unchanged — the app
  works perfectly without it, just without the extra precision boost.
"""
import asyncio
from typing import Optional

import cohere
from loguru import logger

from app.config import settings

# Lazy-initialized client — only created if the API key is configured
_client: Optional[cohere.Client] = None


def _get_client() -> Optional[cohere.Client]:
    global _client
    if not settings.cohere_api_key:
        return None
    if _client is None:
        _client = cohere.Client(api_key=settings.cohere_api_key)
    return _client


def _rerank_sync(query: str, docs: list[dict], top_n: int) -> list[dict]:
    client = _get_client()

    # If Cohere isn't configured, just return the first top_n from RRF order
    if client is None:
        return docs[:top_n]

    # Cohere's rerank endpoint expects a list of plain strings
    texts = [doc["content"] for doc in docs]

    response = client.rerank(
        model="rerank-english-v3.0",
        query=query,
        documents=texts,
        top_n=top_n,
    )

    # response.results is sorted best-first; each item has .index and .relevance_score
    reranked = []
    for item in response.results:
        doc = dict(docs[item.index])           # get the original doc at that position
        doc["score"] = round(item.relevance_score, 6)   # replace RRF score with Cohere score
        reranked.append(doc)

    return reranked


async def rerank(query: str, docs: list[dict], top_n: int = 5) -> list[dict]:
    """
    Re-rank `docs` against `query` using Cohere's cross-encoder model.
    Returns the top_n most relevant docs with updated scores.
    Falls back to returning docs[:top_n] if COHERE_API_KEY is not set.
    """
    if not settings.cohere_api_key:
        logger.debug("COHERE_API_KEY not set — skipping re-ranking, using RRF order")
        return docs[:top_n]

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _rerank_sync, query, docs, top_n)
    logger.debug(f"Cohere re-ranked {len(docs)} candidates → top {len(result)}")
    return result
