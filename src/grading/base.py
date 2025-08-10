from __future__ import annotations
from typing import Dict, Any, Tuple

class Grader:
    name: str
    def grade(self, prompt: Dict[str, Any]) -> Tuple[float, str, list, bool]:
        raise NotImplementedError
