# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in Sentinel DV, please report it responsibly:

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please use GitHub Security Advisories:
- **Private report**: https://github.com/kiranreddi/sentinel-dv/security/advisories/new
- **Security center**: https://github.com/kiranreddi/sentinel-dv/security

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

---

## Security Model

Sentinel DV is designed with security as a core principle. See [Architecture → Security](../architecture/security.md) for the complete security model.

### Key Security Features

**1. Read-Only Design**
- MCP tools only read verification data
- No write, delete, or modify operations
- Prevents accidental or malicious data corruption

**2. Automatic Redaction**
- Credentials automatically removed from logs
- File paths sanitized
- Sensitive data filtered before exposure

**3. Path Sandboxing**
- File access restricted to allowed paths
- Path traversal attacks prevented
- Symbolic link following disabled

**4. Bounded Outputs**
- Response size limits prevent DoS
- Pagination enforced for large datasets
- Memory usage capped

**5. Input Validation**
- All inputs validated with Pydantic schemas
- SQL injection prevented (parameterized queries)
- No arbitrary code execution

---

## Supported Versions

We actively maintain security updates for:

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | ✅ Yes             |
| 0.x     | ❌ No (beta only)  |

Security patches are backported to the latest stable release only.

---

## Security Best Practices

### For Users

**1. Configure Path Restrictions**
```bash
# Restrict file access by configuring `artifact_roots` in `config.yaml`.
# The server validates that roots exist and are readable at startup.
python -m sentinel_dv.server --config config.yaml
```

**2. Use Separate Databases**
```bash
# Use separate `config.yaml` files with different `index.path` values.
python -m sentinel_dv.server --config ./config-prod.yaml  # Production
python -m sentinel_dv.server --config ./config-dev.yaml   # Development
```

**3. Regular Updates**
```bash
# Keep Sentinel DV up to date
pip install --upgrade sentinel-dv
```

**4. Monitor Logs**
```bash
# Run under your process manager and collect stdout/stderr logs.
python -m sentinel_dv.server --config config.yaml
```

---

### For Developers

**1. Validate All Inputs**
```python
from pydantic import BaseModel, Field

class SafeInput(BaseModel):
    run_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    page: int = Field(ge=1, le=1000)
```

**2. Sanitize Outputs**
```python
def redact_credentials(text: str) -> str:
    """Remove credentials from text."""
    patterns = [
        r"(password|token|key|secret)[:=]\s*[^\s]+",
        r"Bearer\s+[A-Za-z0-9_-]+",
    ]
    for pattern in patterns:
        text = re.sub(pattern, r"\1: [REDACTED]", text, flags=re.IGNORECASE)
    return text
```

**3. Limit Resource Usage**
```python
MAX_PAGE_SIZE = 100
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB

def safe_query(page_size: int):
    if page_size > MAX_PAGE_SIZE:
        raise ValueError(f"Page size exceeds maximum ({MAX_PAGE_SIZE})")
    # Execute query...
```

**4. Use Parameterized Queries**
```python
# ✅ Good - parameterized
cursor.execute(
    "SELECT * FROM tests WHERE run_id = ?",
    (run_id,)
)

# ❌ Bad - SQL injection risk
cursor.execute(
    f"SELECT * FROM tests WHERE run_id = '{run_id}'"
)
```

---

## Known Security Considerations

### 1. Local File Access

**Risk**: Sentinel DV indexes local files
**Mitigation**:
- Configure path access by setting `artifact_roots` in `config.yaml`.
- Run with least-privilege user account
- Use read-only file mounts in Docker

**Example**:
```bash
# Docker with read-only mount
docker run -v ./verification:/data:ro sentinel-dv:latest
```

---

### 2. Database Access

**Risk**: Index database contains indexed data
**Mitigation**:
- Restrict database file permissions (chmod 600)
- Store in secure directory
- Encrypt at rest if needed

**Example**:
```bash
# Secure database permissions
chmod 600 ./sentinel_db/index.db
chown sentinel-user:sentinel-group ./sentinel_db/index.db
```

---

### 3. MCP Communication

**Risk**: MCP protocol uses stdio communication
**Mitigation**:
- MCP servers run locally only (no network exposure)
- Communication authenticated by AI client (Claude/Cline)
- No external network access required

---

### 4. Log Parsing

**Risk**: Parsing untrusted log files
**Mitigation**:
- No code execution from logs
- Regex patterns bounded
- File size limits enforced
- Timeout for parsing operations

**Example**:
```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
PARSE_TIMEOUT = 30  # seconds

@timeout(PARSE_TIMEOUT)
def parse_log(file_path: str):
    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        raise ValueError("File too large")
    # Parse...
```

---

## Threat Model

### Assets

- **Verification data**: Test results, logs, coverage
- **System files**: Configuration, database
- **User credentials**: If present in logs (auto-redacted)

### Threats

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| Path traversal | Low | Medium | Path sandboxing |
| Credential exposure | Medium | High | Auto-redaction |
| DoS (large queries) | Medium | Medium | Bounded outputs |
| SQL injection | Low | High | Parameterized queries |
| Code injection (logs) | Low | Critical | No code execution |

### Assumptions

- MCP server runs in trusted environment
- AI client (Claude/Cline) is trusted
- User has legitimate access to verification data
- Database is stored securely

---

## Security Audits

### Internal Reviews

- ✅ Code review for all changes
- ✅ Automated security scanning (Dependabot)
- ✅ SAST with Bandit and Ruff
- ✅ Dependency vulnerability scanning

### External Audits

No external security audits have been performed yet. If you're interested in conducting a security audit, please contact us.

---

## Vulnerability Disclosure Timeline

1. **T+0**: Vulnerability reported
2. **T+48h**: Acknowledgment sent
3. **T+7d**: Initial assessment completed
4. **T+30d**: Fix developed and tested
5. **T+45d**: Security release published
6. **T+90d**: Public disclosure (if agreed)

We follow responsible disclosure practices and will work with reporters to coordinate public disclosure.

---

## Security Contacts

- **Private security reports**: https://github.com/kiranreddi/sentinel-dv/security/advisories/new
- **Security advisories**: https://github.com/kiranreddi/sentinel-dv/security/advisories
- **General issues**: https://github.com/kiranreddi/sentinel-dv/issues

---

## Acknowledgments

We thank the following researchers for responsibly disclosing security issues:

*(None yet - this section will be updated as security reports are received and addressed)*

---

## Related Documentation

- [Architecture → Security Model](../architecture/security.md) - Complete security design
- [Installation Guide](../getting-started/installation.md) - Secure installation practices
- [Contributing Guide](https://github.com/kiranreddi/sentinel-dv/blob/main/CONTRIBUTING.md) - Secure development practices

---

## Updates

This security policy was last updated: January 25, 2026

Security policy changes are tracked in [CHANGELOG.md](changelog.md).
