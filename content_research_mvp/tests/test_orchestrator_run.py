import json
from types import SimpleNamespace

import content_research.pipeline.orchestrator as orchestrator_module
from content_research.cli import build_parser
from content_research.config import AppConfig, CollectionConfig
from content_research.models import WorkerTaskStatus, WorkflowStage
from content_research.pipeline.orchestrator import ContentResearchOrchestrator


def _write_oil_records(tmp_path):
    records_path = tmp_path / "records.jsonl"
    records = [
        {
            "evidence_id": "ev_oil_news",
            "source_id": "newsapi",
            "source_name": "Reuters",
            "title": "Oil prices rise after supply warning",
            "description": "Energy markets watch OPEC supply signals.",
            "url": "https://example.com/oil",
            "published_at": "2026-04-27T02:00:00Z",
            "collected_at": "2026-04-27T11:00:00+09:00",
            "content_snippet": "WTI traded near 83.10 dollars per barrel.",
        },
        {
            "evidence_id": "data_eia_wti",
            "source_id": "eia",
            "series_id": "PET.RWTC.D",
            "series_description": "WTI crude oil spot price",
            "period": "2026-04-24",
            "value": "83.10",
            "units": "dollars per barrel",
            "retrieved_at": "2026-04-27T11:02:00+09:00",
            "body_collection_tier": 3,
        },
    ]
    records_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return records_path


def test_run_stops_at_plan_review_without_user_approval(monkeypatch, tmp_path):
    records_path = _write_oil_records(tmp_path)

    class FakeCollectionProcess:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def run_once(self, mode="manual"):
            assert mode == "run"
            manifest = SimpleNamespace(
                results=[
                    SimpleNamespace(source_id="newsapi", status="fetched_metadata", message="", records_path=str(records_path))
                ]
            )
            return manifest, None, None

    monkeypatch.setattr(orchestrator_module, "HourlyCollectionProcess", FakeCollectionProcess)
    config = AppConfig(
        output_dir=tmp_path / "outputs",
        collection=CollectionConfig(output_dir=tmp_path / "collections"),
    )

    bundle = ContentResearchOrchestrator(config).run("국제 유가")

    assert bundle.evidence_cards
    assert bundle.workflow_stage is WorkflowStage.BLOCKED
    assert bundle.approval_required is True
    assert bundle.approved_by is None
    assert bundle.approved_at is None
    assert bundle.worker_instructions == []
    assert bundle.slides == []
    assert bundle.script == []
    assert all("placeholder" not in card.tags for card in bundle.evidence_cards)
    assert any(card.sources[0].url == "https://example.com/oil" for card in bundle.evidence_cards)
    assert any(
        fact.value == "83.10"
        for card in bundle.evidence_cards
        for fact in card.numeric_facts
    )
    assert any(finding.problem_type == "insufficient_core_sources" for finding in bundle.risk_findings)
    assert any(finding.problem_type == "insufficient_official_sources" for finding in bundle.risk_findings)
    assert not any(finding.problem_type == "review_status" for finding in bundle.risk_findings)

    markdown_path, jsonl_path = ContentResearchOrchestrator(config).write_outputs(bundle)
    markdown = markdown_path.read_text(encoding="utf-8")
    jsonl = jsonl_path.read_text(encoding="utf-8")

    assert "승인 상태: blocked" in markdown
    assert "사용자 승인 대기" in markdown
    assert '"workflow_stage": "blocked"' in jsonl
    assert '"approval_required": true' in jsonl
    assert '"type": "fact_check"' in jsonl


