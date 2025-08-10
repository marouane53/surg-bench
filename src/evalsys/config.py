from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import yaml

class ProviderConfig(BaseModel):
    enabled: bool = True
    base_url: Optional[str] = None
    models: List[str] = Field(default_factory=list)

class AppConfig(BaseModel):
    openai: ProviderConfig = ProviderConfig()
    gemini: ProviderConfig = ProviderConfig()
    anthropic: ProviderConfig = ProviderConfig()
    groq: ProviderConfig = ProviderConfig()
    xai: ProviderConfig = ProviderConfig()
    openrouter: ProviderConfig = ProviderConfig()
    mistral: ProviderConfig = ProviderConfig(enabled=False)
    cohere: ProviderConfig = ProviderConfig(enabled=False)

def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        if value.startswith("${") and value.endswith("}"):
            inner = value[2:-1]
            if ":" in inner:
                env, default = inner.split(":", 1)
                return os.getenv(env, default)
            return os.getenv(inner, "")
        return value
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(x) for x in value]
    return value

def load_config(path: str = "providers.yaml") -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data = _expand_env(data)
    return AppConfig(**data)
