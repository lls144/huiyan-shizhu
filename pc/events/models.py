"""Public M4 data models; detections are observations, events are lifecycle facts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

BBox = tuple[int, int, int, int]


class EventType(StrEnum):
    OBJECT_ENTER = "OBJECT_ENTER"
    OBJECT_EXIT = "OBJECT_EXIT"


@dataclass(frozen=True)
class Detection:
    """One instantaneous observation in a single frame."""

    label: str
    confidence: float
    bbox: BBox
    frame_index: int

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("detection label must not be empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("detection confidence must be in [0, 1]")
        if self.frame_index < 0:
            raise ValueError("detection frame_index must be non-negative")
        if len(self.bbox) != 4 or self.bbox[2] <= 0 or self.bbox[3] <= 0:
            raise ValueError("detection bbox must be (x, y, positive width, positive height)")

    @classmethod
    def from_record(cls, record: dict[str, Any], frame_index: int) -> "Detection":
        return cls(
            label=str(record["label"]),
            confidence=float(record["confidence"]),
            bbox=tuple(int(value) for value in record["bbox"]),  # type: ignore[arg-type]
            frame_index=frame_index,
        )

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["bbox"] = list(self.bbox)
        return record


@dataclass(frozen=True)
class ObjectState:
    """Snapshot of one logical object maintained across frames."""

    object_id: int
    label: str
    bbox: BBox
    first_seen: int
    last_seen: int
    hit_count: int
    consecutive_hits: int
    miss_count: int
    confirmed: bool
    active: bool
    event_emitted: bool
    status: str
    confidence: float

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["bbox"] = list(self.bbox)
        return record


@dataclass(frozen=True)
class VisionEvent:
    """One discrete lifecycle event suitable for later consumers."""

    event_id: int
    event_type: EventType
    object_id: int
    label: str
    confidence: float
    frame_index: int

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["event_type"] = self.event_type.value
        return record


@dataclass(frozen=True)
class FrameUpdate:
    """Observable result of processing one ordered detection frame."""

    frame_index: int
    detections: tuple[Detection, ...]
    object_states: tuple[ObjectState, ...]
    events: tuple[VisionEvent, ...]

    @property
    def active_objects(self) -> tuple[ObjectState, ...]:
        return tuple(
            state for state in self.object_states if state.active and state.confirmed
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "detections": [item.to_record() for item in self.detections],
            "object_states": [item.to_record() for item in self.object_states],
            "events": [item.to_record() for item in self.events],
        }
