import os
import sys
import threading
from pathlib import Path
from typing import Optional

# Resolve brain-memory core on PYTHONPATH
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("BRAIN_MEMORY_ROOT", str(ROOT))
os.environ.setdefault(
    "BM_MEMORY_DIR",
    str(Path(os.environ.get("ProgramData", "C:/ProgramData")) / "brain-memory-g1" / "data"),
)

from brain_memory import BrainMemoryRuntime
from core.llm_client import LLMClient
from core.model_registry import ModelRegistry

_runtime: Optional[BrainMemoryRuntime] = None
_registry: Optional[ModelRegistry] = None
_llm = LLMClient()
_runtime_lock = threading.Lock()


def get_runtime() -> BrainMemoryRuntime:
    global _runtime
    if _runtime is None:
        with _runtime_lock:
            if _runtime is None:
                _runtime = BrainMemoryRuntime(project_root=str(ROOT))
    return _runtime


def get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        with _runtime_lock:
            if _registry is None:
                _registry = ModelRegistry(str(ROOT / "config"))
    return _registry


def get_llm() -> LLMClient:
    return _llm
