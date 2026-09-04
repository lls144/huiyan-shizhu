"""Offline-only command-line entry point for M2 single-object recognition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from .config import load_vision_config
from .pipeline import analyze_image
from .reporting import (
    diagnostic_montage,
    discover_images,
    result_record,
    write_csv_report,
    write_image,
    write_json_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("pc/config/vision.json"),
        help="vision JSON config path",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    batch = subparsers.add_parser("batch", help="analyze the labeled offline M2 image folders")
    batch.add_argument("--input-root", type=Path, required=True)
    batch.add_argument("--output-json", type=Path, required=True)
    batch.add_argument("--output-csv", type=Path, required=True)
    batch.add_argument("--diagnostics-dir", type=Path, required=True)
    batch.add_argument(
        "--acceptance-status",
        choices=("pending_user_validation", "offline_stage_user_validated"),
        default="pending_user_validation",
        help="recorded acceptance state; use validated only after explicit user confirmation",
    )
    batch.add_argument(
        "--evidence-dir",
        type=Path,
        help="optional directory for the first diagnostic montage of each source category",
    )
    live = subparsers.add_parser("live", help="run M2 OpenCV preview with startup ROI calibration")
    live.add_argument(
        "--camera-config",
        type=Path,
        default=Path("pc/config/camera.json"),
        help="existing M1 camera JSON config path",
    )
    live.add_argument(
        "--roi-mode",
        choices=("auto", "manual", "fixed_normalized"),
        default="auto",
        help="startup calibration mode; auto falls back to manual then fixed_normalized",
    )
    live.add_argument(
        "--calibration-file",
        type=Path,
        default=Path("output/m2/runtime-calibration.json"),
        help="ignored local runtime calibration JSON",
    )
    live.add_argument(
        "--reuse-calibration",
        action="store_true",
        help="explicitly restore the saved normalized ROI instead of recalibrating at startup",
    )
    live.add_argument(
        "--evidence-dir",
        type=Path,
        default=Path("output/m2/live-evidence"),
        help="ignored directory for S-key frame evidence and session JSON",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    config = load_vision_config(args.config)
    if args.command == "live":
        from .live import run_live_session

        return run_live_session(
            camera_config_path=args.camera_config,
            vision_config=config,
            requested_roi_mode=args.roi_mode,
            calibration_path=args.calibration_file,
            evidence_root=args.evidence_dir,
            reuse_calibration=args.reuse_calibration,
        )

    paths = discover_images(args.input_root)
    if not paths:
        print(f"no supported images found under {args.input_root}")
        return 2

    records: list[dict[str, object]] = []
    evidence_categories: set[str] = set()
    for path in paths:
        source = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if source is None:
            raise RuntimeError(f"failed to read image: {path}")
        analysis = analyze_image(source, config)
        record = result_record(path, args.input_root, analysis)
        records.append(record)
        relative_stem = path.relative_to(args.input_root).with_suffix("")
        montage = diagnostic_montage(source, analysis)
        write_image(args.diagnostics_dir / relative_stem.parent / f"{relative_stem.name}_pipeline.jpg", montage)
        source_category = path.parent.name
        if args.evidence_dir is not None and source_category not in evidence_categories:
            write_image(args.evidence_dir / f"M2-{path.stem}-pipeline.jpg", montage)
            evidence_categories.add(source_category)

    report = write_json_report(
        records,
        config,
        args.config,
        args.input_root,
        args.output_json,
        args.acceptance_status,
    )
    write_csv_report(records, args.output_csv)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["summary"]["mismatching_expected_label"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
