"""SIBT v1 compiler — orchestrates Layer 0/1/2 + back-check into CNexus SIBT format."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from core.sibt.v1.language_projection import get_language_projector
from core.sibt.v1.reversible_mapping import BackCheckEngineV1, build_reversible_mapping
from core.sibt.v1.semantic_invariant import (
    SemanticInvariant,
    detect_language,
    parse_to_semantic_invariant,
)

SIBTOutput = Dict[str, Any]


def sibt_v1_enabled() -> bool:
    flag = os.environ.get("CNEXUS_SIBT_V1", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


class SIBTCompilerV1:
    """Compile text → semantic invariant → bilingual projections with reversibility check."""

    def __init__(self) -> None:
        self.projector = get_language_projector()
        self.back_check = BackCheckEngineV1(self.projector)

    def compile(
        self,
        text: str,
        *,
        source_lang: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> SIBTOutput:
        raw = str(text or "").strip()
        lang = source_lang or detect_language(raw)
        siv = parse_to_semantic_invariant(raw, source_lang=lang)
        if intent:
            siv.intent = str(intent)

        zh_text = self.projector.project_zh(siv)
        en_text = self.projector.project_en(siv)

        if lang == "zh" and raw:
            zh_text = self._merge_projection(zh_text, raw)
        elif lang == "en" and raw:
            en_text = self._merge_projection(en_text, raw)

        mapping = build_reversible_mapping(siv, zh_text, en_text)
        checks = self.back_check.run(
            siv,
            zh_text,
            en_text,
            original_input=raw,
            source_lang=lang,
        )

        return {
            "semantic_invariant_id": siv.invariant_id(),
            "semantic_layer": siv.to_layer(),
            "zh": {
                "text": zh_text,
                "faithfulness": checks["faithfulness"]["zh"],
            },
            "en": {
                "text": en_text,
                "faithfulness": checks["faithfulness"]["en"],
            },
            "reversible_mapping": {
                "zh_sentence": mapping.zh_sentence,
                "en_sentence": mapping.en_sentence,
                "maps_to": mapping.maps_to,
                "loss_check": mapping.loss_check,
            },
            "reversibility_score": checks["reversibility_score"],
            "loss_report": checks["loss_report"],
            "back_check": checks,
            "mode": "sibt_v1",
        }

    def project_from_invariant(self, layer: Dict[str, Any]) -> SIBTOutput:
        siv = SemanticInvariant(
            intent=str(layer.get("intent") or "system_or_user_goal"),
            entities=list(layer.get("entities") or []),
            relations=list(layer.get("relations") or []),
            constraints=list(layer.get("constraints") or []),
            meaning_atoms=list(layer.get("meaning_atoms") or []),
        )
        zh_text = self.projector.project_zh(siv)
        en_text = self.projector.project_en(siv)
        mapping = build_reversible_mapping(siv, zh_text, en_text)
        checks = self.back_check.run(siv, zh_text, en_text)
        return {
            "semantic_invariant_id": siv.invariant_id(),
            "semantic_layer": siv.to_layer(),
            "zh": {"text": zh_text, "faithfulness": checks["faithfulness"]["zh"]},
            "en": {"text": en_text, "faithfulness": checks["faithfulness"]["en"]},
            "reversible_mapping": {
                "zh_sentence": mapping.zh_sentence,
                "en_sentence": mapping.en_sentence,
                "maps_to": mapping.maps_to,
                "loss_check": mapping.loss_check,
            },
            "reversibility_score": checks["reversibility_score"],
            "loss_report": checks["loss_report"],
            "mode": "sibt_v1",
        }

    @staticmethod
    def _merge_projection(projected: str, original: str) -> str:
        if not original.strip():
            return projected
        if original.strip() in projected:
            return projected
        return f"{projected}\n{original.strip()}"


_compiler: Optional[SIBTCompilerV1] = None


def get_sibt_compiler() -> SIBTCompilerV1:
    global _compiler
    if _compiler is None:
        _compiler = SIBTCompilerV1()
    return _compiler
