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


# -----------------------------
# Q / A text helpers
# -----------------------------
def _split_q_blocks(text: str) -> List[Tuple[str, str]]:
    """Return list of (qid, qtext) from a block of page text."""
    parts: List[Tuple[str, str]] = []
    t = re.sub(r"[ \t]+", " ", text)
    tokens = list(Q_RE.finditer(t))
    for i, m in enumerate(tokens):
        start = m.end()
        end = tokens[i + 1].start() if i + 1 < len(tokens) else len(t)
        qid = f"Q{m.group(1)}.{m.group(2)}"
        qtext = t[start:end].strip()
        parts.append((qid, qtext))
    return parts


def _split_a_blocks(text: str) -> List[Tuple[str, str]]:
    """Return list of (aid, atext) from a block of page text."""
    parts: List[Tuple[str, str]] = []
    t = re.sub(r"[ \t]+", " ", text)
    tokens = list(A_RE.finditer(t))
    for i, m in enumerate(tokens):
        start = m.end()
        end = tokens[i + 1].start() if i + 1 < len(tokens) else len(t)
        aid = f"A{m.group(1)}.{m.group(2)}"
        atext = t[start:end].strip()
        parts.append((aid, atext))
    return parts


def _collect_q_anchors(doc: fitz.Document) -> Dict[str, Tuple[int, float]]:
    """Find the top Y position for each question anchor 'Qx.y' using text blocks.

    Returns:
        dict: {qid: (page_index, y0)}  (y0 in PDF points from top)
    """
    anchors: Dict[str, Tuple[int, float]] = {}
    for i in range(doc.page_count):
        page = doc.load_page(i)
        # get_text("blocks") returns [x0,y0,x1,y1,"text", block_no, ...]
        for blk in page.get_text("blocks"):
            try:
                x0, y0, x1, y1, text, *_ = blk
            except Exception:
                continue
            if not isinstance(text, str):
                continue
            for m in Q_RE.finditer(text):
                qid = f"Q{m.group(1)}.{m.group(2)}"
                # If appears multiple times, keep the earliest (topmost y)
                if qid not in anchors or y0 < anchors[qid][1]:
                    anchors[qid] = (i, y0)
    return anchors


# -----------------------------
# Image collection
# -----------------------------
def _to_png(raw: bytes) -> bytes:
    """Convert arbitrary image bytes to PNG; fall back to raw if conversion fails."""
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.mode not in ("RGB", "RGBA", "L"):
                im = im.convert("RGB")
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        return raw


def _collect_images_all_pages(
    doc: fitz.Document,
    min_area_ratio: float = 0.004,   # ~0.4% of page area
    min_bytes: int = 1500
) -> List[Dict[str, object]]:
    """Collect images for the entire document with bounding boxes.

    We combine:
      - rawdict image blocks (fast path, has bbox)
      - XREF listing via page.get_images(full=True) + page.get_image_rects(xref)

    Returns:
        A list of dicts: {"page": int, "bbox": (x0,y0,x1,y1), "bytes": bytes}
    """
    images: List[Dict[str, object]] = []

    for i in range(doc.page_count):
        page = doc.load_page(i)
        pw, ph = page.rect.width, page.rect.height
        page_area = max(pw * ph, 1.0)
        seen_keys = set()

        # 1) From rawdict blocks (often already includes bbox + bytes or xref)
        rd = page.get_text("rawdict")
        for b in rd.get("blocks", []):
            if b.get("type") != 1:
                continue
            bbox = tuple(b["bbox"])
            img_bytes: Optional[bytes] = None

            img_field = b.get("image")
            if isinstance(img_field, (bytes, bytearray)):
                img_bytes = bytes(img_field)
            else:
                # Sometimes 'image' is an xref integer
                try:
                    xref = int(img_field) if img_field is not None else None
                except Exception:
                    xref = None
                if xref:
                    try:
                        base_image = page.parent.extract_image(xref)
                        img_bytes = base_image.get("image")
                    except Exception:
                        img_bytes = None

            if not img_bytes or len(img_bytes) < min_bytes:
                continue

            w = max(0.0, bbox[2] - bbox[0])
            h = max(0.0, bbox[3] - bbox[1])
            if (w * h) / page_area < min_area_ratio:
                continue

            key = (round(bbox[0], 1), round(bbox[1], 1), round(bbox[2], 1), round(bbox[3], 1), len(img_bytes))
            if key in seen_keys:
                continue
            seen_keys.add(key)

            images.append({"page": i, "bbox": bbox, "bytes": img_bytes})

        # 2) From XREF listing + rects (captures images inside XObjects)
        try:
            xrefs = page.get_images(full=True)
        except Exception:
            xrefs = []

        for entry in xrefs:
            # entry[0] is xref according to PyMuPDF docs
            xref = entry[0]
            try:
                base = page.parent.extract_image(xref)
                img_bytes = base.get("image")
            except Exception:
                img_bytes = None
            if not img_bytes or len(img_bytes) < min_bytes:
                continue

            rects = []
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []

            for r in rects or []:
                bbox = (r.x0, r.y0, r.x1, r.y1)
                w = max(0.0, bbox[2] - bbox[0])
                h = max(0.0, bbox[3] - bbox[1])
                if (w * h) / page_area < min_area_ratio:
                    continue

                key = (round(bbox[0], 1), round(bbox[1], 1), round(bbox[2], 1), round(bbox[3], 1), len(img_bytes))
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                images.append({"page": i, "bbox": bbox, "bytes": img_bytes})

    info(f"Collected {len(images)} images across {doc.page_count} pages")
    return images


# -----------------------------
# Assignment helpers
# -----------------------------
def _abspos(page_index: int, y: float, page_height: float) -> float:
    """Return a scalar position combining page index and vertical offset."""
    if page_height <= 0:
        page_height = 1.0
    return page_index + (y / page_height)


def _build_q_position_bands(
    doc: fitz.Document,
    q_map: Dict[str, Tuple[int, str]],
    anchors: Dict[str, Tuple[int, float]],
) -> List[Tuple[str, float, float]]:
    """Create vertical Voronoi-like bands along the document for each question.

    Returns a list of (qid, band_start, band_end) using absolute position units.
    """
    # Build a list of (qid, pos) for all questions
    q_pos_list: List[Tuple[str, float]] = []
    for qid, (page_idx, _qtext) in q_map.items():
        # if anchor not found on page, fall back to small y (close to top)
        if qid in anchors:
            p, y = anchors[qid]
        else:
            p, y = page_idx, 0.0
        ph = doc.load_page(p).rect.height
        q_pos_list.append((qid, _abspos(p, y, ph)))

    q_pos_list.sort(key=lambda t: t[1])
    if not q_pos_list:
        return []

    # Compute midpoints between consecutive questions as band boundaries
    bands: List[Tuple[str, float, float]] = []
    for i, (qid, pos) in enumerate(q_pos_list):
        prev_pos = q_pos_list[i - 1][1] if i > 0 else pos - 1.0
        next_pos = q_pos_list[i + 1][1] if i + 1 < len(q_pos_list) else pos + 1.0
        start = (prev_pos + pos) / 2.0 if i > 0 else prev_pos
        end = (pos + next_pos) / 2.0 if i + 1 < len(q_pos_list) else next_pos
        bands.append((qid, start, end))
    return bands


