import os

from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from loguru import logger


def load_document(file_path: str, original_filename: str) -> list[Document]:
    """
    Load a file and return a list of LangChain Document objects.
    Each Document has .page_content (the text) and .metadata (source info).
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        # PyPDFLoader splits by page and adds {"page": N} to metadata (0-indexed)
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        for doc in docs:
            doc.metadata["source_filename"] = original_filename
        logger.info(f"Loaded PDF '{original_filename}': {len(docs)} pages")

    elif ext in (".txt", ".md"):
        # TextLoader reads the whole file as one Document
        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
        for doc in docs:
            doc.metadata["source_filename"] = original_filename
            doc.metadata["page"] = 0  # Text files don't have pages
        logger.info(f"Loaded text file '{original_filename}'")

    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    return docs
