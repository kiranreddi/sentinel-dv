"""Structured MCP tool errors."""

from __future__ import annotations

from typing import Any, Literal

ErrorCode = Literal[
    "NOT_FOUND",
    "TOPOLOGY_NOT_INDEXED",
    "INVALID_ARGUMENT",
    "PERMISSION_DENIED",
    "INTERNAL",
    "INDEX_NOT_READY",
    "LIMIT_EXCEEDED",
]


class ToolError(Exception):
    """Raised by tool implementations; mapped to structured JSON by the server."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        from sentinel_dv.schemas.versioning import CURRENT_SCHEMA_VERSION

        payload: dict[str, Any] = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "error": {
                "code": self.code,
                "message": self.message,
            },
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload
