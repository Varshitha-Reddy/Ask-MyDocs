"""
Elasticsearch BM25 client.

Multi-tenancy (Phase 4.4):
Every document is stored with a `tenant_id` field (keyword type).
All queries add a `filter` clause so only the requesting tenant's data is returned.
This is standard ES practice — it's faster than separate indices per tenant and
easier to manage at scale.
"""
import asyncio
from datetime import datetime

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from loguru import logger

from app.config import settings
from app.models.document import Chunk

_es = Elasticsearch(settings.es_host)


def create_index_if_not_exists() -> None:
    if _es.indices.exists(index=settings.es_index):
        logger.info(f"ES index '{settings.es_index}' already exists")
        return

    _es.indices.create(
        index=settings.es_index,
        mappings={
            "properties": {
                "chunk_id":        {"type": "keyword"},
                "content":         {"type": "text", "analyzer": "english"},
                "source_filename": {"type": "keyword"},
                "page_number":     {"type": "integer"},
                "chunk_index":     {"type": "integer"},
                # tenant_id must be keyword (not text) so filter queries are exact-match
                "tenant_id":       {"type": "keyword"},
                "ingested_at":     {"type": "date"},
            }
        },
    )
    logger.info(f"Created ES index '{settings.es_index}'")


def _bulk_index(chunks: list[Chunk]) -> None:
    actions = [
        {
            "_index": settings.es_index,
            "_id": chunk.chunk_id,
            "_source": {
                "chunk_id":        chunk.chunk_id,
                "content":         chunk.content,
                "source_filename": chunk.source_filename,
                "page_number":     chunk.page_number,
                "chunk_index":     chunk.chunk_index,
                "tenant_id":       chunk.tenant_id,
                "ingested_at":     datetime.utcnow().isoformat(),
            },
        }
        for chunk in chunks
    ]
    bulk(_es, actions)


async def index_chunks(chunks: list[Chunk]) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _bulk_index, chunks)
    logger.debug(f"ES: indexed {len(chunks)} chunks")


def _search_es(query: str, top_k: int, tenant_id: str) -> list[dict]:
    # bool query: 'must' scores by BM25 relevance, 'filter' restricts to this tenant.
    # Putting tenant isolation in filter (not must) means it doesn't affect relevance scoring.
    response = _es.search(
        index=settings.es_index,
        query={
            "bool": {
                "must": {
                    "match": {"content": {"query": query, "operator": "or"}}
                },
                "filter": [
                    {"term": {"tenant_id": tenant_id}}
                ],
            }
        },
        size=top_k,
    )

    results = []
    for hit in response["hits"]["hits"]:
        src = hit["_source"]
        results.append(
            {
                "chunk_id":        src["chunk_id"],
                "content":         src["content"],
                "source_filename": src["source_filename"],
                "page_number":     int(src.get("page_number", 0)),
                "tenant_id":       src.get("tenant_id", "default"),
                "score":           float(hit["_score"]),
            }
        )
    return results


async def keyword_search(
    query: str, top_k: int = 20, tenant_id: str = "default"
) -> list[dict]:
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _search_es, query, top_k, tenant_id)
    logger.debug(f"ES returned {len(results)} results for tenant '{tenant_id}'")
    return results
