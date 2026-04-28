# content_research_mvp

Korean current affairs and economy YouTube research MVP.

The project builds a metadata-first content research pipeline that turns topics and sources into EvidenceCards, channel-fit scores, narrative outlines, PPT plans, scripts, and risk reports.

## Scope

Included:

- YouTube content research support
- EvidenceCard validation
- Metadata-only YouTube adapter interface
- Channel-fit scoring
- Korean Markdown and JSONL-friendly output models
- PPT outline and script draft builders
- Fact, risk, copyright, and bias review structures

Excluded:

- Investment recommendations
- Quant model design
- Backtests
- Valuation decisions
- Direct YouTube HTML scraping
- Video downloads
- Unauthorized transcript extraction
- Bulk comment scraping

## Quick Start

Run the MVP directly from the source tree without installing the package:

```powershell
cd content_research_mvp
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pytest
python -m content_research.cli run --topic "호르무즈 해협 리스크와 한국 경제"
```

If you prefer the console command, install the project first with `python -m pip install -e .`, then run `content-research run --topic "..."`.

The MVP research bundle command does not call external APIs. The hourly collection command can call implemented source adapters when credentials are configured; `naver_news`, `newsapi`, and `nytimes` are connected to official news APIs and store metadata only, while `ecos`, `kosis`, `opendart`, `fred`, `eia`, and `un_comtrade` collect official statistics, filing, time-series, energy, and trade records.

## Hourly Collection

Create one hourly collection cycle. Configured live adapters such as Naver News Search API and NewsAPI.org will run; unimplemented sources remain placeholder results:

```powershell
python -m content_research.cli collect-once
```

Run the collection process continuously at the configured interval, defaulting to 60 minutes:

```powershell
python -m content_research.cli collect-daemon
```

For a bounded smoke test:

```powershell
python -m content_research.cli collect-daemon --max-cycles 2
```

Collection manifests are written to `outputs/collections/YYYY-MM-DD/HH/`.

## Output

The CLI writes Markdown and JSONL-compatible records to `outputs/` by default.

## Package Layout

- `src/content_research/models.py`: shared dataclass models
- `src/content_research/config.py`: TOML configuration loader
- `src/content_research/pipeline/orchestrator.py`: pipeline coordinator
- `src/content_research/sources/youtube_adapter.py`: metadata-only YouTube adapter interface
- `src/content_research/research/evidence_card.py`: EvidenceCard creation and validation
- `src/content_research/scoring/channel_fit_score.py`: channel-fit scoring
- `src/content_research/narrative/outline_builder.py`: narrative outline builder
- `src/content_research/deck/ppt_outline_builder.py`: PPT outline builder
- `src/content_research/script/script_builder.py`: shooting script builder
- `src/content_research/review/risk_report.py`: risk report builder
