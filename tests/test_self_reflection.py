"""Tests for metacognitive self-reflection."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.audit_log import AuditLog  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402
from core.self_reflection import SelfReflectionEngine  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "audit.log")
        key_path = os.path.join(tmp, "id.key")
        im = IdentityManager(key_path)
        audit = AuditLog(log_path)
        audited = []

        def audit_fn(event, data):
            audited.append(event)
            return audit.log(im, {"event": event, **data})

        engine = SelfReflectionEngine(audit, audit_fn=audit_fn)

        for i in range(8):
            audit.log(
                im,
                {
                    "event": "memory.block",
                    "block_id": f"code-{i}",
                    "label": "code_function",
                    "content_preview": f"auth handler module {i}",
                    "keywords": ["auth", "login"],
                },
            )
        audit.log(im, {"event": "trace.cycle", "trace_id": "t1", "iteration": 1, "input_preview": "how does consensus work"})
        audit.log(
            im,
            {"event": "asset.upload", "asset_id": "a" * 64, "type": "code", "filename": "auth.py", "summary": "login"},
        )

        report = engine.reflect(use_llm=False)
        assert report.get("ok"), report
        assert "领域倾斜" in report.get("reflection", "") or "code" in report.get("reflection", "").lower()
        assert report.get("analysis", {}).get("domain_counts", {}).get("code", 0) >= 8
        assert "reflection.meta" in audited

        status = engine.status()
        assert status.get("enabled") is True

        print("source:", report.get("source"))
        print("biases:", len(report.get("biases") or []))
        print("\nSELF REFLECTION TEST PASSED")


if __name__ == "__main__":
    main()
