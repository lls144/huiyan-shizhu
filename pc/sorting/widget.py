"""QPainter rendering of the three-belt sorting animation.

The widget is presentation-only: it draws whatever immutable
``ConveyorSnapshot`` the worker last published. All sorting logic lives in
``pc/sorting/model.py``.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from .model import STAGES, ConveyorItemView, ConveyorSnapshot, ConveyorStage

_STAGE_RGB = {
    "triangle": (34, 197, 94),
    "rectangle": (59, 130, 246),
    "circle": (249, 115, 22),
}

BACKGROUND = QColor("#141414")
PANEL = QColor("#1d1d1d")
BELT_TOP = QColor("#3a3a3a")
BELT_BOTTOM = QColor("#242424")
BELT_EDGE = QColor("#4a4a4a")
STRIPE = QColor(255, 255, 255, 18)
TEXT = QColor("#d4d4d4")
MUTED = QColor("#8c8c8c")
STRONG = QColor("#f0f0f0")
LAMP_ON = QColor("#ffd45e")
LAMP_OFF = QColor("#3a3a3a")
BLOCK = QColor("#101010")


def stage_color(label: str) -> QColor:
    red, green, blue = _STAGE_RGB.get(label, (150, 150, 150))
    return QColor(red, green, blue)


def _belt_and_local(progress: float) -> tuple[int, float]:
    """Map a 0..3 belt position onto (segment index, 0..1 position inside it)."""

    clamped = max(0.0, min(progress, 3.0))
    index = min(int(clamped), 2)
    if clamped > 0 and clamped == int(clamped):
        index = int(clamped) - 1
    return index, max(0.0, min(clamped - index, 1.0))


class ConveyorWidget(QWidget):
    """Animated three-station conveyor sorted by the recognized shape label."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(720, 430)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._snapshot = ConveyorSnapshot(
            frame_index=0,
            items=(),
            pending_labels=(),
            results=(),
            last_result=None,
            lamp_state=(False, False, False),
        )
        self._flash = [0.0, 0.0, 0.0]
        self._gate_pulse = [0.0, 0.0]
        self._phase = 0.0
        self._last_result_item = -1
        self._progress_cache: dict[int, float] = {}
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # --------------------------------------------------------------- interface

    def set_snapshot(self, snapshot: ConveyorSnapshot) -> None:
        self._register_crossings(snapshot)
        self._snapshot = snapshot
        last = snapshot.last_result
        if last is not None and last.item_id != self._last_result_item:
            self._last_result_item = last.item_id
            self._flash[last.stage_index] = 1.0
        self.update()

    def _register_crossings(self, snapshot: ConveyorSnapshot) -> None:
        for item in snapshot.items:
            previous = self._progress_cache.get(item.item_id)
            if previous is not None:
                for gate in (1, 2):
                    if previous < gate <= item.progress and gate - 1 != item.stage_index:
                        self._gate_pulse[gate - 1] = 1.0
            self._progress_cache[item.item_id] = item.progress
        live = {item.item_id for item in snapshot.items}
        for stale in list(self._progress_cache):
            if stale not in live:
                self._progress_cache.pop(stale, None)

    def _tick(self) -> None:
        self._phase = (self._phase + 0.045) % 1.0
        for index in range(3):
            self._flash[index] = max(0.0, self._flash[index] - 0.03)
        for index in range(2):
            self._gate_pulse[index] = max(0.0, self._gate_pulse[index] - 0.02)
        self.update()

    # ----------------------------------------------------------------- painting

    def paintEvent(self, event: object) -> None:  # noqa: ARG002 - Qt signature
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.fillRect(self.rect(), BACKGROUND)
        if self.width() < 240 or self.height() < 200:
            painter.end()
            return
        geometry = self._geometry()
        self._paint_belts(painter, geometry)
        self._paint_items(painter, geometry)
        self._paint_toast(painter, geometry)
        painter.end()

    def _geometry(self) -> dict[str, float]:
        margin = 18.0
        gap = 12.0
        header_h = 30.0
        belt_h = 74.0
        bin_gap = 46.0
        bin_h = 82.0
        usable = self.width() - 2 * margin
        seg_w = max(60.0, (usable - 2 * gap) / 3.0)
        belt_top = margin + header_h
        bin_top = belt_top + belt_h + bin_gap
        if bin_top + bin_h > self.height() - margin:
            bin_top = max(belt_top + belt_h + 16.0, self.height() - margin - bin_h)
        return {
            "margin": margin,
            "gap": gap,
            "header_h": header_h,
            "belt_h": belt_h,
            "seg_w": seg_w,
            "belt_top": belt_top,
            "bin_top": bin_top,
            "bin_h": bin_h,
        }

    def _belt_left(self, geometry: dict[str, float], index: int) -> float:
        return geometry["margin"] + index * (geometry["seg_w"] + geometry["gap"])

    def _paint_belts(self, painter: QPainter, geometry: dict[str, float]) -> None:
        for index, stage in enumerate(STAGES):
            left = self._belt_left(geometry, index)
            width = geometry["seg_w"]
            accent = stage_color(stage.key)
            top = geometry["belt_top"]
            height = geometry["belt_h"]

            font = painter.font()
            font.setPointSize(11)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(accent))
            painter.drawText(
                QRectF(left, geometry["margin"] - 4, width, geometry["header_h"]),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"  第 {stage.number} 段 · {stage.label_zh}",
            )

            belt = QRectF(left, top, width, height)
            gradient = QLinearGradient(belt.topLeft(), belt.bottomLeft())
            gradient.setColorAt(0.0, BELT_TOP)
            gradient.setColorAt(1.0, BELT_BOTTOM)
            painter.setPen(QPen(BELT_EDGE, 1.4))
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(belt, 8.0, 8.0)

            painter.save()
            painter.setClipRect(belt.adjusted(2, 2, -2, -2))
            painter.setPen(QPen(STRIPE, 6.0))
            stripe_spacing = 34.0
            offset = (self._phase * stripe_spacing) % stripe_spacing
            stripe_x = left - height + offset
            while stripe_x < left + width + height:
                painter.drawLine(
                    QPointF(stripe_x, top + height),
                    QPointF(stripe_x + height, top),
                )
                stripe_x += stripe_spacing
            painter.restore()

            self._paint_gate(painter, geometry, index, accent)
            self._paint_bin(painter, geometry, index, stage, accent)

    def _paint_gate(
        self,
        painter: QPainter,
        geometry: dict[str, float],
        index: int,
        accent: QColor,
    ) -> None:
        if index >= 2:
            return
        left = self._belt_left(geometry, index)
        gate_x = left + geometry["seg_w"]
        top = geometry["belt_top"]
        height = geometry["belt_h"]
        pulse = self._gate_pulse[index]
        painter.setPen(QPen(QColor(255, 255, 255, 60 + int(120 * pulse)), 1.2))
        painter.drawLine(QPointF(gate_x + geometry["gap"] / 2, top), QPointF(gate_x + geometry["gap"] / 2, top + height))
        chevron = QPolygonF(
            [
                QPointF(gate_x + geometry["gap"] / 2 - 4, top + height / 2 - 6),
                QPointF(gate_x + geometry["gap"] / 2 + 4, top + height / 2),
                QPointF(gate_x + geometry["gap"] / 2 - 4, top + height / 2 + 6),
            ]
        )
        painter.setBrush(QBrush(QColor(accent.red(), accent.green(), accent.blue(), 120)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(chevron)
        if pulse > 0.05:
            font = painter.font()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
        painter.setPen(QPen(QColor(255, 210, 120, int(255 * pulse))))
        painter.drawText(
                QRectF(gate_x - 46, top + 4, 92, 18),
                Qt.AlignmentFlag.AlignCenter,
                "不符合 · 放行",
            )

    def _paint_bin(
        self,
        painter: QPainter,
        geometry: dict[str, float],
        index: int,
        stage: ConveyorStage,
        accent: QColor,
    ) -> None:
        left = self._belt_left(geometry, index)
        width = geometry["seg_w"]
        top = geometry["bin_top"]
        height = geometry["bin_h"]
        flash = self._flash[index]
        bin_rect = QRectF(left, top, width, height)
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 90 + int(160 * flash)), 1.6))
        painter.setBrush(QBrush(QColor(accent.red(), accent.green(), accent.blue(), 16 + int(50 * flash))))
        painter.drawRoundedRect(bin_rect, 8.0, 8.0)

        for lamp in range(3):
            center = QPointF(left + 20 + lamp * 20, top + 20)
            lit = lamp < stage.lamp_count
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(LAMP_ON if lit else LAMP_OFF))
            painter.drawEllipse(center, 6.0, 6.0)
            if lit and flash > 0.02:
                painter.setBrush(QBrush(QColor(255, 212, 94, int(120 * flash))))
                painter.drawEllipse(center, 11.0, 11.0)

        font = painter.font()
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QPen(MUTED))
        painter.drawText(
            QRectF(left + 80, top + 8, width - 88, 24),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"出队 → {stage.lamp_count} 盏灯",
        )

        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(accent if flash > 0.02 else MUTED))
        message = "示意中…" if flash > 0.02 else "等待物料"
        painter.drawText(
            QRectF(left + 12, top + 34, width - 24, height - 40),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            message,
        )

    def _paint_items(self, painter: QPainter, geometry: dict[str, float]) -> None:
        for item in self._snapshot.items:
            self._paint_item(painter, geometry, item)

    def _paint_item(
        self,
        painter: QPainter,
        geometry: dict[str, float],
        item: ConveyorItemView,
    ) -> None:
        index, local = _belt_and_local(item.progress)
        left = self._belt_left(geometry, index)
        x = left + local * geometry["seg_w"]
        belt_center_y = geometry["belt_top"] + geometry["belt_h"] / 2
        size = 50.0
        color = stage_color(item.label)
        y = belt_center_y
        alpha = 255
        scale = 1.0
        if item.state == "ejecting":
            travel = item.eject_fraction
            y = belt_center_y + travel * (geometry["bin_top"] + 26 - belt_center_y)
            scale = 1.0 - 0.25 * travel
            alpha = int(255 * (1.0 - 0.55 * travel))

        half = size * scale / 2.0
        rect = QRectF(x - half, y - half, half * 2, half * 2)
        painter.save()
        painter.setOpacity(alpha / 255.0)
        glow = QColor(color.red(), color.green(), color.blue(), 70)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawRoundedRect(rect.adjusted(-5, -5, 5, 5), 12.0, 12.0)
        painter.setPen(QPen(color, 2.0))
        painter.setBrush(QBrush(BLOCK))
        painter.drawRoundedRect(rect, 9.0, 9.0)
        self._paint_shape(painter, rect, item.label, color)
        painter.restore()

    @staticmethod
    def _paint_shape(painter: QPainter, rect: QRectF, label: str, color: QColor) -> None:
        inner = rect.adjusted(11, 11, -11, -11)
        painter.setPen(QPen(color, 2.0))
        painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 70)))
        if label == "triangle":
            points = QPolygonF(
                [
                    QPointF(inner.center().x(), inner.top()),
                    QPointF(inner.right(), inner.bottom()),
                    QPointF(inner.left(), inner.bottom()),
                ]
            )
            painter.drawPolygon(points)
        elif label == "rectangle":
            painter.drawRect(inner)
        else:
            painter.drawEllipse(inner)

    def _paint_toast(self, painter: QPainter, geometry: dict[str, float]) -> None:
        last = self._snapshot.last_result
        if last is None:
            return
        flash = self._flash[last.stage_index]
        if flash <= 0.02:
            return
        index = last.stage_index
        left = self._belt_left(geometry, index)
        width = geometry["seg_w"]
        rect = QRectF(left + 8, geometry["belt_top"] + 8, width - 16, 26)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(20, 20, 20, int(220 * flash))))
        painter.drawRoundedRect(rect, 6.0, 6.0)
        font = painter.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255, int(255 * flash))))
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            f"#{last.item_id} {STAGES[index].label_zh} 离开 · {last.lamp_count} 盏灯",
        )

    # -------------------------------------------------------------- diagnostics

    def snapshot(self) -> ConveyorSnapshot:
        return self._snapshot

    def stop_animation(self) -> None:
        self._timer.stop()
