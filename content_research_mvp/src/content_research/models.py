"""Shared models for Korean current affairs/economy content research."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from enum import Enum
import json
from typing import Any


class SourceKind(str, Enum):
    OFFICIAL = "official"
    PRIMARY = "primary"
    STATISTICS = "statistics"
    NEWS = "news"
    EXPERT = "expert"
    YOUTUBE_METADATA = "youtube_metadata"
    OTHER = "other"


class ClaimStrength(str, Enum):
    VERIFIED = "verified"
    INTERPRETIVE = "interpretive"
    UNVERIFIED = "unverified"
    SCENARIO = "scenario"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResearchPriorityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationStatus(str, Enum):
    CONFIRMED = "confirmed"
    REPORTED = "reported"
    INTERPRETATION = "interpretation"
    UNCERTAIN = "uncertain"
    DO_NOT_USE = "do_not_use"


class ContextConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FinalFactcheckStatus(str, Enum):
    READY = "ready"
    REVISE_BEFORE_DELIVERY = "revise_before_delivery"
    SOURCE_MORE_BEFORE_DELIVERY = "source_more_before_delivery"


@dataclass(frozen=True)
class SourceRef:
    title: str
    publisher: str
    url: str
    kind: SourceKind
    published_at: str | None = None
    accessed_at: str | None = None

    def validate(self) -> None:
        if not self.title.strip():
            raise ValueError("source title is required")
        if not self.publisher.strip():
            raise ValueError("source publisher is required")
        if not self.url.startswith(("http://", "https://", "urn:")):
            raise ValueError("source url must be http(s) or urn")


@dataclass(frozen=True)
class NumericFact:
    value: str
    unit: str
    as_of: str
    source_url: str
    label: str = ""

    def validate(self) -> None:
        if not self.value.strip():
            raise ValueError("numeric fact value is required")
        if not self.unit.strip():
            raise ValueError("numeric fact unit is required")
        if not self.as_of.strip():
            raise ValueError("numeric fact as_of date is required")
        if not self.source_url.startswith(("http://", "https://", "urn:")):
            raise ValueError("numeric fact source_url must be http(s) or urn")


@dataclass
class EvidenceCard:
    claim: str
    summary_ko: str
    strength: ClaimStrength
    sources: list[SourceRef]
    numeric_facts: list[NumericFact] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.claim.strip():
            raise ValueError("claim is required")
        if not self.summary_ko.strip():
            raise ValueError("summary_ko is required")
        if not self.sources:
            raise ValueError("at least one source is required")
        for source in self.sources:
            source.validate()
        for fact in self.numeric_facts:
            fact.validate()
        if self.strength in {ClaimStrength.UNVERIFIED, ClaimStrength.SCENARIO} and not self.caveats:
            raise ValueError("unverified or scenario claims require caveats")

    def to_markdown(self) -> str:
        self.validate()
        source_lines = "\n".join(
            f"- {source.publisher}, [{source.title}]({source.url})"
            for source in self.sources
        )
        fact_lines = "\n".join(
            f"- {fact.label or '숫자'}: {fact.value} {fact.unit}, 기준일 {fact.as_of}, 출처 {fact.source_url}"
            for fact in self.numeric_facts
        )
        caveat_lines = "\n".join(f"- {caveat}" for caveat in self.caveats)
        return (
            f"### EvidenceCard\n\n"
            f"**주장:** {self.claim}\n\n"
            f"**요약:** {self.summary_ko}\n\n"
            f"**강도:** {self.strength.value}\n\n"
            f"**출처:**\n{source_lines}\n\n"
            f"**숫자:**\n{fact_lines or '- 없음'}\n\n"
            f"**주의:**\n{caveat_lines or '- 없음'}\n"
        )


@dataclass(frozen=True)
class TopicCandidate:
    topic: str
    latest_trigger: str
    core_question: str
    viewer_interest: str
    required_sources: list[str]
    risk_notes: str = ""


@dataclass(frozen=True)
class IssueCollectionCandidate:
    candidate_issue: str
    current_trigger: str
    why_it_may_matter: str
    source_types_needed: list[str]
    uncertainty_or_risk: str = ""


@dataclass(frozen=True)
class ResearchPrioritySignals:
    social_economic_impact: float
    timeliness: float
    breadth: float
    explanation_need: float
    korea_relevance: float
    source_availability: float
    fact_checkability: float
    neutrality_safety: float
    investment_advice_safety: float
    trigger_clarity: float = 5.0
    structural_meaning: float = 5.0


@dataclass(frozen=True)
class ResearchPriorityWeights:
    social_economic_impact: float = 0.17
    timeliness: float = 0.13
    breadth: float = 0.11
    explanation_need: float = 0.11
    korea_relevance: float = 0.08
    source_availability: float = 0.14
    fact_checkability: float = 0.12
    trigger_clarity: float = 0.07
    structural_meaning: float = 0.07


@dataclass(frozen=True)
class ResearchPriorityCandidate:
    issue: str
    why_now: str
    core_question: str
    source_notes: list[str]
    signals: ResearchPrioritySignals
    risk_notes: str = ""


@dataclass(frozen=True)
class ResearchPriorityAssessment:
    rank: int
    issue: str
    research_priority: ResearchPriorityLevel
    total_score: float
    reason: str
    source_risk: RiskLevel
    wording_risk: RiskLevel
    next_step: str


@dataclass(frozen=True)
class FactVerificationNote:
    claim_or_number: str
    status: VerificationStatus
    unit_and_date: str
    source: str
    note: str


@dataclass(frozen=True)
class ContextNote:
    context_item: str
    explanation: str
    confidence: ContextConfidence
    source_or_basis: str
    final_brief_use: str


@dataclass(frozen=True)
class ResearchBriefDraft:
    issue: str
    summary_lines: list[str]
    why_matters: str
    verified_facts: list[str]
    key_flow: list[str]
    context: list[str]
    watch_points: list[str]
    sources: list[str]
    final_check: str = ""

    def to_markdown(self) -> str:
        summary = "\n".join(f"{index}. {line}" for index, line in enumerate(self.summary_lines[:3], start=1))
        facts = "\n".join(f"- {fact}" for fact in self.verified_facts) or "- 확인된 핵심 사실 없음"
        flow = "\n".join(f"- {item}" for item in self.key_flow) or "- 추가 확인 필요"
        context = "\n".join(f"- {item}" for item in self.context) or "- 핵심 맥락 없음"
        watch_points = "\n".join(f"- {item}" for item in self.watch_points) or "- 추가 확인 필요"
        sources = "\n".join(f"- {source}" for source in self.sources) or "- 출처 추가 필요"
        final_check = self.final_check or "최종 팩트체크 전"
        return f"""### 1. 이슈명
{self.issue}

