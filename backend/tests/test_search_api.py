"""
Integration-style tests for the search API.
All external services (Redis, Pinecone, Elasticsearch, OpenAI) are mocked
so these tests run without any infrastructure.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_search_returns_answer_on_cache_miss():
    fake_embedding = [0.1] * 1536
    fake_chunks = [
        {
            "chunk_id": "abc123",
            "content": "RRF combines multiple ranked lists.",
            "source_filename": "docs.pdf",
            "page_number": 3,
            "score": 0.016,
        }
    ]
    fake_answer = "RRF combines ranked lists using rank positions [source: docs.pdf, page: 3]."

    with (
        patch("app.api.search.get_cached_result", new_callable=AsyncMock, return_value=None),
        patch("app.api.search.get_embedding", new_callable=AsyncMock, return_value=fake_embedding),
        patch("app.api.search.semantic_search", new_callable=AsyncMock, return_value=fake_chunks),
        patch("app.api.search.keyword_search", new_callable=AsyncMock, return_value=fake_chunks),
        patch("app.api.search.generate_answer", new_callable=AsyncMock, return_value=fake_answer),
        patch("app.api.search.cache_result", new_callable=AsyncMock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/search", json={"query": "how does RRF work?", "top_k": 5}
            )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == fake_answer
    assert body["cached"] is False
    assert len(body["sources"]) > 0
    assert "latency_ms" in body


@pytest.mark.asyncio
async def test_search_returns_cached_result_on_cache_hit():
    cached = {
        "answer": "Cached answer text.",
        "sources": [],
        "cached": True,
        "latency_ms": 5,
    }

    with patch("app.api.search.get_cached_result", new_callable=AsyncMock, return_value=cached):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/search", json={"query": "repeated query", "top_k": 5}
            )

    assert response.status_code == 200
    body = response.json()
    assert body["cached"] is True
    assert body["answer"] == "Cached answer text."


@pytest.mark.asyncio
async def test_search_rejects_empty_query():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/search", json={"query": "", "top_k": 5})

    assert response.status_code == 422  # Pydantic validation error
