---
title: Postmortem INC-2025-031: Recurring invoices skipped across the DST change
doc_type: postmortem
audience: internal
owner: platform-team
status: final
last_updated: 2025-11-02
related_bugs: [BUG-2100-02]
---

# Postmortem INC-2025-031: Recurring invoices skipped across the DST change

**Incident:** INC-2025-031
**Bug:** BUG-2100-02 (High)
**Affected version:** 2.1.0
**Fixed in:** 2.3.1

## Impact
312 recurring profiles across 41 organizations missed one invoice.

## Root cause
Schedules were stored as local wall-clock times. On 2025-11-02 clocks went back one hour in the US, and the scheduler's 'next run' calculation landed in a time that it had already passed, so 312 profiles skipped one cycle.

## Resolution
Short term: support re-sent missed invoices by hand. Long term: ADR-014 moves schedule math to UTC. Shipped in 2.3.1.

## Customer communication
Support linked affected tickets to BUG-2100-02. Customers get an email when the fix ships.
