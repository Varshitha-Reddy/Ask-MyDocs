"""
Prometheus metrics for the RAG search API.

Defines counters and histograms that are updated by the API handlers.
The /metrics endpoint (api/metrics.py) exposes them in Prometheus text format.

Why Prometheus?
- Prometheus scrapes /metrics on a schedule and stores time-series data.
- Grafana reads from Prometheus to build dashboards.
- This is the industry-standard way to monitor production APIs.
"""
from prometheus_client import Counter, Histogram

# Total searches, split by whether the result came from cache
SEARCHES_TOTAL = Counter(
    "rag_searches_total",
    "Total number of search requests",
    labelnames=["cache_status"],   # label values: 'hit' or 'miss'
)

# How long /search takes end-to-end (in seconds)
# Buckets: 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s
SEARCH_LATENCY = Histogram(
    "rag_search_latency_seconds",
    "End-to-end search latency",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Total chunks written to Pinecone + Elasticsearch
INGESTED_CHUNKS_TOTAL = Counter(
    "rag_ingested_chunks_total",
    "Total number of document chunks ingested",
)

# Background ingestion jobs by outcome
INGESTION_JOBS_TOTAL = Counter(
    "rag_ingestion_jobs_total",
    "Total ingestion jobs",
    labelnames=["status"],   # label values: 'started', 'done', 'error'
)
