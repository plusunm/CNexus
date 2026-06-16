"""Event bus — serializable signal plane (no callable payloads)."""

from __future__ import annotations

import queue
import threading
import time
from typing import Any, Dict, Optional

TOPIC_L3_TASK = "l3.task"
TOPIC_L3_DONE = "l3.done"
TOPIC_GOVERNANCE = "governance.signal"


class EventBus:
    def __init__(self) -> None:
        self._topics: Dict[str, queue.SimpleQueue] = {}
        self._lock = threading.Lock()
        self._published = 0
        self._consumed = 0

    def publish(self, topic: str, event: Dict[str, Any]) -> None:
        payload = {**event, "topic": topic, "published_at": time.time()}
        with self._lock:
            topic_queue = self._topics.setdefault(topic, queue.SimpleQueue())
            self._published += 1
        topic_queue.put(payload)

    def try_get(self, topic: str, *, timeout_s: float = 0.0) -> Optional[Dict[str, Any]]:
        topic_queue = self._topics.get(topic)
        if topic_queue is None:
            return None
        try:
            if timeout_s <= 0:
                event = topic_queue.get_nowait()
            else:
                event = topic_queue.get(timeout=timeout_s)
        except queue.Empty:
            return None
        with self._lock:
            self._consumed += 1
        return event

    def pending_estimate(self) -> int:
        with self._lock:
            return max(0, self._published - self._consumed)

    def is_idle(self) -> bool:
        with self._lock:
            if self._published > self._consumed:
                return False
        for topic_queue in self._topics.values():
            if not topic_queue.empty():
                return False
        return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "published": self._published,
                "consumed": self._consumed,
                "pending_estimate": max(0, self._published - self._consumed),
                "topics": list(self._topics.keys()),
            }


_bus: Optional[EventBus] = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = EventBus()
        return _bus
