import json

import pytest

from content_research.collection.catalog import CollectionSource
from content_research.collection.process import HourlyCollectionProcess
from content_research.sources.news_discovery import naver_news
from content_research.sources.news_discovery.naver_news import NaverNewsClient, NaverNewsCredentials


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_naver_news_client_parses_metadata(monkeypatch):
    payload = {
        "total": 1,
        "start": 1,
        "display": 1,
        "items": [
            {
                "title": "한국 <b>경제</b> 뉴스",
                "originallink": "https://example.com/original",
                "link": "https://n.news.naver.com/article",
                "description": "요약 &amp; 설명",
                "pubDate": "Mon, 27 Apr 2026 10:00:00 +0900",
            }
        ],
    }

    def fake_urlopen(request, timeout):
        assert request.headers["X-naver-client-id"] == "client"
        assert request.headers["X-naver-client-secret"] == "secret"
        return FakeResponse(payload)

    monkeypatch.setattr(naver_news, "urlopen", fake_urlopen)

    client = NaverNewsClient(NaverNewsCredentials("client", "secret"))
    result = client.search("경제", display=1)

    assert result.total == 1
    assert result.items[0].title == "한국 경제 뉴스"
    assert result.items[0].description == "요약 & 설명"
    assert result.items[0].body_collection_tier == 0
    assert result.items[0].raw_text_storage == "none"


def test_collection_process_writes_naver_records(monkeypatch, tmp_path):
    item = naver_news.NaverNewsItem(
        source_id="naver_news",
        query="경제",
        title="테스트 뉴스",
        link="https://n.news.naver.com/test",
        original_link="https://example.com/test",
        description="테스트 요약",
        published_at="2026-04-27T10:00:00+09:00",
        raw_pub_date="Mon, 27 Apr 2026 10:00:00 +0900",
    )

    class FakeClient:
        def collect_queries(self, display=10, sort="date"):
            assert display == 10
            assert sort == "date"
            return [item]

    monkeypatch.setattr(naver_news.NaverNewsClient, "from_env", classmethod(lambda cls: FakeClient()))

    source = CollectionSource(
        source_id="naver_news",
        display_name="Naver News Search API",
        category="korean_news_discovery",
        adapter="news_discovery.naver_news",
        access_method="api",
        default_body_tier=0,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, _ = process.run_once()

    assert manifest.results[0].status == "fetched_metadata"
    assert manifest.results[0].collected_records == 1
    records_path = tmp_path / manifest.output_partition / "records" / "naver_news.jsonl"
    assert records_path.exists()
    assert "테스트 뉴스" in records_path.read_text(encoding="utf-8")

    manifest_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    source_result = next(record for record in manifest_records if record["type"] == "source_result")
    assert source_result["records_path"].endswith("naver_news.jsonl")


def test_naver_news_missing_credentials_returns_status(monkeypatch, tmp_path):
    monkeypatch.setattr(naver_news.NaverNewsClient, "from_env", classmethod(lambda cls: None))
    source = CollectionSource(
        source_id="naver_news",
        display_name="Naver News Search API",
        category="korean_news_discovery",
        adapter="news_discovery.naver_news",
        access_method="api",
        default_body_tier=0,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, _, _ = process.run_once()

    assert manifest.results[0].status == "missing_credentials"
    assert "NAVER_CLIENT_ID" in manifest.results[0].message


def test_invalid_naver_display_rejected():
    client = NaverNewsClient(NaverNewsCredentials("client", "secret"))

    with pytest.raises(ValueError, match="display"):
        client.search("경제", display=101)
