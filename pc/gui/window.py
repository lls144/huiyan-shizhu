"""Presentation-only PySide6 main window consuming synchronized snapshots."""

from __future__ import annotations

import json
import platform
from collections import deque
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Sequence

import cv2
import PySide6
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QCloseEvent, QImage, QKeyEvent, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pc.events.config import EventConfig
from pc.vision.config import VisionConfig
from pc.vision.live import _git_state

from .models import GuiSnapshot, GuiState, WorkerSummary
from .sources import FrameSource
from .style import APP_STYLE, load_ui_fonts
from .worker import Analyzer, EvidenceRequestBuffer, LatestSnapshotBuffer, VisionWorker

SourceFactory = Callable[[], FrameSource]


def bgr_to_qimage(frame: object) -> QImage:
    """Return an owning RGB QImage so NumPy storage may be released safely."""

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # type: ignore[arg-type]
    height, width, channels = rgb.shape
    return QImage(rgb.data, width, height, channels * width, QImage.Format.Format_RGB888).copy()


def _card(title: str, content: QWidget) -> QFrame:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(8)
    heading = QLabel(title.upper())
    heading.setObjectName("sectionTitle")
    layout.addWidget(heading)
    layout.addWidget(content)
    return frame


class MainWindow(QMainWindow):
    def __init__(
        self,
        source_factory: SourceFactory,
        source_type: str,
        vision_config: VisionConfig,
        event_config: EventConfig,
        session_dir: Path,
        evidence_root: Path,
        expected_labels: Sequence[str],
        analyzer: Analyzer,
    ) -> None:
        super().__init__()
        load_ui_fonts()
        self.source_factory = source_factory
        self.source_type = source_type
        self.vision_config = vision_config
        self.event_config = event_config
        self.session_dir = session_dir
        self.evidence_root = evidence_root
        self.expected_labels = tuple(expected_labels)
        self.analyzer = analyzer
        self._thread: QThread | None = None
        self._worker: VisionWorker | None = None
        self._buffer: LatestSnapshotBuffer | None = None
        self._requests: EvidenceRequestBuffer | None = None
        self._last_image: QImage | None = None
        self._last_frame_index = -1
        self._last_snapshot: GuiSnapshot | None = None
        self._gui_updates = 0
        self._recent_events: deque[str] = deque(maxlen=30)
        self._state = GuiState.IDLE
        self.last_session_summary: dict[str, object] | None = None
        self.session_annotations: dict[str, object] = {}
        self._build_ui()
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("慧眼识珠 · Vision Console")
        self.resize(1380, 840)
        self._set_state(GuiState.IDLE)

    def _build_ui(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("慧眼识珠")
        title.setObjectName("title")
        subtitle = QLabel("AI visual warehouse · local vision console")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        self.state_chip = QLabel("IDLE")
        self.state_chip.setObjectName("stateChip")
        header.addWidget(self.state_chip)
        outer.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        video_column = QWidget()
        video_layout = QVBoxLayout(video_column)
        video_layout.setContentsMargins(0, 0, 0, 0)
        self.video_label = QLabel("Start a synthetic or camera session")
        self.video_label.setObjectName("video")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(720, 480)
        video_layout.addWidget(self.video_label, 1)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("primary")
        self.stop_button = QPushButton("Stop")
        self.start_button.clicked.connect(self.start_session)
        self.stop_button.clicked.connect(self.stop_session)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addSpacing(8)
        self.scenario_buttons: list[QPushButton] = []
        for key, label, scenario in (
            ("1", "Normal", "normal_light"),
            ("2", "Bright / side", "bright_or_side_light"),
            ("3", "Dark", "dark_light"),
            ("4", "Occlusion", "partial_occlusion"),
            ("5", "Touching", "touching_or_merged"),
        ):
            button = QPushButton(f"{key}  {label}")
            button.clicked.connect(lambda checked=False, value=scenario: self.request_evidence(value))
            self.scenario_buttons.append(button)
            controls.addWidget(button)
        controls.addStretch()
        video_layout.addLayout(controls)
        splitter.addWidget(video_column)

        side = QWidget()
        side.setMinimumWidth(360)
        side.setMaximumWidth(470)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(10)

        status = QWidget()
        grid = QGridLayout(status)
        grid.setContentsMargins(0, 0, 0, 0)
        self.metrics: dict[str, QLabel] = {}
        for row, (name, label) in enumerate(
            (
                ("source", "Source"),
                ("fps", "Processed FPS"),
                ("latency", "Processing"),
                ("frame", "Frame"),
                ("roi", "ROI"),
                ("preprocess", "Preprocess"),
                ("error", "Last error"),
            )
        ):
            key = QLabel(label)
            key.setObjectName("subtitle")
            value = QLabel("—")
            value.setObjectName("metricValue")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.metrics[name] = value
            grid.addWidget(key, row, 0)
            grid.addWidget(value, row, 1)
        side_layout.addWidget(_card("Runtime", status))

        self.detection_list = QListWidget()
        self.detection_list.setMinimumHeight(125)
        side_layout.addWidget(_card("Detections · geometric confidence", self.detection_list))
        self.object_list = QListWidget()
        self.object_list.setMinimumHeight(125)
        side_layout.addWidget(_card("Tracked objects", self.object_list))
        self.event_list = QListWidget()
        self.event_list.setMinimumHeight(115)
        side_layout.addWidget(_card("Recent events", self.event_list), 1)
        splitter.addWidget(side)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        outer.addWidget(splitter, 1)
        self.setCentralWidget(root)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    @property
    def state(self) -> GuiState:
        return self._state

    @property
    def last_snapshot(self) -> GuiSnapshot | None:
        return self._last_snapshot

    def _set_state(self, state: GuiState) -> None:
        self._state = state
        self.state_chip.setText(state.value.upper())
        active = state in {GuiState.STARTING, GuiState.RUNNING, GuiState.STOPPING}
        self.start_button.setEnabled(not active)
        self.stop_button.setEnabled(state in {GuiState.STARTING, GuiState.RUNNING})
        camera_running = self.source_type == "camera" and state == GuiState.RUNNING
        for button in self.scenario_buttons:
            button.setEnabled(camera_running)

    def start_session(self) -> None:
        if self.is_running:
            return
        self._last_frame_index = -1
        self._gui_updates = 0
        self._recent_events.clear()
        self.event_list.clear()
        self.metrics["error"].setText("—")
        self._buffer = LatestSnapshotBuffer()
        self._requests = EvidenceRequestBuffer()
        source = self.source_factory()
        thread = QThread(self)
        worker = VisionWorker(
            source,
            self.vision_config,
            self.event_config,
            self._buffer,
            self._requests,
            self.evidence_root,
            self.expected_labels,
            self.analyzer,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.snapshot_available.connect(self._consume_latest)
        worker.state_changed.connect(self._on_worker_state)
        worker.finished.connect(self._on_worker_summary)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        self._thread = thread
        self._worker = worker
        self._set_state(GuiState.STARTING)
        thread.start()

    def stop_session(self, block: bool = False) -> None:
        if self._thread is None or not self._thread.isRunning():
            return
        self._set_state(GuiState.STOPPING)
        self._thread.requestInterruption()
        if block:
            self._thread.wait(5000)
            QApplication.processEvents()

    def request_evidence(self, scenario: str) -> None:
        if self.source_type != "camera" or self._requests is None or not self.is_running:
            return
        self._requests.request(scenario)
        self.statusBar().showMessage(f"Queued M3 evidence: {scenario}", 2500)

    def _on_worker_state(self, value: str) -> None:
        state = GuiState(value)
        self._set_state(state)

    def _consume_latest(self) -> None:
        if self._buffer is None:
            return
        snapshot = self._buffer.take_latest()
        if snapshot is None or snapshot.frame_index <= self._last_frame_index:
            return
        self._last_frame_index = snapshot.frame_index
        self._last_snapshot = snapshot
        self._gui_updates += 1
        self._last_image = bgr_to_qimage(snapshot.annotated_frame)
        self._render_image()
        self.metrics["source"].setText(f"{snapshot.source_type} · {snapshot.source_status}")
        self.metrics["fps"].setText(f"{snapshot.processed_fps:.1f}")
        self.metrics["latency"].setText(f"{snapshot.processing_ms:.2f} ms")
        self.metrics["frame"].setText(str(snapshot.frame_index))
        bounds = ",".join(str(value) for value in snapshot.roi_bounds)
        self.metrics["roi"].setText(
            f"{snapshot.roi_mode} / {snapshot.roi_source} · [{bounds}]"
        )
        self.metrics["preprocess"].setText(snapshot.preprocess_method)
        self.metrics["error"].setText(snapshot.error or "—")

        self.detection_list.clear()
        for detection in snapshot.detections:
            self.detection_list.addItem(f"{detection.label:<10}  {detection.confidence:.3f}")
        if not snapshot.detections:
            self.detection_list.addItem("No object")

        self.object_list.clear()
        for state in snapshot.tracked_objects:
            if state.active:
                self.object_list.addItem(f"#{state.object_id}  {state.label:<10}  {state.status}")
        if self.object_list.count() == 0:
            self.object_list.addItem("No active object")

        for event in snapshot.events:
            self._recent_events.appendleft(
                f"{event.event_type.value.removeprefix('OBJECT_'):<5}  "
                f"#{event.object_id}  {event.label}  · F{event.frame_index}"
            )
        self.event_list.clear()
        self.event_list.addItems(list(self._recent_events) or ["No event yet"])

    def _render_image(self) -> None:
        if self._last_image is None:
            return
        pixmap = QPixmap.fromImage(self._last_image).scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(pixmap)

    def _on_worker_summary(self, summary: WorkerSummary) -> None:
        record = summary.to_record()
        record.update(
            {
                "schema_version": 1,
                "milestone": "M5",
                "acceptance_status": "synthetic_offline_observation"
                if summary.source_type == "synthetic"
                else "pending_user_validation",
                "git": _git_state(),
                "environment": {
                    "platform": platform.platform(),
                    "python": platform.python_version(),
                    "pyside6": PySide6.__version__,
                },
                "vision_config": asdict(self.vision_config),
                "event_config": asdict(self.event_config),
                "gui_updates": self._gui_updates,
                "gui_update_fps": round(self._gui_updates / summary.duration_seconds, 6)
                if summary.duration_seconds
                else 0.0,
                "display_frames_dropped": max(0, summary.frames_processed - self._gui_updates),
                "buffer_overwrites": self._buffer.overwritten_count if self._buffer else 0,
                "clean_shutdown": summary.worker_clean_shutdown,
                **self.session_annotations,
            }
        )
        self.last_session_summary = record
        self.session_dir.mkdir(parents=True, exist_ok=True)
        safe_timestamp = summary.started_at.replace(":", "").replace("+", "_")
        path = self.session_dir / f"session-{safe_timestamp}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if summary.error:
            self.metrics["error"].setText(summary.error)
            self._set_state(GuiState.ERROR)

    def _on_thread_finished(self) -> None:
        had_error = self._state == GuiState.ERROR
        self._thread = None
        self._worker = None
        self._requests = None
        if not had_error:
            self._set_state(GuiState.IDLE)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render_image()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        mapping = {
            Qt.Key.Key_1: "normal_light",
            Qt.Key.Key_2: "bright_or_side_light",
            Qt.Key.Key_3: "dark_light",
            Qt.Key.Key_4: "partial_occlusion",
            Qt.Key.Key_5: "touching_or_merged",
        }
        if event.key() in mapping:
            self.request_evidence(mapping[event.key()])
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.is_running:
            self.stop_session(block=True)
        if self.is_running:
            self.metrics["error"].setText("Worker did not stop within 5 seconds")
            event.ignore()
            return
        event.accept()
