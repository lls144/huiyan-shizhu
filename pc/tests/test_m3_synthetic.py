import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import cv2

from pc.vision.config import load_vision_config
from pc.vision.m3_reporting import (
    CSV_FIELDS,
    evaluate_synthetic_dataset,
    write_m3_csv_report,
    write_m3_json_report,
)
from pc.vision.pipeline import analyze_multiple_objects
from pc.vision.synthetic import IMAGE_HEIGHT, IMAGE_WIDTH, generate_synthetic_dataset

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = REPO_ROOT / "test_data/m3/synthetic"
GROUND_TRUTH_PATH = DATASET_ROOT / "ground_truth.json"
CONFIG_PATH = REPO_ROOT / "pc/config/vision.json"
CONFIG = load_vision_config(CONFIG_PATH)
EXPECTED_FILES = {
    "multi_normal.png",
    "multi_bright.png",
    "multi_dark.png",
    "multi_side_light.png",
    "multi_occlusion.png",
    "multi_touching.png",
    "ground_truth.json",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_committed_synthetic_dataset_is_complete_and_deterministic(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    manifest = generate_synthetic_dataset(generated)

    assert {path.name for path in DATASET_ROOT.iterdir()} == EXPECTED_FILES
    assert {path.name for path in generated.iterdir()} == EXPECTED_FILES
    assert manifest["source_type"] == "synthetic"
    assert manifest["deterministic"] is True
    assert manifest["seed"] == 0
    assert len(manifest["scenes"]) == 6
    for name in EXPECTED_FILES:
        assert _sha256(generated / name) == _sha256(DATASET_ROOT / name)


def test_ground_truth_has_geometry_illumination_and_relation_metadata() -> None:
    manifest = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))

    for scene in manifest["scenes"]:
        assert scene["image_size"] == {"width": IMAGE_WIDTH, "height": IMAGE_HEIGHT}
        assert scene["expected_count"] == len(scene["objects"])
        assert scene["expected_labels"] == [item["label"] for item in scene["objects"]]
        assert scene["illumination"]["model"]
        for item in scene["objects"]:
            assert item["polygon"]
            assert len(item["center"]) == 2
            assert len(item["bbox"]) == 4
    relations = {scene["scene"]: scene["relations"] for scene in manifest["scenes"]}
    assert relations["partial_occlusion"][0]["type"] == "overlap"
    assert relations["touching"][0]["type"] == "edge_contact"


def test_normal_fixture_detects_all_three_shapes_with_both_modes() -> None:
    image = cv2.imread(str(DATASET_ROOT / "multi_normal.png"), cv2.IMREAD_COLOR)
    assert image is not None

    for mode in (CONFIG.preprocess_mode, CONFIG.comparison_preprocess_mode):
        mode_config = replace(CONFIG, preprocess_mode=mode)
        analysis = analyze_multiple_objects(image, mode_config)
        assert analysis.preprocessing.preprocess_mode == mode
        assert [item.label for item in analysis.detections] == [
            "triangle",
            "rectangle",
            "circle",
        ]


def test_offline_report_is_serializable_and_has_standard_schema(tmp_path: Path) -> None:
    report = evaluate_synthetic_dataset(
        DATASET_ROOT,
        GROUND_TRUTH_PATH,
        CONFIG,
        CONFIG_PATH,
        tmp_path / "diagnostics",
    )
    output_json = tmp_path / "results.json"
    output_csv = tmp_path / "results.csv"
    write_m3_json_report(report, output_json)
    write_m3_csv_report(report, output_csv)

    round_trip = json.loads(output_json.read_text(encoding="utf-8"))
    assert round_trip["source_type"] == "synthetic"
    assert round_trip["summary"]["all_required_scenes_pass"] is True
    assert round_trip["summary"]["live_camera_validation_complete"] is False
    assert len(round_trip["results"]) == 6
    assert set(round_trip["results"][0]["methods"]) == {"otsu", "clahe_otsu"}
    for scene in round_trip["results"]:
        for method in scene["methods"].values():
            assert {
                "object_count",
                "predicted_labels",
                "processing_ms",
                "objects",
                "count_matches",
                "labels_match",
            } <= method.keys()
            for item in method["objects"]:
                assert {"confidence", "features", "predicted_label"} <= item.keys()
                assert {
                    "bounding_box",
                    "area_ratio",
                    "solidity",
                    "circularity",
                } <= item["features"].keys()

    with output_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    assert reader.fieldnames == CSV_FIELDS
    assert rows
    assert {row["source_type"] for row in rows} == {"synthetic"}
    assert len(list((tmp_path / "diagnostics").glob("*.png"))) == 12


def test_overlap_and_touching_are_recorded_as_diagnostics_not_forced_passes() -> None:
    report = evaluate_synthetic_dataset(
        DATASET_ROOT,
        GROUND_TRUTH_PATH,
        CONFIG,
        CONFIG_PATH,
    )
    diagnostic_scenes = {
        scene["scene"]: scene
        for scene in report["results"]
        if scene["evaluation_kind"] == "diagnostic_only"
    }

    assert set(diagnostic_scenes) == {"partial_occlusion", "touching"}
    for scene in diagnostic_scenes.values():
        assert scene["required_scene_pass"] is None
        assert all(method["method_pass"] is None for method in scene["methods"].values())
        assert all(method["object_count"] < 3 for method in scene["methods"].values())
