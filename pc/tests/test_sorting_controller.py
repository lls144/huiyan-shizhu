"""Unit tests for the sorting controller and its PLC trigger semantics."""

from __future__ import annotations

from pc.communication.models import PlcCommandResult, PlcCommandStatus
from pc.communication.sink import RecordingPlcSink
from pc.events.models import EventType, VisionEvent
from pc.sorting.config import SortingConfig
from pc.sorting.controller import SortingController


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


def enter(event_id: int, label: str, object_id: int) -> VisionEvent:
    return VisionEvent(event_id, EventType.OBJECT_ENTER, object_id, label, 0.95, 0)


def drain(controller: SortingController, dt: float = 0.02, limit: int = 5000) -> None:
    for step in range(limit):
        controller.advance(dt, frame_index=step)
        if not controller.snapshot().items:
            return
    raise AssertionError("simulation never drained")


def test_exit_trigger_writes_to_the_plc_only_after_the_station_ejects() -> None:
    sink = RecordingPlcSink()
    controller = SortingController(make_config(plc_trigger="exit"), sink)
    controller.submit_events((enter(1, "rectangle", 11),))
    assert sink.commands == []  # nothing written while the block is still riding
    drain(controller)
    assert [command.shape for command in sink.commands] == ["rectangle"]
    assert sink.commands[0].shape_code == 2
    assert controller.plc_command_count == 1


def test_enter_trigger_writes_to_the_plc_at_recognition_time() -> None:
    sink = RecordingPlcSink()
    controller = SortingController(make_config(plc_trigger="enter"), sink)
    controller.submit_events((enter(1, "circle", 12),))
    assert [command.shape for command in sink.commands] == ["circle"]
    assert sink.commands[0].shape_code == 3


def test_unknown_events_never_reach_the_plc() -> None:
    sink = RecordingPlcSink()
    controller = SortingController(make_config(), sink)
    controller.submit_events((enter(1, "unknown", 13),))
    drain(controller)
    assert sink.commands == []
    assert controller.plc_command_count == 0


def test_three_shapes_produce_the_frozen_lamp_counts_in_fifo_order() -> None:
    sink = RecordingPlcSink()
    controller = SortingController(make_config(), sink)
    controller.submit_events(
        (enter(1, "triangle", 1), enter(2, "rectangle", 2), enter(3, "circle", 3))
    )
    for step in range(5000):
        controller.advance(0.02, frame_index=step)
        if len(controller.simulator.results) == 3:
            break
    assert [command.shape for command in sink.commands] == ["triangle", "rectangle", "circle"]
    assert [command.shape_code for command in sink.commands] == [1, 2, 3]
    assert [result.lamp_count for result in controller.simulator.results] == [1, 2, 3]


class _FailingSink:
    def start(self) -> None:
        return None

    def send_event(self, event: VisionEvent) -> PlcCommandResult:
        raise RuntimeError("s7 link down")

    def dequeue(self) -> PlcCommandResult:
        raise RuntimeError("s7 link down")

    def reset(self) -> PlcCommandResult:
        raise RuntimeError("s7 link down")

    def stop(self) -> None:
        return None


def test_sink_failure_is_captured_without_losing_the_sorting_result() -> None:
    controller = SortingController(make_config(), _FailingSink())
    controller.submit_events((enter(1, "triangle", 21),))
    drain(controller)
    assert len(controller.simulator.results) == 1
    assert controller.plc_error is not None
    assert "s7 link down" in controller.plc_error
    assert controller.plc_results[-1].status is PlcCommandStatus.ERROR


def test_disabled_plc_still_runs_the_animation() -> None:
    controller = SortingController(make_config(), None)
    controller.submit_events((enter(1, "triangle", 31),))
    drain(controller)
    assert controller.plc_results == []
    assert controller.plc_command_count == 0
    assert controller.simulator.results[0].lamp_count == 1
