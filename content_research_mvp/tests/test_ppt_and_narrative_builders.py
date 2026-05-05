from content_research.deck.ppt_outline_builder import build_ppt_outline
from content_research.models import NarrativeOutline
from content_research.narrative.outline_builder import build_outline
from content_research.script.script_builder import build_script


def test_ppt_outline_uses_mvp_slide_range():
    outline = NarrativeOutline(
        hook="훅",
        background="배경",
        structure="구조",
        issues="쟁점",
        twist="반전",
        impact="영향",
        conclusion="결론",
    )

    slides = build_ppt_outline(outline)

    assert 15 <= len(slides) <= 25
    assert slides[0].number == 1
    assert slides[-1].number == len(slides)
    assert slides[-1].title == "마무리 체크포인트"


def test_outline_uses_natural_subject_particle_for_korean_topic():
    assert build_outline("국제 유가", []).hook.startswith("국제 유가는 ")
    assert build_outline("환율", []).hook.startswith("환율은 ")


def test_script_builder_uses_slide_specific_narration():
    outline = NarrativeOutline(
        hook="훅",
        background="배경",
        structure="구조",
        issues="쟁점",
        twist="반전",
        impact="영향",
        conclusion="결론",
    )
    slides = build_ppt_outline(outline)

    script = build_script(slides)

    data_section = next(section for section in script if section.section == "핵심 데이터 1")
    issue_section = next(section for section in script if section.section == "쟁점 정리")
    impact_section = next(section for section in script if section.section == "생활 영향")
    assert "숫자는 단위와 기준일" in data_section.narration
    assert "확인된 사실, 보도된 주장" in issue_section.narration
    assert "개인, 기업, 정부, 시장" in impact_section.narration
    assert len({section.narration for section in script}) >= 8
