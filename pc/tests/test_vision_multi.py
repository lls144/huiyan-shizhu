import json
from pathlib import Path

import cv2
import numpy as np

from pc.camera.config import load_camera_config
from pc.camera.devices import CameraDevice
from pc.events.adapters import detections_from_analysis
from pc.events.config import EventConfig
from pc.events.tracker import ObjectStateManager
from pc.vision.config import load_vision_config
from pc.vision.live import LiveCamera
from pc.vision.m3_live import analyze_preprocess_modes, save_m3_comparison_evidence
from pc.vision.pipeline import analyze_image, analyze_multiple_objects, annotated_multi_image
from pc.vision.roi import CalibrationResult, NormalizedRoi

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_vision_config(REPO_ROOT / "pc/config/vision.json")
CAMERA_CONFIG = load_camera_config(REPO_ROOT / "pc/config/camera.json")
FULL_ROI = NormalizedRoi(0.0, 0.0, 1.0, 1.0)


def _three_shape_scene(background: int = 245, foreground: int = 15) -> np.ndarray:
    image = np.full((800, 1200, 3), background, dtype=np.uint8)
    color = (foreground, foreground, foreground)
    cv2.fillPoly(
        image,
        [np.array([[200, 180], [90, 450], [310, 450]], dtype=np.int32)],
        color,
    )
    cv2.rectangle(image, (470, 210), (690, 430), color, -1)
    cv2.circle(image, (950, 325), 120, color, -1)
    return image


class FakeCapture:
    def get(self, property_id: int) -> float:
        return {
            cv2.CAP_PROP_FRAME_WIDTH: 1200.0,
            cv2.CAP_PROP_FRAME_HEIGHT: 800.0,
            cv2.CAP_PROP_FPS: 30.0,
        }.get(property_id, 0.0)

    def getBackendName(self) -> str:
        return "DSHOW"


def _camera() -> LiveCamera:
    device = CameraDevice(
        0,
        "Insta360 Ace Pro 2",
        "mock",
        0x2E1A,
        0x1003,
        "DSHOW",
        cv2.CAP_DSHOW,
    )
    return LiveCamera(FakeCapture(), device, CAMERA_CONFIG)  # type: ignore[arg-type]


def _calibration() -> CalibrationResult:
    return CalibrationResult(
        requested_mode="fixed_normalized",
        selected_mode="fixed_normalized",
        source="configured",
        roi=FULL_ROI,
        pixel_bounds=(0, 0, 1200, 800),
        fallback_messages=(),
    )


def test_three_separated_shapes_are_returned_independently_left_to_right() -> None:
    result = analyze_multiple_objects(_three_shape_scene(), CONFIG, FULL_ROI)

    assert [detection.label for detection in result.detections] == [
        "triangle",
        "rectangle",
        "circle",
    ]
    assert len(result.detections) == 3
    assert all(detection.confidence > 0 for detection in result.detections)
    assert [detection.center[0] for detection in result.detections if detection.center] == sorted(
        detection.center[0] for detection in result.detections if detection.center
    )


def test_m2_single_object_entry_still_selects_only_the_largest_valid_contour() -> None:
    image = _three_shape_scene()
    single = analyze_image(image, CONFIG, FULL_ROI)
    multi = analyze_multiple_objects(image, CONFIG, FULL_ROI)

    assert single.selected_candidate is not None
    assert len(multi.detections) == 3
    assert single.selected_candidate.features.area == max(
        detection.candidate.features.area for detection in multi.detections
    )


def test_otsu_and_clahe_otsu_process_the_same_dim_scene() -> None:
    analyses = analyze_preprocess_modes(
        _three_shape_scene(background=105, foreground=10),
        CONFIG,
        FULL_ROI,
    )

    assert set(analyses) == {"otsu", "clahe_otsu"}
    for mode, analysis in analyses.items():
        assert analysis.preprocessing.preprocess_mode == mode
        assert [detection.label for detection in analysis.detections] == [
            "triangle",
            "rectangle",
            "circle",
        ]


def test_touching_shapes_are_not_falsely_split_by_m3() -> None:
    image = np.full((600, 800, 3), 245, dtype=np.uint8)
    cv2.rectangle(image, (230, 190), (440, 410), (10, 10, 10), -1)
    cv2.circle(image, (470, 300), 120, (10, 10, 10), -1)

    result = analyze_multiple_objects(image, CONFIG, FULL_ROI)

    assert len(result.detections) <= 1


def test_multi_annotation_preserves_frame_size() -> None:
    image = _three_shape_scene()
    analysis = analyze_multiple_objects(image, CONFIG, FULL_ROI)

    annotated = annotated_multi_image(image, analysis)

    assert annotated.shape == image.shape
    assert not np.array_equal(annotated, image)


def test_m3_evidence_saves_same_frame_method_pair_as_pending(
    tmp_path: Path,
    monkeypatch,
) -> None:
    frame = _three_shape_scene()
    analyses = analyze_preprocess_modes(frame, CONFIG, FULL_ROI)
    manager = ObjectStateManager(EventConfig())
    manager.process_frame(0, detections_from_analysis(analyses["otsu"], 0))
    event_update = manager.process_frame(
        1,
        detections_from_analysis(analyses["otsu"], 1),
    )
    monkeypatch.setattr(
        "pc.vision.m3_live._git_state",
        lambda: {"commit": "mock", "dirty": True},
    )

    json_path = save_m3_comparison_evidence(
        frame,
        analyses,
        "normal_light",
        ("triangle", "rectangle", "circle"),
        _calibration(),
        _camera(),
        CONFIG,
        tmp_path,
        event_update,
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["milestone"] == "M3"
    assert payload["acceptance_status"] == "pending_user_validation"
    assert payload["scenario"] == "normal_light"
    assert set(payload["methods"]) == {"otsu", "clahe_otsu"}
    assert all(record["object_count"] == 3 for record in payload["methods"].values())
    assert all(record["matches_expected_labels"] for record in payload["methods"].values())
    assert [event["event_type"] for event in payload["m4_event_snapshot"]["events"]] == [
        "OBJECT_ENTER",
        "OBJECT_ENTER",
        "OBJECT_ENTER",
    ]
    assert (json_path.parent / "comparison.csv").is_file()
    assert len(list(json_path.parent.iterdir())) == 12
