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

    def _is_gemini_3(self) -> bool:
        return str(self.model).startswith("gemini-3")

    def supports_images(self) -> bool:
        return True

    def _split_messages(self, messages: List[Dict[str, Any]]) -> Tuple[str, List[types.Content]]:
        """Return (system_instruction, contents[]) using the official SDK types."""
        sys = ""
        for m in messages:
            if m.get("role") == "system":
                sys = str(m.get("content") or "")
                break
        user = next((m for m in messages if m.get("role") == "user"), None)
        parts = []
        if user:
            if isinstance(user.get("content"), list):  # parts with images
                for part in user["content"]:
                    if part.get("type") == "text":
                        parts.append(types.Part.from_text(part.get("text", "")))
                    elif part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url") if isinstance(part.get("image_url"), dict) else part.get("image_url")
                        if isinstance(url, str) and url.startswith("data:image"):
                            # inline base64
                            header, b64 = url.split(",", 1)
                            mime = header.split(";")[0].split(":")[1]
                            parts.append(types.Part.from_bytes(data=base64.b64decode(b64), mime_type=mime))
                        elif isinstance(url, str):
                            parts.append(types.Part.from_uri_file(url))
            else:
                parts = [types.Part.from_text(str(user.get("content", "")))]
        return sys, [types.Content(role="user", parts=parts)]

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        system_instruction, contents = self._split_messages(messages)
        cfg_kwargs: Dict[str, Any] = {
            "system_instruction": [system_instruction] if system_instruction else None,
        }

        # Gemini 3 models recommend leaving temperature at the default (1.0) and
        # some endpoints may reject custom temperatures. For Gemini 2.5, we keep
        # a low default for more deterministic benchmark outputs.
        if not self._is_gemini_3():
            cfg_kwargs["temperature"] = kwargs.get("temperature", 0.2)

        # Optional Gemini "thinking" controls:
        # - Gemini 3 uses thinking_level (low/high)
        # - Gemini 2.5 uses thinking_budget (0 disables thinking, 1024+ enables)
        thinking_cfg = None
        ThinkingConfig = getattr(types, "ThinkingConfig", None)
        if ThinkingConfig is not None:
            if self._is_gemini_3():
                thinking_level = kwargs.get("thinking_level")
                if thinking_level:
                    thinking_cfg = ThinkingConfig(thinking_level=str(thinking_level).lower())
            else:
                thinking_budget = kwargs.get("thinking_budget")
                if thinking_budget is not None:
                    thinking_cfg = ThinkingConfig(thinking_budget=int(thinking_budget))

        if thinking_cfg is not None:
            cfg_kwargs["thinking_config"] = thinking_cfg

        try:
            cfg = types.GenerateContentConfig(**cfg_kwargs)
        except TypeError:
            # Older google-genai versions may not support thinking_config.
            cfg_kwargs.pop("thinking_config", None)
            cfg = types.GenerateContentConfig(**cfg_kwargs)
        resp = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=cfg
        )
        text = resp.text or ""
        return text, int((time.time()-start)*1000)
