"""Protocol-neutral immutable values and validated simulation settings."""
from dataclasses import asdict, dataclass
from enum import StrEnum
import json
from pathlib import Path


def positive_int(value, name, *, zero=False):
    if type(value) is not int or value < (0 if zero else 1):
        raise ValueError(f"{name} must be an integer >= {0 if zero else 1}")


@dataclass(frozen=True)
class Config:
    capacity: int = 3
    heartbeat_interval_ms: int = 1000
    heartbeat_timeout_ms: int = 2000
    response_timeout_ms: int = 100

    def __post_init__(self):
        for key, value in asdict(self).items():
            positive_int(value, key)
        if self.heartbeat_interval_ms >= self.heartbeat_timeout_ms:
            raise ValueError("heartbeat interval must be below timeout")

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config must be an object")
        return cls(**data)


@dataclass(frozen=True)
class SemanticCommand:
    command_id: int
    shape: str
    source_event_id: int | None = None
    source_object_id: int | None = None


class Status(StrEnum):
    ACCEPTED = "ACCEPTED"
    QUEUE_FULL = "QUEUE_FULL"
    INVALID = "INVALID"
    DUPLICATE = "DUPLICATE"
    OFFLINE = "OFFLINE"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class SemanticResponse:
    command_id: int
    status: Status
    queue_length: int
    message: str = ""


class CommandAdapter:
    """One command per ENTER supplied by M4; EXIT does not allocate an ID."""
    def __init__(self):
        self._next_id = 1

    def adapt(self, event):
        from pc.events.models import EventType
        if event.event_type == EventType.OBJECT_EXIT:
            return None
        if event.event_type != EventType.OBJECT_ENTER:
            raise ValueError("unsupported lifecycle event")
        command = SemanticCommand(self._next_id, event.label, event.event_id, event.object_id)
        self._next_id += 1
        return command
