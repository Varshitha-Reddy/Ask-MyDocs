import uuid

from loguru import logger

from app.core.embeddings import get_embeddings_batch
from app.core.es_client import index_chunks
from app.core.pinecone_client import upsert_chunks
from app.ingestion.chunker import chunk_documents
from app.ingestion.loaders import load_document
from app.models.schemas import IngestResponse


async def run_ingestion_pipeline(
    file_path: str,
    original_filename: str,
    tenant_id: str = "default",  # Phase 4.4: which tenant owns this document
) -> IngestResponse:
    """
    Full ingestion pipeline:
    1. Load file → LangChain Documents
    2. Split into chunks
    3. Embed in batches of 100
    4. Store in Pinecone + Elasticsearch (both tagged with tenant_id)
    """
    document_id = str(uuid.uuid4())
    logger.info(
        f"[{document_id}] Starting ingestion for '{original_filename}' (tenant: {tenant_id})"
    )

    docs = load_document(file_path, original_filename)
    chunks = chunk_documents(docs, original_filename)

    # Stamp every chunk with the tenant_id before storing anywhere
    for chunk in chunks:
        chunk.tenant_id = tenant_id

    if not chunks:
        logger.warning(f"[{document_id}] No chunks produced from '{original_filename}'")
        return IngestResponse(ingested=0, document_id=document_id, filename=original_filename)

    all_texts = [chunk.content for chunk in chunks]
    all_embeddings = []
    batch_size = 100

    for i in range(0, len(all_texts), batch_size):
        batch = all_texts[i : i + batch_size]
        embeddings = await get_embeddings_batch(batch)
        all_embeddings.extend(embeddings)
        logger.debug(f"[{document_id}] Embedded batch {i // batch_size + 1}")

    await upsert_chunks(chunks, all_embeddings)  # → Pinecone
    await index_chunks(chunks)                    # → Elasticsearch

    logger.info(
        f"[{document_id}] Ingestion complete: {len(chunks)} chunks for "
        f"'{original_filename}' (tenant: {tenant_id})"
    )
    return IngestResponse(
        ingested=len(chunks),
        document_id=document_id,
        filename=original_filename,
    )
