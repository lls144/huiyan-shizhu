from pathlib import Path

from pc.camera import __main__ as camera_cli
from pc.camera.capture import _fourcc_text


def test_fourcc_text_keeps_printable_codes() -> None:
    assert _fourcc_text(float(0x32595559)) == "YUY2"  # 'Y' 'U' 'Y' '2'


def test_fourcc_text_falls_back_to_hex_when_the_backend_reports_no_fourcc() -> None:
    # MSMF answers with a non-printable code instead of a fourcc string.
    assert _fourcc_text(0x16) == "0x00000016"


def test_enumerate_command_does_not_require_duration(monkeypatch, capsys) -> None:
    config_path = Path("pc/config/camera.json")
    monkeypatch.setattr(
        "sys.argv",
        ["pc.camera", "--config", str(config_path), "enumerate"],
    )
    monkeypatch.setattr(camera_cli, "enumerate_camera_devices", lambda backend: [])

    assert camera_cli.main() == 0
    assert capsys.readouterr().out.strip() == "[]"
