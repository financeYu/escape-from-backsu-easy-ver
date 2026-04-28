"""Small helpers shared by JSON-based API adapters."""

from __future__ import annotations

import json
from typing import Any, TypeVar


ApiErrorT = TypeVar("ApiErrorT", bound=RuntimeError)


def parse_json_response(body: str, api_name: str, error_type: type[ApiErrorT]) -> Any:
    """Parse an API JSON body and convert malformed JSON into adapter errors."""

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        preview = " ".join(body[:200].split())
        detail = f": {preview}" if preview else ""
        raise error_type(f"{api_name} returned invalid JSON{detail}") from exc
