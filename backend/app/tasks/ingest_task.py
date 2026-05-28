"""
Celery task for document ingestion.

Key production features:
- max_retries=3: if the task fails (OpenAI down, Pinecone error), it retries
  automatically with exponential backoff — no manual intervention needed.
- task_acks_late=True (set in celery_app.py): task is only removed from the
  queue AFTER it completes. If the worker crashes mid-way, another worker
  picks it up.
- bind=True: gives us access to `self` so we can call self.retry().
"""
import asyncio
import os
from datetime import datetime

from celery import Task
from loguru import logger

from app.core.celery_app import celery_app
from app.core.job_store import update_job
from app.ingestion.pipeline import run_ingestion_pipeline
from app.utils.metrics import INGESTED_CHUNKS_TOTAL, INGESTION_JOBS_TOTAL


@celery_app.task(
    bind=True,           # gives access to self (the task instance)
    max_retries=3,       # retry up to 3 times on failure
    default_retry_delay=5,  # wait 5 seconds before first retry
    name="ingest_document",
)
def ingest_document_task(self: Task, job_id: str, tmp_path: str, filename: str, tenant_id: str):
    """
    Runs in a Celery worker process (separate from the FastAPI server).
    Uses asyncio.run() because Celery tasks are synchronous but our
    ingestion pipeline uses async/await.
    """
    logger.info(f"[{job_id}] Celery worker started ingestion for '{filename}'")

    # run_job is async — asyncio.run() bridges sync Celery → async pipeline
    asyncio.run(_run_job(self, job_id, tmp_path, filename, tenant_id))


async def _run_job(task: Task, job_id: str, tmp_path: str, filename: str, tenant_id: str):
    """Async wrapper that does the actual work and handles retries."""
    await update_job(job_id, status="processing")
    INGESTION_JOBS_TOTAL.labels(status="started").inc()

    try:
        result = await run_ingestion_pipeline(tmp_path, filename, tenant_id)

        await update_job(
            job_id,
            status="done",
            chunks_ingested=result.ingested,
            finished_at=datetime.utcnow().isoformat(),
        )
        INGESTION_JOBS_TOTAL.labels(status="done").inc()
        INGESTED_CHUNKS_TOTAL.inc(result.ingested)
        logger.info(f"[{job_id}] Ingestion done: {result.ingested} chunks")

    except Exception as e:
        logger.error(f"[{job_id}] Ingestion failed: {e}")

        # Check if we have retries left
        if task.request.retries < task.max_retries:
            # Exponential backoff: 5s, 10s, 20s between retries
            countdown = 5 * (2 ** task.request.retries)
            logger.info(f"[{job_id}] Retrying in {countdown}s (attempt {task.request.retries + 1}/{task.max_retries})")
            await update_job(job_id, status=f"retrying (attempt {task.request.retries + 1})")
            raise task.retry(exc=e, countdown=countdown)

        # All retries exhausted — mark as error
        await update_job(
            job_id,
            status="error",
            error=str(e),
            finished_at=datetime.utcnow().isoformat(),
        )
        INGESTION_JOBS_TOTAL.labels(status="error").inc()

    finally:
        # Always clean up the temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
