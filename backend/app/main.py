from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import health, ingest, metrics, search, stream
from app.config import settings

app = FastAPI(
    title="RAG Hybrid Search",
    description="Semantic + keyword search with LLM-generated cited answers.",
    version="0.1.0",
)

# Allow the React dev server (port 5173) and any deployed frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(stream.router, prefix="/search", tags=["search"])   # adds POST /search/stream
app.include_router(metrics.router, tags=["observability"])              # adds GET /metrics


@app.on_event("startup")
async def startup_event():
    logger.info("RAG Hybrid Search API starting up...")
    # Create the Elasticsearch index if it doesn't exist yet.
    # Wrapped in try/except so the app still starts if ES isn't ready yet.
    try:
        from app.core.es_client import create_index_if_not_exists
        create_index_if_not_exists()
        logger.info("Elasticsearch index ready")
    except Exception as e:
        logger.warning(f"Elasticsearch not available at startup: {e}")
