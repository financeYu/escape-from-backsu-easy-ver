from pathlib import Path

from content_research.collection.monitor import monitor_jsonl_files, summarize_report
from content_research.research.brief_builder import build_research_brief
from content_research.research.claim_extractor import extract_claims
from content_research.research.data_matcher import match_issue_data
from content_research.research.evidence_normalizer import normalize_jsonl_file
from content_research.research.issue_radar import detect_issue_candidates
from content_research.research.priority_scorer import score_issue_priorities


FIXTURES = Path(__file__).parent / "fixtures"


def test_content_research_minimum_end_to_end_smoke():
    stage_log: list[str] = []

    try:
        stage_log.append("1. read sample JSONL input")
        records_path = FIXTURES / "e2e_sample_records.jsonl"
        monitor_path = FIXTURES / "e2e_collection_manifest.jsonl"
        assert records_path.exists()
        assert monitor_path.exists()

        stage_log.append("2. normalize Evidence candidates")
        evidence = normalize_jsonl_file(records_path)
        evidence_records = [candidate.to_dict() for candidate in evidence]
        assert len(evidence_records) == 3
        assert {record["source_id"] for record in evidence_records} == {"newsapi", "nytimes", "eia"}
        assert any(
            record["rights_status"]["allowed"] is False and record["rights_status"]["storage_policy"] == "metadata_only"
            for record in evidence_records
            if record["source_id"] in {"newsapi", "nytimes"}
        )
        assert any(
            record["rights_status"]["allowed"] is True
            and record["rights_status"]["storage_policy"] == "official_or_public_data"
            for record in evidence_records
            if record["source_id"] == "eia"
        )

        stage_log.append("3. detect issue candidates")
        issues = detect_issue_candidates(evidence)
        assert len(issues) == 1
        issue = issues[0]
        assert issue.related_evidence_ids == ["ev_oil_news_1", "ev_oil_news_2"]
        assert "Energy" in " ".join(issue.representative_titles)

        stage_log.append("4. match official data")
        matches = match_issue_data(issues, evidence)
        assert len(matches) == 1
        assert matches[0].source_id == "eia"
        assert matches[0].value == "83.10"
        assert matches[0].unit == "dollars per barrel"

        stage_log.append("5. extract claims, numbers, and dates")
        claims = extract_claims(evidence)
        claim_records = [claim.to_dict() for claim in claims]
        assert any(claim["needs_verification"] for claim in claim_records if claim["source_id"] in {"newsapi", "nytimes"})
        assert any(not claim["needs_verification"] for claim in claim_records if claim["source_id"] == "eia")
        assert any("83.10 dollars" in number for claim in claim_records for number in claim["key_numbers"])

        stage_log.append("6. score internal priorities")
        priority_scores = score_issue_priorities(issues, data_matches=matches, claims=claims)
        assert len(priority_scores) == 1
        assert priority_scores[0].issue_id == issue.issue_id
        assert priority_scores[0].internal_score > 0

        stage_log.append("7. build research brief")
        brief = build_research_brief(
            issue_id=issue.issue_id,
            issue_candidates=issues,
            evidence_candidates=evidence,
            data_matches=matches,
            claims=claims,
        )
        brief_markdown = brief.to_markdown()
        assert "83.10 dollars per barrel" in "\n".join(brief.key_facts)
        assert any("needs_verification" in item for item in brief.final_check)
        assert any("no body use" in source for source in brief.sources)
        assert "## " in brief_markdown

        stage_log.append("8. monitor collection status")
        monitor_report = monitor_jsonl_files([monitor_path], expected_min_records={"newsapi": 1, "eia": 1})
        monitor_summary = summarize_report(monitor_report)
        assert monitor_summary["status_counts"] == {"success": 2}
        assert all(source.last_success_at for source in monitor_report.sources)

    except Exception as exc:
        raise AssertionError("E2E failed after stages: " + " > ".join(stage_log)) from exc
