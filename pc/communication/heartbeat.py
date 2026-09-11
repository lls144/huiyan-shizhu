"""PC half of COMM-002: a 1 s heartbeat plus a 2 s communication-loss watchdog.

What this covers and what it does not
-------------------------------------
* Covered: the PC **sends** a heartbeat every ``heartbeat_interval_seconds``
  (default 1 s) into ``M8_AcceptanceData`` DBB2, and independently watches the
  link. If the PLC stops answering for ``comm_loss_timeout_seconds`` (default
  2 s) the PC declares ``comm_lost`` and reports it; when status reads work
  again the outage is closed and its duration recorded.
* Not covered: the PLC-side reaction. "2 s 无心跳 → 三盏灯全闪" needs a watchdog
  and a blink oscillator inside the PLC program, which is a PLC-side change
  (``FB_M8_AcceptanceHarness``), not something the PC can do for it. Until that
  is downloaded the heartbeat byte is simply ignored by the PLC.
* The heartbeat lives in a *reserved* byte of the existing acceptance DB, so no
  block layout changes and the acceptance tool keeps working untouched.

The monitor is clock-injected so the 1 s / 2 s behaviour is unit-testable
without waiting in real time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


@dataclass
class LinkHealth:
    """Everything the UI and the session record need to show about the link."""

    enabled: bool = False
    heartbeat_count: int = 0
    heartbeat_failures: int = 0
    last_heartbeat_at: str | None = None
    heartbeat_intervals: tuple[float, ...] = ()
    comm_lost: bool = False
    comm_lost_for_seconds: float = 0.0
    consecutive_failures: int = 0
    last_success_at: str | None = None
    outage_count: int = 0
    outages: tuple[dict[str, Any], ...] = ()

    @property
    def heartbeat_interval_mean(self) -> float:
        if not self.heartbeat_intervals:
            return 0.0
        return sum(self.heartbeat_intervals) / len(self.heartbeat_intervals)

    def to_record(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "heartbeat_count": self.heartbeat_count,
            "heartbeat_failures": self.heartbeat_failures,
            "last_heartbeat_at": self.last_heartbeat_at,
            "heartbeat_interval_mean_seconds": round(self.heartbeat_interval_mean, 6),
            "heartbeat_interval_min_seconds": round(min(self.heartbeat_intervals), 6)
            if self.heartbeat_intervals
            else None,
            "heartbeat_interval_max_seconds": round(max(self.heartbeat_intervals), 6)
            if self.heartbeat_intervals
            else None,
            "comm_lost": self.comm_lost,
            "comm_lost_for_seconds": round(self.comm_lost_for_seconds, 6),
            "consecutive_failures": self.consecutive_failures,
            "last_success_at": self.last_success_at,
            "outage_count": self.outage_count,
            "outages": list(self.outages),
        }


@dataclass
class _Outage:
    started_at: str
    started_clock: float
    ended_at: str | None = None
    duration_seconds: float | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class HeartbeatMonitor:
    """Drive the heartbeat and watch the link, using any guarded PLC sink."""

    sink: Any
    enabled: bool = True
    interval_seconds: float = 1.0
    timeout_seconds: float = 2.0
    clock: Callable[[], float] = time.monotonic
    wall_clock: Callable[[], str] = _timestamp
    _heartbeats: int = field(default=0, init=False)
    _heartbeat_failures: int = field(default=0, init=False)
    _intervals: list[float] = field(default_factory=list, init=False)
    _last_heartbeat_clock: float | None = field(default=None, init=False)
    _last_attempt_clock: float | None = field(default=None, init=False)
    _last_heartbeat_wall: str | None = field(default=None, init=False)
    _last_success_clock: float | None = field(default=None, init=False)
    _last_success_wall: str | None = field(default=None, init=False)
    _consecutive_failures: int = field(default=0, init=False)
    _comm_lost: bool = field(default=False, init=False)
    _started_clock: float = field(default=0.0, init=False)
    _started_wall: str = field(default="", init=False)
    _outage: _Outage | None = field(default=None, init=False)
    _outages: list[_Outage] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= self.interval_seconds:
            raise ValueError("timeout_seconds must be larger than interval_seconds")
        if self.interval_seconds <= 0 or self.timeout_seconds <= 0:
            raise ValueError("heartbeat interval and timeout must be positive")
        self.enabled = bool(self.enabled and getattr(self.sink, "write_heartbeat", None))
        self._started_clock = self.clock()
        self._started_wall = self.wall_clock()

    # ------------------------------------------------------------------ ticking

    def tick(self) -> LinkHealth:
        """Read the link, update the watchdog, and send a heartbeat when due."""

        now = self.clock()
        reader = getattr(self.sink, "refresh_state", None)
        state = reader() if reader is not None else None
        if state is not None:
            self._last_success_clock = now
            self._last_success_wall = self.wall_clock()
            self._consecutive_failures = 0
            if self._comm_lost:
                self._comm_lost = False
                if self._outage is not None:
                    self._outage.ended_at = self._last_success_wall
                    self._outage.duration_seconds = round(now - self._outage.started_clock, 6)
                    self._outage = None
        else:
            self._consecutive_failures += 1
            # A link that never answered must alarm too, so the reference is the
            # last good read or, before the first one, the monitor start time.
            reference = (
                self._last_success_clock
                if self._last_success_clock is not None
                else self._started_clock
            )
            if not self._comm_lost and (now - reference) >= self.timeout_seconds:
                self._comm_lost = True
                # The outage starts when the PLC last answered, not when the
                # timeout happened to fire, so the recorded duration is the real
                # silence window.
                self._outage = _Outage(
                    started_at=self._last_success_wall or self._started_wall,
                    started_clock=reference,
                )
                self._outages.append(self._outage)

        if self.enabled and self._heartbeat_due(now):
            self._send_heartbeat(now)
        return self.health()

    def _heartbeat_due(self, now: float) -> bool:
        if self._last_heartbeat_clock is None:
            return True
        return (now - self._last_heartbeat_clock) >= self.interval_seconds

    def tick_heartbeat(self) -> None:
        """Send the heartbeat if it is due; cheap enough for every worker frame.

        ``tick`` also drives this, but calling it from the frame loop keeps the
        period close to 1 s instead of snapping to the slower status-poll
        cadence.
        """

        if not self.enabled:
            return
        now = self.clock()
        if self._heartbeat_due(now):
            self._send_heartbeat(now)

    def _send_heartbeat(self, now: float) -> None:
        # Throttle attempts so a dead link does not retry on every worker frame.
        if self._last_attempt_clock is not None and (
            now - self._last_attempt_clock
        ) < self.interval_seconds:
            return
        self._last_attempt_clock = now
        sender = getattr(self.sink, "write_heartbeat", None)
        if sender is None:
            return
        try:
            sender(self._heartbeats + 1)
        except Exception:
            self._heartbeat_failures += 1
            return
        if self._last_heartbeat_clock is not None:
            self._intervals.append(now - self._last_heartbeat_clock)
            del self._intervals[:-200]
        self._last_heartbeat_clock = now
        self._last_heartbeat_wall = self.wall_clock()
        self._heartbeats += 1

    # ----------------------------------------------------------------- outputs

    def health(self) -> LinkHealth:
        lost_for = 0.0
        if self._comm_lost and self._outage is not None:
            lost_for = max(0.0, self.clock() - self._outage.started_clock)
        return LinkHealth(
            enabled=self.enabled,
            heartbeat_count=self._heartbeats,
            heartbeat_failures=self._heartbeat_failures,
            last_heartbeat_at=self._last_heartbeat_wall,
            heartbeat_intervals=tuple(self._intervals),
            comm_lost=self._comm_lost,
            comm_lost_for_seconds=lost_for,
            consecutive_failures=self._consecutive_failures,
            last_success_at=self._last_success_wall,
            outage_count=len(self._outages),
            outages=tuple(outage.to_record() for outage in self._outages[-20:]),
        )
