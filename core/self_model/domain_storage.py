"""Runbook X2 — SelfModel domain-split persistence (Σ.S / Σ.I / Σ.M metadata)."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Literal, Optional

from core.self_model.self_model import SelfModel

logger = logging.getLogger(__name__)

SelfModelDomain = Literal["cognize", "decide", "store_meta"]

DOMAIN_COGNIZE: SelfModelDomain = "cognize"
DOMAIN_DECIDE: SelfModelDomain = "decide"
DOMAIN_STORE_META: SelfModelDomain = "store_meta"

DOMAIN_FIELDS: dict[SelfModelDomain, tuple[str, ...]] = {
    DOMAIN_COGNIZE: ("relational_models", "future_projection", "coherence_score"),
    DOMAIN_DECIDE: (
        "identity_summary",
        "autobiographical_story",
        "core_beliefs",
        "self_expectations",
        "stable_behavioral_bias",
    ),
    DOMAIN_STORE_META: ("last_reconstruction", "total_experiences"),
}

DOMAIN_FILENAMES: dict[SelfModelDomain, str] = {
    DOMAIN_COGNIZE: "self_model_cognize.json",
    DOMAIN_DECIDE: "self_model_decide.json",
    DOMAIN_STORE_META: "self_model_store_meta.json",
}

ALL_DOMAINS: tuple[SelfModelDomain, ...] = (DOMAIN_COGNIZE, DOMAIN_DECIDE, DOMAIN_STORE_META)


class DomainStorageAdapter:
    """Physical split storage for SelfModel — merge on load, partial write on save."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.observability_dir = self.base_dir / "observability"
        self.observability_dir.mkdir(parents=True, exist_ok=True)
        self.unified_path = self.base_dir / "unified_self_model.json"
        self.legacy_subject_path = self.base_dir / "subject_self_model.json"
        self.unified_legacy_path = self.base_dir / "unified_self_model.json.legacy"

    def domain_path(self, domain: SelfModelDomain) -> Path:
        return self.observability_dir / DOMAIN_FILENAMES[domain]

    def all_domain_paths(self) -> tuple[Path, Path, Path]:
        return tuple(self.domain_path(d) for d in ALL_DOMAINS)

    def domains_complete(self) -> bool:
        return all(p.exists() for p in self.all_domain_paths())

    def load(self) -> SelfModel:
        if self.domains_complete():
            return self._load_from_domains()

        legacy = self._find_legacy_unified()
        if legacy is not None:
            return self._migrate_from_legacy(legacy)

        partial = self._load_partial_domains()
        if partial is not None:
            return partial

        return SelfModel()

    def save_domain(self, domain: SelfModelDomain, model: SelfModel) -> None:
        payload = self._extract_domain(model, domain)
        self._atomic_write_json(self.domain_path(domain), payload)

    def save_all_domains(self, model: SelfModel) -> None:
        for domain in ALL_DOMAINS:
            self.save_domain(domain, model)

    def _extract_domain(self, model: SelfModel, domain: SelfModelDomain) -> Dict[str, Any]:
        data = model.to_dict()
        fields = DOMAIN_FIELDS[domain]
        return {key: data[key] for key in fields if key in data}

    def _load_from_domains(self) -> SelfModel:
        merged: Dict[str, Any] = {}
        for domain in ALL_DOMAINS:
            path = self.domain_path(domain)
            try:
                chunk = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("SelfModel domain load failed (%s): %s", path, exc)
                chunk = {}
            if isinstance(chunk, dict):
                merged.update(chunk)
        return SelfModel.from_dict(merged)

    def _load_partial_domains(self) -> Optional[SelfModel]:
        chunks: Dict[str, Any] = {}
        any_found = False
        for domain in ALL_DOMAINS:
            path = self.domain_path(domain)
            if not path.exists():
                continue
            any_found = True
            try:
                chunk = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                chunk = {}
            if isinstance(chunk, dict):
                chunks.update(chunk)
        if not any_found:
            return None
        return SelfModel.from_dict(chunks)

    def _find_legacy_unified(self) -> Optional[Path]:
        for candidate in (self.unified_path, self.legacy_subject_path):
            if candidate.exists():
                return candidate
        return None

    def _migrate_from_legacy(self, legacy_path: Path) -> SelfModel:
        try:
            data = json.loads(legacy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("SelfModel legacy migration read failed (%s): %s", legacy_path, exc)
            return SelfModel()

        model = SelfModel.from_dict(data)
        self.save_all_domains(model)

        if legacy_path == self.unified_path:
            try:
                legacy_path.rename(self.unified_legacy_path)
                logger.info(
                    "SelfModel migrated to domain storage; renamed %s -> %s",
                    legacy_path.name,
                    self.unified_legacy_path.name,
                )
            except OSError as exc:
                logger.warning("SelfModel legacy rename failed: %s", exc)
        elif legacy_path == self.legacy_subject_path:
            try:
                backup = self.base_dir / "subject_self_model.json.legacy"
                if not backup.exists():
                    legacy_path.rename(backup)
            except OSError as exc:
                logger.warning("SelfModel subject legacy rename failed: %s", exc)

        return model

    @staticmethod
    def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
