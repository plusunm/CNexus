"""EmbeddingService must degrade when plane/scheduler are absent (contract tolerance)."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEmbeddingUnboundFallback(unittest.TestCase):
    def test_unbound_hash_embed_returns_vector(self):
        from core.embedding import EmbeddingService

        svc = EmbeddingService(fallback="hash", vector_dim=128)
        vec = svc.embed("contract break tolerance")
        self.assertEqual(len(vec), 128)

    def test_unbound_zero_fallback(self):
        from core.embedding import EmbeddingService

        svc = EmbeddingService(fallback="zero", vector_dim=64)
        self.assertEqual(svc.embed("x"), [0.0] * 64)

    def test_production_fail_loud_still_raises_when_unbound(self):
        from core.embedding import EmbeddingService

        prev = os.environ.get("CNEXUS_ENV")
        os.environ["CNEXUS_ENV"] = "production"
        try:
            with self.assertRaises(ValueError):
                EmbeddingService(fail_loud_in_production=True)
        finally:
            if prev is None:
                os.environ.pop("CNEXUS_ENV", None)
            else:
                os.environ["CNEXUS_ENV"] = prev


if __name__ == "__main__":
    unittest.main()
