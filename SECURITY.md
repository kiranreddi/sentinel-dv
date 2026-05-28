# Security Policy

## Reporting a Vulnerability

The Sentinel DV team takes security seriously. If you discover a security vulnerability, please follow responsible disclosure practices.

### Please Do Not

- **Do not** open a public GitHub issue
- **Do not** discuss the vulnerability publicly until a fix is released

### Please Do

1. **Email security concerns** to: [security@sentinel-dv.org] (or create a private security advisory)
2. **Include details:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment** within 48 hours
- **Status update** within 5 business days
- **Fix timeline** communicated clearly
- **Credit** in release notes (if desired)

## Security Model

Sentinel DV is designed with **security-first principles** for safe agent usage:

### Threat Model

**In scope:**
- Path traversal attacks via artifact roots
- Credential/secret leakage in logs or evidence
- Denial of service via unbounded queries
- Injection attacks via malformed artifacts
- Privilege escalation via config manipulation

**Out of scope (by design):**
- Write operations (server is read-only)
- Simulator control (no job triggers)
- Network access beyond configured artifact roots
- Arbitrary code execution (no eval/exec)

### Security Features

#### 1. Read-Only by Design

- **No write operations** - All tools are strictly read-only
- **No simulator control** - Cannot trigger simulations or modify configs
- **No artifact modification** - Source files are never altered

**Enforcement:**
- File operations use read-only modes
- Configuration validates no write permissions
- Tool schemas prohibit mutation operations

#### 2. Path Sandboxing

**Problem:** Malicious or misconfigured artifacts could reference files outside intended directories.

**Mitigation:**
```python
# Only files under configured artifact_roots are accessible
artifact_roots:
  - /verified/regression/path
  - /verified/uvm/logs/path

# All paths normalized and validated
# Paths with .. after normalization are rejected
# Absolute paths outside roots are rejected
# Symlinks are resolved and checked
```

**Tests:**
- `tests/security/test_path_traversal.py`
- Validates rejection of `../`, absolute paths, symlinks

#### 3. Automatic Redaction

**Problem:** Logs and reports may contain sensitive information.

**Mitigation:**

Default redaction patterns:
```yaml
redaction:
  patterns:
    - AKIA[0-9A-Z]{16}              # AWS Access Keys
    - ghp_[a-zA-Z0-9]{36}           # GitHub Personal Access Tokens
    - glpat-[a-zA-Z0-9\-]{20}       # GitLab Personal Access Tokens
    - Bearer\s+[A-Za-z0-9\-._~+/]+  # OAuth Bearer Tokens
    - sk-[a-zA-Z0-9]{48}            # OpenAI API Keys
    - -----BEGIN\s+PRIVATE\s+KEY----- # Private Keys
    - password\s*[:=]\s*\S+         # Password assignments
    
  redact_emails: true                # user@domain.com → <EMAIL>
  redact_ips: true                   # 192.168.1.1 → <IP>
  redact_paths: true                 # /home/user → <PATH>
```

All `EvidenceRef.extract` and `FailureEvent.message` fields are automatically redacted.

**Tests:**
- `tests/security/test_redaction.py`
- Validates all pattern types
- Ensures no false negatives

#### 4. Response Size Limits

**Problem:** Unbounded responses can cause denial of service or prompt injection.

**Mitigation:**
```yaml
security:
  max_response_bytes: 2097152        # 2MB hard limit
  max_page_size: 200                 # Max items per page
  max_evidence_refs: 10              # Max evidence per item
  max_excerpt_length: 1024           # Max chars per excerpt
  max_message_length: 4096           # Max failure message length
  max_tags_per_event: 20             # Max tags per failure
  max_coverage_metrics: 200          # Max metrics per summary
  max_bins_missed: 50                # Max missed bins listed
```

Server returns `LIMIT_EXCEEDED` error when limits are hit, with guidance to narrow filters.

**Tests:**
- `tests/security/test_limits.py`
- Validates enforcement of all limits

