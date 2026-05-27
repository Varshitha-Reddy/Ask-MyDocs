"""
Ingestion API — POST /ingest and GET /ingest/status/{job_id}

Phase 4 upgrade: ingestion now runs as a background task.
- POST /ingest returns a job_id immediately (no waiting).
- The actual chunking + embedding + indexing happens in the background.
- Client polls GET /ingest/status/{job_id} to check progress.

Why background tasks?
- Large PDFs can take 30-60 seconds to ingest.
- Blocking the HTTP request for that long times out browsers and proxies.
- BackgroundTasks lets us respond in <100ms and do the work asynchronously.
"""
import os
import tempfile
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, File, Header, HTTPException, UploadFile
from loguru import logger

from app.core.job_store import create_job, get_job, update_job
from app.ingestion.pipeline import run_ingestion_pipeline
from app.models.schemas import IngestJobResponse, IngestStatusResponse
from app.utils.metrics import INGESTED_CHUNKS_TOTAL, INGESTION_JOBS_TOTAL

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


async def _background_ingest(
    job_id: str, tmp_path: str, original_filename: str, tenant_id: str
) -> None:
    """
    Runs after the HTTP response is already sent.
    Updates job status in Redis so the client can poll for progress.
    """
    await update_job(job_id, status="processing")
    INGESTION_JOBS_TOTAL.labels(status="started").inc()

    try:
        result = await run_ingestion_pipeline(tmp_path, original_filename, tenant_id)

        await update_job(
            job_id,
            status="done",
            chunks_ingested=result.ingested,
            finished_at=datetime.utcnow().isoformat(),
        )
        INGESTION_JOBS_TOTAL.labels(status="done").inc()
        INGESTED_CHUNKS_TOTAL.inc(result.ingested)
        logger.info(f"[{job_id}] Background ingestion done: {result.ingested} chunks")

    except Exception as e:
        await update_job(
            job_id,
            status="error",
            error=str(e),
            finished_at=datetime.utcnow().isoformat(),
        )
        INGESTION_JOBS_TOTAL.labels(status="error").inc()
        logger.error(f"[{job_id}] Background ingestion failed: {e}")

    finally:
        # Clean up temp file here (not in the request handler) because the
        # background task still needs it after the response is sent
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("", response_model=IngestJobResponse, status_code=202)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    # X-Tenant-ID header isolates data between organisations.
    # Defaults to "default" so single-tenant usage requires no changes.
    x_tenant_id: str = Header(default="default"),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Allowed: {ALLOWED_EXTENSIONS}",
        )

    job_id = str(uuid.uuid4())
    logger.info(
        f"[{job_id}] Accepted '{file.filename}' for tenant '{x_tenant_id}'"
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    await create_job(job_id, file.filename)
    background_tasks.add_task(_background_ingest, job_id, tmp_path, file.filename, x_tenant_id)

    return IngestJobResponse(job_id=job_id, filename=file.filename, status="pending")


@router.get("/status/{job_id}", response_model=IngestStatusResponse)
async def get_ingest_status(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job
