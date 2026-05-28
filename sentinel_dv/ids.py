"""
Deterministic ID generation for Sentinel DV.

This module implements the ID generation strategy documented in docs/ids.md.
All IDs are SHA-256 based with canonical serialization for reproducibility.
"""

import hashlib
import json
import re
from typing import Any
from urllib.parse import urlparse


def normalize_string(s: str, case_sensitive: bool = True) -> str:
    """
    Normalize a string for ID generation.

    Args:
        s: String to normalize
        case_sensitive: If False, convert to lowercase

    Returns:
        Normalized string
    """
    # Trim whitespace
    s = s.strip()

    # Normalize line endings
    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # Replace platform-dependent path separators
    s = s.replace("\\", "/")

    # Lowercase if not case-sensitive
    if not case_sensitive:
        s = s.lower()

    return s


def strip_volatile(s: str) -> str:
    """
    Remove volatile substrings that vary between runs.

    Args:
        s: String potentially containing volatile data

    Returns:
        String with volatile data replaced with placeholders
    """
    # Replace absolute paths (heuristic: starts with / or C:\)
    s = re.sub(r"(?:^|(?<=\s))(?:[A-Z]:|)/[\w/.-]+", "<ROOT>", s)

    # Replace hostnames (heuristic: hostname.domain pattern)
    s = re.sub(r"\b[\w-]+\.[\w.-]+\.(?:com|org|net|edu|io|local)\b", "<HOST>", s)

    # Replace ISO timestamps
    s = re.sub(
        r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", "<TS>", s
    )

    # Replace temporary directory patterns
    s = re.sub(r"/tmp/[\w-]+", "<TMP>", s)
    s = re.sub(r"\\Temp\\[\w-]+", "<TMP>", s)

    return s


def canonical_json(obj: dict[str, Any]) -> str:
    """
    Serialize object to canonical JSON for hashing.

    Args:
        obj: Dictionary to serialize

    Returns:
        Canonical JSON string (sorted keys, no whitespace, UTF-8)
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str) -> str:
    """
    Compute SHA-256 hash of string.

    Args:
        data: String to hash

    Returns:
        Lowercase hex digest
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def short_id(prefix: str, full_hash: str, length: int = 12) -> str:
    """
    Create short ID from full hash.

    Args:
        prefix: ID prefix (e.g., "r", "t", "f", "s")
        full_hash: Full SHA-256 hex hash
        length: Number of hex chars to use (default: 12)

    Returns:
        Short ID like "r_ab12cd34ef56"
    """
    return f"{prefix}_{full_hash[:length]}"


def normalize_url(url: str) -> str:
    """
    Normalize URL for consistent hashing.

    Args:
        url: URL string

    Returns:
        Normalized URL (scheme + netloc + path, no query/fragment)
    """
    parsed = urlparse(url)
    # Use only stable parts: scheme, netloc, path
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


# ============================================================================
# run_id generation
# ============================================================================


def generate_run_id(
    suite: str,
    ci_system: str | None = None,
    ci_build_id: str | None = None,
    ci_job_url: str | None = None,
    artifact_manifest: list[tuple[str, str]] | None = None,
) -> tuple[str, str]:
    """
    Generate deterministic run_id.

    Preferred: Use CI metadata if available
    Fallback: Use artifact manifest hash

    Args:
        suite: Test suite name
        ci_system: CI system name (github, jenkins, gitlab, etc.)
        ci_build_id: CI build ID
        ci_job_url: CI job URL
        artifact_manifest: List of (relative_path, file_sha256) tuples

    Returns:
        Tuple of (run_id, run_id_full)

    Raises:
        ValueError: If neither CI metadata nor artifact manifest provided
    """
    suite_norm = normalize_string(suite, case_sensitive=False)

    # Preferred: CI-backed run_id
    if ci_system and ci_build_id:
        ci_system_norm = normalize_string(ci_system, case_sensitive=False)
        ci_build_id_norm = normalize_string(ci_build_id)

        inputs = {
            "suite": suite_norm,
            "ci_system": ci_system_norm,
            "ci_build_id": ci_build_id_norm,
        }

        if ci_job_url:
            inputs["ci_job_url"] = normalize_url(ci_job_url)

        run_id_full = sha256_hex(canonical_json(inputs))
        return short_id("r", run_id_full), run_id_full

    # Fallback: artifact-backed run_id
    if artifact_manifest:
        # Sort manifest for determinism
        sorted_manifest = sorted(artifact_manifest)

        # Create manifest hash
        manifest_str = "\n".join(f"{path}:{hash}" for path, hash in sorted_manifest)
        artifact_manifest_hash = sha256_hex(manifest_str)

        inputs = {
            "suite": suite_norm,
            "artifact_manifest": artifact_manifest_hash,
        }

        run_id_full = sha256_hex(canonical_json(inputs))
        return short_id("r", run_id_full), run_id_full

    raise ValueError("Either CI metadata or artifact manifest required for run_id")


