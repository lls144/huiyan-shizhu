"""PySide6 window that presents the conveyor sorting animation."""

from __future__ import annotations

import json
import platform
from collections import deque
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Sequence

import PySide6
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QColor, QCloseEvent, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pc.communication.sink import PlcCommandSink
from pc.events.config import EventConfig
from pc.gui.models import GuiState, WorkerSummary
from pc.gui.sources import FrameSource
from pc.gui.theme import APP_STYLE, THEME, load_ui_fonts
from pc.gui.window import bgr_to_qimage
from pc.gui.worker import Analyzer, EvidenceRequestBuffer, LatestSnapshotBuffer
from pc.vision.config import VisionConfig
from pc.vision.live import _git_state

from .config import SortingConfig
from .model import STAGES, SortingResult
from .widget import ConveyorWidget
from .worker import ControlRequestBuffer, SortingVisionWorker

SourceFactory = Callable[[], FrameSource]

SHAPE_TINT = {"triangle": "#22c55e", "rectangle": "#3b82f6", "circle": "#f97316"}


def _divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line


def _section(title: str, content: QWidget) -> QWidget:
    section = QWidget()
    layout = QVBoxLayout(section)
    layout.setContentsMargins(12, 8, 10, 6)
    layout.setSpacing(4)
    heading = QLabel(title.upper())
    heading.setObjectName("sectionTitle")
    layout.addWidget(heading)
    layout.addWidget(content, 1)
    return section


def _tool_button(text: str, object_name: str = "") -> QToolButton:
    button = QToolButton()
    button.setText(text)
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
    if object_name:
        button.setObjectName(object_name)
    return button


