"""Observation Gateway — ingest, normalize, append (no reverse edge)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.observation.density import DensityPolicy, ObservationDensityManager
from core.observation.event_normalizer import EventNormalizer
from core.observation.schema import CONTRACT_META, ObservationEvent
from core.observation.writer import ObservationWriter

_writer_cache: dict[str, ObservationWriter] = {}


def get_observation_writer(base_dir: str | Path) -> ObservationWriter:
    key = str(Path(base_dir).resolve())
    if key not in _writer_cache:
        _writer_cache[key] = ObservationWriter(key)
    return _writer_cache[key]


class ObservationGateway:
    """
    Runtime → normalize → append-only JSONL.
    Does NOT read CNexus reports, does NOT callback runtime.
    """

    def __init__(
        self,
        base_dir: str | Path,
        *,
        density_policy: DensityPolicy | None = None,
        enable_density: bool = True,
    ) -> None:
        self.base_dir = Path(base_dir)
        self._normalizer = EventNormalizer()
        self._writer = get_observation_writer(base_dir)
        self._density = ObservationDensityManager(base_dir, density_policy) if enable_density else None

    def ingest(
        self,
        *,
        source: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        result = self.ingest_with_density(source=source, event_type=event_type, payload=payload)
        record = result.get("record")
        if record is None:
            return {"skipped": True, "meta": result.get("meta", {})}
        return record

    def ingest_with_density(
        self,
        *,
        source: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        event = ObservationEvent.from_parts(source=source, event_type=event_type, payload=payload)
        normalized = self._normalizer.normalize(event)
        records: list[dict[str, Any]] = [normalized.to_dict()]

        meta: dict[str, Any] = {"accepted": True, "compressed": False}
        if self._density is not None:
            to_append: list[dict[str, Any]] = []
            for rec in records:
                batch, batch_meta = self._density.prepare_for_ingest(rec)
                meta = batch_meta
                if batch_meta.get("accepted") is False:
                    return {"meta": meta, "records": [], "record": None}
                to_append.extend(batch)
            records = to_append

        for rec in records:
            self._writer.append(rec)

        return {
            "meta": meta,
            "records": records,
            "record": records[-1] if records else None,
        }

    def ingest_shadow_compatible(self, observation: dict[str, Any]) -> Path:
        """Optional mirror to gtbs_shadow when runtime shadow observe returns a dict."""
        from core.governance.gtbs.divergence_collector import get_shadow_collector

        return get_shadow_collector(self.base_dir).record(observation)

    @property
    def stream_path(self) -> Path:
        return self._writer.path

    @staticmethod
    def contract_meta() -> dict[str, Any]:
        return dict(CONTRACT_META)
