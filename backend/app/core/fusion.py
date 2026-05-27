def reciprocal_rank_fusion(
    result_lists: list[list[dict]],
    k: int = 60,
    top_n: int = 10,
) -> list[dict]:
    """
    Merge multiple ranked result lists using Reciprocal Rank Fusion (RRF).

    How it works:
    - For each document, look at its rank in every list it appears in.
    - Score = sum of 1 / (k + rank) across all lists.
    - Documents appearing in multiple lists get a score boost.
    - k=60 is the value from the original RRF paper (Cormack et al. 2009).

    Why RRF instead of averaging scores?
    - Pinecone scores (cosine similarity) and ES scores (BM25) are on totally different scales.
    - RRF only uses rank positions, so the scales don't matter.

    Args:
        result_lists: Each inner list is sorted best-first (rank 0 = best).
        k: Smoothing constant. Higher k = smaller difference between early and late ranks.
        top_n: How many merged results to return.

    Returns:
        List of result dicts sorted by RRF score, highest first.
    """
    # Accumulate RRF score per chunk_id
    rrf_scores: dict[str, float] = {}

    # Keep full doc data so we can return it in the final results
    doc_data: dict[str, dict] = {}

    for result_list in result_lists:
        for rank, doc in enumerate(result_list):
            doc_id = doc["chunk_id"]

            # 1-indexed rank: rank 0 -> 1/(k+1), rank 1 -> 1/(k+2), etc.
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)

            # First write wins — all lists should have the same content for the same chunk_id
            if doc_id not in doc_data:
                doc_data[doc_id] = doc

    # Sort all seen docs by their final RRF score, best first
    ranked_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

    # Build the output list with the RRF score replacing the original search score
    results = []
    for doc_id in ranked_ids[:top_n]:
        merged_doc = dict(doc_data[doc_id])       # copy so we don't mutate shared data
        merged_doc["score"] = round(rrf_scores[doc_id], 6)
        results.append(merged_doc)

    return results
