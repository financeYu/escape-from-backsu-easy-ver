"""Match issue candidates to already-collected official data Evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Iterable


OFFICIAL_DATA_SOURCE_IDS = frozenset({"ecos", "eia", "fred", "kosis", "opendart", "un_comtrade"})

_MATCH_RULES: tuple[dict[str, Any], ...] = (
    {
        "category": "energy_oil",
        "issue_keywords": (
            "oil",
            "crude",
            "energy",
            "wti",
            "brent",
            "gas",
            "inventory",
            "inventories",
            "유가",
            "원유",
            "에너지",
            "천연가스",
            "재고",
        ),
        "source_ids": ("eia",),
        "indicator_keywords": ("wti", "brent", "crude", "oil", "inventory", "stock", "gas", "원유", "유가", "재고"),
        "reason": "Energy/oil issue matched to EIA petroleum or energy indicators.",
        "confidence": 0.85,
    },
    {
        "category": "us_rates_prices_jobs",
        "issue_keywords": (
            "fed",
            "federal reserve",
            "interest rate",
            "rate cut",
            "rate hike",
            "inflation",
            "cpi",
            "pce",
            "jobs",
            "employment",
            "unemployment",
            "payroll",
            "미국 금리",
            "연준",
            "기준금리",
            "금리",
            "물가",
            "소비자물가",
            "고용",
            "실업",
        ),
        "source_ids": ("fred",),
        "indicator_keywords": (
            "federal funds",
            "interest rate",
            "cpi",
            "consumer price",
            "pce",
            "unemployment",
            "payroll",
            "employment",
            "금리",
            "소비자물가",
            "물가",
            "고용",
            "실업",
        ),
        "reason": "U.S. rates, prices, or labor issue matched to FRED macro indicators.",
        "confidence": 0.85,
    },
    {
        "category": "korea_macro",
        "issue_keywords": (
            "korea",
            "korean",
            "seoul",
            "kospi",
            "won",
            "consumer price",
            "inflation",
            "employment",
            "unemployment",
            "gdp",
            "한국",
            "국내",
            "서울",
            "원화",
            "코스피",
            "경기",
            "물가",
            "소비자물가",
            "고용",
            "실업",
        ),
        "source_ids": ("ecos", "kosis"),
        "indicator_keywords": (
            "korea",
            "consumer price",
            "inflation",
            "employment",
            "unemployment",
            "gdp",
            "industrial production",
            "retail sales",
            "한국",
            "경기",
            "소비자물가",
            "물가",
            "고용",
            "실업",
            "국내총생산",
            "산업생산",
            "소매판매",
        ),
        "reason": "Korea macro issue matched to ECOS or KOSIS official indicators.",
        "confidence": 0.8,
    },
    {
        "category": "trade",
        "issue_keywords": (
            "trade",
            "export",
            "exports",
            "import",
            "imports",
            "tariff",
            "supply chain",
            "무역",
            "수출",
            "수입",
            "수출입",
            "관세",
            "공급망",
        ),
        "source_ids": ("un_comtrade",),
        "indicator_keywords": ("export", "import", "trade", "total", "commodity", "수출", "수입", "무역", "품목"),
        "reason": "Trade issue matched to UN Comtrade import/export data.",
        "confidence": 0.85,
    },
)


@dataclass(frozen=True)
class DataMatch:
    issue_id: str
    matched_data: str | None
    indicator_name: str | None
    source_id: str | None
    observed_at: str | None
    value: str | None
    unit: str | None
    match_reason: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def match_issue_data(
    issue_candidates: Iterable[Any],
    data_candidates: Iterable[Any],
    *,
    limit_per_issue: int = 3,
) -> list[DataMatch]:
    """Connect issue candidates to official-data Evidence candidates."""

    if limit_per_issue <= 0:
        raise ValueError("limit_per_issue must be positive")

    data_records = [_as_record(candidate) for candidate in data_candidates]
    official_records = [record for record in data_records if _as_str(record.get("source_id")) in OFFICIAL_DATA_SOURCE_IDS]

    matches: list[DataMatch] = []
    for issue in issue_candidates:
        issue_record = _as_record(issue)
        issue_id = _as_str(issue_record.get("issue_id"))
        if not issue_id:
            continue
        issue_matches = _matches_for_issue(issue_record, official_records)
        matches.extend(issue_matches[:limit_per_issue])
    return matches


def _matches_for_issue(issue: dict[str, Any], data_records: list[dict[str, Any]]) -> list[DataMatch]:
    issue_text = _issue_text(issue)
    scored: list[tuple[float, str, DataMatch]] = []
    for rule in _MATCH_RULES:
        if not _contains_any(issue_text, rule["issue_keywords"]):
            continue
        for data_record in data_records:
            if _as_str(data_record.get("source_id")) not in rule["source_ids"]:
                continue
            indicator_text = _indicator_text(data_record)
            if not _contains_any(indicator_text, rule["indicator_keywords"]):
                continue
            match = _build_match(issue, data_record, rule)
            scored.append((match.confidence, match.observed_at or "", match))

    scored.sort(key=lambda item: (item[0], item[1], item[2].matched_data or ""), reverse=True)
    return [match for _, _, match in scored]


def _build_match(issue: dict[str, Any], data_record: dict[str, Any], rule: dict[str, Any]) -> DataMatch:
    value = _none_if_missing(data_record.get("value"))
    unit = _none_if_missing(data_record.get("unit"))
    observed_at = _none_if_missing(data_record.get("published_or_observed_at"))
    confidence = float(rule["confidence"])
    if not value or not unit or not observed_at:
        confidence = min(confidence, 0.55)
    return DataMatch(
        issue_id=_as_str(issue.get("issue_id")),
        matched_data=_data_id(data_record),
        indicator_name=_none_if_missing(data_record.get("title_or_indicator")),
        source_id=_none_if_missing(data_record.get("source_id")),
        observed_at=observed_at,
        value=value,
        unit=unit,
        match_reason=str(rule["reason"]),
        confidence=confidence,
    )


def _issue_text(issue: dict[str, Any]) -> str:
    titles = issue.get("representative_titles", [])
    if not isinstance(titles, list):
        titles = []
    tags = issue.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    parts = [
        _as_str(issue.get("issue_name")),
        _as_str(issue.get("trend_reason")),
        " ".join(_as_str(title) for title in titles),
        " ".join(_as_str(tag) for tag in tags),
    ]
    return " ".join(parts).casefold()


def _indicator_text(data_record: dict[str, Any]) -> str:
    parts = [
        _as_str(data_record.get("title_or_indicator")),
        _as_str(data_record.get("source_id")),
        _as_str(data_record.get("snippet")),
        _as_str(data_record.get("unit")),
    ]
    return " ".join(parts).casefold()


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def _contains_keyword(text: str, keyword: str) -> bool:
    normalized = keyword.casefold()
    if re.fullmatch(r"[0-9a-z ]+", normalized):
        pattern = rf"(?<![0-9a-z]){re.escape(normalized)}(?![0-9a-z])"
        return re.search(pattern, text) is not None
    return normalized in text


def _data_id(data_record: dict[str, Any]) -> str | None:
    explicit_id = _as_str(data_record.get("evidence_id"))
    if explicit_id:
        return explicit_id
    url = _as_str(data_record.get("url"))
    if url:
        return url
    source_id = _as_str(data_record.get("source_id")) or "data"
    indicator = _as_str(data_record.get("title_or_indicator"))
    observed_at = _as_str(data_record.get("published_or_observed_at"))
    digest = hashlib.sha1(f"{source_id}|{indicator}|{observed_at}".encode("utf-8")).hexdigest()[:10]
    return f"{source_id}:{digest}"


def _as_record(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, dict):
        return candidate
    to_dict = getattr(candidate, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        if isinstance(value, dict):
            return value
    return {}


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _none_if_missing(value: Any) -> str | None:
    text = _as_str(value)
    return text or None