#### 5. Configuration Validation

**Problem:** Invalid configuration could lead to unsafe behavior.

**Mitigation:**
- **Schema validation** using Pydantic models
- **Path existence checks** for artifact roots
- **Permission validation** (read-only access)
- **Limit range validation** (prevent zero or negative limits)
- **Fail-fast startup** if config is invalid

**Tests:**
- `tests/unit/test_config.py`
- Validates rejection of invalid configs

#### 6. Input Validation

All tool inputs are validated:
- **Enum fields** checked against allowed values
- **String patterns** validated (IDs, paths, timestamps)
- **Numeric ranges** checked (page numbers, limits)
- **Injection prevention** - no eval/exec on user inputs

**Tests:**
- `tests/unit/tools/test_validation.py`
- Fuzzing tests for malformed inputs

### Secure Deployment Best Practices

#### File System Permissions

```bash
# Artifact roots should be read-only
chmod -R 444 /path/to/artifacts
chown -R sentinel-dv:sentinel-dv /path/to/artifacts

# Index database writable only by server
chmod 600 /path/to/sentinel_dv.db
chown sentinel-dv:sentinel-dv /path/to/sentinel_dv.db
```

#### Process Isolation

```bash
# Run as dedicated user (not root)
useradd -r -s /bin/false sentinel-dv

# Use systemd sandboxing
[Service]
User=sentinel-dv
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/sentinel-dv
```

#### Network Isolation

```yaml
# Limit network access if needed
# (Sentinel DV doesn't require network for local artifacts)

# If using remote artifact mounts:
# - Use VPN or private networks
# - Enable TLS for all connections
# - Validate certificates
```

#### Configuration Security

```bash
# Protect config file
chmod 600 config.yaml
chown sentinel-dv:sentinel-dv config.yaml

# Never commit credentials to git
echo "config.yaml" >> .gitignore

# Use environment variables for sensitive values
export ARTIFACT_ROOT=/secure/path
```

### Security Updates

We will:
- **Patch critical vulnerabilities** within 48 hours
- **Release security updates** as PATCH versions
- **Announce** via GitHub Security Advisories
- **Backport** to supported versions (current + previous MAJOR)

Subscribe to:
- GitHub Security Advisories
- Release notifications
- Mailing list (if available)

### Audit Trail

For production deployments, enable logging:

```yaml
logging:
  level: INFO
  audit: true  # Log all tool calls with parameters
  format: json
  
audit:
  log_file: /var/log/sentinel-dv/audit.log
  include_user: true
  include_timestamp: true
  include_duration: true
```

### Dependency Security

We use:
- **Dependabot** for automated dependency updates
- **pip-audit** for known vulnerability scanning
- **Snyk** for continuous monitoring (optional)

Run security scans:
```bash
# Install pip-audit
pip install pip-audit

# Scan dependencies
pip-audit

# Check for updates
pip list --outdated
```

### Known Limitations

Current security limitations:
1. **Waveform summaries** are experimental and may not have full path validation
2. **Coverage parsing** may expose vendor-specific paths if not configured correctly
3. **Symlink handling** relies on OS resolution (may vary)

### Security Checklist for Deployments

Before deploying to production:

- [ ] Review and customize `redaction.patterns`
- [ ] Set appropriate `security.max_*` limits
- [ ] Validate `artifact_roots` permissions (read-only)
- [ ] Enable audit logging
- [ ] Run as non-root user
- [ ] Configure systemd sandboxing (if applicable)
- [ ] Set up security update notifications
- [ ] Run `pip-audit` to check dependencies
- [ ] Review firewall rules (if network access needed)
- [ ] Test path traversal protections
- [ ] Test redaction with real logs
- [ ] Verify limit enforcement under load

### Contact

For security concerns: [security@sentinel-dv.org]

For general issues: [GitHub Issues](https://github.com/kiranreddi/sentinel-dv/issues)

---

**Last updated:** 2026-05-26
**Version:** 1.1.0
