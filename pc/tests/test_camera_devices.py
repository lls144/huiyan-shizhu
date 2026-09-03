import cv2
import pytest

from pc.camera.devices import CameraDevice, select_camera_device


DEVICES = [
    CameraDevice(0, "Integrated Camera", "path-0", 1, 2, "DSHOW", cv2.CAP_DSHOW),
    CameraDevice(1, "Insta360 Ace Pro 2", "path-1", 3, 4, "DSHOW", cv2.CAP_DSHOW),
]


def test_selects_preferred_name_before_fallback() -> None:
    selected = select_camera_device(DEVICES, "insta360", 0)
    assert selected.index == 1


def test_uses_configured_fallback_when_name_is_missing() -> None:
    selected = select_camera_device(DEVICES, "missing", 0)
    assert selected.name == "Integrated Camera"


def test_missing_device_reports_detected_cameras() -> None:
    with pytest.raises(RuntimeError, match="0:Integrated Camera"):
        select_camera_device(DEVICES, "missing", None)
