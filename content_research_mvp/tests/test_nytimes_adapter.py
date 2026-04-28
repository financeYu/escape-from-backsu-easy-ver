import json

import pytest

from content_research.collection.catalog import CollectionSource
from content_research.collection.process import HourlyCollectionProcess
from content_research.sources.news_discovery import nytimes
from content_research.sources.news_discovery.nytimes import NYTimesClient, NYTimesCredentials


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_nytimes_article_search_parses_metadata(monkeypatch):
    payload = {
        "response": {
            "meta": {"hits": 1, "offset": 0, "time": 4},
            "docs": [
                {
                    "web_url": "https://www.nytimes.com/2026/04/27/business/test.html",
                    "snippet": "Snippet text",
                    "lead_paragraph": "Lead paragraph text",
                    "abstract": "Abstract text",
                    "headline": {"main": "NYT Test Story"},
                    "pub_date": "2026-04-27T02:00:00+0000",
                    "section_name": "Business",
                    "subsection_name": "Economy",
                    "byline": {"original": "By Test Reporter"},
                    "type_of_material": "News",
                    "_id": "nyt://article/test",
                }
            ],
        }
    }

    def fake_urlopen(request, timeout):
        assert "articlesearch.json" in request.full_url
        assert "api-key=secret" in request.full_url
        return FakeResponse(payload)

    monkeypatch.setattr(nytimes, "urlopen", fake_urlopen)

    client = NYTimesClient(NYTimesCredentials("secret"))
    result = client.search_articles("economy")

    assert result.hits == 1
    assert result.items[0].title == "NYT Test Story"
    assert result.items[0].collection_api == "article_search"
    assert result.items[0].body_collection_tier == 0
    assert result.items[0].raw_text_storage == "none"


def test_nytimes_top_stories_parses_metadata(monkeypatch):
    payload = {
        "results": [
            {
                "section": "world",
                "subsection": "asia",
                "title": "Top Story",
                "abstract": "Top abstract",
                "url": "https://www.nytimes.com/2026/04/27/world/test.html",
                "byline": "By Test Reporter",
                "published_date": "2026-04-27T02:00:00-04:00",
                "material_type_facet": "News",
            }
        ]
    }

    def fake_urlopen(request, timeout):
        assert "topstories" in request.full_url
        assert "world.json" in request.full_url
        return FakeResponse(payload)

    monkeypatch.setattr(nytimes, "urlopen", fake_urlopen)

    client = NYTimesClient(NYTimesCredentials("secret"))
    result = client.top_stories("world")

    assert result.section == "world"
    assert result.items[0].title == "Top Story"
    assert result.items[0].collection_api == "top_stories"
    assert result.items[0].top_story_section == "world"


def test_collection_process_writes_nytimes_records(monkeypatch, tmp_path):
    item = nytimes.NYTimesArticleItem(
        source_id="nytimes",
        collection_api="article_search",
        title="NYT Metadata Story",
        url="https://www.nytimes.com/test",
        published_at="2026-04-27T02:00:00+0000",
        section="Business",
        subsection="",
        byline="By Test Reporter",
        abstract="Abstract",
        snippet="Snippet",
        lead_paragraph="Lead",
        query="economy",
    )

    class FakeClient:
        def collect_default(self):
            return [item]

    monkeypatch.setattr(nytimes.NYTimesClient, "from_env", classmethod(lambda cls: FakeClient()))

    source = CollectionSource(
        source_id="nytimes",
        display_name="The New York Times",
        category="international_publisher",
        adapter="news_discovery.nytimes",
        access_method="api",
        default_body_tier=0,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, jsonl_path, _ = process.run_once()

    assert manifest.results[0].status == "fetched_metadata"
    assert manifest.results[0].collected_records == 1
    records_path = tmp_path / manifest.output_partition / "records" / "nytimes.jsonl"
    assert records_path.exists()
    assert "NYT Metadata Story" in records_path.read_text(encoding="utf-8")

    manifest_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    source_result = next(record for record in manifest_records if record["type"] == "source_result")
    assert source_result["records_path"].endswith("nytimes.jsonl")


def test_nytimes_missing_credentials_returns_status(monkeypatch, tmp_path):
    monkeypatch.setattr(nytimes.NYTimesClient, "from_env", classmethod(lambda cls: None))
    source = CollectionSource(
        source_id="nytimes",
        display_name="The New York Times",
        category="international_publisher",
        adapter="news_discovery.nytimes",
        access_method="api",
        default_body_tier=0,
    )
    process = HourlyCollectionProcess(output_dir=tmp_path, sources=[source])

    manifest, _, _ = process.run_once()

    assert manifest.results[0].status == "missing_credentials"
    assert "NYTIMES_API_KEY" in manifest.results[0].message


def test_invalid_nytimes_page_rejected():
    client = NYTimesClient(NYTimesCredentials("secret"))

    with pytest.raises(ValueError, match="page"):
        client.search_articles("economy", page=11)