def _assign_images_to_questions(
    doc: fitz.Document,
    images: List[Dict[str, object]],
    bands: List[Tuple[str, float, float]],
) -> Dict[str, List[Dict[str, object]]]:
    """Assign each image to the question whose band contains the image absolute position."""
    out: Dict[str, List[Dict[str, object]]] = {qid: [] for qid, *_ in bands}
    # Build quick lookup: page height cache
    page_h: Dict[int, float] = {}
    for i in range(doc.page_count):
        page_h[i] = doc.load_page(i).rect.height

    for img in images:
        page_idx = int(img["page"])
        bbox = img["bbox"]  # (x0,y0,x1,y1)
        ymid = (bbox[1] + bbox[3]) / 2.0
        pos = _abspos(page_idx, ymid, page_h.get(page_idx, 1.0))

        # find matching band
        chosen_qid: Optional[str] = None
        for qid, start, end in bands:
            if pos >= start and pos < end:
                chosen_qid = qid
                break
        if chosen_qid is None:
            # if no band matched (shouldn't happen), attach to nearest by distance
            nearest = min(bands, key=lambda b: abs(pos - (b[1] + b[2]) / 2.0))
            chosen_qid = nearest[0]
        out[chosen_qid].append(img)

    # Sort images within each question band by vertical position to keep order
    for qid, lst in out.items():
        lst.sort(key=lambda im: _abspos(int(im["page"]), ((im["bbox"][1] + im["bbox"][3]) / 2.0), page_h[int(im["page"])]))
    return out


# -----------------------------
# Main extract()
# -----------------------------
def extract(pdf_path: str, out_dir: str = "data/out", images_dir: str = "data/out/images") -> List[QAItem]:
    ensure_dir(out_dir)
    ensure_dir(images_dir)
    doc = fitz.open(pdf_path)
    info(f"Opened PDF with {doc.page_count} pages")

    # Pass 1: collect all questions and answers (text only)
    q_map: Dict[str, Tuple[int, str]] = {}
    a_map: Dict[str, Tuple[int, str]] = {}
    chapters_by_page: Dict[int, str] = {}

    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text")
        if not text.strip():
            continue

        # heuristic chapter line: first non-Q/A line
        first_line = text.strip().splitlines()[0].strip()[:60]
        if first_line and not first_line.startswith("Q") and not first_line.startswith("A"):
            chapters_by_page[i] = first_line

        for qid, qtext in _split_q_blocks(text):
            q_map[qid] = (i, qtext)
        for aid, atext in _split_a_blocks(text):
            a_map[aid] = (i, atext)

    if not q_map:
        warn("No questions detected – regex may not match this PDF.")
        return []

    # Pass 2: discover question anchors (page + y)
    anchors = _collect_q_anchors(doc)
    info(f"Found anchors for {len(anchors)} / {len(q_map)} questions")

    # Pass 3: collect all images across the document
    all_images = _collect_images_all_pages(doc)

    # Pass 4: build Voronoi-like bands and assign images
    bands = _build_q_position_bands(doc, q_map, anchors)
    assignment = _assign_images_to_questions(doc, all_images, bands)

    # Pass 5: save images and assemble QA items
    items: List[QAItem] = []
    saved_counts: Dict[str, int] = {}

    for qid, (q_page, qtext) in q_map.items():
        chapter = chapters_by_page.get(q_page)
        aid = "A" + qid[1:]
        a_page, atext = a_map.get(aid, (q_page, ""))

        # Persist images for this question (if any)
        img_paths: List[str] = []
        for idx, img in enumerate(assignment.get(qid, []), start=1):
            raw = img["bytes"]
            # Convert to PNG for consistent downstream handling
            png_bytes = _to_png(raw)
            h = md5_bytes(png_bytes)[:10]
            rel_path = f"{qid.replace('.', '_')}_{idx}_{h}.png"
            save_bytes(Path(images_dir) / rel_path, png_bytes)
            img_paths.append(str(Path("out/images") / rel_path))
        saved_counts[qid] = len(img_paths)

        # Extract sub-questions (simple pattern)
        subs = []
        for line in qtext.split(". "):
            if re.match(r"^\s*\d+\)", line) or re.match(r"^\s*\d+\.", line):
                subs.append(line.strip())

        items.append(
            QAItem(
                qid=qid,
                chapter=chapter,
                page_start=q_page + 1,
                page_end=a_page + 1,
                question_text=qtext.strip(),
                sub_questions=subs,
                images=img_paths,
                answer_text=atext.strip(),
            )
        )

    # Quick summary for debugging
    total_imgs = sum(saved_counts.values())
    zero_img = [k for k, v in saved_counts.items() if v == 0]
    info(f"Assigned {total_imgs} images across {len(items)} Qs; {len(zero_img)} without images")

    return items