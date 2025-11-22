from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Sequence, Tuple, Type

from connectors.base import AbstractSync
from connectors.firms_fires import FIRMSFiresSync
from connectors.osm_changesets import OSMChangesetsSync
from connectors.wiki_pageviews import WikiPageviewsSync
from hbc.forecasting import generate_synthetic_forecast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_DATA_DIR = PROJECT_ROOT / "data" / "public"
CONNECTOR_REGISTRY: Dict[str, Tuple[Type[AbstractSync], str]] = {
    "wiki": (WikiPageviewsSync, "wiki_pageviews"),
    "osm": (OSMChangesetsSync, "osm_changesets"),
    "firms": (FIRMSFiresSync, "firms_fires"),
}


# ---------------------------------------------------------------------------
# Forecast command (legacy default)
# ---------------------------------------------------------------------------


def _build_forecast_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hbc-cli",
        description=(
            "Generate synthetic behavior forecasts (same deterministic logic as the API)."
        ),
    )
    parser.add_argument("--region", required=True, help="Region identifier (free text)")
    parser.add_argument(
        "--horizon",
        type=int,
        default=7,
        help="Forecast horizon in days (1-30). Default: 7",
    )
    parser.add_argument(
        "--modalities",
        nargs="*",
        default=[],
        help="Optional modalities contributing to the forecast (space-separated).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit compact JSON (no pretty-print).",
    )
    return parser


def _validate_horizon(parser: argparse.ArgumentParser, horizon: int) -> None:
    if not 1 <= horizon <= 30:
        parser.error("--horizon must be between 1 and 30 days")


def _output_payload(
    region: str, horizon: int, modalities: Sequence[str], compact: bool
) -> str:
    forecast, confidence, explanations = generate_synthetic_forecast(
        region, horizon, list(modalities)
    )
    payload = {
        "region": region,
        "horizon": horizon,
        "modalities": list(modalities),
        "forecast": forecast,
        "confidence": confidence,
        "explanations": explanations,
        "ethics": {"synthetic": True, "pii": False},
    }
    return json.dumps(payload, indent=None if compact else 2)


def _run_forecast(argv: Sequence[str] | None = None) -> int:
    parser = _build_forecast_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    _validate_horizon(parser, args.horizon)

    try:
        output = _output_payload(args.region, args.horizon, args.modalities, args.json)
    except Exception as exc:  # pragma: no cover - protective fallback
        parser.error(str(exc))

    print(output)
    return 0


# ---------------------------------------------------------------------------
# Public data sync command
# ---------------------------------------------------------------------------


def _build_sync_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hbc-cli sync-public-data",
        description=(
            "Pull daily public data snapshots (wiki, OSM, FIRMS) and store them locally."
        ),
    )
    parser.add_argument(
        "--date",
        help="Date in YYYY-MM-DD format (default: today UTC).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_PUBLIC_DATA_DIR),
        help="Destination directory for snapshots (default: %(default)s).",
    )
    parser.add_argument(
        "--sources",
        nargs="*",
        choices=sorted(CONNECTOR_REGISTRY.keys()),
        default=sorted(CONNECTOR_REGISTRY.keys()),
        help="Subset of sources to pull (default: all).",
    )
    parser.add_argument(
        "--wiki-hours",
        type=int,
        default=6,
        help="Maximum number of hourly pageview files to fetch (1-24, default: 6).",
    )
    parser.add_argument(
        "--osm-max-bytes",
        type=int,
        default=10 * 1024 * 1024,
        help="Maximum decompressed bytes to read from OSM changesets (default: 10MB).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy the snapshot into data/public/latest for immediate API use.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a JSON summary to stdout after completion.",
    )
    return parser


def _run_sync_public_data(argv: Sequence[str] | None = None) -> int:
    parser = _build_sync_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    date = args.date or datetime.utcnow().strftime("%Y-%m-%d")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError as exc:
        parser.error(f"--date must be YYYY-MM-DD (error: {exc})")

    output_root = Path(args.output_dir).resolve()
    snapshot_dir = output_root / date
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    sources_summary: Dict[str, Dict[str, object]] = {}
    errors: Dict[str, str] = {}

    for source_name in args.sources:
        connector_cls, stem = CONNECTOR_REGISTRY[source_name]
        kwargs = {"date": date}
        if source_name == "wiki":
            kwargs["max_hours"] = args.wiki_hours
        if source_name == "osm":
            kwargs["max_bytes"] = args.osm_max_bytes
        connector = connector_cls(**kwargs)
        try:
            df = connector.pull()
            csv_path = snapshot_dir / f"{stem}.csv"
            df.to_csv(csv_path, index=False)
            # Handle paths both inside and outside PROJECT_ROOT
            try:
                path_str = str(csv_path.relative_to(PROJECT_ROOT))
            except ValueError:
                # Path is outside PROJECT_ROOT, use absolute path
                path_str = str(csv_path)
            sources_summary[source_name] = {
                "rows": int(len(df)),
                "path": path_str,
            }
        except Exception as exc:  # pragma: no cover - external dependencies
            errors[source_name] = str(exc)
            sources_summary[source_name] = {"rows": 0, "error": str(exc)}

    snapshot = {
        "date": date,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "sources": sources_summary,
        "errors": errors,
    }

    snapshot_path = snapshot_dir / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2))

    if args.apply:
        latest_dir = output_root / "latest"
        if latest_dir.exists():
            shutil.rmtree(latest_dir)
        shutil.copytree(snapshot_dir, latest_dir)

    if args.summary:
        print(json.dumps(snapshot, indent=2))

    if errors:
        print(
            f"Completed with {len(errors)} error(s); see {snapshot_path} for details.",
            file=sys.stderr,
        )
        return 1

    print(f"Snapshot written to {snapshot_dir}")
    if args.apply:
        print(f"'latest' pointer updated to {snapshot_dir}")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    arg_list = list(argv) if argv is not None else sys.argv[1:]
    if arg_list and arg_list[0] == "sync-public-data":
        return _run_sync_public_data(arg_list[1:])
    return _run_forecast(arg_list)


if __name__ == "__main__":  # pragma: no cover - handled via entrypoint
    sys.exit(main())
