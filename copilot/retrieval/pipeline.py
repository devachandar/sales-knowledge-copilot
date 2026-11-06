# copilot/retrieval/pipeline.py
"""
Day 8: one retrieval function for every version, V1 to V4.

    from pipeline import Retriever
    r = Retriever()
    chunks = r.retrieve("Has BUG-2310-02 been fixed yet?", version="V4")

Every later day (answers, evals, the agent) calls this, so a change to
retrieval happens in one place, and old versions stay runnable.
"""

import os

import numpy as np
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from copilot.retrieval.authority import diversify, with_authority
from copilot.retrieval.bm25 import load_index
from copilot.llm.embeddings import embed
from copilot.retrieval.metadata import apply_mode
from copilot.retrieval.query_filters import rule_filters
from copilot.retrieval.fusion import rrf

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
K, FETCH, DEPTH = 5, 50, 20
RERANKER = os.getenv("RERANKER", "cross-encoder/ms-marco-MiniLM-L-6-v2")

VERSIONS = {
    "V1": "fixed-500 chunks, vector search (Day 4)",
    "V2": "structure-aware chunks, vector search (Day 5)",
    "V3": "V2 + soft version/plan boost + no community posts (Day 6)",
    "V4": "hybrid (BM25 + vector, RRF) -> rerank top 20 -> authority -> diversity (Day 7)",
}

SQL = """
SELECT chunk_id, doc_id, text, metadata, 1 - (embedding <=> %(q)s) AS score
FROM ip.chunks WHERE strategy = %(s)s
ORDER BY embedding <=> %(q)s LIMIT %(n)s
"""


class Retriever:
    def __init__(self):
        self.conn = psycopg.connect(DATABASE_URL)
        register_vector(self.conn)
        self.index = load_index("structure-aware")
        self.chunk = {c["chunk_id"]: c for c in self.index.chunks}
        self._reranker = None

    @property
    def reranker(self):
        if self._reranker is None:              # load the model only when V4 needs it
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(RERANKER)
        return self._reranker

    def _vector(self, qvec, strategy, n):
        rows = self.conn.execute(SQL, {"q": np.array(qvec), "s": strategy, "n": n}).fetchall()
        return [{"chunk_id": r[0], "doc_id": r[1], "text": r[2], "metadata": r[3],
                 "source_type": r[3].get("source_type"), "score": float(r[4])} for r in rows]

    def retrieve(self, question, version="V4", k=K, qvec=None):
        """Top-k chunks for a question. Pass qvec to reuse an embedding you already have."""
        if qvec is None:
            qvec = embed([question], "RETRIEVAL_QUERY")[0]

        if version == "V1":
            return self._vector(qvec, "fixed-500", k)

        if version == "V2":
            return self._vector(qvec, "structure-aware", k)

        if version == "V3":
            candidates = self._vector(qvec, "structure-aware", FETCH)
            return apply_mode(candidates, rule_filters(question), "soft+no-community")[:k]

        if version == "V4":
            vec = [c["chunk_id"] for c in self._vector(qvec, "structure-aware", FETCH)]
            lex = [c["chunk_id"] for c in self.index.search(question, k=FETCH)]
            ids = [cid for cid, _ in rrf([vec, lex])][:DEPTH]
            scores = [float(s) for s in self.reranker.predict([(question, self.chunk[c]["text"]) for c in ids])]
            ranked = diversify(with_authority(ids, scores, self.chunk), self.chunk)
            score_of = dict(zip(ids, scores))
            return [{**self.chunk[c], "score": score_of[c]} for c in ranked[:k]]

        raise ValueError(f"unknown version {version!r}; choose from {list(VERSIONS)}")

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    r = Retriever()
    q = "A call failed with IP-4030. Should the integration retry it?"
    for v, desc in VERSIONS.items():
        print(f"\n{v}: {desc}")
        for c in r.retrieve(q, version=v):
            print(f"  {c['score']:7.3f}  {c['source_type']:16s} {c['chunk_id']}")
    r.close()