from __future__ import annotations
import os, time
from typing import Any, Dict, List, Tuple
try:
    from groq import Groq
except ImportError:
    Groq = None
from .base import Provider

class GroqProvider(Provider):
    name = "groq"
    def __init__(self, model: str):
        super().__init__(model)
        if Groq is None:
            raise ImportError("groq package required for GroqProvider")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def supports_images(self) -> bool:
        # most Groq chat models are text only
        return False

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        # strip images
        clean = []
        for m in messages:
            c = m["content"]
            if isinstance(c, list):
                c = [p for p in c if p.get("type") == "text"]
                if c:
                    c = c[0]["text"]
                else:
                    c = ""
            clean.append({"role": m["role"], "content": c})
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=clean,
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 500)
        )
        text = resp.choices[0].message.content or ""
        return text, int((time.time()-start)*1000)