def test_run_builds_orchestrated_bundle_after_user_approval(monkeypatch, tmp_path):
    records_path = _write_oil_records(tmp_path)

    class FakeCollectionProcess:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def run_once(self, mode="manual"):
            assert mode == "run"
            manifest = SimpleNamespace(
                results=[
                    SimpleNamespace(source_id="newsapi", status="fetched_metadata", message="", records_path=str(records_path))
                ]
            )
            return manifest, None, None

    monkeypatch.setattr(orchestrator_module, "HourlyCollectionProcess", FakeCollectionProcess)
    config = AppConfig(
        output_dir=tmp_path / "outputs",
        collection=CollectionConfig(output_dir=tmp_path / "collections"),
    )

    bundle = ContentResearchOrchestrator(config).run("국제 유가", approve_plan=True, approved_by="tester")

    assert bundle.workflow_stage is WorkflowStage.ORCHESTRATED
    assert bundle.approval_required is False
    assert bundle.approved_by == "tester"
    assert bundle.approved_at
    task_ids = [task.task_id for task in bundle.worker_instructions]
    assert task_ids == [
        "narrative_outline_worker",
        "ppt_outline_worker",
        "script_worker",
        "fact_risk_worker",
        "assembly_worker",
    ]
    assert all(task.status is WorkerTaskStatus.COMPLETED for task in bundle.worker_instructions)
    assert bundle.worker_instructions[1].dependencies == ["narrative_outline_worker"]
    assert bundle.worker_instructions[2].input_refs == ["bundle.slides"]
    assert bundle.worker_instructions[3].expected_output == "bundle.fact_checks,bundle.risk_findings"
    data_slide = next(slide for slide in bundle.slides if slide.title == "핵심 데이터 1")
    news_slide = next(slide for slide in bundle.slides if slide.title == "주요 보도 정리")
    assert data_slide.source_refs
    assert news_slide.source_refs
    assert "U.S. Energy Information Administration" in data_slide.source_refs[0]
    assert "Reuters" in news_slide.source_refs[0]

    markdown_path, jsonl_path = ContentResearchOrchestrator(config).write_outputs(bundle)
    markdown = markdown_path.read_text(encoding="utf-8")
    jsonl = jsonl_path.read_text(encoding="utf-8")

    assert "# 유튜브 리서치 브리프" in markdown
    assert "승인 상태: orchestrated" in markdown
    assert "## 3. 핵심 자료 10개" in markdown
    assert "## 6. 팩트체크 표" in markdown
    assert "## 7. 리스크 수정 제안" in markdown
    assert "WTI crude oil spot price" in markdown
    assert "## 오케스트라 워커 지시" in markdown
    assert "ppt_outline_worker" in markdown
    assert '"workflow_stage": "orchestrated"' in jsonl
    assert '"approved_by": "tester"' in jsonl
    assert '"type": "worker_instruction"' in jsonl
    assert '"task_id": "script_worker"' in jsonl
    assert '"type": "fact_check"' in jsonl
    assert "placeholder" not in markdown.lower()
    assert "placeholder" not in jsonl.lower()


def test_run_filters_collected_evidence_to_requested_topic(monkeypatch, tmp_path):
    records_path = tmp_path / "records.jsonl"
    records = [
        {
            "evidence_id": "ev_oil_news",
            "source_id": "newsapi",
            "source_name": "Reuters",
            "title": "Oil prices rise after supply warning",
            "description": "Energy markets watch OPEC supply signals.",
            "url": "https://example.com/oil",
            "published_at": "2026-04-27T02:00:00Z",
            "collected_at": "2026-04-27T11:00:00+09:00",
            "content_snippet": "WTI traded near 83.10 dollars per barrel.",
        },
        {
            "evidence_id": "ev_chip_news",
            "source_id": "newsapi",
            "source_name": "Bloomberg",
            "title": "AI chip export controls lift Nvidia and HBM supply concerns",
            "description": "Semiconductor suppliers track new demand signals.",
            "url": "https://example.com/chips",
            "published_at": "2026-04-27T01:00:00Z",
            "collected_at": "2026-04-27T11:00:00+09:00",
            "content_snippet": "AI accelerator and memory supply remains tight.",
        },
    ]
    records_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )

    class FakeCollectionProcess:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def run_once(self, mode="manual"):
            manifest = SimpleNamespace(
                results=[
                    SimpleNamespace(source_id="newsapi", status="fetched_metadata", message="", records_path=str(records_path))
                ]
            )
            return manifest, None, None

    monkeypatch.setattr(orchestrator_module, "HourlyCollectionProcess", FakeCollectionProcess)
    config = AppConfig(
        output_dir=tmp_path / "outputs",
        collection=CollectionConfig(output_dir=tmp_path / "collections"),
    )

    bundle = ContentResearchOrchestrator(config).run("AI semiconductors")

    source_urls = [source.url for card in bundle.evidence_cards for source in card.sources]
    assert "https://example.com/chips" in source_urls
    assert "https://example.com/oil" not in source_urls
    assert all("oil" not in card.claim.casefold() for card in bundle.evidence_cards)


