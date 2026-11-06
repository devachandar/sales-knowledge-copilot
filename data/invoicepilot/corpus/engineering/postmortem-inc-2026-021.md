---
title: Postmortem INC-2026-021: PDF export drops pages after 25 line items
doc_type: postmortem
audience: internal
owner: platform-team
status: final
last_updated: 2026-08-29
related_bugs: [BUG-2310-02]
---

# Postmortem INC-2026-021: PDF export drops pages after 25 line items

**Incident:** INC-2026-021
**Bug:** BUG-2310-02 (High)
**Affected version:** 2.3.1
**Fixed in:** not yet fixed

## Impact
Invoices with more than 25 line items; about 3% of invoices sent.

## Root cause
The new PDF renderer in 2.3.1 sets a fixed page height for the line item table. Rows past the first page are clipped instead of flowing to page 2.

## Resolution
Workaround: send by link. A fix to the renderer's pagination is in progress.

## Customer communication
Support linked affected tickets to BUG-2310-02. Customers get an email when the fix ships.
