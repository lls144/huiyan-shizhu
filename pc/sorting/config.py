"""Configuration for the conveyor sorting visualization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PLC_TRIGGERS = ("exit", "enter")


@dataclass(frozen=True)
class SortingConfig:
    """Presentation and timing parameters for the three-belt simulation.

    The values only shape the *animation*. They never change which station an
    item is ejected at, because that is fixed by the shape the vision pipeline
    already reported.
    """

    belt_speed_units_per_second: float = 0.60
    min_gap_units: float = 0.30
    eject_seconds: float = 0.85
    max_pending_items: int = 6
    plc_trigger: str = "exit"

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "SortingConfig":
        known = {
            field: values.get(field, default)
            for field, default in (
                ("belt_speed_units_per_second", 0.60),
                ("min_gap_units", 0.30),
                ("eject_seconds", 0.85),
                ("max_pending_items", 6),
                ("plc_trigger", "exit"),
            )
        }
        config = cls(**known)
        config.validate()
        return config

    def validate(self) -> None:
        if self.belt_speed_units_per_second <= 0:
            raise ValueError("belt_speed_units_per_second must be positive")
        if self.min_gap_units <= 0:
            raise ValueError("min_gap_units must be positive")
        if self.min_gap_units >= 1.0:
            raise ValueError("min_gap_units must be smaller than one belt segment")
        if self.eject_seconds <= 0:
            raise ValueError("eject_seconds must be positive")
        if self.max_pending_items < 1:
            raise ValueError("max_pending_items must be at least 1")
        if self.plc_trigger not in PLC_TRIGGERS:
            raise ValueError(f"plc_trigger must be one of {PLC_TRIGGERS}")


def load_sorting_config(path: str | Path) -> SortingConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("sorting config root must be an object")
    return SortingConfig.from_dict(payload)
