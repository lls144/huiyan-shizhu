"""Tests for the PC-side reliability layer (queue full, dedup, timeouts)."""

from __future__ import annotations

from pc.communication.config import PlcCommunicationConfig
from pc.communication.fake_plc import FakeAcceptancePlc
from pc.communication.models import PlcCommandResult, PlcCommandStatus, PlcState
from pc.communication.reliability import GuardedPlcSink
from pc.communication.sink import S7PlcCommandSink
from pc.events.models import EventType, VisionEvent
from pc.sorting.config import SortingConfig
from pc.sorting.controller import SortingController


def make_config(**overrides: object) -> PlcCommunicationConfig:
    values: dict[str, object] = {
        "enabled": True,
        "db_number": 12,
        "auto_dequeue": False,
        "command_pulse_seconds": 0.0,
        "dequeue_pulse_seconds": 0.0,
        "reset_pulse_seconds": 0.0,
        "write_confirm_interval_seconds": 0.0,
        "queue_full_policy": "defer",
        "duplicate_policy": "refuse",
        "command_timeout_seconds": 3.0,
    }
    values.update(overrides)
    return PlcCommunicationConfig(**values)  # type: ignore[arg-type]


def guarded(config: PlcCommunicationConfig, plc: FakeAcceptancePlc) -> GuardedPlcSink:
    sink = GuardedPlcSink(S7PlcCommandSink(config, low_level=plc), config)
    sink.start()
    return sink


def enter(label: str, semantic_id: int) -> VisionEvent:
    return VisionEvent(
        event_id=semantic_id,
        event_type=EventType.OBJECT_ENTER,
        object_id=semantic_id,
        label=label,
        confidence=0.95,
        frame_index=0,
    )


class _StubInner:
    """Inner sink whose 'write' succeeds but whose queue never grows."""

    def __init__(self, state: PlcState, detail: str = "pretend write") -> None:
        self.state = state
        self.detail = detail
        self.write_retry_count = 0

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def send_event(self, event: VisionEvent) -> PlcCommandResult:
        return PlcCommandResult(None, PlcCommandStatus.SENT, detail=self.detail)

    def dequeue(self) -> PlcCommandResult:
        return PlcCommandResult(None, PlcCommandStatus.SENT)

    def reset(self) -> PlcCommandResult:
        return PlcCommandResult(None, PlcCommandStatus.SENT)

    def read_state(self) -> PlcState:
        return self.state


def _state(queue_length: int, capacity: int = 3) -> PlcState:
    return PlcState(
        acceptance_ready=True,
        queue_empty=queue_length == 0,
        queue_full=queue_length >= capacity,
        leds=(False, False, False),
        last_dequeued_valid=False,
        queue_length=queue_length,
        last_dequeued_shape=0,
        last_dequeued_semantic_id=0,
        cycle_counter=1,
        layout_magic=0x4D38,
        layout_version=1,
    )


def test_confirmed_send_reports_the_queue_growth() -> None:
    sink = guarded(make_config(), FakeAcceptancePlc())
    result = sink.send_event(enter("triangle", 1))
    assert result.status is PlcCommandStatus.SENT
    assert result.confirmed is True
    assert (result.queue_length_before, result.queue_length) == (0, 1)
    assert sink.counters.sent_confirmed == 1
    assert sink.sent_semantic_ids == {1}


def test_same_semantic_id_is_never_written_twice() -> None:
    sink = guarded(make_config(), FakeAcceptancePlc())
    sink.send_event(enter("triangle", 7))
    again = sink.send_event(enter("triangle", 7))
    assert again.status is PlcCommandStatus.DUPLICATE
    assert sink.counters.duplicate_rejections == 1
    assert sink.counters.sent_confirmed == 1
    assert sink.status().queue_length == 1  # a resend can never double-enqueue


def test_duplicate_policy_allow_keeps_the_old_behaviour() -> None:
    sink = guarded(make_config(duplicate_policy="allow"), FakeAcceptancePlc())
    sink.send_event(enter("triangle", 7))
    sink.send_event(enter("triangle", 7))
    assert sink.status().queue_length == 2


def test_full_queue_defers_instead_of_losing_the_item() -> None:
    plc = FakeAcceptancePlc(capacity=3)
    sink = guarded(make_config(), plc)
    for index in range(3):
        assert sink.send_event(enter("circle", 10 + index)).status is PlcCommandStatus.SENT
    blocked = sink.send_event(enter("triangle", 99))
    assert blocked.status is PlcCommandStatus.QUEUE_FULL
    assert blocked.detail.startswith("PLC queue is full")
    assert sink.status().queue_full is True
    assert sink.status().deferred_count == 1
    assert sink.counters.queue_full_deferrals == 1

    sink.dequeue()  # the physical button frees one slot
    flushed = sink.flush_deferred()
    assert [item.status for item in flushed] == [PlcCommandStatus.SENT]
    assert sink.status().deferred_count == 0
    assert sink.status().queue_length == 3


