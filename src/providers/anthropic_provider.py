from __future__ import annotations
import os, time, base64
from typing import Any, Dict, List, Tuple, Optional
try:
    import anthropic
except ImportError:
    anthropic = None
from .base import Provider

class AnthropicProvider(Provider):
    name = "anthropic"
    def __init__(self, model: str):
        super().__init__(model)
        if anthropic is None:
            raise ImportError("anthropic package required for AnthropicProvider")
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def supports_images(self) -> bool:
        return True

    def _to_blocks(self, messages: List[Dict[str, Any]]):
        sys = ""
        for m in messages:
            if m["role"] == "system":
                sys = m["content"]
        user = next((m for m in messages if m["role"] == "user"), None)
        blocks = []
        if isinstance(user["content"], list):
            for part in user["content"]:
                if part.get("type") == "text":
                    txt = (sys + "\n\n" if sys else "") + part["text"]
                    sys = ""
                    blocks.append({"type": "text", "text": txt})
                elif part.get("type") == "image_url":
                    url = part["image_url"]["url"]
                    header, b64 = url.split(",", 1)
                    mime = header.split(";")[0].split(":")[1]
                    blocks.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}})
        else:
            txt = (sys + "\n\n" if sys else "") + str(user["content"])
            blocks.append({"type": "text", "text": txt})
        return blocks

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        blocks = self._to_blocks(messages)

        # Determine output token budget with generous default
        try:
            max_tok = int(kwargs.get("max_tokens")) if kwargs.get("max_tokens") is not None else None
        except Exception:
            max_tok = None
        if not isinstance(max_tok, int) or max_tok <= 0:
            try:
                max_tok = int(os.getenv("ANTHROPIC_MAX_TOKENS", "8192"))
            except Exception:
                max_tok = 8192

        # Optional Anthropic "thinking" (reasoning) config
        thinking_cfg: Optional[Dict[str, Any]] = kwargs.get("thinking")
        if thinking_cfg is None:
            # Allow enabling via env var, e.g., ANTHROPIC_THINKING_BUDGET_TOKENS=16000
            env_budget = os.getenv("ANTHROPIC_THINKING_BUDGET_TOKENS")
            if env_budget:
                try:
                    thinking_cfg = {"type": "enabled", "budget_tokens": int(env_budget)}
                except Exception:
                    thinking_cfg = None

        params: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tok,
            "messages": [{"role": "user", "content": blocks}],
            "temperature": kwargs.get("temperature", 0.2),
        }
        if thinking_cfg:
            params["thinking"] = thinking_cfg

        resp = self.client.messages.create(**params)
        # content is a list of items with text
        text = "".join([c.text for c in resp.content if getattr(c, "type", "") == "text"])
        return text, int((time.time()-start)*1000)
