from __future__ import annotations
import os, time
from typing import Any, Dict, List, Tuple
from openai import OpenAI
from .base import Provider

class OpenRouterProvider(Provider):
    name = "openrouter"
    def __init__(self, model: str):
        super().__init__(model)
        base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.client = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url=base)

    def supports_images(self) -> bool:
        # depends on routed model, we keep images
        return True

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        # Respect explicit override; else env; else 8192 default
        try:
            max_tok = int(kwargs.get("max_tokens")) if kwargs.get("max_tokens") is not None else None
        except Exception:
            max_tok = None
        if not isinstance(max_tok, int) or max_tok <= 0:
            try:
                max_tok = int(os.getenv("OPENROUTER_MAX_TOKENS", "8192"))
            except Exception:
                max_tok = 8192

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=max_tok,
        )
        return resp.choices[0].message.content or "", int((time.time()-start)*1000)
