"""Batch evidence output and diagnostic image composition for M2."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import VisionConfig
from .pipeline import ImageAnalysis, annotated_image
from .preprocess import Image

SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
EXPECTED_LABELS = {
    "background": "no_object",
    "triangle": "triangle",
    "rectangle": "rectangle",
    "circle": "circle",
}


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def discover_images(input_root: Path) -> list[Path]:
    """Return supported images below the expected-label directories."""

    return sorted(
        path
        for path in input_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        and path.parent.name in EXPECTED_LABELS
    )


def expected_label_for(path: Path) -> str:
    try:
        return EXPECTED_LABELS[path.parent.name]
    except KeyError as error:
        raise ValueError(f"unsupported expected-label directory: {path.parent.name}") from error


def result_record(path: Path, input_root: Path, analysis: ImageAnalysis) -> dict[str, Any]:
    """Create a serializable result without turning an observation into acceptance."""

    record = analysis.to_record()
    expected = expected_label_for(path)
    record.update(
        {
            "image": path.relative_to(input_root).as_posix(),
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "expected_label": expected,
            "matches_expected_label": analysis.label == expected,
        }
    )
    return record


def _panel(image: Image, title: str, size: tuple[int, int] = (480, 320)) -> Image:
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    target_width, target_height = size
    usable_height = target_height - 34
    scale = min(target_width / image.shape[1], usable_height / image.shape[0])
    resized = cv2.resize(
        image,
        (max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale))),
        interpolation=cv2.INTER_AREA,
    )
    canvas = np.full((target_height, target_width, 3), 245, dtype=np.uint8)
    x = (target_width - resized.shape[1]) // 2
    y = 34 + (usable_height - resized.shape[0]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    cv2.putText(canvas, title, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
    return canvas


def diagnostic_montage(source: Image, analysis: ImageAnalysis) -> Image:
    """Compose the report-relevant stages; Canny remains diagnostic only."""

    stages = analysis.preprocessing
    panels = [
        _panel(annotated_image(source, analysis), "source / ROI / result"),
        _panel(stages.roi, "ROI"),
        _panel(stages.gray, "gray"),
        _panel(stages.blurred, "Gaussian blur"),
        _panel(stages.binary, f"inverse Otsu = {stages.otsu_threshold:.0f}"),
        _panel(stages.canny, "Canny (diagnostic only)"),
    ]
    return np.vstack((np.hstack(panels[:3]), np.hstack(panels[3:])))


def write_image(path: Path, image: Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f"failed to write image: {path}")


def write_json_report(
    records: list[dict[str, Any]],
    config: VisionConfig,
    config_path: Path,
    input_root: Path,
    output_path: Path,
    acceptance_status: str = "pending_user_validation",
) -> dict[str, Any]:
    """Write versioned batch observations with pending user acceptance."""

    report = {
        "schema_version": 1,
        "generated_at": _timestamp(),
        "acceptance_status": acceptance_status,
        "scope": "M2 offline single-object recognition only",
        "input_root": str(input_root),
        "config_path": str(config_path),
        "config": config.__dict__,
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "opencv": cv2.__version__,
            "numpy": np.__version__,
        },
        "summary": {
            "images": len(records),
            "matching_expected_label": sum(bool(record["matches_expected_label"]) for record in records),
            "mismatching_expected_label": sum(not bool(record["matches_expected_label"]) for record in records),
        },
        "results": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def write_csv_report(records: list[dict[str, Any]], output_path: Path) -> None:
    """Write the requested one-row-per-image measurements."""

    fieldnames = [
        "image",
        "expected_label",
        "predicted_label",
        "matches_expected_label",
        "confidence",
        "vertices",
        "area_ratio",
        "solidity",
        "circularity",
        "passed_contour_filter",
        "otsu_threshold",
        "valid_contours",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            features = record["features"] or {}
            writer.writerow(
                {
                    "image": record["image"],
                    "expected_label": record["expected_label"],
                    "predicted_label": record["predicted_label"],
                    "matches_expected_label": record["matches_expected_label"],
                    "confidence": record["confidence"],
                    "vertices": features.get("vertices", ""),
                    "area_ratio": features.get("area_ratio", ""),
                    "solidity": features.get("solidity", ""),
                    "circularity": features.get("circularity", ""),
                    "passed_contour_filter": record["passed_contour_filter"],
                    "otsu_threshold": record["otsu_threshold"],
                    "valid_contours": record["valid_contours"],
                }
            )
