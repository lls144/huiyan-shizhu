import json
from pathlib import Path

import cv2
import numpy as np

from pc.camera.config import load_camera_config
from pc.camera.devices import CameraDevice
from pc.vision.config import load_vision_config
from pc.vision.live import (
    LiveCamera,
    StableLabelFilter,
    open_live_camera,
    process_live_frame,
    render_live_overlay,
    save_live_evidence,
)
from pc.vision.pipeline import analyze_image
from pc.vision.roi import CalibrationResult, fixed_roi

REPO_ROOT = Path(__file__).resolve().parents[2]
VISION_CONFIG = load_vision_config(REPO_ROOT / "pc/config/vision.json")
CAMERA_CONFIG = load_camera_config(REPO_ROOT / "pc/config/camera.json")


def _device() -> CameraDevice:
    return CameraDevice(1, "Insta360 Ace Pro 2", "mock", 0x2E1A, 0x1003, "DSHOW", cv2.CAP_DSHOW)


class FakeCapture:
    def get(self, property_id: int) -> float:
        return {
            cv2.CAP_PROP_FRAME_WIDTH: 1920.0,
            cv2.CAP_PROP_FRAME_HEIGHT: 1080.0,
            cv2.CAP_PROP_FPS: 30.0,
        }.get(property_id, 0.0)

    def getBackendName(self) -> str:
        return "DSHOW"


def test_live_camera_opening_reuses_m1_functions(monkeypatch) -> None:
    device = _device()
    capture = FakeCapture()
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr("pc.vision.live.load_camera_config", lambda _: CAMERA_CONFIG)
    monkeypatch.setattr(
        "pc.vision.live.enumerate_camera_devices",
        lambda backend: calls.append(("enumerate", backend)) or [device],
    )
    monkeypatch.setattr(
        "pc.vision.live.select_camera_device",
        lambda devices, name, fallback: calls.append(("select", tuple(devices), name, fallback)) or device,
    )
    monkeypatch.setattr(
        "pc.vision.live.open_configured_camera",
        lambda selected, config: calls.append(("open", selected, config)) or capture,
    )

    opened = open_live_camera(Path("camera.json"))

    assert opened.capture is capture
    assert opened.device is device
    assert [call[0] for call in calls] == ["enumerate", "select", "open"]


def test_live_frame_and_offline_frame_use_the_same_core_pipeline() -> None:
    frame = np.full((600, 800, 3), 255, dtype=np.uint8)
    cv2.fillPoly(frame, [np.array([[400, 110], [280, 410], [520, 410]], np.int32)], (0, 0, 0))
    roi = fixed_roi(VISION_CONFIG)

    offline = analyze_image(frame, VISION_CONFIG, roi)
    live = process_live_frame(frame, VISION_CONFIG, roi)

    assert live.to_record() == offline.to_record()
    assert live.label == "triangle"


def test_stable_label_filter_requires_configured_majority() -> None:
    stabilizer = StableLabelFilter(window_size=5, minimum_votes=3)
    assert stabilizer.update("triangle") == "no_object"
    assert stabilizer.update("circle") == "no_object"
    assert stabilizer.update("triangle") == "no_object"
    assert stabilizer.update("triangle") == "triangle"
    assert stabilizer.update("circle") == "triangle"
    assert stabilizer.update("circle") == "circle"


def test_s_key_evidence_payload_writes_requested_artifacts(tmp_path: Path, monkeypatch) -> None:
    frame = np.full((600, 800, 3), 255, dtype=np.uint8)
    cv2.circle(frame, (400, 280), 110, (0, 0, 0), -1)
    roi = fixed_roi(VISION_CONFIG)
    analysis = process_live_frame(frame, VISION_CONFIG, roi)
    calibration = CalibrationResult(
        requested_mode="fixed_normalized",
        selected_mode="fixed_normalized",
        source="configured",
        roi=roi,
        pixel_bounds=roi.to_pixels(frame.shape),
        fallback_messages=(),
    )
    camera = LiveCamera(FakeCapture(), _device(), CAMERA_CONFIG)  # type: ignore[arg-type]
    annotated = render_live_overlay(frame, analysis, analysis.label, 29.7, calibration)
    monkeypatch.setattr("pc.vision.live._git_state", lambda: {"commit": "mock", "dirty": True})

    json_path = save_live_evidence(
        frame,
        analysis,
        annotated,
        analysis.label,
        29.7,
        calibration,
        camera,
        VISION_CONFIG,
        tmp_path,
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["predicted_class"] == "circle"
    assert payload["roi_mode"] == "fixed_normalized"
    assert payload["center"] is not None
    assert {path.name for path in json_path.parent.iterdir()} == {
        "frame.jpg",
        "roi.jpg",
        "binary.png",
        "canny.png",
        "annotated.jpg",
        "evidence.json",
    }
