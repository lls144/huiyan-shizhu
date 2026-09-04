import csv
import json
from pathlib import Path

from pc.events.config import load_event_config
from pc.events.reporting import (
    CSV_FIELDS,
    load_sequence_manifest,
    simulate_manifest,
    write_csv_report,
    write_json_report,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "pc/config/events.json"
MANIFEST_PATH = REPO_ROOT / "test_data/m4/detection-sequences.json"


def test_sequence_manifest_covers_required_m4_scenarios() -> None:
    manifest = load_sequence_manifest(MANIFEST_PATH)
    names = {scenario["name"] for scenario in manifest["scenarios"]}

    assert names == {
        "persistent_object",
        "single_frame_noise",
        "short_dropout",
        "true_removal",
        "reentry",
        "multi_class",
        "three_objects",
        "same_label_objects",
        "small_movement",
        "confidence_variation",
        "detection_order_change",
        "clear_all",
    }


def test_offline_event_report_is_serializable_and_all_scenarios_pass(
    tmp_path: Path,
) -> None:
    config = load_event_config(CONFIG_PATH)
    report = simulate_manifest(MANIFEST_PATH, config, CONFIG_PATH)
    json_path = tmp_path / "m4.json"
    csv_path = tmp_path / "m4.csv"
    write_json_report(report, json_path)
    write_csv_report(report, csv_path)

    round_trip = json.loads(json_path.read_text(encoding="utf-8"))
    assert round_trip["source_type"] == "offline_simulated_detection_sequence"
    assert round_trip["acceptance_status"] == "offline_simulation_validated"
    assert round_trip["summary"] == {
        "scenario_count": 12,
        "passing_scenarios": 12,
        "failing_scenarios": 0,
        "all_scenarios_pass": True,
        "live_camera_validation_complete": False,
    }
    assert round_trip["performance"]["frames"] == 300
    assert round_trip["performance"]["detections"] == 900
    assert round_trip["performance"]["events"] == 3
    assert round_trip["performance"]["processing_ms"] > 0
    assert all(result["scenario_pass"] for result in round_trip["results"])

    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    assert reader.fieldnames == CSV_FIELDS
    assert rows
    assert {row["source_type"] for row in rows} == {
        "offline_simulated_detection_sequence"
    }
    assert {row["scenario_pass"] for row in rows} == {"True"}
