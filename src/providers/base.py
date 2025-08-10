from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import time

class Provider:
    name: str
    def __init__(self, model: str):
        self.model = model

    def supports_images(self) -> bool:
        return True

    def ask(self, messages: List[Dict[str, Any]], **kwargs) -> Tuple[str, int]:
        """Return text and latency_ms"""
        raise NotImplementedError
