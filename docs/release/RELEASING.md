# Releasing Sentinel DV

Releases are **tag-driven**: pushing `v*` triggers PyPI, GitHub Release, and MCP registry publish.  
**Do not tag until every step below passes** — the release workflow runs the same gates, but fixing issues after publish is painful.

## Before you tag (required)

### 1. Land changes on `main` with green CI

Every push to `main` runs [CI](https://github.com/kiranreddi/sentinel-dv/actions):

- Ruff + Black
- Full test suite + **≥70% coverage**
- Wheel import smoke (Python 3.12 job)

Wait for CI to succeed before releasing.

### 2. Run pre-release locally

```bash
./scripts/pre_release.sh vX.Y.Z
```

This runs the same checks as CI plus version alignment. Example:

```bash
# After bumping pyproject.toml to 1.3.2 and updating docs pins:
./scripts/pre_release.sh v1.3.2
```

Without a tag (version bump only):

```bash
./scripts/pre_release.sh
```

### 3. Version bump checklist

Update **all** of these to the same `X.Y.Z`:

| File | Field |
|------|--------|
| `pyproject.toml` | `version = "X.Y.Z"` |
| `sentinel_dv/__init__.py` | `__version__` |
| `server.json` | top-level and `packages[].version` |
| `README.md` | title + `>=X.Y.Z` / `@X.Y.Z` |
| `docs/index.md` | hero badge |
| `docs/getting-started/installation.md` | current release + pip pin |
| `docs/getting-started/quick-start.md` | pip pin + server banner |
| `examples/*.md`, `mkdocs.yml` | install pins |
| `CHANGELOG.md` | new `[X.Y.Z]` section |
| `docs/about/changelog.md` | new section + link |

`python scripts/check_versions.py vX.Y.Z` verifies the critical paths.

### 4. Documentation

- [ ] Mandatory config: `cp config.example.yaml` in installation + quick-start
- [ ] Changelog entry for user-visible changes
- [ ] `docs/release/vX.Y.Z-checklist.md` (copy from prior checklist)

### 5. Tag and push (publishes)

```bash
git add -A
git commit -m "Release vX.Y.Z: <short summary>"
git push origin main

git tag vX.Y.Z
git push origin vX.Y.Z
```

The [Release workflow](https://github.com/kiranreddi/sentinel-dv/actions/workflows/release.yml) will:

1. Run **preflight** (lint, tests, coverage, version vs tag)
2. Build wheel, publish PyPI, GitHub Release, MCP registry

### 6. After publish

- [ ] Confirm [PyPI](https://pypi.org/project/sentinel-dv/) shows `X.Y.Z`
- [ ] Confirm [GitHub Releases](https://github.com/kiranreddi/sentinel-dv/releases)
- [ ] Mark release checklist complete

## What went wrong on v1.3.1 (lessons)

| Issue | When it showed up | Prevention |
|-------|-------------------|------------|
| Coverage & new code untested | After tag; CI on later commits | Run `./scripts/pre_release.sh` before tag |
| Ruff SIM105 | CI failed on `main` after release | Pre-release runs ruff |
| Docs/config not obvious | User confusion | Checklist + quick-start `cp` step |
| Tag without waiting for CI | Release succeeded; `main` was red | Preflight job on tag + green `main` policy |

## Branch protection (recommended)

On GitHub → Settings → Branches → `main`:

- Require status check **CI / Test Python 3.12** (or all matrix jobs)
- Require branches to be up to date before merge

That blocks merging broken code; pre-release + tag preflight blocks bad releases.
