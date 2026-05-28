"""Redactor wiring from configuration."""

from sentinel_dv.config import RedactionConfig
from sentinel_dv.normalization.redaction import Redactor


def test_redactor_from_config_redacts_email() -> None:
    cfg = RedactionConfig(enabled=True, redact_emails=True, redact_paths=False)
    redactor = Redactor.from_config(cfg)
    assert "<EMAIL>" in redactor.redact("contact user@example.com now")


def test_redactor_disabled_skips_optional_patterns() -> None:
    cfg = RedactionConfig(enabled=False)
    redactor = Redactor.from_config(cfg)
    assert "user@example.com" in redactor.redact("user@example.com")
