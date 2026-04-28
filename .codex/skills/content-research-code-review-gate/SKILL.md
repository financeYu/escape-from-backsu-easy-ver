---
name: content-research-code-review-gate
description: Code review gate for `content_research_mvp`: scope, tests, source safety, rights/copyright, evidence provenance, pipeline outputs, and policy risks. Excludes Quant/chart/stock projects and any scoring, backtesting, valuation, trading, portfolio, or ranking work.
---

# Content Research Code Review Gate

## Guard

Use only for `content_research_mvp`. If the task is in Quant, chart, stock, scoring, backtesting, valuation, trading, portfolio, or ranking work, stop and use that project's local gates.

## Review

Inspect only the diff, nearby code/tests, relevant `AGENTS.md`, and any directly relevant local skill:

- evidence shape/provenance: `content-research-evidence-pipeline`
- source health/status: `content-research-monitoring`
- body storage/quotes/licenses: `content-research-rights-gate`

Avoid generated outputs, caches, raw provider payloads, and old artifacts unless the review is explicitly about them.

## Checklist

- Scope: stays in `content_research_mvp`; no investment advice, quant design, backtests, valuation, trading signals, or portfolio logic.
- Sources: news stays metadata/snippet/allowed-summary only; official data preserves source, URL, unit, period/as-of date, and retrieval method.
- Rights: no article body storage without an explicit tier; no copied article prose, scripts, creator style, or title formulas.
- Evidence: numbers have source/unit/date; claims separate fact, scenario, interpretation, and unverified status; modules do not invent provenance.
- Monitoring: errors use specific statuses; credentials/secrets/full unsafe responses are not logged or persisted.
- Pipeline: JSONL/Markdown remain stable and serializable; CLI defaults and paths are backward compatible unless intentionally changed.
- Policy: no YouTube HTML scraping, video download, unauthorized transcript extraction, or bulk comment scraping.
- Tests: changed behavior has focused tests, or the missing test reason is stated as risk.

## Verdicts

- `PASS`: no blocking issue.
- `PASS_WITH_WARNINGS`: acceptable with non-blocking test/docs/observability risk.
- `NEEDS_FIX`: defect, regression, missing required test, provenance gap, rights violation, or scope breach.
- `NEEDS_CLARIFICATION`: scope, rights, source contract, or expected behavior is ambiguous.

## Output

Lead with findings. Use severity `P0`-`P3`, file/line, concrete risk, and expected fix. Then report verdict, validation run/not run, and residual risk in Korean.
