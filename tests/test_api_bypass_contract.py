"""Contract: API layers must not bypass AuthorityDispatcher for writes."""

from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BYPASS_PATTERNS = [
    r"get_runtime\(\)\.process_interaction\s*\(",
    r"get_runtime\(\)\.run_governance_cycle\s*\(",
    r"get_runtime\(\)\.recall\s*\(",
    r"runtime\.capture\s*\(",
    r"runtime\.recall\s*\(",
    r"runtime\.run_governance_cycle\s*\(",
]

SCAN_FILES = [
    os.path.join(ROOT, "api", "server.py"),
    os.path.join(ROOT, "api", "v1_endpoints.py"),
    os.path.join(ROOT, "api", "ws_routes.py"),
    os.path.join(ROOT, "core", "openai_compat", "handler.py"),
    os.path.join(ROOT, "brain-memory-ui", "api", "routes", "openai_compatible.py"),
]


class TestApiBypassContract(unittest.TestCase):
    def test_write_endpoints_have_no_direct_runtime_bypass(self):
        for path in SCAN_FILES:
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            for pattern in BYPASS_PATTERNS:
                match = re.search(pattern, source)
                if match is None:
                    continue
                if path.endswith("handler.py") and pattern.startswith(r"runtime\.process_interaction"):
                    if "legacy_adapter is not None" in source:
                        continue
                if path.endswith("ws_routes.py") and pattern.startswith(r"runtime\.process_interaction"):
                    self.fail(
                        f"{os.path.basename(path)} must not call runtime.process_interaction directly"
                    )
                self.fail(
                    f"{os.path.basename(path)} still has bypass {pattern!r}: {match.group(0)}"
                )

    def test_v1_and_server_use_legacy_adapter(self):
        for name in ("server.py", "v1_endpoints.py"):
            with open(os.path.join(ROOT, "api", name), encoding="utf-8") as fh:
                source = fh.read()
            self.assertIn("get_legacy_adapter", source)


if __name__ == "__main__":
    unittest.main()
