from typing import List, Optional

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    ingested: int       # Number of chunks indexed
    document_id: str    # UUID assigned to this ingestion job
    filename: str       # Original filename


# --- Phase 4: Background ingestion schemas ---

class IngestJobResponse(BaseModel):
    """Returned immediately when a file is accepted for background ingestion."""
    job_id: str
    filename: str
    status: str         # Always "pending" at this point


class IngestStatusResponse(BaseModel):
    """Returned when polling GET /ingest/status/{job_id}."""
    job_id: str
    status: str                       # pending | processing | done | error
    filename: str
    chunks_ingested: int = 0
    error: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language question")
    top_k: int = Field(default=5, ge=1, le=20, description="Max number of source chunks to return")


class SourceChunk(BaseModel):
    chunk_id: str
    content: str
    source_filename: str
    page_number: int
    score: float         # RRF score after fusion (higher = more relevant)


class SearchResponse(BaseModel):
    answer: str              # LLM-generated cited answer
    sources: List[SourceChunk]
    cached: bool             # True if this result was served from Redis
    latency_ms: int          # End-to-end latency in milliseconds
