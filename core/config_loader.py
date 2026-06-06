import json
import os
from pathlib import Path
from typing import Any, Dict


class ConfigLoader:
    def __init__(self, base_path: str = "config"):
        self.base_path = Path(base_path)
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        default_file = self.base_path / "default.json"
        if default_file.exists():
            with open(default_file, encoding="utf-8") as f:
                self.config = json.load(f)

        for key in list(self.config.keys()):
            env_key = f"BRAIN_MEMORY_{key.upper()}"
            if env_key in os.environ:
                val = os.environ[env_key]
                if isinstance(self.config[key], bool):
                    self.config[key] = val.lower() in ("true", "1", "yes")
                elif isinstance(self.config[key], (int, float)):
                    self.config[key] = type(self.config[key])(val)
                else:
                    self.config[key] = val
        return self.config

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def save(self):
        pass
