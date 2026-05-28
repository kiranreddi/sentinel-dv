"""Query layer for the DuckDB index (delegates from IndexStore)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel_dv.indexing.store import IndexStore


def query_assertions(
    store: IndexStore,
    *,
    scope: str | None = None,
    name_pattern: str | None = None,
    protocol: str | None = None,
    tag: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """List assertion definitions with filters."""
    return store.query_assertions(
        scope=scope,
        name_pattern=name_pattern,
        protocol=protocol,
        tag=tag,
        page=page,
        page_size=page_size,
    )
