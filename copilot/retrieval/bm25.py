# copilot/retrieval/bm25.py
"""
Day 7, Lesson 1: BM25 keyword search, written by hand.

The index lives in memory. It is built from the chunks file in well under a
second, so there is nothing to store: rebuild it whenever the chunks change.

Run from the project root to try a few queries:
    python -m copilot.retrieval.bm25
"""

import json
import math
import re
from collections import Counter, defaultdict
from copilot.config import PROCESSED_DIR

CHUNKS = PROCESSED_DIR
K1, B = 1.2, 0.75          # the standard BM25 settings

# A token is letters/digits, optionally joined by - _ . / { } so that codes stay whole:
#   bug-2310-02   ip-4220   x-ratelimit-reset   ip_test_   2.3.1
#   /v2/payments/{payment_id}   client.invoices.void
TOKEN_RE = re.compile(r"/?[a-z0-9{}]+(?:[-_./][a-z0-9{}]*)*")
SPLIT_RE = re.compile(r"[-_./{}]+")
STOPWORDS = set("""a an and are as at be by can do does for from has have how i if in is it its
of on or our so that the their them they this to was we what when which who why will with you your""".split())


def tokenize(text):
    """Whole tokens, plus their parts, so 'rate-limit' still matches 'rate limit'.

    'BUG-2310-02' -> ['bug-2310-02', 'bug', '2310', '02']
    The whole token is rare, so its IDF is high and it dominates the score.
    The parts are common, so they add a little and never decide the ranking.
    """
    out = []
    for tok in TOKEN_RE.findall(text.lower()):
        tok = tok.strip("./")              # sentence-ending periods and leading slashes
        if not tok or tok in STOPWORDS:
            continue
        out.append(tok)
        parts = [p for p in SPLIT_RE.split(tok) if p]
        if len(parts) > 1:
            out.extend(p for p in parts if p not in STOPWORDS)
    return out


class BM25:
    def __init__(self, chunks):
        self.chunks = chunks
        self.tf = []                          # per chunk: Counter(token -> count)
        self.postings = defaultdict(list)     # token -> [chunk index, ...]  (the inverted index)
        for i, c in enumerate(chunks):
            counts = Counter(tokenize(c["text"]))
            self.tf.append(counts)
            for tok in counts:
                self.postings[tok].append(i)
        self.length = [sum(c.values()) for c in self.tf]
        self.avg_len = sum(self.length) / len(self.length)
        n = len(chunks)
        self.idf = {tok: math.log((n - len(ids) + 0.5) / (len(ids) + 0.5) + 1)
                    for tok, ids in self.postings.items()}

    def score(self, query_tokens, i):
        tf, norm = self.tf[i], K1 * (1 - B + B * self.length[i] / self.avg_len)
        return sum(self.idf[t] * tf[t] * (K1 + 1) / (tf[t] + norm) for t in query_tokens if t in tf)

    def search(self, question, k=5):
        q = set(tokenize(question))
        # Only chunks that contain at least one query token can score above 0.
        candidates = {i for t in q for i in self.postings.get(t, [])}
        scored = sorted(((self.score(q, i), i) for i in candidates), reverse=True)[:k]
        return [{**self.chunks[i], "score": s} for s, i in scored]

    def explain(self, question, chunk_index):
        """Which tokens gave this chunk its score. BM25 is fully explainable."""
        q = set(tokenize(question))
        tf, norm = self.tf[chunk_index], K1 * (1 - B + B * self.length[chunk_index] / self.avg_len)
        parts = {t: self.idf[t] * tf[t] * (K1 + 1) / (tf[t] + norm) for t in q if t in tf}
        return sorted(parts.items(), key=lambda x: -x[1])


def load_index(strategy="structure-aware"):
    path = CHUNKS / f"chunks_{strategy}.jsonl"
    chunks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return BM25(chunks)


if __name__ == "__main__":
    for sample in ["BUG-2310-02", "rate-limit headers", "/v2/payments/{payment_id}", "client.invoices.void()", "On 2.3.1."]:
        print(f"{sample!r:30s} -> {tokenize(sample)}")

    index = load_index()
    print(f"\n{len(index.chunks)} chunks, {len(index.postings)} distinct tokens, "
          f"average chunk length {index.avg_len:.0f} tokens")
    for tok in ["ip-4030", "ip-5030", "retry", "invoice", "bug-2310-02"]:
        print(f"  IDF {tok:14s} {index.idf.get(tok, 0):5.2f}   in {len(index.postings.get(tok, []))} chunks")

    for question in ["A call failed with IP-4030. Should the integration retry it?",
                     "Has BUG-2310-02 been fixed yet?"]:
        print(f"\nQ: {question}")
        for r in index.search(question):
            i = next(j for j, c in enumerate(index.chunks) if c["chunk_id"] == r["chunk_id"])
            top = ", ".join(f"{t} {s:.2f}" for t, s in index.explain(question, i)[:3])
            print(f"  {r['score']:6.2f}  {r['source_type']:16s} {r['chunk_id'][:45]:45s} [{top}]")