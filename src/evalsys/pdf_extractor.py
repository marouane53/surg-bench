from __future__ import annotations
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import fitz
from PIL import Image
import io
from .dataset import QAItem
from .utils import ensure_dir, md5_bytes, save_bytes
from .logging_setup import info, warn

Q_RE = re.compile(r"\bQ\s*(\d+)\.(\d+)\b")
A_RE = re.compile(r"\bA\s*(\d+)\.(\d+)\b")

def _extract_blocks(page: fitz.Page):
    # rawdict preserves image bbox
    d = page.get_text("rawdict")
    blocks = d.get("blocks", [])
    return blocks

def _split_q_blocks(text: str) -> List[Tuple[str, str]]:
    # returns list of (qid, qtext)
    parts: List[Tuple[str, str]] = []
    # Normalize
    t = re.sub(r"[ \t]+", " ", text)
    tokens = list(Q_RE.finditer(t))
    for i, m in enumerate(tokens):
        start = m.end()
        end = tokens[i+1].start() if i+1 < len(tokens) else len(t)
        qid = f"Q{m.group(1)}.{m.group(2)}"
        qtext = t[start:end].strip()
        parts.append((qid, qtext))
    return parts

def _split_a_blocks(text: str) -> List[Tuple[str, str]]:
    parts: List[Tuple[str, str]] = []
    t = re.sub(r"[ \t]+", " ", text)
    tokens = list(A_RE.finditer(t))
    for i, m in enumerate(tokens):
        start = m.end()
        end = tokens[i+1].start() if i+1 < len(tokens) else len(t)
        aid = f"A{m.group(1)}.{m.group(2)}"
        atext = t[start:end].strip()
        parts.append((aid, atext))
    return parts

def _image_candidates_with_bbox(page: fitz.Page) -> List[Tuple[Tuple[float,float,float,float], bytes]]:
    blocks = _extract_blocks(page)
    images: List[Tuple[Tuple[float,float,float,float], bytes]] = []
    for b in blocks:
        if b.get("type") == 1:  # image
            bbox = tuple(b["bbox"])
            xref = b["image"]
            pix = fitz.Pixmap(page.parent, xref)
            if pix.n >= 5:  # CMYK
                pix = fitz.Pixmap(fitz.csRGB, pix)
            img_bytes = pix.tobytes("png")
            images.append((bbox, img_bytes))
    return images

def _nearest_images_to_qids(page: fitz.Page, q_positions: Dict[str, float], size_thresh: int = 10000) -> Dict[str, List[bytes]]:
    # Map each Qid to closest images on this page by vertical proximity
    imgs = _image_candidates_with_bbox(page)
    assignments: Dict[str, List[bytes]] = {k: [] for k in q_positions}
    if not imgs:
        return assignments
    # pre filter tiny images
    filtered = []
    for bbox, raw in imgs:
        if len(raw) < size_thresh:
            continue
        filtered.append((bbox, raw))
    imgs = filtered
    for bbox, raw in imgs:
        ymid = (bbox[1]+bbox[3])/2.0
        # choose nearest q by abs(y - qy)
        nearest = min(q_positions.items(), key=lambda kv: abs(kv[1]-ymid))
        nid, dist = nearest[0], abs(nearest[1]-ymid)
        # only attach if within a sane vertical window
        if dist < 250:  # points
            assignments[nid].append(raw)
    return assignments

def _q_positions(page: fitz.Page) -> Dict[str, float]:
    # return approximate Y for qid anchor line
    positions: Dict[str, float] = {}
    for span in page.get_text("blocks"):
        try:
            x0,y0,x1,y1, text, *_ = span
        except Exception:
            continue
        if not isinstance(text, str):
            continue
        for m in Q_RE.finditer(text):
            qid = f"Q{m.group(1)}.{m.group(2)}"
            positions[qid] = y0
    return positions

def extract(pdf_path: str, out_dir: str = "data/out", images_dir: str = "data/out/images") -> List[QAItem]:
    ensure_dir(out_dir)
    ensure_dir(images_dir)
    doc = fitz.open(pdf_path)
    info(f"Opened PDF with {doc.page_count} pages")

    # pass 1 collect all questions and answers
    q_map: Dict[str, Tuple[int, str]] = {}
    a_map: Dict[str, Tuple[int, str]] = {}

    chapters_by_page: Dict[int, str] = {}

    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text")
        if not text.strip():
            continue
        # naive chapter line: first line often contains section name
        first_line = text.strip().splitlines()[0].strip()[:60]
        if first_line and not first_line.startswith("Q") and not first_line.startswith("A"):
            chapters_by_page[i] = first_line

        for qid, qtext in _split_q_blocks(text):
            q_map[qid] = (i, qtext)
        for aid, atext in _split_a_blocks(text):
            a_map[aid] = (i, atext)

    # pass 2 map images to qids
    img_map: Dict[str, List[str]] = {k: [] for k in q_map}
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text")
        qids_here = [qid for qid, (pi, _) in q_map.items() if pi == i]
        if not qids_here:
            continue
        qpos = _q_positions(page)
        if not qpos:
            continue
        assign = _nearest_images_to_qids(page, qpos)
        for qid, raws in assign.items():
            for idx, raw in enumerate(raws, start=1):
                h = md5_bytes(raw)[:10]
                rel_path = f"{qid.replace('.', '_')}_{idx}_{h}.png"
                save_bytes(Path(images_dir) / rel_path, raw)
                img_map[qid].append(str(Path("out/images") / rel_path))

    # build items
    items: List[QAItem] = []
    for qid, (q_page, qtext) in q_map.items():
        chapter = chapters_by_page.get(q_page)
        aid = "A" + qid[1:]
        a_page, atext = a_map.get(aid, (q_page, ""))  # fall back if missing
        # split sub questions
        subs = []
        for line in qtext.split(". "):
            if re.match(r"^\s*\d+\)", line) or re.match(r"^\s*\d+\.", line):
                subs.append(line.strip())
        items.append(QAItem(
            qid=qid,
            chapter=chapter,
            page_start=q_page+1,
            page_end=a_page+1,
            question_text=qtext.strip(),
            sub_questions=subs,
            images=img_map.get(qid, []),
            answer_text=atext.strip()
        ))
    info(f"Built {len(items)} QA items")
    return items