# ============================================================================
# test_id generation
# ============================================================================


def generate_test_id(
    run_id_full: str,
    framework: str,
    test_name: str,
    seed: int | None = None,
    simulator_vendor: str | None = None,
    simulator_version: str | None = None,
    dut_top: str | None = None,
    test_guid: str | None = None,
) -> tuple[str, str]:
    """
    Generate deterministic test_id.

    Args:
        run_id_full: Full SHA-256 hash of run_id
        framework: Framework name (uvm, cocotb, sv_unit, unknown)
        test_name: Test name
        seed: Random seed (if applicable)
        simulator_vendor: Simulator vendor
        simulator_version: Simulator version
        dut_top: Top-level DUT module
        test_guid: Explicit test GUID (if available)

    Returns:
        Tuple of (test_id, test_id_full)
    """
    framework_norm = normalize_string(framework, case_sensitive=False)
    test_name_norm = normalize_string(test_name)

    inputs: dict[str, Any] = {
        "run_id_full": run_id_full,
        "framework": framework_norm,
        "test_name": test_name_norm,
    }

    # Include optional fields if present
    if test_guid:
        inputs["test_guid"] = normalize_string(test_guid)

    if seed is not None:
        inputs["seed"] = seed

    if simulator_vendor:
        inputs["simulator_vendor"] = normalize_string(simulator_vendor, case_sensitive=False)

    if simulator_version:
        inputs["simulator_version"] = normalize_string(simulator_version, case_sensitive=False)

    if dut_top:
        inputs["dut_top"] = normalize_string(dut_top)

    test_id_full = sha256_hex(canonical_json(inputs))
    return short_id("t", test_id_full), test_id_full


# ============================================================================
# assertion_id generation
# ============================================================================


def generate_assertion_id(
    name: str,
    scope: str,
    file: str,
    line: int,
    language: str = "sva",
) -> tuple[str, str]:
    """Generate deterministic assertion_id for a definition."""
    inputs: dict[str, Any] = {
        "name": normalize_string(name),
        "scope": normalize_string(scope),
        "file": normalize_string(file),
        "line": line,
        "language": normalize_string(language, case_sensitive=False),
    }
    assertion_id_full = sha256_hex(canonical_json(inputs))
    return short_id("a", assertion_id_full), assertion_id_full


def generate_unknown_assertion_id(test_id_full: str, failure_message: str) -> tuple[str, str]:
    """Synthetic assertion for uncorrelated failures (deterministic)."""
    inputs = {
        "unknown": True,
        "test_id_full": test_id_full,
        "message_norm": strip_volatile(normalize_string(failure_message))[:200],
    }
    assertion_id_full = sha256_hex(canonical_json(inputs))
    return short_id("a", assertion_id_full), assertion_id_full


# ============================================================================
# failure_id generation
# ============================================================================


