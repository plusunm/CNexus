import math
from enum import Enum
from typing import Tuple


class CaptureMode(str, Enum):
    UNSPECIFIED = "unspecified"
    CHAT = "chat"
    INGEST = "ingest"
    SYSTEM = "system"
    RAW = "raw"


class CaptureFilter:
    ROLE_BLOCKLIST = {"toolResult", "tool_error", "system", "debug"}
    MAX_JSON_RATIO = 0.45
    MIN_LEN = 12
    MAX_LEN = 8000
    ENTROPY_THRESHOLD = 6.2

    @staticmethod
    def should_reject(role: str, content: str, mode: CaptureMode | None = None) -> Tuple[bool, str]:
        if role in CaptureFilter.ROLE_BLOCKLIST:
            return True, f"blocklisted role: {role}"
        if len(content) < CaptureFilter.MIN_LEN:
            return True, "too short"

        content = content[: CaptureFilter.MAX_LEN]
        json_ratio = sum(1 for c in content if c in '{}[]":,') / max(len(content), 1)
        if json_ratio > CaptureFilter.MAX_JSON_RATIO:
            return True, "high json ratio"

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
