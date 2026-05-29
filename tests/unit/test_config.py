"""Tests for configuration module."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from sentinel_dv.config import (
    AdaptersConfig,
    IndexConfig,
    RedactionConfig,
    SecurityLimits,
    SentinelDVConfig,
)


class TestSecurityLimits:
    """Tests for SecurityLimits model."""

    def test_default_limits(self):
        """SecurityLimits should have sensible defaults."""
        limits = SecurityLimits()
        assert limits.max_response_bytes == 2_097_152  # 2MB
        assert limits.max_page_size == 200
        assert limits.max_evidence_refs == 10

    def test_custom_limits(self):
        """SecurityLimits should accept custom values."""
        limits = SecurityLimits(
            max_response_bytes=1_048_576,
            max_page_size=100,
        )
        assert limits.max_response_bytes == 1_048_576
        assert limits.max_page_size == 100


class TestRedactionConfig:
    """Tests for RedactionConfig model."""

    def test_default_redaction(self):
        """RedactionConfig should default to enabled."""
        config = RedactionConfig()
        assert config.enabled is True
        assert config.redact_emails is True
        assert config.redact_paths is True

    def test_custom_patterns(self):
        """RedactionConfig should accept custom patterns."""
        config = RedactionConfig(patterns=["pattern1", "pattern2"])
        assert len(config.patterns) == 2


class TestIndexConfig:
    """Tests for IndexConfig model."""

    def test_default_index(self):
        """IndexConfig should default to duckdb."""
        config = IndexConfig()
        assert config.type == "duckdb"
        assert config.path == "./sentinel_dv.db"

    def test_invalid_type(self):
        """IndexConfig should reject invalid types."""
        with pytest.raises(ValidationError):
            IndexConfig(type="invalid")


class TestAdaptersConfig:
    """Tests for AdaptersConfig model."""

    def test_default_adapters(self):
        """AdaptersConfig should enable most adapters by default."""
        config = AdaptersConfig()
        assert config.uvm is True
        assert config.cocotb is True
        assert config.waveform_summary is False  # Experimental


class TestSentinelDVConfig:
    """Tests for main configuration."""

    def test_minimal_config(self):
        """Config should work with just artifact_roots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SentinelDVConfig(artifact_roots=[tmpdir])
            assert len(config.artifact_roots) == 1
            assert config.index.type == "duckdb"

    def test_artifact_root_validation(self):
        """Config should validate artifact roots exist."""
        with pytest.raises(ValidationError, match="does not exist"):
            SentinelDVConfig(artifact_roots=["/nonexistent/path"])

    def test_artifact_root_must_be_directory(self):
        """Config should reject files as artifact roots."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            with pytest.raises(ValidationError, match="not a directory"):
                SentinelDVConfig(artifact_roots=[tmpfile.name])

    def test_from_yaml(self):
        """Config should load from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = Path(tmpdir) / "artifacts"
            artifacts.mkdir()
            config_data = {
                "artifact_roots": ["artifacts"],
                "index": {"type": "duckdb", "path": "./test.db"},
                "security": {"max_page_size": 100},
            }

            config_file = Path(tmpdir) / "config.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config_data, f)

            config = SentinelDVConfig.from_yaml(str(config_file))
            assert config.artifact_roots == [str(artifacts.resolve())]
            assert config.index.path == str((Path(tmpdir) / "test.db").resolve())
            assert config.security.max_page_size == 100

    def test_to_yaml(self):
        """Config should save to YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SentinelDVConfig(artifact_roots=[tmpdir])

            config_file = Path(tmpdir) / "output.yaml"
            config.to_yaml(str(config_file))

            assert config_file.exists()

            # Verify round-trip
            loaded = SentinelDVConfig.from_yaml(str(config_file))
            assert loaded.artifact_roots == config.artifact_roots
