"""Vision worker variant that drives the conveyor simulation and PLC bridge."""

from __future__ import annotations

import threading
import time
from collections import deque
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import Signal

from pc.communication.sink import PlcCommandSink
from pc.communication.heartbeat import HeartbeatMonitor
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


class ControlRequestBuffer:
    """Operator actions queued from the UI thread for the worker thread.

    The S7 client belongs to the worker, so the 'dequeue / reset' buttons only
    enqueue an intent here; the worker performs the blocking request on its own
    thread in the frame loop.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: deque[str] = deque(maxlen=8)

    def request(self, action: str) -> None:
        if action not in ("dequeue", "reset"):
            raise ValueError(f"unknown control action: {action}")
        with self._lock:
            self._requests.append(action)

    def take_all(self) -> tuple[str, ...]:
        with self._lock:
            pending = tuple(self._requests)
            self._requests.clear()
            return pending


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
        control_requests: ControlRequestBuffer | None = None,
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
        plc_config = getattr(command_sink, "config", None)
        self.heartbeat: HeartbeatMonitor | None = (
            HeartbeatMonitor(
                command_sink,
                enabled=bool(getattr(plc_config, "heartbeat_enabled", True)),
                interval_seconds=float(
                    getattr(plc_config, "heartbeat_interval_seconds", 1.0)
                ),
                timeout_seconds=float(
                    getattr(plc_config, "comm_loss_timeout_seconds", 2.0)
                ),
            )
            if command_sink is not None
            else None
        )
        self.control_requests = control_requests or ControlRequestBuffer()
        self._last_tick: float | None = None
        self._last_plc_poll = 0.0
        self._last_flush = -1.0
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
        self._serve_control_requests()
        self._flush_deferred()
        if self.heartbeat is not None:
            self.heartbeat.tick_heartbeat()
        self._publish_plc_status()

    def _serve_control_requests(self) -> None:
        if self.command_sink is None:
            return
        for action in self.control_requests.take_all():
            try:
                if action == "dequeue":
                    self.command_sink.dequeue()
                else:
                    self.command_sink.reset()
            except Exception as error:
                self.controller.plc_error = f"{type(error).__name__}: {error}"
        self._last_plc_poll = 0.0  # force a status refresh right after an action

    def _flush_deferred(self) -> None:
        flush = getattr(self.command_sink, "flush_deferred", None)
        if flush is None:
            return
        # A deferred retry costs several DB accesses; once every half second is
        # plenty and keeps the S7 traffic well below the vision frame rate.
        now = time.perf_counter()
        if now - self._last_flush < 0.5:
            return
        self._last_flush = now
        try:
            results = flush()
        except Exception as error:
            self.controller.plc_error = f"{type(error).__name__}: {error}"
            return
        if not results:
            return
        self.controller.plc_results.extend(results)
        for result in results:
            if result.status.value == "ERROR" and self.controller.plc_error is None:
                self.controller.plc_error = result.detail

    def _publish_plc_status(self, force: bool = False) -> None:
        """Publish the real PLC queue/LED state so the UI can show hardware truth."""

        if self.controller.plc_error is not None and self.controller.plc_error != self._last_plc_error:
            self._last_plc_error = self.controller.plc_error
            self.plc_state_updated.emit({"error": self.controller.plc_error})
        if self.command_sink is None:
            return
        now = time.perf_counter()
        if not force and now - self._last_plc_poll < 0.5:
            return
        self._last_plc_poll = now
        status_reader = getattr(self.command_sink, "status", None)
        if status_reader is not None:
            try:
                if self.heartbeat is not None:
                    health = self.heartbeat.tick()
                else:
                    refresh = getattr(self.command_sink, "refresh_state", None)
                    if refresh is not None:
                        refresh()
                    health = None
                payload: dict[str, object] = {"status": status_reader().to_record()}
                if health is not None:
                    payload["health"] = health.to_record()
                self.plc_state_updated.emit(payload)
            except Exception as error:
                self.plc_state_updated.emit({"error": f"{type(error).__name__}: {error}"})
            return
        reader = getattr(self.command_sink, "read_state", None)
        if reader is None:
            return
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
