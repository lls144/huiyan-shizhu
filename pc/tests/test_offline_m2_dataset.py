from pathlib import Path

import cv2
import pytest

from pc.vision.config import load_vision_config
from pc.vision.pipeline import analyze_image
from pc.vision.reporting import discover_images, expected_label_for

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "test_data/raw/m2"
CONFIG = load_vision_config(REPO_ROOT / "pc/config/vision.json")


def test_real_m2_offline_images_match_directory_labels() -> None:
    paths = discover_images(RAW_ROOT) if RAW_ROOT.exists() else []
    if not paths:
        pytest.skip("ignored real M2 image set is not present")

    assert len(paths) == 10, "the current recorded M2 batch must contain exactly 10 images"
    mismatches: list[str] = []
    for path in paths:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        assert image is not None, f"failed to read {path}"
        predicted = analyze_image(image, CONFIG).label
        expected = expected_label_for(path)
        if predicted != expected:
            mismatches.append(f"{path.relative_to(RAW_ROOT)}: expected {expected}, got {predicted}")
    assert not mismatches, "\n".join(mismatches)
