# src2/answer.py
"""
Day 4, Lesson 4: the full RAG pipeline. Search picks the evidence, grounded_v2 answers.

Run from src2/:
    python answer.py
"""

import time

from day2_grounded import PROMPT_VERSION, ask, check
from retrieve import search

PRICE_IN, PRICE_OUT = 0.30, 2.50   # USD per 1M tokens, flash-lite (Day 1)


def rag_answer(question, k=5, strategy="fixed-500"):
    results, t = search(question, k=k, strategy=strategy)
    evidence = [{"id": r["chunk_id"], "text": r["text"]} for r in results]

    t0 = time.perf_counter()
    result, usage = ask(question, evidence)
    llm_ms = (time.perf_counter() - t0) * 1000

    tin = usage.get("promptTokenCount", 0)
    tout = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
    return {
        "result": result,
        "retrieved": results,
        "problems": check(result, evidence),
        "timings": {**t, "llm_ms": llm_ms},
        "tokens_in": tin,
        "tokens_out": tout,
        "cost": tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT,
    }


if __name__ == "__main__":
    print(f"prompt: {PROMPT_VERSION}")
    for q in [
        "Has BUG-2310-02 been fixed yet?",
        "How far back does the audit log go for Enterprise customers?",
        "What does error IP-4090 mean?",
    ]:
        out = rag_answer(q)
        r, t = out["result"], out["timings"]
        print(f"\n{'=' * 70}\nQ: {q}")
        print("retrieved:", [x["chunk_id"] for x in out["retrieved"]])
        print(f"status: {r['status']}")
        print(f"answer: {r['answer']}")
        print(f"cited:  {r['citations']}")
        print(f"checks: {'OK' if not out['problems'] else out['problems']}")
        print(f"time: embed {t['embed_ms']:.0f} + db {t['db_ms']:.0f} + llm {t['llm_ms']:.0f} ms"
              f" | tokens {out['tokens_in']} in / {out['tokens_out']} out | ${out['cost']:.5f}")