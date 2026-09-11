"""The S7 client must rebuild its socket after a cable pull or a CPU restart."""

from __future__ import annotations

from collections import deque
from dataclasses import replace

import pytest

from pc.communication.config import PlcCommunicationConfig
from pc.communication.fake_plc import FakeAcceptancePlc
from pc.communication.sink import S7PlcCommandSink
from pc.events.models import EventType, VisionEvent


class FlakyLowLevelClient:
    """Wraps the fake PLC and drops the socket on demand."""

    def __init__(self, plc: FakeAcceptancePlc) -> None:
        self.plc = plc
        self.connected = False
        self.reconnects = 0
        self.connect_attempts = 0
        self.fail_next_reads = 0
        self.can_connect = True

    def connect(self, host: str, rack: int, slot: int) -> None:
        self.connect_attempts += 1
        if not self.can_connect:
            raise RuntimeError("no carrier")
        self.connected = True
        self.reconnects += 1
        self.plc.connect(host, rack, slot)

    def disconnect(self) -> None:
        self.connected = False
        self.plc.disconnect()

    def get_connected(self) -> bool:
        return self.connected

    def db_read(self, db_number: int, offset: int, size: int) -> bytes:
        if not self.connected:
            raise RuntimeError("socket is not connected")
        if self.fail_next_reads > 0:
            self.fail_next_reads -= 1
            self.connected = False
            raise RuntimeError("connection reset by peer")
        return self.plc.db_read(db_number, offset, size)

    def db_write(self, db_number: int, offset: int, raw: bytes) -> None:
        if not self.connected:
            raise RuntimeError("socket is not connected")
        self.plc.db_write(db_number, offset, raw)


def _config() -> PlcCommunicationConfig:
    return PlcCommunicationConfig(
        enabled=True,
        db_number=12,
        command_pulse_seconds=0.0,
        dequeue_pulse_seconds=0.0,
        reset_pulse_seconds=0.0,
        write_confirm_interval_seconds=0.0,
    )


def _event(semantic_id: int) -> VisionEvent:
    return VisionEvent(
        event_id=semantic_id,
        event_type=EventType.OBJECT_ENTER,
        object_id=semantic_id,
        label="triangle",
        confidence=1.0,
        frame_index=0,
    )


def test_a_dropped_socket_is_rebuilt_on_the_next_status_read() -> None:
    plc = FakeAcceptancePlc()
    client = FlakyLowLevelClient(plc)
    sink = S7PlcCommandSink(_config(), low_level=client)
    sink.start()
    assert sink.reconnect_count == 0  # the initial connect is not a reconnect
    client.fail_next_reads = 1        # the cable is pulled
    state = sink.read_state()
    assert state is not None          # it reconnected and read anyway
    assert sink.reconnect_count == 1


def test_a_dropped_socket_is_rebuilt_during_a_command_write() -> None:
    plc = FakeAcceptancePlc()
    client = FlakyLowLevelClient(plc)
    config = _config()
    sink = S7PlcCommandSink(config, low_level=client)
    sink.start()
    client.fail_next_reads = 1        # the read-back hits a dead socket
    result = sink.send_event(_event(7))
    assert result.status.value == "SENT"
    assert sink.reconnect_count == 1
    assert [shape for shape, _ in plc.queue] == [1]


def test_a_link_that_never_recovers_still_returns_none_instead_of_raising() -> None:
    plc = FakeAcceptancePlc()
    client = FlakyLowLevelClient(plc)
    sink = S7PlcCommandSink(_config(), low_level=client)
    sink.start()
    client.fail_next_reads = 5        # reconnect succeeds but reads keep dying
    assert sink.read_state() is None
    assert sink.reconnect_count >= 1


def test_reconnect_attempts_are_bounded_per_write() -> None:
    plc = FakeAcceptancePlc()
    client = FlakyLowLevelClient(plc)
    config = replace(_config(), write_confirm_attempts=4)
    sink = S7PlcCommandSink(config, low_level=client)
    sink.start()
    client.connected = False  # the cable is out and stays out
    client.can_connect = False
    result = sink.send_event(_event(9))
    assert result.status.value == "ERROR"
    # one initial connect plus at most one reconnect attempt inside that write
    assert client.connect_attempts == 2
    assert sink.reconnect_count == 0
    assert plc.queue == deque()


def test_reconnect_attempts_are_rate_limited() -> None:
    plc = FakeAcceptancePlc()
    client = FlakyLowLevelClient(plc)
    config = replace(_config(), reconnect_min_interval_seconds=60.0)
    sink = S7PlcCommandSink(config, low_level=client)
    sink.start()
    client.connected = False
    client.can_connect = False
    attempts_before = client.connect_attempts
    for _ in range(5):
        assert sink.read_state() is None
    # The first read tried once, the rest were skipped by the rate limit, so a
    # dead link cannot stall the watchdog with a connect timeout every sample.
    assert client.connect_attempts == attempts_before + 1
