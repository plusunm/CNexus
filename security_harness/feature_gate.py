"""CNexus FeatureGate — runtime mode × tier authorization engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable


class RuntimeMode(str, Enum):
    TRUSTED = "Trusted"
    OFFLINE_GRACE = "OfflineGrace"
    DEGRADED = "Degraded"
    LOCKED = "Locked"


class Tier(str, Enum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"


@dataclass
class FeatureGate:
    runtime_mode_allowed_tiers: dict[str, list[str]]
    core_capabilities: dict[str, str]
    edition_defaults: dict[str, list[str]]
    granted_features: set[str] = field(default_factory=set)
    runtime_mode: RuntimeMode = RuntimeMode.TRUSTED

    @classmethod
    def from_config(cls, path: str | Path) -> "FeatureGate":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        editions = {
            name: cfg["default_features"]
            for name, cfg in data.get("editions", {}).items()
        }
        return cls(
            runtime_mode_allowed_tiers=data["runtime_mode_allowed_tiers"],
            core_capabilities=data["core_capabilities"],
            edition_defaults=editions,
        )

    def load_edition(self, edition: str) -> None:
        features = self.edition_defaults.get(edition, [])
        self.granted_features = set(features)

    def set_runtime_mode(self, mode: RuntimeMode | str) -> None:
        self.runtime_mode = RuntimeMode(mode)

    def set_granted_features(self, features: Iterable[str]) -> None:
        self.granted_features = set(features)

    def tier_for(self, capability_id: str) -> Tier:
        tier_name = self.core_capabilities.get(capability_id)
        if not tier_name:
            raise KeyError(f"unknown capability: {capability_id}")
        return Tier(tier_name)

    def allowed_tiers(self) -> set[Tier]:
        names = self.runtime_mode_allowed_tiers[self.runtime_mode.value]
        return {Tier(name) for name in names}

    def allow(self, capability_id: str) -> bool:
        if capability_id not in self.granted_features:
            return False
        required = self.tier_for(capability_id)
        return required in self.allowed_tiers()

    def denied_reason(self, capability_id: str) -> str:
        if capability_id not in self.granted_features:
            return "not_granted"
        required = self.tier_for(capability_id)
        if required not in self.allowed_tiers():
            return f"tier_blocked:{required.value}:{self.runtime_mode.value}"
        return "ok"

    def apply_heartbeat_failure(self, fail_count: int, *, fail_to_degraded: int, fail_to_locked: int) -> RuntimeMode:
        if fail_count >= fail_to_locked:
            self.runtime_mode = RuntimeMode.LOCKED
        elif fail_count >= fail_to_degraded:
            self.runtime_mode = RuntimeMode.DEGRADED
        elif fail_count >= 1:
            self.runtime_mode = RuntimeMode.OFFLINE_GRACE
        else:
            self.runtime_mode = RuntimeMode.TRUSTED
        return self.runtime_mode
