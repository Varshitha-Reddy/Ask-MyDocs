"""
Tests for the background ingestion API.
The pipeline and job store are mocked so no real services are needed.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.mark.asyncio
async def test_ingest_returns_202_and_job_id():
    # Mock the job store and background pipeline so nothing real runs
    with (
        patch("app.api.ingest.create_job", new_callable=AsyncMock),
        patch("app.api.ingest._background_ingest", new_callable=AsyncMock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/ingest",
                files={"file": ("test.txt", b"Hello world content", "text/plain")},
            )

    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    assert body["status"] == "pending"
    assert body["filename"] == "test.txt"


@pytest.mark.asyncio
async def test_ingest_rejects_unsupported_file_type():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/ingest",
            files={"file": ("script.py", b"print('hello')", "text/plain")},
        )

    assert response.status_code == 400
    assert ".py" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ingest_status_returns_job():
    fake_job = {
        "job_id": "abc-123",
        "status": "done",
        "filename": "doc.pdf",
        "chunks_ingested": 10,
        "error": None,
        "started_at": "2024-01-01T00:00:00",
        "finished_at": "2024-01-01T00:00:05",
    }

    with patch("app.api.ingest.get_job", new_callable=AsyncMock, return_value=fake_job):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ingest/status/abc-123")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["chunks_ingested"] == 10


@pytest.mark.asyncio
async def test_ingest_status_404_for_unknown_job():
    with patch("app.api.ingest.get_job", new_callable=AsyncMock, return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ingest/status/nonexistent-job")

    assert response.status_code == 404
