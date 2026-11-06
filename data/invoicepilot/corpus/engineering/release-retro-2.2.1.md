---
title: Release retro: 2.2.1
doc_type: release_retro
audience: internal
owner: release-eng
status: final
last_updated: 2026-03-10
---

# Release retro: 2.2.1

Release 2.2.1 went out on 2026-03-10.

## Fixed in this release
- BUG-2110-02: Expense CSV import rejects DD/MM/YYYY dates (Medium)
- BUG-2200-03: Bulk void leaves payment reminders scheduled (Medium)
- BUG-2200-04: API v2 list endpoints return next_cursor on the last page (Medium)

## Bugs first seen on this version
- BUG-2210-01: Portal Pay now button hidden for partially paid invoices (Fixed)
- BUG-2210-02: Idempotency-Key ignored on POST /v2/payments (Fixed)

## Notes
Rollout was staged over 3 days: 10%, 50%, 100% of organizations.
