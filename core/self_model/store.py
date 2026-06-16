"""Persistence for Unified SelfModel."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from core.self_model.self_model import SelfModel

logger = logging.getLogger(__name__)


class SelfModelStore:
    """Persist unified self-model — single subjective source of truth."""

    def __init__(self, base_dir: str):
        self.path = Path(base_dir) / "unified_self_model.json"
        self.legacy_path = Path(base_dir) / "subject_self_model.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.model = self._load()

    def _load(self) -> SelfModel:
        for candidate in (self.path, self.legacy_path):
            if not candidate.exists():
                continue
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                return SelfModel.from_dict(data)
            except Exception as exc:
                logger.warning("SelfModel load failed (%s): %s", candidate, exc)
        return SelfModel()

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self.model.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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
