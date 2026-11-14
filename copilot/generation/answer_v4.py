# copilot/generation/answer_v4.py
"""
Day 10: the current full pipeline. V4 retrieval picks the evidence, grounded_v2 answers.

This is the "system under test" that the judge grades. (answer.py is the Day 4 version,
kept because evals/retrieval/chunking_baseline.py still uses it.)

Run from the project root:
    python -m copilot.generation.answer_v4
"""

import time

from copilot.generation.grounded import PROMPT_VERSION, ask, check
from copilot.llm.client import MODEL
from copilot.retrieval.pipeline import Retriever

PRICE_IN, PRICE_OUT = 0.30, 2.50   # USD per 1M tokens, flash-lite (Day 1)


def answer(question, retriever, version="V4", k=5):
    """Retrieve with `version`, answer with grounded_v2. Returns everything a judge needs."""
    t0 = time.perf_counter()
    chunks = retriever.retrieve(question, version=version, k=k)
    t1 = time.perf_counter()
    evidence = [{"id": c["chunk_id"], "text": c["text"]} for c in chunks]
    result, usage = ask(question, evidence)
    t2 = time.perf_counter()

    tin = usage.get("promptTokenCount", 0)
    tout = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
    return {
        "result": result,
        "evidence": [{**e, "doc_id": c["doc_id"], "source_type": c.get("source_type")}
                     for e, c in zip(evidence, chunks)],
        "problems": check(result, evidence),
        "config": {"retrieval": version, "prompt": PROMPT_VERSION, "model": MODEL, "k": k},
        "ms": {"retrieve": (t1 - t0) * 1000, "llm": (t2 - t1) * 1000},
        "tokens_in": tin,
        "tokens_out": tout,
        "cost": tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT,
    }


if __name__ == "__main__":
    r = Retriever()
    for q in ["Has BUG-2310-02 been fixed yet?", "Can a Starter customer use webhooks?"]:
        out = answer(q, r)
        print(f"\nQ: {q}\nstatus: {out['result']['status']}\nanswer: {out['result']['answer']}")
        print(f"cited: {out['result']['citations']}  checks: {out['problems'] or 'OK'}  ${out['cost']:.5f}")
    r.close()
