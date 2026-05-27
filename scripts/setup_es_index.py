"""
One-time setup script: creates the Elasticsearch index with the correct field mappings.
Run this before ingesting any documents:
    python scripts/setup_es_index.py
"""
import os
from elasticsearch import Elasticsearch

ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_INDEX = os.getenv("ES_INDEX", "documents")

es = Elasticsearch(ES_HOST)

# The 'english' analyzer is important — it stems words (search -> search, searching -> search)
# so BM25 matches "searching" even if the doc says "search"
MAPPING = {
    "mappings": {
        "properties": {
            "chunk_id":        {"type": "keyword"},
            "content":         {"type": "text", "analyzer": "english"},
            "source_filename": {"type": "keyword"},
            "page_number":     {"type": "integer"},
            "chunk_index":     {"type": "integer"},
            "tenant_id":       {"type": "keyword"},
            "ingested_at":     {"type": "date"},
        }
    }
}

if es.indices.exists(index=ES_INDEX):
    print(f"Index '{ES_INDEX}' already exists — skipping.")
else:
    es.indices.create(index=ES_INDEX, mappings=MAPPING["mappings"])
    print(f"Created index '{ES_INDEX}' successfully.")
