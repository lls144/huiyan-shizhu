"""Offline M4 detection-sequence simulator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_event_config
from .reporting import simulate_manifest, write_csv_report, write_json_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("pc/config/events.json"),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    simulate = subparsers.add_parser(
        "simulate",
        help="convert offline detection sequences to object lifecycle events",
    )
    simulate.add_argument("--input", type=Path, required=True)
    simulate.add_argument("--output-json", type=Path, required=True)
    simulate.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    config = load_event_config(args.config)
    report = simulate_manifest(args.input, config, args.config)
    write_json_report(report, args.output_json)
    write_csv_report(report, args.output_csv)
    print(json.dumps({**report["summary"], "performance": report["performance"]}, indent=2))
    return 0 if report["summary"]["all_scenarios_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
