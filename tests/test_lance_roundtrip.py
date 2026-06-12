import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.schema import Memory
from storage.vector import LanceMemoryStore


class TestLanceRoundtrip(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.store = LanceMemoryStore(db_path=os.path.join(self._tmpdir, "lancedb"))

    def test_insert_search_restart(self):
        content = "Lance roundtrip integration test content for recall"
        mem = Memory(
            memory_id=str(uuid.uuid4()),
            role="user",
            content=content,
            layer="episodic",
            importance=0.7,
            timestamp=datetime.now(),
            embedding=[0.1] * 768,
        )
        mid = self.store.insert_memory(mem)
        self.assertEqual(mid, mem.memory_id)

        store2 = LanceMemoryStore(db_path=os.path.join(self._tmpdir, "lancedb"))
        hits = store2.search_memory([0.1] * 768, top_k=5)
        self.assertGreaterEqual(len(hits), 1)
        self.assertIn(content[:20], hits[0].get("content", ""))


if __name__ == "__main__":
    unittest.main()
