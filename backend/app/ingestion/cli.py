"""Command line: `python -m app.ingestion.cli validate|load [--dir PATH]`."""

import argparse
import sys
from pathlib import Path

from app.ingestion.bundle import SeedError, load_bundle

DEFAULT_DIR = Path(__file__).resolve().parents[3] / "data" / "seed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingestion")
    parser.add_argument("command", choices=["validate", "load"])
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args(argv)
    try:
        bundle = load_bundle(args.dir)
    except SeedError as exc:
        print(f"{len(exc.problems)} problem(s) in {args.dir}:", file=sys.stderr)
        for p in exc.problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(
        f"valid: {len(bundle.sources)} sources, {len(bundle.opportunities)} opportunities, "
        f"{len(bundle.careers)} careers"
    )
    if args.command == "load":
        from app.core.config import get_settings
        from app.core.db import make_engine, make_session_factory
        from app.ingestion.loader import upsert_bundle

        settings = get_settings()
        with make_session_factory(make_engine(settings))() as db:
            counts = upsert_bundle(db, bundle)
        print("loaded:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
