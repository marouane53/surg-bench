from __future__ import annotations
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any

def ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def md5_bytes(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()

def save_bytes(path: Path, data: bytes) -> Path:
    ensure_dir(path.parent)
    path.write_bytes(data)
    return path

def chunk(items: List[Any], n: int):
    for i in range(0, len(items), n):
        yield items[i:i+n]
