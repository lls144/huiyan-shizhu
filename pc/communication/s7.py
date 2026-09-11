"""Small S7 access layer for the TEST-ONLY M8 acceptance DB layout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import PlcState


CONTROL_SIZE = 8
STATUS_OFFSET = 8
STATUS_SIZE = 16
LAYOUT_MAGIC = 0x4D38
LAYOUT_VERSION = 1


@dataclass(frozen=True)
class PlcControls:
    test_enable: bool = False
    command_valid: bool = False
    command_data_valid: bool = False
    dequeue_request: bool = False
    reset_request: bool = False
    shape_code: int = 0
    semantic_id: int = 0
    # DBB2 (M8_AcceptanceData.ReservedInputByte2) carries the COMM-002 heartbeat
    # counter on its low byte. The remaining reserved control bytes stay zero so
    # the packed block of a plain command is unchanged.
    heartbeat: int = 0

    def pack(self) -> bytes:
        raw = bytearray(CONTROL_SIZE)
        raw[0] = (
            (int(self.test_enable) << 0)
            | (int(self.command_valid) << 1)
            | (int(self.command_data_valid) << 2)
            | (int(self.dequeue_request) << 3)
            | (int(self.reset_request) << 4)
        )
        raw[1] = int(self.shape_code) & 0xFF
        raw[2] = int(self.heartbeat) & 0xFF
        raw[4:8] = int(self.semantic_id).to_bytes(4, byteorder="big", signed=True)
        return bytes(raw)


def unpack_controls(raw: bytes) -> PlcControls:
    if len(raw) < CONTROL_SIZE:
        raise ValueError(f"control payload must be at least {CONTROL_SIZE} bytes")

    def bit(index: int) -> bool:
        return bool(raw[0] & (1 << index))

    return PlcControls(
        test_enable=bit(0),
        command_valid=bit(1),
        command_data_valid=bit(2),
        dequeue_request=bit(3),
        reset_request=bit(4),
        shape_code=raw[1],
        semantic_id=int.from_bytes(raw[4:8], byteorder="big", signed=True),
        heartbeat=raw[2],
    )


class S7LowLevelClient(Protocol):
    def connect(self, host: str, rack: int, slot: int) -> None: ...

    def disconnect(self) -> None: ...

    def get_connected(self) -> bool: ...

    def db_read(self, db_number: int, offset: int, size: int) -> bytes: ...

    def db_write(self, db_number: int, offset: int, raw: bytes) -> None: ...


class Snap7LowLevelClient:
    """Minimal adapter so the transport remains replaceable in tests."""

    def __init__(self) -> None:
        self._client = None
        self.socket_params_applied = False

    # Short timeouts keep the 2 s comm-loss alarm meaningful: with the defaults a
    # call against a pulled cable blocks for many seconds, which delays the
    # watchdog sample instead of letting it fail fast. KeepAliveTime also makes
    # the OS notice a dead peer in about a second.
    SOCKET_PARAMS: tuple[tuple[str, int], ...] = (
        ("PingTimeout", 500),
        ("SendTimeout", 1000),
        ("RecvTimeout", 1000),
        ("KeepAliveTime", 1000),
    )

    def _apply_socket_params(self) -> None:
        try:
            from snap7.type import Parameter
        except ImportError:  # pragma: no cover - snap7 is a runtime dependency
            return
        applied = 0
        for name, value in self.SOCKET_PARAMS:
            member = getattr(Parameter, name, None)
            if member is None:
                continue
            try:
                self._client.set_param(member, value)
                applied += 1
            except Exception:
                continue
        self.socket_params_applied = applied > 0

    @staticmethod
    def _client_type():
        try:
            import snap7.client

            return snap7.client.Client
        except ImportError as exc:
            raise RuntimeError(
                "python-snap7 is required: python -m pip install -r plc/tools/requirements.txt"
            ) from exc

    def connect(self, host: str, rack: int, slot: int) -> None:
        self._client = self._client_type()()
        self._apply_socket_params()
        self._client.connect(host, rack, slot)
        if not self._client.get_connected():
            raise RuntimeError(f"S7 connection to {host} did not become active")

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.disconnect()
        self._client = None

    def get_connected(self) -> bool:
        return bool(self._client is not None and self._client.get_connected())

    def db_read(self, db_number: int, offset: int, size: int) -> bytes:
        if self._client is None:
            raise RuntimeError("S7 client is not connected")
        return self._client.db_read(db_number, offset, size)

    def db_write(self, db_number: int, offset: int, raw: bytes) -> None:
        if self._client is None:
            raise RuntimeError("S7 client is not connected")
        self._client.db_write(db_number, offset, raw)


def unpack_state(raw: bytes) -> PlcState:
    if len(raw) < STATUS_SIZE:
        raise ValueError(f"status payload must be at least {STATUS_SIZE} bytes")

    def bit(byte_index: int, bit_index: int) -> bool:
        return bool(raw[byte_index] & (1 << bit_index))

    def usint(byte_index: int) -> int:
        return raw[byte_index]

    return PlcState(
        acceptance_ready=bit(0, 0),
        queue_empty=bit(0, 1),
        queue_full=bit(0, 2),
        leds=(bit(0, 3), bit(0, 4), bit(0, 5)),
        last_dequeued_valid=bit(0, 6),
        queue_length=usint(1),
        last_dequeued_shape=usint(2),
        last_dequeued_semantic_id=int.from_bytes(raw[4:8], byteorder="big", signed=True),
        cycle_counter=int.from_bytes(raw[8:12], byteorder="big", signed=False),
        layout_magic=int.from_bytes(raw[12:14], byteorder="big", signed=False),
        layout_version=usint(14),
    )
