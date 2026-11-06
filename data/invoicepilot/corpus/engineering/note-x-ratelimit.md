---
title: Note: rate limit headers
doc_type: design_note
audience: internal
owner: platform-team
status: final
last_updated: 2026-05-12
---

# Note: rate limit headers

Since 2.3.0 every v2 response includes X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset. Concurrency (IP-4291) has no header; clients learn it from the 429.
