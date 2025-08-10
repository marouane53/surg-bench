from __future__ import annotations
from typing import Dict, Any, List
import base64
from pathlib import Path
from .dataset import QAItem

SYSTEM_MEDICAL = (
    "You are a senior surgical trainee. Provide accurate, concise, guideline aligned answers. "
    "Use numbered steps when appropriate. Avoid unsafe advice. If uncertain, say what is needed to decide."
)

def pack_messages_for_question(item: QAItem) -> Dict[str, Any]:
    # OpenAI style messages with optional images
    content_parts: List[Dict[str, Any]] = [{"type": "text", "text": item.question_text}]
    for img_rel in item.images:
        p = Path("data") / img_rel  # images saved under data/out/images/...
        if not p.exists():
            # try absolute fallback
            p = Path(img_rel)
        if p.exists():
            b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
            content_parts.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "auto"}})

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_MEDICAL},
            {"role": "user", "content": content_parts}
        ]
    }

GRADING_RUBRIC = (
    "You are grading a surgical viva style answer against a reference answer. "
    "Score from 0 to 1. Use this rubric: accuracy 0.5, completeness 0.3, clinical reasoning 0.2. "
    "Be strict with harmful or outdated recommendations. "
    "Return JSON with fields: score float 0..1, justification string, missed list of short strings, harmful boolean."
)

def build_grading_prompt(question: str, ref_answer: str, candidate: str) -> Dict[str, Any]:
    user_text = (
        f"Question:\n{question}\n\nReference answer:\n{ref_answer}\n\nCandidate answer:\n{candidate}\n\n"
        "Grade now."
    )
    return {
        "messages": [
            {"role": "system", "content": GRADING_RUBRIC},
            {"role": "user", "content": user_text}
        ]
    }
