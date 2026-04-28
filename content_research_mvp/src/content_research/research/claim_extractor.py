"""Extract checkable claims, numbers, and dates from Evidence candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Iterable


OFFICIAL_DATA_SOURCE_IDS = frozenset({"ecos", "eia", "fred", "kosis", "opendart", "un_comtrade"})

_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])[-+]?\d+(?:,\d{3})*(?:\.\d+)?\s?(?:%|percent|dollars?|points?|bp|bps|USD|index)?",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"\b\d{4}(?:-\d{1,2}(?:-\d{1,2})?)?\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractedClaim:
    claim: str
    key_numbers: list[str]
    dates: list[str]
    source_id: str | None
    evidence_id: str | None
    needs_verification: bool
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_claims(evidence_candidates: Iterable[Any]) -> list[ExtractedClaim]:
    """Extract one concise, source-linked claim per Evidence candidate."""

    claims: list[ExtractedClaim] = []
    for candidate in evidence_candidates:
        record = _as_record(candidate)
        claim_text = _claim_text(record)
        if not claim_text:
            continue
        source_id = _none_if_missing(record.get("source_id"))
        key_numbers = _key_numbers(record, claim_text)
        dates = _dates(record, claim_text)
        needs_verification = _needs_verification(record, source_id, key_numbers, dates)
        confidence = _confidence(record, source_id, key_numbers, dates, needs_verification)
        claims.append(
            ExtractedClaim(
                claim=claim_text,
                key_numbers=key_numbers,
                dates=dates,
                source_id=source_id,
                evidence_id=_evidence_id(record),
                needs_verification=needs_verification,
                confidence=confidence,
            )
        )
    return claims


def _claim_text(record: dict[str, Any]) -> str:
    title = _as_str(record.get("title_or_indicator") or record.get("title"))
    snippet = _as_str(record.get("snippet"))
    value = _as_str(record.get("value"))
    unit = _as_str(record.get("unit"))
    observed_at = _as_str(record.get("published_or_observed_at"))
    if value:
        subject = title or "Official data point"
        unit_part = f" {unit}" if unit else ""
        date_part = f" on {observed_at}" if observed_at else ""
        return _clean(f"{subject} was {value}{unit_part}{date_part}.")
    if title and snippet:
        return _clean(f"{title}: {snippet}")
    return _clean(title or snippet)


def _key_numbers(record: dict[str, Any], claim_text: str) -> list[str]:
    number_text = claim_text
    for date in _dates(record, claim_text):
        number_text = number_text.replace(date, " ")
    numbers = _unique(_clean_number(match.group(0)) for match in _NUMBER_RE.finditer(number_text))
    value = _as_str(record.get("value"))
    unit = _as_str(record.get("unit"))
    if value:
        value_with_unit = _clean(f"{value} {unit}") if unit else value
        numbers = [value_with_unit, value, *numbers]
    return _unique(numbers)


def _dates(record: dict[str, Any], claim_text: str) -> list[str]:
    dates = _unique(match.group(0).strip() for match in _DATE_RE.finditer(claim_text))
    observed_at = _as_str(record.get("published_or_observed_at"))
    if observed_at:
        dates.insert(0, observed_at)
    return _unique(dates)


def _needs_verification(
    record: dict[str, Any],
    source_id: str | None,
    key_numbers: list[str],
    dates: list[str],
) -> bool:
    if source_id not in OFFICIAL_DATA_SOURCE_IDS:
        return True
    if not key_numbers or not dates:
        return True
    rights = record.get("rights_status")
    if isinstance(rights, dict) and rights.get("allowed") is False:
        return True
    return False


def _confidence(
    record: dict[str, Any],
    source_id: str | None,
    key_numbers: list[str],
    dates: list[str],
    needs_verification: bool,
) -> float:
    base = float(record.get("confidence") or 0.5)
    if source_id in OFFICIAL_DATA_SOURCE_IDS and key_numbers and dates:
        base = max(base, 0.85)
    elif source_id in OFFICIAL_DATA_SOURCE_IDS and key_numbers:
        base = max(base, 0.65)
    if needs_verification:
        base = min(base, 0.65)
    return round(max(0.0, min(1.0, base)), 2)


def _evidence_id(record: dict[str, Any]) -> str | None:
    explicit_id = _as_str(record.get("evidence_id"))
    if explicit_id:
        return explicit_id
    source_id = _as_str(record.get("source_id"))
    title = _as_str(record.get("title_or_indicator") or record.get("title"))
    observed_at = _as_str(record.get("published_or_observed_at"))
    if not source_id and not title:
        return None
    digest = hashlib.sha1(f"{source_id}|{title}|{observed_at}".encode("utf-8")).hexdigest()[:10]
    return f"{source_id or 'evidence'}:{digest}"


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


def _clean(value: str) -> str:
    return " ".join(value.strip().split())


def _clean_number(value: str) -> str:
    return _clean(value).rstrip(".")


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _clean(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
