import numpy as np

from pc.gui.models import GuiSnapshot
from pc.gui.worker import LatestSnapshotBuffer


def _snapshot(frame_index: int) -> GuiSnapshot:
    return GuiSnapshot(
        frame_index=frame_index,
        timestamp="2026-09-04T00:00:00+08:00",
        annotated_frame=np.zeros((8, 12, 3), dtype=np.uint8),
        detections=(),
        tracked_objects=(),
        events=(),
        source_type="synthetic",
        source_status="running",
        processed_fps=20.0,
        processing_ms=4.0,
        roi_bounds=(0, 0, 12, 8),
        roi_mode="fixed_normalized",
        roi_source="configured",
        preprocess_method="otsu",
    )


def test_latest_snapshot_buffer_is_bounded_and_latest_wins() -> None:
    buffer = LatestSnapshotBuffer()

    assert buffer.publish(_snapshot(1)) is True
    assert buffer.publish(_snapshot(2)) is False
    assert buffer.publish(_snapshot(3)) is False

    assert buffer.take_latest().frame_index == 3  # type: ignore[union-attr]
    assert buffer.overwritten_count == 2
    assert buffer.published_count == 3
    assert buffer.consumed_count == 1
    assert buffer.take_latest() is None


def test_consumption_rearms_exactly_one_ui_notification() -> None:
    buffer = LatestSnapshotBuffer()

    assert buffer.publish(_snapshot(1)) is True
    assert buffer.take_latest() is not None
    assert buffer.publish(_snapshot(2)) is True
