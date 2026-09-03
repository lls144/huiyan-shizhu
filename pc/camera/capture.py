"""Open a configured camera and collect reproducible stability metrics."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2

from .config import CameraConfig
from .devices import CameraDevice


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _fourcc_text(value: float) -> str:
    integer = int(value)
    return "".join(chr((integer >> (8 * offset)) & 0xFF) for offset in range(4))


def open_configured_camera(device: CameraDevice, config: CameraConfig) -> cv2.VideoCapture:
    """Open a device and apply requested mode settings."""

    capture = cv2.VideoCapture(device.index, device.backend_id)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"failed to open camera {device.index}: {device.name}")

    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*config.fourcc))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.requested_width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.requested_height)
    capture.set(cv2.CAP_PROP_FPS, config.requested_fps)
    return capture


def verify_reopen_cycles(device: CameraDevice, config: CameraConfig) -> list[dict[str, Any]]:
    """Open, read one frame, and close the camera repeatedly."""

    results: list[dict[str, Any]] = []
    for cycle in range(1, config.reopen_cycles + 1):
        capture: cv2.VideoCapture | None = None
        started = time.perf_counter()
        try:
            capture = open_configured_camera(device, config)
            success, frame = capture.read()
            results.append(
                {
                    "cycle": cycle,
                    "opened": capture.isOpened(),
                    "frame_read": bool(success),
                    "frame_shape": list(frame.shape) if success else None,
                    "elapsed_seconds": round(time.perf_counter() - started, 6),
                }
            )
        except Exception as error:  # captured in the test report, then evaluated
            results.append(
                {
                    "cycle": cycle,
                    "opened": False,
                    "frame_read": False,
                    "frame_shape": None,
                    "elapsed_seconds": round(time.perf_counter() - started, 6),
                    "error": f"{type(error).__name__}: {error}",
                }
            )
        finally:
            if capture is not None:
                capture.release()
    return results


def run_stability_test(
    device: CameraDevice,
    config: CameraConfig,
    config_path: Path,
    sample_frame_path: Path | None = None,
) -> dict[str, Any]:
    """Capture continuously for the configured duration and return raw metrics."""

    started_at = _timestamp()
    capture = open_configured_camera(device, config)
    sample_frame = None
    successful_reads = 0
    failed_reads = 0
    success_times: list[float] = []
    observed_shapes: dict[str, int] = {}

    try:
        for _ in range(config.warmup_frames):
            capture.read()

        actual_properties = {
            "width": capture.get(cv2.CAP_PROP_FRAME_WIDTH),
            "height": capture.get(cv2.CAP_PROP_FRAME_HEIGHT),
            "fps": capture.get(cv2.CAP_PROP_FPS),
            "fourcc": _fourcc_text(capture.get(cv2.CAP_PROP_FOURCC)),
            "backend": capture.getBackendName(),
        }

        test_started = time.perf_counter()
        while time.perf_counter() - test_started < config.test_duration_seconds:
            success, frame = capture.read()
            now = time.perf_counter()
            if success:
                successful_reads += 1
                success_times.append(now)
                shape_key = "x".join(str(value) for value in frame.shape)
                observed_shapes[shape_key] = observed_shapes.get(shape_key, 0) + 1
                if sample_frame is None:
                    sample_frame = frame.copy()
            else:
                failed_reads += 1
        measured_duration = time.perf_counter() - test_started
    finally:
        capture.release()

    attempts = successful_reads + failed_reads
    gaps = [later - earlier for earlier, later in zip(success_times, success_times[1:])]
    max_gap = max(gaps, default=0.0)
    success_rate = successful_reads / attempts if attempts else 0.0
    measured_fps = successful_reads / measured_duration if measured_duration else 0.0

    sample_sha256 = None
    if sample_frame_path is not None and sample_frame is not None:
        sample_frame_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(sample_frame_path), sample_frame):
            raise RuntimeError(f"failed to write sample frame to {sample_frame_path}")
        sample_sha256 = hashlib.sha256(sample_frame_path.read_bytes()).hexdigest()

    reopen_results = verify_reopen_cycles(device, config)
    criteria = {
        "all_reopen_cycles_passed": all(
            result["opened"] and result["frame_read"] for result in reopen_results
        ),
        "read_success_rate_passed": success_rate >= config.minimum_read_success_rate,
        "maximum_frame_gap_passed": max_gap <= config.maximum_frame_gap_seconds,
        "actual_frame_size_matches_request": (
            int(actual_properties["width"]) == config.requested_width
            and int(actual_properties["height"]) == config.requested_height
        ),
    }

    return {
        "schema_version": 1,
        "started_at": started_at,
        "finished_at": _timestamp(),
        "config_path": str(config_path),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "opencv": cv2.__version__,
        },
        "device": asdict(device),
        "requested": {
            "width": config.requested_width,
            "height": config.requested_height,
            "fps": config.requested_fps,
            "fourcc": config.fourcc,
        },
        "actual_properties": actual_properties,
        "duration": {
            "requested_seconds": config.test_duration_seconds,
            "measured_seconds": round(measured_duration, 6),
        },
        "frames": {
            "attempted": attempts,
            "successful": successful_reads,
            "failed": failed_reads,
            "success_rate": round(success_rate, 9),
            "measured_fps": round(measured_fps, 6),
            "maximum_successful_frame_gap_seconds": round(max_gap, 6),
            "observed_shapes": observed_shapes,
        },
        "reopen_cycles": reopen_results,
        "criteria": criteria,
        "passed": all(criteria.values()),
        "sample_frame": str(sample_frame_path) if sample_frame_path else None,
        "sample_frame_sha256": sample_sha256,
    }


def write_json_report(report: dict[str, Any], path: Path) -> None:
    """Write a deterministic, UTF-8 JSON evidence file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
