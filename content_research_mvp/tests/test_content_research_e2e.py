import os
from pathlib import Path

import pytest

from content_research.collection.catalog import DEFAULT_COLLECTION_SOURCES, MVP_COLLECTION_SOURCE_IDS
from content_research.collection.monitor import monitor_jsonl_files, summarize_report
from content_research.collection.process import HourlyCollectionProcess
from content_research.env import load_dotenv
from content_research.research.brief_builder import build_research_brief
from content_research.research.claim_extractor import extract_claims
from content_research.research.data_matcher import match_issue_data
from content_research.research.evidence_normalizer import normalize_jsonl_file
from content_research.research.issue_radar import detect_issue_candidates
from content_research.research.priority_scorer import score_issue_priorities


FIXTURES = Path(__file__).parent / "fixtures"
LIVE_E2E_ENV = "CONTENT_RESEARCH_RUN_LIVE_E2E"


def test_content_research_offline_e2e_fixture_to_brief_markdown_contract():
    stage_log: list[str] = []

    try:
        stage_log.append("1. read expanded offline JSONL fixtures")
        records_path = FIXTURES / "e2e_sample_records.jsonl"
        monitor_path = FIXTURES / "e2e_collection_manifest.jsonl"
        assert records_path.exists()
        assert monitor_path.exists()

        stage_log.append("2. normalize only MVP Evidence candidates")
        evidence = normalize_jsonl_file(records_path)
        evidence_records = [candidate.to_dict() for candidate in evidence]
        assert len(evidence_records) == 4
        assert {record["source_id"] for record in evidence_records} == {"newsapi", "nytimes", "eia", "ecos"}
        assert "guardian" not in {record["source_id"] for record in evidence_records}
        assert any(record["field_status"]["collected_at"] == "missing" for record in evidence_records)
        assert any(record["field_status"]["collected_at"] == "present" for record in evidence_records)
        assert any(
            record["rights_status"]["allowed"] is False and record["rights_status"]["storage_policy"] == "metadata_only"
            for record in evidence_records
            if record["source_id"] in {"newsapi", "nytimes"}
        )
        assert any(
            record["rights_status"]["allowed"] is True
            and record["rights_status"]["storage_policy"] == "official_or_public_data"
            for record in evidence_records
            if record["source_id"] in {"eia", "ecos"}
        )

        stage_log.append("3. detect issue candidates from MVP news Evidence")
        issues = detect_issue_candidates(evidence)
        energy_issues = [issue for issue in issues if {"ev_oil_news_1", "ev_oil_news_2"}.issubset(set(issue.related_evidence_ids))]
        assert len(energy_issues) == 1
        issue = energy_issues[0]
        assert "Energy" in " ".join(issue.representative_titles)

        stage_log.append("4. match official data")
        matches = match_issue_data([issue], evidence)
        assert len(matches) == 1
        assert matches[0].source_id == "eia"
        assert matches[0].value == "83.10"
        assert matches[0].unit == "dollars per barrel"

        stage_log.append("5. extract claims, numbers, and dates")
        claims = extract_claims(evidence)
        claim_records = [claim.to_dict() for claim in claims]
        assert any(claim["needs_verification"] for claim in claim_records if claim["source_id"] in {"newsapi", "nytimes"})
        assert any(not claim["needs_verification"] for claim in claim_records if claim["source_id"] in {"eia", "ecos"})
        assert any("83.10 dollars" in number for claim in claim_records for number in claim["key_numbers"])

        stage_log.append("6. score internal priorities")
        priority_scores = score_issue_priorities([issue], data_matches=matches, claims=claims)
        assert len(priority_scores) == 1
        assert priority_scores[0].issue_id == issue.issue_id
        assert priority_scores[0].internal_score > 0

        stage_log.append("7. build readable ResearchBrief Markdown")
        brief = build_research_brief(
            issue_id=issue.issue_id,
            issue_candidates=[issue],
            evidence_candidates=evidence,
            data_matches=matches,
            claims=claims,
        )
        brief_markdown = brief.to_markdown()
        assert "83.10 dollars per barrel" in "\n".join(brief.key_facts)
        assert any("needs_verification" in item for item in brief.final_check)
        assert any("no body use" in source for source in brief.sources)
        assert "guardian" not in brief_markdown
        assert "## 제목" in brief_markdown
        assert "## 핵심 요약" in brief_markdown
        assert "## 근거와 출처" in brief_markdown
        assert "출처명 Reuters" in brief_markdown
        assert "수집 2026-04-27T11:00:00+09:00" in brief_markdown
        assert "수집 시각 확인 필요" in brief_markdown
        assert _has_no_mojibake_markers(brief_markdown)

        stage_log.append("8. monitor collection status including non-MVP separation")
        monitor_report = monitor_jsonl_files(
            [monitor_path],
            expected_min_records={"newsapi": 1, "nytimes": 1, "eia": 1, "ecos": 1},
        )
        monitor_summary = summarize_report(monitor_report)
        assert monitor_summary["status_counts"] == {"success": 4, "planned_non_mvp": 1}
        assert {source.source_id for source in monitor_report.sources} >= {"newsapi", "nytimes", "eia", "ecos", "guardian"}

    except Exception as exc:
        raise AssertionError("Offline E2E failed after stages: " + " > ".join(stage_log)) from exc


def test_content_research_optional_live_e2e_collect_once_dry_run(tmp_path):
    if os.environ.get(LIVE_E2E_ENV) != "1":
        pytest.skip(f"set {LIVE_E2E_ENV}=1 to run optional live/dry-run E2E")

    load_dotenv(".env")
    credential_env_by_source = {
        "naver_news": ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"),
        "newsapi": ("NEWSAPI_KEY",),
        "nytimes": ("NYTIMES_API_KEY",),
        "ecos": ("ECOS_API_KEY",),
        "kosis": ("KOSIS_API_KEY",),
        "opendart": ("OPENDART_API_KEY",),
        "fred": ("FRED_API_KEY",),
        "eia": ("EIA_API_KEY",),
        "un_comtrade": ("UN_COMTRADE_KEY", "COMTRADE_API_KEY"),
    }
    live_source_ids = {
        source_id
        for source_id, env_names in credential_env_by_source.items()
        if all(os.environ.get(name, "").strip() for name in env_names)
        or (source_id == "un_comtrade" and any(os.environ.get(name, "").strip() for name in env_names))
    }
    if not live_source_ids:
        pytest.skip("no MVP API credentials are configured for optional live/dry-run E2E")

    sources = [
        source
        for source in DEFAULT_COLLECTION_SOURCES
        if source.source_id in MVP_COLLECTION_SOURCE_IDS and source.source_id in live_source_ids
    ]
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=sources)

    manifest, jsonl_path, markdown_path = process.run_once(mode="live_e2e")

    assert jsonl_path.exists()
    assert markdown_path.exists()
    assert {result.source_id for result in manifest.results} == live_source_ids
    assert all(result.status not in {"planned", "planned_non_mvp", "missing_handler"} for result in manifest.results)
    assert all(result.status != "missing_credentials" for result in manifest.results)


def _has_no_mojibake_markers(markdown: str) -> bool:
    markers = ("?댁", "異쒖", "紐", "筌", "\ufffd")
    return not any(marker in markdown for marker in markers)
