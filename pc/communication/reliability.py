"""PC-side reliability layer for the M8 command bridge (M9 PC half).

What this layer really guarantees — and what it cannot
-----------------------------------------------------
The lab CPU silently drops roughly half of the put/get writes into
``DB_M8_Acceptance`` (measured 2026-09-10), so :class:`S7PlcCommandSink` already
writes, reads back and re-sends every control block until the PLC really holds
it. That resend is idempotent: the PLC only enqueues on the ``CommandValid``
rising edge, and the dropped write never produced one.

This module adds the parts that were still missing on the PC side:

* **queue-full notification** — the PLC status is read before writing, and a
  full queue is reported instead of letting the command vanish silently
  (``QUEUE_FULL``). With ``queue_full_policy="defer"`` the command is kept and
  re-sent by :meth:`GuardedPlcSink.flush_deferred` once space appears.
* **per-command acknowledgement** — the queue length is compared before and
  after the write; ``SENT`` now means "the queue really grew", not "the write
  did not raise".
* **duplicate protection** — a semantic id that was already confirmed is never
  written a second time (``DUPLICATE``), so a retry can never enqueue twice.
* **timeout accounting** — a command that exceeds ``command_timeout_seconds``
  is reported as ``UNCONFIRMED`` and counted, instead of looking like a success.

What is still TODO and owned by the shared protocol: the PLC program has no
sequence-number/ACK field yet, so a *later* higher-level resend of an
unconfirmed command cannot be proven duplicate-free by the PLC. That is the
M7/M8 contract listed in ``docs/PLC_INTERFACE.md``; this layer refuses to
guess, and reports ``UNCONFIRMED`` for the operator instead.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pc.events.models import VisionEvent

from .config import PlcCommunicationConfig
from .models import (
    PlcCommand,
    PlcCommandResult,
    PlcCommandStatus,
    PlcState,
    command_from_event,
)
from .sink import PlcCommandSink


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


@dataclass
class ReliabilityCounters:
    """Everything an operator or a test needs to see about the PC half."""

    dispatches: int = 0
    sent_confirmed: int = 0
    write_resends: int = 0
    queue_full_deferrals: int = 0
    deferred_retries: int = 0
    queue_full_drops: int = 0
    duplicate_rejections: int = 0
    unconfirmed: int = 0
    timeouts: int = 0
    errors: int = 0

    def to_record(self) -> dict[str, int]:
        return {
            "dispatches": self.dispatches,
            "sent_confirmed": self.sent_confirmed,
            "write_resends": self.write_resends,
            "queue_full_deferrals": self.queue_full_deferrals,
            "deferred_retries": self.deferred_retries,
            "queue_full_drops": self.queue_full_drops,
            "duplicate_rejections": self.duplicate_rejections,
            "unconfirmed": self.unconfirmed,
            "timeouts": self.timeouts,
            "errors": self.errors,
        }


@dataclass
class PlcLinkStatus:
    """Latest observed PLC hardware state plus the PC-side counters."""

    connected: bool = False
    queue_length: int | None = None
    queue_empty: bool | None = None
    queue_full: bool | None = None
    leds: tuple[bool, bool, bool] = (False, False, False)
    last_dequeued_shape: int = 0
    last_dequeued_semantic_id: int = 0
    deferred_count: int = 0
    last_error: str | None = None
    counters: ReliabilityCounters = field(default_factory=ReliabilityCounters)
    fresh: bool = False

    def to_record(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "queue_length": self.queue_length,
            "queue_empty": self.queue_empty,
            "queue_full": self.queue_full,
            "leds": list(self.leds),
            "last_dequeued_shape": self.last_dequeued_shape,
            "last_dequeued_semantic_id": self.last_dequeued_semantic_id,
            "deferred_count": self.deferred_count,
            "last_error": self.last_error,
            "counters": self.counters.to_record(),
            "fresh": self.fresh,
        }


class GuardedPlcSink:
    """Wrap any :class:`PlcCommandSink` with acknowledgement and flow control."""

    def __init__(self, inner: PlcCommandSink, config: PlcCommunicationConfig) -> None:
        self.inner = inner
        self.config = config
        self.counters = ReliabilityCounters()
        self.sent_semantic_ids: set[int] = set()
        self.deferred: deque[VisionEvent] = deque(maxlen=32)
        self._deferred_ids: set[int] = set()
        self.notable: list[dict[str, Any]] = []
        self._state: PlcState | None = None
        self._fresh = False
        self._last_error: str | None = None
        self._inner_resends_at_last = self._inner_resend_counter()

    # ------------------------------------------------------------- lifecycle

    def start(self) -> None:
        self.inner.start()
        self.refresh_state()

    def stop(self) -> None:
        self.inner.stop()

    # ----------------------------------------------------------------- state

    def _inner_resend_counter(self) -> int:
        return int(getattr(self.inner, "write_retry_count", 0) or 0)

    def _collect_resends(self) -> int:
        current = self._inner_resend_counter()
        delta = max(0, current - self._inner_resends_at_last)
        self._inner_resends_at_last = current
        self.counters.write_resends += delta
        return delta

    def refresh_state(self) -> PlcState | None:
        """Read the PLC-owned status bytes; keep the last good value on failure."""

        reader = getattr(self.inner, "read_state", None)
        if reader is None:
            self._fresh = False
            return None
        try:
            state = reader()
        except Exception as error:
            self._last_error = f"{type(error).__name__}: {error}"
            self._fresh = False
            return None
        if state is None:
            self._fresh = False
            return None
        self._state = state
        self._fresh = True
        return state

    def status(self) -> PlcLinkStatus:
        state = self._state
        return PlcLinkStatus(
            connected=state is not None,
            queue_length=state.queue_length if state else None,
            queue_empty=state.queue_empty if state else None,
            queue_full=state.queue_full if state else None,
            leds=state.leds if state else (False, False, False),
            last_dequeued_shape=state.last_dequeued_shape if state else 0,
            last_dequeued_semantic_id=state.last_dequeued_semantic_id if state else 0,
            deferred_count=len(self.deferred),
            last_error=self._last_error,
            counters=self.counters,
            fresh=self._fresh,
        )

    # --------------------------------------------------------------- commands

    def send_event(self, event: VisionEvent) -> PlcCommandResult:
        return self._attempt(event, is_retry=False)

    def _attempt(self, event: VisionEvent, *, is_retry: bool) -> PlcCommandResult:
        command = command_from_event(event)
        if command is None:
            return PlcCommandResult(None, PlcCommandStatus.SKIPPED, detail="not a known ENTER shape")
        if is_retry:
            self.counters.deferred_retries += 1
        else:
            self.counters.dispatches += 1

        if (
            self.config.duplicate_policy == "refuse"
            and command.semantic_id in self.sent_semantic_ids
        ):
            self.counters.duplicate_rejections += 1
            self._note("duplicate", command, f"semantic id {command.semantic_id} already confirmed")
            return PlcCommandResult(
                command,
                PlcCommandStatus.DUPLICATE,
                detail=f"semantic id {command.semantic_id} already confirmed; not written again",
                confirmed=True,
            )

        state = self.refresh_state()
        if state is not None and state.queue_full:
            return self._handle_full_queue(command, event, state, note="pre-write check")

        return self._write(command, event, state)

    def _handle_full_queue(
        self,
        command: PlcCommand,
        event: VisionEvent,
        state: PlcState,
        note: str,
    ) -> PlcCommandResult:
        if self.config.queue_full_policy == "defer":
            if command.semantic_id not in self._deferred_ids:
                self.deferred.append(event)
                self._deferred_ids.add(command.semantic_id)
                self.counters.queue_full_deferrals += 1
            self._note(
                "queue_full",
                command,
                f"{note}: queue length {state.queue_length} is full; command deferred",
            )
            return PlcCommandResult(
                command,
                PlcCommandStatus.QUEUE_FULL,
                queue_length=state.queue_length,
                queue_length_before=state.queue_length,
                detail=(
                    f"PLC queue is full (length {state.queue_length}); "
                    f"command deferred, {len(self.deferred)} waiting"
                ),
            )
        self.counters.queue_full_drops += 1
        self._note("queue_full", command, f"{note}: queue full; command dropped by policy")
        return PlcCommandResult(
            command,
            PlcCommandStatus.QUEUE_FULL,
            queue_length=state.queue_length,
            queue_length_before=state.queue_length,
            detail=f"PLC queue is full (length {state.queue_length}); command dropped by policy",
        )

    def _write(
        self,
        command: PlcCommand,
        event: VisionEvent,
        before_state: PlcState | None,
    ) -> PlcCommandResult:
        before_length = before_state.queue_length if before_state else None
        started = time.perf_counter()
        try:
            result = self.inner.send_event(event)
        except Exception as error:
            self._last_error = f"{type(error).__name__}: {error}"
            self.counters.errors += 1
            self._note("error", command, self._last_error)
            return PlcCommandResult(
                command,
                PlcCommandStatus.ERROR,
                queue_length_before=before_length,
                detail=self._last_error,
            )
        elapsed = time.perf_counter() - started
        resends = self._collect_resends()

        if result.status is PlcCommandStatus.ERROR:
            self.counters.errors += 1
            self._last_error = result.detail or "PLC write failed"
            if "never confirmed" in self._last_error:
                self.counters.timeouts += 1
            self._note("error", command, self._last_error)
            return PlcCommandResult(
                command,
                PlcCommandStatus.ERROR,
                queue_length_before=before_length,
                resends=resends,
                elapsed_seconds=round(elapsed, 6),
                detail=result.detail,
            )

        after_state = self.refresh_state()
        after_length = after_state.queue_length if after_state else result.queue_length
        confirmed = False
        confirmation = ""
        if before_length is not None and after_length is not None:
            confirmed = after_length == before_length + 1
            confirmation = f"queue {before_length} -> {after_length}"
        elif after_length is not None:
            confirmed = after_length > 0
            confirmation = f"queue length {after_length}"
        else:
            # No readable status: fall back to the inner sink's own confirmation.
            confirmed = result.status is PlcCommandStatus.SENT
            confirmation = "inner sink reported SENT (no status region readable)"
        if not confirmed and after_state is not None and command.semantic_id:
            # auto_dequeue drains the queue inside send_event, so the length can
            # return to its previous value; the dequeued semantic id is then the
            # proof that this exact command reached the PLC.
            if after_state.last_dequeued_semantic_id == command.semantic_id:
                confirmed = True
                confirmation = (
                    f"dequeued semantic id {command.semantic_id} "
                    f"(queue length returned to {after_length})"
                )

        timed_out = elapsed > self.config.command_timeout_seconds
        if confirmed and not timed_out:
            self.counters.sent_confirmed += 1
            if command.semantic_id:
                self.sent_semantic_ids.add(command.semantic_id)
            return PlcCommandResult(
                command,
                PlcCommandStatus.SENT,
                queue_length=after_length,
                queue_length_before=before_length,
                resends=resends,
                elapsed_seconds=round(elapsed, 6),
                confirmed=True,
                detail=(
                    f"confirmed by {confirmation}; "
                    f"write resends={resends}; elapsed={elapsed:.3f}s"
                ),
            )

        if after_state is not None and after_state.queue_full and before_length == after_length:
            # The queue filled up between the pre-check and the write, and the PLC
            # silently refuses enqueues into a full queue.
            return self._handle_full_queue(command, event, after_state, note="post-write check")

        if timed_out:
            self.counters.timeouts += 1
        self.counters.unconfirmed += 1
        detail = (
            f"write did not raise but the queue did not grow "
            f"({before_length} -> {after_length}); elapsed={elapsed:.3f}s"
        )
        if timed_out:
            detail += f"; exceeded command_timeout_seconds={self.config.command_timeout_seconds}"
        self._last_error = detail
        self._note("unconfirmed", command, detail)
        return PlcCommandResult(
            command,
            PlcCommandStatus.UNCONFIRMED,
            queue_length=after_length,
            queue_length_before=before_length,
            resends=resends,
            elapsed_seconds=round(elapsed, 6),
            detail=detail,
        )

    def flush_deferred(self, limit: int = 4) -> tuple[PlcCommandResult, ...]:
        """Re-send deferred commands once the queue has room again."""

        results: list[PlcCommandResult] = []
        for _ in range(min(limit, len(self.deferred))):
            if not self.deferred:
                break
            event = self.deferred[0]  # peek: a still-blocked command stays queued
            result = self._attempt(event, is_retry=True)
            results.append(result)
            if result.status is PlcCommandStatus.QUEUE_FULL:
                break
            self.deferred.popleft()
            self._deferred_ids.discard(event.object_id)
        if results:
            self.refresh_state()
        return tuple(results)

    def dequeue(self) -> PlcCommandResult:
        try:
            result = self.inner.dequeue()
        except Exception as error:
            self._last_error = f"{type(error).__name__}: {error}"
            self.counters.errors += 1
            return PlcCommandResult(None, PlcCommandStatus.ERROR, detail=self._last_error)
        self._collect_resends()
        self.refresh_state()
        return result

    def reset(self) -> PlcCommandResult:
        try:
            result = self.inner.reset()
        except Exception as error:
            self._last_error = f"{type(error).__name__}: {error}"
            self.counters.errors += 1
            return PlcCommandResult(None, PlcCommandStatus.ERROR, detail=self._last_error)
        self._collect_resends()
        self.deferred.clear()
        self._deferred_ids.clear()
        self.sent_semantic_ids.clear()
        self.refresh_state()
        return result

    # ---------------------------------------------------------------- helpers

    def _note(self, kind: str, command: PlcCommand, detail: str) -> None:
        self.notable.append(
            {
                "at": _timestamp(),
                "kind": kind,
                "shape": command.shape,
                "semantic_id": command.semantic_id,
                "detail": detail,
            }
        )
        if len(self.notable) > 200:
            del self.notable[: len(self.notable) - 200]

    def recent_notable(self, limit: int = 20) -> tuple[dict[str, Any], ...]:
        return tuple(self.notable[-limit:])


def build_guarded_plc_sink(config: PlcCommunicationConfig) -> GuardedPlcSink | None:
    """Return the guarded bridge, or ``None`` when PLC communication is disabled."""

    from .sink import build_plc_sink

    inner = build_plc_sink(config)
    if inner is None:
        return None
    return GuardedPlcSink(inner, config)
