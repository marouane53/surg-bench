from __future__ import annotations
import json, time, os, re
from typing import Dict, Any, Tuple, List
from .base import Grader
from openai import OpenAI
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

class OpenAIGrader(Grader):
    name = "gpt-5-mini"
    def __init__(self, model: str = "gpt-5-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def grade(self, prompt: Dict[str, Any]) -> Tuple[float, str, list, bool]:
        # ask for structured JSON
        sys = {"role": "system", "content": "Return a JSON object only."}
        msgs = [sys] + prompt["messages"]
        params = {}
        if str(self.model).startswith("gpt-5"):
            params["max_completion_tokens"] = 350
            # Many gpt-5 chat endpoints use fixed temperature; avoid passing
        else:
            params["max_tokens"] = 350
            params["temperature"] = 0.0
        resp = self.client.chat.completions.create(model=self.model, messages=msgs, **params)
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
        resp = self.client.models.generate_content(model=self.model, contents=[text], config=types.GenerateContentConfig(temperature=0))
        raw = resp.text or "{}"
        data = _robust_json_parse(raw)
        return _normalize_grader_output(data)

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
