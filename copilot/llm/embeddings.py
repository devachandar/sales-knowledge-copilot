# copilot/llm/embeddings.py
"""
Day 3, Lesson 1: what embeddings capture, and what they miss.

Run from the project root:
    python -m copilot.llm.embeddings
"""

import math

from copilot.llm.client import API_KEY, post_with_retry

EMBED_MODEL = "gemini-embedding-001"
DIM = 768
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:batchEmbedContents"


def embed(texts, task_type):
    body = {"requests": [{
        "model": f"models/{EMBED_MODEL}",
        "content": {"parts": [{"text": t}]},
        "taskType": task_type,
        "outputDimensionality": DIM,
    } for t in texts]}
    resp = post_with_retry(URL, {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}, body)
    return [e["values"] for e in resp.json()["embeddings"]]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


DOCS = [
    "Sent invoices cannot be deleted. Void them instead so your records stay complete.",
    "Draft invoices can be deleted at any time.",
    "API rate limits per minute: Starter 60, Professional 300, Enterprise 1,000.",
    "BUG-2310-01: auto-match does not convert foreign-currency transactions.",
    "BUG-2310-02: invoices with more than 25 line items export as a single-page PDF.",
]

QUERIES = [
    "How do I cancel an invoice I already emailed?",   # paraphrase, few shared words
    "How many API calls can a Professional customer make?",
    "Is BUG-2310-02 fixed?",                            # exact code
    "Why is my euro bank transaction not matching?",    # meaning, no code
]


if __name__ == "__main__":
    doc_vecs = embed(DOCS, "RETRIEVAL_DOCUMENT")
    query_vecs = embed(QUERIES, "RETRIEVAL_QUERY")
    print(f"each vector has {len(doc_vecs[0])} numbers; first 5: {[round(x, 3) for x in doc_vecs[0][:5]]}\n")

    for q, qv in zip(QUERIES, query_vecs):
        scores = sorted(((cosine(qv, dv), d) for d, dv in zip(DOCS, doc_vecs)), reverse=True)
        print(f"Q: {q}")
        for s, d in scores:
            print(f"   {s:.3f}  {d[:70]}")
        gap = scores[0][0] - scores[1][0]
        print(f"   gap between #1 and #2: {gap:.3f}\n")