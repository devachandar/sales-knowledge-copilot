---
title: Note: webhook ordering
doc_type: design_note
audience: internal
owner: platform-team
status: final
last_updated: 2026-06-18
---

# Note: webhook ordering

We don't guarantee ordering. invoice.paid can arrive before payment.created. Consumers should fetch the object by id when order matters.
