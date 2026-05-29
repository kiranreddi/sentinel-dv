"""Configuration management for Sentinel DV."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class SecurityLimits(BaseModel):
    """Security and response limits."""

    max_response_bytes: int = Field(
        default=2_097_152, ge=1024, description="Maximum response size in bytes (2MB default)"
    )
    max_page_size: int = Field(default=200, ge=1, le=1000, description="Maximum items per page")
    max_evidence_refs: int = Field(
        default=10, ge=1, le=100, description="Maximum evidence references per item"
    )
    max_excerpt_length: int = Field(
        default=1024, ge=256, le=8192, description="Maximum excerpt length in characters"
    )
    max_message_length: int = Field(
        default=4096, ge=512, le=16384, description="Maximum failure message length"
    )
    max_tags_per_event: int = Field(
        default=20, ge=1, le=100, description="Maximum tags per failure event"
    )
    max_coverage_metrics: int = Field(
        default=200, ge=1, le=1000, description="Maximum coverage metrics per summary"
    )
    max_bins_missed: int = Field(
        default=50, ge=1, le=200, description="Maximum missed bins listed per metric"
    )
    max_wave_signals: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum signals returned by wave.signals",
    )
    max_artifact_bytes: int = Field(
        default=52_428_800,
        ge=1_048_576,
        le=536_870_912,
        description="Maximum artifact file size read during index or VCD re-parse (50MB default)",
    )


class RedactionConfig(BaseModel):
    """Redaction configuration."""

    enabled: bool = Field(default=True, description="Enable automatic redaction")
    patterns: list[str] = Field(default_factory=list, description="Custom regex patterns to redact")
    redact_emails: bool = Field(default=True, description="Redact email addresses")
    redact_ips: bool = Field(default=False, description="Redact IP addresses")
    redact_paths: bool = Field(default=True, description="Redact absolute file paths")


class IndexConfig(BaseModel):
    """Index storage configuration."""

    type: str = Field(default="duckdb", pattern=r"^duckdb$")
    path: str = Field(default="./sentinel_dv.db", description="Index database path")


class AdaptersConfig(BaseModel):
    """Adapter enable/disable flags."""

    uvm: bool = Field(default=True, description="Enable UVM log adapter")
    cocotb: bool = Field(default=True, description="Enable cocotb adapter")
    assertions: bool = Field(default=True, description="Enable assertion adapter")
    coverage: bool = Field(default=True, description="Enable coverage adapter")
    waveform_summary: bool = Field(default=False, description="Enable waveform summary adapter")


class SentinelDVConfig(BaseModel):
    """Main Sentinel DV configuration."""

    artifact_roots: list[str] = Field(
        ..., min_length=1, description="List of artifact root directories (read-only)"
    )
    index: IndexConfig = Field(default_factory=IndexConfig, description="Index configuration")
    adapters: AdaptersConfig = Field(
        default_factory=AdaptersConfig, description="Adapter configuration"
    )
    security: SecurityLimits = Field(default_factory=SecurityLimits, description="Security limits")
    redaction: RedactionConfig = Field(
        default_factory=RedactionConfig, description="Redaction configuration"
    )

    @field_validator("artifact_roots")
    @classmethod
    def validate_artifact_roots(cls, v: list[str]) -> list[str]:
        """Validate artifact roots exist and are accessible."""
        validated = []
        for root in v:
            path = Path(root).resolve()
            if not path.exists():
                raise ValueError(f"Artifact root does not exist: {root}")
            if not path.is_dir():
                raise ValueError(f"Artifact root is not a directory: {root}")
            if not os.access(path, os.R_OK):
                raise ValueError(f"Artifact root is not readable: {root}")
            validated.append(str(path))
        return validated

    @classmethod
    def from_yaml(cls, path: str) -> "SentinelDVConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file.

        Returns:
            Loaded configuration.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config is invalid.
        """
        config_path = Path(path).resolve()
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(config_path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Configuration must be a YAML mapping: {path}")

        base_dir = config_path.parent
        roots = data.get("artifact_roots")
        if isinstance(roots, list):
            data["artifact_roots"] = [
                (
                    str((base_dir / root).resolve())
                    if not Path(str(root)).is_absolute()
                    else str(Path(str(root)).resolve())
                )
                for root in roots
            ]

        index = data.get("index")
        if isinstance(index, dict) and index.get("path"):
            index_path = Path(str(index["path"]))
            if not index_path.is_absolute():
                data["index"] = {**index, "path": str((base_dir / index_path).resolve())}

        return cls(**data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SentinelDVConfig":
        """Create configuration from dictionary.

        Args:
            data: Configuration dictionary.

        Returns:
            Configuration instance.
        """
        return cls(**data)

    def to_yaml(self, path: str) -> None:
        """Save configuration to YAML file.

        Args:
            path: Path to save configuration.
        """
        with open(path, "w") as f:
            yaml.safe_dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)


# Global configuration instance
_config: SentinelDVConfig | None = None


def get_config() -> SentinelDVConfig:
    """Get global configuration instance.

    Returns:
        Current configuration.

    Raises:
        RuntimeError: If configuration not initialized.
    """
    if _config is None:
        raise RuntimeError("Configuration not initialized. Call load_config() first.")
    return _config


def load_config(path: str | Path) -> SentinelDVConfig:
    """Load and set global configuration.

    Args:
        path: Path to configuration file.

    Returns:
        Loaded configuration.
    """
    global _config
    _config = SentinelDVConfig.from_yaml(str(path))
    return _config


def resolve_config(config_path: str | Path | None = None) -> SentinelDVConfig:
    """Resolve configuration from explicit path, env, or repository defaults."""
    if config_path is not None:
        return load_config(config_path)

    env_path = os.environ.get("SENTINEL_DV_CONFIG")
    if env_path:
        return load_config(env_path)

    for candidate in (Path("config.yaml"), Path("config.yml")):
        if candidate.is_file():
            return load_config(candidate)

    repo_root = Path(__file__).resolve().parent.parent
    demo_root = repo_root / "demo"
    if demo_root.is_dir():
        return SentinelDVConfig(
            artifact_roots=[str(demo_root)],
            index=IndexConfig(path=str(repo_root / "sentinel_dv.db")),
        )

    raise RuntimeError(
        "No configuration found. Set SENTINEL_DV_CONFIG or pass --config to the server."
    )


def set_config(config: SentinelDVConfig) -> None:
    """Set global configuration instance.

    Args:
        config: Configuration to set.
    """
    global _config
    _config = config
