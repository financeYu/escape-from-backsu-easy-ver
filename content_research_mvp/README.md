# content_research_mvp

Korean current-affairs and economy research MVP for YouTube-style content planning.

This repository has two practical paths:

- `content-research run`: runs one collection cycle and creates a local MVP research bundle from fetched Evidence records.
- `content-research collect-once` / `collect-daemon`: runs the source collection layer for implemented MVP adapters, writes manifests and record JSONL, and leaves non-MVP catalog sources out of the Evidence pipeline.

## MVP Scope

The MVP is metadata-first. It supports source discovery, official-data collection, conservative Evidence normalization, issue detection, data matching, claim extraction, priority scoring, and final ResearchBrief generation. It is designed to help a researcher assemble a grounded brief, not to publish article bodies or make investment recommendations.

Included in the MVP:

- Metadata-only news discovery through official APIs.
- Official/statistical data records from implemented public data APIs.
- EvidenceCandidate normalization with source trace fields.
- Issue, data-match, claim, priority, and ResearchBrief flow.
- Markdown and JSONL outputs under `outputs/`.
- Copyright and source-rights gates that block durable article-body storage unless a source is explicitly allowed.

Excluded from the MVP:

- Investment advice, valuation decisions, backtests, or quant model design.
- Direct YouTube HTML scraping, video downloads, unauthorized transcript extraction, or bulk comment scraping.
- Article body crawling, full-text news archiving, paywall bypassing, or licensed publisher body storage without an explicit rights basis.
- Live collection from catalog sources that are not listed as MVP sources below.

## Quick Start

Install in editable mode with test dependencies:

```sh
cd content_research_mvp
python -m pip install -e ".[dev]"
```

Run the full test suite:

```sh
python -m pytest
```

Run the offline E2E smoke test:

```sh
python -m pytest tests/test_content_research_e2e.py
```

Run a local topic bundle from one collection cycle:

```sh
python -m content_research.cli run --topic "한국 경제 주요 이슈"
content-research run --topic "한국 경제 주요 이슈"
```

The `run` command runs the configured MVP collection sources once, normalizes fetched record JSONL into Evidence, and writes `outputs/research_bundle.md` and `outputs/research_bundle.jsonl` unless `--output-dir` is supplied. `--topic` is treated as a requested research topic, not a latest-issue recommendation hint: only Evidence that matches the requested topic is allowed into the brief. If no Evidence records are available, the bundle reports missing credentials or adapter errors instead of fabricating sources. If Evidence exists but none of it matches `--topic`, the bundle reports a topic-mismatch status instead of substituting an unrelated issue.

The generated Markdown follows the root-agent MVP architecture:

1. One-line topic definition
2. Why it matters now
3. Ten core source materials when available
4. PPT slide outline
5. Shooting script
6. Fact-check table
7. Risk revision suggestions

## MVP Collection Sources

Only these source IDs are dispatched to collection handlers:

| Source ID | Category | Handler status | Evidence use | Required credential |
|---|---|---|---|---|
| `naver_news` | Korean news discovery | Implemented | Metadata only | `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` |
| `newsapi` | International news discovery | Implemented | Metadata/snippets only | `NEWSAPI_KEY` |
| `nytimes` | International publisher metadata | Implemented | Metadata only | `NYTIMES_API_KEY` |
| `ecos` | Korean official data | Implemented | Official data records | `ECOS_API_KEY` |
| `kosis` | Korean official data | Implemented | Official data records | `KOSIS_API_KEY` |
| `opendart` | Korean disclosure data | Implemented | Disclosure metadata | `OPENDART_API_KEY` |
| `fred` | U.S. official data | Implemented | Official data records | `FRED_API_KEY` |
| `eia` | U.S. energy data | Implemented | Official data records | `EIA_API_KEY` |
| `un_comtrade` | International trade data | Implemented | Official data records | `UN_COMTRADE_KEY` or `COMTRADE_API_KEY` |

All other default catalog sources are treated as non-MVP. They are still visible in the catalog for future planning, but the collection process writes them as `planned_non_mvp`, does not run an adapter, does not write a record file, and does not feed them into Evidence normalization.

## Hourly Collection

Run one collection cycle:

```sh
python -m content_research.cli collect-once
content-research collect-once
```

Run continuously at the configured interval, defaulting to 60 minutes:

```sh
python -m content_research.cli collect-daemon
```

Run a bounded smoke cycle:

```sh
python -m content_research.cli collect-daemon --max-cycles 2
```

Collection manifests are written to:

```text
outputs/collections/YYYY-MM-DD/HH/{run_id}.jsonl
outputs/collections/YYYY-MM-DD/HH/{run_id}.md
outputs/collections/YYYY-MM-DD/HH/records/{run_id}/{source_id}.jsonl
```

Each manifest JSONL starts with a `collection_run` record. Subsequent `source_result` records show the per-source status:

- `fetched_metadata`, `fetched_statistics`, `fetched_catalog`, `fetched_disclosures`, `fetched_observations`, `fetched_energy_series`, or `fetched_trade_data` when an MVP source fetched records.
- `missing_credentials` when an MVP source has no required key in the environment or `.env`.
- `planned_non_mvp` when a catalog source is outside the MVP source set.
- `error` when an implemented adapter fails during an API call.

## Optional Live/Dry-Run Conditions

The default tests are offline and deterministic. The optional live/dry-run E2E test is skipped unless all of these are true:

- `CONTENT_RESEARCH_RUN_LIVE_E2E=1` is set.
- At least one MVP API credential is configured in the process environment or `.env`.
- The test can call the relevant external API from the current machine.

Run it from POSIX-style shells:

