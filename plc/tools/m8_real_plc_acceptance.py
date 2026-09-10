#!/usr/bin/env python3
"""Real S7-1200 acceptance runner for the TEST-ONLY M8 acceptance DB."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

try:
    import snap7
    from snap7.util import get_bool, get_dint, get_udint, get_usint, get_word
except ImportError as exc:  # pragma: no cover - exercised on deployment hosts
    raise SystemExit(
        "python-snap7 is required: python -m pip install -r plc/tools/requirements.txt"
    ) from exc


LAYOUT_MAGIC = 0x4D38
LAYOUT_VERSION = 1
CONTROL_SIZE = 8
DB_SIZE = 24
STATUS_OFFSET = 8
STATUS_SIZE = DB_SIZE - STATUS_OFFSET


@dataclass(frozen=True)
class State:
    acceptance_ready: bool
    queue_empty: bool
    queue_full: bool
    leds: tuple[bool, bool, bool]
    last_dequeued_valid: bool
    queue_length: int
    last_dequeued_shape: int
    last_dequeued_semantic_id: int
    cycle_counter: int
    layout_magic: int
    layout_version: int

    def to_dict(self) -> dict:
        data = asdict(self)
        data["leds"] = [int(value) for value in self.leds]
        return data


@dataclass
class Controls:
    test_enable: bool = False
    command_valid: bool = False
    command_data_valid: bool = False
    dequeue_request: bool = False
    reset_request: bool = False
    shape_code: int = 0
    semantic_id: int = 0


class AcceptanceError(RuntimeError):
    pass


class S7AcceptanceClient:
    def __init__(self, host: str, rack: int, slot: int, db_number: int):
        self.host = host
        self.rack = rack
        self.slot = slot
        self.db_number = db_number
        self.client = snap7.client.Client()
        self.controls = Controls()

    def connect(self) -> None:
        self.client.connect(self.host, self.rack, self.slot)
        if not self.client.get_connected():
            raise AcceptanceError(f"S7 connection to {self.host} did not become active")

    def close(self) -> None:
        self.client.disconnect()

    def read_state(self) -> State:
        raw = self.client.db_read(self.db_number, STATUS_OFFSET, STATUS_SIZE)
        return State(
            acceptance_ready=get_bool(raw, 0, 0),
            queue_empty=get_bool(raw, 0, 1),
            queue_full=get_bool(raw, 0, 2),
            leds=(get_bool(raw, 0, 3), get_bool(raw, 0, 4), get_bool(raw, 0, 5)),
            last_dequeued_valid=get_bool(raw, 0, 6),
            queue_length=get_usint(raw, 1),
            last_dequeued_shape=get_usint(raw, 2),
            last_dequeued_semantic_id=get_dint(raw, 4),
            cycle_counter=get_udint(raw, 8),
            layout_magic=get_word(raw, 12),
            layout_version=get_usint(raw, 14),
        )

    def write_controls(self, **changes: object) -> None:
        for name, value in changes.items():
            if not hasattr(self.controls, name):
                raise ValueError(f"unknown control field: {name}")
            setattr(self.controls, name, value)
        c = self.controls
        raw = bytearray(CONTROL_SIZE)
        raw[0] = (
            (int(c.test_enable) << 0)
            | (int(c.command_valid) << 1)
            | (int(c.command_data_valid) << 2)
            | (int(c.dequeue_request) << 3)
            | (int(c.reset_request) << 4)
        )
        raw[1] = int(c.shape_code) & 0xFF
        raw[4:8] = int(c.semantic_id).to_bytes(4, byteorder="big", signed=True)
        self.client.db_write(self.db_number, 0, raw)

    def restore_safe_controls(self) -> None:
        self.controls = Controls()
        self.write_controls()


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


class Runner:
    def __init__(self, client: S7AcceptanceClient, timeout: float, poll: float):
        self.client = client
        self.timeout = timeout
        self.poll = poll
        self.actions: list[dict] = []
        self.samples: list[dict] = []

    def state(self, label: str) -> State:
        state = self.client.read_state()
        self.samples.append({"at": utc_now(), "label": label, "state": state.to_dict()})
        return state

    def action(self, name: str, **details: object) -> None:
        self.actions.append({"at": utc_now(), "action": name, **details})

    def wait_for(self, label: str, predicate: Callable[[State], bool]) -> State:
        deadline = time.monotonic() + self.timeout
        last = self.state(label)
        while not predicate(last) and time.monotonic() < deadline:
            time.sleep(self.poll)
            last = self.state(label)
        if not predicate(last):
            raise AssertionError(f"timeout waiting for {label}; last state={last.to_dict()}")
        return last

    def reset(self) -> State:
        self.action("reset")
        self.client.write_controls(
            test_enable=True,
            command_valid=False,
            command_data_valid=False,
            dequeue_request=False,
            reset_request=False,
            shape_code=0,
            semantic_id=0,
        )
        time.sleep(0.1)
        self.client.write_controls(reset_request=True)
        time.sleep(0.25)
        self.client.write_controls(reset_request=False)
        return self.wait_for(
            "reset complete",
            lambda s: s.queue_length == 0
            and s.queue_empty
            and not s.queue_full
            and s.leds == (False, False, False),
        )

    def enqueue(
        self,
        shape: int,
        semantic_id: int,
        *,
        data_valid: bool = True,
        expected_length: int | None = None,
        leave_high: bool = False,
    ) -> State:
        before = self.client.read_state()
        if expected_length is None:
            expected_length = min(before.queue_length + int(data_valid), 3)
        self.action(
            "enqueue edge",
            shape_code=shape,
            semantic_id=semantic_id,
            command_data_valid=data_valid,
        )
        self.client.write_controls(
            command_valid=False,
            command_data_valid=data_valid,
            shape_code=shape,
            semantic_id=semantic_id,
        )
        time.sleep(0.1)
        self.client.write_controls(command_valid=True)
        result = self.wait_for(
            f"enqueue {shape}/{semantic_id}", lambda s: s.queue_length == expected_length
        )
        if not leave_high:
            self.client.write_controls(command_valid=False)
            time.sleep(0.1)
        return result

    def dequeue(self, expected_length: int, *, hold: float = 0.25) -> State:
        self.action("dequeue press", hold_seconds=hold)
        self.client.write_controls(dequeue_request=True)
        time.sleep(hold)
        result = self.wait_for(
            f"dequeue to length {expected_length}",
            lambda s: s.queue_length == expected_length,
        )
        self.client.write_controls(dequeue_request=False)
        time.sleep(0.25)
        return result


def assert_state(
    state: State,
    *,
    length: int,
    empty: bool,
    full: bool,
    leds: tuple[bool, bool, bool] | None = None,
    shape: int | None = None,
    semantic_id: int | None = None,
) -> None:
    assert state.queue_length == length, state.to_dict()
    assert state.queue_empty is empty, state.to_dict()
    assert state.queue_full is full, state.to_dict()
    if leds is not None:
        assert state.leds == leds, state.to_dict()
    if shape is not None:
        assert state.last_dequeued_valid and state.last_dequeued_shape == shape, state.to_dict()
    if semantic_id is not None:
        assert state.last_dequeued_semantic_id == semantic_id, state.to_dict()


def t01(r: Runner) -> None:
    r.reset()
    result = r.dequeue(0)
    assert_state(result, length=0, empty=True, full=False, leds=(False, False, False))


def t02(r: Runner) -> None:
    r.reset()
    result = r.enqueue(1, 101)
    assert_state(result, length=1, empty=False, full=False, leds=(False, False, False))
    result = r.dequeue(0)
    assert_state(result, length=0, empty=True, full=False, leds=(True, False, False), shape=1, semantic_id=101)


def t03(r: Runner) -> None:
    r.reset()
    for length, item in enumerate(((1, 101), (2, 102), (3, 103)), start=1):
        r.enqueue(*item, expected_length=length)
    assert_state(r.state("fifo full"), length=3, empty=False, full=True, leds=(False, False, False))
    for length, shape, sid, leds in (
        (2, 1, 101, (True, False, False)),
        (1, 2, 102, (True, True, False)),
        (0, 3, 103, (True, True, True)),
    ):
        result = r.dequeue(length)
        assert_state(result, length=length, empty=length == 0, full=False, leds=leds, shape=shape, semantic_id=sid)


def t04(r: Runner) -> None:
    r.reset()
    for length, item in enumerate(((1, 101), (2, 102), (3, 103)), start=1):
        r.enqueue(*item, expected_length=length)
    r.enqueue(1, 104, expected_length=3)
    assert_state(r.state("fourth rejected"), length=3, empty=False, full=True)
    for length, shape, sid in ((2, 1, 101), (1, 2, 102), (0, 3, 103)):
        result = r.dequeue(length)
        assert_state(result, length=length, empty=length == 0, full=False, shape=shape, semantic_id=sid)


def t05(r: Runner) -> None:
    r.reset()
    for length, shape in enumerate((1, 2, 3), start=1):
        r.enqueue(shape, 100 + shape, expected_length=length)
    r.action("held dequeue", hold_seconds=1.0)
    r.client.write_controls(dequeue_request=True)
    time.sleep(0.25)
    observed = []
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        observed.append(r.state("held dequeue sample").queue_length)
        time.sleep(0.1)
    r.client.write_controls(dequeue_request=False)
    time.sleep(0.25)
    assert observed and all(value == 2 for value in observed), observed


def t06(r: Runner) -> None:
    r.reset()
    for length, shape in enumerate((1, 2, 3), start=1):
        r.enqueue(shape, 100 + shape, expected_length=length)
    first = r.dequeue(2)
    second = r.dequeue(1)
    assert_state(first, length=2, empty=False, full=False, shape=1, semantic_id=101)
    assert_state(second, length=1, empty=False, full=False, shape=2, semantic_id=102)


def t07(r: Runner) -> None:
    r.reset()
    r.enqueue(1, 101)
    r.enqueue(2, 102)
    r.dequeue(1)
    result = r.reset()
    assert_state(result, length=0, empty=True, full=False, leds=(False, False, False))
    assert not result.last_dequeued_valid, result.to_dict()


def t08(r: Runner) -> None:
    for shape, leds in ((1, (True, False, False)), (2, (True, True, False)), (3, (True, True, True))):
        r.reset()
        enqueued = r.enqueue(shape, 100 + shape)
        assert enqueued.leds == (False, False, False), enqueued.to_dict()
        result = r.dequeue(0)
        assert_state(result, length=0, empty=True, full=False, leds=leds, shape=shape, semantic_id=100 + shape)


def t09(r: Runner) -> None:
    r.reset()
    for length, shape in enumerate((1, 2, 3), start=1):
        r.enqueue(shape, 100 + shape, expected_length=length)
    full = r.state("full boundary")
    assert_state(full, length=3, empty=False, full=True)
    r.enqueue(1, 104, expected_length=3)
    result = r.dequeue(2)
    assert_state(result, length=2, empty=False, full=False, shape=1, semantic_id=101)


def t10(r: Runner) -> None:
    # Current M8 core accepts any CommandIn.Valid item into FIFO. Shape 0/99
    # dequeue successfully but FB_LedDisplay deliberately preserves prior LEDs.
    r.reset()
    r.enqueue(2, 102)
    r.dequeue(0)
    baseline = (True, True, False)
    for shape, sid in ((0, 200), (99, 299)):
        enqueued = r.enqueue(shape, sid)
        assert_state(enqueued, length=1, empty=False, full=False, leds=baseline)
        result = r.dequeue(0)
        assert_state(result, length=0, empty=True, full=False, leds=baseline, shape=shape, semantic_id=sid)
    r.client.write_controls(command_data_valid=False, command_valid=False, shape_code=1, semantic_id=999)
    time.sleep(0.1)
    r.client.write_controls(command_valid=True)
    time.sleep(0.25)
    invalid = r.state("CommandData.Valid FALSE rejected")
    assert_state(invalid, length=0, empty=True, full=False, leds=baseline)
    r.client.write_controls(command_valid=False)


def t11(r: Runner) -> None:
    r.reset()
    for length, shape in enumerate((1, 2, 3), start=1):
        r.enqueue(shape, 100 + shape, expected_length=length)
    r.dequeue(2)
    r.enqueue(1, 104, expected_length=3)
    assert r.state("full with display").queue_full
    result = r.reset()
    assert_state(result, length=0, empty=True, full=False, leds=(False, False, False))


def t15(r: Runner) -> None:
    r.reset()
    r.enqueue(1, 101, leave_high=True)
    observed = []
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        observed.append(r.state("CommandValid held TRUE").queue_length)
        time.sleep(0.1)
    assert observed and all(value == 1 for value in observed), observed
    r.client.write_controls(command_valid=False)
    time.sleep(0.25)
    assert r.state("CommandValid released").queue_length == 1
    r.enqueue(2, 102, expected_length=2, leave_high=True)

    r.action("reset while CommandValid remains TRUE")
    r.client.write_controls(reset_request=True)
    time.sleep(0.25)
    r.client.write_controls(reset_request=False)
    time.sleep(0.5)
    held_after_reset = r.state("held TRUE after reset release")
    assert_state(held_after_reset, length=0, empty=True, full=False, leds=(False, False, False))
    r.client.write_controls(command_valid=False)
    time.sleep(0.25)
    result = r.enqueue(3, 103, expected_length=1)
    assert_state(result, length=1, empty=False, full=False, leds=(False, False, False))


TESTS: dict[str, Callable[[Runner], None]] = {
    "M8-T01": t01,
    "M8-T02": t02,
    "M8-T03": t03,
    "M8-T04": t04,
    "M8-T05": t05,
    "M8-T06": t06,
    "M8-T07": t07,
    "M8-T08": t08,
    "M8-T09": t09,
    "M8-T10": t10,
    "M8-T11": t11,
    "M8-T15": t15,
}


def check_access(client: S7AcceptanceClient, poll: float) -> dict:
    first = client.read_state()
    time.sleep(max(0.2, poll * 2))
    second = client.read_state()
    errors = []
    if first.layout_magic != LAYOUT_MAGIC or first.layout_version != LAYOUT_VERSION:
        errors.append(
            f"layout mismatch: magic=0x{first.layout_magic:04X}, version={first.layout_version}"
        )
    if not first.acceptance_ready:
        errors.append("AcceptanceReady is FALSE")
    if first.cycle_counter == second.cycle_counter:
        errors.append("CycleCounter did not change; harness is not executing in RUN")
    if errors:
        raise AcceptanceError("; ".join(errors))
    return {"first": first.to_dict(), "second": second.to_dict(), "pass": True}


def run_one(client: S7AcceptanceClient, test_id: str, timeout: float, poll: float) -> dict:
    started = utc_now()
    runner = Runner(client, timeout, poll)
    pre_state = client.read_state().to_dict()
    passed = False
    failure_reason = None
    try:
        TESTS[test_id](runner)
        passed = True
    except Exception as exc:  # evidence must survive assertion and S7 failures
        failure_reason = f"{type(exc).__name__}: {exc}"
    post_state = None
    try:
        post_state = client.read_state().to_dict()
    except Exception as exc:
        if failure_reason is None:
            failure_reason = f"post-state read failed: {type(exc).__name__}: {exc}"
            passed = False
    return {
        "test_id": test_id,
        "started_at": started,
        "ended_at": utc_now(),
        "pre_state": pre_state,
        "actions": runner.actions,
        "samples": runner.samples,
        "post_state": post_state,
        "expected": "See plc/tests/README.md and test implementation",
        "actual": post_state,
        "status": "AUTO PASS" if passed else "FAIL",
        "pass": passed,
        "failure_reason": failure_reason,
    }


def write_evidence(output: Path, document: dict) -> tuple[Path, Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "m8-real-acceptance.json"
    csv_path = output / "m8-real-acceptance.csv"
    md_path = output / "m8-real-summary.md"
    json_path.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("test_id", "status", "pass", "started_at", "ended_at", "failure_reason"),
        )
        writer.writeheader()
        for result in document["results"]:
            writer.writerow({key: result.get(key) for key in writer.fieldnames})

    lines = [
        "# M8 Real PLC Acceptance Summary",
        "",
        f"- Generated: {document['generated_at']}",
        f"- PLC: `{document['plc_ip']}`",
        f"- DB number: `{document['db_number']}`",
        f"- Git commit: `{document['git_commit']}`",
        "- Evidence boundary: AUTO reflects S7 DB/Q-state reads; it does not replace visual LED, physical button, or power-cycle evidence.",
        "",
        "| Test | Status | Failure |",
        "|---|---|---|",
    ]
    for result in document["results"]:
        failure = (result.get("failure_reason") or "").replace("|", "\\|")
        lines.append(f"| {result['test_id']} | {result['status']} | {failure} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, csv_path, md_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="192.0.2.1")
    parser.add_argument("--rack", type=int, default=0)
    parser.add_argument("--slot", type=int, default=1)
    # Not required so that `--dry-run` can be used as a no-hardware smoke test.
    parser.add_argument("--db-number", type=int)
    parser.add_argument("--output", type=Path, default=Path("evidence/data/m8-real"))
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--poll", type=float, default=0.05)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-access", action="store_true")
    mode.add_argument("--all", action="store_true")
    mode.add_argument("--test", choices=sorted(TESTS))
    mode.add_argument("--verify-power-on", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.dry_run:
        print(json.dumps({"tests": list(TESTS), "writes": "DBB0..DBB7 only", "status": "DRY RUN"}, indent=2))
        return 0

    if args.db_number is None:
        parser_error = "--db-number is required unless --dry-run is used"
        print(parser_error, file=sys.stderr)
        return 2

    client = S7AcceptanceClient(args.host, args.rack, args.slot, args.db_number)
    document = {
        "generated_at": utc_now(),
        "plc_ip": args.host,
        "rack": args.rack,
        "slot": args.slot,
        "db_number": args.db_number,
        "git_commit": git_commit(),
        "snap7_version": getattr(snap7, "__version__", "unknown"),
        "results": [],
    }
    exit_code = 0
    try:
        client.connect()
        access = check_access(client, args.poll)
        document["access_check"] = access
        if args.check_access:
            print(json.dumps(access, indent=2))
            return 0
        if args.verify_power_on:
            state = client.read_state()
            passed = (
                state.queue_length == 0
                and state.queue_empty
                and not state.queue_full
                and state.leds == (False, False, False)
                and not client.controls.test_enable
            )
            document["results"].append(
                {
                    "test_id": "M8-T12",
                    "started_at": document["generated_at"],
                    "ended_at": utc_now(),
                    "pre_state": state.to_dict(),
                    "actions": ["read-only verification after operator power cycle"],
                    "samples": [],
                    "post_state": state.to_dict(),
                    "expected": "empty FIFO, Full FALSE, all business LEDs FALSE",
                    "actual": state.to_dict(),
                    "status": "PHYSICAL PASS" if passed else "FAIL",
                    "pass": passed,
                    "failure_reason": None if passed else "power-on state did not match expected initialization",
                }
            )
            exit_code = 0 if passed else 1
        else:
            selected = list(TESTS) if args.all else [args.test]
            for test_id in selected:
                result = run_one(client, test_id, args.timeout, args.poll)
                document["results"].append(result)
                if not result["pass"]:
                    exit_code = 1
                    break  # fail-safe: do not continue mutating PLC after a failed test
            document["results"].extend(
                {
                    "test_id": test_id,
                    "started_at": None,
                    "ended_at": None,
                    "pre_state": None,
                    "actions": [],
                    "samples": [],
                    "post_state": None,
                    "expected": "See plc/tests/README.md",
                    "actual": None,
                    "status": "NOT RUN",
                    "pass": False,
                    "failure_reason": "stopped after earlier failure",
                }
                for test_id in selected[len(document["results"]):]
            )
    except Exception as exc:
        document["access_error"] = f"{type(exc).__name__}: {exc}"
        exit_code = 2
    finally:
        if client.client.get_connected():
            try:
                client.restore_safe_controls()
            except Exception as exc:
                document["cleanup_error"] = f"{type(exc).__name__}: {exc}"
                exit_code = max(exit_code, 2)
            client.close()

    if args.check_access and "access_error" in document:
        print(document["access_error"], file=sys.stderr)
        return exit_code
    paths = write_evidence(args.output, document)
    print("\n".join(str(path) for path in paths))
    if "access_error" in document:
        print(document["access_error"], file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
