---
name: content-research-evidence-pipeline
description: Evidence normalization for `content_research_mvp`: news/official-data records, provenance, issue_radar, data_matcher, claim_extractor, brief_builder, and Korean economy/current-affairs YouTube research handoffs.
---

# Content Research Evidence Pipeline

## Core

Normalize source metadata and official data into Evidence candidates before issue ranking, data matching, claim extraction, or brief building. Keep provenance explicit; never invent missing source, date, unit, or rights status.

## Evidence Fields

Use the local model when present. Otherwise prefer these fields:

- identity: `evidence_id`, `source_id`, `source_type`, `publisher`, `title`, `url`
- dates: `published_at`, `as_of_date`, `retrieved_at`
- content: `language`, `topic_tags`, `summary`, `claims`, `key_numbers`
- controls: `rights`, `quality_flags`

News records should use title, publisher, URL, timestamp, snippet, tags, and rights metadata. Official data should use dataset/report id, period, geography, unit, value, release/as-of date, and publisher.

## Flow

1. Collect allowed metadata or official data.
2. Apply the rights gate before body text or long excerpts.
3. Normalize to Evidence fields.
4. Deduplicate by canonical URL, dataset/report id, or stable source key.
5. Emit JSONL-compatible records with provenance.

## Rules

- Every number needs unit, period/as-of date, geography when relevant, and source.
- Treat news as context unless independently confirmed.
- Mark uncertainty as `unverified`, `scenario`, or `interpretation`.
- Summaries must be neutral and not copied from article prose.
- `issue_radar`, `data_matcher`, `claim_extractor`, and `brief_builder` stay downstream; they do not fetch new source bodies or fill provenance gaps silently.
