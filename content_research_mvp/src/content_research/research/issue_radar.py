"""Detect issue candidates from normalized news Evidence candidates."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Iterable
from urllib.parse import urlparse


NEWS_SOURCE_IDS = frozenset({"naver_news", "newsapi", "nytimes"})
MAX_REPRESENTATIVE_TITLES = 3

_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")

_STOPWORDS = frozenset(
    {
        "and",
        "are",
        "but",
        "for",
        "from",
        "has",
        "into",
        "new",
        "news",
        "over",
        "the",
        "with",
        "amid",
        "after",
        "before",
        "says",
        "said",
        "about",
        "will",
        "could",
        "would",
        "that",
        "this",
    }
)

_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "key": "central_bank_rates",
        "issue_name": "금리와 중앙은행 정책",
        "keywords": (
            "central bank",
            "interest rate",
            "rate cut",
            "rate hike",
            "federal reserve",
            "fed",
            "ecb",
            "boj",
            "금리",
            "중앙은행",
            "연준",
            "기준금리",
        ),
        "tags": ("국제", "경제"),
    },
    {
        "key": "inflation_prices",
        "issue_name": "물가와 인플레이션 압력",
        "keywords": ("inflation", "prices", "cpi", "pce", "물가", "인플레이션", "소비자물가"),
        "tags": ("국제", "경제"),
    },
    {
        "key": "korea_economy",
        "issue_name": "한국 경제와 시장 흐름",
        "keywords": ("korea", "south korea", "seoul", "kospi", "won", "한국", "국내", "서울", "코스피", "원화"),
        "tags": ("한국", "경제"),
    },
    {
        "key": "china_economy",
        "issue_name": "중국 경제 흐름",
        "keywords": ("china", "beijing", "yuan", "중국", "베이징", "위안"),
        "tags": ("국제", "경제"),
    },
    {
        "key": "semiconductors_ai",
        "issue_name": "반도체와 AI 산업",
        "keywords": ("semiconductor", "chip", "chips", "ai", "nvidia", "hbm", "반도체", "인공지능", "칩"),
        "tags": ("국제", "경제", "산업"),
    },
    {
        "key": "energy_oil",
        "issue_name": "에너지와 유가",
        "keywords": ("oil", "crude", "brent", "wti", "energy", "gas", "opec", "유가", "원유", "에너지", "천연가스"),
        "tags": ("국제", "경제", "산업", "지정학"),
    },
    {
        "key": "trade_supply_chain",
        "issue_name": "무역과 공급망",
        "keywords": (
            "trade",
            "tariff",
            "export",
            "imports",
            "supply chain",
            "export control",
            "무역",
            "관세",
            "수출",
            "수입",
            "공급망",
            "수출통제",
        ),
        "tags": ("국제", "경제", "산업", "지정학"),
    },
    {
        "key": "geopolitical_security",
        "issue_name": "지정학과 안보 리스크",
        "keywords": ("war", "conflict", "sanction", "security", "geopolitical", "전쟁", "분쟁", "제재", "안보", "지정학"),
        "tags": ("국제", "지정학"),
    },
)


@dataclass(frozen=True)
class IssueRadarCandidate:
    issue_id: str
    issue_name: str
    representative_titles: list[str]
    related_evidence_ids: list[str]
    tags: list[str]
    trend_reason: str
    first_seen_at: str | None
    last_seen_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_issue_candidates(
    evidence_candidates: Iterable[Any],
    *,
    limit: int = 10,
    min_evidence_count: int = 1,
) -> list[IssueRadarCandidate]:
    """Build issue candidates from normalized news Evidence records."""

    if limit <= 0:
        raise ValueError("limit must be positive")
    if min_evidence_count <= 0:
        raise ValueError("min_evidence_count must be positive")

    deduped = _dedupe_by_url(_news_records(evidence_candidates))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    group_meta: dict[str, dict[str, Any]] = {}

    for record in deduped:
        match = _match_group(record)
        grouped[match["key"]].append(record)
        group_meta[match["key"]] = match

    scored: list[tuple[int, str, IssueRadarCandidate]] = []
    for key, records in grouped.items():
        if len(records) < min_evidence_count:
            continue
        issue = _build_issue(key, records, group_meta[key])
        score = _sort_score(records)
        scored.append((score, issue.last_seen_at or "", issue))

    scored.sort(key=lambda item: (item[0], item[1], item[2].issue_id), reverse=True)
    return [issue for _, _, issue in scored[:limit]]


def _news_records(evidence_candidates: Iterable[Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for candidate in evidence_candidates:
        record = _as_record(candidate)
        if _as_str(record.get("source_id")) in NEWS_SOURCE_IDS:
            records.append(record)
    return records


def _dedupe_by_url(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for record in records:
        canonical_url = _canonical_url(_as_str(record.get("url")))
        if canonical_url:
            if canonical_url in seen_urls:
                continue
            seen_urls.add(canonical_url)
        deduped.append(record)
    return deduped


def _match_group(record: dict[str, Any]) -> dict[str, Any]:
    text = _search_text(record)
    matches: list[dict[str, Any]] = []
    for group in _GROUPS:
        if any(_contains_keyword(text, keyword) for keyword in group["keywords"]):
            matches.append(group)
    if matches:
        return max(matches, key=lambda group: _group_priority(str(group["key"])))

    key_token = _fallback_token(text)
    return {
        "key": f"keyword_{key_token}",
        "issue_name": _fallback_issue_name(record, key_token),
        "keywords": (key_token,),
        "tags": tuple(_tags_from_text(text)),
    }


def _group_priority(key: str) -> int:
    priorities = {
        "energy_oil": 90,
        "semiconductors_ai": 80,
        "trade_supply_chain": 75,
        "central_bank_rates": 70,
        "korea_economy": 65,
        "china_economy": 65,
        "geopolitical_security": 60,
        "inflation_prices": 50,
    }
    return priorities.get(key, 0)


def _build_issue(key: str, records: list[dict[str, Any]], meta: dict[str, Any]) -> IssueRadarCandidate:
    titles = _unique_nonempty(_title(record) for record in records)[:MAX_REPRESENTATIVE_TITLES]
    evidence_ids = [_evidence_id(record, index) for index, record in enumerate(records, start=1)]
    seen_times = sorted(_as_str(record.get("published_or_observed_at")) for record in records if record.get("published_or_observed_at"))
    first_seen_at = seen_times[0] if seen_times else None
    last_seen_at = seen_times[-1] if seen_times else None
    return IssueRadarCandidate(
        issue_id=_issue_id(key),
        issue_name=str(meta["issue_name"]),
        representative_titles=titles,
        related_evidence_ids=evidence_ids,
        tags=_issue_tags(records, meta),
        trend_reason=_trend_reason(records, first_seen_at, last_seen_at),
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
    )


def _issue_tags(records: list[dict[str, Any]], meta: dict[str, Any]) -> list[str]:
    tags = list(meta["tags"])
    for record in records:
        tags.extend(_tags_from_text(_search_text(record)))
    return list(dict.fromkeys(tags))


def _sort_score(records: list[dict[str, Any]]) -> int:
    source_count = len({_as_str(record.get("source_id")) for record in records if record.get("source_id")})
    return len(records) * 10 + source_count


def _trend_reason(records: list[dict[str, Any]], first_seen_at: str | None, last_seen_at: str | None) -> str:
    count = len(records)
    source_count = len({_as_str(record.get("source_id")) for record in records if record.get("source_id")})
    if count >= 2:
        if first_seen_at and last_seen_at and first_seen_at != last_seen_at:
            return f"반복 출현: {count}건이 {first_seen_at}부터 {last_seen_at}까지 확인됨."
        return f"반복 출현: 관련 Evidence {count}건이 확인됨."
    if source_count >= 2:
        return f"복수 출처 관측: {source_count}개 뉴스 출처에서 확인됨."
    return "단건 후보: 추가 출처 확인이 필요함."


def _tags_from_text(text: str) -> list[str]:
    tags: list[str] = []
    tag_keywords = {
        "한국": ("korea", "korean", "seoul", "한국", "국내", "서울", "원화", "코스피"),
        "경제": ("economy", "market", "rate", "inflation", "price", "trade", "경제", "시장", "금리", "물가", "무역"),
        "산업": ("industry", "chip", "semiconductor", "energy", "auto", "산업", "반도체", "에너지", "자동차"),
        "지정학": ("war", "conflict", "sanction", "security", "geopolitical", "전쟁", "분쟁", "제재", "안보", "지정학"),
        "국제": ("global", "world", "us", "china", "europe", "japan", "국제", "미국", "중국", "유럽", "일본"),
    }
    for tag, keywords in tag_keywords.items():
        if any(_contains_keyword(text, keyword) for keyword in keywords):
            tags.append(tag)
    return tags or ["국제"]


def _contains_keyword(text: str, keyword: str) -> bool:
    normalized_keyword = keyword.casefold()
    if re.fullmatch(r"[0-9a-z ]+", normalized_keyword):
        pattern = rf"(?<![0-9a-z]){re.escape(normalized_keyword)}(?![0-9a-z])"
        return re.search(pattern, text) is not None
    return normalized_keyword in text


def _fallback_issue_name(record: dict[str, Any], token: str) -> str:
    title = _title(record)
    if title:
        return title[:80]
    return f"{token} 관련 이슈"


def _fallback_token(text: str) -> str:
    for token in _TOKEN_RE.findall(text):
        if token not in _STOPWORDS and len(token) >= 3:
            return token
    return "general"


def _search_text(record: dict[str, Any]) -> str:
    return " ".join((_title(record), _as_str(record.get("snippet")))).casefold()


def _title(record: dict[str, Any]) -> str:
    return _as_str(record.get("title_or_indicator") or record.get("title"))


def _evidence_id(record: dict[str, Any], index: int) -> str:
    explicit_id = _as_str(record.get("evidence_id"))
    if explicit_id:
        return explicit_id
    url = _canonical_url(_as_str(record.get("url")))
    if url:
        return url
    source_id = _as_str(record.get("source_id")) or "evidence"
    title_hash = hashlib.sha1(_title(record).encode("utf-8")).hexdigest()[:10]
    return f"{source_id}:{title_hash or index}"


def _issue_id(key: str) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return f"issue_{digest}"


def _canonical_url(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/")
    return f"{host}{path}".lower()


def _unique_nonempty(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        text = " ".join(value.split())
        if text and text not in seen:
            seen.add(text)
            unique.append(text)
    return unique


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
