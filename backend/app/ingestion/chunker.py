from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from app.models.document import Chunk

# RecursiveCharacterTextSplitter tries the separators in order:
# first split on double newlines (paragraphs), then single newlines, then spaces.
# This keeps semantically related sentences together where possible.
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       # characters per chunk
    chunk_overlap=50,     # overlap to preserve context across chunk boundaries
    length_function=len,
    separators=["\n\n", "\n", " ", ""],
)


def chunk_documents(docs: list[Document], source_filename: str) -> list[Chunk]:
    """
    Split LangChain Documents into smaller Chunk objects ready for embedding.
    Returns chunks in order, each with a sequential chunk_index.
    """
    chunks = []
    chunk_index = 0

    for doc in docs:
        text_pieces = _splitter.split_text(doc.page_content)

        for text in text_pieces:
            # Skip chunks that are only whitespace — they add noise to the index
            if not text.strip():
                continue

            # PyPDFLoader sets metadata["page"] as 0-indexed — convert to 1-indexed for display
            page_number = doc.metadata.get("page", 0) + 1

            chunks.append(
                Chunk(
                    content=text,
                    source_filename=source_filename,
                    page_number=page_number,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    logger.info(f"Chunker produced {len(chunks)} chunks from '{source_filename}'")
    return chunks
