"""Deterministic offline M4 sequence simulation and structured evidence output."""

from __future__ import annotations

import csv
import json
import platform
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from pc.vision.live import _git_state

from .config import EventConfig
from .models import Detection
from .tracker import ObjectStateManager

CSV_FIELDS = [
    "scenario",
    "scenario_pass",
    "source_type",
    "frame_count",
    "detection_count",
    "event_id",
    "event_type",
    "object_id",
    "label",
    "confidence",
    "frame_index",
]


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_sequence_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("source_type") != "offline_simulated_detection_sequence":
        raise ValueError(
            "M4 manifest must declare source_type=offline_simulated_detection_sequence"
        )
    if not isinstance(payload.get("scenarios"), list) or not payload["scenarios"]:
        raise ValueError("M4 manifest must contain scenarios")
    return payload


def _event_expectation(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": event["event_type"],
        "object_id": event["object_id"],
        "label": event["label"],
        "frame_index": event["frame_index"],
    }


def _benchmark(config: EventConfig, frames: int = 300) -> dict[str, Any]:
    manager = ObjectStateManager(config)
    started = time.perf_counter()
    event_count = 0
    for frame_index in range(frames):
        detections = [
            Detection("triangle", 0.95, (100, 100, 100, 120), frame_index),
            Detection("rectangle", 0.96, (400, 100, 130, 110), frame_index),
            Detection("circle", 0.97, (750, 100, 120, 120), frame_index),
        ]
        event_count += len(manager.process_frame(frame_index, detections).events)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "source_type": "offline_simulated_detection_sequence",
        "frames": frames,
        "detections": frames * 3,
        "events": event_count,
        "processing_ms": round(elapsed_ms, 3),
        "frames_per_second": round(frames / (elapsed_ms / 1000.0), 3),
        "note": "State-manager-only timing; excludes image processing and I/O.",
    }


def simulate_manifest(
    manifest_path: Path,
    config: EventConfig,
    config_path: Path,
) -> dict[str, Any]:
    """Run all detection-only scenarios with a fresh state manager each time."""

    manifest = load_sequence_manifest(manifest_path)
    results: list[dict[str, Any]] = []
    for scenario in manifest["scenarios"]:
        manager = ObjectStateManager(config)
        frame_results: list[dict[str, Any]] = []
        emitted_events: list[dict[str, Any]] = []
        detection_count = 0
        started = time.perf_counter()
        for frame in scenario["frames"]:
            frame_index = int(frame["frame_index"])
            detections = [
                Detection.from_record(record, frame_index)
                for record in frame["detections"]
            ]
            detection_count += len(detections)
            update = manager.process_frame(frame_index, detections)
            frame_results.append(update.to_record())
            emitted_events.extend(event.to_record() for event in update.events)
        processing_ms = round((time.perf_counter() - started) * 1000.0, 3)

        expected_events = scenario["expected"]["events"]
        actual_event_keys = [_event_expectation(event) for event in emitted_events]
        expected_event_keys = [_event_expectation(event) for event in expected_events]
        final_active_ids = [
            state.object_id
            for state in manager.object_states()
            if state.active and state.confirmed
        ]
        expected_active_ids = scenario["expected"]["active_object_ids"]
        events_match = actual_event_keys == expected_event_keys
        active_match = final_active_ids == expected_active_ids
        results.append(
            {
                "scenario": scenario["name"],
                "description": scenario["description"],
                "source_type": manifest["source_type"],
                "frame_count": len(scenario["frames"]),
                "detection_count": detection_count,
                "processing_ms": processing_ms,
                "expected": scenario["expected"],
                "actual": {
                    "events": emitted_events,
                    "final_active_object_ids": final_active_ids,
                    "final_object_states": [
                        state.to_record() for state in manager.object_states()
                    ],
                },
                "events_match": events_match,
                "active_objects_match": active_match,
                "scenario_pass": bool(events_match and active_match),
                "frames": frame_results,
            }
        )

    all_pass = all(result["scenario_pass"] for result in results)
    return {
        "schema_version": 1,
        "milestone": "M4",
        "source_type": manifest["source_type"],
        "generated_at": _timestamp(),
        "acceptance_status": (
            "offline_simulation_validated" if all_pass else "offline_simulation_failed"
        ),
        "scope": "M4 detection-sequence to event validation; not live camera evidence",
        "git": _git_state(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
        },
        "manifest_path": str(manifest_path),
        "config_path": str(config_path),
        "event_config_snapshot": asdict(config),
        "summary": {
            "scenario_count": len(results),
            "passing_scenarios": sum(result["scenario_pass"] for result in results),
            "failing_scenarios": sum(not result["scenario_pass"] for result in results),
            "all_scenarios_pass": all_pass,
            "live_camera_validation_complete": False,
        },
        "performance": _benchmark(config),
        "limitations": [
            "Inputs are offline simulated detections, not live camera frames.",
            "Association uses only label, bbox IoU, and center distance; no motion model or ReID.",
            "M3 remains pending its five-scene real camera acceptance.",
            "M4 remains pending one short real camera lifecycle validation.",
        ],
        "results": results,
    }


def write_json_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for result in report["results"]:
            common = {
                "scenario": result["scenario"],
                "scenario_pass": result["scenario_pass"],
                "source_type": result["source_type"],
                "frame_count": result["frame_count"],
                "detection_count": result["detection_count"],
            }
            events = result["actual"]["events"]
            if not events:
                writer.writerow(common)
                continue
            for event in events:
                writer.writerow({**common, **event})
