"""
Seed script: uploads sample text to test the full ingestion + search pipeline.
Run after the backend is up:
    python scripts/seed_sample_docs.py
"""
import os
import tempfile
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")

# A few paragraphs covering RRF, hybrid search, and the tech stack.
# Good for verifying that searches about these topics return relevant results.
SAMPLE_TEXT = """\
Reciprocal Rank Fusion (RRF) is a method for combining multiple ranked result lists.
It was introduced by Cormack, Clarke, and Buettcher in 2009 at SIGIR.
The key insight: a document's position in a ranked list matters more than its raw score.

RRF score = sum of 1/(k + rank) for each list the document appears in.
The constant k (typically 60) controls how much early ranks are boosted over late ranks.
Documents appearing in multiple lists receive a higher combined score.

Hybrid search combines dense vector retrieval (semantic) with sparse BM25 keyword matching.
This captures both semantic meaning and exact keyword matches simultaneously.
Research shows hybrid search outperforms either method alone by 10-25% on standard benchmarks.

Elasticsearch uses BM25 as its default relevance scoring algorithm.
BM25 improves on TF-IDF by normalizing for document length.
It is particularly effective for exact keyword matches and rare or domain-specific terms.

Pinecone is a managed vector database optimized for approximate nearest-neighbor search.
Vector search finds semantically similar documents even when they use completely different words.
OpenAI's text-embedding-3-small model produces 1536-dimensional vectors.

Redis caching stores query results so repeated identical searches are returned instantly.
Cache hits for this system typically complete in under 10 milliseconds.
Cache keys are SHA-256 hashes of the query string, making them collision-resistant.
"""


def seed():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_TEXT)
        tmp_path = f.name

    try:
        with open(tmp_path, "rb") as f:
            resp = requests.post(
                f"{API_URL}/ingest",
                files={"file": ("sample_docs.txt", f, "text/plain")},
                timeout=60,
            )

        if resp.status_code == 200:
            data = resp.json()
            print(f"Seeded successfully: {data['ingested']} chunks indexed (doc_id={data['document_id']})")
        else:
            print(f"Seed failed: HTTP {resp.status_code} — {resp.text}")
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    seed()
