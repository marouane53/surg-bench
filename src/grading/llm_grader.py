from __future__ import annotations
import json, time, os
from typing import Dict, Any, Tuple
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
        resp = self.client.chat.completions.create(model=self.model, messages=msgs, temperature=0.0, max_tokens=350)
        txt = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(txt.strip("` \n"))
        except Exception:
            data = {"score": 0.0, "justification": txt, "missed": [], "harmful": False}
        return float(data.get("score", 0.0)), str(data.get("justification", "")), list(data.get("missed", [])), bool(data.get("harmful", False))

class GeminiGrader(Grader):
    name = "gemini-2.5-flash"
    def __init__(self, model: str = "gemini-2.5-flash"):
        if genai is None:
            raise ImportError("google-genai package required for GeminiGrader")
        self.client = genai.Client()
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
        try:
            data = json.loads(raw.strip("` \n"))
        except Exception:
            data = {"score": 0.0, "justification": raw, "missed": [], "harmful": False}
        return float(data.get("score", 0.0)), str(data.get("justification", "")), list(data.get("missed", [])), bool(data.get("harmful", False))
