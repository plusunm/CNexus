"""Metrics scrape adapter — periodic metric snapshots → Observation Bus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from core.observation.gateway import ObservationGateway


class MetricsScrapeAdapter:
    """Scrape metrics from JSON file or HTTP endpoint (read-only pull)."""

    def __init__(self, base_dir: str | Path, *, source_label: str = "external.metrics") -> None:
        self.gateway = ObservationGateway(base_dir)
        self.source_label = source_label

    def scrape_json_file(self, path: str | Path) -> dict[str, Any]:
        file_path = Path(path)
        if not file_path.exists():
            return {"ingested": 0, "error": "file_not_found"}
        try:
            metrics = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {"ingested": 0, "error": f"invalid_json:{exc}"}
        return self._ingest_metrics(metrics, origin=str(file_path.name))

    def scrape_url(self, url: str, *, timeout: float = 5.0) -> dict[str, Any]:
        try:
            with urlopen(url, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            metrics = json.loads(raw)
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {"ingested": 0, "error": str(exc)}
        return self._ingest_metrics(metrics, origin=url)

    def _ingest_metrics(self, metrics: Any, *, origin: str) -> dict[str, Any]:
        if isinstance(metrics, dict):
            items = metrics.get("metrics", metrics)
            if isinstance(items, dict):
                payload = {"origin": origin, "metrics": items, "metric_count": len(items)}
            else:
                payload = {"origin": origin, "metrics": metrics}
        elif isinstance(metrics, list):
            payload = {"origin": origin, "metrics": metrics, "metric_count": len(metrics)}
        else:
            payload = {"origin": origin, "value": metrics}

        result = self.gateway.ingest_with_density(
            source=self.source_label,
            event_type="metrics_tick",
            payload=payload,
        )
        accepted = result.get("meta", {}).get("accepted", True)
        return {
            "ingested": len(result.get("records") or []) if accepted else 0,
            "skipped": 0 if accepted else 1,
            "origin": origin,
            "meta": result.get("meta"),
        }