def _set_dynamic_property(widget: QWidget, name: str, value: object) -> None:
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class SortingWindow(QMainWindow):
    """Live camera view + three-belt animation + PLC command bridge."""

    def __init__(
        self,
        source_factory: SourceFactory,
        source_type: str,
        vision_config: VisionConfig,
        event_config: EventConfig,
        sorting_config: SortingConfig,
        session_dir: Path,
        evidence_root: Path,
        expected_labels: Sequence[str],
        analyzer: Analyzer,
        command_sink: PlcCommandSink | None = None,
    ) -> None:
        super().__init__()
        load_ui_fonts()
        self.source_factory = source_factory
        self.source_type = source_type
        self.vision_config = vision_config
        self.event_config = event_config
        self.sorting_config = sorting_config
        self.session_dir = session_dir
        self.evidence_root = evidence_root
        self.expected_labels = tuple(expected_labels)
        self.analyzer = analyzer
        self.command_sink = command_sink
        self._thread: QThread | None = None
        self._worker: SortingVisionWorker | None = None
        self._buffer: LatestSnapshotBuffer | None = None
        self._requests: EvidenceRequestBuffer | None = None
        self._last_image: QImage | None = None
        self._last_frame_index = -1
        self._gui_updates = 0
        self._recent_detections: deque[str] = deque(maxlen=40)
        self._sorting_results: list[SortingResult] = []
        self._pending_labels: tuple[str, ...] = ()
        self._plc_state: dict[str, object] | None = None
        self._plc_error: str | None = None
        self._controls = ControlRequestBuffer()
        self._state = GuiState.IDLE
        self.last_session_summary: dict[str, object] | None = None
        self.session_annotations: dict[str, object] = {}
        self._build_ui()
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("慧眼识珠 · 分拣流水线模拟 (三节传送带)")
        self.setMinimumSize(1120, 680)
        self.resize(1440, 820)
        self._render_mapping()
        self.plc_enabled_value.setText(
            "disabled" if self.command_sink is None else "connecting…"
        )
        self._set_state(GuiState.IDLE)

    # ------------------------------------------------------------------ layout

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_application_bar())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_workspace())
        splitter.addWidget(self._build_inspector())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1040, 390])
        outer.addWidget(splitter, 1)
        self.setCentralWidget(root)
        self._build_status_bar()

    def _build_application_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("applicationBar")
        bar.setFixedHeight(THEME.app_bar_height)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)
        title = QLabel("慧眼识珠")
        title.setObjectName("appTitle")
        subtitle = QLabel("SORTING LINE SIMULATION · 三节传送带")
        subtitle.setObjectName("appSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        self.state_dot = QLabel("●")
        self.state_dot.setObjectName("stateDot")
        self.state_text = QLabel("Idle")
        self.state_text.setObjectName("stateText")
        layout.addWidget(self.state_dot)
        layout.addWidget(self.state_text)
        return bar

    def _build_workspace(self) -> QFrame:
        workspace = QFrame()
        workspace.setObjectName("workspace")
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QFrame()
        toolbar.setObjectName("workspaceToolbar")
        toolbar.setFixedHeight(THEME.workspace_bar_height)
        tools = QHBoxLayout(toolbar)
        tools.setContentsMargins(10, 0, 8, 0)
        tools.setSpacing(5)
        heading = QLabel("CONVEYOR")
        heading.setObjectName("workspaceTitle")
        self.source_badge = QLabel(self.source_type.upper())
        self.source_badge.setObjectName("sourceBadge")
        tools.addWidget(heading)
        tools.addWidget(self.source_badge)
        tools.addStretch()
        self.start_button = _tool_button("Start", "startTool")
        self.stop_button = _tool_button("Stop")
        self.start_button.clicked.connect(self.start_session)
        self.stop_button.clicked.connect(self.stop_session)
        tools.addWidget(self.start_button)
        tools.addWidget(self.stop_button)
        layout.addWidget(toolbar)

        self.conveyor = ConveyorWidget(max_pending=self.sorting_config.max_pending_items)
        layout.addWidget(self.conveyor, 1)

        preview_bar = QFrame()
        preview_bar.setObjectName("evidenceToolbar")
        preview_layout = QHBoxLayout(preview_bar)
        preview_layout.setContentsMargins(10, 6, 10, 8)
        preview_layout.setSpacing(10)
        self.preview_label = QLabel("Camera preview")
        self.preview_label.setObjectName("video")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedSize(240, 135)
        preview_layout.addWidget(self.preview_label)
        self.preview_hint = QLabel(
            "把物体放进画面中央并停住约 1 秒；识别后物料块会进入第 1 段传送带。"
        )
        self.preview_hint.setObjectName("metadataKey")
        self.preview_hint.setWordWrap(True)
        preview_layout.addWidget(self.preview_hint, 1)
        layout.addWidget(preview_bar)
        return workspace

    def _build_inspector(self) -> QFrame:
        inspector = QFrame()
        inspector.setObjectName("inspector")
        inspector.setMinimumWidth(THEME.sidebar_min_width)
        inspector.setMaximumWidth(THEME.sidebar_max_width + 80)
        layout = QVBoxLayout(inspector)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QWidget()
        header.setFixedHeight(THEME.workspace_bar_height)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 10, 0)
        title = QLabel("SORTING INSPECTOR")
        title.setObjectName("inspectorTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addWidget(header)
        layout.addWidget(_divider())

        self.map_list = QListWidget()
        self.map_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(_section("形状 → 灯 映射", self.map_list))
        layout.addWidget(_divider())

        plc = QWidget()
        plc_layout = QVBoxLayout(plc)
        plc_layout.setContentsMargins(0, 0, 0, 0)
        plc_layout.setSpacing(6)
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        self.plc_enabled_value = QLabel("—")
        self.plc_queue_value = QLabel("—")
        self.plc_full_value = QLabel("—")
        self.plc_led_value = QLabel("—")
        self.plc_deferred_value = QLabel("—")
        self.plc_resend_value = QLabel("—")
        self.plc_unconfirmed_value = QLabel("—")
        self.plc_heartbeat_value = QLabel("—")
        self.plc_link_value = QLabel("—")
        self.plc_error_value = QLabel("No errors")
        self.plc_error_value.setObjectName("errorValue")
        self.plc_error_value.setWordWrap(True)
        rows = (
            ("Bridge", self.plc_enabled_value),
            ("Queue length", self.plc_queue_value),
            ("Queue full", self.plc_full_value),
            ("Real LEDs", self.plc_led_value),
            ("Deferred (queue full)", self.plc_deferred_value),
            ("Resends / timeouts", self.plc_resend_value),
            ("Unconfirmed", self.plc_unconfirmed_value),
            ("Heartbeat", self.plc_heartbeat_value),
            ("Link (COMM-002)", self.plc_link_value),
            ("Last error", self.plc_error_value),
        )
        for row, (key_text, value) in enumerate(rows):
            key = QLabel(key_text)
            key.setObjectName("metadataKey")
            value.setObjectName("metadataValue")
            grid.addWidget(key, row, 0)
            grid.addWidget(value, row, 1)
        plc_layout.addWidget(grid_host)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(5)
        self.dequeue_button = _tool_button("出队（等同按键）")
        self.reset_button = _tool_button("复位")
        self.dequeue_button.clicked.connect(lambda: self._send_control("dequeue"))
        self.reset_button.clicked.connect(lambda: self._send_control("reset"))
        buttons.addWidget(self.dequeue_button)
        buttons.addWidget(self.reset_button)
        buttons.addStretch()
        plc_layout.addLayout(buttons)
        layout.addWidget(_section("PLC", plc))
        layout.addWidget(_divider())

        self.log_list = QListWidget()
        layout.addWidget(_section("分拣日志", self.log_list), 2)
        layout.addWidget(_divider())
        self.detection_list = QListWidget()
        layout.addWidget(_section("本帧识别", self.detection_list), 1)
        return inspector

    def _build_status_bar(self) -> None:
        bar = QStatusBar()
        bar.setObjectName("statusBar")
        bar.setSizeGripEnabled(False)
        self.setStatusBar(bar)
        self.status_source = QLabel("SOURCE —")
        self.status_fps = QLabel("— FPS")
        self.status_frame = QLabel("FRAME —")
        self.status_pending = QLabel("QUEUE —")
        self.status_state = QLabel("IDLE")
        self.status_source.setObjectName("statusSource")
        self.status_state.setObjectName("statusState")
        for widget in (self.status_fps, self.status_frame, self.status_pending):
            widget.setObjectName("statusItem")
        for widget in (
            self.status_source,
            self.status_fps,
            self.status_frame,
            self.status_pending,
        ):
            bar.addWidget(widget)
        bar.addPermanentWidget(self.status_state)

    def _render_mapping(self) -> None:
        self.map_list.clear()
        for stage in STAGES:
            item = QListWidgetItem(
                f" 第{stage.number}段 {stage.label_zh:<4}→ 亮 {stage.lamp_count} 盏灯"
                f"   (code {stage.shape_code})"
            )
            item.setForeground(QColor(SHAPE_TINT[stage.key]))
            self.map_list.addItem(item)
        self.map_list.setFixedHeight(3 * 26 + 8)

    # ------------------------------------------------------------------ state

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    @property
    def state(self) -> GuiState:
        return self._state

    @property
    def sorting_results(self) -> tuple[SortingResult, ...]:
        return tuple(self._sorting_results)

    def _set_state(self, state: GuiState) -> None:
        self._state = state
        self.state_text.setText(state.value.title())
        self.status_state.setText(state.value.upper())
        _set_dynamic_property(self.state_dot, "state", state.value)
        active = state in {GuiState.STARTING, GuiState.RUNNING, GuiState.STOPPING}
        self.start_button.setEnabled(not active)
        self.stop_button.setEnabled(state in {GuiState.STARTING, GuiState.RUNNING})
        plc_ready = state is GuiState.RUNNING and self.command_sink is not None
        self.dequeue_button.setEnabled(plc_ready)
        self.reset_button.setEnabled(plc_ready)

    def _send_control(self, action: str) -> None:
        if not self.is_running or self.command_sink is None:
            return
        self._controls.request(action)
        self.statusBar().showMessage(
            "已请求出队（等同按下实验箱出队键）" if action == "dequeue" else "已请求复位", 2500
        )

    # -------------------------------------------------------------- lifecycle

    def start_session(self) -> None:
        if self.is_running:
            return
        self._last_frame_index = -1
        self._gui_updates = 0
        self._recent_detections.clear()
        self._sorting_results.clear()
        self._plc_state = None
        self.log_list.clear()
        self.detection_list.clear()
        self.plc_error_value.setText("No errors")
        _set_dynamic_property(self.plc_error_value, "hasError", False)
        self._buffer = LatestSnapshotBuffer()
        self._requests = EvidenceRequestBuffer()
        source = self.source_factory()
        thread = QThread(self)
        worker = SortingVisionWorker(
            source,
            self.vision_config,
            self.event_config,
            self._buffer,
            self._requests,
            self.evidence_root,
            self.expected_labels,
            self.sorting_config,
            self.analyzer,
            self.command_sink,
            self._controls,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.snapshot_available.connect(self._consume_latest)
        worker.sorting_updated.connect(self._on_sorting_updated)
        worker.sorting_result.connect(self._on_sorting_result)
        worker.plc_state_updated.connect(self._on_plc_state)
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

    def _on_worker_state(self, value: str) -> None:
        self._set_state(GuiState(value))

    def _on_thread_finished(self) -> None:
        had_error = self._state == GuiState.ERROR
        self._thread = None
        self._worker = None
        self._requests = None
        if not had_error:
            self._set_state(GuiState.IDLE)

    # ---------------------------------------------------------------- updates

    def _consume_latest(self) -> None:
        if self._buffer is None:
            return
        snapshot = self._buffer.take_latest()
        if snapshot is None or snapshot.frame_index <= self._last_frame_index:
            return
        self._last_frame_index = snapshot.frame_index
        self._gui_updates += 1
        self._last_image = bgr_to_qimage(snapshot.annotated_frame)
        self._render_preview()
        self.status_source.setText(snapshot.source_type.upper())
        self.status_fps.setText(f"{snapshot.processed_fps:.1f} FPS")
        self.status_frame.setText(f"FRAME {snapshot.frame_index}")

        self.detection_list.clear()
        for detection in snapshot.detections:
            label = detection.label
            self.detection_list.addItem(
                f"{label:<10}{detection.confidence * 100:>6.1f}%"
            )
        if not snapshot.detections:
            muted = QListWidgetItem("No detections")
            muted.setForeground(QColor(THEME.muted_text))
            self.detection_list.addItem(muted)

    def _on_sorting_updated(self, snapshot: object) -> None:
        self.conveyor.set_snapshot(snapshot)  # type: ignore[arg-type]
        self._pending_labels = snapshot.pending_labels  # type: ignore[attr-defined]
        waiting = len(self._pending_labels)
        self.status_pending.setText(
            f"QUEUE {waiting}" + (f" ({', '.join(self._pending_labels)})" if waiting else "")
        )

    def _on_sorting_result(self, result: SortingResult) -> None:
        self._sorting_results.append(result)
        label_item = QListWidgetItem(
            f"#{result.item_id:<3}{result.label:<10}离开第{result.stage_index + 1}段 → "
            f"{result.lamp_count} 盏灯"
        )
        label_item.setForeground(QColor(SHAPE_TINT.get(result.label, "#d4d4d4")))
        self.log_list.insertItem(0, label_item)
        self.statusBar().showMessage(
            f"分拣完成 · {result.label} → {result.lamp_count} 盏灯", 2500
        )

    def _on_plc_state(self, payload: object) -> None:
        data = payload if isinstance(payload, dict) else {}
        if "error" in data:
            self._plc_error = str(data["error"])
            self.plc_error_value.setText(self._plc_error)
            _set_dynamic_property(self.plc_error_value, "hasError", True)
            return
        state = data.get("status") or data.get("state")
        if not isinstance(state, dict):
            self.plc_enabled_value.setText(
                "disabled" if self.command_sink is None else "no state"
            )
            self.plc_queue_value.setText("—")
            self.plc_led_value.setText("—")
            return
        self._plc_state = state
        counters = state.get("counters") or {}
        self.plc_enabled_value.setText("connected" if state.get("connected", True) else "no state")
        self.plc_queue_value.setText(f"{state.get('queue_length', '—')}")
        leds = state.get("leds") or [False, False, False]
        self.plc_led_value.setText("".join("●" if led else "○" for led in leds))
        full = state.get("queue_full")
        if full is None:
            self.plc_full_value.setText("—")
        else:
            self.plc_full_value.setText("FULL（队列满）" if full else "ok")
            _set_dynamic_property(self.plc_full_value, "hasError", bool(full))
        self.plc_deferred_value.setText(f"{state.get('deferred_count', 0)} 条待入队")
        self.plc_resend_value.setText(
            f"{counters.get('write_resends', 0)} / {counters.get('timeouts', 0)}"
        )
        self.plc_unconfirmed_value.setText(f"{counters.get('unconfirmed', 0)} 笔待核实")
        health = data.get("health")
        if isinstance(health, dict):
            if not health.get("enabled"):
                self.plc_heartbeat_value.setText("disabled")
            else:
                self.plc_heartbeat_value.setText(
                    f"{health.get('heartbeat_count', 0)} 次 · 均值 "
                    f"{health.get('heartbeat_interval_mean_seconds', 0):.2f} s"
                )
            if health.get("comm_lost"):
                self.plc_link_value.setText(
                    f"通信中断 {health.get('comm_lost_for_seconds', 0):.1f} s"
                )
                _set_dynamic_property(self.plc_link_value, "hasError", True)
            else:
                outages = health.get("outage_count", 0)
                self.plc_link_value.setText(
                    "正常" + (f"（历史中断 {outages} 次）" if outages else "")
                )
                _set_dynamic_property(self.plc_link_value, "hasError", False)

    def _render_preview(self) -> None:
        if self._last_image is None:
            return
        pixmap = QPixmap.fromImage(self._last_image).scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(pixmap)

    # ---------------------------------------------------------------- summary

    def _on_worker_summary(self, summary: WorkerSummary) -> None:
        results = tuple(result.to_record() for result in self._sorting_results)
        record = summary.to_record()
        record.update(
            {
                "schema_version": 1,
                "milestone": "M-SORTING-VIZ",
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
                "sorting_config": asdict(self.sorting_config),
                "shape_to_lamp_map": {
                    stage.key: stage.lamp_count for stage in STAGES
                },
                "plc_enabled": self.command_sink is not None,
                "plc_state_last": self._plc_state,
                "plc_dispatch_count": len(summary.plc_results),
                "plc_status_counts": {
                    status: sum(
                        1 for item in summary.plc_results if item.get("status") == status
                    )
                    for status in sorted(
                        {str(item.get("status")) for item in summary.plc_results}
                    )
                },
                "plc_sent_count": sum(
                    1 for item in summary.plc_results if item.get("status") == "SENT"
                ),
                "plc_error_count": sum(
                    1
                    for item in summary.plc_results
                    if item.get("status") in ("ERROR", "UNCONFIRMED")
                ),
                "sorting_results": list(results),
                "sorting_result_count": len(results),
                "sorting_results_by_shape": {
                    stage.key: sum(1 for item in results if item["label"] == stage.key)
                    for stage in STAGES
                },
                "gui_updates": self._gui_updates,
                "clean_shutdown": summary.worker_clean_shutdown,
                **self.session_annotations,
            }
        )
        self.last_session_summary = record
        self.session_dir.mkdir(parents=True, exist_ok=True)
        safe_timestamp = summary.started_at.replace(":", "").replace("+", "_")
        path = self.session_dir / f"sorting-session-{safe_timestamp}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if summary.error:
            self.plc_error_value.setText(summary.error)
            _set_dynamic_property(self.plc_error_value, "hasError", True)
            self._set_state(GuiState.ERROR)

    # ----------------------------------------------------------------- events

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render_preview()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.is_running:
            self.stop_session(block=True)
        if self.is_running:
            event.ignore()
            return
        self.conveyor.stop_animation()
        event.accept()
