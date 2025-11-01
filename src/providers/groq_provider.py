from __future__ import annotations
import inspect
import os, time
from typing import Any, Dict, List, Tuple
try:
    from groq import Groq
except ImportError:
    Groq = None
from .base import Provider

VISION_MODELS = {
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
}


class GroqProvider(Provider):
    name = "groq"

    def __init__(self, model: str):
        super().__init__(model)
        if Groq is None:
            raise ImportError("groq package required for GroqProvider")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self._supports_images = self.model in VISION_MODELS
        create_sig = inspect.signature(self.client.chat.completions.create)
        self._max_token_param = "max_completion_tokens" if "max_completion_tokens" in create_sig.parameters else "max_tokens"

    def supports_images(self) -> bool:
        return self._supports_images

    def _convert_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        content = message.get("content", "")
        if isinstance(content, list):
            converted: List[Dict[str, Any]] = []
            for part in content:
                ptype = part.get("type")
                if ptype in {"text", "input_text"}:
                    text = part.get("text") or part.get("content") or ""
                    if text:
                        converted.append({"type": "text", "text": text})
                elif ptype == "image_url":
                    image_url = part.get("image_url")
                    url = None
                    if isinstance(image_url, dict):
                        url = image_url.get("url")
                    elif isinstance(image_url, str):
                        url = image_url
                    if url:
                        converted.append({"type": "image_url", "image_url": {"url": url}})
                elif ptype == "input_image":
                    # Convert old input_image format to standard image_url format
                    img_url = part.get("image_url")
                    if img_url:
                        if isinstance(img_url, str):
                            converted.append({"type": "image_url", "image_url": {"url": img_url}})
                        else:
                            converted.append({"type": "image_url", "image_url": img_url})
            if converted:
                return {"role": message.get("role", "user"), "content": converted}
            # fall back to plain text if list had no usable parts
            content = ""
        return {"role": message.get("role", "user"), "content": content}

    def _max_completion_tokens(self, kwargs: Dict[str, Any]) -> int:
        raw = kwargs.get("max_tokens") if kwargs.get("max_tokens") else os.getenv("GROQ_MAX_COMPLETION_TOKENS")
        try:
            value = int(raw) if raw is not None else 1024
        except (TypeError, ValueError):
            value = 1024
        return max(value, 1)

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        payload = [self._convert_message(m) for m in messages]
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": payload,
            "temperature": kwargs.get("temperature", 0.2),
        }
        params[self._max_token_param] = self._max_completion_tokens(kwargs)
        if "response_format" in kwargs:
            params["response_format"] = kwargs["response_format"]
        else:
            params["response_format"] = {"type": "text"}

        resp = self.client.chat.completions.create(**params)
        choice = resp.choices[0].message
        content = getattr(choice, "content", "")
        text = ""
        if isinstance(content, list):
            text = "".join(part.get("text", "") for part in content if part.get("type") in {"output_text", "text"})
        elif isinstance(content, str):
            text = content
        return text or "", int((time.time() - start) * 1000)
