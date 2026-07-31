#!/usr/bin/env python3
"""Synchronize canonical Sentinel DV skills into agent discovery directories."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills"
TARGETS = (
    ROOT / ".agents" / "skills",
    ROOT / ".claude" / "skills",
    ROOT / ".github" / "skills",
)


def skill_directories(root: Path) -> dict[str, Path]:
    return {
        path.name: path
        for path in sorted(root.iterdir())
        if path.is_dir() and (path / "SKILL.md").is_file()
    }


def directories_match(source: Path, target: Path) -> bool:
    comparison = filecmp.dircmp(source, target)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    if comparison.diff_files:
        return False
    return all(directories_match(source / name, target / name) for name in comparison.common_dirs)


def check() -> int:
    expected = skill_directories(SOURCE)
    failures: list[str] = []
    for target_root in TARGETS:
        if not target_root.is_dir():
            failures.append(f"missing directory: {target_root.relative_to(ROOT)}")
            continue
        actual = skill_directories(target_root)
        if actual.keys() != expected.keys():
            failures.append(f"skill set differs: {target_root.relative_to(ROOT)}")
            continue
        for name, source_dir in expected.items():
            if not directories_match(source_dir, actual[name]):
                failures.append(f"skill differs: {(target_root / name).relative_to(ROOT)}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        print("Run: python scripts/sync_agent_skills.py", file=sys.stderr)
        return 1
    print("Agent skill mirrors match canonical skills/.")
    return 0


def sync() -> None:
    expected = skill_directories(SOURCE)
    for target_root in TARGETS:
        target_root.mkdir(parents=True, exist_ok=True)
        for path in target_root.iterdir():
            if path.is_dir() and path.name not in expected:
                shutil.rmtree(path)
        for name, source_dir in expected.items():
            target_dir = target_root / name
            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.copytree(source_dir, target_dir)
    print("Synchronized skills for Codex, Claude Code, and GitHub Copilot.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when an agent discovery directory differs from skills/.",
    )
    args = parser.parse_args()
    if args.check:
        return check()
    sync()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
