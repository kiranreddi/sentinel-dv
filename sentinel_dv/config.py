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
    max_command_length: int = Field(
        default=4096,
        ge=256,
        le=32768,
        description="Maximum generated shell command length in characters",
    )
    max_coverage_gaps: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum coverage gap entries returned by coverage.gaps",
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
    live_sim: bool = Field(default=False, description="Enable live simulation status adapter")
    live_sim_max_age_seconds: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Maximum age of live_status.json in seconds before reporting as stale",
    )


class SimulatorTemplate(BaseModel):
    """Command template for a specific simulator."""

    simulator: str = Field(..., description="Simulator name (vcs|questa|xcelium|verilator)")
    template: str = Field(
        ...,
        description=(
            "Shell command template. Available placeholders: "
            "{suite}, {seed}, {test_filter}, {extra_args}, {artifact_root}"
        ),
    )
    default_args: str = Field(default="", description="Default extra arguments")
    replay_template: str | None = Field(
        None,
        description=(
            "Template for single-test replay. Placeholders: "
            "{test_name}, {seed}, {dut_top}, {suite}, {extra_args}, {artifact_root}. "
            "Falls back to template with TESTFILTER={test_name} SEED={seed} if not set."
        ),
    )


class SubmitConfig(BaseModel):
    """Regression job submission configuration."""

    enabled: bool = Field(default=False, description="Enable runs.submit and tests.replay tools")
    default_simulator: str = Field(default="vcs", description="Default simulator name")
    templates: list[SimulatorTemplate] = Field(
        default_factory=list,
        description="Per-simulator command templates",
    )
    lsf_queue: str | None = Field(
        None, description="LSF queue name (wraps generated command in bsub)"
    )
    slurm_partition: str | None = Field(None, description="SLURM partition name (wraps in sbatch)")


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
    submit: SubmitConfig = Field(
        default_factory=SubmitConfig,  # type: ignore[arg-type]
        description="Regression job submission and replay command generation",
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

    raise RuntimeError(
        "No configuration found. Pass --config, set SENTINEL_DV_CONFIG, "
        "or place config.yaml in the working directory. "
        "Sentinel DV does not silently default to demo/ in production."
    )


def resolve_config_with_demo_fallback(
    config_path: str | Path | None = None,
    demo_root: Path | None = None,
) -> SentinelDVConfig:
    """Resolve config, falling back to demo data with a loud warning.

    This variant is used by tests and the demo CLI. Production code should use
    resolve_config() which raises instead of falling back silently.
    """
    import warnings

    try:
        return resolve_config(config_path)
    except RuntimeError:
        pass

    if demo_root is None:
        demo_root = Path(__file__).parent.parent / "demo"

    if demo_root.is_dir():
        warnings.warn(
            f"No config.yaml found. Falling back to demo data at {demo_root}. "
            "This is for development only. Set SENTINEL_DV_CONFIG or pass --config "
            "for production use.",
            UserWarning,
            stacklevel=2,
        )
        return SentinelDVConfig(artifact_roots=[str(demo_root)])

    raise RuntimeError(
        "No configuration found and demo/ directory does not exist. "
        "Pass --config or set SENTINEL_DV_CONFIG."
    )


def set_config(config: SentinelDVConfig) -> None:
    """Set global configuration instance.

    Args:
        config: Configuration to set.
    """
    global _config
    _config = config
