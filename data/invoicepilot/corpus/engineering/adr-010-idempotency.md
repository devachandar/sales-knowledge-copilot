---
title: ADR-010: Idempotency keys for POST
doc_type: design_note
audience: internal
owner: platform-team
status: final
last_updated: 2025-11-18
---

# ADR-010: Idempotency keys for POST

## Decision
POST endpoints accept an Idempotency-Key header. We store the key with a hash of the body for 24 hours.

## Behavior
Same key and same body returns the stored response. Same key and a different body returns 409 IP-4090. A key whose first request is still running returns 409 IP-4091.
