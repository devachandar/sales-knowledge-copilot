# copilot/retrieval/fusion.py
"""
Day 7, Lesson 2: Reciprocal Rank Fusion (RRF).

Each retriever gives a ranked list. RRF ignores the scores and uses only the
positions:  RRF(chunk) = sum over lists of 1 / (k + rank in that list).
A chunk that is missing from a list gets nothing from it.
"""

RRF_K = 60


def rrf(ranked_lists, k=RRF_K):
    """ranked_lists: lists of chunk_ids, best first. Returns [(chunk_id, rrf_score)], best first."""
    scores = {}
    for ranking in ranked_lists:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


if __name__ == "__main__":
    # The worked example from the lesson
    vector = ["postmortem-016", "ticket-a", "ticket-b"] + [f"v{i}" for i in range(19)] + ["api-errors#1"]
    bm25 = ["ticket-b", "ticket-a", "ticket-c", "ticket-d", "ticket-e", "ticket-f", "api-errors#1"]
    for chunk_id, score in rrf([vector, bm25])[:6]:
        print(f"  {score:.4f}  {chunk_id}")