"""Deterministic millisecond clock and one-shot fault-injected memory link."""
from dataclasses import dataclass, asdict
import heapq
from .models import SemanticResponse, Status, positive_int


class VirtualClock:
    def __init__(self):
        self.now_ms = 0
        self._listeners = []
        self._scheduled = []
        self._sequence = 0

    def subscribe(self, callback):
        self._listeners.append(callback)

    def schedule(self, delay_ms, callback):
        positive_int(delay_ms, "delay_ms", zero=True)
        self._sequence += 1
        heapq.heappush(self._scheduled, (self.now_ms + delay_ms, self._sequence, callback))

    def _move(self, time_ms):
        old = self.now_ms
        self.now_ms = time_ms
        for callback in self._listeners:
            callback(old, time_ms)

    def advance(self, milliseconds):
        positive_int(milliseconds, "milliseconds", zero=True)
        target = self.now_ms + milliseconds
        while self._scheduled and self._scheduled[0][0] <= target:
            when, _, callback = heapq.heappop(self._scheduled)
            self._move(when)
            callback()
        self._move(target)


@dataclass(frozen=True)
class Fault:
    channel: str
    action: str
    command_id: int | None = None
    delay_ms: int = 0

    def __post_init__(self):
        if self.channel not in ("request", "response", "heartbeat") or self.action not in ("drop", "delay"):
            raise ValueError("invalid fault channel/action")
        positive_int(self.delay_ms, "delay_ms", zero=True)
        if self.action == "drop" and self.delay_ms:
            raise ValueError("drop must have zero delay")
        if self.command_id is not None:
            positive_int(self.command_id, "command_id")
        if self.channel == "heartbeat" and self.command_id is not None:
            raise ValueError("heartbeat has no command ID")


class FaultInjector:
    """First matching rule consumed once; ordered plans replay exactly."""
    def __init__(self, plan=()):
        self.pending = list(plan)
        self.injected = []

    def take(self, channel, command_id=None):
        for index, rule in enumerate(self.pending):
            if rule.channel == channel and rule.command_id in (None, command_id):
                self.injected.append(asdict(rule))
                return self.pending.pop(index)
        return None


@dataclass
class Exchange:
    command_id: int
    sent_ms: int
    deadline_ms: int
    response: SemanticResponse | None = None
    completed_ms: int | None = None
    late_response: SemanticResponse | None = None


class InMemoryLink:
    def __init__(self, plc, faults=None):
        self.plc = plc
        self.clock = plc.clock
        self.faults = faults or FaultInjector()
        self.connected = True
        self._generation = 0

    def disconnect(self):
        self.connected = False
        self._generation += 1
        self.plc.record("DISCONNECT", direction="link")

    def reconnect(self):
        self.connected = True
        self.plc.record("RECONNECT", direction="link")

    def _deliver(self, channel, command_id, callback):
        generation = self._generation
        rule = self.faults.take(channel, command_id)
        if rule:
            self.plc.record(channel.upper() + "_" + rule.action.upper(), command_id,
                            fault=asdict(rule), direction="link")
            if rule.action == "drop":
                return

        def delivery():
            if not self.connected or generation != self._generation:
                self.plc.record(channel.upper() + "_CANCELLED", command_id, direction="link")
                return
            callback()

        self.clock.schedule(rule.delay_ms if rule else 0, delivery)

    def send(self, command):
        exchange = Exchange(command.command_id, self.clock.now_ms,
                            self.clock.now_ms + self.plc.config.response_timeout_ms)
        self.plc.record("SEND", command.command_id, direction="pc_to_plc", command=asdict(command))
        if not self.connected:
            exchange.response = SemanticResponse(command.command_id, Status.OFFLINE, len(self.plc.queue))
            exchange.completed_ms = self.clock.now_ms
            self.plc.record("OFFLINE", command.command_id, Status.OFFLINE, direction="caller")
            return exchange

        def response_received(response):
            if exchange.response is None:
                exchange.response = response
                exchange.completed_ms = self.clock.now_ms
                self.plc.record("ACK_RX", command.command_id, response.status, direction="plc_to_pc")
            else:
                exchange.late_response = response
                self.plc.record("LATE_ACK", command.command_id, response.status, direction="plc_to_pc")

        def request_received():
            response = self.plc.receive(command)
            self._deliver("response", command.command_id, lambda: response_received(response))

        def expire():
            if exchange.response is None:
                exchange.response = SemanticResponse(command.command_id, Status.TIMEOUT, len(self.plc.queue),
                                                      "caller deadline reached; state is simulator observation")
                exchange.completed_ms = self.clock.now_ms
                self.plc.record("TIMEOUT", command.command_id, Status.TIMEOUT, direction="caller")
        self.clock.schedule(self.plc.config.response_timeout_ms, expire)
        self._deliver("request", command.command_id, request_received)
        self.clock.advance(0)
        return exchange

    def poll(self, exchange):
        self.clock.advance(0)
        return exchange.response

    def advance(self, milliseconds):
        self.clock.advance(milliseconds)

    def heartbeat(self):
        if not self.connected:
            self.plc.record("HEARTBEAT_OFFLINE", direction="link")
            return
        self._deliver("heartbeat", None, self.plc.receive_heartbeat)
        self.clock.advance(0)
