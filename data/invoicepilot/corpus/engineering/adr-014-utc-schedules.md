---
title: ADR-014: Calculate recurring schedules in UTC
doc_type: design_note
audience: internal
owner: platform-team
status: final
last_updated: 2026-06-20
---

# ADR-014: Calculate recurring schedules in UTC

## Decision
Store and calculate recurring schedules in UTC. Show them in the organization's local time.

## Why
Local wall-clock math broke twice a year at DST changes (BUG-2100-02).

## Consequences
Shipped in 2.3.1. The old help page about local-time schedules is stale and should be retired.
