"""Live simulation status adapter.

Reads ``live_status.json`` files written by simulator harnesses alongside
build artifacts. The sentinel-dv server *never* executes the simulator — it
only reads the pre-written status file.

Expected JSON format (all fields optional except ``suite`` and ``phase``):

.. code-block:: json

    {
        "suite": "axi4_regression",
        "phase": "running",
        "tests_total": 120,
        "tests_done": 47,
        "tests_passing": 44,
        "tests_failing": 3,
        "current_test": "axi4_random_burst_test",
        "elapsed_seconds": 183.5,
        "estimated_remaining_seconds": 240.0,
        "last_updated": "2026-01-25T14:23:05Z"
    }
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sentinel_dv.schemas.live_sim import LiveSimProgress

logger = logging.getLogger(__name__)

_STATUS_FILENAMES = ("live_status.json", "sim_status.json", ".live_status.json")


class LiveSimAdapter:
    """Reads live simulation progress from a ``live_status.json`` file.

    The adapter searches for the status file under the provided artifact root
    directories, optionally filtered by suite name.

    Args:
        artifact_roots: List of artifact root directory paths to search.
        max_age_seconds: Maximum age of the status file in seconds before
            marking the result as ``stale``. Default is 300 seconds.
    """

    def __init__(
        self,
        artifact_roots: list[str | Path],
        max_age_seconds: int = 300,
    ) -> None:
        self._roots = [Path(r) for r in artifact_roots]
        self._max_age_seconds = max_age_seconds

    def find_status_file(self, suite: str | None = None) -> Path | None:
        """Locate the most recently modified live status file.

        Searches artifact roots for known status filenames. If *suite* is
        given, only files under directories containing the suite name are
        considered.

        Args:
            suite: Optional suite name to narrow the search.

        Returns:
            Path to the most recently modified status file, or ``None``.
        """
        candidates: list[tuple[float, Path]] = []

        for root in self._roots:
            if not root.is_dir():
                continue
            for filename in _STATUS_FILENAMES:
                for path in root.rglob(filename):
                    if suite and suite not in str(path):
                        continue
                    try:
                        mtime = path.stat().st_mtime
                        candidates.append((mtime, path))
                    except OSError:
                        continue

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def read(self, suite: str | None = None, status_path: Path | None = None) -> LiveSimProgress | None:
        """Read and parse live simulation progress.

        Args:
            suite: Suite name to search for. Also used as ``suite`` field in
                the returned object if the file doesn't include it.
            status_path: Explicit path to the status file. If given, the
                artifact root search is skipped.

        Returns:
            A :class:`~sentinel_dv.schemas.live_sim.LiveSimProgress` instance,
            or ``None`` if no status file could be found.
        """
        if status_path is None:
            status_path = self.find_status_file(suite=suite)

        if status_path is None:
            return None

        try:
            text = status_path.read_text(encoding="utf-8")
            raw: dict[str, Any] = json.loads(text)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("LiveSimAdapter: failed to read %s: %s", status_path, exc)
            return None

        # Determine staleness
        try:
            mtime = status_path.stat().st_mtime
            age_seconds = datetime.now(timezone.utc).timestamp() - mtime
            is_stale = age_seconds > self._max_age_seconds
        except OSError:
            is_stale = False

        # Fill in optional fields
        if suite and not raw.get("suite"):
            raw["suite"] = suite
        raw.setdefault("suite", "unknown")
        raw.setdefault("phase", "unknown")
        raw["stale"] = is_stale

        # Compute percent_done if possible
        total = raw.get("tests_total", 0) or 0
        done = raw.get("tests_done", 0) or 0
        if total > 0 and "percent_done" not in raw:
            raw["percent_done"] = round(100.0 * done / total, 2)

        try:
            return LiveSimProgress.model_validate(raw)
        except Exception as exc:
            logger.warning("LiveSimAdapter: schema validation failed for %s: %s", status_path, exc)
            return None

    def find_suite_status_path(self, suite: str, artifact_root: str | Path) -> Path:
        """Return the canonical path for a suite's live status file.

        This is the *write* target path that simulator harnesses should use.
        The sentinel-dv server never writes to this path.

        Args:
            suite: Suite name.
            artifact_root: Root directory for the suite artifacts.

        Returns:
            Expected path: ``<artifact_root>/<suite>/live_status.json``
        """
        return Path(artifact_root) / suite / "live_status.json"
