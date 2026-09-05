"""M6 headless semantics, fault boundaries, upstream compatibility and evidence."""
from dataclasses import FrozenInstanceError, asdict
import json
import pytest
from simulator.models import Config, SemanticCommand, CommandAdapter
from simulator.fake_plc import FakePLC
from simulator.link import VirtualClock, InMemoryLink, Fault, FaultInjector
from simulator.scenarios import NAMES, run_scenario, m4_events


def setup_link(*faults, config=None):
    clock = VirtualClock()
    plc = FakePLC(clock, config)
    return clock, plc, InMemoryLink(plc, FaultInjector(faults))


@pytest.mark.parametrize("name", NAMES)
def test_scenario_and_exact_replay(name):
    first = run_scenario(name)
    assert first["passed"], first
    assert first == run_scenario(name)


@pytest.mark.parametrize("field", ("capacity", "heartbeat_interval_ms", "heartbeat_timeout_ms", "response_timeout_ms"))
@pytest.mark.parametrize("value", (0, -1, True, 1.5, "3", None))
def test_invalid_config(field, value):
    with pytest.raises(ValueError):
        Config(**{field: value})


def test_config_load_and_relations(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(asdict(Config(capacity=5))))
    assert Config.load(path).capacity == 5
    with pytest.raises(ValueError):
        Config(heartbeat_interval_ms=2000)
    path.write_text("[]")
    with pytest.raises(ValueError):
        Config.load(path)
    path.write_text('{"unknown": 3}')
    with pytest.raises(TypeError):
        Config.load(path)


@pytest.mark.parametrize("fault", [dict(channel="wire", action="drop"), dict(channel="request", action="random"),
                                  dict(channel="response", action="delay", delay_ms=-1),
                                  dict(channel="response", action="drop", delay_ms=1),
                                  dict(channel="heartbeat", action="drop", command_id=1)])
def test_invalid_fault(fault):
    with pytest.raises(ValueError):
        Fault(**fault)


def test_immutable_and_serializable():
    command = SemanticCommand(1, "triangle")
    with pytest.raises(FrozenInstanceError):
        command.shape = "circle"
    assert json.loads(json.dumps(asdict(command)))["command_id"] == 1


@pytest.mark.parametrize("command", [SemanticCommand(0, "circle"), SemanticCommand(True, "circle"),
                                      SemanticCommand(1, "unknown"), SemanticCommand(1, "circle", -1),
                                      SemanticCommand(1, "circle", None, False)])
def test_invalid_command_does_not_mutate(command):
    _, plc, link = setup_link()
    assert link.send(command).response.status == "INVALID"
    assert plc.queue == ()
    assert plc.snapshot()["accepted_command_ids"] == []


def test_duplicate_conflict_and_consumed_id():
    _, plc, link = setup_link(config=Config(capacity=1))
    first = SemanticCommand(1, "circle")
    assert link.send(first).response.status == "ACCEPTED"
    assert link.send(first).response.status == "DUPLICATE"  # before full check
    assert link.send(SemanticCommand(1, "triangle")).response.status == "INVALID"
    assert plc.consume_one() == first
    assert link.send(first).response.status == "DUPLICATE"
    assert plc.queue == ()


def test_request_delay_and_disconnect_cancels_old_generation():
    clock, plc, link = setup_link(Fault("request", "delay", delay_ms=10))
    exchange = link.send(SemanticCommand(1, "circle"))
    assert plc.queue == ()
    clock.advance(9)
    assert link.poll(exchange) is None
    link.disconnect()
    link.reconnect()
    clock.advance(100)
    assert link.poll(exchange).status == "TIMEOUT"
    assert plc.queue == ()


def test_delayed_request_arrives_after_timeout_and_is_observable():
    clock, plc, link = setup_link(Fault("request", "delay", delay_ms=101))
    exchange = link.send(SemanticCommand(1, "circle"))
    clock.advance(100)
    assert exchange.response.status == "TIMEOUT"
    assert plc.queue == ()
    clock.advance(1)
    assert len(plc.queue) == 1
    assert exchange.late_response.status == "ACCEPTED"
    assert exchange.response.status == "TIMEOUT"


