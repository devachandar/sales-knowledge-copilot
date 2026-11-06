---
title: Release retro: 2.1.0
doc_type: release_retro
audience: internal
owner: release-eng
status: final
last_updated: 2025-09-16
---

# Release retro: 2.1.0

Release 2.1.0 went out on 2025-09-16.

## Fixed in this release
- BUG-2000-01: Currency rounding error on invoice totals (High)
- BUG-2010-01: Archived tax rates hidden on existing drafts (Low)

## Bugs first seen on this version
- BUG-2100-01: Receipt OCR misreads handwritten totals (Won't Fix)
- BUG-2100-02: Recurring invoices skip a cycle across DST changes (Fixed)
- BUG-2100-03: Receipt scanning rotates landscape receipts (Fixed)
- BUG-2100-04: Payment reminder sent twice when the send window crosses midnight (Fixed)

## Notes
Rollout was staged over 3 days: 10%, 50%, 100% of organizations.
