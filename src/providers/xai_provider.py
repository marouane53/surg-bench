from __future__ import annotations
import os, time
from typing import Any, Dict, List, Tuple, Optional
from openai import OpenAI
from .base import Provider

class XAIProvider(Provider):
    name = "xai"
    def __init__(self, model: str, base_url: Optional[str] = None):
        super().__init__(model)
        base = base_url or os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
        self.client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url=base)

    def supports_images(self) -> bool:
        # OpenAI client compatibility may support images, but Grok support varies
        return False

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        # strip images for safety
        clean = []
        for m in messages:
            c = m["content"]
            if isinstance(c, list):
                c = [p for p in c if p.get("type") == "text"]
                c = c[0]["text"] if c else ""
            clean.append({"role": m["role"], "content": c})
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=clean,
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 500)
        )
        return resp.choices[0].message.content or "", int((time.time()-start)*1000)
