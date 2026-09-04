from pathlib import Path

import cv2
import numpy as np
import pytest

from pc.vision.config import load_vision_config
from pc.vision.roi import (
    CalibrationResult,
    NormalizedRoi,
    calibrate_roi,
    detect_auto_roi,
    fixed_roi,
    load_runtime_calibration,
    save_runtime_calibration,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_vision_config(REPO_ROOT / "pc/config/vision.json")


def test_normalized_roi_converts_to_resolution_specific_pixels() -> None:
    roi = NormalizedRoi(0.24, 0.08, 0.76, 0.75)
    assert roi.to_pixels((1080, 1920, 3)) == (461, 86, 1459, 810)
    assert roi.to_pixels((720, 1280, 3)) == (307, 58, 973, 540)


@pytest.mark.parametrize(
    "values",
    [
        (-0.1, 0.1, 0.8, 0.9),
        (0.7, 0.1, 0.6, 0.9),
        (0.1, 0.9, 0.8, 0.8),
        (0.1, 0.2, 1.1, 0.9),
    ],
)
def test_invalid_normalized_roi_is_rejected(values: tuple[float, float, float, float]) -> None:
    with pytest.raises(ValueError):
        NormalizedRoi(*values)


def _synthetic_white_board() -> np.ndarray:
    frame = np.full((600, 800, 3), 70, dtype=np.uint8)
    cv2.rectangle(frame, (150, 90), (650, 520), (235, 235, 235), -1)
    cv2.circle(frame, (420, 310), 75, (15, 15, 15), -1)
    return frame


def test_auto_roi_detects_synthetic_board_with_dark_target_present() -> None:
    result = detect_auto_roi(_synthetic_white_board(), CONFIG)
    assert result.success, result.reason
    assert result.roi is not None
    left, top, right, bottom = result.roi.to_pixels((600, 800, 3))
    assert 150 < left < 220
    assert 90 < top < 150
    assert 580 < right < 650
    assert 460 < bottom < 520
    assert left < 420 < right and top < 310 < bottom


def test_auto_roi_reports_explicit_failure_when_board_is_absent() -> None:
    frame = np.full((600, 800, 3), 60, dtype=np.uint8)
    result = detect_auto_roi(frame, CONFIG)
    assert not result.success
    assert result.roi is None
    assert "no acceptable" in result.reason


def test_auto_falls_back_to_manual_selection() -> None:
    frame = np.full((600, 800, 3), 60, dtype=np.uint8)
    messages: list[str] = []
    result = calibrate_roi(
        frame,
        CONFIG,
        "auto",
        lambda _: (120, 100, 500, 380),
        messages.append,
    )
    assert result.selected_mode == "manual"
    assert result.source == "selected"
    assert result.pixel_bounds == (120, 100, 620, 480)
    assert result.fallback_messages
    assert any("auto ROI failed" in message for message in messages)


def test_auto_then_cancelled_manual_uses_fixed_fallback_explicitly() -> None:
    frame = np.full((600, 800, 3), 60, dtype=np.uint8)
    messages: list[str] = []
    result = calibrate_roi(frame, CONFIG, "auto", lambda _: None, messages.append)
    assert result.selected_mode == "fixed_normalized"
    assert result.source == "configured_fallback"
    assert result.roi == fixed_roi(CONFIG)
    assert len(result.fallback_messages) == 2
    assert any("fixed_normalized fallback" in message for message in messages)


def test_manual_runtime_calibration_can_be_saved_and_restored(tmp_path: Path) -> None:
    frame_shape = (600, 800, 3)
    roi = NormalizedRoi.from_pixel_rect(120, 100, 500, 380, frame_shape)
    calibration = CalibrationResult(
        requested_mode="manual",
        selected_mode="manual",
        source="selected",
        roi=roi,
        pixel_bounds=roi.to_pixels(frame_shape),
        fallback_messages=(),
    )
    path = tmp_path / "runtime-calibration.json"

    save_runtime_calibration(calibration, frame_shape, path)
    restored = load_runtime_calibration(path, (1080, 1920, 3))

    assert path.exists()
    assert restored.source == "restored"
    assert restored.roi == roi
    assert restored.pixel_bounds == roi.to_pixels((1080, 1920, 3))
