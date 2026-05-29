"""Tests for utility functions."""

import pytest

from sentinel_dv.utils.bounded_text import (
    count_lines,
    extract_excerpt,
    normalize_whitespace,
    truncate_text,
)
from sentinel_dv.utils.hashing import hash_file_chunk, sha256_hex, stable_signature
from sentinel_dv.utils.time import (
    now_utc,
    ns_to_human,
    parse_rfc3339,
    parse_simulation_time,
    to_rfc3339,
)


class TestHashing:
    """Tests for hashing utilities."""

    def test_sha256_hex_string(self):
        """SHA-256 hash of string should be deterministic."""
        hash1 = sha256_hex("test")
        hash2 = sha256_hex("test")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 is 64 hex chars

    def test_sha256_hex_bytes(self):
        """SHA-256 hash of bytes should work."""
        hash1 = sha256_hex(b"test")
        hash2 = sha256_hex("test")
        assert hash1 == hash2

    def test_stable_signature(self):
        """Stable signature should be deterministic and sorted."""
        sig1 = stable_signature(["component1", "category", "summary"])
        sig2 = stable_signature(["summary", "category", "component1"])  # Different order
        assert sig1 == sig2  # Should be same due to sorting
        assert len(sig1) == 16  # Truncated to 16 chars

    def test_hash_file_chunk(self, tmp_path):
        log = tmp_path / "sim.log"
        log.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
        h = hash_file_chunk(str(log), 1, 2)
        assert len(h) == 64
        with pytest.raises(ValueError):
            hash_file_chunk(str(log), 0, 1)
        with pytest.raises(ValueError):
            hash_file_chunk(str(log), 1, 99)


class TestTimeUtils:
    """Tests for time utilities."""

    def test_now_utc(self):
        """now_utc should return timezone-aware datetime."""
        dt = now_utc()
        assert dt.tzinfo is not None

    def test_parse_rfc3339(self):
        """parse_rfc3339 should parse valid timestamps."""
        dt = parse_rfc3339("2026-01-25T14:23:05Z")
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 25

    def test_parse_rfc3339_invalid(self):
        """parse_rfc3339 should reject invalid timestamps."""
        with pytest.raises(ValueError):
            parse_rfc3339("invalid")

    def test_to_rfc3339(self):
        """to_rfc3339 should format datetime correctly."""
        dt = parse_rfc3339("2026-01-25T14:23:05Z")
        formatted = to_rfc3339(dt)
        assert "2026-01-25" in formatted
        assert formatted.endswith("Z")

    def test_ns_to_human(self):
        """ns_to_human should format nanoseconds correctly."""
        assert ns_to_human(0) == "0ns"
        assert ns_to_human(500) == "500ns"
        assert "us" in ns_to_human(1500)
        assert "ms" in ns_to_human(1_500_000)
        assert "s" in ns_to_human(1_500_000_000)

    def test_parse_simulation_time(self):
        """parse_simulation_time should parse various formats."""
        assert parse_simulation_time("1250ns") == 1250
        assert parse_simulation_time("1.25us") == 1250
        assert parse_simulation_time("3.5ms") == 3_500_000
        assert parse_simulation_time("2s") == 2_000_000_000

    def test_parse_simulation_time_invalid(self):
        """parse_simulation_time should return None for invalid input."""
        assert parse_simulation_time("invalid") is None


class TestBoundedText:
    """Tests for bounded text utilities."""

    def test_truncate_text_short(self):
        """truncate_text should not truncate short text."""
        text = "Short text"
        result = truncate_text(text, max_length=100)
        assert result == text

    def test_truncate_text_long(self):
        """truncate_text should truncate long text."""
        text = "A" * 100
        result = truncate_text(text, max_length=50, suffix="...")
        assert len(result) == 50
        assert result.endswith("...")

    def test_truncate_text_preserve_newlines(self):
        text = "line one\nline two\nline three\nline four"
        result = truncate_text(text, max_length=30, suffix="...", preserve_newlines=True)
        assert len(result) <= 30
        assert result.endswith("...")

    def test_extract_excerpt(self):
        """extract_excerpt should extract line ranges."""
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        excerpt = extract_excerpt(text, start_line=2, end_line=4, max_length=1000)
        assert "Line 2" in excerpt
        assert "Line 3" in excerpt
        assert "Line 4" in excerpt

    def test_extract_excerpt_default_lines(self):
        text = "\n".join(f"line {i}" for i in range(20))
        excerpt = extract_excerpt(text, max_length=500)
        assert "line 0" in excerpt
        assert "line 9" in excerpt

    def test_normalize_whitespace(self):
        """normalize_whitespace should normalize spaces."""
        text = "  Multiple   spaces  \n\n  and   newlines  "
        result = normalize_whitespace(text)
        assert "  " not in result  # No double spaces in lines
        assert result.strip() == result  # No leading/trailing

    def test_normalize_whitespace_single_line(self):
        """normalize_whitespace should convert to single line."""
        text = "Line 1\nLine 2\nLine 3"
        result = normalize_whitespace(text, single_line=True)
        assert "\n" not in result
        assert result == "Line 1 Line 2 Line 3"

    def test_count_lines(self):
        """count_lines should count lines correctly."""
        assert count_lines("") == 0
        assert count_lines("Single line") == 1
        assert count_lines("Line 1\nLine 2\nLine 3") == 3