def test_large_time_jump_does_not_turn_late_response_into_success():
    clock, plc, link = setup_link(Fault("response", "delay", delay_ms=101))
    exchange = link.send(SemanticCommand(1, "circle"))
    clock.advance(1000)
    assert link.poll(exchange).status == "TIMEOUT"
    assert exchange.completed_ms == 100
    assert exchange.late_response.status == "ACCEPTED"


def test_response_exact_deadline_and_concurrent_same_ids_are_correlated():
    clock, plc, link = setup_link(Fault("response", "delay", delay_ms=100))
    first = link.send(SemanticCommand(1, "circle"))
    second = link.send(SemanticCommand(1, "circle"))
    assert second.response.status == "DUPLICATE"
    clock.advance(100)
    assert first.response.status == "TIMEOUT"
    assert first.late_response.status == "ACCEPTED"
    assert second.response.status == "DUPLICATE"
    assert len(plc.queue) == 1


def test_id_targeted_fault_consumed_once():
    clock, plc, link = setup_link(Fault("response", "drop", command_id=2))
    assert link.send(SemanticCommand(1, "circle")).response.status == "ACCEPTED"
    lost = link.send(SemanticCommand(2, "triangle"))
    clock.advance(100)
    assert lost.response.status == "TIMEOUT"
    assert link.send(SemanticCommand(2, "triangle")).response.status == "DUPLICATE"
    assert len(link.faults.injected) == 1


def test_offline_device_distinct_from_link_and_heartbeat():
    clock, plc, link = setup_link()
    assert plc.snapshot()["heartbeat_state"] == "never_received"
    plc.online = False
    assert link.connected
    assert link.send(SemanticCommand(1, "circle")).response.status == "OFFLINE"
    link.heartbeat()
    assert plc.last_heartbeat is None
    plc.online = True
    link.heartbeat()
    clock.advance(1999)
    assert plc.snapshot()["heartbeat_alive"]
    clock.advance(1)
    assert not plc.snapshot()["heartbeat_alive"]
    assert plc.online and link.connected


def test_clock_validation_and_stable_same_tick_order():
    clock = VirtualClock()
    events = []
    clock.schedule(2, lambda: events.append("first"))
    clock.schedule(2, lambda: events.append("second"))
    clock.advance(2)
    assert events == ["first", "second"]
    for value in (-1, True, 0.5):
        with pytest.raises(ValueError):
            clock.advance(value)


def test_m4_enter_exit_adapter_and_source_ids():
    adapter = CommandAdapter()
    events = m4_events()
    commands = [adapter.adapt(event) for event in events]
    assert [c.shape for c in commands[:3]] == ["triangle", "rectangle", "circle"]
    assert commands[3:] == [None, None, None]
    assert commands[0].source_event_id == events[0].event_id
    assert commands[0].source_object_id == events[0].object_id
    assert adapter.adapt(events[0]).command_id == 4  # adapter does not pretend to implement M9 replay policy


def test_json_csv_and_cli_failure(tmp_path, monkeypatch):
    from simulator import __main__ as cli
    import csv
    item = run_scenario("normal_fifo")
    data = dict(scenarios=[item], deterministic_replay=True, benchmark={}, passed=True)
    monkeypatch.setattr(cli, "report", lambda *args: data)
    j, c = tmp_path / "result.json", tmp_path / "result.csv"
    args = ["--output-json", str(j), "--output-csv", str(c)]
    assert cli.main(args) == 0
    assert json.loads(j.read_text())["scenarios"][0]["passed"]
    with c.open() as stream:
        assert list(csv.DictReader(stream))[0]["source_type"] == "simulated"
    data["passed"] = False
    assert cli.main(args) == 1
