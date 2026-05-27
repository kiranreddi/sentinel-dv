"""CLI for indexing verification artifacts into the DuckDB store."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sentinel_dv.config import resolve_config, set_config
from sentinel_dv.indexing.indexer import ArtifactIndexer


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Index verification artifacts for Sentinel DV")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.yaml")
    parser.add_argument(
        "--index-all",
        action="store_true",
        help="Scan artifact roots and rebuild the index",
    )
    args = parser.parse_args(argv)

    try:
        config = resolve_config(args.config)
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    set_config(config)
    indexer = ArtifactIndexer(
        config.artifact_roots,
        Path(config.index.path),
        adapters=config.adapters,
    )

    if not args.index_all:
        print("Nothing to do. Pass --index-all to scan and index artifacts.", file=sys.stderr)
        sys.exit(0)

    stats = indexer.index_all()
    print(
        f"Indexed runs={stats['runs']} tests={stats['tests']} "
        f"failures={stats['failures']} waveforms={stats.get('waveforms', 0)} "
        f"from {stats['artifacts']} artifacts"
    )


if __name__ == "__main__":
    main()
