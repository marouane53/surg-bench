from __future__ import annotations
import os, time, base64
from typing import Any, Dict, List, Tuple
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
from .base import Provider

class GeminiProvider(Provider):
    name = "gemini"
    def __init__(self, model: str):
        super().__init__(model)
        if genai is None:
            raise ImportError("google-genai package required for GeminiProvider")
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def supports_images(self) -> bool:
        return True

    def _to_contents(self, messages: List[Dict[str, Any]]) -> List[types.Content]:
        # collapse system into prompt prefix, then user content with inline images
        sys = ""
        for m in messages:
            if m["role"] == "system":
                sys = m["content"]
        user = next((m for m in messages if m["role"] == "user"), None)
        parts = []
        if isinstance(user["content"], list):  # parts with images
            for part in user["content"]:
                if part.get("type") == "text":
                    txt = part["text"]
                    if sys:
                        txt = sys + "\n\n" + txt
                        sys = ""
                    parts.append(types.Part.from_text(txt))
                elif part.get("type") == "image_url":
                    url = part["image_url"]["url"]
                    if url.startswith("data:image"):
                        # inline base64
                        header, b64 = url.split(",", 1)
                        mime = header.split(";")[0].split(":")[1]
                        parts.append(types.Part.from_inline_data(data=base64.b64decode(b64), mime_type=mime))
                    else:
                        parts.append(types.Part.from_uri_file(url))
        else:
            txt = (sys + "\n\n" if sys else "") + str(user["content"])
            parts = [types.Part.from_text(txt)]
        return [types.Content(role="user", parts=parts)]

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        contents = self._to_contents(messages)
        resp = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(temperature=kwargs.get("temperature", 0.2))
        )
        text = resp.text or ""
        return text, int((time.time()-start)*1000)
