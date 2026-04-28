"""Normalize collected source JSONL records into Evidence candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from content_research.sources.copyright import decide_storage, lookup_source_rights


NEWS_SOURCE_IDS = frozenset({"naver_news", "newsapi", "nytimes"})
OFFICIAL_DATA_SOURCE_IDS = frozenset({"ecos", "eia", "fred", "kosis", "opendart", "un_comtrade"})
MVP_EVIDENCE_SOURCE_IDS = NEWS_SOURCE_IDS | OFFICIAL_DATA_SOURCE_IDS
NON_EVIDENCE_STATUSES = frozenset(
    {
        "planned",
        "planned_non_mvp",
        "skipped",
        "missing_credentials",
        "missing_handler",
        "error",
    }
)


@dataclass(frozen=True)
class EvidenceCandidate:
    source_id: str | None
    source_name: str | None
    publisher_or_institution: str | None
    title_or_indicator: str | None
    url: str | None
    published_or_observed_at: str | None
    collected_at: str | None
    accessed_at: str | None
    value: str | None
    unit: str | None
    snippet: str | None
    rights_status: dict[str, Any]
    confidence: float
    field_status: dict[str, str]
    evidence_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_jsonl_file(path: str | Path) -> list[EvidenceCandidate]:
    """Read source records from a JSONL file and return Evidence candidates."""

    return normalize_jsonl_lines(Path(path).read_text(encoding="utf-8").splitlines())


def normalize_jsonl_lines(lines: Iterable[str]) -> list[EvidenceCandidate]:
    """Normalize JSONL lines, skipping blank lines and malformed JSON records."""

    candidates: list[EvidenceCandidate] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and _is_evidence_input_record(record):
            candidates.append(normalize_record(record))
    return candidates


def candidates_to_jsonl(candidates: Iterable[EvidenceCandidate]) -> str:
    """Serialize Evidence candidates as JSONL."""

    return "\n".join(json.dumps(candidate.to_dict(), ensure_ascii=False) for candidate in candidates)


def normalize_record(record: dict[str, Any]) -> EvidenceCandidate:
    """Normalize a single collected source record."""

    source_id = _none_if_missing(record.get("source_id"))
    rights_status = _rights_status(record)

    return EvidenceCandidate(
        source_id=source_id,
        source_name=_source_name(record),
        publisher_or_institution=_publisher_or_institution(record),
        title_or_indicator=_title_or_indicator(record),
        url=_url(record),
        published_or_observed_at=_published_or_observed_at(record),
        collected_at=_collected_at(record),
        accessed_at=_accessed_at(record),
        value=_value(record),
        unit=_unit(record),
        snippet=_snippet(record),
        rights_status=rights_status,
        confidence=_confidence(record, rights_status),
        field_status=_field_status(record),
        evidence_id=_evidence_id(record),
    )


def _is_evidence_input_record(record: dict[str, Any]) -> bool:
    if _as_str(record.get("type")) in {"collection_run", "source_result"}:
        return False
    if _as_str(record.get("status")) in NON_EVIDENCE_STATUSES:
        return False
    source_id = _as_str(record.get("source_id"))
    return source_id in MVP_EVIDENCE_SOURCE_IDS


def _rights_status(record: dict[str, Any]) -> dict[str, Any]:
    rights = lookup_source_rights(
        domain=_domain_for_rights(record),
        api_source_id=_as_str(record.get("source_id")),
        source_name=_source_name_for_rights(record),
    )
    decision = decide_storage(rights)
    return {
        **rights.to_dict(),
        **decision.to_dict(),
    }


def _publisher_or_institution(record: dict[str, Any]) -> str | None:
    source_id = _as_str(record.get("source_id"))
    if source_id == "newsapi":
        return _first_present(record, "source_name", "source_api_id") or None
    if source_id == "nytimes":
        return "The New York Times"
    if source_id == "naver_news":
        return _domain_from_url(_first_present(record, "original_link", "link"))
    if source_id == "fred":
        return "Federal Reserve Bank of St. Louis"
    if source_id == "eia":
        return "U.S. Energy Information Administration"
    if source_id == "un_comtrade":
        return "UN Comtrade"
    if source_id == "ecos":
        return "Bank of Korea ECOS"
    if source_id == "kosis":
        return "KOSIS"
    if source_id == "opendart":
        return "OpenDART"
    return _first_present(record, "publisher", "institution", "source_name") or None


def _source_name(record: dict[str, Any]) -> str | None:
    return (
        _first_present(
            record,
            "source_name",
            "publisher",
            "institution",
            "source_api_id",
        )
        or _publisher_or_institution(record)
        or None
    )


def _title_or_indicator(record: dict[str, Any]) -> str | None:
    source_id = _as_str(record.get("source_id"))
    if source_id == "eia":
        return _first_present(record, "series_description", "series_id")
    if source_id == "un_comtrade":
        return _join_nonempty(
            _first_present(record, "commodity_name", "commodity_code"),
            _first_present(record, "flow_name"),
            _first_present(record, "reporter_name"),
        )
    if source_id == "opendart":
        return _join_nonempty(_first_present(record, "corp_name"), _first_present(record, "report_name"))
    return (
        _first_present(
            record,
            "title",
            "indicator_name",
            "statistic_name",
            "series_id",
            "stat_name",
            "item_name",
            "table_name",
            "list_name",
        )
        or None
    )


def _url(record: dict[str, Any]) -> str | None:
    source_id = _as_str(record.get("source_id"))
    if source_id == "naver_news":
        return _first_present(record, "original_link", "link") or None
    if source_id == "fred":
        series_id = _first_present(record, "series_id")
        if series_id:
            return f"https://fred.stlouisfed.org/series/{series_id}"
    if source_id == "eia":
        series_id = _first_present(record, "series_id")
        if series_id:
            return f"https://www.eia.gov/opendata/browser/{series_id}"
    if source_id == "un_comtrade":
        return "https://comtradeplus.un.org/"
    return _first_present(record, "url", "link", "web_url") or None


def _published_or_observed_at(record: dict[str, Any]) -> str | None:
    return (
        _first_present(
            record,
            "published_at",
            "observation_date",
            "period",
            "published_date",
            "pub_date",
            "rcept_dt",
            "cycle",
            "updated_at",
            "send_de",
            "last_updated",
        )
        or None
    )


def _collected_at(record: dict[str, Any]) -> str | None:
    return (
        _first_present(
            record,
            "collected_at",
            "retrieved_at",
            "fetched_at",
            "created_at",
        )
        or None
    )


def _accessed_at(record: dict[str, Any]) -> str | None:
    return (
        _first_present(
            record,
            "accessed_at",
            "last_accessed_at",
            "retrieved_at",
            "fetched_at",
            "collected_at",
        )
        or None
    )


def _value(record: dict[str, Any]) -> str | None:
    source_id = _as_str(record.get("source_id"))
    if source_id == "un_comtrade":
        return _first_present(record, "primary_value", "quantity", "net_weight") or None
    return _first_present(record, "value", "data_value", "obs_value", "amount") or None


def _unit(record: dict[str, Any]) -> str | None:
    source_id = _as_str(record.get("source_id"))
    if source_id == "un_comtrade" and _first_present(record, "primary_value"):
        return "USD"
    return _first_present(record, "unit", "unit_name", "units", "units_short", "quantity_unit") or None


def _snippet(record: dict[str, Any]) -> str | None:
    source_id = _as_str(record.get("source_id"))
    if source_id in NEWS_SOURCE_IDS:
        return (
            _first_present(record, "content_snippet", "description", "snippet", "abstract")
            or None
        )
    if source_id == "eia":
        return _join_nonempty(
            _first_present(record, "area_name"),
            _first_present(record, "product_name"),
            _first_present(record, "process_name"),
        )
    if source_id == "un_comtrade":
        return _join_nonempty(
            _first_present(record, "reporter_name"),
            _first_present(record, "partner_name"),
            _first_present(record, "flow_name"),
        )
    return _first_present(record, "summary", "notes", "description") or None


def _confidence(record: dict[str, Any], rights_status: dict[str, Any]) -> float:
    source_id = _as_str(record.get("source_id"))
    if source_id in OFFICIAL_DATA_SOURCE_IDS:
        return 0.9 if _value(record) and _published_or_observed_at(record) else 0.75
    if source_id in NEWS_SOURCE_IDS:
        return 0.65 if _url(record) and _title_or_indicator(record) else 0.5
    if rights_status.get("license_basis") == "unknown":
        return 0.4
    return 0.5


def _evidence_id(record: dict[str, Any]) -> str | None:
    return _none_if_missing(record.get("evidence_id"))


def _field_status(record: dict[str, Any]) -> dict[str, str]:
    source_id = _as_str(record.get("source_id"))
    values = {
        "issue_title": _title_or_indicator(record),
        "published_or_observed_at": _published_or_observed_at(record),
        "source_name": _source_name(record),
        "source_url": _url(record),
        "collected_at": _collected_at(record),
        "accessed_at": _accessed_at(record),
        "key_number": _value(record),
        "unit": _unit(record),
        "snippet_or_context": _snippet(record),
    }
    optional_by_source = {
        "key_number": source_id in NEWS_SOURCE_IDS,
        "unit": source_id in NEWS_SOURCE_IDS,
        "snippet_or_context": source_id in OFFICIAL_DATA_SOURCE_IDS,
    }
    return {
        field: _status_for(value, unsupported=optional_by_source.get(field, False))
        for field, value in values.items()
    }


def _status_for(value: str | None, *, unsupported: bool = False) -> str:
    if value:
        return "present"
    if unsupported:
        return "unsupported"
    return "missing"


def _domain_for_rights(record: dict[str, Any]) -> str:
    return _domain_from_url(_url(record) or "") or _first_present(record, "domain")


def _source_name_for_rights(record: dict[str, Any]) -> str:
    return _first_present(record, "source_name", "publisher", "institution")


def _first_present(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _none_if_missing(value: Any) -> str | None:
    text = _as_str(value)
    return text or None


def _domain_from_url(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = parsed.netloc or parsed.path
    if "@" in host:
        host = host.rsplit("@", 1)[-1]
    if ":" in host:
        host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host.strip(".") or None


def _join_nonempty(*values: str) -> str | None:
    parts = [value for value in values if value]
    if not parts:
        return None
    return " / ".join(parts)
