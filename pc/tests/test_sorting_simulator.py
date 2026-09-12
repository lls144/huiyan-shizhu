"""Unit tests for the three-station conveyor sorting simulation."""

from __future__ import annotations

import pytest

from pc.events.models import EventType, VisionEvent
from pc.sorting.config import SortingConfig
from pc.sorting.model import (
    DONE,
    EJECTING,
    RIDING,
    STAGES,
    ConveyorSimulator,
    stage_index_for_label,
)


def make_config(**overrides: object) -> SortingConfig:
    values = {
        "belt_speed_units_per_second": 1.0,
        "min_gap_units": 0.30,
        "eject_seconds": 0.50,
        "max_pending_items": 4,
        "plc_trigger": "exit",
    }
    values.update(overrides)
    return SortingConfig(**values)  # type: ignore[arg-type]


def run_until_result(simulator: ConveyorSimulator, dt: float = 0.02, limit: int = 5000):
    for step in range(limit):
        results = simulator.advance(dt, frame_index=step)
        if results:
            return results
    raise AssertionError("the item never reached a station")


def test_station_order_and_lamp_mapping_is_the_frozen_shape_code() -> None:
    assert [stage.key for stage in STAGES] == ["triangle", "rectangle", "circle"]
    assert [stage.shape_code for stage in STAGES] == [1, 2, 3]
    assert [stage.lamp_count for stage in STAGES] == [1, 2, 3]
    assert stage_index_for_label("triangle") == 0
    assert stage_index_for_label("rectangle") == 1
    assert stage_index_for_label("circle") == 2
    assert stage_index_for_label("unknown") is None


@pytest.mark.parametrize(
    ("label", "stage_index", "lamp_count", "shape_code"),
    [
        ("triangle", 0, 1, 1),
        ("rectangle", 1, 2, 2),
        ("circle", 2, 3, 3),
    ],
)
def test_each_shape_is_ejected_at_its_own_station(
    label: str, stage_index: int, lamp_count: int, shape_code: int
) -> None:
    simulator = ConveyorSimulator(make_config())
    item = simulator.submit(label, semantic_id=41)
    assert item is not None
    assert item.stage_index == stage_index
    (result,) = run_until_result(simulator)
    assert result.label == label
    assert result.stage_index == stage_index
    assert result.lamp_count == lamp_count
    assert result.shape_code == shape_code
    assert result.lamps == tuple(index < lamp_count for index in range(3))
    assert result.semantic_id == 41
    assert simulator.lamp_state == result.lamps


def test_items_never_leave_the_belt_before_their_station() -> None:
    simulator = ConveyorSimulator(make_config())
    simulator.submit("circle", semantic_id=1)
    seen = []
    for step in range(500):
        simulator.advance(0.02, frame_index=step)
        views = simulator.snapshot().items
        seen.extend(view.progress for view in views)
        if not views:
            break
    assert seen
    assert max(seen) == pytest.approx(3.0)
    assert simulator.results[-1].stage_index == 2


def test_unknown_label_is_rejected_and_never_becomes_an_item() -> None:
    simulator = ConveyorSimulator(make_config())
    assert simulator.submit("unknown", semantic_id=7) is None
    assert simulator.snapshot().items == ()
    assert simulator.rejected_labels == ["unknown"]


def test_second_item_waits_at_the_entrance_until_the_belt_is_clear() -> None:
    simulator = ConveyorSimulator(make_config())
    simulator.submit("triangle", semantic_id=1)
    assert simulator.submit("rectangle", semantic_id=2) is None
    snapshot = simulator.snapshot()
    assert [item.label for item in snapshot.items] == ["triangle"]
    assert snapshot.pending_labels == ("rectangle",)
    # The waiting item is released once the first one has travelled far enough.
    for step in range(200):
        simulator.advance(0.02, frame_index=step)
        if not simulator.snapshot().pending_labels:
            break
    snapshot = simulator.snapshot()
    assert snapshot.pending_labels == ()
    assert {item.label for item in snapshot.items} == {"triangle", "rectangle"}
    progresses = sorted(item.progress for item in snapshot.items)
    assert progresses[1] - progresses[0] >= simulator.config.min_gap_units - 1e-9


def test_multiple_objects_share_one_lane_and_never_overtake() -> None:
    simulator = ConveyorSimulator(make_config())
    labels = ["circle", "triangle", "rectangle"]
    for index, label in enumerate(labels):
        simulator.submit(label, semantic_id=100 + index)
    completed: list[str] = []
    for step in range(5000):
        for result in simulator.advance(0.02, frame_index=step):
            completed.append(result.label)
        progresses = [
            view.progress
            for view in sorted(simulator.snapshot().items, key=lambda view: view.item_id)
        ]
        assert progresses == sorted(progresses, reverse=True)
        if len(completed) == len(labels):
            break
    # Items leave at their own station, so a triangle that entered second can
    # finish before a circle that entered first: stations are at different
    # distances. The lane still releases them in physical order.
    assert sorted(completed) == sorted(labels)
    assert [result.label for result in simulator.results] == completed
    assert [result.lamp_count for result in simulator.results] == [
        {"triangle": 1, "rectangle": 2, "circle": 3}[label] for label in completed
    ]


def test_simulation_is_deterministic_for_the_same_input_sequence() -> None:
    def scripted() -> list[tuple[str, int, int]]:
        simulator = ConveyorSimulator(make_config())
        simulator.submit("rectangle", semantic_id=5)
        completed = []
        for step in range(600):
            for result in simulator.advance(0.03, frame_index=step):
                completed.append((result.label, result.lamp_count, result.frame_index))
            if step == 40:
                simulator.submit("triangle", semantic_id=6)
        return completed

    assert scripted() == scripted()


def test_advance_with_zero_delta_does_not_move_the_item() -> None:
    simulator = ConveyorSimulator(make_config())
    simulator.submit("triangle", semantic_id=1)
    simulator.advance(0.2, frame_index=0)
    before = simulator.snapshot().items[0].progress
    simulator.advance(0.0, frame_index=1)
    assert simulator.snapshot().items[0].progress == before


def test_ejecting_state_is_reported_until_the_result_completes() -> None:
    simulator = ConveyorSimulator(make_config())
    simulator.submit("triangle", semantic_id=1)
    states = []
    for step in range(500):
        results = simulator.advance(0.02, frame_index=step)
        views = simulator.snapshot().items
        if views:
            states.append(views[0].state)
        if results:
            break
    assert RIDING in states
    assert EJECTING in states
    assert simulator.results[0].frame_index > 0
    assert DONE == "done"


def test_submit_events_only_reacts_to_confirmed_enter_events() -> None:
    simulator = ConveyorSimulator(make_config())
    events = (
        VisionEvent(1, EventType.OBJECT_EXIT, 3, "triangle", 0.9, 0),
        VisionEvent(2, EventType.OBJECT_ENTER, 4, "unknown", 0.9, 1),
        VisionEvent(3, EventType.OBJECT_ENTER, 5, "circle", 0.9, 2),
    )
    created = simulator.submit_events(events)
    assert [item.label for item in created] == ["circle"]
    assert simulator.rejected_labels == ["unknown"]
