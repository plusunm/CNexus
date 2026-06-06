import json
import uuid
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


ProviderType = Literal["ollama", "openai", "openai_compatible"]


class ModelProfile(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    provider: ProviderType = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    is_default: bool = False
    enabled: bool = True


class ModelProfilePublic(BaseModel):
    id: str
    name: str
    provider: ProviderType
    base_url: str
    model: str
    api_key_set: bool
    is_default: bool
    enabled: bool


def _mask_key(key: str) -> bool:
    return bool(key and key.strip())


def to_public(profile: ModelProfile) -> ModelProfilePublic:
    return ModelProfilePublic(
        id=profile.id,
        name=profile.name,
        provider=profile.provider,
        base_url=profile.base_url,
        model=profile.model,
        api_key_set=_mask_key(profile.api_key),
        is_default=profile.is_default,
        enabled=profile.enabled,
    )


DEFAULT_MODELS = [
    ModelProfile(
        id="ollama-local",
        name="Ollama 本地",
        provider="ollama",
        base_url="http://localhost:11434",
        api_key="",
        model="llama3.2",
        is_default=True,
    ),
    ModelProfile(
        id="openai-default",
        name="OpenAI GPT-4o mini",
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="",
        model="gpt-4o-mini",
    ),
    ModelProfile(
        id="deepseek-chat",
        name="DeepSeek Chat",
        provider="openai_compatible",
        base_url="https://api.deepseek.com/v1",
        api_key="",
        model="deepseek-chat",
    ),
    ModelProfile(
        id="moonshot-kimi",
        name="Moonshot Kimi",
        provider="openai_compatible",
        base_url="https://api.moonshot.cn/v1",
        api_key="",
        model="moonshot-v1-8k",
    ),
    ModelProfile(
        id="qwen-turbo",
        name="通义千问 Qwen",
        provider="openai_compatible",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="",
        model="qwen-turbo",
    ),
    ModelProfile(
        id="zhipu-glm4",
        name="智谱 GLM-4",
        provider="openai_compatible",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key="",
        model="glm-4-flash",
    ),
    ModelProfile(
        id="siliconflow-deepseek",
        name="SiliconFlow DeepSeek",
        provider="openai_compatible",
        base_url="https://api.siliconflow.cn/v1",
        api_key="",
        model="deepseek-ai/DeepSeek-V3",
    ),
    ModelProfile(
        id="google-gemini",
        name="Google Gemini",
        provider="openai_compatible",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key="",
        model="gemini-2.0-flash",
    ),
]


class ModelRegistry:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.local_file = self.config_dir / "models.local.json"
        self.models: List[ModelProfile] = []
        self.load()

    def load(self):
        if self.local_file.exists():
            with open(self.local_file, encoding="utf-8") as f:
                data = json.load(f)
            self.models = [ModelProfile(**m) for m in data.get("models", [])]
            self._merge_missing_defaults()
        else:
            self.models = [m.model_copy() for m in DEFAULT_MODELS]
            self.save()

    def _merge_missing_defaults(self):
        """Append new built-in presets without overwriting user config."""
        existing_ids = {m.id for m in self.models}
        added = False
        for preset in DEFAULT_MODELS:
            if preset.id not in existing_ids:
                self.models.append(preset.model_copy())
                added = True
        if added:
            self.save()

    def save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.local_file, "w", encoding="utf-8") as f:
            json.dump({"models": [m.model_dump() for m in self.models]}, f, indent=2, ensure_ascii=False)

    def list_public(self) -> List[ModelProfilePublic]:
        return [to_public(m) for m in self.models if m.enabled]

    def get(self, model_id: str) -> Optional[ModelProfile]:
        for m in self.models:
            if m.id == model_id:
                return m
        return None

    def get_default(self) -> Optional[ModelProfile]:
        for m in self.models:
            if m.is_default and m.enabled:
                return m
        enabled = [m for m in self.models if m.enabled]
        return enabled[0] if enabled else None

    def add(self, profile: ModelProfile) -> ModelProfile:
        if profile.is_default:
            for m in self.models:
                m.is_default = False
        self.models.append(profile)
        self.save()
        return profile

    def update(self, model_id: str, updates: dict) -> Optional[ModelProfile]:
        for i, m in enumerate(self.models):
            if m.id != model_id:
                continue
            data = m.model_dump()
            if updates.get("api_key") in ("", None) and not updates.get("api_key_set"):
                updates.pop("api_key", None)
            data.update({k: v for k, v in updates.items() if k != "api_key_set"})
            if updates.get("is_default"):
                for other in self.models:
                    other.is_default = False
            self.models[i] = ModelProfile(**data)
            self.save()
            return self.models[i]
        return None

    def delete(self, model_id: str) -> bool:
        before = len(self.models)
        self.models = [m for m in self.models if m.id != model_id]
        if len(self.models) < before:
            if not any(m.is_default for m in self.models) and self.models:
                self.models[0].is_default = True
            self.save()
            return True
        return False
