---
title: ADR-018: Webhook retry schedule
doc_type: design_note
audience: internal
owner: platform-team
status: final
last_updated: 2026-07-15
---

# ADR-018: Webhook retry schedule

## Decision
Retry failed webhook deliveries up to 8 times over 24 hours (was 5). Disable an endpoint after 3 days of failures.

## Why
5 retries over 6 hours missed weekend outages at small customers.
