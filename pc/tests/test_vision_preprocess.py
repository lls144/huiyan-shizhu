from pathlib import Path

import cv2
import numpy as np

from pc.vision.config import load_vision_config
from pc.vision.pipeline import analyze_image
from pc.vision.preprocess import preprocess_image

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_vision_config(REPO_ROOT / "pc/config/vision.json")


def test_preprocess_produces_configured_roi_and_all_stages() -> None:
    image = np.full((100, 200, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (80, 35), (120, 70), (0, 0, 0), -1)

    result = preprocess_image(image, CONFIG)

    assert result.roi_bounds == (48, 8, 152, 75)
    assert result.roi.shape == (67, 104, 3)
    assert result.gray.shape == result.binary.shape == result.canny.shape == (67, 104)
    assert set(np.unique(result.binary)).issubset({0, 255})


def test_blank_white_image_returns_no_object() -> None:
    image = np.full((600, 800, 3), 255, dtype=np.uint8)
    result = analyze_image(image, CONFIG)
    assert result.label == "no_object"
    assert result.confidence == 0.0
    assert result.selected_candidate is None
