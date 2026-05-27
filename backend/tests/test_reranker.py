"""
Tests for the Cohere re-ranker.
No real Cohere API is called — the client is mocked.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.core.reranker import rerank


def make_doc(chunk_id: str, content: str = "test content", score: float = 0.5) -> dict:
    return {
        "chunk_id": chunk_id,
        "content": content,
        "source_filename": "test.pdf",
        "page_number": 1,
        "score": score,
    }


@pytest.mark.asyncio
async def test_rerank_falls_back_to_rrf_order_when_no_api_key():
    # When COHERE_API_KEY is empty, we should just return docs[:top_n] unchanged
    docs = [make_doc("A"), make_doc("B"), make_doc("C"), make_doc("D")]

    with patch("app.core.reranker.settings") as mock_settings:
        mock_settings.cohere_api_key = ""
        result = await rerank("what is RRF?", docs, top_n=2)

    assert len(result) == 2
    assert result[0]["chunk_id"] == "A"
    assert result[1]["chunk_id"] == "B"


@pytest.mark.asyncio
async def test_rerank_calls_cohere_and_reorders_when_key_is_set():
    docs = [
        make_doc("A", content="RRF combines ranked lists"),
        make_doc("B", content="unrelated content"),
        make_doc("C", content="hybrid search overview"),
    ]

    # Build a fake Cohere response that puts doc C first, then A
    mock_result = MagicMock()
    mock_result.results = [
        MagicMock(index=2, relevance_score=0.95),  # doc C
        MagicMock(index=0, relevance_score=0.80),  # doc A
    ]

    mock_client = MagicMock()
    mock_client.rerank.return_value = mock_result

    with (
        patch("app.core.reranker.settings") as mock_settings,
        patch("app.core.reranker._get_client", return_value=mock_client),
    ):
        mock_settings.cohere_api_key = "test-cohere-key"
        result = await rerank("hybrid search", docs, top_n=2)

    assert len(result) == 2
    # Cohere put C first — verify the reordering happened
    assert result[0]["chunk_id"] == "C"
    assert result[1]["chunk_id"] == "A"
    # Scores should be updated to Cohere's relevance scores
    assert result[0]["score"] == 0.95
    assert result[1]["score"] == 0.80


@pytest.mark.asyncio
async def test_rerank_top_n_limits_output():
    docs = [make_doc(f"doc{i}") for i in range(10)]

    with patch("app.core.reranker.settings") as mock_settings:
        mock_settings.cohere_api_key = ""
        result = await rerank("query", docs, top_n=3)

    assert len(result) == 3
