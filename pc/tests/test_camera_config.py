import pytest

from pc.camera.config import CameraConfig


def valid_values() -> dict[str, object]:
    return {
        "device_name": "Insta360 Ace Pro 2",
        "fallback_index": None,
        "backend": "DSHOW",
        "requested_width": 1920,
        "requested_height": 1080,
        "requested_fps": 30.0,
        "fourcc": "MJPG",
        "warmup_frames": 15,
        "test_duration_seconds": 60.0,
        "reopen_cycles": 3,
        "minimum_read_success_rate": 0.99,
        "maximum_frame_gap_seconds": 2.0,
    }


def test_valid_config_is_accepted() -> None:
    config = CameraConfig.from_dict(valid_values())
    assert config.device_name == "Insta360 Ace Pro 2"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("requested_width", 0),
        ("requested_fps", 0),
        ("fourcc", "MJ"),
        ("test_duration_seconds", 0),
        ("reopen_cycles", 0),
        ("minimum_read_success_rate", 1.1),
        ("maximum_frame_gap_seconds", 0),
    ],
)
def test_invalid_values_are_rejected(field: str, value: object) -> None:
    values = valid_values()
    values[field] = value
    with pytest.raises(ValueError):
        CameraConfig.from_dict(values)


def test_missing_name_and_fallback_are_rejected() -> None:
    values = valid_values()
    values["device_name"] = ""
    values["fallback_index"] = None
    with pytest.raises(ValueError):
        CameraConfig.from_dict(values)
