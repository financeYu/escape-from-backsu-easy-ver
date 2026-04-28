# Content Research Data Collection Design

## 1. Goal

Design a data collection layer for the Research Master Agent that can collect international and Korean current affairs and economy materials, including article bodies when permitted, while controlling copyright, license, attribution, and redistribution risk.

This design supports research briefs only. It does not produce PPT plans, scripts, titles, thumbnails, or video packaging.

## 2. Collection Principles

- Collect metadata broadly, collect full text narrowly.
- Prefer official APIs, RSS feeds, licensed data providers, and public datasets.
- Treat news article bodies as copyrighted by default unless an API license, site terms, or explicit permission allows use.
- Store source URL, publisher, author, publication time, collection time, license status, and retrieval method for every item.
- Never republish full article text in user-facing output.
- Use article body text for internal research, fact extraction, clustering, and source comparison only when the copyright gate allows it.
- Keep generated briefs transformative: summarize facts, context, uncertainty, and sources in original language.

## 3. Source Classes

### A. News Discovery APIs

Use these for issue radar and article discovery.

| Source | Coverage | Body Access | Role | Notes |
|---|---|---:|---|---|
| Naver Search API News | Korean portal-indexed news | No full body; title, link, original link, snippet, publication time | Korean news discovery | Good for Korean issue radar and duplicate URL discovery. |
| GDELT DOC 2.0 / Context 2.0 | Global multilingual news web | Search/snippets and article URLs, not a republication license for body text | International issue radar | Useful for global trend detection and source diversity. |
| NewsAPI | Global news discovery | Truncated content where available | International news discovery | Terms prohibit using the service to reproduce or republish copyrighted material. |
| BIGKinds | Korean news archive and analysis | Depends on service/API/usage agreement | Korean media analysis | Use only according to BIGKinds/NewsStore terms or licensed agreement. |
| Publisher-specific APIs | NYT, Guardian, Reuters, AP, etc. | Depends on API terms | High-quality source-specific ingestion | Use only where terms allow storage/analysis. |

### A-1. Overseas Publisher Source Registry

Use this registry as the first overseas watchlist. These sources should be collected through official APIs, RSS feeds, licensed feeds, or metadata search by domain. Do not treat a famous publisher as automatically safe for full-body collection.

