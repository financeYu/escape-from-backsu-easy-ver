# content_research_mvp Agents

## Mission

`content_research_mvp` produces Korean-language research materials for current affairs and economy YouTube production.

This subproject owns:

- Topic research briefs
- EvidenceCard records
- Channel-fit scoring for content suitability
- Narrative outlines
- PPT outline plans and speaker notes
- Shooting scripts
- Fact, bias, copyright, and risk review reports

This subproject does not own:

- Investment recommendations
- Quant score design
- Backtesting
- Valuation judgment
- Trading signals
- Portfolio construction

Keep responsibilities separate from `reserch_mvp`, `Quant_mvp`, and `chart_mvp`.

## Collection Policy

Allowed:

- Official reports, statistical releases, government and international organization pages
- Licensed or openly accessible article metadata and summaries
- YouTube Data API metadata-only collection, such as video id, title, channel id, published time, description snippet, tags when available, duration, and public statistics

Forbidden:

- Direct scraping of `youtube.com` HTML
- Video download
- Unauthorized transcript extraction
- Bulk comment scraping
- Copying a specific YouTuber's unique tone, jokes, title formulas, catchphrases, or character
- Copying article prose or third-party scripts verbatim

## Output Rules

- All structured outputs must be serializable to JSONL.
- Human-facing reports must be exportable as Markdown.
- Korean is the default reporting language.
- Every number must include unit, as-of date, and source.
- Unverified claims must be marked as unverified or rewritten as scenarios.
- Political and social topics must include multiple perspectives.

## Root Agent Workflow

1. Topic Radar Agent gathers current issue candidates.
2. Channel Fit Agent scores popularity, economic linkage, story potential, source availability, and risk safety.
3. Research Agent collects sources and builds EvidenceCards.
4. Narrative Agent creates hook-background-structure-issues-twist-impact-conclusion flow.
5. PPT Agent creates 15-25 slide outline and speaker notes.
6. Script Agent writes a shooting script.
7. Fact & Risk Check Agent reviews claims, numbers, bias, copyright, and policy risk.

The root agent must not simply concatenate sub-agent output. It must resolve conflicts by source quality and downgrade weak claims.

