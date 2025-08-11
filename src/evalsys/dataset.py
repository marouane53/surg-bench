from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional

class QAItem(BaseModel):
    qid: str                            # "Q1.1"
    chapter: Optional[str] = None
    page_start: int
    page_end: int
    question_text: str
    sub_questions: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)  # relative paths
    answer_text: Optional[str] = None

class ModelResponse(BaseModel):
    provider: str
    model: str
    qid: str
    answer: str
    latency_ms: int
    used_images: int
    retry_attempts: int = 0  # Number of retries attempted
    is_empty_answer: bool = False  # True if final answer is empty after all retries

class GradedResponse(BaseModel):
    provider: str
    model: str
    qid: str
    answer: str
    grader: str
    score: float
    justification: str
    missed: List[str] = Field(default_factory=list)
    harmful: bool = False