| Source | Primary Focus | Preferred Access | Default Body Tier | Notes |
|---|---|---|---:|---|
| The New York Times | US, world, politics, business, technology | NYT Article Search API, Top Stories API, Archive API, domain search | 0 | Use headline, abstract, lead paragraph, metadata, and URL unless separate rights allow more. |
| The Guardian | World, UK, US, business, technology, climate | Guardian Open Platform Commercial / Rights Managed / Full Access | 0 until licensed; 2 after registry approval | Treat as paid/licensed for this project. Free Developer access is non-commercial and should not be used as the default collection path. |
| Reuters | Global breaking news, markets, companies, commodities, central banks | LSEG Reuters News / News API / SFTP | 2 | Enterprise entitlement required. Treat as licensed text only. |
| Associated Press | Global wire, US politics, world, business | AP licensed content/API services | 2 | Use only with AP contract/API entitlement. |
| Bloomberg | Global business, markets, policy, companies | Bloomberg Data License / Enterprise Access Point | 2 | Enterprise data license; may include news and data delivery via REST/SFTP/cloud. |
| Dow Jones / Wall Street Journal | US/world business, markets, companies, policy | Dow Jones News API / licensed feed | 2 | Subscription/entitlement required; includes WSJ/Dow Jones content depending on package. |
| Financial Times | Global economy, companies, markets, geopolitics | Licensed FT feed/API if available; otherwise metadata/domain discovery | 0 or 2 | Default metadata-only unless licensed. Paywall and terms must be respected. |
| The Economist | International affairs, finance/economics, business | Metadata/domain discovery or licensed syndication | 0 or 2 | Default metadata-only; use for issue discovery and context triangulation. |
| BBC News | World, UK, business, technology, public-service coverage | RSS or metadata/domain discovery | 0 | Use headline, summary, URL. Do not store full article bodies without permission. |
| CNN / CNN Business | US/world breaking news, business, markets | CNN RSS where allowed, metadata/domain discovery | 0 | CNNMoney RSS terms limit use; default metadata-only. |
| CNBC | Markets, business, economy, technology | RSS/domain discovery, licensed services if available | 0 | Good for market/economy radar; avoid turning into investment signal output. |
| NPR | US/world, policy, economy, public radio features | NPR RSS, CDS API where authorized | 0 or 2 | CDS requires authorization and terms compliance. RSS is metadata/summary-first. |
| Washington Post | US politics, world, economy, policy | RSS where allowed, metadata/domain discovery | 0 | RSS/commercial uses require careful terms review. |
| POLITICO | US/EU politics, policy, trade, technology, energy | RSS/domain discovery, licensed Pro products if needed | 0 or 2 | Strong policy radar source; default metadata-only. |
| Axios | US policy, business, tech, energy, AI | RSS/domain discovery | 0 | Use as fast issue radar; verify elsewhere. |
| Foreign Affairs | Geopolitics, international relations, trade, security | RSS/domain discovery, subscription/licensed access | 0 | Analysis source, not primary fact source. |
| Le Monde | France, Europe, world, economy | Official RSS | 0 | RSS terms are personal/non-commercial unless authorized. |
| Nikkei Asia | Asia economy, Japan, China, supply chains, technology | Official RSS, licensed access | 0 | RSS is for personal noncommercial headline viewing; use metadata only unless licensed. |
| Al Jazeera | Middle East, Global South, conflict, energy, geopolitics | RSS/domain discovery | 0 | Useful perspective source; verify conflict claims with multiple sources. |
| Deutsche Welle | Germany, Europe, global public broadcaster coverage | RSS/domain discovery | 0 | Useful for Europe/global public media perspective. |
| South China Morning Post | China, Hong Kong, Asia business and geopolitics | Metadata/domain discovery, licensed access if available | 0 or 2 | Good China/Asia radar source; paywall and rights review needed. |
| Japan Times | Japan politics, economy, society | RSS/domain discovery | 0 | Use for Japan radar; verify numbers with official Japanese sources. |
| Straits Times | Singapore, ASEAN, Asia economy | Metadata/domain discovery, licensed access if available | 0 or 2 | Useful ASEAN lens; default metadata-only. |
| The Hindu / Indian Express / Economic Times | India politics, economy, technology | RSS/domain discovery | 0 | Use to track India; verify official numbers with RBI, MOSPI, government sources. |
| Caixin / Sixth Tone | China economy, society, companies | Metadata/domain discovery, licensed access if available | 0 or 2 | Use for China context; verify against official data and multiple reports. |

Default rule: if a publisher is not explicitly licensed or open for body storage, set `body_collection_tier = 0` and collect only metadata, URL, snippet/summary, and publisher/date fields.

### B. Government, Institution, and Policy Sources

Use these for official facts, policy announcements, and source-of-truth verification.

| Source | Coverage | Role |
|---|---|---|
| 대한민국 정책브리핑 RSS | Korean government policy news and releases | Policy/news trigger collection and official confirmation |
| Bank of Korea ECOS API | Korean macro, rates, financial statistics | Fact verification and charts |
| KOSIS OpenAPI | Korean official statistics | Population, labor, prices, industry, household data |
| OpenDART API | Korean corporate filings | Company-related fact verification |
| data.go.kr APIs | Korean public datasets | Trade, customs, sector data, ministry data |
| Customs / trade statistics APIs | Korean import/export data | Supply-chain and trade verification |

### C. International Data APIs

Use these to verify macro and geopolitical-economic claims.

