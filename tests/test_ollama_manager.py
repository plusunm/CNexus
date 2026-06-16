import unittest
from unittest.mock import ANY, MagicMock, patch

from core.ollama_manager import start_ollama


class TestOllamaManagerStart(unittest.TestCase):
    @patch("core.ollama_manager.time.sleep", return_value=None)
    @patch("core.ollama_manager.subprocess.Popen")
    @patch("core.ollama_manager.find_ollama_binary", return_value=r"C:\Ollama\ollama.exe")
    @patch("core.ollama_manager.is_ollama_running", side_effect=[False, True])
    def test_windows_starts_serve_headless(self, _running, _find, popen_mock, _sleep):
        popen_mock.return_value = MagicMock()
        out = start_ollama()

        self.assertTrue(out["ok"])
        popen_mock.assert_called_once()
        args, kwargs = popen_mock.call_args
        self.assertEqual(args[0], [r"C:\Ollama\ollama.exe", "serve"])
        self.assertIn("creationflags", kwargs)
        self.assertEqual(kwargs["stdout"], ANY)

    @patch("core.ollama_manager.is_ollama_running", return_value=True)
    def test_already_running_short_circuits(self, _running):
        out = start_ollama()
        self.assertEqual(out["detail"], "already_running")


if __name__ == "__main__":
    unittest.main()
