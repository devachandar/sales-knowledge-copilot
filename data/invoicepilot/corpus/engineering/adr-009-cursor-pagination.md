---
title: ADR-009: Cursor pagination for API v2
doc_type: design_note
audience: internal
owner: platform-team
status: final
last_updated: 2025-11-10
---

# ADR-009: Cursor pagination for API v2

## Decision
v2 list endpoints use opaque cursors (next_cursor) with limit up to 100, instead of v1's ?page=&per_page=.

## Why
Page numbers skip or repeat rows when data changes between calls.

## Note
2.2.0 returned a cursor on the last page by mistake (BUG-2200-04); fixed in 2.2.1.
