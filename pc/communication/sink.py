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
    PlcState,
    command_from_event,
)
from .s7 import (
    CONTROL_SIZE,
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
        self._write_retries = 0
        self._heartbeat = 0

    @property
    def write_retry_count(self) -> int:
        """Control writes that had to be re-sent because the PLC dropped the first one."""

        return self._write_retries

    def start(self) -> None:
        if not self.config.enabled:
            raise RuntimeError("PLC communication is disabled in config")
        self._client.connect(self.config.host, self.config.rack, self.config.slot)
        self._started = True

    def safe_init(self) -> int:
        """Clear every request bit before the first command of a session.

        ``DB_M8_Acceptance`` keeps its values across a power cycle (measured
        2026-09-11: the harness ``CycleCounter`` continued after a power-off),
        so a session that was killed instead of stopped can leave
        ``TestEnable``/``CommandDataValid``/``CommandValidTest`` set. The PLC
        enqueues on the ``CommandValid`` rising edge and its edge memory starts
        clear, so a retained ``CommandValidTest := TRUE`` would enqueue one
        ghost item on the first scan after power-up. Writing an idle-but-enabled
        control block on connect makes that impossible.
        """

        return self._write(
            test_enable=True,
            command_valid=False,
            command_data_valid=False,
            dequeue_request=False,
            reset_request=False,
            shape_code=0,
            semantic_id=0,
        )

    def write_heartbeat(self, counter: int) -> int:
        """Send the COMM-002 heartbeat (DBB2) and confirm the PLC really holds it."""

        return self._write(heartbeat=int(counter) & 0xFF)

    def _read_controls(self) -> bytes:
        return bytes(self._client.db_read(self.config.db_number, 0, CONTROL_SIZE))

    def _write(self, **changes: object) -> int:
        """Write the control block and confirm it, returning the attempts used.

        The lab CPU silently drops roughly half of the put/get writes into this
        TEST-ONLY DB (measured 2026-09-10), so a single ``db_write`` that returns
        without error is not evidence that the PLC received the command. Every write
        is read back and re-sent until the PLC really holds the requested value.
        """

        values = {
            "test_enable": True,
            "command_valid": False,
            "command_data_valid": False,
            "dequeue_request": False,
            "reset_request": False,
            "shape_code": 0,
            "semantic_id": 0,
            "heartbeat": self._heartbeat,
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
            "heartbeat": int(values["heartbeat"]) & 0xFF,
        }
        raw = PlcControls(**controls).pack()
        self._heartbeat = int(controls["heartbeat"])
        attempts = 0
        last = b""
        for attempt in range(1, self.config.write_confirm_attempts + 1):
            attempts = attempt
            self._client.db_write(self.config.db_number, 0, raw)
            last = self._read_controls()
            if last == raw:
                self._write_retries += attempt - 1
                return attempt
            if attempt < self.config.write_confirm_attempts:
                time.sleep(self.config.write_confirm_interval_seconds)
        raise RuntimeError(
            f"control write to DB{self.config.db_number} was never confirmed after "
            f"{attempts} attempts (wanted {raw.hex()}, last read {last.hex()})"
        )

    def _read_queue_length(self) -> int | None:
        state = self.read_state()
        return state.queue_length if state is not None else None

    def read_state(self) -> PlcState | None:
        """Read PLC-owned status bytes, returning ``None`` on layout/transport failure."""

        try:
            raw = self._client.db_read(self.config.db_number, 8, 16)
            state = unpack_state(raw)
            if state.layout_magic != LAYOUT_MAGIC or state.layout_version != LAYOUT_VERSION:
                return None
            return state
        except Exception:
            return None

    def send_event(self, event: VisionEvent) -> PlcCommandResult:
        command = command_from_event(event)
        if command is None:
            return PlcCommandResult(None, PlcCommandStatus.SKIPPED, detail="not a known ENTER shape")
        try:
            retries = 0
            retries += self._write(
                command_data_valid=True,
                shape_code=command.shape_code,
                semantic_id=command.semantic_id,
                command_valid=False,
            ) - 1
            time.sleep(self.config.command_pulse_seconds)
            retries += self._write(
                command_data_valid=True,
                shape_code=command.shape_code,
                semantic_id=command.semantic_id,
                command_valid=True,
            ) - 1
            time.sleep(self.config.command_pulse_seconds)
            retries += self._write(
                command_data_valid=True,
                shape_code=command.shape_code,
                semantic_id=command.semantic_id,
                command_valid=False,
            ) - 1
            queue_length = self._read_queue_length()
            if self.config.auto_dequeue:
                self.dequeue()
            return PlcCommandResult(
                command,
                PlcCommandStatus.SENT,
                queue_length=queue_length,
                detail=f"command edge written to PLC (control writes=3, re-sent={retries})",
            )
        except Exception as exc:
            return PlcCommandResult(command, PlcCommandStatus.ERROR, detail=f"{type(exc).__name__}: {exc}")

    def dequeue(self) -> PlcCommandResult:
        try:
            retries = self._write(dequeue_request=True) - 1
            time.sleep(self.config.dequeue_pulse_seconds)
            retries += self._write(dequeue_request=False) - 1
            return PlcCommandResult(
                None,
                PlcCommandStatus.SENT,
                queue_length=self._read_queue_length(),
                detail=f"dequeue request written to PLC (re-sent={retries})",
            )
        except Exception as exc:
            return PlcCommandResult(None, PlcCommandStatus.ERROR, detail=f"{type(exc).__name__}: {exc}")

    def reset(self) -> PlcCommandResult:
        try:
            retries = self._write(reset_request=True) - 1
            time.sleep(self.config.reset_pulse_seconds)
            retries += self._write(reset_request=False) - 1
            return PlcCommandResult(
                None,
                PlcCommandStatus.SENT,
                queue_length=self._read_queue_length(),
                detail=f"reset request written to PLC (re-sent={retries})",
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
