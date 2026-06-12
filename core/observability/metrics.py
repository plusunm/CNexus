"""Lightweight in-process metrics for production observability (P3-A)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional


class MetricsCollector:
    """Thread-safe counters and latency histograms (no external deps)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._gauges: Dict[str, float] = {}

    def inc(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = float(value)

    def observe_ms(self, name: str, duration_ms: float, *, max_samples: int = 256) -> None:
        with self._lock:
            bucket = self._latencies[name]
            bucket.append(float(duration_ms))
            if len(bucket) > max_samples:
                del bucket[: len(bucket) - max_samples]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            lat_summary = {}
            for key, samples in self._latencies.items():
                if not samples:
                    continue
                sorted_s = sorted(samples)
                n = len(sorted_s)
                lat_summary[key] = {
                    "count": n,
                    "p50_ms": round(sorted_s[n // 2], 2),
                    "p95_ms": round(sorted_s[int(n * 0.95) if n > 1 else 0], 2),
                    "max_ms": round(sorted_s[-1], 2),
                }
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "latencies": lat_summary,
            }


_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _metrics


class timed:
    """Context manager: record wall-clock ms to metrics."""

    def __init__(self, metric_name: str):
        self.metric_name = metric_name
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed_ms = (time.perf_counter() - self._start) * 1000.0
        get_metrics().observe_ms(self.metric_name, elapsed_ms)
        if exc_type is None:
            get_metrics().inc(f"{self.metric_name}.ok")
        else:
            get_metrics().inc(f"{self.metric_name}.error")
        return False
