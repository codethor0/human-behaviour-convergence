from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from hbc.forecasting import generate_synthetic_forecast


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hbc-cli",
        description=(
            "Generate synthetic behaviour forecasts (same deterministic logic as the API)."
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    _validate_horizon(parser, args.horizon)

    try:
        output = _output_payload(args.region, args.horizon, args.modalities, args.json)
    except Exception as exc:  # pragma: no cover - protective fallback
        parser.error(str(exc))

    print(output)
    return 0


if __name__ == "__main__":  # pragma: no cover - handled via entrypoint
    sys.exit(main())
