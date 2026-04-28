# Hourly Collection Process

## Goal

Run the content research collection layer once per hour, every day, while preserving copyright and source-rights controls.

The process writes collection manifests and source results every hour. The Naver News Search API, NewsAPI.org, New York Times, Bank of Korea ECOS, KOSIS, OpenDART, FRED, EIA, and UN Comtrade adapters perform live collection when their credentials are available. Sources without implemented adapters still write planned placeholder results.

## Schedule

- Interval: 60 minutes
- Timezone: Asia/Seoul
- Default next run: next top of the hour
- Output partition: `outputs/collections/YYYY-MM-DD/HH/`

## Commands

Run one collection cycle:

```powershell
content-research collect-once
```

Run continuously every hour:

```powershell
content-research collect-daemon
```

Run two cycles for a smoke test:

```powershell
content-research collect-daemon --max-cycles 2
```

Override the output directory:

```powershell
content-research collect-once --output-dir outputs/collections
```

## Process Flow

```text
Hourly trigger
  -> Load collection config
  -> Load default source catalog
  -> Plan enabled source runs
  -> Run implemented source adapters, starting with Naver News Search API, NewsAPI.org, New York Times APIs, ECOS, KOSIS, OpenDART, FRED, EIA, and UN Comtrade
  -> Apply body collection tier defaults
  -> Write source record JSONL files when records are fetched
  -> Write JSONL manifest
  -> Write Markdown manifest
  -> Sleep until next scheduled run
```

## Source Coverage

The default hourly catalog includes:

- Korean news discovery: Naver News Search API, BIGKinds
- Korean official sources: Korea Policy Briefing RSS, ECOS, KOSIS, OpenDART
- International discovery: GDELT, NewsAPI
- Overseas publishers: NYT, BBC, CNN, CNBC, NPR, Washington Post, POLITICO, Axios, Foreign Affairs, Le Monde, Nikkei Asia, Al Jazeera, DW
- Paid/licensed overseas publishers: Guardian Commercial/Rights Managed, Reuters/LSEG, AP, Bloomberg, Dow Jones/WSJ, FT, Economist
- International official data: World Bank, IMF, OECD, FRED, EIA, UN Comtrade

## Body Collection Gate

Each source carries a default `body_collection_tier`:

- `0`: metadata only
- `1`: temporary text extraction when permitted
- `2`: licensed internal archive
- `3`: open/public-license or official-source archive

The hourly process records the tier in every source result. Actual body fetching must use the copyright gate from `data_collection_design.md` before storing raw text.

## Output Contract

Each hourly run writes:

- `{run_id}.jsonl`: machine-readable run and source records
- `{run_id}.md`: human-readable run manifest

The first JSONL record has `type = "collection_run"`.
Subsequent records have `type = "source_result"`.

## Implemented Adapters

### `naver_news`

Connected to the official Naver News Search API.

- Credentials: `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`
- Endpoint: `https://openapi.naver.com/v1/search/news.json`
- Sort: `date`
- Default display per query: `10`
- Body collection tier: `0`, metadata only
- Record output: `records/naver_news.jsonl`

### `nytimes`

Connected to the official New York Times Article Search API and Top Stories API.

- Credential: `NYTIMES_API_KEY`
- Article Search endpoint: `https://api.nytimes.com/svc/search/v2/articlesearch.json`
- Top Stories endpoint: `https://api.nytimes.com/svc/topstories/v2/{section}.json`
- Required NYT developer app products: Article Search API and Top Stories API
- Default article-search queries: global economy, central banks, China economy, artificial intelligence, semiconductors
- Default top-story sections: world, business, technology
- Body collection tier: `0`, metadata only
- Record output: `records/nytimes.jsonl`

### `newsapi`

Connected to the official NewsAPI.org Everything and Top Headlines APIs.

