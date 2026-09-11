"""Deterministic three-station conveyor sorting simulation.

Scope and honesty notes (read before quoting this in a report)
-------------------------------------------------------------
* This module performs **no shape recognition**. Every item carries the label
  that the M2/M3 vision pipeline already produced and that the M4 event tracker
  already confirmed. The belts are *decision stations*, not a second classifier.
* Station order is the order the operator asked for: triangle, then rectangle,
  then circle. An item leaves the belt at the first station whose shape equals
  its label; otherwise it rides on to the next station, so the last station
  (circle) receives everything that was not rejected earlier.
* Because the label is already known, the animation is a *presentation* of the
  classification result. It must not be reported as a new recognition
  capability or as extra vision evidence.
* Lamp counts follow the frozen PC/PLC shape codes:
  triangle -> 1 lamp, rectangle -> 2 lamps, circle -> 3 lamps.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from pc.events.models import EventType, VisionEvent

from .config import SortingConfig

RIDING = "riding"
EJECTING = "ejecting"
DONE = "done"


@dataclass(frozen=True)
class ConveyorStage:
    """One belt segment: the shape it accepts and the lamp result it produces."""

    key: str
    label_zh: str
    shape_code: int
    lamp_count: int
    number: int


STAGES: tuple[ConveyorStage, ...] = (
    ConveyorStage(key="triangle", label_zh="三角形", shape_code=1, lamp_count=1, number=1),
    ConveyorStage(key="rectangle", label_zh="矩形", shape_code=2, lamp_count=2, number=2),
    ConveyorStage(key="circle", label_zh="圆形", shape_code=3, lamp_count=3, number=3),
)

STAGE_BY_KEY = {stage.key: stage for stage in STAGES}


def stage_index_for_label(label: str) -> int | None:
    """Return the station that accepts ``label``, or ``None`` for unknown input."""

    for index, stage in enumerate(STAGES):
        if stage.key == label:
            return index
    return None


@dataclass
class ConveyorItem:
    """Mutable in-flight item owned by :class:`ConveyorSimulator`."""

    item_id: int
    label: str
    stage_index: int
    semantic_id: int
    source_event: VisionEvent | None = None
    progress: float = 0.0
    state: str = RIDING
    eject_elapsed: float = 0.0

    @property
    def gate(self) -> float:
        """Belt position of the ejector this item must stop at."""

        return float(self.stage_index + 1)


@dataclass(frozen=True)
class ConveyorItemView:
    """Immutable render view of one in-flight item."""

    item_id: int
    label: str
    stage_index: int
    progress: float
    state: str
    eject_fraction: float


@dataclass(frozen=True)
class SortingResult:
    """One completed sorting action: where the item left and how many lamps."""

    item_id: int
    label: str
    shape_code: int
    lamp_count: int
    stage_index: int
    semantic_id: int
    source_event_id: int | None
    frame_index: int
    source_event: VisionEvent | None = field(default=None, compare=False)

    @property
    def lamps(self) -> tuple[bool, bool, bool]:
        return tuple(index < self.lamp_count for index in range(3))  # type: ignore[return-value]

    def to_record(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "label": self.label,
            "shape_code": self.shape_code,
            "lamp_count": self.lamp_count,
            "stage_index": self.stage_index,
            "stage_key": STAGES[self.stage_index].key,
            "semantic_id": self.semantic_id,
            "source_event_id": self.source_event_id,
            "frame_index": self.frame_index,
            "lamps": list(self.lamps),
        }


@dataclass(frozen=True)
class ConveyorSnapshot:
    """Immutable hand-off from the worker thread to the Qt widget."""

    frame_index: int
    items: tuple[ConveyorItemView, ...]
    pending_labels: tuple[str, ...]
    results: tuple[SortingResult, ...]
    last_result: SortingResult | None
    lamp_state: tuple[bool, bool, bool]


class ConveyorSimulator:
    """Pure, frame-driven state machine; no Qt, no wall-clock, no PLC."""

    def __init__(self, config: SortingConfig) -> None:
        config.validate()
        self.config = config
        self._items: list[ConveyorItem] = []
        self._pending: deque[tuple[str, int, VisionEvent | None]] = deque()
        self._results: list[SortingResult] = []
        self._lamp_state: tuple[bool, bool, bool] = (False, False, False)
        self._next_item_id = 1
        self._frame_index = 0
        self.rejected_labels: list[str] = []

    # ------------------------------------------------------------------ input

    def submit(
        self,
        label: str,
        semantic_id: int,
        source_event: VisionEvent | None = None,
    ) -> ConveyorItem | None:
        """Queue one already-recognized object for sorting.

        Returns ``None`` when the label has no station (for example ``unknown``)
        or when the entrance queue is already full.
        """

        if stage_index_for_label(label) is None:
            self.rejected_labels.append(label)
            return None
        if len(self._pending) >= self.config.max_pending_items:
            self.rejected_labels.append(label)
            return None
        self._pending.append((label, semantic_id, source_event))
        return self._release_pending()

    def submit_events(self, events: Iterable[VisionEvent]) -> list[ConveyorItem]:
        """Feed M4 events; only confirmed ``OBJECT_ENTER`` rows create items."""

        created: list[ConveyorItem] = []
        for event in events:
            if event.event_type is not EventType.OBJECT_ENTER:
                continue
            item = self.submit(event.label, event.object_id, event)
            if item is not None:
                created.append(item)
        return created

    # ------------------------------------------------------------- simulation

    def advance(self, dt_seconds: float, frame_index: int | None = None) -> tuple[SortingResult, ...]:
        """Advance the belts by ``dt_seconds`` and return newly finished items."""

        if dt_seconds < 0:
            raise ValueError("dt_seconds must be non-negative")
        if frame_index is not None:
            self._frame_index = frame_index
        self._release_pending()
        step = self.config.belt_speed_units_per_second * dt_seconds
        completed: list[SortingResult] = []
        ahead_progress: float | None = None
        for item in sorted(self._items, key=lambda entry: entry.item_id):
            if item.state == RIDING:
                target = item.progress + step
                if ahead_progress is not None:
                    target = min(target, ahead_progress - self.config.min_gap_units)
                item.progress = max(item.progress, target)
                if item.progress >= item.gate:
                    item.progress = item.gate
                    item.state = EJECTING
                    item.eject_elapsed = 0.0
            if item.state == EJECTING:
                item.eject_elapsed += dt_seconds
                if item.eject_elapsed >= self.config.eject_seconds:
                    item.state = DONE
                    result = self._complete(item)
                    self._results.append(result)
                    self._lamp_state = result.lamps
                    completed.append(result)
                    ahead_progress = item.gate
                    continue
            ahead_progress = item.progress
        if completed:
            self._items = [item for item in self._items if item.state != DONE]
        return tuple(completed)

    # ---------------------------------------------------------------- outputs

    @property
    def results(self) -> tuple[SortingResult, ...]:
        return tuple(self._results)

    @property
    def lamp_state(self) -> tuple[bool, bool, bool]:
        return self._lamp_state

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def snapshot(self) -> ConveyorSnapshot:
        views = tuple(
            ConveyorItemView(
                item_id=item.item_id,
                label=item.label,
                stage_index=item.stage_index,
                progress=item.progress,
                state=item.state,
                eject_fraction=min(1.0, item.eject_elapsed / self.config.eject_seconds)
                if item.state == EJECTING
                else 0.0,
            )
            for item in sorted(self._items, key=lambda entry: entry.progress, reverse=True)
        )
        return ConveyorSnapshot(
            frame_index=self._frame_index,
            items=views,
            pending_labels=tuple(entry[0] for entry in self._pending),
            results=tuple(self._results),
            last_result=self._results[-1] if self._results else None,
            lamp_state=self._lamp_state,
        )

    # --------------------------------------------------------------- internal

    def _release_pending(self) -> ConveyorItem | None:
        if not self._pending:
            return None
        if self._items:
            newest = max(self._items, key=lambda entry: entry.item_id)
            if newest.progress < self.config.min_gap_units:
                return None
        label, semantic_id, source_event = self._pending.popleft()
        stage_index = stage_index_for_label(label)
        if stage_index is None:
            self.rejected_labels.append(label)
            return None
        item = ConveyorItem(
            item_id=self._next_item_id,
            label=label,
            stage_index=stage_index,
            semantic_id=semantic_id,
            source_event=source_event,
        )
        self._items.append(item)
        self._next_item_id += 1
        return item

    def _complete(self, item: ConveyorItem) -> SortingResult:
        stage = STAGES[item.stage_index]
        return SortingResult(
            item_id=item.item_id,
            label=item.label,
            shape_code=stage.shape_code,
            lamp_count=stage.lamp_count,
            stage_index=item.stage_index,
            semantic_id=item.semantic_id,
            source_event_id=item.source_event.event_id if item.source_event else None,
            frame_index=self._frame_index,
            source_event=item.source_event,
        )
