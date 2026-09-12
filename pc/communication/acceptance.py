"""Deterministic offline non-vision acceptance using synthetic events + fake PLC."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from pc.events.models import EventType, VisionEvent

from .config import PlcCommunicationConfig
from .fake_plc import FakeAcceptancePlc
from .models import PlcCommandResult, PlcCommandStatus, PlcState
from .s7 import PlcControls
from .sink import S7PlcCommandSink


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _enter_event(label: str, object_id: int) -> VisionEvent:
    return VisionEvent(
        event_id=object_id,
        event_type=EventType.OBJECT_ENTER,
        object_id=object_id,
        label=label,
        confidence=0.95,
        frame_index=object_id,
    )


def _config() -> PlcCommunicationConfig:
    return PlcCommunicationConfig(
        enabled=True,
        db_number=12,
        auto_dequeue=False,
        command_pulse_seconds=0.0,
        dequeue_pulse_seconds=0.0,
        reset_pulse_seconds=0.0,
    )


def _fresh_sink() -> tuple[S7PlcCommandSink, FakeAcceptancePlc]:
    plc = FakeAcceptancePlc()
    sink = S7PlcCommandSink(_config(), low_level=plc)
    sink.start()
    return sink, plc


def _state(sink: S7PlcCommandSink) -> PlcState:
    state = sink.read_state()
    if state is None:
        raise AssertionError("fake PLC status could not be read")
    return state


def _assert(condition: bool, message: str, state: PlcState) -> None:
    if not condition:
        raise AssertionError(f"{message}; state={state.to_record()}")


def _single_shape_mapping() -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    expected: list[dict[str, Any]] = []
    for shape, code, leds in (
        ("triangle", 1, (True, False, False)),
        ("rectangle", 2, (True, True, False)),
        ("circle", 3, (True, True, True)),
    ):
        sink, _ = _fresh_sink()
        try:
            enqueued = sink.send_event(_enter_event(shape, 100 + code))
            after_enqueue = _state(sink)
            _assert(enqueued.status is PlcCommandStatus.SENT, "command not sent", after_enqueue)
            _assert(after_enqueue.queue_length == 1, "enqueue did not increase length", after_enqueue)
            _assert(after_enqueue.leds == (False, False, False), "enqueue lit LEDs", after_enqueue)
            dequeued = sink.dequeue()
            after_dequeue = _state(sink)
            _assert(dequeued.status is PlcCommandStatus.SENT, "dequeue not sent", after_dequeue)
            _assert(after_dequeue.queue_length == 0, "dequeue did not consume item", after_dequeue)
            _assert(after_dequeue.leds == leds, "LED mapping mismatch", after_dequeue)
            _assert(after_dequeue.last_dequeued_shape == code, "last shape mismatch", after_dequeue)
            expected.append({"shape": shape, "queue_after_enqueue": 1, "queue_after_dequeue": 0, "leds": list(leds)})
            samples.append(
                {
                    "shape": shape,
                    "enqueue": enqueued.to_record(),
                    "after_enqueue": after_enqueue.to_record(),
                    "dequeue": dequeued.to_record(),
                    "after_dequeue": after_dequeue.to_record(),
                }
            )
        finally:
            sink.stop()
    return {"samples": samples, "expected": expected}


def _fifo_order() -> dict[str, Any]:
    sink, _ = _fresh_sink()
    try:
        sent: list[PlcCommandResult] = []
        for code in (1, 2, 3):
            sent.append(sink.send_event(_enter_event(("triangle", "rectangle", "circle")[code - 1], 100 + code)))
        full = _state(sink)
        _assert(full.queue_length == 3, "FIFO did not reach capacity", full)
        _assert(full.queue_full, "QueueFull was not set", full)
        _assert(full.leds == (False, False, False), "enqueue lit LEDs", full)

        dequeued: list[PlcCommandResult] = []
        states: list[PlcState] = []
        for _ in range(3):
            dequeued.append(sink.dequeue())
            states.append(_state(sink))
        _assert([item.last_dequeued_shape for item in states] == [1, 2, 3], "FIFO order mismatch", states[-1])
        _assert([item.leds for item in states] == [
            (True, False, False),
            (True, True, False),
            (True, True, True),
        ], "FIFO LED sequence mismatch", states[-1])
        _assert(states[-1].queue_empty, "FIFO did not become empty", states[-1])
        return {
            "enqueue_results": [item.to_record() for item in sent],
            "full_state": full.to_record(),
            "dequeue_results": [item.to_record() for item in dequeued],
            "dequeue_states": [item.to_record() for item in states],
        }
    finally:
        sink.stop()


def _held_command_valid_single_shot() -> dict[str, Any]:
    plc = FakeAcceptancePlc()
    plc.connect("fake", 0, 1)
    controls = PlcControls(
        test_enable=True,
        command_data_valid=True,
        shape_code=1,
        semantic_id=101,
        command_valid=False,
    )
    plc.db_write(12, 0, controls.pack())
    controls = PlcControls(
        test_enable=True,
        command_data_valid=True,
        shape_code=1,
        semantic_id=101,
        command_valid=True,
    )
    for _ in range(5):
        plc.db_write(12, 0, controls.pack())
    state = plc._status_bytes()
    from .s7 import unpack_state

    observed = unpack_state(state)
    _assert(observed.queue_length == 1, "held CommandValid produced duplicate enqueue", observed)
    plc.disconnect()
    return {"queue_length": observed.queue_length, "queue_empty": observed.queue_empty, "writes": len(plc.writes)}


def _unknown_event_skipped() -> dict[str, Any]:
    sink, _ = _fresh_sink()
    try:
        result = sink.send_event(_enter_event("unknown", 900))
        state = _state(sink)
        _assert(result.status is PlcCommandStatus.SKIPPED, "unknown event was not skipped", state)
        _assert(state.queue_length == 0, "unknown event changed queue", state)
        return {"result": result.to_record(), "state": state.to_record()}
    finally:
        sink.stop()


def _reset_clears_state() -> dict[str, Any]:
    sink, _ = _fresh_sink()
    try:
        sink.send_event(_enter_event("circle", 103))
        sink.dequeue()
        before = _state(sink)
        _assert(before.leds == (True, True, True), "circle did not light three LEDs", before)
        reset_result = sink.reset()
        after = _state(sink)
        _assert(reset_result.status is PlcCommandStatus.SENT, "reset not sent", after)
        _assert(after.queue_length == 0, "reset did not clear queue", after)
        _assert(after.queue_empty, "reset did not set empty", after)
        _assert(after.leds == (False, False, False), "reset did not clear LEDs", after)
        _assert(not after.last_dequeued_valid, "reset did not clear last dequeued", after)
        return {"before": before.to_record(), "after": after.to_record()}
    finally:
        sink.stop()


SCENARIOS: dict[str, Callable[[], dict[str, Any]]] = {
    "single_shape_led_mapping": _single_shape_mapping,
    "three_shape_fifo_order": _fifo_order,
    "held_command_valid_single_shot": _held_command_valid_single_shot,
    "unknown_event_skipped": _unknown_event_skipped,
    "reset_clears_state": _reset_clears_state,
}


def run_offline_acceptance(
    config: PlcCommunicationConfig | None = None,
) -> dict[str, Any]:
    del config  # deterministic local config is used by scenarios
    results: list[dict[str, Any]] = []
    for scenario, runner in SCENARIOS.items():
        started = _timestamp()
        try:
            actual = runner()
            passed = True
            failure_reason = None
        except Exception as error:
            actual = {}
            passed = False
            failure_reason = f"{type(error).__name__}: {error}"
        results.append(
            {
                "scenario": scenario,
                "started_at": started,
                "ended_at": _timestamp(),
                "status": "OFFLINE PASS" if passed else "FAIL",
                "pass": passed,
                "failure_reason": failure_reason,
                "actual": actual,
            }
        )
    return {
        "schema_version": 1,
        "milestone": "M8-bridge-offline",
        "source_type": "offline_fake_s7_and_synthetic_events",
        "generated_at": _timestamp(),
        "git_commit": _git_commit(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
        },
        "scope": "Non-vision PC bridge against an in-memory M8 acceptance PLC; not real hardware evidence",
        "config": asdict(_config()),
        "summary": {
            "scenario_count": len(results),
            "passing_scenarios": sum(item["pass"] for item in results),
            "all_scenarios_pass": all(item["pass"] for item in results),
        },
        "results": results,
    }


def write_offline_acceptance(
    document: dict[str, Any],
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "m8-bridge-offline.json"
    csv_path = output_dir / "m8-bridge-offline.csv"
    json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    import csv

    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("scenario", "status", "pass", "started_at", "ended_at", "failure_reason"))
        writer.writeheader()
        for result in document["results"]:
            writer.writerow({key: result.get(key) for key in writer.fieldnames})
    return json_path, csv_path
