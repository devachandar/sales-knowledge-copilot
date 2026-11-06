---
title: ADR-012: New PDF renderer
doc_type: design_note
audience: internal
owner: platform-team
status: final
last_updated: 2026-07-01
---

# ADR-012: New PDF renderer

## Decision
Replace the HTML-to-PDF service with a native renderer in 2.3.1 for speed.

## Risk noted
Table pagination needs more testing. (Later: BUG-2310-02.)
