# -*- coding: utf-8 -*-
"""定时巩固入口 — Windows 任务计划程序调用"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if os.environ.get("OLLAMA_MODELS"):
    pass  # 用户可在任务计划中设置

from memory_backend import BrainMemoryBackend

if __name__ == "__main__":
    brain = BrainMemoryBackend()
    result = brain.consolidate()
    print(result)
