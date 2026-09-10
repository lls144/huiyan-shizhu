"""Offline acceptance PLC implementing the TEST-ONLY M8 DB layout.

This model intentionally implements the same edge/queue/LED semantics as the
SCL acceptance harness.  It is not a scan-cycle simulator and is not evidence
for a real S7-1200.
"""

from __future__ import annotations

from collections import deque

from .s7 import (
    LAYOUT_MAGIC,
    LAYOUT_VERSION,
    PlcControls,
    unpack_controls,
)


class FakeAcceptancePlc:
    """In-memory implementation of ``DB_M8_Acceptance``."""

    def __init__(self, capacity: int = 3) -> None:
        if capacity < 1:
            raise ValueError("fake PLC capacity must be positive")
        self.capacity = capacity
        self.queue: deque[tuple[int, int]] = deque()
        self.displayed_shape: int | None = None
        self.last_dequeued: tuple[int, int] | None = None
        self.cycle_counter = 0
        self.connected = False
        self.writes: list[tuple[int, int, bytes]] = []
        self._previous_command_valid = False
        self._previous_dequeue_request = False
        self._previous_reset_request = False

    def connect(self, host: str, rack: int, slot: int) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def get_connected(self) -> bool:
        return self.connected

    def db_read(self, db_number: int, offset: int, size: int) -> bytes:
        if offset != 8 or size != 16:
            raise ValueError(f"unsupported fake DB read: db={db_number}, offset={offset}, size={size}")
        self.cycle_counter += 1
        return self._status_bytes()

    def db_write(self, db_number: int, offset: int, raw: bytes) -> None:
        if offset != 0 or len(raw) < 8:
            raise ValueError(f"unsupported fake DB write: db={db_number}, offset={offset}, size={len(raw)}")
        controls = unpack_controls(raw)
        self.writes.append((db_number, offset, bytes(raw)))
        self.cycle_counter += 1
        self._apply(controls)

    def _apply(self, controls: PlcControls) -> None:
        command_edge = bool(controls.command_valid and not self._previous_command_valid)
        dequeue_edge = bool(controls.dequeue_request and not self._previous_dequeue_request)
        reset_edge = bool(controls.reset_request and not self._previous_reset_request)

        if controls.test_enable:
            if command_edge and controls.command_data_valid and len(self.queue) < self.capacity:
                self.queue.append((controls.shape_code, controls.semantic_id))
            if dequeue_edge and self.queue:
                shape_code, semantic_id = self.queue.popleft()
                self.displayed_shape = shape_code
                self.last_dequeued = (shape_code, semantic_id)
            if reset_edge:
                self.queue.clear()
                self.displayed_shape = None
                self.last_dequeued = None

        self._previous_command_valid = controls.command_valid
        self._previous_dequeue_request = controls.dequeue_request
        self._previous_reset_request = controls.reset_request

    def _leds(self) -> tuple[bool, bool, bool]:
        if self.displayed_shape is None:
            return (False, False, False)
        return (
            self.displayed_shape >= 1,
            self.displayed_shape >= 2,
            self.displayed_shape >= 3,
        )

    def _status_bytes(self) -> bytes:
        raw = bytearray(16)
        raw[0] = (
            (1 << 0)
            | (int(len(self.queue) == 0) << 1)
            | (int(len(self.queue) == self.capacity) << 2)
            | (int(self._leds()[0]) << 3)
            | (int(self._leds()[1]) << 4)
            | (int(self._leds()[2]) << 5)
            | (int(self.last_dequeued is not None) << 6)
        )
        raw[1] = len(self.queue)
        raw[2] = self.last_dequeued[0] if self.last_dequeued is not None else 0
        semantic_id = self.last_dequeued[1] if self.last_dequeued is not None else 0
        raw[4:8] = semantic_id.to_bytes(4, byteorder="big", signed=True)
        raw[8:12] = self.cycle_counter.to_bytes(4, byteorder="big", signed=False)
        raw[12:14] = LAYOUT_MAGIC.to_bytes(2, byteorder="big", signed=False)
        raw[14] = LAYOUT_VERSION
        return bytes(raw)
