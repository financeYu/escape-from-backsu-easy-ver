"""Root pipeline orchestrator for content research MVP."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Iterable

from content_research.collection import HourlyCollectionProcess
from content_research.config import AppConfig, load_config
from content_research.deck.ppt_outline_builder import build_ppt_outline
from content_research.models import (
    ChannelFitScore,
    ClaimStrength,
    EvidenceCard,
    NumericFact,
    ResearchBundle,
    RiskFinding,
    RiskLevel,
    ScriptSection,
    SlidePlan,
    SourceKind,
    SourceRef,
    WorkerInstruction,
    WorkerTaskStatus,
    WorkflowStage,
)
from content_research.narrative.outline_builder import build_outline
from content_research.research.claim_extractor import extract_claims
from content_research.research.data_matcher import match_issue_data
from content_research.research.evidence_normalizer import EvidenceCandidate, normalize_jsonl_file
from content_research.research.fact_verification import verify_evidence_cards
from content_research.research.issue_radar import detect_issue_candidates
from content_research.review.risk_report import build_risk_report
from content_research.script.script_builder import build_script


_TOPIC_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")
_TOPIC_STOPWORDS = frozenset(
    {
        "관련",
        "경제",
        "국제",
        "뉴스",
        "시사",
        "오늘",
        "이슈",
        "주요",
        "최신",
        "시장",
        "the",
        "and",
        "for",
        "from",
        "with",
        "about",
    }
)
_TOPIC_SYNONYMS = {
    "ai": ("ai", "artificial intelligence", "인공지능", "nvidia", "gpu", "hbm", "semiconductor", "chip", "chips", "반도체"),
    "인공지능": ("ai", "artificial intelligence", "인공지능", "nvidia", "gpu", "hbm", "semiconductor", "chip", "chips", "반도체"),
    "반도체": ("ai", "nvidia", "gpu", "hbm", "semiconductor", "chip", "chips", "반도체"),
    "semiconductor": ("ai", "nvidia", "gpu", "hbm", "semiconductor", "chip", "chips", "반도체"),
    "chip": ("ai", "nvidia", "gpu", "hbm", "semiconductor", "chip", "chips", "반도체"),
    "유가": ("oil", "crude", "wti", "brent", "opec", "energy", "gas", "원유", "유가", "에너지"),
    "원유": ("oil", "crude", "wti", "brent", "opec", "energy", "gas", "원유", "유가", "에너지"),
    "oil": ("oil", "crude", "wti", "brent", "opec", "energy", "gas", "원유", "유가", "에너지"),
    "energy": ("oil", "crude", "wti", "brent", "opec", "energy", "gas", "원유", "유가", "에너지"),
    "금리": ("interest rate", "rate cut", "rate hike", "central bank", "fed", "federal reserve", "ecb", "boj", "금리", "중앙은행"),
    "fed": ("interest rate", "rate cut", "rate hike", "central bank", "fed", "federal reserve", "ecb", "boj", "금리", "중앙은행"),
    "물가": ("inflation", "prices", "cpi", "pce", "물가", "인플레이션"),
    "inflation": ("inflation", "prices", "cpi", "pce", "물가", "인플레이션"),
    "무역": ("trade", "tariff", "export", "import", "supply chain", "export control", "무역", "관세", "수출", "수입", "공급망"),
    "trade": ("trade", "tariff", "export", "import", "supply chain", "export control", "무역", "관세", "수출", "수입", "공급망"),
    "한국": ("korea", "south korea", "seoul", "kospi", "won", "한국", "국내", "서울", "코스피", "원화"),
    "korea": ("korea", "south korea", "seoul", "kospi", "won", "한국", "국내", "서울", "코스피", "원화"),
}
_MIN_CORE_SOURCE_COUNT = 10
_MIN_OFFICIAL_SOURCE_COUNT = 3


class ContentResearchOrchestrator:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()

    def run(
        self,
        topic: str,
        *,
        approve_plan: bool = False,
        approved_by: str | None = None,
    ) -> ResearchBundle:
        """Collect configured sources once and turn fetched records into a PPT-ready research bundle."""

        if not topic.strip():
            raise ValueError("topic is required")

        process = HourlyCollectionProcess(
            output_dir=self.config.collection.output_dir,
            interval_minutes=self.config.collection.interval_minutes,
            timezone_name=self.config.collection.timezone,
        )
        manifest, _, _ = process.run_once(mode="run")
        record_paths = [Path(result.records_path) for result in manifest.results if result.records_path]
        evidence = _load_evidence(record_paths)
        if not evidence:
            return self._empty_collection_bundle(topic, manifest.results)

        topic_evidence = _topic_relevant_evidence(evidence, topic)
        if not topic_evidence:
            return self._topic_mismatch_bundle(topic, manifest.results, len(evidence))
        evidence = topic_evidence

        issues = detect_issue_candidates(evidence)
        data_matches = match_issue_data(issues, evidence) if issues else []
        claims = extract_claims(evidence)
        selected_issue = issues[0] if issues else None

        if selected_issue is not None:
            topic_definition = f"{topic}: {selected_issue.issue_name}"
            why_now = [
                selected_issue.trend_reason,
                f"정규화된 Evidence {len(evidence)}개와 공식 데이터 매칭 {len(data_matches)}개를 확인했습니다.",
                f"검증이 필요한 주장 {sum(1 for claim in claims if claim.needs_verification)}개를 분리했습니다.",
            ]
        else:
            topic_definition = f"{topic}: 수집된 근거를 바탕으로 한 시사·경제 리서치 브리프"
            why_now = [
                f"이번 실행에서 Evidence 후보 {len(evidence)}개를 수집했습니다.",
                "뉴스 메타데이터와 공식 통계 자료를 분리해 확인합니다.",
                "PPT 작성 전 출처, 기준일, 수치 단위를 먼저 점검합니다.",
            ]

        evidence_cards = [_evidence_to_card(candidate) for candidate in evidence[:10]]
        outline = build_outline(topic, evidence_cards)
        fact_checks = verify_evidence_cards(evidence_cards)
        plan_review_findings = _plan_review_findings(evidence_cards)
        slides: list[SlidePlan] = []
        script: list[ScriptSection] = []
        worker_instructions: list[WorkerInstruction] = []
        approved_at = None
        workflow_stage = _plan_review_stage(plan_review_findings)
        if approve_plan:
            worker_instructions, slides, script = _dispatch_approved_worker_pool(outline, evidence)
            approved_at = datetime.now(UTC).isoformat(timespec="seconds")
            workflow_stage = WorkflowStage.ORCHESTRATED

        risk_findings = _merge_risk_findings(
            build_risk_report(evidence_cards, "\n".join(section.narration for section in script)),
            plan_review_findings,
        )
        if approve_plan:
            worker_instructions = [_mark_worker_completed(task) for task in worker_instructions]
        return ResearchBundle(
            topic_definition=topic_definition,
            why_now=why_now,
            evidence_cards=evidence_cards,
            channel_fit=_score_from_evidence(evidence),
            narrative=outline,
            slides=slides,
            script=script,
            risk_findings=risk_findings,
            fact_checks=fact_checks,
            worker_instructions=worker_instructions,
            workflow_stage=workflow_stage,
            approval_required=not approve_plan,
            approved_by=(approved_by or "unspecified") if approve_plan else None,
            approved_at=approved_at,
        )

    def _topic_mismatch_bundle(
        self,
        topic: str,
        results: Iterable[object],
        collected_evidence_count: int,
    ) -> ResearchBundle:
        status_lines = [
            f"{result.source_id}: {result.status} - {result.message}"
            for result in results
            if getattr(result, "status", "") in {"fetched_metadata", "fetched_statistics", "fetched_catalog", "fetched_disclosures", "fetched_observations", "fetched_energy_series", "fetched_trade_data"}
        ]
        source = SourceRef(
            title="수집 결과 토픽 매칭",
            publisher="content_research_mvp",
            url="urn:content-research:topic-filter",
            kind=SourceKind.OTHER,
            accessed_at=self.config.default_as_of or None,
        )
        card = EvidenceCard(
            claim=f"{topic}와 직접 관련된 Evidence record를 이번 수집 결과에서 찾지 못했습니다.",
            summary_ko="run --topic은 요청 주제에 맞는 자료만 브리프에 사용합니다. 관련 자료가 없으면 다른 최신 이슈로 대체하지 않고 이 상태를 보고합니다.",
            strength=ClaimStrength.UNVERIFIED,
            sources=[source],
            caveats=[
                f"전체 수집 Evidence 후보: {collected_evidence_count}개",
                *(status_lines[:10] or ["수집은 완료됐지만 토픽 필터를 통과한 Evidence가 없습니다."]),
            ],
            tags=["topic_mismatch"],
        )
        outline = build_outline(topic, [card])
        risk_findings = [
            RiskFinding(
                item="토픽 관련 근거",
                problem_type="no_topic_evidence",
                risk_level=RiskLevel.HIGH,
                recommendation="검색어, 수집 어댑터 기본 질의, 또는 API 키를 조정해 요청 주제와 직접 관련된 record JSONL을 먼저 확보해야 합니다.",
                required_source=", ".join(status_lines[:3]),
            )
        ]
        return ResearchBundle(
            topic_definition=f"{topic}: 관련 Evidence 부족으로 브리프 생성 보류",
            why_now=[
                f"이번 실행에서 Evidence 후보 {collected_evidence_count}개를 수집했지만 요청 주제와 직접 매칭되는 자료가 없었습니다.",
                "다른 최신 이슈를 대신 선택하지 않았습니다.",
                "PPT 직전 리서치 재료로 쓰려면 주제 관련 출처를 다시 수집해야 합니다.",
            ],
            evidence_cards=[card],
            channel_fit=ChannelFitScore(0, 0, 0, 0, 10, 2.0, "토픽 관련 Evidence가 없어 브리프 준비도를 낮게 산정했습니다."),
            narrative=outline,
            slides=[],
            script=[],
            risk_findings=risk_findings,
            fact_checks=verify_evidence_cards([card]),
            workflow_stage=WorkflowStage.BLOCKED,
            approval_required=True,
        )

    def _empty_collection_bundle(self, topic: str, results: Iterable[object]) -> ResearchBundle:
        status_lines = [
            f"{result.source_id}: {result.status} - {result.message}"
            for result in results
            if getattr(result, "status", "") in {"missing_credentials", "error", "missing_handler"}
        ]
        source = SourceRef(
            title="수집 실행 결과",
            publisher="content_research_mvp",
            url="urn:content-research:collection-status",
            kind=SourceKind.OTHER,
            accessed_at=self.config.default_as_of or None,
        )
        card = EvidenceCard(
            claim=f"{topic} 리서치에 사용할 수 있는 Evidence record가 아직 수집되지 않았습니다.",
            summary_ko="API 키가 없거나 어댑터 오류가 발생하면 실제 뉴스·통계 record가 생성되지 않습니다.",
            strength=ClaimStrength.UNVERIFIED,
            sources=[source],
            caveats=status_lines[:12] or ["수집 결과가 비어 있습니다."],
            tags=["collection_status"],
        )
        outline = build_outline(topic, [card])
        risk_findings = [
            RiskFinding(
                item="수집 자료",
                problem_type="missing_evidence",
                risk_level=RiskLevel.HIGH,
                recommendation="필요한 API 키를 설정하거나 record JSONL을 먼저 수집해야 PPT 직전 리서치 재료로 사용할 수 있습니다.",
                required_source=", ".join(status_lines[:3]),
            )
        ]
        return ResearchBundle(
            topic_definition=f"{topic}: 실제 수집 자료 부족으로 브리프 생성 보류",
            why_now=[
                "이번 실행에서는 Evidence로 정규화할 수 있는 record가 없었습니다.",
                "가짜 근거 대신 수집 실패 사유를 남겼습니다.",
                "API 키 설정 후 다시 실행하면 실제 수집 자료 기반 브리프를 생성합니다.",
            ],
            evidence_cards=[card],
            channel_fit=ChannelFitScore(0, 0, 0, 0, 10, 2.0, "실제 Evidence가 없어 브리프 품질 점수를 낮게 산정했습니다."),
            narrative=outline,
            slides=[],
            script=[],
            risk_findings=risk_findings,
            fact_checks=verify_evidence_cards([card]),
            workflow_stage=WorkflowStage.BLOCKED,
            approval_required=True,
        )

    def write_outputs(self, bundle: ResearchBundle, output_dir: str | Path | None = None) -> tuple[Path, Path]:
        target_dir = Path(output_dir) if output_dir else self.config.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        slug = "research_bundle"
        markdown_path = target_dir / f"{slug}.md"
        jsonl_path = target_dir / f"{slug}.jsonl"
        markdown_path.write_text(bundle.to_markdown(), encoding="utf-8")
        jsonl_path.write_text(bundle.to_jsonl() + "\n", encoding="utf-8")
        return markdown_path, jsonl_path


def _load_evidence(record_paths: list[Path]) -> list[EvidenceCandidate]:
    evidence: list[EvidenceCandidate] = []
    for path in record_paths:
        if path.exists():
            evidence.extend(normalize_jsonl_file(path))
    return evidence


def _topic_relevant_evidence(evidence: list[EvidenceCandidate], topic: str) -> list[EvidenceCandidate]:
    terms = _topic_terms(topic)
    scored: list[tuple[int, int, EvidenceCandidate]] = []
    for index, candidate in enumerate(evidence):
        score = _topic_relevance_score(candidate, terms)
        if score > 0:
            scored.append((score, -index, candidate))
    scored.sort(reverse=True)
    return [candidate for _, _, candidate in scored]


def _topic_terms(topic: str) -> set[str]:
    raw_tokens = {
        token.casefold()
        for token in _TOPIC_TOKEN_RE.findall(topic)
        if len(token.casefold()) >= 2
    }
    terms = {token for token in raw_tokens if token not in _TOPIC_STOPWORDS}
    if not terms:
        terms = set(raw_tokens)

    lowered_topic = topic.casefold()
    for key, synonyms in _TOPIC_SYNONYMS.items():
        normalized_key = key.casefold()
        if normalized_key in raw_tokens or normalized_key in lowered_topic:
            terms.update(term.casefold() for term in synonyms)
    return terms


def _topic_relevance_score(candidate: EvidenceCandidate, terms: set[str]) -> int:
    title = (candidate.title_or_indicator or "").casefold()
    text = _evidence_search_text(candidate)
    score = 0
    for term in terms:
        if not term:
            continue
        if _topic_term_matches(title, term):
            score += 3
        elif _topic_term_matches(text, term):
            score += 1
    return score


def _topic_term_matches(text: str, term: str) -> bool:
    if re.fullmatch(r"[0-9a-z]+", term):
        pattern = rf"(?<![0-9a-z]){re.escape(term)}(?![0-9a-z])"
        return re.search(pattern, text) is not None
    return term in text


def _evidence_search_text(candidate: EvidenceCandidate) -> str:
    values = [
        candidate.title_or_indicator,
        candidate.snippet,
        candidate.publisher_or_institution,
        candidate.source_name,
        candidate.source_id,
        candidate.unit,
        candidate.url,
    ]
    return " ".join(value for value in values if value).casefold()


def _evidence_to_card(candidate: EvidenceCandidate) -> EvidenceCard:
    source_url = candidate.url or f"urn:content-research:{candidate.source_id or 'unknown'}"
    kind = _source_kind(candidate.source_id)
    source = SourceRef(
        title=candidate.title_or_indicator or "제목 확인 필요",
        publisher=candidate.publisher_or_institution or candidate.source_name or candidate.source_id or "unknown",
        url=source_url,
        kind=kind,
        published_at=candidate.published_or_observed_at,
        accessed_at=candidate.accessed_at,
    )
    numeric_facts = []
    if candidate.value:
        numeric_facts.append(
            NumericFact(
                value=candidate.value,
                unit=candidate.unit or "단위 확인 필요",
                as_of=candidate.published_or_observed_at or "기준일 확인 필요",
                source_url=source_url,
                label=candidate.title_or_indicator or "핵심 수치",
            )
        )
    return EvidenceCard(
        claim=_claim(candidate),
        summary_ko=candidate.snippet or "요약 문구는 원문 본문 저장 없이 메타데이터와 수치 중심으로 정리했습니다.",
        strength=ClaimStrength.VERIFIED if kind in {SourceKind.OFFICIAL, SourceKind.STATISTICS} else ClaimStrength.INTERPRETIVE,
        sources=[source],
        numeric_facts=numeric_facts,
        caveats=_caveats(candidate),
        tags=[candidate.source_id or "unknown"],
    )


def _claim(candidate: EvidenceCandidate) -> str:
    title = candidate.title_or_indicator or "수집 자료"
    if candidate.value:
        return f"{title}: {candidate.value} {candidate.unit or ''} ({candidate.published_or_observed_at or '기준일 확인 필요'})".strip()
    return title


def _caveats(candidate: EvidenceCandidate) -> list[str]:
    caveats = []
    if candidate.rights_status.get("allowed") is False:
        caveats.append("뉴스 본문은 저장하지 않고 메타데이터·링크·짧은 요약만 사용합니다.")
    missing = [field for field, status in candidate.field_status.items() if status == "missing"]
    if missing:
        caveats.append("누락 필드: " + ", ".join(missing))
    return caveats or ["추가 교차 확인 권장"]


def _source_kind(source_id: str | None) -> SourceKind:
    if source_id in {"ecos", "eia", "fred", "kosis", "opendart", "un_comtrade"}:
        return SourceKind.STATISTICS
    if source_id in {"naver_news", "newsapi", "nytimes"}:
        return SourceKind.NEWS
    return SourceKind.OTHER


def _score_from_evidence(evidence: list[EvidenceCandidate]) -> ChannelFitScore:
    official_count = sum(1 for item in evidence if _source_kind(item.source_id) is SourceKind.STATISTICS)
    news_count = sum(1 for item in evidence if _source_kind(item.source_id) is SourceKind.NEWS)
    source_availability = min(10.0, len(evidence))
    fact_checkability = min(10.0, official_count * 2.5 + news_count)
    total = round((source_availability * 0.45) + (fact_checkability * 0.35) + 1.5, 2)
    return ChannelFitScore(
        popularity=min(10.0, news_count * 2.0),
        economic_linkage=min(10.0, official_count * 2.5 + news_count),
        story_potential=min(10.0, news_count * 2.0 + official_count),
        source_availability=source_availability,
        risk_safety=7.0,
        total=total,
        rationale=f"Evidence {len(evidence)}개, 뉴스 {news_count}개, 공식자료 {official_count}개를 기준으로 산정했습니다.",
    )


def _source_label(candidate: EvidenceCandidate) -> str:
    publisher = candidate.publisher_or_institution or candidate.source_name or candidate.source_id or "unknown"
    title = candidate.title_or_indicator or "untitled"
    return f"{publisher}: {title}"


def _dispatch_approved_worker_pool(
    outline: object,
    evidence: list[EvidenceCandidate],
) -> tuple[list[WorkerInstruction], list[SlidePlan], list[ScriptSection]]:
    worker_instructions = _build_worker_instructions(evidence)
    slides = _build_approved_slides(outline, evidence)
    script = build_script(slides)
    return worker_instructions, slides, script


def _build_worker_instructions(evidence: list[EvidenceCandidate]) -> list[WorkerInstruction]:
    evidence_refs = _unique_source_labels(evidence, limit=10)
    return [
        WorkerInstruction(
            task_id="narrative_outline_worker",
            worker_role="Narrative Agent",
            instruction="검증된 EvidenceCard와 플랜리뷰 결과를 바탕으로 훅, 배경, 구조, 쟁점, 반전, 영향, 결론 흐름을 정리한다.",
            input_refs=["plan_review", *evidence_refs],
            expected_output="bundle.narrative",
        ),
        WorkerInstruction(
            task_id="ppt_outline_worker",
            worker_role="PPT Agent",
            instruction="승인된 내러티브를 15~25장 PPT 구성으로 확장하고 각 슬라이드별 검증 가능한 출처를 배정한다.",
            input_refs=["bundle.narrative", *evidence_refs],
            expected_output="bundle.slides",
            dependencies=["narrative_outline_worker"],
        ),
        WorkerInstruction(
            task_id="script_worker",
            worker_role="Script Agent",
            instruction="PPT 구성을 촬영용 대본으로 바꾸고 슬라이드별 자막, 구두 설명, 출처 참조를 연결한다.",
            input_refs=["bundle.slides"],
            expected_output="bundle.script",
            dependencies=["ppt_outline_worker"],
        ),
        WorkerInstruction(
            task_id="fact_risk_worker",
            worker_role="Fact/Risk Check Agent",
            instruction="EvidenceCard, PPT 구성, 대본을 검토해 팩트체크 표와 리스크 수정 제안을 작성한다.",
            input_refs=["bundle.evidence_cards", "bundle.slides", "bundle.script"],
            expected_output="bundle.fact_checks,bundle.risk_findings",
            dependencies=["ppt_outline_worker", "script_worker"],
        ),
        WorkerInstruction(
            task_id="assembly_worker",
            worker_role="Orchestrator Assembly",
            instruction="워커 산출물을 ResearchBundle, Markdown, JSONL 감사 로그로 묶는다.",
            input_refs=["bundle.narrative", "bundle.slides", "bundle.script", "bundle.fact_checks", "bundle.risk_findings"],
            expected_output="bundle.markdown,bundle.jsonl",
            dependencies=["narrative_outline_worker", "ppt_outline_worker", "script_worker", "fact_risk_worker"],
        ),
    ]


def _mark_worker_completed(task: WorkerInstruction) -> WorkerInstruction:
    return WorkerInstruction(
        task_id=task.task_id,
        worker_role=task.worker_role,
        instruction=task.instruction,
        input_refs=task.input_refs,
        expected_output=task.expected_output,
        dependencies=task.dependencies,
        status=WorkerTaskStatus.COMPLETED,
        result_ref=task.expected_output,
    )


def _build_approved_slides(outline: object, evidence: list[EvidenceCandidate]) -> list[SlidePlan]:
    return [
        type(slide)(
            number=slide.number,
            title=slide.title,
            core_message=slide.core_message,
            visual_idea=slide.visual_idea,
            speaker_note=slide.speaker_note,
            source_refs=_source_refs_for_slide(slide.title, evidence),
        )
        for slide in build_ppt_outline(outline)
    ]


def _source_refs_for_slide(slide_title: str, evidence: list[EvidenceCandidate]) -> list[str]:
    official = [item for item in evidence if _source_kind(item.source_id) in {SourceKind.OFFICIAL, SourceKind.PRIMARY, SourceKind.STATISTICS}]
    news = [item for item in evidence if _source_kind(item.source_id) is SourceKind.NEWS]
    other = [item for item in evidence if item not in official and item not in news]

    if any(keyword in slide_title for keyword in ("데이터", "지표", "확실한 사실")):
        selected = official + news
    elif any(keyword in slide_title for keyword in ("보도", "쟁점", "오해", "반전", "불확실")):
        selected = news + official
    elif any(keyword in slide_title for keyword in ("영향", "구조", "경로", "배경")):
        selected = official + news + other
    else:
        selected = news + official + other

    return _unique_source_labels(selected or evidence, limit=3)


def _unique_source_labels(evidence: list[EvidenceCandidate], limit: int) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for candidate in evidence:
        label = _source_label(candidate)
        if label in seen:
            continue
        seen.add(label)
        labels.append(label)
        if len(labels) >= limit:
            break
    return labels


def _plan_review_findings(cards: list[EvidenceCard]) -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    if len(cards) < _MIN_CORE_SOURCE_COUNT:
        findings.append(
            RiskFinding(
                item="핵심 자료 수",
                problem_type="insufficient_core_sources",
                risk_level=RiskLevel.HIGH,
                recommendation=(
                    f"촬영용 플랜 전환 전에 핵심 자료를 최소 {_MIN_CORE_SOURCE_COUNT}개까지 보강하세요. "
                    f"현재 사용 가능한 EvidenceCard는 {len(cards)}개입니다."
                ),
            )
        )

    official_count = sum(
        1
        for card in cards
        if any(source.kind in {SourceKind.OFFICIAL, SourceKind.PRIMARY, SourceKind.STATISTICS} for source in card.sources)
    )
    if official_count < _MIN_OFFICIAL_SOURCE_COUNT:
        findings.append(
            RiskFinding(
                item="공식·원문 자료 수",
                problem_type="insufficient_official_sources",
                risk_level=RiskLevel.HIGH,
                recommendation=(
                    f"공식 자료, 원문 자료, 통계 자료를 최소 {_MIN_OFFICIAL_SOURCE_COUNT}개 확보한 뒤 PPT와 대본을 확정하세요. "
                    f"현재 공식·원문 계열 EvidenceCard는 {official_count}개입니다."
                ),
            )
        )
    return findings


def _plan_review_stage(findings: list[RiskFinding]) -> WorkflowStage:
    if any(finding.risk_level is RiskLevel.HIGH for finding in findings):
        return WorkflowStage.BLOCKED
    return WorkflowStage.PENDING_REVIEW


def _merge_risk_findings(
    risk_findings: list[RiskFinding],
    plan_review_findings: list[RiskFinding],
) -> list[RiskFinding]:
    if not plan_review_findings:
        return risk_findings
    return [
        finding
        for finding in risk_findings
        if finding.problem_type != "review_status"
    ] + plan_review_findings


def _bundle_to_markdown(bundle: ResearchBundle) -> str:
    return bundle.to_markdown()


def _card_to_markdown(card: EvidenceCard) -> str:
    sources = "\n".join(
        f"- {source.publisher}, [{source.title}]({source.url})"
        for source in card.sources
    )
    numbers = "\n".join(
        f"- {fact.label or '숫자'}: {fact.value} {fact.unit}, 기준일 {fact.as_of}, 출처 {fact.source_url}"
        for fact in card.numeric_facts
    )
    caveats = "\n".join(f"- {caveat}" for caveat in card.caveats)
    return f"""### EvidenceCard

**주장:** {card.claim}

**요약:** {card.summary_ko}

**강도:** {card.strength.value}

**출처:**
{sources}

**숫자:**
{numbers or '- 없음'}

**주의:**
{caveats or '- 없음'}
"""


def _cell(value: object) -> str:
    text = str(value)
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    return "<br>".join(part.strip() for part in text.splitlines())
