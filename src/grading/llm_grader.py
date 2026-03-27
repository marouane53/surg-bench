from __future__ import annotations
import json, time, os, re
from typing import Dict, Any, Tuple, List
from .base import Grader
from openai import OpenAI
import httpx
try:
    from google import genai
    from google.genai import types
    from google.genai import errors as genai_errors
except ImportError:
    genai = None
    types = None
    genai_errors = None

class OpenAIGrader(Grader):
    """
    Grader powered by OpenAI models.

    **What's new:**
    - Uses the **Responses API** automatically for GPT‑5 models (gpt-5, gpt-5-mini),
      which fixes the "GPT‑5 Mini as grader" issue when using Chat Completions.
    - Falls back to Chat Completions for non‑GPT‑5 models.
    """
    name = "gpt-5-mini"
    def __init__(self, model: str = "gpt-5-mini", base_url: str | None = None, api_key: str | None = None):
        kwargs: Dict[str, Any] = {}
        if base_url:
            kwargs["base_url"] = base_url
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self._api_key, **kwargs)
        self.model = model
        self._supports_responses_sdk = bool(getattr(self.client, "responses", None) and hasattr(self.client.responses, "create"))

    # ---------- Responses API helpers ----------
    def _msgs_to_responses(self, prompt: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        """Convert chat-style prompt to Responses API 'input' + 'instructions'."""
        instructions = ""
        input_messages: List[Dict[str, Any]] = []
        # Ensure strict JSON-only instruction comes first
        instructions_parts: List[str] = ["Return a JSON object only."]
        for m in prompt.get("messages", []):
            role = m.get("role")
            if role == "system":
                instructions_parts.append(str(m.get("content") or ""))
            elif role in {"user", "assistant"}:
                content = m.get("content")
                if isinstance(content, str):
                    input_messages.append({
                        "role": role,
                        "content": [{"type": "input_text", "text": content}],
                    })
                elif isinstance(content, list):
                    converted: List[Dict[str, Any]] = []
                    for part in content:
                        if part.get("type") == "text":
                            converted.append({"type": "input_text", "text": part.get("text", "")})
                        elif part.get("type") == "image_url":
                            iu = part.get("image_url")
                            url = iu.get("url") if isinstance(iu, dict) else (iu if isinstance(iu, str) else None)
                            if url:
                                converted.append({"type": "input_image", "image_url": url})
                    if converted:
                        input_messages.append({"role": role, "content": converted})
        instructions = "\n".join(p for p in instructions_parts if p.strip())
        return input_messages, instructions

    def _extract_text_from_responses_sdk(self, resp: Any) -> str:
        # Preferred: unified 'output_text'
        try:
            txt = getattr(resp, "output_text", None)
            if isinstance(txt, str) and txt.strip():
                return txt
        except Exception:
            pass
        if isinstance(resp, dict):
            txt = resp.get("output_text")
            if isinstance(txt, str) and txt.strip():
                return txt
        # Fallback: walk 'output' blocks
        try:
            output = getattr(resp, "output", None)
            if output:
                chunks: List[str] = []
                for item in output:
                    typ = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)
                    if typ in {"output_text", "text"}:
                        t = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else None)
                        if isinstance(t, str) and t.strip():
                            chunks.append(t)
                            continue
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
        if isinstance(resp, dict):
            output = resp.get("output")
            if output:
                chunks: List[str] = []
                for item in output:
                    typ = item.get("type") if isinstance(item, dict) else None
                    if typ in {"output_text", "text"}:
                        t = item.get("text")
                        if isinstance(t, str) and t.strip():
                            chunks.append(t)
                            continue
                    if typ == "message":
                        content = item.get("content")
                        if isinstance(content, list):
                            for c in content:
                                ctype = c.get("type")
                                if ctype in {"output_text", "text"}:
                                    t = c.get("text")
                                    if isinstance(t, str) and t.strip():
                                        chunks.append(t)
                if chunks:
                    return "".join(chunks)
        # Last ditch
        try:
            txt = getattr(resp, "text", None)
            if isinstance(txt, str) and txt.strip():
                return txt
        except Exception:
            pass
        return ""

    def _response_to_dict(self, resp: Any) -> Dict[str, Any]:
        if isinstance(resp, dict):
            return resp
        for attr in ("model_dump", "to_dict"):
            fn = getattr(resp, attr, None)
            if callable(fn):
                try:
                    return fn()
                except Exception:
                    pass
        fn_json = getattr(resp, "model_dump_json", None)
        if callable(fn_json):
            try:
                return json.loads(fn_json())
            except Exception:
                pass
        fn_json2 = getattr(resp, "to_json", None)
        if callable(fn_json2):
            try:
                return json.loads(fn_json2())
            except Exception:
                pass
        # Fallback: try attribute access for known fields
        return {
            "status": getattr(resp, "status", None),
            "output": getattr(resp, "output", None),
            "output_text": getattr(resp, "output_text", None),
            "incomplete_details": getattr(resp, "incomplete_details", None),
        }

    def _invoke_responses(self, params: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        if self._supports_responses_sdk:
            resp = self.client.responses.create(**params)
            resp_dict = self._response_to_dict(resp)
            raw = self._extract_text_from_responses_sdk(resp)
        else:
            http_resp = self.client.post("/responses", cast_to=httpx.Response, body=params)
            http_resp.raise_for_status()
            resp_dict = http_resp.json()
            raw = self._extract_text_from_responses_sdk(resp_dict)
        return resp_dict, raw or ""

    def grade(self, prompt: Dict[str, Any]) -> Tuple[float, str, list, bool]:
        """
        Return (score 0..1, justification, missed[], harmful?).

        For GPT‑5 family we call the **Responses API** with `max_output_tokens`,
        otherwise we use Chat Completions with `max_tokens`.
        """
        model = self.model or "gpt-5-mini"
        if str(model).startswith("gpt-5"):
            # Responses API path (recommended for GPT‑5)
            input_messages, instructions = self._msgs_to_responses(prompt)
            if not input_messages:
                # Fallback to concatenated user/assistant text if helper could not map structured content
                combined = []
                for msg in prompt.get("messages", []):
                    role = msg.get("role")
                    if role not in {"user", "assistant"}:
                        continue
                    content = msg.get("content")
                    if isinstance(content, str) and content.strip():
                        combined.append(content.strip())
                    elif isinstance(content, list):
                        parts = []
                        for part in content:
                            if part.get("type") == "text" and part.get("text"):
                                parts.append(part["text"])
                        if parts:
                            combined.append("\n".join(parts))
                if combined:
                    input_messages = [{
                        "role": "user",
                        "content": [{"type": "input_text", "text": "\n\n".join(combined)}]
                    }]
            params: Dict[str, Any] = {
                "model": model,
                "input": input_messages,
                "max_output_tokens": 900,
                "reasoning": {"effort": "minimal"},
                "text": {"format": {"type": "json_object"}},
            }
            if instructions:
                params["instructions"] = instructions
            max_tokens = params["max_output_tokens"]
            for attempt in range(int(os.getenv("GRADER_MAX_ATTEMPTS", "3"))):
                resp_dict, raw = self._invoke_responses(params)
                status = resp_dict.get("status") if isinstance(resp_dict, dict) else None
                if status == "incomplete" and (resp_dict.get("incomplete_details") or {}).get("reason") == "max_output_tokens":
                    max_tokens = min(int(max_tokens * 2), 4096)
                    params["max_output_tokens"] = max_tokens
                    # ensure we stay in the lowest effort for retries
                    params["reasoning"] = {"effort": "minimal"}
                    continue
                if not raw.strip():
                    raw = self._extract_text_from_responses_sdk(resp_dict) or "{}"
                data = _robust_json_parse(raw)
                return _normalize_grader_output(data)
            # If all attempts result in incomplete or unparsable output, fall back to zeros.
            return 0.0, "", [], False

        # --- Non GPT‑5 path: Chat Completions ---
        sys = {"role": "system", "content": "Return a JSON object only."}
        msgs = [sys] + prompt["messages"]
        params = {
            "max_tokens": 350,
            "temperature": 0.0,
        }
        # Some providers mirror 'max_completion_tokens' for newer models; keep it simple here.
        resp = self.client.chat.completions.create(model=model, messages=msgs, **params)
        txt = resp.choices[0].message.content or "{}"
        data = _robust_json_parse(txt)
        return _normalize_grader_output(data)

class GeminiGrader(Grader):
    name = "gemini-2.5-flash"
    def __init__(self, model: str = "gemini-2.5-flash"):
        if genai is None:
            raise ImportError("google-genai package required for GeminiGrader")
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = model

    def grade(self, prompt: Dict[str, Any]) -> Tuple[float, str, list, bool]:
        sys = "Return a JSON object only."
        text = ""
        for m in prompt["messages"]:
            if m["role"] == "system":
                text += m["content"] + "\n"
            else:
                text += m["content"] if isinstance(m["content"], str) else "\n".join([p.get("text","") for p in m["content"] if p.get("type")=="text"])
        text = sys + "\n" + text
        # Retry/backoff on transient server errors (e.g., 503)
        attempts = int(os.getenv("GRADER_RETRIES", "4"))
        delay = 1.0
        last_exc: Exception | None = None
        for i in range(attempts):
            try:
                resp = self.client.models.generate_content(
                    model=self.model,
                    contents=[text],
                    config=types.GenerateContentConfig(**({"temperature": 0} if not str(self.model).startswith("gemini-3") else {}))
                )
                raw = resp.text or "{}"
                data = _robust_json_parse(raw)
                return _normalize_grader_output(data)
            except Exception as e:
                # Identify retryable server-side/network issues
                msg = str(e)
                retryable = False
                if genai_errors is not None and isinstance(e, getattr(genai_errors, "ServerError", tuple())):
                    retryable = True
                elif "503" in msg or "UNAVAILABLE" in msg or "temporarily unavailable" in msg.lower():
                    retryable = True
                if not retryable or i == attempts - 1:
                    last_exc = e
                    break
                time.sleep(min(delay, 10.0))
                delay *= 2
        # If we reach here, retries failed
        if last_exc:
            raise last_exc
        # Fallback safeguard (should not reach)
        return 0.0, "", [], False

def _strip_code_fence(s: str) -> str:
    s = s.strip()
    # Remove leading and trailing code fences, e.g., ```json ... ``` or ``` ... ```
    if s.startswith("```"):
        # drop first fence line
        s = re.sub(r"^```[a-zA-Z0-9_\-]*\n", "", s)
    if s.endswith("```"):
        s = re.sub(r"\n```$", "", s)
    return s.strip()

def _robust_json_parse(s: str) -> Dict[str, Any]:
    """Best-effort extraction of a JSON object from model output.
    Handles code fences and extra prose. Falls back to regex parsing.
    """
    if not s:
        return {"score": 0.0, "justification": "", "missed": [], "harmful": False}
    s1 = _strip_code_fence(s)
    # Try direct parse
    try:
        return json.loads(s1)
    except Exception:
        pass

    # Try to locate the first JSON object within the text
    start = s1.find("{")
    end = s1.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = s1[start:end+1]
        try:
            return json.loads(candidate)
        except Exception:
            # sometimes single quotes are used
            candidate2 = candidate.replace("'", '"')
            try:
                return json.loads(candidate2)
            except Exception:
                pass

    # Fallback: extract fields with regex
    score = _extract_score(s1)
    missed = _extract_list(s1, key="missed")
    harmful = bool(re.search(r"harmful\s*[:=]\s*(true|yes|1)", s1, re.I))
    just = s1
    return {"score": score, "justification": just, "missed": missed, "harmful": harmful}

def _extract_score(text: str) -> float:
    # Look for JSON-like score first
    m = re.search(r'"score"\s*:\s*([0-9.]+)', text)
    if m:
        try:
            return _clamp01(float(m.group(1)))
        except Exception:
            pass
    # Look for percentage
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)%", text)
    if m:
        try:
            return _clamp01(float(m.group(1)) / 100.0)
        except Exception:
            pass
    # Look for plain score 0..1
    m = re.search(r"score\s*[:=]?\s*([01](?:\.[0-9]+)?)\b", text, re.I)
    if m:
        try:
            val = float(m.group(1))
            return _clamp01(val)
        except Exception:
            pass
    # Look for x/1 format (with or without 'score' label)
    m = re.search(r"score\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)[\s/]1\b", text, re.I)
    if m:
        try:
            return _clamp01(float(m.group(1)))
        except Exception:
            pass
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)[\s/]1\b", text)
    if m:
        try:
            return _clamp01(float(m.group(1)))
        except Exception:
            pass
    return 0.0

def _extract_list(text: str, key: str) -> List[str]:
    # Try to find JSON array after key
    m = re.search(rf'"{key}"\s*:\s*(\[.*?\])', text, re.S)
    if m:
        try:
            arr = json.loads(m.group(1))
            if isinstance(arr, list):
                return [str(x) for x in arr]
        except Exception:
            pass
    return []

def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def _normalize_grader_output(data: Dict[str, Any]) -> Tuple[float, str, list, bool]:
    score_raw = data.get("score", 0.0)
    try:
        score = float(score_raw)
    except Exception:
        # If string like "70%" or "0.7/1"
        score = _extract_score(str(score_raw))
    score = _clamp01(score)
    just = str(data.get("justification", ""))
    missed = data.get("missed", [])
    if not isinstance(missed, list):
        missed = [str(missed)]
    harmful = bool(data.get("harmful", False))
    return score, just, missed, harmful
