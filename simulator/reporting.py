"""Reproducible scenario evidence plus explicitly non-deterministic benchmark metadata."""
import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from time import perf_counter
from dataclasses import asdict
from .models import Config, SemanticCommand
from .link import VirtualClock, InMemoryLink, Fault
from .fake_plc import FakePLC
from .scenarios import NAMES, run_scenario

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def benchmark(cycles=250):
    clock = VirtualClock()
    plc = FakePLC(clock)
    link = InMemoryLink(plc)
    start = perf_counter()
    for index in range(cycles):
        command = SemanticCommand(index + 1, "circle")
        link.send(command)
        link.send(command)
        plc.consume_one()
        link.heartbeat()
        link.faults.pending.append(Fault("request", "drop"))
        exchange = link.send(SemanticCommand(cycles + index + 1, "triangle"))
        clock.advance(plc.config.response_timeout_ms)
        assert link.poll(exchange).status == "TIMEOUT"
    return dict(operations=cycles * 6, elapsed_seconds=perf_counter() - start,
                accepted=plc.statistics["accepted_count"], duplicates=plc.statistics["duplicate_count"],
                consumed=plc.statistics["consumed_count"], source_type="simulated")


def report(names=NAMES, config=None):
    config = config or Config()
    scenarios = [run_scenario(name, config) for name in names]
    replay = all(first == run_scenario(first["scenario"], config) for first in scenarios)
    source_hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted((ROOT / "simulator").rglob("*"))
                     if p.is_file() and p.suffix in (".py", ".json")}
    return dict(source_type="simulated", physical_plc=False, git_baseline=git("rev-parse", "HEAD"),
                origin_master=git("rev-parse", "origin/master"), dirty=bool(git("status", "--porcelain")),
                python=platform.python_version(), environment=platform.platform(), config=asdict(config),
                source_sha256=source_hashes, scenarios=scenarios, deterministic_replay=replay,
                passed=replay and all(s["passed"] for s in scenarios), benchmark=benchmark())


def write_report(data, json_path, csv_path):
    for path in (json_path, csv_path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with Path(csv_path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["scenario", "source_type", "passed", "expected", "actual"])
        writer.writeheader()
        for item in data["scenarios"]:
            writer.writerow({key: json.dumps(item[key], ensure_ascii=False) if key in ("expected", "actual") else item[key]
                             for key in writer.fieldnames})
