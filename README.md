# Sales Product Knowledge Copilot

A retrieval-augmented assistant that answers sales and support questions about **InvoicePilot**, a synthetic
invoicing SaaS product, with citations. Built step by step over a 30-day plan, with every change measured.
Model calls use raw HTTP (no SDK, no orchestration framework).

## Current results (retrieval, corpus v2: 436 documents, 68 questions)

| | V1 (Day 4) | V4 (Day 7) |
|---|---|---|
| recall@5, exact-token questions | 45% | 100% |
| recall@1, all questions | 40% | 79% |

Full table and notes: [`docs/results_table.md`](docs/results_table.md).

## Layout

```
copilot/            the product
  config.py         every path and shared setting
  llm/              model client (retries, backoff) and embeddings
  ingest/           parsers (HTML, PDF, JSON tickets, Markdown, DOCX) -> documents.jsonl; SQL tables
  indexing/         chunking strategies, chunk + embed into pgvector
  retrieval/        vector, BM25, RRF fusion, metadata filters, authority, and pipeline.py (V1-V4)
  generation/       grounded answering, prompts
  db/schema.sql
evals/              how we measure
  questions/        seed, hard, filter, exact, non_official
  retrieval/        run_pipeline (the results table) and the per-technique experiments
  generation/       Day 2 prompt experiments (attacks, decomposition)
docs/               results table, failure log
data/invoicepilot/  corpus, processed files, results (answer_key/ is never ingested)
archive/            old code kept for reference, not used
```

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# .env in the project root: GOOGLE_API_KEY=..., DATABASE_URL=postgresql://...
```

## Run (always from the project root)

```bash
# build the data
python -m copilot.ingest.load_tables                                 # CSVs -> Postgres tables
python -m copilot.ingest.build_documents                             # corpus -> documents.jsonl
STRATEGY=structure-aware python -m copilot.indexing.build_chunks     # documents -> chunks
STRATEGY=structure-aware python -m copilot.indexing.embed_chunks     # chunks -> pgvector
STRATEGY=fixed-500 python -m copilot.indexing.build_chunks           # (V1 uses fixed-500)
STRATEGY=fixed-500 python -m copilot.indexing.embed_chunks

# retrieve and answer
python -m copilot.retrieval.pipeline                                 # one question through V1-V4
python -m copilot.generation.answer

# evaluate
python -m evals.check_questions                                      # test the tests
python -m evals.retrieval.run_pipeline                               # V1-V4 results table
QUESTIONS=exact,non_official python -m evals.retrieval.authority_eval
```

`QUESTIONS` takes short names (`seed,hard,filter,exact,non_official`) or file paths. With no value, every set is used.
