"""Tests for the document chunker — pure logic, no external services needed."""
import pytest
from langchain.schema import Document
from app.ingestion.chunker import chunk_documents


def make_doc(text: str, page: int = 0) -> Document:
    return Document(page_content=text, metadata={"page": page})


def test_chunks_are_created():
    docs = [make_doc("Hello world. " * 30)]
    chunks = chunk_documents(docs, "test.pdf")
    assert len(chunks) > 0


def test_source_filename_is_preserved():
    docs = [make_doc("Some content. " * 50)]
    chunks = chunk_documents(docs, "my_report.pdf")
    for chunk in chunks:
        assert chunk.source_filename == "my_report.pdf"


def test_page_numbers_are_one_indexed():
    # PyPDF returns page=0 for page 1. The chunker should convert to 1-indexed.
    docs = [make_doc("Page one content " * 20, page=0)]
    chunks = chunk_documents(docs, "test.pdf")
    for chunk in chunks:
        assert chunk.page_number == 1  # 0 + 1 = 1


def test_multiple_pages_have_different_page_numbers():
    docs = [
        make_doc("Page one content " * 20, page=0),
        make_doc("Page two content " * 20, page=1),
    ]
    chunks = chunk_documents(docs, "test.pdf")
    page_nums = {c.page_number for c in chunks}
    assert 1 in page_nums
    assert 2 in page_nums


def test_chunk_indexes_are_sequential():
    # Chunk indexes should be 0, 1, 2, ... with no gaps
    docs = [make_doc("Word " * 300)]
    chunks = chunk_documents(docs, "test.pdf")
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_whitespace_only_chunks_are_skipped():
    docs = [make_doc("   \n\n   \t  ")]
    chunks = chunk_documents(docs, "empty.txt")
    assert len(chunks) == 0


def test_multiple_docs_produce_chunks_from_all():
    docs = [
        make_doc("First document text " * 30, page=0),
        make_doc("Second document text " * 30, page=1),
    ]
    chunks = chunk_documents(docs, "multi.pdf")
    # Should have chunks from both documents — pages 1 and 2 both present
    page_nums = {c.page_number for c in chunks}
    assert len(page_nums) >= 2
