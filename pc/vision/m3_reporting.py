"""Offline M3 evaluation over deterministic or user-supplied scene manifests."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import VisionConfig
from .live import _git_state
from .pipeline import MultiImageAnalysis, analyze_multiple_objects, annotated_multi_image
from .reporting import write_image

STANDARD_SCENES = {"normal", "bright", "dark", "side_light"}
CSV_FIELDS = [
    "filename",
    "scene",
    "source_type",
    "evaluation_kind",
    "preprocess_mode",
    "expected_count",
    "detected_count",
    "expected_labels",
    "detected_labels",
    "matched_label_count",
    "count_matches",
    "labels_match",
    "method_pass",
    "processing_ms",
    "object_index",
    "predicted_label",
    "confidence",
    "bbox",
    "area_ratio",
    "solidity",
    "circularity",
]


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("source_type") != "synthetic":
        raise ValueError("M3 synthetic manifest must declare source_type=synthetic")
    if not isinstance(payload.get("scenes"), list) or not payload["scenes"]:
        raise ValueError("M3 synthetic manifest must contain at least one scene")
    return payload


def _matched_label_count(expected: list[str], detected: list[str]) -> int:
    expected_counts = Counter(expected)
    detected_counts = Counter(detected)
    return sum(min(expected_counts[label], detected_counts[label]) for label in expected_counts)


def _evaluate_method(
    image: np.ndarray,
    config: VisionConfig,
    mode: str,
    expected_labels: list[str],
    evaluation_kind: str,
) -> tuple[dict[str, Any], MultiImageAnalysis]:
    started = time.perf_counter()
    analysis = analyze_multiple_objects(image, replace(config, preprocess_mode=mode))
    processing_ms = round((time.perf_counter() - started) * 1000.0, 3)
    detected_labels = [item.label for item in analysis.detections]
    count_matches = len(detected_labels) == len(expected_labels)
    labels_match = Counter(detected_labels) == Counter(expected_labels)
    record = analysis.to_record()
    record.update(
        {
            "processing_ms": processing_ms,
            "expected_count": len(expected_labels),
            "expected_labels": expected_labels,
            "matched_label_count": _matched_label_count(expected_labels, detected_labels),
            "count_matches": count_matches,
            "labels_match": labels_match,
            "method_pass": (
                bool(count_matches and labels_match)
                if evaluation_kind == "required_exact_match"
                else None
            ),
        }
    )
    return record, analysis


def evaluate_synthetic_dataset(
    input_root: Path,
    ground_truth_path: Path,
    config: VisionConfig,
    config_path: Path,
    diagnostics_dir: Path | None = None,
) -> dict[str, Any]:
    """Evaluate every manifest scene with both configured preprocessing modes."""

    manifest = _load_manifest(ground_truth_path)
    modes = (config.preprocess_mode, config.comparison_preprocess_mode)
    scene_records: list[dict[str, Any]] = []
    for truth in manifest["scenes"]:
        image_path = input_root / truth["filename"]
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"failed to read M3 synthetic image: {image_path}")
        expected_labels = list(truth["expected_labels"])
        evaluation_kind = (
            "required_exact_match" if truth["scene"] in STANDARD_SCENES else "diagnostic_only"
        )
        methods: dict[str, dict[str, Any]] = {}
        for mode in modes:
            method_record, analysis = _evaluate_method(
                image,
                config,
                mode,
                expected_labels,
                evaluation_kind,
            )
            methods[mode] = method_record
            if diagnostics_dir is not None:
                write_image(
                    diagnostics_dir / f"{Path(truth['filename']).stem}-{mode}-annotated.png",
                    annotated_multi_image(image, analysis),
                )

        required_pass = (
            all(bool(methods[mode]["method_pass"]) for mode in modes)
            if evaluation_kind == "required_exact_match"
            else None
        )
        scene_records.append(
            {
                "filename": truth["filename"],
                "source_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                "scene": truth["scene"],
                "source_type": manifest["source_type"],
                "evaluation_kind": evaluation_kind,
                "ground_truth": truth,
                "methods": methods,
                "required_scene_pass": required_pass,
                "comparison": {
                    "same_detected_count": len(
                        {methods[mode]["object_count"] for mode in modes}
                    )
                    == 1,
                    "same_detected_labels": len(
                        {tuple(methods[mode]["predicted_labels"]) for mode in modes}
                    )
                    == 1,
                },
            }
        )

    required = [item for item in scene_records if item["evaluation_kind"] == "required_exact_match"]
    diagnostic = [item for item in scene_records if item["evaluation_kind"] == "diagnostic_only"]
    all_required_pass = all(bool(item["required_scene_pass"]) for item in required)
    return {
        "schema_version": 1,
        "milestone": "M3",
        "source_type": "synthetic",
        "generated_at": _timestamp(),
        "acceptance_status": (
            "synthetic_offline_validated" if all_required_pass else "synthetic_offline_failed"
        ),
        "scope": "M3 offline multi-object and lighting-method comparison; not camera evidence",
        "git": _git_state(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "opencv": cv2.__version__,
            "numpy": np.__version__,
        },
        "input_root": str(input_root),
        "ground_truth_path": str(ground_truth_path),
        "config_path": str(config_path),
        "vision_config_snapshot": asdict(config),
        "generator": {
            "version": manifest.get("generator_version"),
            "seed": manifest.get("seed"),
            "deterministic": manifest.get("deterministic"),
        },
        "summary": {
            "scene_count": len(scene_records),
            "method_count": len(modes),
            "required_scene_count": len(required),
            "required_scene_pass_count": sum(
                bool(item["required_scene_pass"]) for item in required
            ),
            "all_required_scenes_pass": all_required_pass,
            "diagnostic_scene_count": len(diagnostic),
            "live_camera_validation_complete": False,
        },
        "limitations": [
            "Synthetic fixtures are deterministic software evidence, not real camera captures.",
            "Overlap and touching scenes are diagnostic observations and are not forced to pass.",
            "Real normal, bright/side, dark, occlusion, and touching scenes remain pending.",
        ],
        "results": scene_records,
    }


def write_m3_json_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_m3_csv_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for scene in report["results"]:
            expected = scene["ground_truth"]["expected_labels"]
            for mode, method in scene["methods"].items():
                common = {
                    "filename": scene["filename"],
                    "scene": scene["scene"],
                    "source_type": scene["source_type"],
                    "evaluation_kind": scene["evaluation_kind"],
                    "preprocess_mode": mode,
                    "expected_count": method["expected_count"],
                    "detected_count": method["object_count"],
                    "expected_labels": "|".join(expected),
                    "detected_labels": "|".join(method["predicted_labels"]),
                    "matched_label_count": method["matched_label_count"],
                    "count_matches": method["count_matches"],
                    "labels_match": method["labels_match"],
                    "method_pass": method["method_pass"],
                    "processing_ms": method["processing_ms"],
                }
                if not method["objects"]:
                    writer.writerow(common)
                    continue
                for item in method["objects"]:
                    features = item["features"]
                    writer.writerow(
                        {
                            **common,
                            "object_index": item["object_index"],
                            "predicted_label": item["predicted_label"],
                            "confidence": item["confidence"],
                            "bbox": json.dumps(features["bounding_box"]),
                            "area_ratio": features["area_ratio"],
                            "solidity": features["solidity"],
                            "circularity": features["circularity"],
                        }
                    )
