"""
RAGAS evaluation script (Phase 4.5)

Measures retrieval and answer quality using four automatic metrics:
  - faithfulness       : are claims in the answer supported by the retrieved chunks?
  - answer_relevancy   : does the answer actually address the question?
  - context_precision  : are the retrieved chunks relevant to the question?
  - context_recall     : did we retrieve all necessary information? (needs ground truths)

RAGAS uses an LLM internally (same OpenAI key as the app) to evaluate these.
No human-labelled test set is needed for faithfulness and answer_relevancy.
For context_recall you need ground_truths (expected answer per question).

Usage:
    export OPENAI_API_KEY=sk-...
    python scripts/eval_ragas.py

Output:
    Prints a table of metric scores and saves eval_results.json in the current dir.
"""
import json
import os
import sys

import requests
from datasets import Dataset

# Add backend to path so we can import app config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

API_URL = os.getenv("API_URL", "http://localhost:8000")
TENANT_ID = os.getenv("EVAL_TENANT_ID", "default")

# ---------------------------------------------------------------------------
# Test questions — edit these to match documents you have ingested
# ---------------------------------------------------------------------------
TEST_CASES = [
    {
        "question": "What is Reciprocal Rank Fusion and how does it work?",
        "ground_truth": (
            "Reciprocal Rank Fusion (RRF) combines multiple ranked lists by scoring each "
            "document as the sum of 1/(k + rank) across all lists. Documents appearing in "
            "multiple lists receive a higher combined score."
        ),
    },
    {
        "question": "How does hybrid search improve retrieval quality?",
        "ground_truth": (
            "Hybrid search combines semantic vector search with BM25 keyword matching. "
            "Semantic search handles paraphrasing while BM25 handles exact terms. "
            "Together they outperform either method alone."
        ),
    },
    {
        "question": "What is Elasticsearch used for in this system?",
        "ground_truth": (
            "Elasticsearch provides BM25 keyword search. It is particularly good at "
            "matching exact terms, product codes, and rare domain-specific words."
        ),
    },
]


def call_search(question: str) -> dict:
    resp = requests.post(
        f"{API_URL}/search",
        json={"query": question, "top_k": 5},
        headers={"X-Tenant-ID": TENANT_ID},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def build_ragas_dataset(test_cases: list[dict]) -> Dataset:
    questions, answers, contexts, ground_truths = [], [], [], []

    for tc in test_cases:
        print(f"  Querying: {tc['question'][:60]}...")
        try:
            result = call_search(tc["question"])
        except Exception as e:
            print(f"  SKIP (API error): {e}")
            continue

        questions.append(tc["question"])
        answers.append(result["answer"])
        # RAGAS expects contexts as a list of strings (one per retrieved chunk)
        contexts.append([src["content"] for src in result["sources"]])
        ground_truths.append([tc["ground_truth"]])  # RAGAS expects a list of strings

    return Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truths": ground_truths,
        }
    )


def run_evaluation():
    # Import here so the script fails clearly if ragas isn't installed
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    print(f"Building evaluation dataset from {len(TEST_CASES)} test cases...")
    dataset = build_ragas_dataset(TEST_CASES)

    if len(dataset) == 0:
        print("No results to evaluate — is the backend running and are documents ingested?")
        return

    print(f"\nRunning RAGAS evaluation on {len(dataset)} questions...")
    scores = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )

    print("\n--- RAGAS Evaluation Results ---")
    for metric, value in scores.items():
        print(f"  {metric:<25} {value:.4f}")

    # Save to file for the benchmark notebook
    output_path = "eval_results.json"
    with open(output_path, "w") as f:
        json.dump(dict(scores), f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    run_evaluation()
