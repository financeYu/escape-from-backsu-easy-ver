"""Conservative source rights registry.

Unknown sources are treated as metadata-only so article bodies cannot be
stored unless a source is explicitly classified with stronger rights.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class SourceRights:
    body_collection_tier: int
    license_basis: str
    retention_days: int | None
    quote_policy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


UNKNOWN_SOURCE_RIGHTS = SourceRights(
    body_collection_tier=0,
    license_basis="unknown",
    retention_days=0,
    quote_policy="no_article_body",
)

METADATA_ONLY_RIGHTS = SourceRights(
    body_collection_tier=0,
    license_basis="metadata_only",
    retention_days=0,
    quote_policy="no_article_body",
)

OFFICIAL_DATA_RIGHTS = SourceRights(
    body_collection_tier=3,
    license_basis="public_official_data",
    retention_days=None,
    quote_policy="official_data_excerpt",
)


_NEWS_DISCOVERY_SOURCE_IDS: frozenset[str] = frozenset(
    {
        "naver_news",
        "newsapi",
        "nytimes",
    }
)

_NEWS_DISCOVERY_DOMAINS: frozenset[str] = frozenset(
    {
        "api.nytimes.com",
        "developer.nytimes.com",
        "newsapi.org",
        "openapi.naver.com",
    }
)

_OFFICIAL_DATA_SOURCE_IDS: frozenset[str] = frozenset(
    {
        "ecos",
        "eia",
        "fred",
        "kosis",
        "opendart",
        "un_comtrade",
    }
)

_OFFICIAL_DATA_DOMAINS: frozenset[str] = frozenset(
    {
        "api.eia.gov",
        "api.stlouisfed.org",
        "bok.or.kr",
        "comtradeapi.un.org",
        "dart.fss.or.kr",
        "ecos.bok.or.kr",
        "fred.stlouisfed.org",
        "kosis.kr",
    }
)


def lookup_source_rights(
    domain: str = "",
    api_source_id: str = "",
    source_name: str = "",
) -> SourceRights:
    """Return conservative body collection rights for a source.

    Args:
        domain: Publisher/API domain or URL.
        api_source_id: Adapter source id, catalog id, or upstream API source id.
        source_name: Human-readable source name. It is currently used only as a
            fallback signal for official sources that already have explicit ids.
    """

    normalized_domain = _normalize_domain(domain)
    normalized_source_id = _normalize_key(api_source_id)
    normalized_source_name = _normalize_key(source_name)

    if normalized_source_id in _OFFICIAL_DATA_SOURCE_IDS:
        return OFFICIAL_DATA_RIGHTS
    if normalized_domain in _OFFICIAL_DATA_DOMAINS:
        return OFFICIAL_DATA_RIGHTS
    if _has_parent_domain(normalized_domain, _OFFICIAL_DATA_DOMAINS):
        return OFFICIAL_DATA_RIGHTS
    if normalized_source_name in _OFFICIAL_DATA_SOURCE_IDS:
        return OFFICIAL_DATA_RIGHTS

    if normalized_source_id in _NEWS_DISCOVERY_SOURCE_IDS:
        return METADATA_ONLY_RIGHTS
    if normalized_domain in _NEWS_DISCOVERY_DOMAINS:
        return METADATA_ONLY_RIGHTS
    if _has_parent_domain(normalized_domain, _NEWS_DISCOVERY_DOMAINS):
        return METADATA_ONLY_RIGHTS

    return UNKNOWN_SOURCE_RIGHTS


def _normalize_domain(value: str) -> str:
    text = value.strip().lower()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = parsed.netloc or parsed.path
    if "@" in host:
        host = host.rsplit("@", 1)[-1]
    if ":" in host:
        host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host.strip(".")


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _has_parent_domain(domain: str, known_domains: frozenset[str]) -> bool:
    if not domain:
        return False
    return any(domain.endswith(f".{known_domain}") for known_domain in known_domains)
