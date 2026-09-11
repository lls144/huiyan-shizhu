"""Unit tests for the COMM-002 PC half: heartbeat rhythm and link watchdog."""

from __future__ import annotations

from pc.communication.config import PlcCommunicationConfig
from pc.communication.fake_plc import FakeAcceptancePlc
from pc.communication.heartbeat import HeartbeatMonitor
from pc.communication.models import PlcState
from pc.communication.reliability import GuardedPlcSink
from pc.communication.sink import S7PlcCommandSink


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        # Round so repeatedly adding 0.1 s does not drift below an exact second.
        self.now = round(self.now + seconds, 9)


def _state() -> PlcState:
    return PlcState(
        acceptance_ready=True,
        queue_empty=True,
        queue_full=False,
        leds=(False, False, False),
        last_dequeued_valid=False,
        queue_length=0,
        last_dequeued_shape=0,
        last_dequeued_semantic_id=0,
        cycle_counter=1,
        layout_magic=0x4D38,
        layout_version=1,
    )


class _StubLink:
    def __init__(self) -> None:
        self.up = True
        self.heartbeats: list[int] = []
        self.fail_heartbeat = False

    def refresh_state(self) -> PlcState | None:
        return _state() if self.up else None

    def write_heartbeat(self, counter: int) -> None:
        if self.fail_heartbeat or not self.up:
            raise RuntimeError("link is down")
        self.heartbeats.append(counter)


def _monitor(link: _StubLink, clock: _Clock, **overrides: object) -> HeartbeatMonitor:
    values: dict[str, object] = {
        "enabled": True,
        "interval_seconds": 1.0,
        "timeout_seconds": 2.0,
        "clock": clock,
    }
    values.update(overrides)
    return HeartbeatMonitor(link, **values)  # type: ignore[arg-type]


def test_heartbeat_is_sent_once_per_second() -> None:
    link, clock = _StubLink(), _Clock()
    monitor = _monitor(link, clock)
    for _ in range(21):  # t = 0.0 .. 2.0 in 0.1 s steps
        monitor.tick()
        clock.advance(0.1)
    assert link.heartbeats == [1, 2, 3]
    health = monitor.health()
    assert health.heartbeat_count == 3
    assert 0.99 < health.heartbeat_interval_mean < 1.01


def test_no_heartbeat_is_sent_before_the_interval_elapses() -> None:
    link, clock = _StubLink(), _Clock()
    monitor = _monitor(link, clock)
    monitor.tick()
    assert link.heartbeats == [1]
    clock.advance(0.9)
    monitor.tick()
    assert link.heartbeats == [1]
    clock.advance(0.2)
    monitor.tick()
    assert link.heartbeats == [1, 2]


def test_link_loss_is_declared_only_after_the_two_second_timeout() -> None:
    link, clock = _StubLink(), _Clock()
    monitor = _monitor(link, clock)
    monitor.tick()
    link.up = False
    for _ in range(19):  # up to t = 1.9 s
        clock.advance(0.1)
        health = monitor.tick()
        assert health.comm_lost is False
    clock.advance(0.2)
    health = monitor.tick()  # t = 2.1 s
    assert health.comm_lost is True
    assert health.comm_lost_for_seconds >= 0.0


def test_recovery_closes_the_outage_and_records_its_duration() -> None:
    link, clock = _StubLink(), _Clock()
    monitor = _monitor(link, clock)
    monitor.tick()
    link.up = False
    clock.advance(3.0)
    assert monitor.tick().comm_lost is True
    link.up = True
    clock.advance(0.5)
    health = monitor.tick()
    assert health.comm_lost is False
    assert health.outage_count == 1
    outage = health.outages[-1]
    assert outage["ended_at"] is not None
    assert outage["duration_seconds"] is not None
    assert outage["duration_seconds"] > 2.0


def test_a_failed_heartbeat_is_counted_and_the_rhythm_is_not_advanced() -> None:
    link, clock = _StubLink(), _Clock()
    monitor = _monitor(link, clock)
    monitor.tick()
    assert link.heartbeats == [1]
    link.fail_heartbeat = True
    clock.advance(1.1)
    health = monitor.tick()
    assert health.heartbeat_count == 1
    assert health.heartbeat_failures == 1
    link.fail_heartbeat = False
    clock.advance(1.1)
    health = monitor.tick()
    assert health.heartbeat_count == 2
    assert link.heartbeats == [1, 2]


def test_the_monitor_disables_itself_for_a_sink_without_heartbeat_support() -> None:
    class _NoHeartbeat:
        def refresh_state(self) -> PlcState:
            return _state()

    monitor = HeartbeatMonitor(_NoHeartbeat(), enabled=True)
    assert monitor.enabled is False
    assert monitor.tick().enabled is False


def test_a_link_that_never_answers_still_alarms_after_the_timeout() -> None:
    link, clock = _StubLink(), _Clock()
    link.up = False
    monitor = _monitor(link, clock)
    assert monitor.tick().comm_lost is False
    clock.advance(2.1)
    health = monitor.tick()
    assert health.comm_lost is True
    assert health.heartbeat_count == 0
    assert health.heartbeat_failures >= 1


def test_tick_heartbeat_keeps_the_period_close_to_one_second() -> None:
    link, clock = _StubLink(), _Clock()
    monitor = _monitor(link, clock)
    # Emulate the 30 fps worker loop calling the cheap check every frame.
    for _ in range(300):
        monitor.tick_heartbeat()
        clock.advance(1.0 / 30.0)
    intervals = monitor.health().heartbeat_intervals
    assert link.heartbeats[0] == 1
    assert all(1.0 <= value < 1.05 for value in intervals)


def test_the_heartbeat_reaches_a_real_bus_path_and_leaves_the_queue_alone() -> None:
    plc = FakeAcceptancePlc(capacity=3)
    config = PlcCommunicationConfig(
        enabled=True,
        db_number=12,
        command_pulse_seconds=0.0,
        dequeue_pulse_seconds=0.0,
        reset_pulse_seconds=0.0,
        write_confirm_interval_seconds=0.0,
    )
    sink = GuardedPlcSink(S7PlcCommandSink(config, low_level=plc), config)
    sink.start()
    clock = _Clock()
    monitor = HeartbeatMonitor(sink, interval_seconds=1.0, timeout_seconds=2.0, clock=clock)
    for _ in range(11):
        monitor.tick()
        clock.advance(0.2)
    assert monitor.health().heartbeat_count == 3
    assert plc.control_bytes[2] == 3  # DBB2 carries the counter
    assert sink.status().queue_length == 0
    assert monitor.health().comm_lost is False
