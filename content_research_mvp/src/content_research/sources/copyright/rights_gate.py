"""Rights gate for deciding whether source body text may be stored."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from content_research.sources.copyright.source_registry import SourceRights


DURABLE_BODY = "durable_body"
TEMPORARY_CACHE = "temporary_cache"
LICENSED_BODY = "licensed_body"
OFFICIAL_DATA = "official_or_public_data"
METADATA_ONLY = "metadata_only"


@dataclass(frozen=True)
class RightsDecision:
    allowed: bool
    reason: str
    storage_policy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def decide_storage(
    source_rights: SourceRights,
    *,
    requested_storage: str = DURABLE_BODY,
) -> RightsDecision:
    """Decide whether the requested source body storage is allowed."""

    tier = source_rights.body_collection_tier

    if tier == 0:
        return RightsDecision(
            allowed=False,
            reason="Body storage is blocked because the source is unknown or metadata-only.",
            storage_policy=METADATA_ONLY,
        )

    if tier == 1:
        if requested_storage == TEMPORARY_CACHE:
            return RightsDecision(
                allowed=True,
                reason="Temporary cache is allowed under the source retention policy.",
                storage_policy=TEMPORARY_CACHE,
            )
        return RightsDecision(
            allowed=False,
            reason="Durable body storage is blocked; this source only allows temporary cache storage.",
            storage_policy=TEMPORARY_CACHE,
        )

    if tier == 2:
        return RightsDecision(
            allowed=True,
            reason="Licensed body storage is allowed under the recorded license basis.",
            storage_policy=LICENSED_BODY,
        )

    if tier == 3:
        return RightsDecision(
            allowed=True,
            reason="Official or public data storage is allowed with provenance and attribution.",
            storage_policy=OFFICIAL_DATA,
        )

    return RightsDecision(
        allowed=False,
        reason=f"Body storage is blocked because body_collection_tier={tier} is not recognized.",
        storage_policy=METADATA_ONLY,
    )
