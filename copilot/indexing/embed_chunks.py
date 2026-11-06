# copilot/indexing/embed_chunks.py
"""
Day 4, Lesson 2: embed every chunk and store it in pgvector.

Run from the project root with Postgres running:
    python -m copilot.indexing.embed_chunks
"""

import json
import os
import time

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from copilot.config import PROCESSED_DIR
from copilot.llm.embeddings import DIM, embed

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
STRATEGY = os.getenv("STRATEGY", "fixed-500")
CHUNKS_FILE = PROCESSED_DIR / f"chunks_{STRATEGY}.jsonl"
BATCH = 100   # texts per embedding request

SCHEMA = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS ip.chunks (
    chunk_id   TEXT NOT NULL,
    doc_id     TEXT NOT NULL,
    strategy   TEXT NOT NULL,
    text       TEXT NOT NULL,
    metadata   JSONB NOT NULL DEFAULT '{{}}',
    embedding  vector({DIM}) NOT NULL,
    PRIMARY KEY (chunk_id, strategy)
);
"""


def main():
    chunks = [json.loads(l) for l in open(CHUNKS_FILE, encoding="utf-8")]
    chars = sum(len(c["text"]) for c in chunks)
    print(f"{len(chunks)} chunks, {chars:,} characters (~{chars // 4:,} tokens, rough 4 chars/token)")

    # 1. Embed in batches
    start = time.perf_counter()
    vectors = []
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        vectors += embed([c["text"] for c in batch], "RETRIEVAL_DOCUMENT")
        print(f"  embedded {len(vectors)}/{len(chunks)}")
    print(f"embedding took {time.perf_counter() - start:.1f}s")
    assert len(vectors) == len(chunks), "lost some embeddings"
    assert all(len(v) == DIM for v in vectors), "wrong vector size"

    # 2. Store, replacing any earlier rows for this strategy
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(SCHEMA)
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ip.chunks WHERE strategy = %s", (STRATEGY,))
            for c, v in zip(chunks, vectors):
                meta = {k: c[k] for k in c if k not in ("chunk_id", "doc_id", "strategy", "text")}
                cur.execute(
                    "INSERT INTO ip.chunks (chunk_id, doc_id, strategy, text, metadata, embedding) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (c["chunk_id"], c["doc_id"], STRATEGY, c["text"], json.dumps(meta), v),
                )
        conn.commit()

        # 3. Check what's stored
        n, docs = conn.execute(
            "SELECT count(*), count(DISTINCT doc_id) FROM ip.chunks WHERE strategy = %s", (STRATEGY,)
        ).fetchone()
        print(f"\nstored {n} chunks from {docs} documents (strategy {STRATEGY})")
        row = conn.execute(
            "SELECT chunk_id, metadata->>'applies_to', metadata->'plans', vector_dims(embedding) "
            "FROM ip.chunks WHERE chunk_id = 'api/api-rate-limits#0' AND strategy = %s", (STRATEGY,)
        ).fetchone()
        print("sample row:", row)


if __name__ == "__main__":
    main()