def test_run_reports_topic_mismatch_instead_of_selecting_unrelated_issue(monkeypatch, tmp_path):
    records_path = tmp_path / "records.jsonl"
    records = [
        {
            "evidence_id": "ev_oil_news",
            "source_id": "newsapi",
            "source_name": "Reuters",
            "title": "Oil prices rise after supply warning",
            "description": "Energy markets watch OPEC supply signals.",
            "url": "https://example.com/oil",
            "published_at": "2026-04-27T02:00:00Z",
            "collected_at": "2026-04-27T11:00:00+09:00",
            "content_snippet": "WTI traded near 83.10 dollars per barrel.",
        }
    ]
    records_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )

    class FakeCollectionProcess:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def run_once(self, mode="manual"):
            manifest = SimpleNamespace(
                results=[
                    SimpleNamespace(source_id="newsapi", status="fetched_metadata", message="", records_path=str(records_path))
                ]
            )
            return manifest, None, None

    monkeypatch.setattr(orchestrator_module, "HourlyCollectionProcess", FakeCollectionProcess)
    config = AppConfig(
        output_dir=tmp_path / "outputs",
        collection=CollectionConfig(output_dir=tmp_path / "collections"),
    )

    bundle = ContentResearchOrchestrator(config).run("AI semiconductors")

    assert bundle.evidence_cards[0].tags == ["topic_mismatch"]
    assert bundle.risk_findings[0].problem_type == "no_topic_evidence"
    assert "https://example.com/oil" not in [source.url for source in bundle.evidence_cards[0].sources]
    assert "1" in bundle.evidence_cards[0].caveats[0]


def test_run_reports_collection_status_when_no_evidence(monkeypatch, tmp_path):
    class FakeCollectionProcess:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def run_once(self, mode="manual"):
            manifest = SimpleNamespace(
                results=[
                    SimpleNamespace(
                        source_id="newsapi",
                        status="missing_credentials",
                        message="NEWSAPI_KEY is required in environment or .env.",
                        records_path="",
                    )
                ]
            )
            return manifest, None, None

    monkeypatch.setattr(orchestrator_module, "HourlyCollectionProcess", FakeCollectionProcess)
    config = AppConfig(
        output_dir=tmp_path / "outputs",
        collection=CollectionConfig(output_dir=tmp_path / "collections"),
    )

    bundle = ContentResearchOrchestrator(config).run("국제 유가")

    assert bundle.evidence_cards[0].tags == ["collection_status"]
    assert bundle.risk_findings[0].problem_type == "missing_evidence"
    assert "NEWSAPI_KEY" in bundle.evidence_cards[0].caveats[0]


def test_run_cli_accepts_worker_task_output_option():
    args = build_parser().parse_args(
        [
            "run",
            "--topic",
            "국제 유가",
            "--approve-plan",
            "--approved-by",
            "tester",
            "--emit-worker-tasks",
        ]
    )

    assert args.approve_plan is True
    assert args.approved_by == "tester"
    assert args.emit_worker_tasks is True
