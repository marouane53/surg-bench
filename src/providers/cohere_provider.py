from __future__ import annotations
import os, time
from typing import Any, Dict, List, Tuple
try:
    import cohere
except ImportError:
    cohere = None
from .base import Provider

class CohereProvider(Provider):
    name = "cohere"
    def __init__(self, model: str):
        super().__init__(model)
        if cohere is None:
            raise ImportError("cohere package required for CohereProvider")
        self.client = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

    def supports_images(self) -> bool:
        return False

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        sys = ""
        content = ""
        for m in messages:
            if m["role"] == "system":
                sys = m["content"]
            elif m["role"] == "user":
                if isinstance(m["content"], list):
                    content = next((p["text"] for p in m["content"] if p["type"]=="text"), "")
                else:
                    content = m["content"]
        msgs = []
        if sys:
            msgs.append({"role": "system", "content": sys})
        msgs.append({"role": "user", "content": content})
        res = self.client.chat(model=self.model, messages=msgs)
        text = res.message.content[0].text if res and res.message and res.message.content else ""
        return text, int((time.time()-start)*1000)
