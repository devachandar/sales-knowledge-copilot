---
title: Note: why bulk actions cap at 100
doc_type: design_note
audience: internal
owner: platform-team
status: final
last_updated: 2026-01-15
---

# Note: why bulk actions cap at 100

Bulk actions run synchronously in the browser request. 100 invoices keeps the request under 30 seconds. An older prototype used 50; some community posts still repeat that number.
