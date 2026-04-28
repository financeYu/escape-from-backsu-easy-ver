"""Root pipeline orchestrator for content research MVP."""

from __future__ import annotations

from pathlib import Path

from content_research.config import AppConfig, load_config
from content_research.deck.ppt_outline_builder import build_ppt_outline
from content_research.models import (
    ClaimStrength,
    NumericFact,
    ResearchBundle,
    SourceKind,
    SourceRef,
)
from content_research.narrative.outline_builder import build_outline
from content_research.research.evidence_card import build_evidence_card
from content_research.review.risk_report import build_risk_report
from content_research.scoring.channel_fit_score import calculate_channel_fit_score
from content_research.script.script_builder import build_script


class ContentResearchOrchestrator:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()

    def run(self, topic: str) -> ResearchBundle:
        if not topic.strip():
            raise ValueError("topic is required")

        placeholder_source = SourceRef(
            title="사용자 입력 기반 MVP 예시 자료",
            publisher="content_research_mvp",
            url="urn:content-research:mvp-placeholder",
            kind=SourceKind.PRIMARY,
            accessed_at=self.config.default_as_of or None,
        )
        card = build_evidence_card(
            claim=f"{topic}은 시사·경제 유튜브 리서치 주제로 검토할 수 있다.",
            summary_ko="첫 구현은 외부 API를 호출하지 않으므로 실제 자료 수집 전 단계의 예시 EvidenceCard를 생성합니다.",
            strength=ClaimStrength.SCENARIO,
            sources=[placeholder_source],
            numeric_facts=[
                NumericFact(
                    value="1",
                    unit="개 MVP 예시",
                    as_of=self.config.default_as_of or "not-set",
                    source_url="urn:content-research:mvp-placeholder",
                    label="생성된 예시 EvidenceCard",
                )
            ],
            caveats=["실제 촬영 전 공식 자료와 주요 보도로 교체해야 합니다."],
            tags=["mvp", "placeholder"],
        )
        score = calculate_channel_fit_score(
            popularity=6,
            economic_linkage=7,
            story_potential=7,
            source_availability=3,
            risk_safety=8,
            weights=self.config.scoring_weights,
            rationale="MVP 기본값입니다. 실제 Topic Radar와 Research 결과로 재산정해야 합니다.",
        )
        outline = build_outline(topic, [card])
        slides = build_ppt_outline(outline)
        script = build_script(slides)
        risk_findings = build_risk_report([card], "\n".join(section.narration for section in script))
        return ResearchBundle(
            topic_definition=f"{topic}: 확인 자료를 바탕으로 구조를 설명하는 시사·경제 콘텐츠 주제",
            why_now=[
                "최신 계기와 공식 자료 확인이 필요한 주제입니다.",
                "경제 연결성, 자료성, 리스크 안전성을 분리 평가합니다.",
                "투자 추천이 아니라 구조 이해를 목표로 합니다.",
            ],
            evidence_cards=[card],
            channel_fit=score,
            narrative=outline,
            slides=slides,
            script=script,
            risk_findings=risk_findings,
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

