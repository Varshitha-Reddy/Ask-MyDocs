"""Tests for the RRF fusion algorithm — this is a pure function with no external deps."""
import pytest
from app.core.fusion import reciprocal_rank_fusion


def make_doc(chunk_id: str, score: float = 1.0) -> dict:
    return {
        "chunk_id": chunk_id,
        "content": "test content",
        "source_filename": "test.pdf",
        "page_number": 1,
        "score": score,
    }


def test_doc_in_both_lists_ranks_highest():
    # Doc "A" appears at rank 0 in both lists — should get the highest combined score
    list1 = [make_doc("A"), make_doc("B"), make_doc("C")]
    list2 = [make_doc("A"), make_doc("D"), make_doc("E")]

    results = reciprocal_rank_fusion([list1, list2], top_n=5)
    assert results[0]["chunk_id"] == "A"


def test_all_unique_docs_appear_in_results():
    # When there's no overlap, all 4 unique docs should still appear
    list1 = [make_doc("A"), make_doc("B")]
    list2 = [make_doc("C"), make_doc("D")]

    results = reciprocal_rank_fusion([list1, list2], top_n=10)
    result_ids = {r["chunk_id"] for r in results}
    assert result_ids == {"A", "B", "C", "D"}


def test_empty_lists_return_empty():
    results = reciprocal_rank_fusion([[], []], top_n=5)
    assert results == []


def test_one_empty_list_still_works():
    list1 = [make_doc("A"), make_doc("B")]
    list2 = []

    results = reciprocal_rank_fusion([list1, list2], top_n=5)
    assert len(results) == 2
    assert results[0]["chunk_id"] == "A"


def test_different_length_lists():
    list1 = [make_doc("A"), make_doc("B"), make_doc("C")]
    list2 = [make_doc("D")]

    results = reciprocal_rank_fusion([list1, list2], top_n=10)
    assert len(results) == 4


def test_top_n_limits_output():
    list1 = [make_doc(f"doc{i}") for i in range(10)]
    list2 = [make_doc(f"doc{i}") for i in range(5, 15)]

    results = reciprocal_rank_fusion([list1, list2], top_n=5)
    assert len(results) == 5


def test_rrf_scores_are_positive():
    list1 = [make_doc("A"), make_doc("B")]
    list2 = [make_doc("A")]

    results = reciprocal_rank_fusion([list1, list2], top_n=3)
    for r in results:
        assert r["score"] > 0


def test_overlap_doc_scores_higher_than_single_list_doc():
    # "A" is in both lists; "B" is only in list1. "A" should score higher.
    list1 = [make_doc("A"), make_doc("B")]
    list2 = [make_doc("A"), make_doc("C")]

    results = reciprocal_rank_fusion([list1, list2], top_n=3)
    scores = {r["chunk_id"]: r["score"] for r in results}
    assert scores["A"] > scores["B"]
    assert scores["A"] > scores["C"]
