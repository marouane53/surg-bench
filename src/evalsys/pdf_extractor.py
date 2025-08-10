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


def _q_positions(page: fitz.Page) -> Dict[str, float]:
    """Return approximate top-Y of each question header ("Qx.y") on the page.
    We rely on PyMuPDF's block extraction (which is reliable and fast) rather
    than OCR or color heuristics.
    """
    positions: Dict[str, float] = {}
    for span in page.get_text("blocks"):
        try:
            x0, y0, x1, y1, text, *_ = span
        except Exception:
            continue
        if not isinstance(text, str):
            continue
        for m in Q_RE.finditer(text):
            qid = f"Q{m.group(1)}.{m.group(2)}"
            positions[qid] = y0
    return positions


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


def _image_candidates_with_bbox(page: fitz.Page) -> List[Tuple[Tuple[float, float, float, float], bytes]]:
    """Extract images with their bounding boxes from a page.
    
    Returns:
        List of (bbox, raw_bytes) tuples where bbox is (x0, y0, x1, y1)
    """
    images = []
    pw, ph = page.rect.width, page.rect.height
    page_area = max(pw * ph, 1.0)
    seen_keys = set()
    min_area_ratio = 0.004  # 0.4% of page area
    min_bytes = 1500

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

        images.append((bbox, img_bytes))

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

            images.append((bbox, img_bytes))

    return images


def _assign_images_to_qids(page: fitz.Page, q_positions: Dict[str, float], size_thresh: int = 4000) -> Dict[str, List[bytes]]:
    """
    Assign images to the question whose header appears ABOVE them (band-wise),
    instead of the previous 'nearest' heuristic.

    Why this matters:
    - In two-column surgical books, a figure under Q1.1 can sit physically close to the
      Q1.2 header. Nearest-distance would wrongly attach it to Q1.2.
    - Band-wise assignment ensures everything between Qn and Q(n+1) belongs to Qn,
      matching how you (and examiners) read the page.

    Args:
        page: current PyMuPDF page
        q_positions: mapping of 'Qx.y' -> Y coordinate (top of the header block)
        size_thresh: minimum image byte-size to keep (filters tiny artifacts)

    Returns:
        Dict[str, List[bytes]] mapping question-id -> list of raw image bytes on that page
    """
    imgs = _image_candidates_with_bbox(page)
    assignments: Dict[str, List[bytes]] = {k: [] for k in q_positions}
    if not imgs or not q_positions:
        return assignments

    # Pre-filter very small images (decorations / icons)
    filtered = []
    for bbox, raw in imgs:
        if len(raw) < size_thresh:
            continue
        filtered.append((bbox, raw))
    imgs = filtered

    # Build vertical bands: [ y(Qi) .. y(Qi+1) ), last band ends at bottom of page
    ordered = sorted(q_positions.items(), key=lambda kv: kv[1])  # [(qid, y), ...] ascending by y
    bands: List[Tuple[str, float, float]] = []
    page_bottom = float(page.rect.br.y)
    for i, (qid, y) in enumerate(ordered):
        y0 = float(y) - 4.0  # small upward margin
        y1 = float(ordered[i+1][1]) - 4.0 if i+1 < len(ordered) else page_bottom + 1.0
        bands.append((qid, y0, y1))

    # Assign each image to the band containing its vertical midpoint
    for bbox, raw in imgs:
        ymid = (bbox[1] + bbox[3]) / 2.0
        attached = False
        for qid, y0, y1 in bands:
            if ymid >= y0 and ymid < y1:
                assignments[qid].append(raw)
                attached = True
                break
        if not attached:
            # If an image somehow lands above the first header (rare), attach to the first Q on page
            assignments[ordered[0][0]].append(raw)

    return assignments


# Remove the old document-wide assignment function as we're switching to page-by-page


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

    # Pass 2: assign images page by page using ownership bands
    assignment: Dict[str, List[bytes]] = {}
    total_images = 0
    
    for i in range(doc.page_count):
        page = doc.load_page(i)
        
        # NEW: Skip pages that do not visibly contain any "Qx.y" anchors
        # (e.g., cover pages, chapter dividers). This prevents extracting
        # decorative/background images from non-question pages.
        qpos = _q_positions(page)
        if not qpos:
            continue
        
        # Restrict to questions that actually start on this page AND that we detected
        # positions for on this page (guards against stray or mis-read tokens).
        qids_here = [qid for qid, (pi, _) in q_map.items() if pi == i and qid in qpos]
        if not qids_here:
            continue
            
        assign = _assign_images_to_qids(page, qpos)
        for qid, imgs in assign.items():
            # Only attach/save for QIDs that truly start on this page
            if qid not in qids_here:
                continue
            if qid not in assignment:
                assignment[qid] = []
            assignment[qid].extend(imgs)
            total_images += len(imgs)
    
    info(f"Collected {total_images} images across {doc.page_count} pages")

    # Pass 3: save images and assemble QA items
    items: List[QAItem] = []
    saved_counts: Dict[str, int] = {}

    for qid, (q_page, qtext) in q_map.items():
        chapter = chapters_by_page.get(q_page)
        aid = "A" + qid[1:]
        a_page, atext = a_map.get(aid, (q_page, ""))

        # Persist images for this question (if any)
        img_paths: List[str] = []
        for idx, raw in enumerate(assignment.get(qid, []), start=1):
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