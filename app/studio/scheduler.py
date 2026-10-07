"""One shared queue in front of the engine. Customer requests go before dev-job requests; dev jobs never use the last
(max_inflight - dev_max_inflight) slots, so a customer request starts within one generation time even under a full
dataset job. An `exclusive` request (an exact-seed take) waits until nothing else runs and blocks new work while it
runs: vLLM batches requests together, and a seed only reproduces a take when the request runs alone."""
from __future__ import annotations

import asyncio
import itertools
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

CUSTOMER, DEV = 0, 1


@dataclass(order=True)
class _Waiter:
    priority: int
    seq: int
    exclusive: bool = field(compare=False, default=False)
    event: asyncio.Event = field(compare=False, default_factory=asyncio.Event)


class Busy(Exception):
    def __init__(self, waiting: int):
        super().__init__(f"server busy: {waiting} customer requests already waiting")
        self.waiting = waiting


class Scheduler:
    def __init__(self, max_inflight: int, dev_max_inflight: int, customer_queue_max: int = 40):
        self.max_inflight = max_inflight
        self.dev_max = min(dev_max_inflight, max_inflight)
        self.customer_queue_max = customer_queue_max
        self.inflight = {CUSTOMER: 0, DEV: 0}
        self.exclusive_running = False
        self.waiting: list[_Waiter] = []
        self._seq = itertools.count()
        self.served = {CUSTOMER: 0, DEV: 0}

    @property
    def total_inflight(self) -> int:
        return self.inflight[CUSTOMER] + self.inflight[DEV]

    def position(self, w: _Waiter) -> int:
        """1-based position among waiters that go before or with it."""
        return 1 + sum(1 for o in self.waiting if o < w)

    def _can_start(self, w: _Waiter) -> bool:
        if self.exclusive_running:
            return False
        if w.exclusive:
            return self.total_inflight == 0
        if self.total_inflight >= self.max_inflight:
            return False
        if w.priority == DEV and self.inflight[DEV] >= self.dev_max:
            return False
        return True

    def _dispatch(self) -> None:
        self.waiting.sort()  # customers first, then FIFO
        for w in list(self.waiting):
            if self._can_start(w):
                self.waiting.remove(w)
                if w.exclusive:
                    self.exclusive_running = True
                self.inflight[w.priority] += 1
                w.event.set()
            elif w.exclusive:
                break  # an exclusive request waits for the engine to drain: nothing behind it may start

    def status(self) -> dict:
        return {"inflight": dict(customer=self.inflight[CUSTOMER], dev=self.inflight[DEV]),
                "waiting": dict(customer=sum(w.priority == CUSTOMER for w in self.waiting),
                                dev=sum(w.priority == DEV for w in self.waiting)),
                "max_inflight": self.max_inflight, "dev_max_inflight": self.dev_max,
                "exclusive_running": self.exclusive_running, "served": dict(self.served)}

    @asynccontextmanager
    async def slot(self, priority: int = DEV, exclusive: bool = False, on_wait=None):
        if priority == CUSTOMER:
            waiting = sum(w.priority == CUSTOMER for w in self.waiting)
            if waiting >= self.customer_queue_max:
                raise Busy(waiting)
        w = _Waiter(priority, next(self._seq), exclusive)
        self.waiting.append(w)
        self._dispatch()
        try:
            while not w.event.is_set():
                if on_wait is not None:
                    await on_wait(self.position(w))
                try:
                    await asyncio.wait_for(w.event.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass
        except BaseException:
            if w in self.waiting:
                self.waiting.remove(w)
            elif w.event.is_set():
                self._release(w)
            raise
        try:
            yield
        finally:
            self._release(w)

    def _release(self, w: _Waiter) -> None:
        self.inflight[w.priority] -= 1
        self.served[w.priority] += 1
        if w.exclusive:
            self.exclusive_running = False
        self._dispatch()
