from pathlib import Path

import cv2
import numpy as np

from pc.events.adapters import detections_from_analysis
from pc.events.config import load_event_config
from pc.events.tracker import ObjectStateManager
from pc.gui.overlay import annotated_gui_frame
from pc.gui.theme import OVERLAY
from pc.vision.config import load_vision_config
from pc.vision.pipeline import analyze_multiple_objects
from pc.vision.roi import fixed_roi

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_gui_overlay_is_id_aware_and_does_not_mutate_source(monkeypatch) -> None:
    config = load_vision_config(REPO_ROOT / "pc/config/vision.json")
    event_config = load_event_config(REPO_ROOT / "pc/config/events.json")
    source = cv2.imread(str(REPO_ROOT / "test_data/m3/synthetic/multi_normal.png"))
    assert source is not None
    before = source.copy()
    analysis = analyze_multiple_objects(source, config, fixed_roi(config))
    detections = detections_from_analysis(analysis, 0)
    update = ObjectStateManager(event_config).process_frame(0, detections)
    drawn_labels: list[str] = []
    real_put_text = cv2.putText

    def capture_text(image, text, *args, **kwargs):
        drawn_labels.append(text)
        return real_put_text(image, text, *args, **kwargs)

    monkeypatch.setattr(cv2, "putText", capture_text)
    output = annotated_gui_frame(source, analysis, detections, update.object_states)

    assert np.array_equal(source, before)
    assert not np.array_equal(output, source)
    assert [label.split()[1] for label in drawn_labels] == [
        "TRIANGLE",
        "RECTANGLE",
        "CIRCLE",
    ]
    assert [label.split()[0] for label in drawn_labels] == ["#1", "#2", "#3"]
    assert all(label.endswith("%") for label in drawn_labels)


def test_gui_overlay_uses_subdued_roi_token() -> None:
    config = load_vision_config(REPO_ROOT / "pc/config/vision.json")
    source = cv2.imread(str(REPO_ROOT / "test_data/m3/synthetic/multi_normal.png"))
    assert source is not None
    analysis = analyze_multiple_objects(source, config, fixed_roi(config))
    detections = detections_from_analysis(analysis, 0)
    output = annotated_gui_frame(source, analysis, detections, ())
    left, top, _, _ = analysis.preprocessing.roi_bounds

    roi_pixel = tuple(int(value) for value in output[top, left])
    assert roi_pixel[0] == roi_pixel[1] == roi_pixel[2]
    assert OVERLAY.roi_bgr[0] <= roi_pixel[0] < int(source[top, left, 0])
    assert OVERLAY.roi_thickness == 1
