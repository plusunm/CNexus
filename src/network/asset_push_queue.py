"""Persistent retry queue for failed asset peer pushes."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


class AssetPushRetryQueue:
    """Exponential-backoff queue for asset pushes that failed transiently."""

    def __init__(
        self,
        storage_path: str | Path,
        peer_sync,
        *,
        max_attempts: Optional[int] = None,
        base_delay_s: Optional[float] = None,
        max_delay_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        enabled: Optional[bool] = None,
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.peer_sync = peer_sync
        self.max_attempts = max_attempts if max_attempts is not None else _env_int("CNEXUS_ASSET_PUSH_RETRY_MAX", 8)
        self.base_delay_s = base_delay_s if base_delay_s is not None else float(_env_int("CNEXUS_ASSET_PUSH_RETRY_BASE", 30))
        self.max_delay_s = max_delay_s if max_delay_s is not None else float(_env_int("CNEXUS_ASSET_PUSH_RETRY_MAX_DELAY", 3600))
        self.poll_interval_s = poll_interval_s if poll_interval_s is not None else float(_env_int("CNEXUS_ASSET_PUSH_RETRY_POLL", 45))
        self.enabled = enabled if enabled is not None else _env_truthy("CNEXUS_ASSET_PUSH_RETRY_ENABLE", True)
        self._lock = threading.Lock()
        self._items: List[Dict[str, Any]] = self._load()
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_stop = threading.Event()
        self.last_run_at: Optional[float] = None
        self.last_run_report: Dict[str, Any] = {}

    def _load(self) -> List[Dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _persist(self):
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(self._items, handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _retryable(error: str) -> bool:
        err = str(error or "").lower()
        if not err:
            return False
        if err.startswith("asset_too_large"):
            return False
        if err.startswith("asset_not_found"):
            return False
        if err.startswith("invalid_"):
            return False
        return True

    def enqueue(
        self,
        asset_id: str,
        peer_host: str,
        *,
        peer_pubkey: str = "",
        error: str = "",
    ) -> dict:
        if not self.enabled:
            return {"ok": False, "error": "retry_queue_disabled"}
        asset_id = str(asset_id or "").strip()
        peer_host = str(peer_host or "").strip()
        if not asset_id or not peer_host:
            return {"ok": False, "error": "missing_asset_or_peer"}
        if not self._retryable(error):
            return {"ok": False, "error": "not_retryable", "reason": error}

        now = time.time()
        with self._lock:
            for item in self._items:
                if item.get("asset_id") == asset_id and item.get("peer_host") == peer_host:
                    item["last_error"] = error
                    item["updated_at"] = now
                    item["status"] = "pending"
                    if item.get("next_retry_at", 0) <= now:
                        item["next_retry_at"] = now + self.base_delay_s
                    self._persist()
                    return {"ok": True, "queued": True, "id": item.get("id"), "deduped": True}

            row = {
                "id": uuid.uuid4().hex[:16],
                "asset_id": asset_id,
                "peer_host": peer_host,
                "peer_pubkey": peer_pubkey,
                "attempts": 0,
                "max_attempts": self.max_attempts,
                "next_retry_at": now + self.base_delay_s,
                "last_error": error,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            }
            self._items.append(row)
            self._persist()
            return {"ok": True, "queued": True, "id": row["id"]}

    def _backoff_delay(self, attempts: int) -> float:
        delay = self.base_delay_s * (2 ** max(0, attempts - 1))
        return min(delay, self.max_delay_s)

    def process_pending(self, *, limit: int = 20) -> dict:
        if not self.enabled or self.peer_sync is None:
            return {"ok": False, "error": "queue_unavailable"}

        now = time.time()
        processed = 0
        succeeded = 0
        failed = 0
        requeued = 0
        dead = 0

        with self._lock:
            pending = [
                item for item in self._items
                if item.get("status") == "pending" and float(item.get("next_retry_at") or 0) <= now
            ]
            pending.sort(key=lambda row: float(row.get("next_retry_at") or 0))

        for item in pending[: max(1, limit)]:
            processed += 1
            asset_id = str(item.get("asset_id") or "")
            host = str(item.get("peer_host") or "")
            pubkey = str(item.get("peer_pubkey") or "")
            result = self.peer_sync.push_to_peer(host, pubkey, asset_id)
            with self._lock:
                target = next((row for row in self._items if row.get("id") == item.get("id")), None)
                if target is None:
                    continue
                target["attempts"] = int(target.get("attempts") or 0) + 1
                target["updated_at"] = time.time()
                if result.get("ok"):
                    target["status"] = "done"
                    target["last_error"] = None
                    succeeded += 1
                else:
                    failed += 1
                    err = str(result.get("error") or "push_failed")
                    target["last_error"] = err
                    if int(target.get("attempts") or 0) >= int(target.get("max_attempts") or self.max_attempts):
                        target["status"] = "dead"
                        dead += 1
                    elif self._retryable(err):
                        target["status"] = "pending"
                        target["next_retry_at"] = time.time() + self._backoff_delay(int(target["attempts"]))
                        requeued += 1
                    else:
                        target["status"] = "dead"
                        dead += 1
                self._persist()

        report = {
            "ok": True,
            "processed": processed,
            "succeeded": succeeded,
            "failed": failed,
            "requeued": requeued,
            "dead": dead,
            "pending": self.pending_count(),
            "at": time.time(),
        }
        self.last_run_at = report["at"]
        self.last_run_report = report
        return report

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for item in self._items if item.get("status") == "pending")

    def dead_count(self) -> int:
        with self._lock:
            return sum(1 for item in self._items if item.get("status") == "dead")

    def list_items(self, *, status: Optional[str] = None, limit: int = 50) -> List[dict]:
        with self._lock:
            rows = [dict(item) for item in self._items]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        rows.sort(key=lambda row: float(row.get("updated_at") or 0), reverse=True)
        return rows[: max(1, limit)]

    def start_worker(self):
        if not self.enabled:
            return
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._worker_stop.clear()

        def _loop():
            while not self._worker_stop.wait(self.poll_interval_s):
                try:
                    self.process_pending()
                except Exception:
                    pass

        self._worker_thread = threading.Thread(
            target=_loop,
            daemon=True,
            name="cnexus-asset-push-retry",
        )
        self._worker_thread.start()

    def stop_worker(self):
        self._worker_stop.set()

    def status(self) -> dict:
        with self._lock:
            items = list(self._items)
        return {
            "enabled": self.enabled,
            "pending": sum(1 for item in items if item.get("status") == "pending"),
            "done": sum(1 for item in items if item.get("status") == "done"),
            "dead": sum(1 for item in items if item.get("status") == "dead"),
            "max_attempts": self.max_attempts,
            "poll_interval_s": self.poll_interval_s,
            "last_run_at": self.last_run_at,
            "last_run": dict(self.last_run_report),
            "recent": self.list_items(limit=10),
        }
