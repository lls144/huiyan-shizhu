"""Scripted acceptance with independently stated expected observations."""
from dataclasses import asdict
from .models import Config, SemanticCommand, CommandAdapter
from .fake_plc import FakePLC
from .link import VirtualClock, InMemoryLink, FaultInjector, Fault

NAMES = ("normal_fifo", "dequeue_order", "queue_full", "full_recovery", "invalid_shape",
         "duplicate", "request_loss", "ack_loss", "delayed_ack", "timeout", "disconnect",
         "reconnect", "heartbeat_normal", "heartbeat_lost", "heartbeat_recovery", "m4_integration")
SHAPES = ("triangle", "rectangle", "circle")


def m4_events():
    from pc.events.config import load_event_config
    from pc.events.models import Detection
    from pc.events.tracker import ObjectStateManager
    from pathlib import Path
    config = load_event_config(Path(__file__).resolve().parents[1] / "pc/config/events.json")
    manager = ObjectStateManager(config)
    events = []
    present_frames = config.min_confirm_frames + 20
    for frame in range(present_frames + config.max_missing_frames + 1):
        detections = [Detection(label, .95, (index * 200, 0, 80, 80), frame)
                      for index, label in enumerate(SHAPES)] if frame < present_frames else []
        events.extend(manager.process_frame(frame, detections).events)
    return events


def run_scenario(name, config=None):
    if name not in NAMES:
        raise ValueError(f"unknown scenario: {name}")
    config = config or Config()
    clock = VirtualClock()
    plc = FakePLC(clock, config)
    faults = FaultInjector()
    link = InMemoryLink(plc, faults)
    observations = {}
    expected = {}
    input_events = []

    def check(key, actual, wanted):
        observations[key] = actual
        expected[key] = wanted

    def send(index, shape="triangle"):
        exchange = link.send(SemanticCommand(index, shape))
        return exchange

    def fill():
        return [send(i + 1, SHAPES[i % 3]).response.status for i in range(config.capacity)]

    def order():
        return [item.shape for item in plc.queue]

    if name in ("normal_fifo", "dequeue_order", "queue_full", "full_recovery"):
        check("accepted", fill(), ["ACCEPTED"] * config.capacity)
        initial = [SHAPES[i % 3] for i in range(config.capacity)]
        check("initial_order", order(), initial)
        if name == "dequeue_order":
            check("consumed", [plc.consume_one().shape for _ in initial], initial)
            check("empty_dequeue", plc.consume_one(), None)
            check("empty", plc.snapshot()["empty"], True)
        if name in ("queue_full", "full_recovery"):
            check("overflow_status", send(config.capacity + 1).response.status, "QUEUE_FULL")
            check("unchanged", order(), initial)
        if name == "full_recovery":
            plc.consume_one()
            check("recovery", send(config.capacity + 1).response.status, "ACCEPTED")
            check("recovered_order", order(), initial[1:] + ["triangle"])
    elif name == "invalid_shape":
        check("status", send(1, "hexagon").response.status, "INVALID")
        check("queue", order(), [])
    elif name == "duplicate":
        check("first", send(100, "circle").response.status, "ACCEPTED")
        check("second", send(100, "circle").response.status, "DUPLICATE")
        check("queue", order(), ["circle"])
    elif name in ("request_loss", "ack_loss", "delayed_ack", "timeout"):
        channel = "request" if name == "request_loss" else "response"
        delay = max(0, config.response_timeout_ms // 2) if name == "delayed_ack" else config.response_timeout_ms + 1
        faults.pending.append(Fault(channel, "drop" if name in ("request_loss", "ack_loss") else "delay",
                                    command_id=1, delay_ms=0 if name in ("request_loss", "ack_loss") else delay))
        exchange = send(1)
        clock.advance(delay if name == "delayed_ack" else config.response_timeout_ms)
        check("caller", link.poll(exchange).status, "ACCEPTED" if name == "delayed_ack" else "TIMEOUT")
        check("queue", order(), [] if name == "request_loss" else ["triangle"])
        check("accepted_count", plc.snapshot()["accepted_count"], 0 if name == "request_loss" else 1)
        check("latency_ms", exchange.completed_ms - exchange.sent_ms,
              delay if name == "delayed_ack" else config.response_timeout_ms)
        if name == "ack_loss":
            check("manual_resend", send(1).response.status, "DUPLICATE")
            check("after_resend", order(), ["triangle"])
        if name == "timeout":
            clock.advance(1)
            check("late_ack", exchange.late_response.status, "ACCEPTED")
            check("caller_still_timeout", exchange.response.status, "TIMEOUT")
    elif name in ("disconnect", "reconnect"):
        send(1)
        link.disconnect()
        check("offline", send(2, "circle").response.status, "OFFLINE")
        check("preserved", order(), ["triangle"])
        if name == "reconnect":
            link.reconnect()
            plc.consume_one()
            check("resumed", send(2, "circle").response.status, "ACCEPTED")
            check("queue", order(), ["circle"])
    elif name.startswith("heartbeat"):
        link.heartbeat()
        clock.advance(config.heartbeat_interval_ms)
        link.heartbeat()
        check("normal", plc.snapshot()["heartbeat_state"], "healthy")
        if name != "heartbeat_normal":
            faults.pending.append(Fault("heartbeat", "drop"))
            clock.advance(config.heartbeat_interval_ms)
            link.heartbeat()
            clock.advance(config.heartbeat_timeout_ms)
            check("lost", plc.snapshot()["heartbeat_state"], "lost")
            check("link_connected", link.connected, True)
            check("last_heartbeat_ms", plc.last_heartbeat, config.heartbeat_interval_ms)
            transitions = [row["transition_time_ms"] for row in plc.log if row["action"] == "HEARTBEAT_TIMEOUT"]
            check("transition_time_ms", transitions, [config.heartbeat_interval_ms + config.heartbeat_timeout_ms])
        if name == "heartbeat_recovery":
            link.heartbeat()
            check("recovered", plc.snapshot()["heartbeat_state"], "healthy")
    elif name == "m4_integration":
        adapter = CommandAdapter()
        events = m4_events()
        commands = [command for event in events if (command := adapter.adapt(event)) is not None]
        for command in commands:
            link.send(command)
        check("event_types", [event.event_type.value for event in events],
              ["OBJECT_ENTER"] * 3 + ["OBJECT_EXIT"] * 3)
        check("command_ids", [c.command_id for c in commands], [1, 2, 3])
        check("queue", order(), list(SHAPES))
        check("accepted_count", plc.snapshot()["accepted_count"], 3)
        input_events = [e.to_record() for e in events]
    return dict(scenario=name, source_type="simulated", config=asdict(config), expected=expected,
                actual=observations, passed=observations == expected, final_plc_state=plc.snapshot(),
                link_connected=link.connected, faults_injected=faults.injected, steps=plc.log,
                input_events=input_events)
