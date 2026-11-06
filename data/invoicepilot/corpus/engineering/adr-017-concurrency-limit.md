---
title: ADR-017: Per-key concurrency limit
doc_type: design_note
audience: internal
owner: platform-team
status: final
last_updated: 2026-06-25
---

# ADR-017: Per-key concurrency limit

## Decision
Limit each API key to 10 requests in flight, on every plan. Over the limit returns 429 IP-4291.

## Why
A few integrations ran 50+ parallel workers and caused slowdowns for everyone, while staying under their per-minute limit.
