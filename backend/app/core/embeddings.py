import asyncio

from langchain_openai import OpenAIEmbeddings
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

# Initialize once at module load — reused for every embedding call
_embeddings_model = OpenAIEmbeddings(
    model=settings.openai_embedding_model,
    openai_api_key=settings.openai_api_key,
)


# Retry up to 3 times with exponential back-off (1s, 2s, 4s) if OpenAI is slow
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def get_embedding(text: str) -> list[float]:
    # OpenAI SDK is synchronous — run it in a thread so it doesn't block the event loop
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(
        None, _embeddings_model.embed_query, text
    )
    return embedding


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    # Batch embedding is more cost-efficient than calling embed_query one by one
    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(
        None, _embeddings_model.embed_documents, texts
    )
    logger.debug(f"Embedded batch of {len(texts)} texts")
    return embeddings
