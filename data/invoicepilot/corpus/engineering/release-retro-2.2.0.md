---
title: Release retro: 2.2.0
doc_type: release_retro
audience: internal
owner: release-eng
status: final
last_updated: 2026-01-20
---

# Release retro: 2.2.0

Release 2.2.0 went out on 2026-01-20.

## Fixed in this release
- BUG-2200-01: Client portal login loop on Safari (Medium)
- BUG-2110-01: Recurring invoice preview shows the wrong currency symbol (Low)

## Bugs first seen on this version
- BUG-2200-01: Client portal login loop on Safari (Fixed)
- BUG-2200-02: API v2 rate limit headers missing (Fixed)
- BUG-2200-03: Bulk void leaves payment reminders scheduled (Fixed)
- BUG-2200-04: API v2 list endpoints return next_cursor on the last page (Fixed)

## Notes
Rollout was staged over 3 days: 10%, 50%, 100% of organizations.
