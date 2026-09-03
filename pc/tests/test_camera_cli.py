from pathlib import Path

from pc.camera import __main__ as camera_cli


def test_enumerate_command_does_not_require_duration(monkeypatch, capsys) -> None:
    config_path = Path("pc/config/camera.json")
    monkeypatch.setattr(
        "sys.argv",
        ["pc.camera", "--config", str(config_path), "enumerate"],
    )
    monkeypatch.setattr(camera_cli, "enumerate_camera_devices", lambda backend: [])

    assert camera_cli.main() == 0
    assert capsys.readouterr().out.strip() == "[]"
