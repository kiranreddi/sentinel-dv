"""Shared validation and response envelopes for MCP tools."""

from __future__ import annotations

import json
import re

from sentinel_dv.config import get_config
from sentinel_dv.schemas.common import PaginationInfo
from sentinel_dv.schemas.versioning import CURRENT_SCHEMA_VERSION

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,127}$")


def validate_id(value: str, field: str) -> str:
    """Validate stable identifier strings (run_id, test_id, etc.)."""
    if not _ID_PATTERN.match(value):
        raise ValueError(f"Invalid {field}: must match [a-z][a-z0-9_]*")
    return value


def clamp_pagination(page: int, page_size: int) -> tuple[int, int]:
    """Clamp pagination to configured security limits."""
    if page < 1:
        raise ValueError("page must be >= 1")
    max_page_size = get_config().security.max_page_size
    if page_size < 1 or page_size > max_page_size:
        raise ValueError(f"page_size must be between 1 and {max_page_size}")
    return page, page_size


def pagination_dict(page: int, page_size: int, total: int) -> dict:
    """Build pagination metadata dict."""
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginationInfo(
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=total_pages,
    ).model_dump()


def bound_response(payload: dict) -> dict:
    """Truncate oversized MCP payloads to configured max_response_bytes."""
    max_bytes = get_config().security.max_response_bytes
    encoded = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    if len(encoded) <= max_bytes:
        return payload
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "error": {
            "code": "LIMIT_EXCEEDED",
            "message": (
                f"Response exceeds max_response_bytes ({max_bytes}); "
                "narrow filters or reduce page_size."
            ),
            "details": {"bytes": len(encoded), "max_bytes": max_bytes},
        },
    }


def list_response(
    key: str,
    items: list,
    page: int,
    page_size: int,
    total: int,
    extra: dict | None = None,
) -> dict:
    """Standard list tool response envelope.

    Args:
        key: Primary result key name.
        items: List of result items.
        page: Current page number.
        page_size: Items per page.
        total: Total number of items across all pages.
        extra: Optional extra fields merged into the top-level response dict.
    """
    payload: dict = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        key: items,
        "pagination": pagination_dict(page, page_size, total),
    }
    if extra:
        payload.update(extra)
    return bound_response(payload)


def item_response(item: dict) -> dict:
    """Standard get/detail tool response envelope."""
    return bound_response({"schema_version": CURRENT_SCHEMA_VERSION, "item": item})


def detail_response(payload: dict) -> dict:
    """Non-item detail response (e.g. runs.get, runs.diff)."""
    payload.setdefault("schema_version", CURRENT_SCHEMA_VERSION)
    return bound_response(payload)
