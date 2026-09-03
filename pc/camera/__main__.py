"""Command-line entry point for M1 camera enumeration and stability testing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .capture import run_stability_test, write_json_report
from .config import load_camera_config
from .devices import enumerate_camera_devices, select_camera_device


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("pc/config/camera.json"),
        help="camera JSON config path",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("enumerate", help="list cameras visible to the configured backend")

    stability = subparsers.add_parser("stability", help="run continuous capture and reopen checks")
    stability.add_argument("--output", type=Path, required=True, help="JSON result path")
    stability.add_argument("--sample-frame", type=Path, help="optional representative JPEG/PNG")
    stability.add_argument(
        "--duration",
        type=float,
        help="override configured duration in seconds for an intentional test run",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    config = load_camera_config(args.config)
    duration_override = getattr(args, "duration", None)
    if duration_override is not None:
        values = dict(config.__dict__)
        values["test_duration_seconds"] = duration_override
        config = type(config).from_dict(values)

    devices = enumerate_camera_devices(config.backend)
    if args.command == "enumerate":
        print(json.dumps([device.__dict__ for device in devices], ensure_ascii=False, indent=2))
        return 0

    device = select_camera_device(devices, config.device_name, config.fallback_index)
    report = run_stability_test(device, config, args.config, args.sample_frame)
    write_json_report(report, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
