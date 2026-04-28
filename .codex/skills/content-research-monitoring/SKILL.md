---
name: content-research-monitoring
description: Collection-health monitoring for `content_research_mvp`: source statuses, credential/permission errors, count drops, last_success_at, manifests, and operational health reports.
---

# Content Research Monitoring

## Core

Track collection health without hiding failures. Store specific machine-readable statuses plus short human messages.

## Statuses

Use the narrowest status:

- `success`: usable records fetched
- `empty`: request succeeded with zero usable records
- `missing_credentials`: local key/token absent
- `permission_denied`: provider rejects access, quota, plan, or scope
- `rate_limited`: provider throttled
- `source_error`: API/HTTP provider error
- `parse_error`: response shape changed or parsing failed
- `partial_success`: usable records plus failed subrequests
- `skipped`: intentionally not run

## Run Fields

Each source result or manifest entry should include `source_id`, `display_name`, `status`, `message`, `started_at`, `finished_at`, `collected_records`, and when relevant `expected_min_records`, `last_success_at`, `error_type`, `error_detail`.

Never store secrets, tokens, API keys, or unsafe full provider responses.

## Rules

- Update `last_success_at` only after usable records or a source-specific success condition.
- Compare volume against `expected_min_records` first, then recent successful baselines if available.
- Do not inflate counts with duplicate or unusable records.
- Report totals by status, credential/permission blockers, count-drop warnings, and stale sources.
