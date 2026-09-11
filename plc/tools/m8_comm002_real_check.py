#!/usr/bin/env python3
"""Real-PLC check for the COMM-002 PLC half (2 s heartbeat watchdog -> three lamps blink).

The scenario is driven through the production PC bridge (``pc.communication``),
so what is exercised is the same code path the sorting GUI uses:

1. ARM      start the sink (writes ``TestEnable`` + the DBX0.5 heartbeat enable)
            and send 1 s heartbeats: the alarm must stay FALSE;
2. SILENCE  stop sending heartbeats while still reading the PLC status: the
            alarm must go TRUE about 2 s after the last heartbeat;
3. BLINK    keep sampling while the alarm is up: the three PLC lamp bits must
            toggle together at about 2 Hz (the physical lamps mirror these bits);
4. RESUME   send heartbeats again: the alarm must clear;
5. CLEANUP  disarm the watchdog and leave the DB in an idle state.

What this proves and what it does not
-------------------------------------
* Proves: the downloaded PLC program runs a 2 s watchdog on the heartbeat byte,
  raises DBX8.7, overrides the three lamp bits with the blink, and clears both
  when heartbeats resume.
* Does not prove: that the physical lamps are wired to Q0.0..Q0.2 and lit. That
  is a visual check on the lab bench and is recorded separately.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Run as a script from anywhere: the repo root is two levels above this file.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pc.communication.config import load_plc_communication_config
from pc.communication.sink import S7PlcCommandSink

CONTROL_SIZE = 8


def local_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


class Recorder:
    """Timestamped samples plus the notes that explain them."""

    def __init__(self) -> None:
        self.samples: list[dict] = []
        self.notes: list[dict] = []

    def sample(self, phase: str, state, *, extra: dict | None = None) -> dict:
        row = {
            "at": local_now(),
            "phase": phase,
            "monotonic": round(time.monotonic(), 4),
            "alarm": bool(state.comm_lost_alarm),
            "leds": [int(value) for value in state.leds],
            "queue_length": state.queue_length,
            "queue_empty": bool(state.queue_empty),
            "cycle_counter": state.cycle_counter,
        }
        if extra:
            row.update(extra)
        self.samples.append(row)
        return row

    def note(self, event: str, **details: object) -> None:
        self.notes.append({"at": local_now(), "event": event, **details})

    def phase(self, name: str) -> list[dict]:
        return [row for row in self.samples if row["phase"] == name]


def wait_for_alarm(
    sink: S7PlcCommandSink,
    recorder: Recorder,
    phase: str,
    wanted: bool,
    timeout: float,
    poll: float,
    *,
    on_sample=None,
) -> dict | None:
    """Poll until ``alarm == wanted``; return the first sample that matches."""

    deadline = time.monotonic() + timeout
    while True:
        state = sink.read_state()
        if state is None:
            recorder.note("status read failed", phase=phase)
        else:
            row = recorder.sample(phase, state)
            if on_sample is not None:
                on_sample(row)
            if bool(state.comm_lost_alarm) is wanted:
                return row
        if time.monotonic() >= deadline:
            return None
        time.sleep(poll)


def blink_stats(rows: list[dict]) -> dict:
    """Measure the blink rate of the three lamp bits from a sample window."""

    if not rows:
        return {"samples": 0}
    aligned = all(tuple(row["leds"]) in ((0, 0, 0), (1, 1, 1)) for row in rows)
    transitions = 0
    for previous, current in zip(rows, rows[1:]):
        if previous["leds"][0] != current["leds"][0]:
            transitions += 1
    duration = rows[-1]["monotonic"] - rows[0]["monotonic"]
    period = (2 * duration / transitions) if transitions else None
    return {
        "samples": len(rows),
        "window_seconds": round(duration, 3),
        "lamps_toggle_together": aligned,
        "transitions": transitions,
        "measured_period_seconds": round(period, 4) if period else None,
        "measured_frequency_hz": round(1 / period, 3) if period else None,
        "saw_lit": any(row["leds"][0] for row in rows),
        "saw_dark": any(not row["leds"][0] for row in rows),
    }


def disarm(sink: S7PlcCommandSink) -> bool:
    """Clear TestEnable and the heartbeat enable so the watchdog cannot stay armed."""

    try:
        sink._write(  # noqa: SLF001 - the tool needs the unexposed enable bits
            test_enable=False,
            command_valid=False,
            command_data_valid=False,
            dequeue_request=False,
            reset_request=False,
            shape_code=0,
            semantic_id=0,
            heartbeat_enabled=False,
        )
        return True
    except Exception:
        return False


def run(args: argparse.Namespace) -> int:
    config = load_plc_communication_config(args.config)
    config.validate()
    sink = S7PlcCommandSink(config)
    recorder = Recorder()
    results: dict[str, object] = {}
    failures: list[str] = []

    print(f"COMM-002 real-PLC check  target={config.host} DB{config.db_number}")
    sink.start()
    try:
        # ---------------------------------------------------------------- ARM
        recorder.note("sink started", host=config.host, db_number=config.db_number)
        sink.safe_init()
        retained = sink._client.db_read(config.db_number, 0, CONTROL_SIZE)  # noqa: SLF001
        counter = (retained[2] + 1) & 0xFF
        recorder.note("retained control bytes", raw=bytes(retained).hex())

        arm_until = time.monotonic() + args.arm_seconds
        next_beat = 0.0
        last_beat_at: float | None = None
        while time.monotonic() < arm_until:
            now = time.monotonic()
            if now >= next_beat:
                attempts = sink.write_heartbeat(counter)
                counter = (counter + 1) & 0xFF
                last_beat_at = time.monotonic()
                recorder.note("heartbeat written", attempts=attempts, counter=(counter - 1) & 0xFF)
                next_beat = last_beat_at + config.heartbeat_interval_seconds
            state = sink.read_state()
            if state is not None:
                recorder.sample("arm", state)
            time.sleep(args.poll_seconds)

        arm_rows = recorder.phase("arm")
        results["arm"] = {
            "samples": len(arm_rows),
            "heartbeats": len([n for n in recorder.notes if n["event"] == "heartbeat written"]),
            "alarm_stayed_false": all(not row["alarm"] for row in arm_rows),
        }
        if not results["arm"]["alarm_stayed_false"]:
            failures.append("alarm was TRUE while heartbeats were running")

        # ------------------------------------------------------------ SILENCE
        assert last_beat_at is not None
        recorder.note("heartbeats stopped", phase="silence")
        onset = wait_for_alarm(
            sink, recorder, "silence", True, args.alarm_timeout, args.poll_seconds
        )
        if onset is None:
            failures.append("alarm never became TRUE after the heartbeat stopped")
            results["silence"] = {"detected": False}
        else:
            delay = onset["monotonic"] - last_beat_at
            results["silence"] = {
                "detected": True,
                "detected_at": onset["at"],
                "delay_after_last_heartbeat_seconds": round(delay, 3),
                "within_expected_window": 1.9 <= delay <= 2.6,
            }
            if not results["silence"]["within_expected_window"]:
                failures.append(f"alarm delay {delay:.2f}s is outside 1.9-2.6 s")

        # -------------------------------------------------------------- BLINK
        blink_until = time.monotonic() + args.blink_seconds
        while time.monotonic() < blink_until:
            state = sink.read_state()
            if state is not None:
                recorder.sample("blink", state)
            time.sleep(args.poll_seconds)
        blink = blink_stats(recorder.phase("blink"))
        results["blink"] = blink
        if not blink.get("lamps_toggle_together"):
            failures.append("the three lamp bits were not toggling together")
        if not (blink.get("saw_lit") and blink.get("saw_dark")):
            failures.append("the lamp bits never blinked during the alarm")
        frequency = blink.get("measured_frequency_hz")
        if frequency is not None and not 1.5 <= frequency <= 2.5:
            failures.append(f"blink frequency {frequency} Hz is outside 1.5-2.5 Hz")
        if not all(row["alarm"] for row in recorder.phase("blink")):
            failures.append("the alarm bit dropped during the blink window")

        # ------------------------------------------------------------- RESUME
        recorder.note("heartbeats resumed", phase="resume")
        sink.write_heartbeat(counter)
        counter = (counter + 1) & 0xFF
        recovered = wait_for_alarm(
            sink, recorder, "resume", False, args.recover_timeout, args.poll_seconds
        )
        if recovered is None:
            failures.append("alarm did not clear after heartbeats resumed")
            results["resume"] = {"detected": False}
        else:
            results["resume"] = {
                "detected": True,
                "cleared_at": recovered["at"],
                "alarm_now_false": True,
            }

        # ------------------------------------------------------------ CLEANUP
        recorder.note("disarming", phase="cleanup")
        disarmed = disarm(sink)
        quiet: list[dict] = []
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            state = sink.read_state()
            if state is not None:
                quiet.append(recorder.sample("cleanup", state))
            time.sleep(args.poll_seconds)
        results["cleanup"] = {
            "disarm_write_confirmed": disarmed,
            "samples": len(quiet),
            "alarm_cleared": bool(quiet) and all(not row["alarm"] for row in quiet),
            "lamps_idle": bool(quiet) and all(row["leds"] == [0, 0, 0] for row in quiet),
            "queue_length": quiet[-1]["queue_length"] if quiet else None,
        }
        if not results["cleanup"]["alarm_cleared"]:
            failures.append("the alarm was still TRUE after the watchdog was disarmed")
    finally:
        if not disarm(sink):
            print("WARNING: the disarm write failed; the alarm may still be armed")
        try:
            sink.stop()
        except Exception as error:  # pragma: no cover - cleanup best effort
            print(f"WARNING: sink.stop() failed: {type(error).__name__}: {error}")

    results["write_stats"] = {
        "control_writes_needing_a_resend": sink.write_retry_count,
        "reconnects": sink.reconnect_count,
    }
    document = {
        "generated_at": local_now(),
        "git_commit": git_commit(),
        "target": {
            "host": config.host,
            "rack": config.rack,
            "slot": config.slot,
            "db_number": config.db_number,
        },
        "parameters": {
            "heartbeat_interval_seconds": config.heartbeat_interval_seconds,
            "comm_loss_timeout_seconds": config.comm_loss_timeout_seconds,
            "write_confirm_attempts": config.write_confirm_attempts,
            "poll_seconds": args.poll_seconds,
        },
        "evidence_boundary": (
            "Reads DBX8.7 and the three lamp state bits over S7. It does not replace "
            "the visual check that the physical lamps on Q0.0..Q0.2 are lit."
        ),
        "results": results,
        "notes": recorder.notes,
        "samples": recorder.samples,
        "failure_reasons": failures,
        "passed": not failures,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{args.label}.json"
    csv_path = output_dir / f"{args.label}.csv"
    json_path.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["at", "phase", "monotonic", "alarm", "leds", "queue_length", "queue_empty", "cycle_counter"]
        )
        writer.writeheader()
        for row in recorder.samples:
            writer.writerow({**row, "leds": "".join(str(bit) for bit in row["leds"])})

    print(json.dumps({key: results[key] for key in ("arm", "silence", "blink", "resume", "cleanup")}, indent=2, ensure_ascii=False))
    print(f"evidence: {json_path}")
    print(f"evidence: {csv_path}")
    if failures:
        print("FAILED: " + "; ".join(failures))
        return 1
    print("PASSED: the PLC watchdog alarmed after 2 s of silence, blinked the three lamps, and cleared.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("pc/config/plc.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("evidence/data/m8-real"))
    parser.add_argument("--label", default="2026-09-11-comm002-heartbeat-alarm")
    parser.add_argument("--arm-seconds", type=float, default=4.0)
    parser.add_argument("--blink-seconds", type=float, default=2.5)
    parser.add_argument("--alarm-timeout", type=float, default=6.0)
    parser.add_argument("--recover-timeout", type=float, default=6.0)
    parser.add_argument("--poll-seconds", type=float, default=0.05)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
