"""Command-line launcher for the three-belt sorting simulation window.

Usage examples
--------------
Offline self-check (no hardware)::

    python -m pc.sorting --source synthetic --offscreen --soak-seconds 40 \
        --summary-json output/sorting/synthetic-smoke.json --screenshot output/sorting/synthetic.png

Real closed loop with the lab PLC (recognition -> belt -> PLC command)::

    python -m pc.sorting --source camera --reuse-calibration \
        --plc-config pc/config/plc.json
"""

from __future__ import annotations

import argparse
import os
import sys
import tracemalloc
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from pc.communication.config import load_plc_communication_config
from pc.communication.sink import build_plc_sink
from pc.events.config import load_event_config
from pc.vision.config import load_vision_config
from pc.vision.pipeline import analyze_multiple_objects

from .config import load_sorting_config
from .window import SortingWindow


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("synthetic", "camera"), default="camera")
    parser.add_argument("--vision-config", type=Path, default=Path("pc/config/vision.json"))
    parser.add_argument("--event-config", type=Path, default=Path("pc/config/events.json"))
    parser.add_argument("--sorting-config", type=Path, default=Path("pc/config/sorting.json"))
    parser.add_argument(
        "--plc-config",
        type=Path,
        default=None,
        help=(
            "PLC bridge config. Default: pc/config/plc.json for the camera source; "
            "the bridge stays off for synthetic runs unless this is given explicitly."
        ),
    )
    parser.add_argument("--camera-config", type=Path, default=Path("pc/config/camera.json"))
    parser.add_argument(
        "--roi-mode", choices=("auto", "manual", "fixed_normalized"), default="auto"
    )
    parser.add_argument(
        "--calibration-file", type=Path, default=Path("output/m2/runtime-calibration.json")
    )
    parser.add_argument("--reuse-calibration", action="store_true")
    parser.add_argument("--dataset-root", type=Path, default=Path("test_data/m3/synthetic"))
    parser.add_argument("--synthetic-fps", type=float, default=20.0)
    parser.add_argument("--frames-per-scene", type=int, default=20)
    parser.add_argument("--no-loop", action="store_true")
    parser.add_argument("--session-dir", type=Path, default=Path("output/sorting/sessions"))
    parser.add_argument("--m3-evidence-dir", type=Path, default=Path("output/m3/live-evidence"))
    parser.add_argument(
        "--expected-labels",
        nargs="*",
        choices=("triangle", "rectangle", "circle"),
        default=("triangle", "rectangle", "circle"),
    )
    parser.add_argument(
        "--auto-dequeue",
        action="store_true",
        help="light the lamps as soon as the belt finishes, without the physical button",
    )
    parser.add_argument(
        "--no-plc",
        action="store_true",
        help="force the PLC bridge off even when a plc config would otherwise be used",
    )
    parser.add_argument("--no-auto-start", action="store_true")
    parser.add_argument("--offscreen", action="store_true")
    parser.add_argument("--soak-seconds", type=float, default=0.0)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--screenshot", type=Path)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.offscreen:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from pc.gui.reporting import write_csv_record, write_json_record
    from pc.gui.sources import CameraFrameSource, SyntheticFrameSource

    vision_config = load_vision_config(args.vision_config)
    event_config = load_event_config(args.event_config)
    sorting_config = load_sorting_config(args.sorting_config)
    # Safety: an offline synthetic run must not write commands into the lab PLC
    # just because pc/config/plc.json has enabled=true. The bridge therefore only
    # starts for synthetic data when the operator points at a config explicitly.
    plc_config_path = args.plc_config
    if args.no_plc:
        plc_config_path = None
    elif plc_config_path is None:
        plc_config_path = Path("pc/config/plc.json") if args.source == "camera" else None
    if plc_config_path is None:
        command_sink = None
    else:
        plc_config = load_plc_communication_config(plc_config_path)
        if args.auto_dequeue:
            plc_config = replace(plc_config, auto_dequeue=True)
        command_sink = build_plc_sink(plc_config)

    if args.source == "synthetic":
        source_factory = lambda: SyntheticFrameSource(
            args.dataset_root,
            vision_config,
            target_fps=args.synthetic_fps,
            frames_per_scene=args.frames_per_scene,
            loop=not args.no_loop,
        )
    else:
        source_factory = lambda: CameraFrameSource(
            args.camera_config,
            vision_config,
            args.roi_mode,
            args.calibration_file,
            args.reuse_calibration,
        )

    app = QApplication.instance() or QApplication([sys.argv[0]])
    window = SortingWindow(
        source_factory=source_factory,
        source_type=args.source,
        vision_config=vision_config,
        event_config=event_config,
        sorting_config=sorting_config,
        session_dir=args.session_dir,
        evidence_root=args.m3_evidence_dir,
        expected_labels=args.expected_labels,
        analyzer=analyze_multiple_objects,
        command_sink=command_sink,
    )
    window.show()
    if not args.no_auto_start:
        QTimer.singleShot(0, window.start_session)

    if args.soak_seconds > 0:
        tracemalloc.start()

        def finish_soak() -> None:
            current_bytes, peak_bytes = tracemalloc.get_traced_memory()
            window.session_annotations.update(
                {
                    "requested_soak_seconds": args.soak_seconds,
                    "python_traced_current_bytes": current_bytes,
                    "python_traced_peak_bytes": peak_bytes,
                    "screenshot": str(args.screenshot) if args.screenshot else None,
                }
            )
            window.stop_session(block=True)
            if args.screenshot is not None:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                if not window.grab().save(str(args.screenshot)):
                    window.session_annotations["screenshot_error"] = "QWidget.grab save failed"
            tracemalloc.stop()
            app.quit()

        QTimer.singleShot(max(1, round(args.soak_seconds * 1000)), finish_soak)

    exit_code = app.exec()
    if window.is_running:
        window.stop_session(block=True)
    record = window.last_session_summary
    if record is not None:
        if args.summary_json is not None:
            write_json_record(record, args.summary_json)
        if args.summary_csv is not None:
            write_csv_record(record, args.summary_csv)
    if record is not None and record.get("error"):
        return 1
    return exit_code


def main() -> int:
    return run()
