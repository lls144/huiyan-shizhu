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
    # Measured 2026-09-10 on the lab CPU: put/get writes into
    # DB_M8_Acceptance.DBB0..7 are silently dropped roughly half the time, so every
    # control write is read back and re-sent until the PLC really holds it.
    write_confirm_attempts: int = 12
    write_confirm_interval_seconds: float = 0.02
    # M9 PC-side reliability layer (see pc/communication/reliability.py).
    queue_full_policy: str = "defer"
    duplicate_policy: str = "refuse"
    command_timeout_seconds: float = 3.0
    # A manual dequeue press can land between the pre-write and post-write status
    # reads, so a missing queue growth is re-checked briefly before it is called
    # unconfirmed.
    confirm_repoll_attempts: int = 3
    confirm_repoll_interval_seconds: float = 0.15

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
                ("write_confirm_attempts", 12),
                ("write_confirm_interval_seconds", 0.02),
                ("queue_full_policy", "defer"),
                ("duplicate_policy", "refuse"),
                ("command_timeout_seconds", 3.0),
                ("confirm_repoll_attempts", 3),
                ("confirm_repoll_interval_seconds", 0.15),
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
            "write_confirm_interval_seconds",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.write_confirm_attempts < 1:
            raise ValueError("write_confirm_attempts must be at least 1")
        if self.queue_full_policy not in ("defer", "drop"):
            raise ValueError("queue_full_policy must be 'defer' or 'drop'")
        if self.duplicate_policy not in ("refuse", "allow"):
            raise ValueError("duplicate_policy must be 'refuse' or 'allow'")
        if self.command_timeout_seconds <= 0:
            raise ValueError("command_timeout_seconds must be positive")
        if self.confirm_repoll_attempts < 1:
            raise ValueError("confirm_repoll_attempts must be at least 1")
        if self.confirm_repoll_interval_seconds < 0:
            raise ValueError("confirm_repoll_interval_seconds must be non-negative")


def load_plc_communication_config(path: str | Path) -> PlcCommunicationConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("PLC communication config root must be an object")
    return PlcCommunicationConfig.from_dict(payload)
