"""Automatic redaction for Sentinel DV.

Removes sensitive information from logs and messages before exposure.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentinel_dv.config import RedactionConfig


class Redactor:
    """Automatic PII and credential redaction."""

    # Default redaction patterns
    DEFAULT_PATTERNS = [
        # AWS keys
        (r"AKIA[0-9A-Z]{16}", "<AWS_KEY>"),
        # GitHub tokens
        (r"ghp_[a-zA-Z0-9]{36}", "<GITHUB_TOKEN>"),
        (r"gho_[a-zA-Z0-9]{36}", "<GITHUB_TOKEN>"),
        (r"ghu_[a-zA-Z0-9]{36}", "<GITHUB_TOKEN>"),
        (r"ghs_[a-zA-Z0-9]{36}", "<GITHUB_TOKEN>"),
        (r"ghr_[a-zA-Z0-9]{36}", "<GITHUB_TOKEN>"),
        # GitLab tokens
        (r"glpat-[a-zA-Z0-9\-]{20,}", "<GITLAB_TOKEN>"),
        # OAuth Bearer tokens
        (r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer <TOKEN>"),
        # OpenAI API keys
        (r"sk-[a-zA-Z0-9]{48}", "<OPENAI_KEY>"),
        # Generic API keys
        (r"api[_-]?key['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-_]{16,})", "api_key=<REDACTED>"),
        # Private keys
        (r"-----BEGIN\s+PRIVATE\s+KEY-----", "<PRIVATE_KEY>"),
        (r"-----BEGIN\s+RSA\s+PRIVATE\s+KEY-----", "<RSA_PRIVATE_KEY>"),
        # Password assignments
        (r"password\s*[:=]\s*['\"]?([^\s'\"]+)", "password=<REDACTED>"),
        (r"passwd\s*[:=]\s*['\"]?([^\s'\"]+)", "passwd=<REDACTED>"),
    ]

    # Email pattern
    EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    # IP address pattern (IPv4)
    IPV4_PATTERN = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"

    # Absolute path pattern (Unix and Windows)
    UNIX_PATH_PATTERN = r"/(?:home|root|usr|opt|var)/[^\s]*"
    WINDOWS_PATH_PATTERN = r"[A-Z]:\\[^\s]*"

    def __init__(
        self,
        custom_patterns: list[tuple[str, str]] | None = None,
        redact_emails: bool = False,
        redact_ips: bool = False,
        redact_paths: bool = False,
    ):
        """Initialize redactor.

        Args:
            custom_patterns: Additional (pattern, replacement) tuples.
            redact_emails: Whether to redact email addresses.
            redact_ips: Whether to redact IP addresses.
            redact_paths: Whether to redact absolute file paths.
        """
        self.patterns = self.DEFAULT_PATTERNS.copy()

        if custom_patterns:
            self.patterns.extend(custom_patterns)

        if redact_emails:
            self.patterns.append((self.EMAIL_PATTERN, "<EMAIL>"))

        if redact_ips:
            self.patterns.append((self.IPV4_PATTERN, "<IP>"))

        if redact_paths:
            self.patterns.append((self.UNIX_PATH_PATTERN, "<PATH>"))
            self.patterns.append((self.WINDOWS_PATH_PATTERN, "<PATH>"))

        # Compile patterns
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.patterns
        ]

    @classmethod
    def from_config(cls, config: "RedactionConfig") -> "Redactor":
        """Build a redactor from Sentinel DV YAML settings."""
        if not config.enabled:
            return cls(redact_emails=False, redact_ips=False, redact_paths=False)
        custom: list[tuple[str, str]] = [(p, "<REDACTED>") for p in config.patterns]
        return cls(
            custom_patterns=custom or None,
            redact_emails=config.redact_emails,
            redact_ips=config.redact_ips,
            redact_paths=config.redact_paths,
        )

    def redact(self, text: str) -> str:
        """Redact sensitive information from text.

        Args:
            text: Input text to redact.

        Returns:
            Redacted text.
        """
        redacted = text

        # Apply all patterns in order
        for pattern, replacement in self.compiled_patterns:
            redacted = pattern.sub(replacement, redacted)

        return redacted

    def redact_lines(self, lines: list[str]) -> list[str]:
        """Redact each line in a list.

        Args:
            lines: List of text lines.

        Returns:
            List of redacted lines.
        """
        return [self.redact(line) for line in lines]


# Global default redactor instance
_default_redactor: Redactor | None = None


def get_default_redactor() -> Redactor:
    """Get or create default redactor instance.

    Returns:
        Default Redactor instance.
    """
    global _default_redactor
    if _default_redactor is None:
        _default_redactor = Redactor()
    return _default_redactor


def set_default_redactor(redactor: Redactor) -> None:
    """Set custom default redactor.

    Args:
        redactor: Redactor instance to use as default.
    """
    global _default_redactor
    _default_redactor = redactor


def redact(text: str) -> str:
    """Redact text using default redactor.

    Args:
        text: Text to redact.

    Returns:
        Redacted text.
    """
    return get_default_redactor().redact(text)
