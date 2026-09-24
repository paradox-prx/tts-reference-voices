"""Admission control: at most max_inflight requests at the engine, at most max_queue waiting, each for at most
timeout_s. The engine itself queues without limit, so this is the only back-pressure the service has."""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class QueueFull(Exception):
    """Every slot is busy and the wait queue is full (HTTP 429)."""

    def __init__(self, retry_after_s: int) -> None:
        super().__init__(f"queue full; retry in {retry_after_s} s")
        self.retry_after_s = retry_after_s


class QueueTimeout(Exception):
    """Waited too long for a slot (HTTP 503)."""


class Slot:
    """An acquired in-flight slot. release() is idempotent, so every exit path may call it."""

    def __init__(self, admission: Admission, waited_s: float) -> None:
        self.waited_s = waited_s
        self._admission = admission
        self._since = time.monotonic()
        self._released = False

    def release(self) -> None:
        if not self._released:
            self._released = True
            self._admission._release(time.monotonic() - self._since)


class Admission:
    def __init__(self, max_inflight: int, max_queue: int, timeout_s: float) -> None:
        self.max_inflight, self.max_queue, self.timeout_s = max_inflight, max_queue, timeout_s
        self.inflight = 0
        self.waiting = 0
        self._sem = asyncio.Semaphore(max_inflight)
        self._hold_s = 2.0  # moving average of slot hold time, for Retry-After

    async def acquire(self) -> Slot:
        """Wait for a slot. Raises QueueFull at once when the queue is full, QueueTimeout after timeout_s.
        Cancellation while waiting leaves no trace."""
        if self.inflight >= self.max_inflight and self.waiting >= self.max_queue:
            raise QueueFull(self.retry_after_s())
        start = time.monotonic()
        self.waiting += 1
        try:
            async with asyncio.timeout(self.timeout_s):
                await self._sem.acquire()
        except TimeoutError:
            raise QueueTimeout(f"no engine slot within {self.timeout_s:g} s") from None
        finally:
            self.waiting -= 1
        self.inflight += 1
        return Slot(self, time.monotonic() - start)

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[Slot]:
        slot = await self.acquire()
        try:
            yield slot
        finally:
            slot.release()

    def retry_after_s(self) -> int:
        """Rough time until a queued request would get a slot."""
        return max(1, min(60, math.ceil(self._hold_s * (self.waiting + 1) / self.max_inflight)))

    def _release(self, held_s: float) -> None:
        self.inflight -= 1
        self._hold_s += 0.1 * (held_s - self._hold_s)
        self._sem.release()
