---
title: Postmortem INC-2025-012: Blank dashboard for large accounts
doc_type: postmortem
audience: internal
owner: platform-team
status: final
last_updated: 2025-06-28
related_bugs: [BUG-2000-02]
---

# Postmortem INC-2025-012: Blank dashboard for large accounts

**Incident:** INC-2025-012
**Bug:** BUG-2000-02 (Medium)
**Affected version:** 2.0.0
**Fixed in:** 2.0.0

## Impact
About 60 large organizations.

## Root cause
The dashboard loaded every contact in one query. For accounts with more than 500 contacts the query timed out after 30 seconds.

## Resolution
Paginated the contacts query. Fixed within 2.0.0 on 2025-07-01.

## Customer communication
Support linked affected tickets to BUG-2000-02. Customers get an email when the fix ships.
