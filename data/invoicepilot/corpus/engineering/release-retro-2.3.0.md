---
title: Release retro: 2.3.0
doc_type: release_retro
audience: internal
owner: release-eng
status: final
last_updated: 2026-05-11
---

# Release retro: 2.3.0

Release 2.3.0 went out on 2026-05-11.

## Fixed in this release
- BUG-2200-02: API v2 rate limit headers missing (Low)
- BUG-2210-01: Portal Pay now button hidden for partially paid invoices (High)
- BUG-2210-02: Idempotency-Key ignored on POST /v2/payments (High)

## Bugs first seen on this version
- BUG-2300-01: Custom report builder times out on 3+ year date ranges (Open)

## Notes
Rollout was staged over 3 days: 10%, 50%, 100% of organizations.
