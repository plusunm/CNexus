from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any, Dict, List, Optional

from core.execution.plane import ExecutionPlane
from core.execution.types import ExecutionStatus
from core.model_registry import ModelProfile, ModelRegistry
from core.ollama_manager import find_ollama_binary, get_ollama_status, start_ollama, stop_ollama

logger = logging.getLogger(__name__)


class LocalStackManager:
    """Layer 3 — start/detect/pull/health only; no cognition."""

    def __init__(self, plane: ExecutionPlane, config: Dict[str, Any]):
        self.plane = plane
        self.config = config
        self.host = plane.ollama_host

    def readiness(
        self,
        registry: Optional[ModelRegistry] = None,
    ) -> ExecutionStatus:
        profile = registry.get_default() if registry else None
        return self.plane.execution_status(chat_profile=profile)

    def readiness_dict(self, registry: Optional[ModelRegistry] = None) -> Dict[str, Any]:
        return self.readiness(registry=registry).to_dict()

    def ollama_status(self) -> Dict[str, Any]:
        return get_ollama_status(self.host)

    def start_ollama(self) -> Dict[str, Any]:
        return start_ollama(self.host)

    def stop_ollama(self) -> Dict[str, Any]:
        return stop_ollama(self.host)

    def ensure_models(
        self,
        models: Optional[List[str]] = None,
        *,
        timeout_seconds: int = 600,
    ) -> Dict[str, Any]:
        """Background-friendly model bootstrap (pull missing models)."""
        if models is None:
            models = self._default_bootstrap_models()
        if not models:
            return {"ok": True, "detail": "nothing_to_bootstrap", "results": []}

        if not get_ollama_status(self.host).get("running"):
            start = start_ollama(self.host)
            if not start.get("ok") and not start.get("running"):
                return {"ok": False, "detail": "ollama_not_running", "results": []}

        binary = find_ollama_binary()
        if not binary:
            return {"ok": False, "detail": "ollama_binary_missing", "results": []}

        results: List[Dict[str, Any]] = []
        from core.windows_subprocess import run_hidden

        for model in models:
            if self.plane.ollama.model_pulled(model):
                results.append({"model": model, "status": "already_present"})
                continue
            try:
                proc = run_hidden(
                    [binary, "pull", model],
                    timeout=float(timeout_seconds),
                )
                ok = proc.returncode == 0
                results.append(
                    {
                        "model": model,
                        "status": "pulled" if ok else "failed",
                        "detail": (proc.stderr or proc.stdout or "")[:300],
                    }
                )
            except subprocess.TimeoutExpired:
                results.append({"model": model, "status": "timeout"})
            except Exception as exc:
                results.append({"model": model, "status": "error", "detail": str(exc)})

        self.plane.ollama._cached_tags = None
        ok = all(r.get("status") in ("already_present", "pulled") for r in results)
        return {"ok": ok, "detail": "bootstrap_complete", "results": results}

    def _default_bootstrap_models(self) -> List[str]:
        models: List[str] = []
        embed = self.config.get("embedding_model")
        if embed:
            models.append(str(embed))
        llm = self.config.get("llm_model")
        if llm:
            models.append(str(llm))
        return list(dict.fromkeys(models))
