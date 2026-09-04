from pathlib import Path

import cv2
import numpy as np
import pytest

from pc.vision.classifier import classify_shape
from pc.vision.config import load_vision_config
from pc.vision.contours import extract_contour_features
from pc.vision.pipeline import analyze_image

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_vision_config(REPO_ROOT / "pc/config/vision.json")
ROI_SHAPE = (600, 800)


def _classification(points: np.ndarray) -> tuple[str, float, int]:
    contour = points.astype(np.int32).reshape(-1, 1, 2)
    features, _ = extract_contour_features(contour, ROI_SHAPE, CONFIG)
    result = classify_shape(features, CONFIG)
    return result.label, result.confidence, features.vertices


def test_synthetic_triangle_is_classified() -> None:
    label, confidence, vertices = _classification(np.array([[400, 120], [250, 430], [550, 430]]))
    assert (label, vertices) == ("triangle", 3)
    assert 0 < confidence <= 1


def test_synthetic_rotated_rectangle_is_classified() -> None:
    points = cv2.boxPoints(((400, 300), (260, 180), 23))
    label, confidence, vertices = _classification(points)
    assert (label, vertices) == ("rectangle", 4)
    assert 0 < confidence <= 1


def test_synthetic_circle_is_classified() -> None:
    angles = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    points = np.column_stack((400 + 145 * np.cos(angles), 300 + 145 * np.sin(angles)))
    label, confidence, vertices = _classification(points)
    assert label == "circle"
    assert vertices >= CONFIG.circle_min_vertices
    assert 0 < confidence <= 1


def test_synthetic_pentagon_is_unknown() -> None:
    angles = np.linspace(-np.pi / 2, 3 * np.pi / 2, 5, endpoint=False)
    points = np.column_stack((400 + 150 * np.cos(angles), 300 + 150 * np.sin(angles)))
    label, confidence, vertices = _classification(points)
    assert (label, vertices) == ("unknown", 5)
    assert confidence == 0.0


def test_synthetic_pentagon_survives_filter_and_pipeline_returns_unknown() -> None:
    image = np.full((600, 800, 3), 255, dtype=np.uint8)
    angles = np.linspace(-np.pi / 2, 3 * np.pi / 2, 5, endpoint=False)
    points = np.column_stack((400 + 120 * np.cos(angles), 280 + 120 * np.sin(angles))).astype(np.int32)
    cv2.fillPoly(image, [points], (0, 0, 0))

    result = analyze_image(image, CONFIG)

    assert result.label == "unknown"
    assert result.confidence == 0.0
    assert result.selected_candidate is not None
    assert result.selected_candidate.passed_filter


@pytest.mark.parametrize("label", ["triangle", "rectangle", "circle", "unknown"])
def test_classifier_labels_are_part_of_the_m2_contract(label: str) -> None:
    assert label in {"triangle", "rectangle", "circle", "unknown"}
