"""PLC command sinks used by the GUI worker and standalone CLI."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

from pc.events.models import VisionEvent

from .config import PlcCommunicationConfig
from .models import (
    PlcCommandResult,
    PlcCommandStatus,
    command_from_event,
)
from .s7 import (
    S7LowLevelClient,
    Snap7LowLevelClient,
    unpack_state,
    LAYOUT_MAGIC,
    LAYOUT_VERSION,
    PlcControls,
)


class PlcCommandSink(Protocol):
    def start(self) -> None: ...

    def send_event(self, event: VisionEvent) -> PlcCommandResult: ...

    def dequeue(self) -> PlcCommandResult: ...

    def reset(self) -> PlcCommandResult: ...

    def stop(self) -> None: ...


class NullPlcSink:
    """No-op sink for environments where PLC communication is disabled."""

    def start(self) -> None:
        return None

    def send_event(self, event: VisionEvent) -> PlcCommandResult:
        return PlcCommandResult(None, PlcCommandStatus.SKIPPED, detail="PLC sink disabled")

    def dequeue(self) -> PlcCommandResult:
        return PlcCommandResult(None, PlcCommandStatus.SKIPPED, detail="PLC sink disabled")

    def reset(self) -> PlcCommandResult:
        return PlcCommandResult(None, PlcCommandStatus.SKIPPED, detail="PLC sink disabled")

    def stop(self) -> None:
        return None


@dataclass
class RecordingPlcSink:
    """Deterministic in-memory sink for integration tests and dry runs."""

    commands: list[PlcCommand] = field(default_factory=list)
    events: list[VisionEvent] = field(default_factory=list)
    dequeue_count: int = 0
    reset_count: int = 0

    def start(self) -> None:
        return None

    def send_event(self, event: VisionEvent) -> PlcCommandResult:
        self.events.append(event)
        command = command_from_event(event)
        if command is None:
            return PlcCommandResult(None, PlcCommandStatus.SKIPPED, detail="not a known ENTER shape")
        self.commands.append(command)
        return PlcCommandResult(command, PlcCommandStatus.SENT, detail="recorded in memory")

    def dequeue(self) -> PlcCommandResult:
        self.dequeue_count += 1
        return PlcCommandResult(None, PlcCommandStatus.SENT, detail="recorded dequeue")

    def reset(self) -> PlcCommandResult:
        self.reset_count += 1
        return PlcCommandResult(None, PlcCommandStatus.SENT, detail="recorded reset")

    def stop(self) -> None:
        return None


class S7PlcCommandSink:
    """Write M4 ENTER events into the TEST-ONLY M8 acceptance DB."""

    def __init__(
        self,
        config: PlcCommunicationConfig,
        low_level: S7LowLevelClient | None = None,
    ) -> None:
        self.config = config
        self._client = low_level or Snap7LowLevelClient()
        self._started = False

    def start(self) -> None:
        if not self.config.enabled:
            raise RuntimeError("PLC communication is disabled in config")
        self._client.connect(self.config.host, self.config.rack, self.config.slot)
        self._started = True

    def _write(self, **changes: object) -> None:
        values = {
            "test_enable": True,
            "command_valid": False,
            "command_data_valid": False,
            "dequeue_request": False,
            "reset_request": False,
            "shape_code": 0,
            "semantic_id": 0,
        }
        values.update(changes)
        controls = {
            "test_enable": bool(values["test_enable"]),
            "command_valid": bool(values["command_valid"]),
            "command_data_valid": bool(values["command_data_valid"]),
            "dequeue_request": bool(values["dequeue_request"]),
            "reset_request": bool(values["reset_request"]),
            "shape_code": int(values["shape_code"]),
            "semantic_id": int(values["semantic_id"]),
        }
        raw = PlcControls(**controls).pack()
        self._client.db_write(self.config.db_number, 0, raw)

    def _read_queue_length(self) -> int | None:
        try:
            raw = self._client.db_read(self.config.db_number, 8, 16)
            state = unpack_state(raw)
            if state.layout_magic != LAYOUT_MAGIC or state.layout_version != LAYOUT_VERSION:
                return None
            return state.queue_length
        except Exception:
            return None

    def send_event(self, event: VisionEvent) -> PlcCommandResult:
        command = command_from_event(event)
        if command is None:
            return PlcCommandResult(None, PlcCommandStatus.SKIPPED, detail="not a known ENTER shape")
        try:
            self._write(
                command_data_valid=True,
                shape_code=command.shape_code,
                semantic_id=command.semantic_id,
                command_valid=False,
            )
            time.sleep(self.config.command_pulse_seconds)
            self._write(
                command_data_valid=True,
                shape_code=command.shape_code,
                semantic_id=command.semantic_id,
                command_valid=True,
            )
            time.sleep(self.config.command_pulse_seconds)
            self._write(
                command_data_valid=True,
                shape_code=command.shape_code,
                semantic_id=command.semantic_id,
                command_valid=False,
            )
            queue_length = self._read_queue_length()
            if self.config.auto_dequeue:
                self.dequeue()
            return PlcCommandResult(
                command,
                PlcCommandStatus.SENT,
                queue_length=queue_length,
                detail="command edge written to PLC",
            )
        except Exception as exc:
            return PlcCommandResult(command, PlcCommandStatus.ERROR, detail=f"{type(exc).__name__}: {exc}")

    def dequeue(self) -> PlcCommandResult:
        try:
            self._write(dequeue_request=True)
            time.sleep(self.config.dequeue_pulse_seconds)
            self._write(dequeue_request=False)
            return PlcCommandResult(
                None,
                PlcCommandStatus.SENT,
                queue_length=self._read_queue_length(),
                detail="dequeue request written to PLC",
            )
        except Exception as exc:
            return PlcCommandResult(None, PlcCommandStatus.ERROR, detail=f"{type(exc).__name__}: {exc}")

    def reset(self) -> PlcCommandResult:
        try:
            self._write(reset_request=True)
            time.sleep(self.config.reset_pulse_seconds)
            self._write(reset_request=False)
            return PlcCommandResult(
                None,
                PlcCommandStatus.SENT,
                queue_length=self._read_queue_length(),
                detail="reset request written to PLC",
            )
        except Exception as exc:
            return PlcCommandResult(None, PlcCommandStatus.ERROR, detail=f"{type(exc).__name__}: {exc}")

    def stop(self) -> None:
        if not self._started:
            return
        try:
            self._write(
                test_enable=False,
                command_valid=False,
                command_data_valid=False,
                dequeue_request=False,
                reset_request=False,
                shape_code=0,
                semantic_id=0,
            )
        finally:
            self._client.disconnect()
            self._started = False


def build_plc_sink(config: PlcCommunicationConfig) -> PlcCommandSink | None:
    if not config.enabled:
        return None
    config.validate()
    return S7PlcCommandSink(config)
