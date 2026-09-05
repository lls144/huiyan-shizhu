"""Observable FIFO device semantics, separate from link availability."""
from collections import deque
from dataclasses import asdict
from .models import Config, SemanticResponse, Status


class FakePLC:
    def __init__(self, clock, config=None):
        self.clock = clock
        self.config = config or Config()
        self.online = True
        self._queue = deque()
        self._accepted = {}
        self.last_heartbeat = None
        self.statistics = dict(accepted_count=0, rejected_count=0, duplicate_count=0, consumed_count=0)
        self.log = []
        self._heartbeat_state = "never_received"
        clock.subscribe(self._tick)

    @property
    def queue(self):
        return tuple(self._queue)

    def record(self, action, command_id=None, status=None, fault=None, direction="device", **extra):
        self.log.append(dict(step=len(self.log) + 1, virtual_time_ms=self.clock.now_ms,
                             direction=direction, command_id=command_id, action=action,
                             status=status, queue_length=len(self._queue), fault=fault, **extra))

    def _tick(self, old, now):
        if self.last_heartbeat is not None:
            deadline = self.last_heartbeat + self.config.heartbeat_timeout_ms
            if now >= deadline and self._heartbeat_state != "lost":
                self._heartbeat_state = "lost"
                self.record("HEARTBEAT_TIMEOUT", transition_time_ms=deadline,
                            last_heartbeat_ms=self.last_heartbeat,
                            threshold_ms=self.config.heartbeat_timeout_ms)

    def receive_heartbeat(self):
        if not self.online:
            self.record("HEARTBEAT_OFFLINE")
            return False
        self.last_heartbeat = self.clock.now_ms
        self._heartbeat_state = "healthy"
        self.record("HEARTBEAT_RX")
        return True

    def receive(self, command):
        key = command.command_id
        if not self.online:
            status = Status.OFFLINE
        elif (type(key) is not int or key <= 0 or
              command.shape not in ("triangle", "rectangle", "circle") or
              any(v is not None and (type(v) is not int or v <= 0)
                  for v in (command.source_event_id, command.source_object_id))):
            status = Status.INVALID
        elif key in self._accepted:
            status = Status.DUPLICATE if self._accepted[key] == command else Status.INVALID
        elif len(self._queue) >= self.config.capacity:
            status = Status.QUEUE_FULL
        else:
            status = Status.ACCEPTED
            self._queue.append(command)
            self._accepted[key] = command
        counter = ("accepted_count" if status == Status.ACCEPTED else
                   "duplicate_count" if status == Status.DUPLICATE else "rejected_count")
        self.statistics[counter] += 1
        self.record("PLC_" + status, key, status)
        return SemanticResponse(key, status, len(self._queue))

    def consume_one(self):
        item = self._queue.popleft() if self.online and self._queue else None
        if item is not None:
            self.statistics["consumed_count"] += 1
        self.record("DEQUEUE", item.command_id if item else None,
                    "CONSUMED" if item else "NO_ITEM")
        return item

    def snapshot(self):
        return dict(online=self.online, queue=[asdict(c) for c in self._queue],
                    capacity=self.config.capacity, queue_length=len(self._queue),
                    empty=not self._queue, full=len(self._queue) == self.config.capacity,
                    accepted_command_ids=sorted(self._accepted), last_heartbeat_ms=self.last_heartbeat,
                    heartbeat_state=self._heartbeat_state,
                    heartbeat_alive=self._heartbeat_state == "healthy", **self.statistics)
