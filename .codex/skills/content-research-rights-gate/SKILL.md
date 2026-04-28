---
name: content-research-rights-gate
description: Rights/copyright gate for `content_research_mvp`: source_registry, rights_gate, body storage, snippets, quotes, retention, license_basis, and body_collection_tier.
---

# Content Research Rights Gate

## Core

Default to metadata-only when rights are unknown. Store facts and provenance needed for verification, not copyrighted article bodies for convenience.

## Tiers

| Tier | Meaning | Body storage |
|---:|---|---|
| 0 | Unknown or metadata/snippet-only news | Forbidden |
| 1 | API/license allows temporary cache | Temporary only |
| 2 | Licensed body storage | Allowed within license |
| 3 | Official/public/open institutional data | Allowed with attribution |

Required decision fields: `body_collection_tier`, `license_basis`, `retention_days`, `quote_policy`.

## Gate

- Tier 0: `allowed=false`, `storage_policy=metadata_only`.
- Tier 1: allow only temporary cache with enforced retention.
- Tier 2: preserve license basis and constraints.
- Tier 3: preserve URL, publisher, as-of date, and dataset/report id when available.

Deny storage that exceeds the tier. Never upgrade rights from public accessibility, paywall absence, RSS availability, or successful scraping.

## Defaults

- Unknown source or news API without body license: Tier 0, `license_basis=unknown` or `metadata_only`, `retention_days=0`, `quote_policy=no_article_body`.
- Official statistics, government releases, central bank data, public agency datasets, international organizations: usually Tier 3 unless terms prohibit reuse.
- Paid/licensed provider: Tier 2 only with a clear storage license.
- Short-lived API cache: Tier 1 with a concrete retention limit.
