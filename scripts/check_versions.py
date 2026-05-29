#!/usr/bin/env python3
"""Verify package and documentation versions match before tagging a release."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files that must reference the same release version (edit when adding surfaces).
PINNED_FILES: tuple[tuple[Path, str], ...] = (
    (ROOT / "pyproject.toml", r'^version = "{version}"'),
    (ROOT / "sentinel_dv" / "__init__.py", r'^__version__ = "{version}"'),
    (ROOT / "server.json", r'"version": "{version}"'),
    (ROOT / "README.md", r"Sentinel DV v{version}"),
    (ROOT / "docs" / "index.md", r"v{version}"),
    (ROOT / "docs" / "getting-started" / "installation.md", r"v{version}"),
    (ROOT / "mkdocs.yml", r"Sentinel DV v{version}"),
)


def read_package_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("Could not read version from pyproject.toml")
    return match.group(1)


def normalize_tag(tag: str | None) -> str | None:
    if not tag:
        return None
    return tag.removeprefix("v")


def check_pinned_files(version: str) -> list[str]:
    errors: list[str] = []
    for path, pattern_tpl in PINNED_FILES:
        if not path.is_file():
            errors.append(f"Missing expected file: {path}")
            continue
        pattern = pattern_tpl.format(version=version)
        content = path.read_text(encoding="utf-8")
        if not re.search(pattern, content, re.MULTILINE):
            errors.append(f"{path.relative_to(ROOT)}: expected pattern {pattern!r}")
    # server.json PyPI package version
    server = (ROOT / "server.json").read_text(encoding="utf-8")
    if f'"version": "{version}"' not in server:
        errors.append("server.json: packages[].version does not match")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tag",
        nargs="?",
        help="Git tag (e.g. v1.3.2). If set, must match pyproject.toml version.",
    )
    args = parser.parse_args(argv)

    package_version = read_package_version()
    tag_version = normalize_tag(args.tag)

    errors = check_pinned_files(package_version)

    if tag_version and tag_version != package_version:
        errors.append(
            f"Tag version {tag_version!r} != pyproject.toml version {package_version!r}"
        )

    if errors:
        print("Version check FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            f"\nBump all surfaces to {package_version!r} (see docs/release/RELEASING.md).",
            file=sys.stderr,
        )
        return 1

    print(f"Version check OK: {package_version}")
    if tag_version:
        print(f"  Tag {args.tag} matches package version.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
