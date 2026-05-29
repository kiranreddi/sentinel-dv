#!/usr/bin/env bash
# Run every check required before tagging vX.Y.Z (matches CI + release workflow).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "==> Installing dev dependencies"
python -m pip install -q -U pip
python -m pip install -q -e ".[dev]"

TAG="${1:-}"
if [[ -n "$TAG" ]]; then
  echo "==> Version consistency (tag: $TAG)"
  python scripts/check_versions.py "$TAG"
else
  echo "==> Version consistency (package only; pass tag before release, e.g. v1.3.2)"
  python scripts/check_versions.py
fi

echo "==> Ruff"
ruff check sentinel_dv/ tests/

echo "==> Black"
black --check sentinel_dv/ tests/

echo "==> Tests + coverage (>=70%)"
pytest tests/ \
  --cov=sentinel_dv \
  --cov-report=term-missing \
  --cov-report=json \
  --cov-fail-under=70 \
  -q

echo "==> Wheel smoke import"
python -m pip install -q build
rm -rf dist-wheel
python -m build --wheel --outdir dist-wheel
pip install -q --force-reinstall dist-wheel/*.whl
python -c "
import importlib
for mod in (
    'sentinel_dv.indexing.store',
    'sentinel_dv.server',
    'sentinel_dv.tools.mcp_metadata',
):
    importlib.import_module(mod)
print('wheel smoke OK')
"
pip install -q -e ".[dev]"

echo ""
echo "Pre-release checks passed."
if [[ -z "$TAG" ]]; then
  echo "Next: bump versions if needed, commit, then:"
  echo "  ./scripts/pre_release.sh vX.Y.Z"
  echo "  git tag vX.Y.Z && git push origin main && git push origin vX.Y.Z"
else
  echo "Next: git tag $TAG && git push origin main && git push origin $TAG"
fi
