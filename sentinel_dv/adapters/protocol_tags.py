"""Deterministic protocol tagging from assertion/coverage text."""

from __future__ import annotations

import re

# Ordered for stable first-match preference in detect_protocols
_PROTOCOL_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("axi4", ("axi", "axvalid", "awvalid", "bvalid", "wvalid", "arvalid")),
    ("ahb", ("ahb", "hready", "htrans")),
    ("apb", ("apb", "psel", "penable", "pready", "pslverr")),
    ("pcie", ("pcie", "tlp", "dllp")),
    ("usb", ("usb", "utmi", "ulpi")),
    ("spi", ("spi", "mosi", "miso", "sclk")),
    ("i2c", ("i2c", "sda", "scl")),
    ("jtag", ("jtag", "tdi", "tdo", "tms", "tck")),
    ("gpio", ("gpio",)),
)


def detect_protocols(*texts: str) -> list[str]:
    """Return sorted unique protocol tags found in any of the texts."""
    blob = " ".join(t for t in texts if t).lower()
    found: list[str] = []
    for tag, keywords in _PROTOCOL_RULES:
        if any(kw in blob for kw in keywords):
            found.append(tag)
    return sorted(set(found))


def primary_protocol(tags: list[str]) -> str | None:
    """Pick canonical intent.protocol value (first in stable order)."""
    if not tags:
        return None
    order = [p for p, _ in _PROTOCOL_RULES]
    for proto in order:
        if proto in tags:
            return proto
    return tags[0]


def normalize_scope(scope: str) -> str:
    """Normalize hierarchy scope for stable IDs."""
    s = scope.strip().replace("\\", "/")
    s = re.sub(r"^uvm_test_top\.", "", s, flags=re.IGNORECASE)
    return s or "top"


def normalize_assertion_file(path: str) -> str:
    """Store relative-style paths only (basename if absolute)."""
    p = path.strip().replace("\\", "/")
    if p.startswith("/") or re.match(r"^[A-Za-z]:/", p):
        return p.rsplit("/", 1)[-1]
    return p
