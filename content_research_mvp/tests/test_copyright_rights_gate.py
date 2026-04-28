from content_research.sources.copyright.rights_gate import (
    DURABLE_BODY,
    TEMPORARY_CACHE,
    decide_storage,
)
from content_research.sources.copyright.source_registry import SourceRights, lookup_source_rights


def test_unknown_source_defaults_to_body_storage_blocked():
    rights = lookup_source_rights(
        domain="unknown.example",
        api_source_id="mystery_api",
        source_name="Mystery Publisher",
    )
    decision = decide_storage(rights)

    assert rights.body_collection_tier == 0
    assert rights.license_basis == "unknown"
    assert rights.retention_days == 0
    assert rights.quote_policy == "no_article_body"
    assert rights.to_dict()["body_collection_tier"] == 0
    assert decision.allowed is False
    assert decision.to_dict()["allowed"] is False
    assert decision.storage_policy == "metadata_only"


def test_news_discovery_source_is_metadata_only():
    rights = lookup_source_rights(domain="newsapi.org", api_source_id="newsapi", source_name="NewsAPI")
    decision = decide_storage(rights)

    assert rights.body_collection_tier == 0
    assert rights.license_basis == "metadata_only"
    assert decision.allowed is False


def test_tier_1_allows_temporary_cache_only():
    rights = SourceRights(
        body_collection_tier=1,
        license_basis="temporary_cache_terms",
        retention_days=7,
        quote_policy="short_quotes_only",
    )

    durable_decision = decide_storage(rights, requested_storage=DURABLE_BODY)
    cache_decision = decide_storage(rights, requested_storage=TEMPORARY_CACHE)

    assert durable_decision.allowed is False
    assert durable_decision.storage_policy == "temporary_cache"
    assert cache_decision.allowed is True
    assert cache_decision.storage_policy == "temporary_cache"


def test_tier_2_allows_licensed_body_storage():
    rights = SourceRights(
        body_collection_tier=2,
        license_basis="licensed_contract",
        retention_days=365,
        quote_policy="licensed_excerpt",
    )
    decision = decide_storage(rights)

    assert decision.allowed is True
    assert decision.storage_policy == "licensed_body"


def test_official_data_source_is_tier_3_and_allowed():
    rights = lookup_source_rights(domain="api.stlouisfed.org", api_source_id="fred", source_name="FRED")
    decision = decide_storage(rights)

    assert rights.body_collection_tier == 3
    assert rights.license_basis == "public_official_data"
    assert rights.retention_days is None
    assert rights.quote_policy == "official_data_excerpt"
    assert decision.allowed is True
    assert decision.storage_policy == "official_or_public_data"


def test_broad_official_parent_domains_do_not_upgrade_unknown_sources():
    press_rights = lookup_source_rights(domain="press.un.org", api_source_id="", source_name="")
    stlouis_rights = lookup_source_rights(domain="research.stlouisfed.org", api_source_id="", source_name="")
    eia_rights = lookup_source_rights(domain="www.eia.gov", api_source_id="", source_name="")

    assert press_rights.body_collection_tier == 0
    assert stlouis_rights.body_collection_tier == 0
    assert eia_rights.body_collection_tier == 0
