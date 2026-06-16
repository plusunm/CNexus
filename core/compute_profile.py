"""ComputeProfile — machine envelope detection for compute-adaptive CNexus."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal, Optional

Locality = Literal["local", "hybrid", "cloud"]
StorageType = Literal["ssd", "hdd"]
ProfileSource = Literal["detected", "override", "env", "fallback"]

# Safe default envelope when hardware cannot be probed — not a system ceiling.
SAFE_BASELINE_RAM_GB = 16.0


@dataclass
class ComputeProfile:
    ram_gb: float
    cpu_cores: int
    gpu: bool
    gpu_vram_gb: Optional[float] = None
    storage_type: StorageType = "ssd"
    locality: Locality = "local"
    source: ProfileSource = "detected"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComputeProfile":
        return cls(
            ram_gb=float(data.get("ram_gb", SAFE_BASELINE_RAM_GB)),
            cpu_cores=int(data.get("cpu_cores") or 1),
            gpu=bool(data.get("gpu")),
            gpu_vram_gb=(
                float(data["gpu_vram_gb"])
                if data.get("gpu_vram_gb") is not None
                else None
            ),
            storage_type=str(data.get("storage_type") or "ssd"),  # type: ignore[arg-type]
            locality=str(data.get("locality") or "local"),  # type: ignore[arg-type]
            source=str(data.get("source") or "override"),  # type: ignore[arg-type]
        )

    def compute_score(self) -> float:
        """Rough relative score for policy tier selection."""
        score = self.ram_gb + self.cpu_cores * 0.5
        if self.gpu:
            score += (self.gpu_vram_gb or 4.0) * 2.0
        if self.storage_type == "hdd":
            score *= 0.85
        return score


def _detect_ram_gb() -> float:
    try:
        if sys.platform == "win32":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return round(stat.ullTotalPhys / (1024**3), 2)
        elif sys.platform == "darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True, timeout=2)
            return round(int(out.strip()) / (1024**3), 2)
        else:
            with open("/proc/meminfo", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024**2), 2)
    except Exception:
        pass
    return SAFE_BASELINE_RAM_GB


def _detect_cpu_cores() -> int:
    count = os.cpu_count() or 1
    return max(1, int(count))


def _detect_gpu() -> tuple[bool, Optional[float]]:
    env_flag = os.environ.get("CNEXUS_GPU", "").strip().lower()
    if env_flag in ("1", "true", "yes"):
        vram_env = os.environ.get("CNEXUS_GPU_VRAM_GB", "").strip()
        vram = float(vram_env) if vram_env else 8.0
        return True, vram
    if env_flag in ("0", "false", "no"):
        return False, None

    try:
        from core.windows_subprocess import check_output_hidden

        out = check_output_hidden(
            [
                "nvidia-smi",
                "--query-gpu=memory.total",
                "--format=csv,noheader,nounits",
            ],
            timeout=2,
        )
        line = out.strip().splitlines()[0]
        mib = float(line.strip())
        return True, round(mib / 1024, 2)
    except Exception:
        return False, None


def _detect_storage_type() -> StorageType:
    env = os.environ.get("CNEXUS_STORAGE_TYPE", "").strip().lower()
    if env in ("ssd", "hdd"):
        return env  # type: ignore[return-value]
    return "ssd"


def _detect_locality(cfg: Dict[str, Any]) -> Locality:
    env = os.environ.get("CNEXUS_LOCALITY", "").strip().lower()
    if env in ("local", "hybrid", "cloud"):
        return env  # type: ignore[return-value]
    compute_cfg = cfg.get("compute") or {}
    loc = str(compute_cfg.get("locality") or "local").lower()
    if loc in ("local", "hybrid", "cloud"):
        return loc  # type: ignore[return-value]
    return "local"


def detect_compute_profile(cfg: Optional[Dict[str, Any]] = None) -> ComputeProfile:
    cfg = cfg or {}
    gpu, vram = _detect_gpu()
    profile = ComputeProfile(
        ram_gb=_detect_ram_gb(),
        cpu_cores=_detect_cpu_cores(),
        gpu=gpu,
        gpu_vram_gb=vram,
        storage_type=_detect_storage_type(),
        locality=_detect_locality(cfg),
        source="detected",
    )
    if profile.ram_gb <= 0:
        profile.ram_gb = SAFE_BASELINE_RAM_GB
        profile.source = "fallback"
    return profile


def _parse_override_json(raw: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def resolve_compute_profile(cfg: Dict[str, Any]) -> ComputeProfile:
    """
    Resolve effective compute profile:
    1. CNEXUS_COMPUTE_PROFILE JSON env
    2. config.compute.override
    3. auto-detect (+ safe baseline fallback)
    """
    compute_cfg = cfg.get("compute") or {}
    mode = str(compute_cfg.get("mode") or "auto").lower()

    env_raw = os.environ.get("CNEXUS_COMPUTE_PROFILE", "").strip()
    if env_raw:
        merged = _parse_override_json(env_raw)
        base = detect_compute_profile(cfg)
        profile = ComputeProfile.from_dict({**base.to_dict(), **merged})
        profile.source = "env"
        return profile

    override = compute_cfg.get("override")
    if isinstance(override, dict) and override:
        base = detect_compute_profile(cfg)
        profile = ComputeProfile.from_dict({**base.to_dict(), **override})
        profile.source = "override"
        return profile

    if mode == "override" and isinstance(override, dict):
        profile = ComputeProfile.from_dict(override)
        profile.source = "override"
        return profile

    profile = detect_compute_profile(cfg)
    safe_ram = float(compute_cfg.get("safe_baseline_ram_gb", SAFE_BASELINE_RAM_GB))
    if profile.source == "fallback":
        profile.ram_gb = safe_ram
    return profile
