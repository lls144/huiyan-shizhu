"""Configuration for the minimal PC-to-PLC bridge."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PlcCommunicationConfig:
    enabled: bool = False
    host: str = "192.0.2.1"
    rack: int = 0
    slot: int = 1
    db_number: int | None = None
    auto_dequeue: bool = False
    command_pulse_seconds: float = 0.05
    dequeue_pulse_seconds: float = 0.20
    reset_pulse_seconds: float = 0.20
    timeout_seconds: float = 2.0
    poll_seconds: float = 0.02

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "PlcCommunicationConfig":
        known = {
            field: values.get(field, default)
            for field, default in (
                ("enabled", False),
                ("host", "192.0.2.1"),
                ("rack", 0),
                ("slot", 1),
                ("db_number", None),
                ("auto_dequeue", False),
                ("command_pulse_seconds", 0.05),
                ("dequeue_pulse_seconds", 0.20),
                ("reset_pulse_seconds", 0.20),
                ("timeout_seconds", 2.0),
                ("poll_seconds", 0.02),
            )
        }
        config = cls(**known)
        config.validate()
        return config

    def validate(self) -> None:
        if self.enabled and not isinstance(self.db_number, int):
            raise ValueError("db_number must be an integer when PLC communication is enabled")
        if self.enabled and self.db_number is not None and self.db_number <= 0:
            raise ValueError("db_number must be positive")
        for name in (
            "command_pulse_seconds",
            "dequeue_pulse_seconds",
            "reset_pulse_seconds",
            "timeout_seconds",
            "poll_seconds",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")


def load_plc_communication_config(path: str | Path) -> PlcCommunicationConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("PLC communication config root must be an object")
    return PlcCommunicationConfig.from_dict(payload)