```sh
CONTENT_RESEARCH_RUN_LIVE_E2E=1 python -m pytest tests/test_content_research_e2e.py
```

Run it from PowerShell:

```powershell
$env:CONTENT_RESEARCH_RUN_LIVE_E2E = "1"
python -m pytest tests/test_content_research_e2e.py
```

The live/dry-run test selects only MVP sources that have credentials. Sources without credentials are not called in that test. Normal `collect-once` will include all enabled default catalog sources and report missing MVP credentials explicitly.

## Evidence To Brief Flow

The current offline E2E flow is:

```text
collection record JSONL
  -> EvidenceCandidate normalization
  -> issue detection from MVP news Evidence
  -> official data matching
  -> claim extraction
  -> internal priority scoring
  -> ResearchBrief Markdown
```

Evidence normalization only accepts records from MVP Evidence sources:

- News metadata: `naver_news`, `newsapi`, `nytimes`
- Official data: `ecos`, `eia`, `fred`, `kosis`, `opendart`, `un_comtrade`

It skips collection manifest rows, malformed JSON, non-Evidence statuses such as `planned_non_mvp` and `missing_credentials`, and non-MVP source IDs such as `guardian`.

Normalized Evidence candidates preserve trace fields when available:

- `source_id`, `source_name`, `publisher_or_institution`
- `title_or_indicator`, `url`
- `published_or_observed_at`, `collected_at`, `accessed_at`
- `value`, `unit`, `snippet`
- `rights_status`, `confidence`, `field_status`

ResearchBrief generation uses related Evidence, matched official data, and extracted claims. It includes source notes, missing-field notes, rights notes such as `no body use`, and final checks for unverified claims, source-less claims, and certain future predictions.

## Short Korean ResearchBrief Example

```md
## 제목
국제 유가와 한국 물가 부담

## 핵심 요약
- 국제 유가 상승 보도가 반복되고 있어 에너지 비용 이슈로 묶을 수 있습니다.
- EIA WTI 현물가격은 2026-04-24 기준 배럴당 83.10달러로 확인됩니다.
- 일부 뉴스 주장은 추가 검증 전까지 확정 사실로 쓰지 않습니다.

## 주요 날짜·수치·직접 원인
- WTI crude oil spot price: 83.10 dollars per barrel, 기준 2026-04-24, 출처 eia
- 확인 필요: 공급 차질 보도가 가격 상승 배경으로 제시되었습니다.

## 근거와 출처
- newsapi - Oil prices rise after supply warning - https://example.com/oil (rights: metadata_only, no body use)
- eia - WTI crude oil spot price - data_eia_wti
```

The exact generated wording depends on the Evidence and claim inputs. The important contract is that the brief remains conservative, source-traced, and metadata/body-rights aware.

## Copyright, Source, And Body Storage Limits

The rights gate is intentionally conservative:

- Unknown and news-discovery sources default to `metadata_only`; durable body storage is blocked.
- `newsapi`, `nytimes`, and `naver_news` are used for metadata, links, publication times, and snippets/abstracts only.
- NewsAPI `content` is treated as a truncated snippet, not article body storage.
- Official data sources use `official_or_public_data` storage policy when recognized by source ID or official API domain.
- Non-MVP sources are not passed into Evidence, even if they appear in the catalog.
- Article bodies, filing bodies, licensed news text, and long quotations require a separate rights basis and implementation before they can be stored.

Body collection tiers used by the source registry:

| Tier | Meaning | Durable body storage |
|---:|---|---|
| `0` | Metadata only or unknown rights | Blocked |
| `1` | Temporary cache only | Blocked for durable storage |
| `2` | Licensed body storage | Allowed only under recorded license |
| `3` | Official/public data | Allowed with provenance and attribution |

## Test Commands

```sh
python -m pytest
python -m pytest tests/test_content_research_e2e.py
python -m pytest tests/test_evidence_normalizer.py tests/test_brief_builder.py tests/test_hourly_collection_process.py
```

The project config sets `tests` as the pytest root and uses `src` on `pythonpath`.

## Package Layout

- `src/content_research/cli.py`: CLI entry points.
- `src/content_research/collection/catalog.py`: default source catalog and MVP source gate.
- `src/content_research/collection/process.py`: hourly collection process and manifest writer.
- `src/content_research/research/evidence_normalizer.py`: collected-record to EvidenceCandidate normalization.
- `src/content_research/research/brief_builder.py`: final ResearchBrief builder.
- `src/content_research/sources/news_discovery/`: implemented news metadata adapters.
- `src/content_research/sources/official_data/`: implemented official-data adapters.
- `src/content_research/sources/copyright/`: source-rights registry and storage decision gate.
- `tests/test_content_research_e2e.py`: offline and optional live/dry-run E2E coverage.

## Known Limitations

- The `run` command depends on API credentials and upstream availability; if no source records are fetched, it produces a collection-status bundle rather than a source-backed brief.
- Collection is credential-dependent; missing API keys produce `missing_credentials` rows, not fetched records.
- Non-MVP catalog sources are planning entries only and never become Evidence until promoted into the MVP source set with an implemented handler.
- News sources are metadata/snippet only; full article text is not collected or stored.
- Official-data adapters use fixed default queries/series and are not yet topic-adaptive.
- The ResearchBrief builder is deterministic and conservative; it is not an LLM writer and may need editorial cleanup before publication.
- Source quality depends on upstream API payloads. Missing timestamps, URLs, values, or units are surfaced through `field_status` instead of being inferred.
- Optional live/dry-run tests require network access and real credentials, so CI should keep them disabled unless a controlled credentialed environment is available.
