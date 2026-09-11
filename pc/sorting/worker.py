"""Vision worker variant that drives the conveyor simulation and PLC bridge."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import Signal

from pc.communication.sink import PlcCommandSink
from pc.events.config import EventConfig
from pc.events.models import VisionEvent
from pc.gui.worker import (
    Analyzer,
    EvidenceRequestBuffer,
    LatestSnapshotBuffer,
    VisionWorker,
)
from pc.gui.sources import FrameSource
from pc.vision.config import VisionConfig

from .config import SortingConfig
from .controller import SortingController
from .model import SortingResult


class SortingVisionWorker(VisionWorker):
    """Same pipeline as M5, but PLC commands follow the conveyor instead of ENTER.

    The base worker writes to the PLC as soon as an ``OBJECT_ENTER`` arrives.
    Here the events are fed into :class:`SortingController` instead, so the write
    happens when the simulated item is ejected (or at ENTER, if configured).

    The frame loop also advances the simulation, which keeps every timing value
    deterministic with respect to processed frames rather than GUI repaints.
    """

    sorting_updated = Signal(object)
    sorting_result = Signal(object)
    plc_state_updated = Signal(object)

    def __init__(
        self,
        source: FrameSource,
        vision_config: VisionConfig,
        event_config: EventConfig,
        buffer: LatestSnapshotBuffer,
        evidence_requests: EvidenceRequestBuffer,
        evidence_root: Path,
        expected_labels: Sequence[str],
        sorting_config: SortingConfig,
        analyzer: Analyzer,
        command_sink: PlcCommandSink | None = None,
    ) -> None:
        super().__init__(
            source,
            vision_config,
            event_config,
            buffer,
            evidence_requests,
            evidence_root,
            expected_labels,
            analyzer,
            command_sink,
        )
        self.controller = SortingController(sorting_config, command_sink)
        self._last_tick: float | None = None
        self._last_plc_poll = 0.0
        self._last_plc_error: str | None = None
        self._frame_counter = 0

    def _dispatch_plc_events(self, events: tuple[VisionEvent, ...]) -> None:
        now = time.perf_counter()
        dt = 0.0 if self._last_tick is None else min(now - self._last_tick, 0.5)
        self._last_tick = now
        self.controller.submit_events(events)
        completed = self.controller.advance(dt, frame_index=self._frame_counter)
        self._frame_counter += 1
        for result in completed:
            self.sorting_result.emit(result)
        self.sorting_updated.emit(self.controller.snapshot())
        self._publish_plc_status()

    def _publish_plc_status(self) -> None:
        """Publish the real PLC queue/LED state so the UI can show hardware truth."""

        if self.controller.plc_error is not None and self.controller.plc_error != self._last_plc_error:
            self._last_plc_error = self.controller.plc_error
            self.plc_state_updated.emit({"error": self.controller.plc_error})
        reader = getattr(self.command_sink, "read_state", None)
        if reader is None:
            return
        now = time.perf_counter()
        if now - self._last_plc_poll < 0.5:
            return
        self._last_plc_poll = now
        try:
            state = reader()
        except Exception as error:
            self.plc_state_updated.emit({"error": f"{type(error).__name__}: {error}"})
            return
        self.plc_state_updated.emit(
            {"state": state.to_record() if state is not None else None}
        )

    def _stop_plc_sink(self) -> None:
        self.plc_command_results.extend(self.controller.plc_results)
        if self.controller.plc_error is not None and self.plc_sink_error is None:
            self.plc_sink_error = self.controller.plc_error
        super()._stop_plc_sink()

    @property
    def sorting_results(self) -> tuple[SortingResult, ...]:
        return self.controller.simulator.results