def generate_failure_id(
    test_id_full: str,
    severity: str,
    category: str,
    summary: str,
    component: str | None = None,
    phase: str | None = None,
    time_ns: int | None = None,
    evidence_paths: list[tuple[str, int, int]] | None = None,
) -> tuple[str, str]:
    """
    Generate deterministic failure_id.

    Args:
        test_id_full: Full SHA-256 hash of test_id
        severity: Severity level (info, warning, error, fatal)
        category: Failure category
        summary: Failure summary (will be normalized)
        component: Component name (optional)
        phase: Test phase (optional)
        time_ns: Simulation time in nanoseconds (optional)
        evidence_paths: List of (path, start_line, end_line) tuples

    Returns:
        Tuple of (failure_id, failure_id_full)
    """
    severity_norm = normalize_string(severity, case_sensitive=False)
    category_norm = normalize_string(category, case_sensitive=False)
    summary_norm = strip_volatile(normalize_string(summary))

    inputs: dict[str, Any] = {
        "test_id_full": test_id_full,
        "severity": severity_norm,
        "category": category_norm,
        "summary_norm": summary_norm,
    }

    if component:
        inputs["component_norm"] = normalize_string(component)

    if phase:
        inputs["phase_norm"] = normalize_string(phase, case_sensitive=False)

    # Time bucketing for stability (1 µs buckets)
    if time_ns is not None:
        inputs["time_bucket"] = str(time_ns // 1000)

    # Evidence fingerprint for disambiguation
    if evidence_paths:
        evidence_strs = sorted(
            [f"{path}:{start_line}:{end_line}" for path, start_line, end_line in evidence_paths]
        )
        evidence_fingerprint = sha256_hex("\n".join(evidence_strs))
        inputs["evidence_fingerprint"] = evidence_fingerprint

    failure_id_full = sha256_hex(canonical_json(inputs))
    return short_id("f", failure_id_full), failure_id_full


# ============================================================================
# signature_id generation (for regression clustering)
# ============================================================================


def signature_normalize_summary(summary: str) -> str:
    """
    Apply stronger normalization for failure signatures.

    This strips instance-specific details to cluster similar failures.

    Args:
        summary: Failure summary

    Returns:
        Signature-normalized summary
    """
    s = normalize_string(summary)

    # Replace hex literals
    s = re.sub(r"0x[0-9a-fA-F]+", "<HEX>", s, flags=re.IGNORECASE)

    # Replace decimal numbers
    s = re.sub(r"\b\d+\b", "<NUM>", s)

    # Replace time units
    s = re.sub(r"<NUM>\s*(?:ns|us|ms|ps|fs)", "<TIME>", s, flags=re.IGNORECASE)

    # Replace file paths
    s = re.sub(r"[\w/.-]+\.(?:sv|v|svh|vh|py|cpp|c|h)", "<PATH>", s)

    # Replace instance paths (optional, configurable)
    # Pattern: tb.top.env.agent[3].drv
    s = re.sub(r"\b\w+(?:\.\w+|\[\d+\])+", "<INST>", s)

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    return s


def generate_signature_id(
    category: str,
    summary: str,
    protocol: str | None = None,
    component_role: str | None = None,
) -> tuple[str, str]:
    """
    Generate deterministic signature_id for failure clustering.

    Args:
        category: Failure category
        summary: Failure summary (will be signature-normalized)
        protocol: Protocol tag (optional)
        component_role: Component role tag (optional)

    Returns:
        Tuple of (signature_id, signature_id_full)
    """
    category_norm = normalize_string(category, case_sensitive=False)
    summary_sig = signature_normalize_summary(summary)

    inputs: dict[str, Any] = {
        "category": category_norm,
        "summary_signature": summary_sig,
    }

    if protocol:
        inputs["protocol"] = normalize_string(protocol, case_sensitive=False)

    if component_role:
        inputs["component_role"] = normalize_string(component_role, case_sensitive=False)

    signature_id_full = sha256_hex(canonical_json(inputs))
    return short_id("s", signature_id_full), signature_id_full


# ============================================================================
# Collision handling
# ============================================================================


def extend_short_id(prefix: str, full_hash: str, existing_ids: set[str]) -> str:
    """
    Extend short ID length to resolve collisions.

    Args:
        prefix: ID prefix (e.g., "r", "t", "f", "s")
        full_hash: Full SHA-256 hex hash
        existing_ids: Set of existing IDs to check against

    Returns:
        Non-colliding short ID (may be longer than 12 chars)
    """
    for length in range(12, 65, 4):  # Try 12, 16, 20, ... 64
        candidate = short_id(prefix, full_hash, length)
        if candidate not in existing_ids:
            return candidate

    # If we get here, use full hash (extremely unlikely)
    return f"{prefix}_{full_hash}"
