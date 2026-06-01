# Contributing to Sentinel DV

First off, thank you for considering contributing to Sentinel DV! It's people like you that make Sentinel DV a great tool for the verification community.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

### Our Pledge

We are committed to making participation in this project a harassment-free experience for everyone, regardless of level of experience, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

**Bug Report Template:**

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Configuration: '...'
2. Artifacts: '...'
3. Tool call: '...'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What actually happened.

**Environment:**
- OS: [e.g., Linux, macOS, Windows]
- Python version: [e.g., 3.10.5]
- Sentinel DV version: [e.g., 2.2.0]
- Simulator: [e.g., VCS, Xcelium, Questa]

**Configuration:**
```yaml
# Paste relevant config.yaml sections
```

**Logs:**
```
# Paste relevant error logs
```

**Additional context**
Add any other context about the problem here.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

**Enhancement Request Template:**

```markdown
**Is your feature request related to a problem?**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Would this break backward compatibility?**
- [ ] Yes (requires MAJOR version bump)
- [ ] No (MINOR or PATCH)

**Additional context**
Add any other context or screenshots about the feature request here.
```

### Pull Requests

We actively welcome your pull requests! Follow this process:

1. **Fork the repo** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** if you've added code that should be tested
4. **Update documentation** if you've changed APIs or added features
5. **Ensure the test suite passes** (`pytest`)
6. **Ensure coverage doesn't decrease** (target: 70%+)
7. **Run linters** (`ruff`, `black`, `mypy`)
8. **Write a clear commit message** following Conventional Commits
9. **Submit your pull request**

**Pull Request Template:**

```markdown
**Description**
Brief description of changes.

**Type of change**
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

**Checklist:**
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Coverage remains at or above 70%
- [ ] I have updated CHANGELOG.md

**Related Issues**
Fixes #(issue)

**Testing**
Describe the tests you ran to verify your changes.
```

## Releasing (maintainers)

Do **not** push a `v*` tag until pre-release checks pass. See **[docs/release/RELEASING.md](docs/release/RELEASING.md)** for the full checklist.

```bash
# After bumping version in pyproject.toml + docs:
./scripts/pre_release.sh vX.Y.Z
git push origin main
git tag vX.Y.Z && git push origin vX.Y.Z
```

The GitHub Release workflow runs the same gates (lint, tests, ≥70% coverage, version vs tag) before publishing to PyPI.

## Development Setup

### Prerequisites

- **Python 3.10 or higher**
- **pip** or **poetry**
- **Git**

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/sentinel-dv.git
cd sentinel-dv

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
python -c "import sentinel_dv; print(sentinel_dv.__version__)"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sentinel_dv --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_schemas.py

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

### Code Quality

```bash
# Format code
black sentinel_dv/ tests/

# Lint code
ruff check sentinel_dv/ tests/

# Auto-fix linting issues
ruff check --fix sentinel_dv/ tests/

# Type checking
mypy sentinel_dv/
```

### Building Documentation

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Serve docs locally
mkdocs serve

# Build docs
mkdocs build

# Open in browser
open http://127.0.0.1:8000
```

## Coding Standards

### Python Style Guide

We follow **PEP 8** with these specifics:
- **Line length:** 100 characters
- **Indentation:** 4 spaces
- **Quotes:** Double quotes for strings
- **Type hints:** Required for public APIs

### Naming Conventions

- **Modules:** `lowercase_with_underscores.py`
- **Classes:** `PascalCase`
- **Functions/methods:** `lowercase_with_underscores()`
- **Constants:** `UPPERCASE_WITH_UNDERSCORES`
- **Private:** `_leading_underscore`

### Documentation

- **Docstrings:** Use Google style
- **Type hints:** For all function signatures
- **Comments:** Explain "why", not "what"

Example:

```python
def parse_uvm_log(log_path: str, max_events: int = 1000) -> list[FailureEvent]:
    """Parse UVM log file and extract failure events.
    
    Args:
        log_path: Absolute path to UVM log file.
        max_events: Maximum number of events to extract (default: 1000).
        
    Returns:
        List of FailureEvent objects sorted by time.
        
    Raises:
        FileNotFoundError: If log_path doesn't exist.
        ValueError: If log format is invalid.
    """
    # Implementation details...
