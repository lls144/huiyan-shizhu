"""Shape-command data models shared by PC integration and tests."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from pc.events.models import EventType, VisionEvent


SHAPE_CODES = {
    "triangle": 1,
    "rectangle": 2,
    "circle": 3,
}


class PlcCommandStatus(StrEnum):
    SENT = "SENT"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"
    QUEUE_FULL = "QUEUE_FULL"
    DUPLICATE = "DUPLICATE"
    UNCONFIRMED = "UNCONFIRMED"


@dataclass(frozen=True)
class PlcCommand:
    shape: str
    shape_code: int
    semantic_id: int
    source_event_id: int | None = None
    source_object_id: int | None = None


@dataclass(frozen=True)
class PlcCommandResult:
    command: PlcCommand | None
    status: PlcCommandStatus
    queue_length: int | None = None
    detail: str = ""
    queue_length_before: int | None = None
    attempts: int = 0
    resends: int = 0
    elapsed_seconds: float = 0.0
    confirmed: bool = False

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["status"] = self.status.value
        if self.command is not None:
            record["command"] = asdict(self.command)
        return record


@dataclass(frozen=True)
class PlcState:
    acceptance_ready: bool
    queue_empty: bool
    queue_full: bool
    leds: tuple[bool, bool, bool]
    last_dequeued_valid: bool
    queue_length: int
    last_dequeued_shape: int
    last_dequeued_semantic_id: int
    cycle_counter: int
    layout_magic: int
    layout_version: int

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["leds"] = list(self.leds)
        return record


def label_to_shape_code(label: str) -> int | None:
    return SHAPE_CODES.get(label)


def command_from_event(event: VisionEvent) -> PlcCommand | None:
    if event.event_type is not EventType.OBJECT_ENTER:
        return None
    shape_code = label_to_shape_code(event.label)
    if shape_code is None:
        return None
    return PlcCommand(
        shape=event.label,
        shape_code=shape_code,
        semantic_id=event.object_id,
        source_event_id=event.event_id,
        source_object_id=event.object_id,
    )
