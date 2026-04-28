# Research Master Sub-Agent Modules

## Purpose

These modules are internal sub-agents controlled by the Research Master Agent.

They exist only to create reliable research briefs for Korean current affairs and economy content. They do not produce PPT plans, shooting scripts, titles, thumbnail copy, openings, Shorts adaptations, or video packaging.

The user should not receive module-by-module reports. The Research Master Agent must integrate, compress, and factcheck module outputs before producing the final brief.

## Module Map

1. `issue_collection`: collects and normalizes internationally important current affairs and economy issue candidates. Code: `content_research.research.issue_collection`.
2. `research_priority`: selects which issues deserve research based on news value, relevance, source availability, and risk. Code: `content_research.research.priority`.
3. `fact_verification`: verifies core facts, dates, numbers, source status, and uncertainty. Code: `content_research.research.fact_verification`.
4. `context_analysis`: explains causes, background, structural context, historical context, and relevant actors. Code: `content_research.research.context_analysis`.
5. `brief_structuring`: compresses verified material into the required research brief format. Code: `content_research.research.brief_structuring`.
6. `final_factcheck`: checks the final brief for accuracy, wording risk, source clarity, sensationalism, definitive forecasts, and investment-advice risk. Code: `content_research.review.final_factcheck`.

## Handoff Order

Use the modules in this default order:

1. Issue Collection
2. Research Priority
3. Fact Verification
4. Context Analysis
5. Brief Structuring
6. Final Factcheck

The Research Master Agent can skip a module when the user gives a narrow, already-selected issue, but final factcheck must always run before delivery.

## Shared Rules

- Korean is the default final reporting language.
- Keep outputs short and research-focused.
- Distinguish confirmed facts, reported claims, expert interpretation, and uncertainty.
- Every important number needs unit, as-of date, and source when available.
- Do not create video production elements.
- Do not give investment advice, stock recommendations, trading strategy, valuation judgment, or asset-price predictions.
- Do not copy article prose, third-party scripts, or a specific creator's unique style.

## Internal Handoff Contract

Each module should return only the information needed by the next module:

- `issue`: concise issue name
- `why_now`: current trigger or reason for timeliness
- `verified_facts`: confirmed facts with source notes
- `uncertainties`: facts or claims that should not be stated as settled
- `context`: causes, actors, background, and historical context
- `watch_points`: variables and conservative outlook points
- `source_notes`: short list of high-value sources
- `risk_notes`: wording, bias, source, or investment-advice risks

The Research Master Agent decides what survives into the final user-facing brief.