```

### Schema Design Principles

When adding or modifying schemas:

1. **Backward compatibility:** Never remove or rename fields in MINOR/PATCH versions
2. **Explicit typing:** Use Pydantic models with strict validation
3. **Optional vs required:** Make fields optional only when truly optional in source data
4. **Enums for categories:** Use Literal types for closed sets
5. **Documentation:** Every field must have a docstring

### Testing Requirements

- **Coverage target:** 70% minimum (aim for 80%+)
- **Unit tests:** For all public functions and classes
- **Integration tests:** For tool workflows end-to-end
- **Fixtures:** Use pytest fixtures for common test data
- **Mocking:** Mock external dependencies (file I/O, simulators)

Example test structure:

```python
# tests/unit/schemas/test_common.py
import pytest
from sentinel_dv.schemas.common import EvidenceRef

def test_evidence_ref_valid():
    """EvidenceRef should validate with valid inputs."""
    ref = EvidenceRef(
        kind="log",
        path="regression/test.log",
        span={"start_line": 10, "end_line": 20},
        extract="Error message",
        hash="abc123"
    )
    assert ref.kind == "log"
    assert ref.span["start_line"] == 10

def test_evidence_ref_missing_optional():
    """EvidenceRef should work without optional fields."""
    ref = EvidenceRef(kind="log", path="test.log")
    assert ref.span is None
```

## Adapter Development

When adding support for a new verification tool or format:

1. **Create adapter module** in `sentinel_dv/adapters/`
2. **Implement parser functions** that return schema objects
3. **Add tests** with real-world fixture files
4. **Document** in `docs/adapters/custom.md`
5. **Add config flag** to enable/disable
6. **Update examples**

See [Adapter Development Guide](docs/adapters/custom.md) for details.

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples:**

```
feat(adapters): add Verilator coverage parser

Implements parser for Verilator coverage output format.
Supports line and toggle coverage metrics.

Closes #42
```

```
fix(redaction): correctly handle multi-line tokens

Bearer tokens spanning multiple lines were not being
fully redacted. Updated regex pattern and added test.

Fixes #58
```

## Versioning

We use **Semantic Versioning** (SemVer):

- **MAJOR** (1.x.x): Breaking changes (schema removals, API changes)
- **MINOR** (x.1.x): New features (backward compatible)
- **PATCH** (x.x.1): Bug fixes (backward compatible)

Schema versions track separately and must be updated when schema changes.

## Release Process

1. Update `CHANGELOG.md` with release notes
2. Bump version in `pyproject.toml`
3. Create git tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. GitHub Actions will build and publish

## Continuous Integration

All checks run on [GitHub Actions](https://github.com/kiranreddi/sentinel-dv/actions). There is no CircleCI or other external CI for this repository.

| Workflow | File | When it runs |
|----------|------|----------------|
| **CI** | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Push and pull requests to `main` and `develop` |
| **Documentation** | [`.github/workflows/docs.yml`](.github/workflows/docs.yml) | Push and pull requests to `main` |
| **Release** | [`.github/workflows/release.yml`](.github/workflows/release.yml) | Pushes of version tags (`v*`) |

The **CI** workflow runs on Python 3.10, 3.11, and 3.12: `ruff`, `black --check`, `mypy` (non-blocking), `pytest` with coverage, and a security scan (`pip-audit`, `safety`). Coverage must stay at or above 70%.

Before opening a pull request, run the same checks locally:

```bash
pip install -e ".[dev]"
ruff check sentinel_dv/ tests/
black --check sentinel_dv/ tests/
pytest --cov=sentinel_dv --cov-report=term
pip install -e ".[docs]" && mkdocs build
```

## Community

- **Discussions:** For questions and ideas
- **Issues:** For bugs and feature requests
- **Pull Requests:** For contributions

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- Documentation acknowledgments

## Questions?

Feel free to:
- Open a [Discussion](https://github.com/kiranreddi/sentinel-dv/discussions)
- Ask in pull request comments
- Reach out to maintainers

---

**Thank you for contributing to Sentinel DV!** 🎉
