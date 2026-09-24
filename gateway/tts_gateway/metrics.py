"""Prometheus metrics (one registry per app, so tests can build several apps)."""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    disable_created_metrics,
    generate_latest,
)

from .admission import Admission

CONTENT_TYPE = CONTENT_TYPE_LATEST
_NS = "tts"

disable_created_metrics()  # no *_created series: they double every label set and nobody graphs them


class Metrics:
    def __init__(self) -> None:
        r = self.registry = CollectorRegistry()
        self.requests = Counter("requests", "Speech requests by final status", ["status", "voice"],
                                namespace=_NS, registry=r)
        self.request_seconds = Histogram("request_seconds", "Speech request wall time, admission to last byte",
                                         namespace=_NS, registry=r,
                                         buckets=(0.1, 0.25, 0.5, 1, 2, 4, 8, 15, 30, 60, 120, 300))
        self.queue_wait = Histogram("queue_wait_seconds", "Time spent waiting for an in-flight slot",
                                    namespace=_NS, registry=r,
                                    buckets=(0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60))
        self.inflight = Gauge("inflight", "Requests holding an engine slot", namespace=_NS, registry=r)
        self.queue_depth = Gauge("queue_depth", "Requests waiting for an engine slot", namespace=_NS, registry=r)
        self.retries = Counter("retries", "Extra takes, by the reason of the take they replace", ["reason"],
                               namespace=_NS, registry=r)
        self.suspect = Counter("suspect", "Takes whose seconds-per-word fell outside the language band", ["voice"],
                               namespace=_NS, registry=r)
        self.audio_seconds = Counter("audio_seconds", "Audio seconds delivered", ["voice"], namespace=_NS, registry=r)
        self.engine_errors = Counter("engine_errors", "Failed engine calls by kind", ["kind"],
                                     namespace=_NS, registry=r)

    def track(self, admission: Admission) -> None:
        self.inflight.set_function(lambda: admission.inflight)
        self.queue_depth.set_function(lambda: admission.waiting)

    def render(self) -> bytes:
        return generate_latest(self.registry)
