---
title: Note: auto-match tolerance
doc_type: design_note
audience: internal
owner: platform-team
status: final
last_updated: 2026-05-02
---

# Note: auto-match tolerance

Auto-match requires an exact amount match and a date within 7 days. We tried a 0.5% tolerance in beta and it caused false matches on recurring payments of similar size, so it was removed before 2.3.0.
