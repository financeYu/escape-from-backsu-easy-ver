import json

from content_research.models import (
    ChannelFitScore,
    ClaimStrength,
    EvidenceCard,
    NarrativeOutline,
    ResearchBundle,
    RiskFinding,
    RiskLevel,
    ScriptSection,
    SlidePlan,
    SourceKind,
    SourceRef,
)


def test_research_bundle_serializes_to_jsonl_and_markdown():
    source = SourceRef(
        title="Official release",
        publisher="Test Agency",
        url="https://example.com/release",
        kind=SourceKind.OFFICIAL,
    )
    card = EvidenceCard(
        claim="검증된 주장",
        summary_ko="한국어 요약",
        strength=ClaimStrength.VERIFIED,
        sources=[source],
    )
    bundle = ResearchBundle(
        topic_definition="한 줄 주제",
        why_now=["지금 중요한 이유"],
        evidence_cards=[card],
        channel_fit=ChannelFitScore(7, 8, 7, 8, 9, 7.8, "근거"),
        narrative=NarrativeOutline("훅", "배경", "구조", "쟁점", "반전", "영향", "결론"),
        slides=[SlidePlan(1, "제목", "메시지", "시각자료", "노트", ["https://example.com/release"])],
        script=[ScriptSection(1, "오프닝", "대본", "자막", ["https://example.com/release"])],
        risk_findings=[RiskFinding("전체", "review_status", RiskLevel.LOW, "사용 가능")],
    )

    jsonl = bundle.to_jsonl()
    records = [json.loads(line) for line in jsonl.splitlines()]

    assert records[0]["type"] == "bundle_meta"
    assert any(record["type"] == "evidence_card" for record in records)
    assert "유튜브 리서치 브리프" in bundle.to_markdown()