### 2. 3줄 요약
{summary}

### 3. 왜 중요한가
{self.why_matters}

### 4. 핵심 사실
{facts}

### 5. 주요 흐름
{flow}

### 6. 관련 주체와 배경 맥락
{context}

### 7. 앞으로 봐야 할 부분
{watch_points}

### 8. 출처 목록
{sources}

### 9. 최종 점검
{final_check}
"""


@dataclass(frozen=True)
class FinalFactcheckFinding:
    item: str
    issue: str
    required_revision: str
    risk_level: RiskLevel = RiskLevel.MEDIUM


@dataclass(frozen=True)
class FinalFactcheckReport:
    status: FinalFactcheckStatus
    findings: list[FinalFactcheckFinding]


@dataclass(frozen=True)
class ChannelFitScore:
    popularity: float
    economic_linkage: float
    story_potential: float
    source_availability: float
    risk_safety: float
    total: float
    rationale: str


@dataclass(frozen=True)
class NarrativeOutline:
    hook: str
    background: str
    structure: str
    issues: str
    twist: str
    impact: str
    conclusion: str

    def to_markdown(self) -> str:
        return "\n\n".join(
            [
                f"## 후킹\n\n{self.hook}",
                f"## 배경\n\n{self.background}",
                f"## 구조\n\n{self.structure}",
                f"## 쟁점\n\n{self.issues}",
                f"## 반전\n\n{self.twist}",
                f"## 영향\n\n{self.impact}",
                f"## 결론\n\n{self.conclusion}",
            ]
        )


@dataclass(frozen=True)
class SlidePlan:
    number: int
    title: str
    core_message: str
    visual_idea: str
    speaker_note: str
    source_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScriptSection:
    slide_number: int
    section: str
    narration: str
    caption: str = ""
    source_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RiskFinding:
    item: str
    problem_type: str
    risk_level: RiskLevel
    recommendation: str
    required_source: str = ""


@dataclass
class ResearchBundle:
    topic_definition: str
    why_now: list[str]
    evidence_cards: list[EvidenceCard]
    channel_fit: ChannelFitScore
    narrative: NarrativeOutline
    slides: list[SlidePlan]
    script: list[ScriptSection]
    risk_findings: list[RiskFinding]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_jsonl(self) -> str:
        records = [
            {"type": "bundle_meta", "topic_definition": self.topic_definition, "created_at": self.created_at},
            *({"type": "evidence_card", **asdict(card)} for card in self.evidence_cards),
            {"type": "channel_fit", **asdict(self.channel_fit)},
            {"type": "narrative", **asdict(self.narrative)},
            *({"type": "slide", **asdict(slide)} for slide in self.slides),
            *({"type": "script", **asdict(section)} for section in self.script),
            *({"type": "risk_finding", **asdict(finding)} for finding in self.risk_findings),
        ]
        return "\n".join(json.dumps(record, ensure_ascii=False, default=_json_default) for record in records)

    def to_markdown(self) -> str:
        why_now = "\n".join(f"- {item}" for item in self.why_now)
        evidence = "\n\n".join(card.to_markdown() for card in self.evidence_cards)
        slides = "\n".join(
            "| {number} | {title} | {core_message} | {visual_idea} | {speaker_note} | {source_refs} |".format(
                number=s.number,
                title=_markdown_table_cell(s.title),
                core_message=_markdown_table_cell(s.core_message),
                visual_idea=_markdown_table_cell(s.visual_idea),
                speaker_note=_markdown_table_cell(s.speaker_note),
                source_refs=_markdown_table_cell(", ".join(s.source_refs)),
            )
            for s in self.slides
        )
        script = "\n\n".join(
            f"### [슬라이드 {s.slide_number}] {s.section}\n\n{s.narration}\n\n자막: {s.caption}"
            for s in self.script
        )
        risks = "\n".join(
            "| {item} | {problem_type} | {risk_level} | {recommendation} | {required_source} |".format(
                item=_markdown_table_cell(r.item),
                problem_type=_markdown_table_cell(r.problem_type),
                risk_level=_markdown_table_cell(r.risk_level.value),
                recommendation=_markdown_table_cell(r.recommendation),
                required_source=_markdown_table_cell(r.required_source),
            )
            for r in self.risk_findings
        )
        return f"""# 유튜브 리서치 브리프

## 1. 한 줄 주제 정의

{self.topic_definition}

## 2. 왜 지금 중요한가

{why_now}

## 3. 핵심 자료

{evidence}

## 4. PPT 슬라이드 구성

| 슬라이드 | 제목 | 핵심 메시지 | 시각자료 | 발표자 노트 | 출처 |
|---:|---|---|---|---|---|
{slides}

## 5. 촬영 대본

{script}

## 6. 팩트체크 표

| 항목 | 문제 유형 | 위험도 | 수정 제안 | 필요한 출처 |
|---|---|---|---|---|
{risks}
"""


def _markdown_table_cell(value: Any) -> str:
    text = str(value)
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    return "<br>".join(part.strip() for part in text.splitlines())


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
