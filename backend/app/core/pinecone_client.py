"""
Pinecone vector database client.

Multi-tenancy (Phase 4.4):
Every chunk is stored with a `tenant_id` metadata field.
All queries include a metadata filter so tenants never see each other's data.
The filter uses Pinecone's $eq operator: {"tenant_id": {"$eq": "acme-corp"}}.
"""
import asyncio

from loguru import logger
from pinecone import Pinecone

from app.config import settings
from app.models.document import Chunk

_pc = Pinecone(api_key=settings.pinecone_api_key)
_index = _pc.Index(settings.pinecone_index_name)


def _upsert_batch(vectors: list[dict]) -> None:
    _index.upsert(vectors=vectors)


async def upsert_chunks(
    chunks: list[Chunk], embeddings: list[list[float]]
) -> None:
    vectors = []
    for chunk, embedding in zip(chunks, embeddings):
        vectors.append(
            {
                "id": chunk.chunk_id,
                "values": embedding,
                "metadata": {
                    "content": chunk.content,
                    "source_filename": chunk.source_filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    # tenant_id stored here so we can filter on it during search
                    "tenant_id": chunk.tenant_id,
                },
            }
        )

    batch_size = 100
    loop = asyncio.get_event_loop()
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        await loop.run_in_executor(None, _upsert_batch, batch)
        logger.debug(f"Pinecone: upserted batch {i // batch_size + 1}")


def _query_index(
    embedding: list[float], top_k: int, tenant_id: str
) -> list[dict]:
    # The filter ensures only this tenant's vectors are returned
    result = _index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
        filter={"tenant_id": {"$eq": tenant_id}},
    )

    matches = []
    for match in result.matches:
        matches.append(
            {
                "chunk_id": match.id,
                "content": match.metadata.get("content", ""),
                "source_filename": match.metadata.get("source_filename", ""),
                "page_number": int(match.metadata.get("page_number", 0)),
                "tenant_id": match.metadata.get("tenant_id", "default"),
                "score": float(match.score),
            }
        )
    return matches


async def semantic_search(
    embedding: list[float], top_k: int = 20, tenant_id: str = "default"
) -> list[dict]:
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _query_index, embedding, top_k, tenant_id)
    logger.debug(f"Pinecone returned {len(results)} results for tenant '{tenant_id}'")
    return results
