"""Persistence for Unified SelfModel — domain-split storage (X2)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from core.self_model.domain_storage import (
    DOMAIN_COGNIZE,
    DOMAIN_DECIDE,
    DOMAIN_STORE_META,
    DomainStorageAdapter,
    SelfModelDomain,
)
from core.self_model.self_model import SelfModel

logger = logging.getLogger(__name__)


class SelfModelStore:
    """Persist unified self-model — in-memory SSOT with split physical domains."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._adapter = DomainStorageAdapter(self.base_dir)
        # Legacy path references for diagnostics / migration audit.
        self.path = self.base_dir / "unified_self_model.json"
        self.legacy_path = self.base_dir / "subject_self_model.json"
        self.model = self._load()

    def _load(self) -> SelfModel:
        return self._adapter.load()

    def save(self) -> None:
        """Full persist — all three domains (integrate / legacy callers)."""
        self._adapter.save_all_domains(self.model)

    def save_domain(self, domain: SelfModelDomain) -> None:
        """Partial persist — single Runbook domain file only."""
        self._adapter.save_domain(domain, self.model)

    def store_step_touch(self, *, block_updated_at: Optional[str] = None) -> Dict[str, Any]:
        """Runbook STORE_step writer — merges last_reconstruction with block_updated_at."""
        from core.evolved.cognitive_hooks import apply_store_selfmodel_step

        return apply_store_selfmodel_step(self, block_updated_at=block_updated_at)

    def integrate(
        self,
        user_input: str,
        response: str,
        *,
        reflection: Optional[str] = None,
        dna=None,
        prediction_error: float = 0.0,
        relation_shift: float = 0.0,
    ) -> Dict[str, Any]:
        report = self.model.integrate_experience(
            user_input,
            response,
            reflection=reflection,
            dna=dna,
            prediction_error=prediction_error,
            relation_shift=relation_shift,
        )
        self.save()
        return report

    def reconstruct(self, experience: str, reflection: str) -> SelfModel:
        """Legacy alias."""
        self.integrate(experience, "", reflection=reflection)
        return self.model


__all__ = [
    "SelfModelStore",
    "DOMAIN_COGNIZE",
    "DOMAIN_DECIDE",
    "DOMAIN_STORE_META",
]