| Source | Coverage | Role |
|---|---|---|
| World Bank Indicators API | Global development and macro indicators | Long-run macro context |
| IMF Data APIs / DataMapper API | WEO, financial, exchange-rate, macro datasets | Global macro verification |
| OECD Data API | OECD indicators via SDMX | Advanced economies and policy context |
| FRED API | US macro and financial time series | US rates, inflation, labor, financial indicators |
| ECB / Eurostat APIs | Eurozone macro and official statistics | Europe-related verification |
| EIA API | Energy data | Oil, gas, electricity, inventory data |
| UN Comtrade API | Trade flows | Supply-chain and trade verification |

## 4. Article Body Collection Policy

Article bodies may be collected only after passing a copyright and access gate.

### Allowed Body Collection Tiers

| Tier | Condition | Storage Rule | Use Rule |
|---|---|---|---|
| Tier 0: Metadata only | No clear body-use permission | Store title, URL, publisher, time, snippet, tags | Use link and snippet only; do not fetch body |
| Tier 1: Ephemeral extraction | Body is publicly accessible, robots/terms do not forbid access, no license for persistent storage | Store temporary text cache for short TTL only | Use for internal extraction; delete raw text after summarization |
| Tier 2: Licensed internal archive | API/license/subscription allows internal storage and analysis | Store raw body with license metadata | Use for internal research; do not republish full text |
| Tier 3: Open/public-license text | Public-domain, government-created, Creative Commons, or explicit open license | Store raw body and license | Use according to license; still cite source |

Default to Tier 0 when permission is unclear.

## 5. Copyright Gate

Before article body ingestion, run these checks:

1. Source permission
   - Is the text from an API or RSS feed that explicitly allows body access?
   - Does the publisher/license allow storage, analysis, or reuse?
   - Is this a paid/licensed database with allowed internal research use?

2. Site access and technical policy
   - Check robots.txt and site terms where feasible.
   - Respect paywalls, login walls, rate limits, and anti-bot controls.
   - Do not bypass access controls.

3. Content type
   - Official public-sector releases can often be safer, but still record the applicable use terms.
   - News articles are copyrighted by default.
   - Photos, videos, charts, and graphics require separate rights handling.

4. Storage scope
   - Store full body only when Tier 2 or Tier 3.
   - For Tier 1, store temporary text only with TTL and hash-based deduplication.
   - For Tier 0, store metadata and source link only.

5. Output scope
   - Never output full article bodies.
   - Quote only short excerpts when necessary.
   - Prefer paraphrase, attribution, and source links.

## 6. Body Ingestion Pipeline

```text
Seed queries / RSS feeds / official API feeds
  -> Article metadata collector
  -> URL canonicalizer and duplicate detector
  -> Source registry lookup
  -> Copyright gate
  -> Body fetcher, only if allowed tier permits
  -> Boilerplate cleaner
  -> Claim and number extractor
  -> Source attribution mapper
  -> Raw text retention policy
  -> EvidenceCard builder
```

## 7. Source Registry

Maintain a `source_registry` table or file with:

| Field | Meaning |
|---|---|
| `source_id` | Stable internal identifier |
| `publisher` | Publisher or institution name |
| `domain` | Canonical domain |
| `source_type` | news, official, data_api, filing, report, rss |
| `discovery_method` | API, RSS, sitemap, manual, licensed feed |
| `body_collection_tier` | 0, 1, 2, or 3 |
| `license_basis` | API terms, subscription, open license, public-sector terms, unknown |
| `raw_text_retention_days` | 0 for metadata-only, short TTL for Tier 1 |
| `quote_limit_policy` | short excerpt only, no quote, licensed quote rules |
| `attribution_required` | required attribution format |
| `notes` | special restrictions |
| `last_reviewed_at` | date terms were checked |

Every fetch decision should be traceable to this registry.

## 8. Evidence Record

Each collected item should become an EvidenceCard-compatible record:

```json
{
  "source_id": "",
  "publisher": "",
  "title": "",
  "url": "",
  "canonical_url": "",
  "author": "",
  "published_at": "",
  "collected_at": "",
  "language": "",
  "country_or_region": "",
  "topic_tags": [],
  "retrieval_method": "api|rss|licensed_feed|manual|web_fetch",
  "body_collection_tier": 0,
  "license_basis": "",
  "raw_text_storage": "none|ttl_cache|licensed_archive|open_archive",
  "raw_text_ttl_days": 0,
  "content_hash": "",
  "snippet": "",
  "extracted_claims": [],
  "extracted_numbers": [],
  "uncertainty_notes": [],
  "rights_notes": []
}
```

## 9. Recommended API Stack

### Phase 1: Low-Risk Issue Radar

- Naver Search API News for Korean media discovery.
- 대한민국 정책브리핑 RSS for government policy triggers.
- GDELT DOC 2.0 / Context 2.0 for international media radar.
- NewsAPI only as supplementary discovery, respecting its anti-republication terms.
- NYT Article Search and Top Stories APIs for New York Times metadata and lead-paragraph discovery.
- Publisher RSS/domain monitors for BBC, CNN, CNBC, NPR, Washington Post, POLITICO, Axios, Le Monde, Nikkei Asia, Al Jazeera, DW, and other selected international outlets.

Output: metadata, URLs, snippets, issue clusters, source diversity map.

### Phase 2: Official Fact Verification

- ECOS for Korean macro and financial statistics.
- KOSIS for Korean official statistics.
- OpenDART for company filings.
- data.go.kr and customs/trade APIs for public datasets.
- World Bank, IMF, OECD, FRED, Eurostat, ECB, EIA, UN Comtrade for international data.

Output: verified facts, numbers, as-of dates, source links.

### Phase 3: Controlled Body Collection

- Tier 2 licensed feeds first.
- Tier 3 open/public-license sources second.
- Tier 1 temporary extraction only when legally and technically permitted.
- Tier 0 metadata-only for all unclear sources.
- Guardian Commercial/Rights Managed/Full Access, Reuters/LSEG, AP, Bloomberg, Dow Jones/WSJ, FT, Economist, Nikkei Asia, SCMP, Straits Times, and similar paid publishers stay metadata-only until a license is registered in `source_registry`.

Output: claim extraction, duplicate detection, summary notes, no full-text redistribution.

## 10. Copyright Risk Controls

- Keep a hard separation between raw source text and generated research brief.
- Store raw body text only in a restricted internal store.
- Attach license and retention metadata to every raw text record.
- Run periodic deletion for Tier 1 temporary text.
- Keep source links and attribution in all EvidenceCards.
- Block export of raw article text to Markdown, PPT, script, or user-facing reports.
- Add an automated check that flags copied passages above the allowed excerpt threshold.
- Keep images, charts, and videos out of ingestion unless rights are separately cleared.

## 11. Implementation Modules

Recommended source package additions:

```text
src/content_research/sources/
  news_discovery/
    naver_news.py
    gdelt.py
    newsapi.py
    nytimes.py
    guardian.py
    publisher_rss.py
    publisher_domain_monitor.py
    policy_briefing_rss.py
  licensed_news/
    reuters_lseg.py
    associated_press.py
    bloomberg_data_license.py
    dow_jones.py
    financial_times.py
  official_data/
    ecos.py
    kosis.py
    opendart.py
    worldbank.py
    imf.py
    fred.py
    eia.py
    un_comtrade.py
  copyright/
    source_registry.py
    rights_gate.py
    robots_policy.py
    retention.py
  extraction/
    article_body_fetcher.py
    boilerplate_cleaner.py
    claim_extractor.py
    number_extractor.py
```

## 12. Environment Variables