- Credential: `NEWSAPI_KEY`
- Everything endpoint: `https://newsapi.org/v2/everything`
- Top Headlines endpoint: `https://newsapi.org/v2/top-headlines`
- Default Everything queries: global economy, central banks, China economy, artificial intelligence, semiconductors, oil prices
- Default Top Headlines pairs: US business, US technology, GB business
- Body collection tier: `0`, metadata only
- Record output: `records/newsapi.jsonl`
- Note: NewsAPI's `content` field is treated as a truncated snippet, not article body storage.

### `ecos`

Connected to the official Bank of Korea ECOS Open API.

- Credential: `ECOS_API_KEY`
- Key statistics endpoint pattern: `https://ecos.bok.or.kr/api/KeyStatisticList/{api_key}/json/kr/1/100`
- Default collection: KeyStatisticList 1-100
- Body collection tier: `3`, official data record
- Record output: `records/ecos.jsonl`

### `kosis`

Connected to the official KOSIS OpenAPI statistics list API.

- Credential: `KOSIS_API_KEY`
- Statistics list endpoint: `https://kosis.kr/openapi/statisticsList.do?method=getList`
- Default collection: `vwCd=MT_ZTITLE`, `parentId=` root list
- Body collection tier: `3`, official data record
- Record output: `records/kosis.jsonl`
- Note: the adapter tries the raw key first and a base64-decoded 32-character hex key as a fallback because KOSIS key formats can be confusing across examples and issued values.

### `opendart`

Connected to the official OpenDART disclosure search API.

- Credential: `OPENDART_API_KEY`
- Disclosure list endpoint: `https://opendart.fss.or.kr/api/list.json`
- Default collection: recent disclosures from the last 7 days
- Body collection tier: `3`, official disclosure metadata
- Record output: `records/opendart.jsonl`
- Note: this adapter collects disclosure metadata only. Filing documents, attachments, and full report contents remain separate rights/need-based fetches.

### `fred`

Connected to the official Federal Reserve Economic Data API.

- Credential: `FRED_API_KEY`
- Series metadata endpoint: `https://api.stlouisfed.org/fred/series`
- Series observations endpoint: `https://api.stlouisfed.org/fred/series/observations`
- Default series: FEDFUNDS, DFF, DGS10, DGS2, CPIAUCSL, PCEPI, UNRATE, PAYEMS, GDPC1, INDPRO, RSAFS, HOUST
- Default collection: latest 12 observations per series, descending date order
- Body collection tier: `3`, official data record
- Record output: `records/fred.jsonl`

### `eia`

Connected to the official U.S. Energy Information Administration API v2.

- Credential: `EIA_API_KEY`
- Series endpoint pattern: `https://api.eia.gov/v2/seriesid/{series_id}`
- Default series: WTI spot, Brent spot, Henry Hub gas, U.S. retail gasoline, U.S. crude stocks, U.S. crude stocks excluding SPR, U.S. electricity generation
- Default collection: latest 12 observations per series
- Body collection tier: `3`, official data record
- Record output: `records/eia.jsonl`

### `un_comtrade`

Connected to the official UN Comtrade API.

- Credential: `UN_COMTRADE_KEY` or `COMTRADE_API_KEY`
- Data endpoint: `https://comtradeapi.un.org/data/v1/get/C/A/HS`
- Default reporters: Republic of Korea, United States, China, Japan, Germany
- Default partner: World
- Default second partner: World
- Default commodity: `TOTAL`
- Default flows: annual total exports and imports
- Default customs/mode filters: total customs procedure and total mode of transport
- Default period: current year minus 2, to favor a stable completed annual dataset
- Body collection tier: `3`, official data record
- Record output: `records/un_comtrade.jsonl`

## Next Implementation Step

Replace remaining placeholder source plans with real adapter results:

```text
planned -> fetched_metadata -> rights_checked -> fetched_body_if_allowed -> evidence_ready
```

Adapters should never bypass the source registry or rights gate.
