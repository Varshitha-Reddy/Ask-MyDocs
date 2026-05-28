"""
Ingestion API — POST /ingest and GET /ingest/status/{job_id}

Production upgrade: uses Celery instead of FastAPI BackgroundTasks.

Why Celery?
- BackgroundTasks: task lives in RAM. Server crashes → task lost, job stuck
  at "pending" forever.
- Celery: task is pushed to Redis queue before response is sent. If the
  worker or server crashes, the task remains in Redis and gets picked up
  when the worker restarts. Nothing is lost.
"""
import os
import tempfile
import uuid

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from loguru import logger

from app.core.job_store import create_job, get_job
from app.models.schemas import IngestJobResponse, IngestStatusResponse
from app.tasks.ingest_task import ingest_document_task

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


@router.post("", response_model=IngestJobResponse, status_code=202)
async def ingest_document(
    file: UploadFile = File(...),
    x_tenant_id: str = Header(default="default"),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Allowed: {ALLOWED_EXTENSIONS}",
        )

    job_id = str(uuid.uuid4())
    logger.info(f"[{job_id}] Accepted '{file.filename}' for tenant '{x_tenant_id}'")

    # Save to temp file — Celery worker runs in a separate process and needs
    # the file on disk (can't share memory with the FastAPI process)
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Create job record in Redis BEFORE dispatching the task.
    # This way /status always returns something even if the worker is slow to start.
    await create_job(job_id, file.filename)

    # Push task to Celery queue (stored in Redis).
    # .delay() is shorthand for .apply_async() — sends task to the queue immediately.
    # The worker picks it up independently — even if this server process restarts.
    ingest_document_task.delay(job_id, tmp_path, file.filename, x_tenant_id)

    logger.info(f"[{job_id}] Task pushed to Celery queue")

    return IngestJobResponse(job_id=job_id, filename=file.filename, status="pending")


@router.get("/status/{job_id}", response_model=IngestStatusResponse)
async def get_ingest_status(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job
