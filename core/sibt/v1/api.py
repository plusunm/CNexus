"""SIBT v1 API — semantic invariant projection endpoint."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def project_sibt(
    text: str,
    *,
    source_lang: Optional[str] = None,
    intent: Optional[str] = None,
) -> Dict[str, Any]:
    from core.sibt.v1.compiler import get_sibt_compiler, sibt_v1_enabled

    if not sibt_v1_enabled():
        return {"status": "disabled", "mode": "sibt_v1"}
    compiler = get_sibt_compiler()
    result = compiler.compile(text, source_lang=source_lang, intent=intent)
    result["status"] = "ok"
    return result


async def project_sibt_from_layer(layer: Dict[str, Any]) -> Dict[str, Any]:
    from core.sibt.v1.compiler import get_sibt_compiler, sibt_v1_enabled

    if not sibt_v1_enabled():
        return {"status": "disabled", "mode": "sibt_v1"}
    compiler = get_sibt_compiler()
    result = compiler.project_from_invariant(layer)
    result["status"] = "ok"
    return result
