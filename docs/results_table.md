# Results table

Interview cheat sheet. Fill in as you go. Source of truth for the recall rows:
`data/invoicepilot/results/pipeline_v1_v4.json` (written by `python -m evals.retrieval.run_pipeline`).

**Setup for every recall number below:** corpus v2 (436 documents, structure-aware 580 chunks /
fixed-500 513 chunks), 68 questions (seed 25, hard 15, filter 10, exact 11, non-official 7), k = 5,
measured 2026-11-05 in one run.

## Versions

| Version | Recipe | Day |
|---|---|---|
| V1 | fixed-500 chunks, vector search | 4 |
| V2 | structure-aware chunks, vector search | 5 |
| V3 | V2 + soft version/plan boost + no community posts | 6 |
| V4 | hybrid (BM25 + vector, RRF k=60) -> cross-encoder rerank top 20 -> soft authority -> diversity caps | 7 |

## The table

| Metric | V1 (Day 4) | Final (V4 so far) | Where earned |
|---|---|---|---|
| recall@5 — capability | 93% | 86% | Day 5 (see note) |
| recall@5 — exact-token | 45% | **100%** | **Day 7** |
| recall@5 — tier-gated | 83% | 100% | Day 6 + Day 7 |
| recall@5 — temporal | 60% | 100% | Day 6 + Day 7 |
| recall@5 — non-official (extra) | 71% | 100% | Day 7 |
| recall@1 — all 68 questions (extra) | 40% | 79% | Days 5–7 |
| Multi-hop success | n/a | | Day 14 |
| Groundedness | | | Day 11 |
| Citation accuracy | | | Day 11 |
| False-answer rate (out-of-scope) | | | **Day 17** |
| Over-refusal rate | | | Day 17 |
| Conflict handling | n/a | | Day 18 |
| Injection resistance | n/a | | **Day 24** |
| Judge/human agreement | n/a | | **Day 10** |
| p95 latency (retrieval only so far) | 9 ms | 153 ms | Day 21 |
| Cost per query | ~$0.0006 (Day 4, answer generation) | unchanged (reranker runs locally) | **Day 21** |

## Per-version detail (r@1)

| r@1 | V1 | V2 | V3 | V4 |
|---|---|---|---|---|
| capability (n=14) | 57% | 57% | 64% | 79% |
| exact_token (n=20) | 15% | 15% | 15% | 75% |
| tier_gated (n=12) | 67% | 67% | 67% | 83% |
| temporal (n=15) | 33% | 33% | 47% | 87% |
| non_official (n=7) | 43% | 71% | 71% | 71% |
| ALL (n=68) | 40% | 43% | 47% | 79% |

## Notes

- Capability r@5 is lower in V2–V4 than V1 (93% -> 71% -> 86%). Day 5 chose structure-aware chunking
  on corpus v1; on corpus v2, fixed-500's larger chunks help capability questions. Re-test chunking on v2
  (for example structure-aware with a larger minimum chunk size).
- Retrieval metric counts only authoritative pages as correct (official pages; for non-official questions,
  the internal or sales doc that holds the answer). Part of V4's authority gain is by construction.
- Earlier numbers on corpus v1 (Days 4–6) are in `data/invoicepilot/results/` and the daily notes. They are
  not comparable with this table.
