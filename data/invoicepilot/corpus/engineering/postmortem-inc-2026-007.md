---
title: Postmortem INC-2026-007: Reminders sent for voided invoices
doc_type: postmortem
audience: internal
owner: platform-team
status: final
last_updated: 2026-02-09
related_bugs: [BUG-2200-03]
---

# Postmortem INC-2026-007: Reminders sent for voided invoices

**Incident:** INC-2026-007
**Bug:** BUG-2200-03 (Medium)
**Affected version:** 2.2.0
**Fixed in:** 2.2.1

## Impact
About 1,900 reminder emails for void invoices.

## Root cause
The bulk void path did not call the reminder scheduler's cancel method, unlike the single-invoice void.

## Resolution
Bulk void now cancels reminders. Fixed in 2.2.1.

## Customer communication
Support linked affected tickets to BUG-2200-03. Customers get an email when the fix ships.
