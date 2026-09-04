"""Immutable GUI-facing snapshots composed from existing domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from numpy.typing import NDArray
import numpy as np

from pc.events.models import Detection, ObjectState, VisionEvent


class GuiState(StrEnum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass(frozen=True)
class GuiSnapshot:
    frame_index: int
    timestamp: str
    annotated_frame: NDArray[np.uint8]
    detections: tuple[Detection, ...]
    tracked_objects: tuple[ObjectState, ...]
    events: tuple[VisionEvent, ...]
    source_type: str
    source_status: str
    processed_fps: float
    processing_ms: float
    roi_bounds: tuple[int, int, int, int]
    roi_mode: str
    roi_source: str
    preprocess_method: str
    error: str | None = None


@dataclass(frozen=True)
class WorkerSummary:
    started_at: str
    finished_at: str
    duration_seconds: float
    source_type: str
    source_metadata: dict[str, Any]
    frames_read: int
    frames_processed: int
    detection_count: int
    event_count: int
    processing_fps: float
    average_processing_ms: float
    p95_processing_ms: float
    failed_reads: int
    error: str | None
    ended_reason: str
    worker_clean_shutdown: bool
    events: tuple[VisionEvent, ...]
    final_object_states: tuple[ObjectState, ...]
    evidence_records: tuple[dict[str, str], ...]

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["events"] = [event.to_record() for event in self.events]
        record["final_object_states"] = [state.to_record() for state in self.final_object_states]
        return record
