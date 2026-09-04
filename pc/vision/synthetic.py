"""Deterministic M3 synthetic multi-object dataset generator.

The generated images are algorithm-development fixtures, not camera evidence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .preprocess import Image

GENERATOR_VERSION = "1.0"
SYNTHETIC_SEED = 0
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080
BACKGROUND_REFLECTANCE = 235
FOREGROUND_REFLECTANCE = 22


@dataclass(frozen=True)
class SyntheticObject:
    """One physical object before same-colour overlap is composited."""

    label: str
    polygon: tuple[tuple[int, int], ...]

    def to_ground_truth(self) -> dict[str, Any]:
        points = np.asarray(self.polygon, dtype=np.int32)
        x, y, width, height = cv2.boundingRect(points)
        moments = cv2.moments(points)
        center = [
            round(moments["m10"] / moments["m00"]),
            round(moments["m01"] / moments["m00"]),
        ]
        return {
            "label": self.label,
            "polygon": [list(point) for point in self.polygon],
            "center": center,
            "bbox": [x, y, width, height],
        }


def _circle_polygon(
    center: tuple[int, int],
    radius: int,
    vertices: int = 72,
) -> tuple[tuple[int, int], ...]:
    angles = np.linspace(0.0, 2.0 * np.pi, vertices, endpoint=False)
    return tuple(
        (
            round(center[0] + radius * np.cos(angle)),
            round(center[1] + radius * np.sin(angle)),
        )
        for angle in angles
    )


def _separated_objects() -> tuple[SyntheticObject, ...]:
    return (
        SyntheticObject("triangle", ((620, 190), (510, 500), (730, 500))),
        SyntheticObject("rectangle", ((820, 220), (1040, 220), (1040, 480), (820, 480))),
        SyntheticObject("circle", _circle_polygon((1280, 350), 120)),
    )


def _occluded_objects() -> tuple[SyntheticObject, ...]:
    return (
        SyntheticObject("triangle", ((620, 190), (510, 500), (730, 500))),
        SyntheticObject("rectangle", ((900, 220), (1120, 220), (1120, 480), (900, 480))),
        SyntheticObject("circle", _circle_polygon((1110, 350), 120)),
    )


def _touching_objects() -> tuple[SyntheticObject, ...]:
    return (
        SyntheticObject("triangle", ((620, 190), (510, 500), (730, 500))),
        SyntheticObject("rectangle", ((820, 220), (1040, 220), (1040, 480), (820, 480))),
        SyntheticObject("circle", _circle_polygon((1160, 350), 120)),
    )


def _illumination_field(scene: str) -> tuple[np.ndarray, dict[str, Any]]:
    if scene == "normal":
        field = np.ones((IMAGE_HEIGHT, IMAGE_WIDTH), dtype=np.float32)
        return field, {"model": "linear", "gain": 1.0, "offset": 0}
    if scene == "bright":
        field = np.full((IMAGE_HEIGHT, IMAGE_WIDTH), 0.76, dtype=np.float32)
        return field, {"model": "linear", "gain": 0.76, "offset": 62}
    if scene == "dark":
        field = np.full((IMAGE_HEIGHT, IMAGE_WIDTH), 0.32, dtype=np.float32)
        return field, {"model": "linear", "gain": 0.32, "offset": 8}
    if scene == "side_light":
        horizontal = np.linspace(1.04, 0.62, IMAGE_WIDTH, dtype=np.float32)
        field = np.broadcast_to(horizontal, (IMAGE_HEIGHT, IMAGE_WIDTH))
        return field, {
            "model": "horizontal_linear_gain",
            "left_gain": 1.04,
            "right_gain": 0.62,
            "offset": 6,
        }
    raise ValueError(f"unsupported illumination scene: {scene}")


def _render_scene(
    objects: tuple[SyntheticObject, ...],
    illumination_scene: str,
) -> tuple[Image, dict[str, Any]]:
    reflectance = np.full(
        (IMAGE_HEIGHT, IMAGE_WIDTH),
        BACKGROUND_REFLECTANCE,
        dtype=np.uint8,
    )
    for item in objects:
        polygon = np.asarray(item.polygon, dtype=np.int32)
        cv2.fillPoly(reflectance, [polygon], FOREGROUND_REFLECTANCE)

    field, parameters = _illumination_field(illumination_scene)
    offset = float(parameters["offset"])
    illuminated = np.clip(reflectance.astype(np.float32) * field + offset, 0, 255).astype(np.uint8)
    return cv2.cvtColor(illuminated, cv2.COLOR_GRAY2BGR), parameters


def _scene_definitions() -> tuple[dict[str, Any], ...]:
    separated = _separated_objects()
    return (
        {
            "filename": "multi_normal.png",
            "scene": "normal",
            "illumination_scene": "normal",
            "objects": separated,
            "relations": [],
        },
        {
            "filename": "multi_bright.png",
            "scene": "bright",
            "illumination_scene": "bright",
            "objects": separated,
            "relations": [],
        },
        {
            "filename": "multi_dark.png",
            "scene": "dark",
            "illumination_scene": "dark",
            "objects": separated,
            "relations": [],
        },
        {
            "filename": "multi_side_light.png",
            "scene": "side_light",
            "illumination_scene": "side_light",
            "objects": separated,
            "relations": [],
        },
        {
            "filename": "multi_occlusion.png",
            "scene": "partial_occlusion",
            "illumination_scene": "normal",
            "objects": _occluded_objects(),
            "relations": [
                {
                    "type": "overlap",
                    "objects": ["rectangle", "circle"],
                    "description": "same-colour silhouettes partially overlap",
                }
            ],
        },
        {
            "filename": "multi_touching.png",
            "scene": "touching",
            "illumination_scene": "normal",
            "objects": _touching_objects(),
            "relations": [
                {
                    "type": "edge_contact",
                    "objects": ["rectangle", "circle"],
                    "description": "circle touches rectangle at one boundary point",
                }
            ],
        },
    )


def generate_synthetic_dataset(output_root: Path) -> dict[str, Any]:
    """Generate the fixed M3 fixtures and return their complete ground truth."""

    output_root.mkdir(parents=True, exist_ok=True)
    scenes: list[dict[str, Any]] = []
    for definition in _scene_definitions():
        image, illumination = _render_scene(
            definition["objects"],
            definition["illumination_scene"],
        )
        image_path = output_root / definition["filename"]
        if not cv2.imwrite(str(image_path), image):
            raise RuntimeError(f"failed to write synthetic image: {image_path}")
        objects = [item.to_ground_truth() for item in definition["objects"]]
        scenes.append(
            {
                "filename": definition["filename"],
                "scene": definition["scene"],
                "image_size": {"width": IMAGE_WIDTH, "height": IMAGE_HEIGHT},
                "background": {
                    "type": "uniform_gray_reflectance",
                    "reflectance_value": BACKGROUND_REFLECTANCE,
                },
                "foreground_reflectance_value": FOREGROUND_REFLECTANCE,
                "objects": objects,
                "expected_count": len(objects),
                "expected_labels": [item["label"] for item in objects],
                "illumination": illumination,
                "relations": definition["relations"],
            }
        )

    ground_truth = {
        "schema_version": 1,
        "source_type": "synthetic",
        "generator_version": GENERATOR_VERSION,
        "deterministic": True,
        "seed": SYNTHETIC_SEED,
        "image_size": {"width": IMAGE_WIDTH, "height": IMAGE_HEIGHT},
        "notes": "OpenCV/NumPy geometric fixtures; not camera captures or ML training data.",
        "scenes": scenes,
    }
    (output_root / "ground_truth.json").write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return ground_truth


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("test_data/m3/synthetic"),
    )
    args = parser.parse_args()
    manifest = generate_synthetic_dataset(args.output_root)
    print(f"generated {len(manifest['scenes'])} deterministic synthetic scenes in {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
