import asyncio

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger

from app.config import settings

# temperature=0 makes the LLM give consistent, factual answers
_llm = ChatOpenAI(
    model=settings.openai_chat_model,
    openai_api_key=settings.openai_api_key,
    temperature=0.0,
)

# The prompt template that tells the LLM how to format its answer.
# Key instruction: cite every claim using [source: filename, page: N].
_PROMPT = ChatPromptTemplate.from_template(
    """You are a precise document Q&A assistant.
Answer the question using ONLY the provided context.
After each factual claim, cite the source using the format [source: <filename>, page: <N>].
If the context does not contain the answer, say "I don't have enough information to answer this."

Context:
{context}

Question: {question}

Answer:"""
)


def _build_context(chunks: list[dict]) -> str:
    # Format each retrieved chunk so the LLM knows which file and page it came from
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        header = f"[Chunk {i} | {chunk['source_filename']}, page {chunk['page_number']}]"
        parts.append(f"{header}\n{chunk['content']}")
    return "\n\n---\n\n".join(parts)


def _call_llm_sync(context: str, question: str) -> str:
    # Synchronous call — wrapped in executor below to avoid blocking the event loop
    chain = _PROMPT | _llm
    response = chain.invoke({"context": context, "question": question})
    return response.content


async def generate_answer(question: str, chunks: list[dict]) -> str:
    context = _build_context(chunks)
    logger.debug(f"Sending {len(chunks)} chunks to LLM for: '{question[:60]}'")

    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(None, _call_llm_sync, context, question)
    return answer


# --- Streaming support (Phase 4) ---

# Separate LLM instance with streaming=True.
# We keep it separate so the non-streaming path is unaffected.
_streaming_llm = ChatOpenAI(
    model=settings.openai_chat_model,
    openai_api_key=settings.openai_api_key,
    temperature=0.0,
    streaming=True,
)


async def stream_answer(question: str, chunks: list[dict]):
    """
    Async generator that yields LLM output tokens one by one.

    LangChain's .astream() returns AIMessageChunk objects as the model produces them.
    We yield only the text content of each chunk.

    Usage:
        async for token in stream_answer(question, chunks):
            print(token, end="", flush=True)
    """
    context = _build_context(chunks)
    chain = _PROMPT | _streaming_llm

    logger.debug(f"Streaming answer for: '{question[:60]}'")
    async for chunk in chain.astream({"context": context, "question": question}):
        if chunk.content:
            yield chunk.content