```text
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
NEWSAPI_KEY
BIGKINDS_KEY
NYTIMES_API_KEY
GUARDIAN_API_KEY
NPR_CDS_TOKEN
LSEG_APP_KEY
LSEG_RDP_USERNAME
LSEG_RDP_PASSWORD
AP_API_KEY
BLOOMBERG_LICENSE_CLIENT_ID
DOW_JONES_API_KEY
FT_LICENSE_KEY
KOSIS_API_KEY
ECOS_API_KEY
OPENDART_API_KEY
FRED_API_KEY
WORLD_BANK_API_KEY_OPTIONAL
IMF_API_AUTH_OPTIONAL
UN_COMTRADE_KEY
```

Keys should be optional per adapter. The pipeline should degrade to sources that are configured.

## 13. Final Recommendation

Use a two-layer system:

1. News radar layer: fast, broad, mostly metadata and snippets.
2. Verification layer: official datasets, filings, reports, and licensed/open article bodies.

Do not rely on full article scraping as the default. Use body collection only when the source registry marks the source as allowed and the copyright gate passes.

This gives the Research Master Agent enough material to find important issues and verify them without turning the project into an unauthorized news database.

Implemented live metadata adapters:

- `naver_news`: Naver News Search API
- `newsapi`: NewsAPI.org Everything and Top Headlines APIs
- `nytimes`: New York Times Article Search API and Top Stories API
- `ecos`: Bank of Korea ECOS KeyStatisticList
- `kosis`: KOSIS statisticsList root catalog
- `opendart`: OpenDART disclosure list for recent filings
- `fred`: FRED official US macro and financial time-series observations
- `eia`: EIA official US energy price, inventory, gas, gasoline, and electricity observations
- `un_comtrade`: UN Comtrade annual total import/export trade records

## 14. Reference Links

- Naver Search API News: https://developers.naver.com/docs/serviceapi/search/news/news.md
- Naver API Terms: https://developers.naver.com/products/intro/terms/terms.md
- NewsAPI Documentation: https://newsapi.org/docs
- NewsAPI Terms: https://newsapi.org/terms
- GDELT DOC 2.0: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- GDELT Context 2.0: https://blog.gdeltproject.org/announcing-the-gdelt-context-2-0-api/
- New York Times Developer APIs: https://developer.nytimes.com/
- New York Times Article Search API: https://developer.nytimes.com/docs/articlesearch-product/1/overview
- New York Times Top Stories API: https://developer.nytimes.com/docs/top-stories-product/1/overview
- Guardian Open Platform: https://open-platform.theguardian.com/
- Guardian Open Platform access levels: https://open-platform.theguardian.com/access
- Guardian Open Platform terms: https://www.theguardian.com/open-platform/terms-and-conditions
- Reuters News via LSEG: https://www.lseg.com/en/data-analytics/financial-data/news/reuters-news
- LSEG News API for Wealth: https://developers.lseg.com/en/api-catalog/refinitiv-data-platform/news-API
- Bloomberg Data License: https://professional.bloomberg.com/products/data/data-management/data-license/
- AP Metadata Services: https://www.ap.org/who-we-serve/media/metadata-services/
- CNNMoney RSS terms: https://money.cnn.com/services/rss/
- NPR Content Distribution Service: https://npr.github.io/content-distribution-service/
- Nikkei Asia RSS: https://info.asia.nikkei.com/rss
- Le Monde RSS feeds: https://www.lemonde.fr/en/about-us/article/2026/03/27/le-monde-rss-feeds_6751860_115.html
- BIGKinds: https://www.bigkinds.or.kr/v2/intro/index.do
- 대한민국 정책브리핑 RSS: https://www.korea.kr/etc/rss.do
- KOSIS OpenAPI: https://kosis.kr/openapi/index/
- ECOS API: https://ecos.bok.or.kr/api/
- OpenDART API: https://opendart.fss.or.kr/
- World Bank Indicators API: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
- IMF Data API: https://data.imf.org/en/Resource-Pages/IMF-API
- OECD Data API: https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html
- UN Comtrade API: https://comtradedeveloper.un.org/apis
- Korean Copyright Act reference: https://law.go.kr/LSW/lsRvsRsnListP.do?chrClsCd=010102&lsId=000798
