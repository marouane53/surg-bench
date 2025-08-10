from __future__ import annotations
import os, time
from typing import Any, Dict, List, Tuple, Optional
from openai import OpenAI
import httpx
from .base import Provider

class OpenAIReasoningProvider(Provider):
    name = "openai-reasoning"
    def __init__(self, model: str, base_url: Optional[str] = None, api_key: Optional[str] = None, effort: str = "minimal"):
        super().__init__(model)
        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
        # Keep a client if available, but also store base_url and api_key for HTTP fallback
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), **kwargs)
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        # Default to public OpenAI endpoint if not provided
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.effort = effort

    def supports_images(self) -> bool:
        return True

    def _convert_messages_to_input(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert standard chat messages to the reasoning API input format"""
        input_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                # System messages are handled differently in reasoning API
                continue
            elif msg["role"] == "user":
                content = msg["content"]
                if isinstance(content, str):
                    input_messages.append({
                        "role": "user",
                        "content": [{"type": "input_text", "text": content}]
                    })
                elif isinstance(content, list):
                    # Handle mixed content (text + images)
                    converted_content = []
                    for item in content:
                        if item.get("type") == "text":
                            converted_content.append({"type": "input_text", "text": item.get("text", "")})
                        elif item.get("type") == "image_url":
                            # Convert image format for reasoning API (image_url at top-level)
                            url = None
                            iu = item.get("image_url")
                            if isinstance(iu, dict):
                                url = iu.get("url")
                            elif isinstance(iu, str):
                                url = iu
                            if url:
                                converted_content.append({"type": "input_image", "image_url": url})
                    input_messages.append({
                        "role": "user", 
                        "content": converted_content
                    })
        
        return input_messages

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        
        # Convert messages to reasoning API format
        input_messages = self._convert_messages_to_input(messages)
        
        # Extract system message content if present (prepend to first user text for compatibility)
        system_content = ""
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
                break
        # Default larger budget so reasoning + answer both fit
        max_tokens = int(kwargs.get("max_tokens", 1024))
        
        # First try via SDK if available
        try:
            # Some installed SDKs may not have client.responses; AttributeError will trigger HTTP fallback
            if not hasattr(self.client, "responses"):
                raise AttributeError("OpenAI client missing 'responses' API")
            resp = self.client.responses.create(
                model=self.model,
                input=input_messages,
                reasoning={"effort": self.effort},
                max_output_tokens=max_tokens,
            )

            # Extract text from Responses API (SDK object)
            text = ""
            if hasattr(resp, 'output_text') and resp.output_text:
                text = resp.output_text
            elif hasattr(resp, 'content') and resp.content:
                # content may be a list of objects or dicts
                for item in resp.content:
                    if hasattr(item, 'text') and item.text:
                        text += item.text
                    elif isinstance(item, dict) and item.get('type') in ("output_text", "reasoning", "redacted"):
                        if 'text' in item and item['text']:
                            text += item['text']
            elif hasattr(resp, 'choices') and resp.choices:
                # Some SDKs expose a choices-like structure
                text = getattr(resp.choices[0].message, 'content', None) or ""
            elif hasattr(resp, 'text'):
                text = resp.text or ""
            else:
                text = str(resp)

        except Exception as e_sdk:
            # Try raw HTTP call to Responses API for broader compatibility
            try:
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
                payload: Dict[str, Any] = {
                    "model": self.model,
                    "input": input_messages,
                    "reasoning": {"effort": self.effort},
                    "max_output_tokens": max_tokens,
                }
                url = f"{self._base_url}/responses"
                r = httpx.post(url, headers=headers, json=payload, timeout=60.0)
                if r.status_code >= 400:
                    try:
                        errj = r.json()
                    except Exception:
                        errj = r.text
                    raise RuntimeError(f"Responses API error {r.status_code}: {errj}")
                data = r.json()
                # Extract text from raw JSON response
                text = ""
                if isinstance(data, dict):
                    # Preferred unified field
                    if isinstance(data.get("output_text"), str):
                        text = data["output_text"]
                    # Top-level content list
                    elif isinstance(data.get("content"), list):
                        for item in data["content"]:
                            if isinstance(item, dict) and isinstance(item.get("text"), str):
                                text += item.get("text")
                    # Output blocks (message/reasoning/tool)
                    elif isinstance(data.get("output"), list):
                        for blk in data["output"]:
                            if isinstance(blk, dict):
                                # message block may have content list
                                if blk.get("type") == "message" and isinstance(blk.get("content"), list):
                                    for it in blk["content"]:
                                        if isinstance(it, dict) and isinstance(it.get("text"), str):
                                            text += it["text"]
                                # Some servers might inline text
                                if isinstance(blk.get("text"), str):
                                    text += blk["text"]
                    # response.message.content fallback
                    elif isinstance(data.get("response"), dict):
                        respobj = data["response"]
                        if isinstance(respobj.get("content"), list):
                            for item in respobj["content"]:
                                if isinstance(item, dict) and isinstance(item.get("text"), str):
                                    text += item["text"]
                    # choices-like fallback
                    elif data.get("choices"):
                        choice0 = data["choices"][0]
                        message = choice0.get("message", {})
                        text = message.get("content", "")
                    # If incomplete due to cap, attempt a one-time retry with larger budget
                    if not text and data.get("status") == "incomplete":
                        inc = data.get("incomplete_details", {})
                        if isinstance(inc, dict) and inc.get("reason") in {"max_output_tokens", "max_tokens"}:
                            payload["max_output_tokens"] = max_tokens * 2
                            r2 = httpx.post(url, headers=headers, json=payload, timeout=60.0)
                            if r2.status_code >= 400:
                                try:
                                    errj2 = r2.json()
                                except Exception:
                                    errj2 = r2.text
                                raise RuntimeError(f"Responses API error {r2.status_code}: {errj2}")
                            data2 = r2.json()
                            if isinstance(data2, dict):
                                if isinstance(data2.get("output_text"), str):
                                    text = data2["output_text"]
                                elif isinstance(data2.get("content"), list):
                                    for item in data2["content"]:
                                        if isinstance(item, dict) and isinstance(item.get("text"), str):
                                            text += item["text"]
                if not text:
                    text = str(data)

            except Exception as e_http:
                # If the first attempt failed (possibly due to max_output_tokens), retry with max_completion_tokens
                try:
                    headers = {
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    }
                    alt_payload: Dict[str, Any] = {
                        "model": self.model,
                        "input": input_messages,
                        "reasoning": {"effort": self.effort},
                        "max_completion_tokens": max_tokens,
                    }
                    url = f"{self._base_url}/responses"
                    r = httpx.post(url, headers=headers, json=alt_payload, timeout=60.0)
                    if r.status_code >= 400:
                        try:
                            errj = r.json()
                        except Exception:
                            errj = r.text
                        raise RuntimeError(f"Responses API error {r.status_code}: {errj}")
                    data = r.json()

                    text = ""
                    if isinstance(data, dict):
                        if isinstance(data.get("output_text"), str):
                            text = data["output_text"]
                        elif isinstance(data.get("content"), list):
                            for item in data["content"]:
                                if isinstance(item, dict) and isinstance(item.get("text"), str):
                                    text += item.get("text")
                        elif isinstance(data.get("output"), list):
                            for blk in data["output"]:
                                if isinstance(blk, dict):
                                    if blk.get("type") == "message" and isinstance(blk.get("content"), list):
                                        for it in blk["content"]:
                                            if isinstance(it, dict) and isinstance(it.get("text"), str):
                                                text += it["text"]
                                    if isinstance(blk.get("text"), str):
                                        text += blk["text"]
                        elif isinstance(data.get("response"), dict):
                            respobj = data["response"]
                            if isinstance(respobj.get("content"), list):
                                for item in respobj["content"]:
                                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                                        text += item["text"]
                        # Retry with larger budget if capped
                        if not text and data.get("status") == "incomplete":
                            inc = data.get("incomplete_details", {})
                            if isinstance(inc, dict) and inc.get("reason") in {"max_output_tokens", "max_tokens"}:
                                alt_payload["max_completion_tokens"] = max_tokens * 2
                                r2 = httpx.post(url, headers=headers, json=alt_payload, timeout=60.0)
                                if r2.status_code >= 400:
                                    try:
                                        errj2 = r2.json()
                                    except Exception:
                                        errj2 = r2.text
                                    raise RuntimeError(f"Responses API error {r2.status_code}: {errj2}")
                                data2 = r2.json()
                                if isinstance(data2, dict) and isinstance(data2.get("output_text"), str):
                                    text = data2["output_text"]
                    if not text:
                        text = str(data)

                except Exception as e_http2:
                # Final fallback: try Chat Completions (may not work for gpt-5)
                    print(f"Reasoning API failed, falling back to standard API: {e_sdk or e_http2}")
                    resp = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_completion_tokens=max_tokens,
                    )
                    text = resp.choices[0].message.content or ""

        return text, int((time.time()-start)*1000)
