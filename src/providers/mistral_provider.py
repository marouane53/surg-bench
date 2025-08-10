from __future__ import annotations
import os, time
from typing import Any, Dict, List, Tuple
try:
    from mistralai import Mistral
except ImportError:
    Mistral = None
from .base import Provider

class MistralProvider(Provider):
    name = "mistral"
    def __init__(self, model: str):
        super().__init__(model)
        if Mistral is None:
            raise ImportError("mistralai package required for MistralProvider")
        self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

    def supports_images(self) -> bool:
        return False

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        clean = []
        for m in messages:
            c = m["content"]
            if isinstance(c, list):
                c = [p for p in c if p.get("type") == "text"]
                c = c[0]["text"] if c else ""
            clean.append({"role": m["role"], "content": c})
        res = self.client.chat.complete(model=self.model, messages=clean)
        text = "".join([c.delta or c.message.get("content", "") for c in getattr(res, "choices", [])]) or getattr(res, "output_text", "")
        return text or str(res), int((time.time()-start)*1000)