def test_full_queue_can_be_dropped_by_policy() -> None:
    sink = guarded(make_config(queue_full_policy="drop"), FakeAcceptancePlc(capacity=1))
    sink.send_event(enter("circle", 1))
    blocked = sink.send_event(enter("triangle", 2))
    assert blocked.status is PlcCommandStatus.QUEUE_FULL
    assert sink.counters.queue_full_drops == 1
    assert sink.status().deferred_count == 0


def test_a_deferred_item_survives_repeated_flush_attempts() -> None:
    sink = guarded(make_config(), FakeAcceptancePlc(capacity=1))
    sink.send_event(enter("circle", 1))
    sink.send_event(enter("triangle", 2))
    for _ in range(3):
        results = sink.flush_deferred()
        assert [item.status for item in results] == [PlcCommandStatus.QUEUE_FULL]
    assert sink.status().deferred_count == 1
    assert sink.counters.queue_full_deferrals == 1  # counted once, not per retry
    assert sink.counters.deferred_retries == 3
    sink.dequeue()
    assert [item.status for item in sink.flush_deferred()] == [PlcCommandStatus.SENT]
    assert sink.status().deferred_count == 0


def test_dropped_control_writes_are_resent_until_confirmed() -> None:
    plc = FakeAcceptancePlc(drop_control_writes=4)
    sink = guarded(make_config(), plc)
    result = sink.send_event(enter("rectangle", 5))
    assert result.status is PlcCommandStatus.SENT
    assert result.resends >= 1
    assert sink.counters.write_resends >= 1
    assert sink.status().queue_length == 1


def test_write_that_does_not_grow_the_queue_is_unconfirmed() -> None:
    sink = GuardedPlcSink(_StubInner(_state(0)), make_config())
    result = sink.send_event(enter("circle", 3))
    assert result.status is PlcCommandStatus.UNCONFIRMED
    assert sink.counters.unconfirmed == 1
    assert sink.sent_semantic_ids == set()
    assert "did not grow" in result.detail


def test_never_confirmed_write_is_counted_as_a_timeout() -> None:
    stub = _StubInner(
        _state(0),
        detail="control write to DB12 was never confirmed after 12 attempts",
    )

    def failing(event: VisionEvent) -> PlcCommandResult:
        return PlcCommandResult(None, PlcCommandStatus.ERROR, detail=stub.detail)

    stub.send_event = failing  # type: ignore[method-assign]
    sink = GuardedPlcSink(stub, make_config())
    result = sink.send_event(enter("triangle", 4))
    assert result.status is PlcCommandStatus.ERROR
    assert sink.counters.timeouts == 1
    assert sink.counters.errors == 1


def test_reset_clears_deferred_items_and_the_duplicate_guard() -> None:
    sink = guarded(make_config(), FakeAcceptancePlc(capacity=1))
    sink.send_event(enter("circle", 1))
    sink.send_event(enter("triangle", 2))
    assert sink.status().deferred_count == 1
    sink.reset()
    assert sink.status().deferred_count == 0
    assert sink.sent_semantic_ids == set()
    assert sink.status().queue_length == 0
    assert sink.send_event(enter("triangle", 2)).status is PlcCommandStatus.SENT


def test_two_objects_in_one_frame_both_enter_the_plc_queue() -> None:
    plc = FakeAcceptancePlc(capacity=3)
    sink = guarded(make_config(), plc)
    sorting = SortingConfig(plc_trigger="enter")
    controller = SortingController(sorting, sink)
    controller.submit_events((enter("triangle", 11), enter("circle", 12)))
    # The second object is recognized at the same time, but it waits in the
    # intake buffer until the lane is clear, so its command follows a moment later.
    assert sink.status().queue_length == 1
    assert controller.simulator.snapshot().pending_labels == ("circle",)
    for step in range(400):
        controller.advance(0.05, frame_index=step)
        if sink.status().queue_length == 2:
            break
    assert sink.status().queue_length == 2
    assert [shape for shape, _ in plc.queue] == [1, 3]


def test_auto_dequeue_is_still_reported_as_confirmed() -> None:
    # With auto_dequeue the queue is drained inside send_event, so the length can
    # return to its previous value; the dequeued semantic id must still confirm.
    sink = guarded(make_config(auto_dequeue=True), FakeAcceptancePlc(capacity=3))
    for index, (label, code) in enumerate(
        (("triangle", 1), ("rectangle", 2), ("circle", 3))
    ):
        result = sink.send_event(enter(label, 100 + index))
        assert result.status is PlcCommandStatus.SENT, result.detail
        assert result.confirmed is True
    state = sink.status()
    assert state.queue_length == 0
    assert state.leds == (True, True, True)
    assert sink.counters.unconfirmed == 0


def test_notable_log_records_the_operationally_interesting_events() -> None:
    sink = guarded(make_config(), FakeAcceptancePlc(capacity=1))
    sink.send_event(enter("circle", 1))
    sink.send_event(enter("triangle", 2))
    sink.send_event(enter("circle", 1))
    kinds = [entry["kind"] for entry in sink.recent_notable()]
    assert kinds == ["queue_full", "duplicate"]
