"""Bridge between M4 vision events, the conveyor simulation and the PLC sink."""

from __future__ import annotations

from typing import Iterable

from pc.communication.models import PlcCommandResult, PlcCommandStatus
from pc.communication.sink import PlcCommandSink
from pc.events.models import EventType, VisionEvent

from .config import SortingConfig
from .model import ConveyorSimulator, ConveyorSnapshot, SortingResult


class SortingController:
    """Turn confirmed objects into conveyor items and PLC commands.

    ``plc_trigger`` decides *when* the PLC command is written:

    * ``"exit"`` (default): after the item is ejected from its station, i.e. the
      demonstrated sorting result is what reaches the PLC.
    * ``"enter"``: the moment the object is recognised, matching the legacy M5
      behaviour where enqueue happens at recognition time.

    Either way the written command is the same frozen shape code, so the PLC
    queue order and the lamp count are identical.
    """

    def __init__(self, config: SortingConfig, sink: PlcCommandSink | None = None) -> None:
        config.validate()
        self.config = config
        self.sink = sink
        self.simulator = ConveyorSimulator(config)
        self.plc_results: list[PlcCommandResult] = []
        self.plc_error: str | None = None

    # ------------------------------------------------------------------ input

    def submit_events(self, events: Iterable[VisionEvent]) -> None:
        created = self.simulator.submit_events(events)
        if self.config.plc_trigger != "enter":
            return
        for item in created:
            if item.source_event is not None:
                self._dispatch(item.source_event, item.label, item.semantic_id, item.item_id)

    def advance(self, dt_seconds: float, frame_index: int | None = None) -> tuple[SortingResult, ...]:
        results = self.simulator.advance(dt_seconds, frame_index)
        if self.config.plc_trigger == "exit":
            for result in results:
                self._dispatch(
                    result.source_event,
                    result.label,
                    result.semantic_id,
                    result.item_id,
                )
        return results

    # ---------------------------------------------------------------- outputs

    def snapshot(self) -> ConveyorSnapshot:
        return self.simulator.snapshot()

    def close(self) -> None:
        if self.sink is None:
            return
        try:
            self.sink.stop()
        except Exception as error:  # pragma: no cover - defensive, mirrors the worker
            if self.plc_error is None:
                self.plc_error = f"{type(error).__name__}: {error}"

    # --------------------------------------------------------------- internal

    def _dispatch(
        self,
        source_event: VisionEvent | None,
        label: str,
        semantic_id: int,
        item_id: int,
    ) -> None:
        if self.sink is None:
            return
        event = source_event or VisionEvent(
            event_id=item_id,
            event_type=EventType.OBJECT_ENTER,
            object_id=semantic_id,
            label=label,
            confidence=1.0,
            frame_index=self.simulator.snapshot().frame_index,
        )
        try:
            outcome = self.sink.send_event(event)
        except Exception as error:
            self.plc_error = f"{type(error).__name__}: {error}"
            self.plc_results.append(
                PlcCommandResult(None, PlcCommandStatus.ERROR, detail=self.plc_error)
            )
            return
        self.plc_results.append(outcome)
        if outcome.status is PlcCommandStatus.ERROR and self.plc_error is None:
            self.plc_error = outcome.detail

    @property
    def plc_command_count(self) -> int:
        return sum(
            1 for result in self.plc_results if result.status is PlcCommandStatus.SENT
        )

    def plc_records(self) -> tuple[dict[str, object], ...]:
        return tuple(result.to_record() for result in self.plc_results)
