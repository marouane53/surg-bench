from __future__ import annotations
import os, time, copy
from typing import Any, Dict, List, Tuple, Optional
from openai import OpenAI
import httpx
from .base import Provider


class OpenAIReasoningProvider(Provider):
    name = "openai-reasoning"

    def __init__(self, model: str, base_url: Optional[str] = None, api_key: Optional[str] = None, effort: str = "minimal"):
        super().__init__(model)
        kwargs: Dict[str, Any] = {}
        if base_url:
            kwargs["base_url"] = base_url
        # Keep a client if available, but also store base_url and api_key for HTTP fallback
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), **kwargs)
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        # Default to public OpenAI endpoint if not provided
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        # OpenAI Responses API supports: "minimal" | "low" | "medium" | "high"
        # (treat "none" as an alias for "minimal" for compatibility)
        self.effort = (effort or "minimal").lower()
        if self.effort == "none":
            self.effort = "minimal"

    def supports_images(self) -> bool:
        return True

    def _sanitize_for_log(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Return a deepcopy of request with large image data URIs redacted.
        Keeps URLs and file paths intact; replaces data: URIs with a short summary.
        """
        safe = copy.deepcopy(req)
        try:
            # Sanitize Responses API input shape
            inp = safe.get("input")
            if isinstance(inp, list):
                for m in inp:
                    if not isinstance(m, dict):
                        continue
                    content = m.get("content")
                    if isinstance(content, list):
                        for part in content:
                            if not isinstance(part, dict):
                                continue
                            if part.get("type") == "input_image":
                                url = part.get("image_url")
                                if isinstance(url, str) and url.startswith("data:"):
                                    preview = url[:40]
                                    part["image_url"] = f"data:<redacted length={len(url)} prefix={preview}>"
            # Sanitize Chat Completions messages shape
            msgs = safe.get("messages")
            if isinstance(msgs, list):
                for m in msgs:
                    if not isinstance(m, dict):
                        continue
                    content = m.get("content")
                    if isinstance(content, list):
                        for part in content:
                            if not isinstance(part, dict):
                                continue
                            if part.get("type") == "image_url":
                                iu = part.get("image_url")
                                if isinstance(iu, dict):
                                    url = iu.get("url")
                                    if isinstance(url, str) and url.startswith("data:"):
                                        preview = url[:40]
                                        iu["url"] = f"data:<redacted length={len(url)} prefix={preview}>"
        except Exception:
            pass
        return safe

    def _convert_messages_to_input(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        """Convert standard chat messages to the Responses API input format and
        return (input_messages, instructions).
        """
        input_messages: List[Dict[str, Any]] = []
        instructions = ""
        for msg in messages:
            role = msg.get("role")
            if role == "system":
                # Responses API expects system content in top-level "instructions"
                instructions = str(msg.get("content") or "")
                continue
            if role != "user":
                # We only send user content in this simple flow
                continue
            content = msg.get("content")
            if isinstance(content, str):
                input_messages.append({
                    "role": "user",
                    "content": [{"type": "input_text", "text": content}]
                })
            elif isinstance(content, list):
                converted_content: List[Dict[str, Any]] = []
                for item in content:
                    t = item.get("type")
                    if t == "text":
                        converted_content.append({"type": "input_text", "text": item.get("text", "")})
                    elif t == "image_url":
                        iu = item.get("image_url")
                        url = iu.get("url") if isinstance(iu, dict) else (iu if isinstance(iu, str) else None)
                        if url:
                            converted_content.append({"type": "input_image", "image_url": url})
                input_messages.append({"role": "user", "content": converted_content})
        return input_messages, instructions

    # ---------- extraction helpers ----------
    def _extract_text_from_sdk(self, resp: Any) -> str:
        """Extract assistant text from an SDK Response object (openai>=1.4x)."""
        # 1) Unified helper if available
        try:
            txt = getattr(resp, "output_text", None)
            if isinstance(txt, str) and txt.strip():
                return txt
        except Exception:
            pass

        # 2) Walk output[] and collect from both 'message' and 'output_text' items
        try:
            output = getattr(resp, "output", None)
            if output:
                chunks: List[str] = []
                for item in output:
                    # item can be a dataclass-like object or dict
                    typ = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)

                    # 2a) Newer SDKs: direct output_text blocks
                    if typ in {"output_text", "text"}:
                        t = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else None)
                        if isinstance(t, str) and t.strip():
                            chunks.append(t)
                            continue

                    # 2b) Message blocks with content parts (some parts themselves are type=output_text)
                    if typ == "message":
                        content = getattr(item, "content", None) or (item.get("content") if isinstance(item, dict) else None)
                        if isinstance(content, list):
                            for c in content:
                                ctype = getattr(c, "type", None) or (c.get("type") if isinstance(c, dict) else None)
                                if ctype in {"output_text", "text"}:
                                    t = getattr(c, "text", None) or (c.get("text") if isinstance(c, dict) else None)
                                    if isinstance(t, str) and t.strip():
                                        chunks.append(t)
                if chunks:
                    return "".join(chunks)
        except Exception:
            pass

        # 3) Some SDKs expose a plain .text
        try:
            txt = getattr(resp, "text", None)
            if isinstance(txt, str) and txt.strip():
                return txt
        except Exception:
            pass

        return ""

    def _extract_text_from_http(self, data: Dict[str, Any]) -> str:
        """Extract assistant text from raw /responses JSON."""
        if not isinstance(data, dict):
            return ""
        # 1) Preferred unified field
        txt = data.get("output_text")
        if isinstance(txt, str) and txt.strip():
            return txt
        # 2) Walk output[] blocks and collect both 'message' and 'output_text'
        out = data.get("output")
        if isinstance(out, list):
            chunks: List[str] = []
            for blk in out:
                if not isinstance(blk, dict):
                    continue
                btype = blk.get("type")
                if btype in {"output_text", "text"}:
                    t = blk.get("text")
                    if isinstance(t, str) and t.strip():
                        chunks.append(t)
                        continue
                if btype == "message":
                    content = blk.get("content", [])
                    if isinstance(content, list):
                        for p in content:
                            if not isinstance(p, dict):
                                continue
                            ptype = p.get("type")
                            if ptype in {"output_text", "text"} and isinstance(p.get("text"), str):
                                chunks.append(p["text"])
            if chunks:
                return "".join(chunks)
        # 3) response.message.content fallback
        respobj = data.get("response")
        if isinstance(respobj, dict):
            content = respobj.get("content")
            if isinstance(content, list):
                chunks: List[str] = []
                for p in content:
                    if isinstance(p, dict) and isinstance(p.get("text"), str):
                        chunks.append(p["text"])
                if chunks:
                    return "".join(chunks)
        # 4) choices-like fallback
        ch = data.get("choices")
        if isinstance(ch, list) and ch:
            message = ch[0].get("message", {}) if isinstance(ch[0], dict) else {}
            txt = message.get("content")
            if isinstance(txt, str):
                return txt
        return ""

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        start = time.time()
        input_messages, instructions = self._convert_messages_to_input(messages)
        # Default to a generous output budget if not explicitly provided
        try:
            max_tokens = int(kwargs.get("max_tokens", 0) or 0)
        except Exception:
            max_tokens = 0
        if max_tokens <= 0:
            # Allow override via env; fallback to 8192
            try:
                max_tokens = int(os.getenv("OPENAI_REASONING_MAX_OUTPUT_TOKENS", "8192"))
            except Exception:
                max_tokens = 8192
        # Initialize debug container for this call
        debug_attempts: List[Dict[str, Any]] = []
        base_request = {
            "model": self.model,
            "input": input_messages,
            "instructions": instructions or None,
            "reasoning": {"effort": self.effort},
            "max_output_tokens": max_tokens,
            "base_url": self._base_url,
        }
        request_for_log = self._sanitize_for_log(base_request)
        text = ""

        # Attempt via SDK first
        try:
            if not hasattr(self.client, "responses"):
                raise AttributeError("OpenAI client missing 'responses' API")
            resp = self.client.responses.create(
                model=self.model,
                input=input_messages,
                instructions=instructions or None,
                reasoning={"effort": self.effort},
                max_output_tokens=max_tokens,
            )
            text = self._extract_text_from_sdk(resp)
            # Record SDK attempt (even if empty)
            sdk_raw: Optional[str] = None
            try:
                # Prefer JSON-like dump when available
                if hasattr(resp, "model_dump_json"):
                    sdk_raw = resp.model_dump_json()
                elif hasattr(resp, "model_dump"):
                    import json as _json
                    sdk_raw = _json.dumps(resp.model_dump(), ensure_ascii=False)
            except Exception:
                pass
            if not sdk_raw:
                try:
                    sdk_raw = str(resp)
                except Exception:
                    sdk_raw = "<unserializable SDK response>"
            debug_attempts.append({
                "path": "sdk",
                "request": request_for_log,
                "response_raw": sdk_raw,
                "parsed_text": text,
                "error": None,
            })
            # If SDK call succeeded but we couldn't parse any text (shape drift),
            # immediately try the raw HTTP path as a fallback.
            if not (text and text.strip()):
                raise RuntimeError("Empty text from SDK response; falling back to HTTP")
        except Exception as e_sdk:
            # Raw HTTP fallback
            try:
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
                payload: Dict[str, Any] = {
                    "model": self.model,
                    "input": input_messages,
                    "instructions": instructions or None,
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
                text = self._extract_text_from_http(data)
                debug_attempts.append({
                    "path": "http",
                    "request": request_for_log,
                    "http_status": r.status_code,
                    "response_raw": r.text,
                    "parsed_text": text,
                    "error": None,
                })

                # If incomplete due to cap, attempt a one-time retry with larger budget
                if (not text) and isinstance(data, dict) and data.get("status") == "incomplete":
                    inc = data.get("incomplete_details", {})
                    reason = inc.get("reason") if isinstance(inc, dict) else None
                    if reason in {"max_output_tokens", "max_tokens"}:
                        payload["max_output_tokens"] = max_tokens * 2
                        r2 = httpx.post(url, headers=headers, json=payload, timeout=60.0)
                        if r2.status_code >= 400:
                            try:
                                errj2 = r2.json()
                            except Exception:
                                errj2 = r2.text
                            raise RuntimeError(f"Responses API error {r2.status_code}: {errj2}")
                        data2 = r2.json()
                        text = self._extract_text_from_http(data2)
                        debug_attempts.append({
                            "path": "http-retry",
                            "request": request_for_log,
                            "http_status": r2.status_code,
                            "response_raw": r2.text,
                            "parsed_text": text,
                            "error": None,
                        })
            except Exception as e_http:
                # Final fallback: try Chat Completions (may not work for gpt-5)
                try:
                    # Build multimodal chat messages: keep text AND images
                    chat_messages: List[Dict[str, Any]] = []
                    if instructions:
                        chat_messages.append({"role": "system", "content": instructions})

                    for im in input_messages:
                        content_parts: List[Dict[str, Any]] = []
                        # 1) Add all text parts (joined)
                        txt_parts: List[str] = []
                        for part in (im.get("content") or []):
                            if part.get("type") == "input_text":
                                txt_parts.append(part.get("text", ""))
                        joined = "\n".join(p for p in txt_parts if p)
                        if joined:
                            content_parts.append({"type": "text", "text": joined})

                        # 2) Add image parts
                        for part in (im.get("content") or []):
                            if part.get("type") == "input_image":
                                url = part.get("image_url")
                                if isinstance(url, str) and url.strip():
                                    content_parts.append({
                                        "type": "image_url",
                                        "image_url": {"url": url, "detail": "auto"}
                                    })

                        # Only append a user turn if we have something to send
                        if content_parts:
                            chat_messages.append({"role": "user", "content": content_parts})

                    # If somehow nothing accumulated, at least send an empty user message
                    if not chat_messages:
                        chat_messages = [{"role": "user", "content": [{"type": "text", "text": ""}]}]

                    resp = self.client.chat.completions.create(
                        model=self.model,
                        messages=chat_messages,
                        max_completion_tokens=max_tokens,
                    )
                    text = resp.choices[0].message.content or ""
                    debug_attempts.append({
                        "path": "chat",
                        "request": self._sanitize_for_log({"model": self.model, "messages": chat_messages, "max_completion_tokens": max_tokens, "base_url": self._base_url}),
                        "response_raw": str(resp),
                        "parsed_text": text,
                        "error": None,
                    })
                except Exception:
                    text = ""
                    debug_attempts.append({
                        "path": "chat",
                        "request": self._sanitize_for_log({"model": self.model, "messages": chat_messages if 'chat_messages' in locals() else None, "max_completion_tokens": max_tokens, "base_url": self._base_url}),
                        "response_raw": None,
                        "parsed_text": text,
                        "error": "chat_fallback_failed",
                    })

        # As a last resort, do not return the whole object string; return empty string
        ms = int((time.time() - start) * 1000)
        # Attach debug info for external logging
        try:
            self.debug_last = {
                "request": request_for_log,
                "attempts": debug_attempts,
                "parsed_text": (text or "").strip(),
                "raw_answer_text": (text or "").strip(),
                "latency_ms": ms,
            }
        except Exception:
            # Never let logging mutate control flow
            self.debug_last = {
                "request": request_for_log,
                "attempts": [],
                "parsed_text": (text or "").strip(),
                "raw_answer_text": (text or "").strip(),
                "latency_ms": ms,
            }
        return (text or "").strip(), ms
