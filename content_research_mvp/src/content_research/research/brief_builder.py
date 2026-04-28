"""Build final research briefs from normalized Evidence pipeline outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Iterable


@dataclass(frozen=True)
class ResearchBrief:
    issue_name: str
    summary_lines: list[str]
    why_important: str
    key_facts: list[str]
    main_flow: list[str]
    actors_and_context: list[str]
    watch_points: list[str]
    sources: list[str]
    final_check: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        return f"""## 이슈명
{self.issue_name}

## 3줄 요약
{_bullet_lines(self.summary_lines[:3])}

## 왜 중요한가
{self.why_important}

## 핵심 사실
{_bullet_lines(self.key_facts)}

## 주요 흐름
{_bullet_lines(self.main_flow)}

## 관련 주체와 배경 맥락
{_bullet_lines(self.actors_and_context)}

## 앞으로 봐야 할 점
{_bullet_lines(self.watch_points)}

## 출처 목록
{_bullet_lines(self.sources)}

## 최종 점검
{_bullet_lines(self.final_check)}
"""


def build_research_brief(
    *,
    issue_id: str,
    issue_candidates: Iterable[Any],
    evidence_candidates: Iterable[Any],
    data_matches: Iterable[Any] | None = None,
    claims: Iterable[Any] | None = None,
) -> ResearchBrief:
    """Build a conservative final research brief for one issue."""

    issue = _find_issue(issue_id, issue_candidates)
    evidence_records = [_as_record(candidate) for candidate in evidence_candidates]
    data_match_records = [
        record
        for record in (_as_record(match) for match in (data_matches or []))
        if _as_str(record.get("issue_id")) == issue_id
    ]
    claim_records = [_as_record(claim) for claim in (claims or [])]
    related_ids = set(_as_list(issue.get("related_evidence_ids")))
    related_evidence = _related_evidence(evidence_records, related_ids)
    related_claims = _related_claims(claim_records, related_ids)

    return ResearchBrief(
        issue_name=_as_str(issue.get("issue_name")) or issue_id,
        summary_lines=_summary_lines(issue, data_match_records, related_claims),
        why_important=_why_important(issue, data_match_records),
        key_facts=_key_facts(data_match_records, related_claims),
        main_flow=_main_flow(issue, related_claims),
        actors_and_context=_actors_and_context(related_evidence, data_match_records),
        watch_points=_watch_points(data_match_records, related_claims),
        sources=_sources(related_evidence, data_match_records, related_claims),
        final_check=_final_check(related_evidence, related_claims),
    )


def _find_issue(issue_id: str, issue_candidates: Iterable[Any]) -> dict[str, Any]:
    for candidate in issue_candidates:
        record = _as_record(candidate)
        if _as_str(record.get("issue_id")) == issue_id:
            return record
    raise ValueError(f"issue_id not found: {issue_id}")


def _summary_lines(issue: dict[str, Any], data_matches: list[dict[str, Any]], claims: list[dict[str, Any]]) -> list[str]:
    issue_name = _as_str(issue.get("issue_name")) or "선정 이슈"
    data_line = _data_summary(data_matches)
    verification_count = sum(1 for claim in claims if claim.get("needs_verification"))
    verification_line = (
        f"확인 필요 항목 {verification_count}건은 단정하지 않고 추가 검증 대상으로 남겼다."
        if verification_count
        else "공식 데이터와 출처가 확인된 사실을 중심으로 정리했다."
    )
    return [
        f"{issue_name}은 현재 뉴스 Evidence에서 반복적으로 관측된 이슈다.",
        data_line,
        verification_line,
    ]


def _why_important(issue: dict[str, Any], data_matches: list[dict[str, Any]]) -> str:
    tags = ", ".join(_as_list(issue.get("tags")))
    data_note = "공식 데이터가 붙어 수치 확인이 가능하다" if data_matches else "공식 데이터 연결은 아직 제한적이다"
    return f"이 이슈는 {tags or '경제/사회'} 맥락과 연결되어 설명 수요가 있다. {data_note}."


def _key_facts(data_matches: list[dict[str, Any]], claims: list[dict[str, Any]]) -> list[str]:
    facts: list[str] = []
    for match in data_matches:
        indicator = _as_str(match.get("indicator_name")) or "공식 지표"
        value = _as_str(match.get("value"))
        unit = _as_str(match.get("unit"))
        observed_at = _as_str(match.get("observed_at"))
        source_id = _as_str(match.get("source_id"))
        if value:
            facts.append(f"{indicator}: {value} {unit}".strip() + f", 기준 {observed_at or '미상'}, 출처 {source_id or '미상'}")
    for claim in claims:
        if claim.get("needs_verification"):
            continue
        facts.append(_as_str(claim.get("claim")))
    return _unique(fact for fact in facts if fact) or ["확인된 핵심 사실은 아직 부족하다."]


def _main_flow(issue: dict[str, Any], claims: list[dict[str, Any]]) -> list[str]:
    flow = []
    trend_reason = _as_str(issue.get("trend_reason"))
    if trend_reason:
        flow.append(trend_reason)
    for claim in claims[:3]:
        prefix = "검증 필요" if claim.get("needs_verification") else "확인"
        flow.append(f"{prefix}: {_as_str(claim.get('claim'))}")
    return flow or ["뉴스 Evidence의 반복 여부를 추가 확인해야 한다."]


def _actors_and_context(evidence: list[dict[str, Any]], data_matches: list[dict[str, Any]]) -> list[str]:
    actors = []
    for record in evidence:
        publisher = _as_str(record.get("publisher_or_institution"))
        source_id = _as_str(record.get("source_id"))
        if publisher or source_id:
            actors.append(f"{publisher or source_id}: 관련 뉴스/자료 출처")
    for match in data_matches:
        source_id = _as_str(match.get("source_id"))
        indicator = _as_str(match.get("indicator_name"))
        if source_id:
            actors.append(f"{source_id}: {indicator or '공식 데이터'} 확인에 사용")
    return _unique(actors) or ["관련 주체와 배경은 추가 출처 확인이 필요하다."]


def _watch_points(data_matches: list[dict[str, Any]], claims: list[dict[str, Any]]) -> list[str]:
    points = [
        "새로운 공식 발표나 후속 통계가 나오면 수치와 기준일을 업데이트한다.",
        "향후 영향은 가능성으로만 표현하고 단정적 전망은 피한다.",
    ]
    if not data_matches:
        points.append("공식 데이터 매칭이 부족하므로 1차 자료를 더 확보한다.")
    if any(claim.get("needs_verification") for claim in claims):
        points.append("검증 필요 주장은 별도 출처로 재확인하기 전까지 핵심 사실로 쓰지 않는다.")
    return points


def _sources(
    evidence: list[dict[str, Any]],
    data_matches: list[dict[str, Any]],
    claims: list[dict[str, Any]],
) -> list[str]:
    lines: list[str] = []
    for record in evidence:
        source_id = _as_str(record.get("source_id"))
        title = _as_str(record.get("title_or_indicator"))
        url = _as_str(record.get("url"))
        rights = record.get("rights_status")
        rights_note = _rights_note(rights if isinstance(rights, dict) else {})
        location = url or source_id or "source_unknown"
        lines.append(f"{source_id or 'unknown'} - {title or 'untitled'} - {location}{rights_note}")
    for match in data_matches:
        source_id = _as_str(match.get("source_id"))
        indicator = _as_str(match.get("indicator_name"))
        matched_data = _as_str(match.get("matched_data"))
        lines.append(f"{source_id or 'official_data'} - {indicator or 'indicator'} - {matched_data or source_id or 'source_id_missing'}")
    for claim in claims:
        if _as_str(claim.get("source_id")) and not _as_str(claim.get("evidence_id")):
            lines.append(_as_str(claim.get("source_id")))
    return _unique(lines) or ["출처 추가 필요"]


def _final_check(evidence: list[dict[str, Any]], claims: list[dict[str, Any]]) -> list[str]:
    checks = [
        "기사 본문은 저장하거나 길게 인용하지 않았고, 제목/스니펫/메타데이터 중심으로만 사용했다.",
        "특정 자산·기업·국가에 대한 직접 의사결정 유도 표현은 넣지 않았다.",
        "미래 전망은 단정하지 않고 관찰 포인트로만 정리했다.",
    ]
    unverified = [claim for claim in claims if claim.get("needs_verification")]
    if unverified:
        checks.append(f"needs_verification 항목 {len(unverified)}건: " + "; ".join(_as_str(claim.get("claim")) for claim in unverified[:3]))
    blocked = [
        record
        for record in evidence
        if isinstance(record.get("rights_status"), dict) and record["rights_status"].get("allowed") is False
    ]
    if blocked:
        checks.append(f"rights_status 제한 출처 {len(blocked)}건은 본문 사용 없이 메타데이터만 반영했다.")
    return checks


def _data_summary(data_matches: list[dict[str, Any]]) -> str:
    if not data_matches:
        return "아직 연결된 공식 데이터가 없어 수치 근거는 제한적이다."
    first = data_matches[0]
    indicator = _as_str(first.get("indicator_name")) or "공식 지표"
    value = _as_str(first.get("value"))
    unit = _as_str(first.get("unit"))
    observed_at = _as_str(first.get("observed_at"))
    return f"연결된 공식 데이터는 {indicator} {value} {unit}".strip() + f" 기준 {observed_at or '미상'}이다."


def _related_evidence(records: list[dict[str, Any]], related_ids: set[str]) -> list[dict[str, Any]]:
    if not related_ids:
        return records
    return [record for record in records if _record_id(record) in related_ids or _as_str(record.get("url")) in related_ids]


def _related_claims(records: list[dict[str, Any]], related_ids: set[str]) -> list[dict[str, Any]]:
    if not related_ids:
        return records
    return [record for record in records if _as_str(record.get("evidence_id")) in related_ids]


def _record_id(record: dict[str, Any]) -> str:
    explicit_id = _as_str(record.get("evidence_id"))
    if explicit_id:
        return explicit_id
    url = _as_str(record.get("url"))
    if url:
        return url
    source_id = _as_str(record.get("source_id")) or "evidence"
    title = _as_str(record.get("title_or_indicator"))
    observed_at = _as_str(record.get("published_or_observed_at"))
    digest = hashlib.sha1(f"{source_id}|{title}|{observed_at}".encode("utf-8")).hexdigest()[:10]
    return f"{source_id}:{digest}"


def _rights_note(rights_status: dict[str, Any]) -> str:
    if not rights_status:
        return ""
    storage_policy = _as_str(rights_status.get("storage_policy"))
    allowed = rights_status.get("allowed")
    if allowed is False:
        return f" (rights: {storage_policy or 'metadata_only'}, no body use)"
    if storage_policy:
        return f" (rights: {storage_policy})"
    return ""


def _bullet_lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 추가 확인 필요"


def _as_record(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, dict):
        return candidate
    to_dict = getattr(candidate, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        if isinstance(value, dict):
            return value
    return {}


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_as_str(item) for item in value if _as_str(item)]


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = " ".join(value.split())
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
