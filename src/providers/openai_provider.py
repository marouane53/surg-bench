from __future__ import annotations
import os, time
from typing import Any, Dict, List, Tuple, Optional
from openai import OpenAI
from .base import Provider

class OpenAIProvider(Provider):
    name = "openai"
    def __init__(self, model: str, base_url: Optional[str] = None, api_key: Optional[str] = None):
        super().__init__(model)
        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), **kwargs)

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 500)
        )
        text = resp.choices[0].message.content or ""
        return text, int((time.time()-start)*1000)
