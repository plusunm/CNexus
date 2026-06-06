import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory import create_runtime
from core.self_model import SelfModel, SelfModelStore
from runtime.predictive_loop import PredictiveSelf
from runtime.cognitive_state import PersistentCognitiveState


class TestUnifiedSelfModel(unittest.TestCase):
    def test_integrate_experience_unified_entry(self):
        model = SelfModel()
        report = model.integrate_experience(
            "讨论长期身份稳定与人格 runtime",
            "我会维护连续性",
            reflection="强化主体连续性",
        )
        self.assertIn("identity_summary", report)
        self.assertGreater(model.total_experiences, 0)
        self.assertIn("主体连续性", model.core_beliefs)

    def test_autobiographical_compression(self):
        model = SelfModel()
        before = model.autobiographical_story
        model.integrate_experience("稳定连续", "ok", reflection="r")
        self.assertNotEqual(before, model.autobiographical_story)
        self.assertLessEqual(len(model.autobiographical_story), 1200)

    def test_belief_cap(self):
        model = SelfModel()
        for _ in range(30):
            model.integrate_experience("稳定连续长期", "r", reflection="x")
        self.assertLessEqual(model.core_beliefs["稳定性优先"], 0.98)

    def test_store_persistence(self):
        tmp = tempfile.mkdtemp()
        store = SelfModelStore(tmp)
        store.integrate("测试经历", "测试响应", reflection="测试反思")
        store2 = SelfModelStore(tmp)
        self.assertGreater(store2.model.total_experiences, 0)
        self.assertIn("测试反思", store2.model.autobiographical_story)

    def test_predictive_self_correction(self):
        pred = PredictiveSelf()
        state = PersistentCognitiveState(identity_threat=0.7)
        model = SelfModel()
        error = pred.predict_and_update("你完全变了，不像之前", "response", state, model)
        self.assertGreater(error, 0.4)
        self.assertGreater(pred.correction_count, 0)

    def test_process_interaction_centers_on_self_model(self):
        tmp = tempfile.mkdtemp()
        rt = create_runtime(project_root=tmp, base_dir="memory")
        result = rt.process_interaction(
            "我的长期目标是维护身份连续性",
            assistant_output="我会持续维护你的身份连续性。",
        )
        self.assertTrue(result["ok"])
        self.assertIn("integration", result)
        self.assertIn("self_model", result)
        self.assertGreater(result["self_model"]["total_experiences"], 0)


if __name__ == "__main__":
    unittest.main()
