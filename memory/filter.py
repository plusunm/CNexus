from __future__ import annotations

import math
from enum import Enum
from typing import Tuple


class CaptureMode(str, Enum):
    UNSPECIFIED = "unspecified"
    CHAT = "chat"
    INGEST = "ingest"
    SYSTEM = "system"
    RAW = "raw"


# Source → CaptureMode mapping (mirrors dispatch's SOURCE_MODE_MAP for cross-check)
SOURCE_MODE_MAP = {
    "chat": CaptureMode.CHAT,
    "ingest": CaptureMode.INGEST,
    "system": CaptureMode.SYSTEM,
    "import": CaptureMode.INGEST,
    "api": CaptureMode.CHAT,
    "replay": CaptureMode.RAW,
    "agent": CaptureMode.SYSTEM,
}


class CaptureFilter:
    ROLE_BLOCKLIST = {"toolResult", "tool_error", "system", "debug"}
    MAX_JSON_RATIO = 0.45
    MIN_LEN = 12
    MAX_LEN = 8000
    ENTROPY_THRESHOLD = 6.2

    @staticmethod
    def should_reject(
        role: str,
        content: str,
        mode: CaptureMode | None = None,
    ) -> Tuple[bool, str]:
        effective = mode if mode is not None else CaptureMode.INGEST
        if effective == CaptureMode.UNSPECIFIED:
            raise RuntimeError("CaptureMode must be explicitly set")

        if role in CaptureFilter.ROLE_BLOCKLIST:
            return True, f"blocklisted role: {role}"

        if effective == CaptureMode.RAW:
            return False, ""

        if effective == CaptureMode.CHAT and len(content) < CaptureFilter.MIN_LEN:
            return True, "too short"

        content = content[: CaptureFilter.MAX_LEN]

        json_ratio = sum(1 for c in content if c in '{}[]":,') / max(len(content), 1)
        if json_ratio > CaptureFilter.MAX_JSON_RATIO and effective == CaptureMode.CHAT:
            return True, "high json ratio"

        if effective == CaptureMode.CHAT:
            freq: dict[str, int] = {}
            for c in content:
                freq[c] = freq.get(c, 0) + 1
            entropy = -sum(
                (count / len(content)) * math.log2(count / len(content))
                for count in freq.values()
                if count > 0
            )
            if entropy > CaptureFilter.ENTROPY_THRESHOLD:
                return True, f"high entropy: {entropy:.2f}"

        return False, ""

    @staticmethod
    def check_mode_consistency(source: str, mode: CaptureMode) -> None:
        """Cross-check that source and mode are consistent."""
        expected = SOURCE_MODE_MAP.get(source)
        if expected is not None and expected != mode:
            raise RuntimeError(
                f"CaptureMode mismatch: source={source} mode={mode.value} expected={expected.value}"
            )
