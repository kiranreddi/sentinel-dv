"""Validate canonical agent skills and cross-agent packaging."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILL_NAMES = {
    "sentinel-dv-regression-triage",
    "sentinel-dv-failure-debugging",
    "sentinel-dv-coverage-closure",
}


def test_agent_skill_mirrors_match() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/sync_agent_skills.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_skills_have_portable_frontmatter_and_metadata() -> None:
    for name in SKILL_NAMES:
        skill_dir = ROOT / "skills" / name
        content = (skill_dir / "SKILL.md").read_text()
        _, frontmatter, body = content.split("---", 2)
        metadata = yaml.safe_load(frontmatter)
        assert metadata["name"] == name
        assert isinstance(metadata["description"], str)
        assert metadata["description"]
        assert body.strip()
        assert (skill_dir / "agents" / "openai.yaml").is_file()


def test_plugin_manifests_reference_canonical_skills() -> None:
    codex = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())
    claude = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert codex["name"] == claude["name"] == "sentinel-dv"
    assert codex["skills"] == claude["skills"] == "./skills/"
    assert codex["version"] == claude["version"]


def test_skills_do_not_reintroduce_removed_contracts() -> None:
    combined = "\n".join((ROOT / "skills" / name / "SKILL.md").read_text() for name in SKILL_NAMES)
    forbidden = (
        "`coverage.trend` with a time window",
        "`runs.cross_sim` with `suite`",
        "`tests.cluster` with `suite`",
        "artifact references from `tests.get`",
    )
    for phrase in forbidden:
        assert phrase not in combined
