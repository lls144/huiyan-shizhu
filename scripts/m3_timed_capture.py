"""Timed, hands-free M3 evidence capture with the built-in webcam.

Why this exists: the interactive ``pc.vision multi-live`` flow needs the
operator to hit 1-5 at the right moment, which is awkward when they are holding
an A3 sheet up to a fixed laptop camera. This helper drives the *same* pipeline
and writes the *same* evidence layout (``save_m3_comparison_evidence``), but
shows a countdown on screen so the operator only has to hold still.

It captures, per scenario, three frames one second apart and keeps the one with
the most valid objects (ties broken by summed confidence), because a hand-held
sheet does move.

This is an acquisition helper, not a new vision path: it adds no thresholds and
changes no algorithm.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

if __package__ in (None, ""):  # allow running this file directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pc.vision.config import load_vision_config
from pc.vision.live import open_live_camera
from pc.vision.m3_live import analyze_preprocess_modes, save_m3_comparison_evidence
from pc.vision.roi import load_runtime_calibration

SCENARIOS: dict[str, str] = {
    "normal_light": "NORMAL LIGHT - three shapes, plain room light",
    "bright_or_side_light": "BRIGHT / SIDE LIGHT - shine a phone light from the side",
    "dark_light": "DARK - dim the room light as much as you can",
    "partial_occlusion": "PARTIAL OCCLUSION - cover part of one shape with your hand",
    "touching_or_merged": "TOUCHING - push the rectangle and circle together",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-config", type=Path, default=Path("pc/config/camera.json"))
    parser.add_argument("--vision-config", type=Path, default=Path("pc/config/vision.json"))
    parser.add_argument(
        "--calibration-file", type=Path, default=Path("output/m2/runtime-calibration.json")
    )
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument(
        "--scenarios", nargs="+", choices=tuple(SCENARIOS), default=("normal_light",)
    )
    parser.add_argument("--expected-labels", nargs="*", default=("triangle", "rectangle", "circle"))
    parser.add_argument("--prepare-seconds", type=float, default=12.0)
    parser.add_argument("--warmup-seconds", type=float, default=8.0)
    parser.add_argument("--capture-attempts", type=int, default=3)
    return parser


def _draw(frame, bounds, title, status, colour):
    annotated = frame.copy()
    left, top, right, bottom = bounds
    cv2.rectangle(annotated, (left, top), (right, bottom), colour, 2)
    cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 96), (0, 0, 0), -1)
    cv2.putText(
        annotated, title, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
    )
    cv2.putText(
        annotated, status, (12, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.8, colour, 2
    )
    cv2.putText(
        annotated,
        "keep the sheet filling the box | Q = abort",
        (12, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (200, 200, 200),
        1,
    )
    return annotated


def main() -> int:
    args = _parser().parse_args()
    vision_config = load_vision_config(args.vision_config)
    camera = open_live_camera(args.camera_config)
    window = "M3 timed capture"
    results: list[dict[str, object]] = []
    try:
        frame = None
        for _ in range(camera.config.warmup_frames + 1):
            success, candidate = camera.capture.read()
            if success:
                frame = candidate
        if frame is None:
            raise RuntimeError("camera produced no frame during warmup")
        calibration = load_runtime_calibration(args.calibration_file, frame.shape)
        bounds = calibration.roi.to_pixels(frame.shape)

        started = time.perf_counter()
        while time.perf_counter() - started < args.warmup_seconds:
            if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
                return 1
            cv2.imshow(
                window,
                _draw(frame, bounds, "GET READY", "hold the sheet up now", (0, 200, 255)),
            )
            success, candidate = camera.capture.read()
            if success:
                frame = candidate

        for index, scenario in enumerate(args.scenarios, start=1):
            title = f"[{index}/{len(args.scenarios)}] {SCENARIOS[scenario]}"
            prepare_until = time.perf_counter() + args.prepare_seconds
            analyses = analyze_preprocess_modes(frame, vision_config, calibration.roi)
            while time.perf_counter() < prepare_until:
                remaining = max(0, int(prepare_until - time.perf_counter()) + 1)
                left, top, right, bottom = bounds
                live = frame.copy()
                for analysis in analyses.values():
                    for detection in analysis.detections:
                        x, y, w, h = detection.candidate.features.bounding_box
                        cv2.rectangle(
                            live, (left + x, top + y), (left + x + w, top + y + h),
                            (0, 255, 0), 2,
                        )
                cv2.imshow(
                    window,
                    _draw(live, bounds, title, f"capturing in {remaining}s", (0, 200, 255)),
                )
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
                    return 1
                success, candidate = camera.capture.read()
                if success:
                    frame = candidate
                    analyses = analyze_preprocess_modes(frame, vision_config, calibration.roi)

            best_frame, best_analyses, best_score = None, None, None
            for _ in range(args.capture_attempts):
                analyses = analyze_preprocess_modes(frame, vision_config, calibration.roi)
                count = max(len(a.detections) for a in analyses.values())
                confidence = sum(
                    sum(d.confidence for d in a.detections) for a in analyses.values()
                )
                score = (count, round(confidence, 6))
                if best_score is None or score > best_score:
                    best_frame, best_analyses, best_score = frame.copy(), analyses, score
                cv2.imshow(
                    window,
                    _draw(frame, bounds, title, f"CAPTURED (objects={count})", (0, 255, 0)),
                )
                cv2.waitKey(400)
                success, candidate = camera.capture.read()
                if success:
                    frame = candidate

            path = save_m3_comparison_evidence(
                best_frame,
                best_analyses,
                scenario,
                args.expected_labels,
                calibration,
                camera,
                vision_config,
                args.evidence_dir,
            )
            results.append(
                {"scenario": scenario, "objects": best_score[0], "evidence": str(path)}
            )
            print(f"saved {scenario}: objects={best_score[0]} -> {path}")
    finally:
        camera.capture.release()
        cv2.destroyAllWindows()

    print("SUMMARY")
    for item in results:
        print(f"  {item['scenario']}: objects={item['objects']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
