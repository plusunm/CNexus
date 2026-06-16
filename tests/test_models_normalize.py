import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BMUI = os.path.join(ROOT, "brain-memory-ui")
sys.path.insert(0, BMUI)
sys.path.insert(0, ROOT)

from api.routes.models import _normalize_base_url


class TestModelsNormalize(unittest.TestCase):
    def test_ollama_keeps_http_localhost(self):
        url = _normalize_base_url("http://localhost:11434", provider="ollama")
        self.assertEqual(url, "http://localhost:11434")

    def test_deepseek_strips_trailing_v1(self):
        url = _normalize_base_url("https://api.deepseek.com/v1", provider="openai_compatible")
        self.assertEqual(url, "https://api.deepseek.com")

    def test_openai_upgrades_http_to_https(self):
        url = _normalize_base_url("http://api.openai.com/v1", provider="openai")
        self.assertTrue(url.startswith("https://"))


if __name__ == "__main__":
    unittest.main()
