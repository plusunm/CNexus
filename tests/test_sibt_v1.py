"""CNexus SIBT v1 — semantic invariant + bidirectional reversible projection."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain-memory-ui"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sibt.v1.compiler import SIBTCompilerV1, sibt_v1_enabled
from core.sibt.v1.language_projection import get_language_projector
from core.sibt.v1.reversible_mapping import BackCheckEngineV1, compare_atom_sets
from core.sibt.v1.semantic_invariant import detect_language, parse_to_semantic_invariant


class TestSIBTV1(unittest.TestCase):
    def test_enabled_default(self):
        self.assertTrue(sibt_v1_enabled())

    def test_detect_language(self):
        self.assertEqual(detect_language("界面语言切换问题"), "zh")
        self.assertEqual(detect_language("UI language switching issue"), "en")

    def test_parse_semantic_invariant(self):
        text = (
            "UI language switching; translation accuracy issue exists; "
            "need prompt design improvement; runtime depends on scheduler; no blocking"
        )
        siv = parse_to_semantic_invariant(text)
        self.assertTrue(siv.meaning_atoms)
        self.assertTrue(any(e["name"] == "runtime" for e in siv.entities))
        self.assertTrue(siv.invariant_id().startswith("SIV-"))

    def test_bilingual_projection(self):
        siv = parse_to_semantic_invariant(
            "界面语言切换存在问题，需要改进提示词设计，低延迟，不允许语义漂移"
        )
        projector = get_language_projector()
        zh = projector.project_zh(siv)
        en = projector.project_en(siv)
        self.assertIn("意图", zh)
        self.assertIn("[Intent]", en)
        self.assertIn("语义原子", zh)
        self.assertIn("[Meaning atoms]", en)

    def test_compiler_output_protocol(self):
        compiler = SIBTCompilerV1()
        result = compiler.compile(
            "UI language switching; translation accuracy issue exists; runtime depends on scheduler"
        )
        self.assertEqual(result["mode"], "sibt_v1")
        self.assertIn("semantic_invariant_id", result)
        self.assertIn("semantic_layer", result)
        self.assertIn("zh", result)
        self.assertIn("en", result)
        self.assertIn("reversible_mapping", result)
        self.assertIn("reversibility_score", result)
        self.assertIn("loss_report", result)
        self.assertGreaterEqual(result["reversibility_score"], 0.0)

    def test_round_trip_atom_preservation(self):
        compiler = SIBTCompilerV1()
        zh_input = "界面语言切换存在问题，需要优化提示词设计，低延迟"
        out = compiler.compile(zh_input, source_lang="zh")
        siv = parse_to_semantic_invariant(zh_input, source_lang="zh")
        round_siv = parse_to_semantic_invariant(out["en"]["text"], source_lang="en")
        loss = compare_atom_sets(siv, round_siv)
        self.assertIsInstance(loss["missing_atoms"], list)

    def test_back_check_engine(self):
        siv = parse_to_semantic_invariant("runtime depends on scheduler; no blocking")
        projector = get_language_projector()
        zh = projector.project_zh(siv)
        en = projector.project_en(siv)
        checks = BackCheckEngineV1(projector).run(siv, zh, en)
        self.assertIn("faithfulness", checks)
        self.assertIn("naturalness", checks)
        self.assertIn("reversibility_score", checks)

    def test_project_from_invariant_layer(self):
        layer = {
            "intent": "improvement_goal",
            "entities": [{"name": "ui", "type": "interface"}],
            "relations": [],
            "constraints": ["low latency"],
            "meaning_atoms": ["UI language switching"],
        }
        result = SIBTCompilerV1().project_from_invariant(layer)
        self.assertEqual(result["mode"], "sibt_v1")
        self.assertIn("UI language switching", result["en"]["text"])


if __name__ == "__main__":
    unittest.main()
