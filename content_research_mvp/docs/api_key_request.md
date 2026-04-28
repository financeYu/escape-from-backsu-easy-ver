# API Key Request for Data Collection

## Purpose

The hourly collection process needs API keys and licensed-feed credentials before real network collection can be enabled.

Put real values in a local `.env` file copied from `.env.example`. Do not paste real keys into Markdown, Git commits, screenshots, or chat logs unless you intentionally want them exposed.

## Minimum Keys for Phase 1

These are the practical first keys to request. They enable Korean and international news discovery plus basic fact verification.

| Priority | Environment Variable | Provider | Use |
|---:|---|---|---|
| 1 | `NAVER_CLIENT_ID` | Naver Developers | Korean news search metadata |
| 1 | `NAVER_CLIENT_SECRET` | Naver Developers | Korean news search authentication |
| 1 | `NYTIMES_API_KEY` | New York Times Developer | NYT article metadata, abstracts, lead paragraphs |
| 1 | `ECOS_API_KEY` | Bank of Korea ECOS | Korean macro and financial statistics |
| 1 | `KOSIS_API_KEY` | KOSIS | Korean official statistics |
| 1 | `OPENDART_API_KEY` | OpenDART | Korean company filings |
| 2 | `NEWSAPI_KEY` | NewsAPI | Supplementary international news discovery |
| 2 | `FRED_API_KEY` | FRED | US macro and financial time series |
| 2 | `UN_COMTRADE_KEY` | UN Comtrade | International trade data |
| 2 | `EIA_API_KEY` | US EIA | Energy data |
| 2 | `DATA_GO_KR_API_KEY` | data.go.kr | Korean public datasets |

## Licensed or Enterprise Keys

These should be requested only if the project has a paid subscription or institutional license. Do not enable full-body collection until the license terms are registered in the source registry.

| Environment Variable | Provider | Use |
|---|---|---|
| `GUARDIAN_API_KEY` | Guardian Open Platform Commercial / Rights Managed | Guardian metadata and article fields when commercial terms allow |
| `LSEG_APP_KEY` | LSEG / Reuters | Reuters news access |
| `LSEG_RDP_USERNAME` | LSEG / Reuters | Reuters/LSEG platform login |
| `LSEG_RDP_PASSWORD` | LSEG / Reuters | Reuters/LSEG platform login |
| `AP_API_KEY` | Associated Press | AP licensed content/API |
| `BLOOMBERG_LICENSE_CLIENT_ID` | Bloomberg | Bloomberg Data License |
| `BLOOMBERG_LICENSE_CLIENT_SECRET` | Bloomberg | Bloomberg Data License |
| `DOW_JONES_API_KEY` | Dow Jones / WSJ | Dow Jones News API |
| `FT_LICENSE_KEY` | Financial Times | FT licensed feed/API |
| `BIGKINDS_KEY` | BIGKinds / NewsStore | Korean news archive/API depending on agreement |

## Optional or Usually No-Key Sources

These can often be used without a key or with separate authorization depending on endpoint and terms.

| Source | Key Needed | Use |
|---|---|---|
| GDELT DOC 2.0 | No | Global news discovery and trend radar |
| 대한민국 정책브리핑 RSS | No | Korean government policy triggers |
| World Bank Indicators API | Usually no | Global macro indicators |
| IMF Data API | Usually no, endpoint-dependent | Global macro data |
| OECD Data API | Usually no, endpoint-dependent | OECD indicators |
| Publisher RSS feeds | Usually no | Metadata-only issue radar |
| `NPR_CDS_TOKEN` | Optional authorization | NPR Content Distribution Service when authorized |

## User Request Message

Please provide the following keys in a local `.env` file at the project root:

```text
content_research_mvp/.env
```

Recommended first batch:

```text
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
NYTIMES_API_KEY=
ECOS_API_KEY=
KOSIS_API_KEY=
OPENDART_API_KEY=
NEWSAPI_KEY=
FRED_API_KEY=
UN_COMTRADE_KEY=
EIA_API_KEY=
DATA_GO_KR_API_KEY=
```

If you have licensed news contracts, also add:

```text
GUARDIAN_API_KEY=
LSEG_APP_KEY=
LSEG_RDP_USERNAME=
LSEG_RDP_PASSWORD=
AP_API_KEY=
BLOOMBERG_LICENSE_CLIENT_ID=
BLOOMBERG_LICENSE_CLIENT_SECRET=
DOW_JONES_API_KEY=
FT_LICENSE_KEY=
BIGKINDS_KEY=
```

## Safety Rules

- `.env` is ignored by Git.
- `.env.example` is safe to commit because it contains no secrets.
- API keys should be loaded at runtime from environment variables.
- The source registry must still decide whether a source is metadata-only, temporary text, licensed archive, or open/public-license text.
- Having an API key does not automatically allow full article-body storage.

## Provider-Specific Activation Notes

- New York Times: the key must be attached to both Article Search API and Top Stories API in the NYT developer app. If either product is not enabled, the API may return `Invalid ApiKey for given resource`.
- Guardian: treat Guardian as paid/licensed for this project. The free Developer tier is non-commercial; commercial use, text/data mining, AI-derived uses, and broader content use require the appropriate Commercial, Rights Managed, or Full Access arrangement.
- KOSIS: if the API returns `유효하지않은 인증KEY입니다.`, confirm that the key is active for KOSIS OpenAPI and not only copied from a registration screen before approval. The adapter tries both raw and base64-decoded key forms.
