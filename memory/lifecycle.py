"""Memory lifecycle — metabolic decay, capacity enforcement, retention."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from storage.manager import UnifiedStorageManager


DEFAULT_PROTECTED_LAYERS = frozenset({"identity", "goal", "belief"})


@dataclass
class MemoryManagementConfig:
    max_total_memories: int = 5000
    max_per_layer: Dict[str, int] = field(
        default_factory=lambda: {
            "episodic": 3000,
            "semantic": 1500,
            "narrative": 500,
            "working": 200,
        }
    )
    protected_layers: frozenset[str] = DEFAULT_PROTECTED_LAYERS
    protected_importance_min: float = 0.72
    metabolic_decay_rate: float = 0.02
    forget_alpha: float = 0.85
    forget_decay_threshold: float = 0.12
    min_importance_retain: float = 0.22
    recall_access_cap: int = 50
    stale_days: int = 7

    @classmethod
    def from_dict(cls, cfg: Dict[str, Any]) -> "MemoryManagementConfig":
        mm = cfg.get("memory_management") or {}
        return cls(
            max_total_memories=int(mm.get("max_total_memories", 5000)),
            max_per_layer=dict(mm.get("max_per_layer") or cls().max_per_layer),
            protected_layers=frozenset(mm.get("protected_layers") or DEFAULT_PROTECTED_LAYERS),
            protected_importance_min=float(
                mm.get("protected_importance_min", cfg.get("importance_threshold", 0.72))
            ),
            metabolic_decay_rate=float(mm.get("metabolic_decay_rate", 0.02)),
            forget_alpha=float(mm.get("forget_alpha", cfg.get("forget_alpha", 0.85))),
            forget_decay_threshold=float(mm.get("forget_decay_threshold", 0.12)),
            min_importance_retain=float(mm.get("min_importance_retain", 0.22)),
            recall_access_cap=int(mm.get("recall_access_cap", 50)),
            stale_days=int(mm.get("stale_days", 7)),
        )


@dataclass
class MemoryStats:
    total: int = 0
    by_layer: Dict[str, int] = field(default_factory=dict)
    avg_importance: float = 0.0
    avg_decay_factor: float = 1.0
    high_access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "by_layer": dict(self.by_layer),
            "avg_importance": round(self.avg_importance, 4),
            "avg_decay_factor": round(self.avg_decay_factor, 4),
            "high_access_count": self.high_access_count,
        }


@dataclass
class MaintenanceReport:
    decayed: int = 0
    forgotten: int = 0
    evicted_capacity: int = 0
    capped_access: int = 0
    remaining: int = 0
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decayed": self.decayed,
            "forgotten": self.forgotten,
            "evicted_capacity": self.evicted_capacity,
            "capped_access": self.capped_access,
            "remaining": self.remaining,
            "details": self.details[:20],
        }


class MemoryLifecycleManager:
    """Metabolic memory management — decay, forget, capacity eviction."""

    def __init__(self, storage: "UnifiedStorageManager", config: MemoryManagementConfig):
        self.storage = storage
        self.config = config

    def collect_stats(self) -> MemoryStats:
        rows = self.storage.vector.scan_memories()
        stats = MemoryStats(total=len(rows))
        if not rows:
            return stats

        imp_sum = 0.0
        decay_sum = 0.0
        for row in rows:
            layer = str(row.get("layer", "episodic"))
            stats.by_layer[layer] = stats.by_layer.get(layer, 0) + 1
            imp_sum += float(row.get("importance", 0.5))
            decay_sum += float(row.get("decay_factor", 1.0))
            if int(row.get("access_count", 0)) >= self.config.recall_access_cap:
                stats.high_access_count += 1

        stats.avg_importance = imp_sum / len(rows)
        stats.avg_decay_factor = decay_sum / len(rows)
        return stats

    def run_maintenance(self, *, force: bool = False) -> MaintenanceReport:
        report = MaintenanceReport()
        rows = self.storage.vector.scan_memories()
        report.remaining = len(rows)
        if not rows:
            return report

        now = datetime.now()
        to_delete: List[str] = []
        to_decay: List[tuple[str, float]] = []
        to_cap_access: List[tuple[str, int]] = []

        for row in rows:
            mid = row.get("memory_id")
            if not mid:
                continue

            layer = str(row.get("layer", "episodic"))
            importance = float(row.get("importance", 0.5))
            decay_factor = float(row.get("decay_factor", 1.0))
            access_count = int(row.get("access_count", 1))

            if access_count > self.config.recall_access_cap:
                to_cap_access.append((mid, self.config.recall_access_cap))

            if self._is_protected(layer, importance):
                continue

            last_access = self._parse_ts(row.get("last_accessed_at") or row.get("created_at"), now)
            age_days = (now - last_access).total_seconds() / 86400
            idle_days = age_days

            if idle_days >= self.config.stale_days and importance < 0.55:
                new_decay = max(
                    self.config.forget_decay_threshold * 0.5,
                    decay_factor * self.config.forget_alpha - self.config.metabolic_decay_rate,
                )
                if new_decay < decay_factor:
                    to_decay.append((mid, round(new_decay, 4)))

            effective = importance * decay_factor
            if decay_factor <= self.config.forget_decay_threshold and importance < self.config.min_importance_retain:
                to_delete.append(mid)
                report.details.append(f"forget:{mid[:8]} decay={decay_factor:.3f}")
            elif effective < self.config.min_importance_retain * 0.5 and idle_days > self.config.stale_days * 2:
                to_delete.append(mid)
                report.details.append(f"stale:{mid[:8]} effective={effective:.3f}")

        for mid, capped in to_cap_access:
            self.storage.vector.update_memory(mid, {"access_count": capped})
            report.capped_access += 1

        for mid, new_decay in to_decay:
            self.storage.vector.update_memory(mid, {"decay_factor": new_decay})
            report.decayed += 1

        for mid in to_delete:
            self.storage.forget_memory(mid)
            report.forgotten += 1

        evicted = self._enforce_capacity()
        report.evicted_capacity = evicted
        if evicted:
            report.details.append(f"capacity_evicted:{evicted}")

        report.remaining = self.storage.vector.count_rows()
        return report

    def _enforce_capacity(self) -> int:
        cfg = self.config
        rows = self.storage.vector.scan_memories()
        if not rows:
            return 0

        scored: List[tuple[float, str, str, float]] = []
        for row in rows:
            mid = row.get("memory_id")
            if not mid:
                continue
            layer = str(row.get("layer", "episodic"))
            importance = float(row.get("importance", 0.5))
            if self._is_protected(layer, importance):
                continue
            decay_factor = float(row.get("decay_factor", 1.0))
            access = int(row.get("access_count", 1))
            retention = importance * decay_factor / (1.0 + access * 0.02)
            scored.append((retention, mid, layer, importance))

        scored.sort(key=lambda x: x[0])
        to_remove: List[str] = []
        total = len(rows)

        if total > cfg.max_total_memories:
            need = total - cfg.max_total_memories
            to_remove.extend(mid for _, mid, _, _ in scored[:need])

        by_layer: Dict[str, List[tuple[float, str]]] = {}
        for retention, mid, layer, _ in scored:
            by_layer.setdefault(layer, []).append((retention, mid))

        for layer, cap in cfg.max_per_layer.items():
            layer_rows = [r for r in rows if str(r.get("layer")) == layer]
            protected = sum(
                1
                for r in layer_rows
                if self._is_protected(layer, float(r.get("importance", 0.5)))
            )
            effective_cap = cap + protected
            if len(layer_rows) > effective_cap:
                need = len(layer_rows) - effective_cap
                candidates = by_layer.get(layer, [])
                to_remove.extend(mid for _, mid in candidates[:need])

        removed = 0
        seen = set()
        for mid in to_remove:
            if mid in seen:
                continue
            seen.add(mid)
            self.storage.forget_memory(mid)
            removed += 1
        return removed

    def _is_protected(self, layer: str, importance: float) -> bool:
        if layer in self.config.protected_layers and importance >= self.config.protected_importance_min:
            return True
        return importance >= 0.92

    @staticmethod
    def _parse_ts(value: Any, default: datetime) -> datetime:
        if not value:
            return default
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00").split("+")[0])
        except ValueError:
            return default
