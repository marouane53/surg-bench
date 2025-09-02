from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Set
from jinja2 import Template
import json, ast, os, re

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Surgical Benchmark</title>
  <style>
    /* Light theme defaults */
    :root {
      --bg: #f7f8fc;
      --panel: #ffffff;
      --panel-2: #f4f6ff;
      --text: #1b2340;
      --muted: #5a6280;
      --accent: #315efb;
      --grid: #e9ecf4;
      --ok: #1e9e63;
      --warn: #c78a00;
      --bad: #cc3b3b;
      --chip: #eef2ff;
      --chip-text: #2d3a86;
    }
    /* Dark theme overrides */
    [data-theme='dark'] {
      --bg: #0f1220;
      --panel: #171a2b;
      --panel-2: #1e2236;
      --text: #e7e9f5;
      --muted: #9aa2c0;
      --accent: #6ea8fe;
      --grid: #2a3050;
      --ok: #33d17a;
      --warn: #ffcc66;
      --bad: #ff7b7b;
      --chip: #263054;
      --chip-text: #c8d2ff;
    }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 24px; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, Noto Sans, "Apple Color Emoji", "Segoe UI Emoji"; color: var(--text); background: var(--bg); }
    .container { max-width: 1200px; margin: 0 auto; }
    header { display:flex; align-items:center; justify-content:space-between; margin-bottom: 18px; }
    header h1 { font-size: 22px; font-weight: 700; margin: 0; letter-spacing: 0.3px; }
    header .meta { color: var(--muted); font-size: 13px; }
    header .actions { display:flex; gap:8px; align-items:center; }

    .card { background: linear-gradient(180deg, var(--panel), var(--panel-2)); border: 1px solid #232845; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); overflow: hidden; }
    .card .hd { padding: 14px 16px; border-bottom: 1px solid #262b49; display:flex; align-items:center; justify-content:space-between; }
    .card .bd { padding: 16px; }

    /* Chart area: ranked bar chart */
    #chartWrap { position: relative; }
    #scoreCanvas { width: 100%; height: 360px; display:block; }
    .controls { display:flex; gap:10px; align-items:center; }
    .btn { padding: 6px 10px; border-radius: 8px; border: 1px solid #cfd6ff33; background: var(--chip); color: var(--chip-text); cursor: pointer; font-size: 12px; }
    .btn:hover { filter: brightness(1.03); }
    .btn.active { outline: 2px solid var(--accent); }
    .tooltip { position: absolute; pointer-events:none; background:#0d1022; color:#dce1ff; border:1px solid #2b3156; padding:8px 10px; border-radius:8px; font-size:12px; box-shadow:0 6px 20px rgba(0,0,0,0.15); display:none; z-index: 10; }

    /* Q&A sections */
    .sect { margin-top: 22px; }
    .sect h2 { font-size: 16px; margin: 0 0 10px 0; font-weight: 600; color: #dce1ff; }
    .qcard { border-top: 1px solid #262b49; padding: 12px 0; }
    details.qd { background: #151a30; border: 1px solid #262b49; border-radius: 10px; margin: 10px 0; }
    details.qd summary { list-style: none; cursor: pointer; padding: 12px 14px; display:flex; align-items:center; gap:10px; }
    details.qd summary::-webkit-details-marker { display:none; }
    .qid { font: 600 13px/1 ui-sans-serif,system-ui; color:#b9c2ff; padding: 3px 8px; background:#202652; border-radius: 8px; border:1px solid #2e3867; }
    .scorechip { padding:2px 8px; border-radius: 999px; border:1px solid #2e375f; background:#22284a; color:#d8ddff; font-size:12px; }
    .score-ok { background:#173626; border-color:#245c3e; color:#98f2c9; }
    .score-warn { background:#3a341a; border-color:#6a5e2a; color:#ffe9a6; }
    .score-bad { background:#3a1a1a; border-color:#6a2a2a; color:#ffb0b0; }
    .muted { color: var(--muted); }
    .kv { display:grid; grid-template-columns: 140px 1fr; gap: 10px; padding: 10px 14px; border-top:1px solid #202545; }
    .kv .k { color:#9aa2c0; font-size:12px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:12px; white-space: pre-wrap; }
    .answer, .question, .just { padding: 10px 14px; border-top:1px solid #202545; }
    .gallery { padding: 10px 14px; border-top:1px solid #202545; display:none; }
    .gallery .thumbs { display:flex; flex-wrap:wrap; gap:10px; }
    .gallery img { width: 180px; max-height: 200px; object-fit: contain; background:#0d1022; border:1px solid #2b3156; border-radius:8px; padding:6px; }
    .toggle { margin-left:auto; }

    a, button { color: inherit; }
    /* Hide rejected QID details when excluding rejections */
    .hide-rejects details.qd.rejected { display: none; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Surgical Benchmark</h1>
      <div class="actions">
        <div class="meta">Questions: {{ total }} · Models: {{ models|length }} · Grader: {{ grader_name }}{% if total_empty > 0 %} · Empty answers: {{ total_empty }}{% endif %}</div>
        <button class="btn" id="themeToggle" type="button">Toggle Theme</button>
      </div>
    </header>

    <!-- Scores Chart Card -->
    <section class="card" id="chartCard">
      <div class="hd">
        <div class="controls">
          <strong id="chartTitle">All Questions Accounted (ranked)</strong>
          <div style="margin-left:12px; display:flex; gap:6px; align-items:center;">
            <button class="btn" id="mode-zeroed" type="button" title="Counts rejections as 0">All questions (rejects = 0)</button>
            <button class="btn" id="mode-score" type="button" title="Exclude rejected answers">Exclude rejections</button>
            <button class="btn" id="mode-reject" type="button" title="Show rejection percentage">Rejection percentage</button>
          </div>
        </div>
        <div class="muted" id="chartHint">Hover bars for details</div>
      </div>
      <div class="bd" id="chartWrap">
        <canvas id="scoreCanvas" width="1200" height="360"></canvas>
        <div class="tooltip" id="tip"></div>
      </div>
    </section>

    {% if total_empty > 0 %}
    <!-- Empty Answers Summary -->
    <section class="card" style="margin:12px 0;">
      <div class="hd">
        <strong>Empty Answers Summary</strong>
        <div class="muted">{{ total_empty }} empty answers not included in scoring</div>
      </div>
      <div class="bd">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
          {% for model, count in empty_stats.items() %}
            <div style="padding: 8px 12px; background: var(--panel-2); border-radius: 8px; border: 1px solid var(--grid);">
              <div style="font-weight: 600;">{{ model }}</div>
              <div style="color: var(--muted); font-size: 12px;">{{ count }} empty answer{{ 's' if count > 1 else '' }}</div>
            </div>
          {% endfor %}
        </div>
      </div>
    </section>
    {% endif %}

    <!-- Q&A Details -->
    <section class="sect">
      <h2>Per-Question Details</h2>
      {% for model_name, rows in rows_by_model.items() %}
      <div class="card" style="margin:12px 0;">
        <div class="hd">
          <div><strong>{{ model_name }}</strong> <span class="muted">Provider: {{ rows[0].provider }}</span></div>
          <div class="muted">Average score: {{ "%.3f"|format(model_avgs[model_name]) }}</div>
        </div>
        <div class="bd">
          {% for r in rows %}
            {% set bucket = 'score-ok' if r.score >= 0.7 else ('score-warn' if r.score >= 0.4 else 'score-bad') %}
            <details class="qd {{ 'rejected' if r.rejected else '' }}">
              <summary>
                <span class="qid">{{ r.qid }}</span>
                <span class="muted">on page {{ r.page_start }}–{{ r.page_end }}</span>
                {% if r.rejected %}
                  <span class="scorechip score-bad">Rejected</span>
                {% else %}
                  <span class="scorechip {{ bucket }}">Score: {{ "%.3f"|format(r.score) }}</span>
                {% endif %}
                {% if r.harmful %}<span class="scorechip score-bad">Harmful</span>{% endif %}
                {% if r.images and r.images|length > 0 %}
                  <button class="btn toggle" type="button" data-target="img-{{ r.model_slug }}-{{ r.qid|replace('.', '_') }}">Show {{ r.images|length }} image{{ 's' if r.images|length>1 else '' }}</button>
                {% endif %}
              </summary>
              <div class="question"><div class="k">Question</div><div class="mono">{{ r.question_text }}</div></div>
              {% if r.answer_text %}<div class="answer"><div class="k">Reference Answer</div><div class="mono">{{ r.answer_text }}</div></div>{% endif %}
              {% if r.rejected %}
                <div class="answer"><div class="k">Model Answer</div><div class="mono">∅ No answer (rejected)</div></div>
              {% else %}
                <div class="answer"><div class="k">Model Answer</div><div class="mono">{{ r.answer }}</div></div>
                <div class="just"><div class="k">Justification</div><div class="mono">{{ r.justification }}</div></div>
              {% endif %}
              {% if r.missed and r.missed|length>0 %}
                <div class="kv"><div class="k">Missed points</div><div>
                  <ul>
                    {% for m in r.missed %}<li class="mono">{{ m }}</li>{% endfor %}
                  </ul>
                </div></div>
              {% endif %}
              {% if r.images and r.images|length > 0 %}
                <div class="gallery" id="img-{{ r.model_slug }}-{{ r.qid|replace('.', '_') }}">
                  <div class="k">Images</div>
                  <div class="thumbs">
                    {% for im in r.images %}
                      <img data-src="{{ im.rel }}" data-alt="{{ im.abs }}" alt="{{ r.qid }} image {{ loop.index }}" loading="lazy" />
                    {% endfor %}
                  </div>
                </div>
              {% endif %}
              <div class="kv"><div class="k">Provider/Model</div><div>{{ r.provider }} / {{ r.model }}</div></div>
              <div class="kv"><div class="k">Grader</div><div>{{ r.grader }}</div></div>
            </details>
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    </section>

    <script id="report-data" type="application/json">{{ data_json | safe }}</script>
    <script>
      const DATA = JSON.parse(document.getElementById('report-data').textContent);
      const canvas = document.getElementById('scoreCanvas');
      const ctx = canvas.getContext('2d');
      const DPR = window.devicePixelRatio || 1;
      // scale for crisp lines on retina
      canvas.width = canvas.clientWidth * DPR;
      canvas.height = canvas.clientHeight * DPR;
      ctx.scale(DPR, DPR);

      const PADDING = {l: 180, r: 40, t: 20, b: 30};
      const W = canvas.clientWidth, H = canvas.clientHeight;
      const innerW = W - PADDING.l - PADDING.r;
      const innerH = H - PADDING.t - PADDING.b;

      const qids = DATA.meta.qids;
      const models = DATA.meta.models;
      const totalQuestions = DATA.meta.total_questions;
      const colorForIdx = (i) => {
        const hue = (i * 137.508) % 360; // golden angle spacing
        return `hsl(${hue}deg 70% 55%)`;
      };

      // Build ranked bars for each mode
      const barsScore = [...(DATA.bars_exclude || DATA.bars || [])];
      const barsZeroed = [...(DATA.bars_zeroed || [])];
      const barsReject = [...(DATA.bars_reject || [])];
      let mode = 'score';
      let bars = barsScore;
      const tip = document.getElementById('tip');

      function drawAxes() {
        ctx.clearRect(0,0,W,H);
        // grid background
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--panel-2') || '#f4f6ff';
        ctx.fillRect(PADDING.l, PADDING.t, innerW, innerH);
        // vertical grid lines and x labels 0..1
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--grid');
        for (let i=0;i<=5;i++) {
          const x = PADDING.l + innerW*(i/5);
          ctx.fillRect(x, PADDING.t, 1, innerH);
        }
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--muted');
        ctx.font = '12px system-ui, -apple-system, Segoe UI, Roboto, Arial';
        for (let i=0;i<=5;i++) {
          const x = PADDING.l + innerW*(i/5);
          const val = (i/5);
          const label = (mode === 'reject') ? Math.round(val*100) + '%' : val.toFixed(1);
          ctx.fillText(label, x-6, H-8);
        }
      }

      function drawPoints(progress=1) {
        // bars
        const rowH = Math.max(18, Math.min(40, innerH / Math.max(1,bars.length)));
        const gap = 8;
        const totalH = bars.length * (rowH + gap) - gap;
        const offsetY = PADDING.t + Math.max(0, (innerH - totalH)/2);
        for (let i=0;i<bars.length;i++) {
          const b = bars[i];
          const y = offsetY + i*(rowH+gap);
          const w = (b.avg) * innerW * progress;
          // draw bar first
          const color = colorForIdx(i);
          ctx.fillStyle = color;
          ctx.fillRect(PADDING.l, y, Math.max(2, w), rowH);
          // model label in left gutter, clipped to avoid overlap
          ctx.save();
          ctx.beginPath();
          ctx.rect(0, y, PADDING.l - 8, rowH);
          ctx.clip();
          ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text');
          ctx.fillText(b.model, 12, y + rowH*0.7, PADDING.l - 24);
          ctx.restore();
          // value chip
          const chipW = 60;
          ctx.fillStyle = '#0008';
          ctx.fillRect(PADDING.l + Math.max(2,w) - chipW, y, chipW, rowH);
          ctx.fillStyle = '#fff';
          const disp = (mode === 'reject') ? (b.avg*100).toFixed(1)+'%' : (b.avg).toFixed(3);
          ctx.fillText(disp, PADDING.l + Math.max(2,w) - chipW + 6, y + rowH*0.7);
          b._geom = {x:PADDING.l, y, w:(b.avg)*innerW, h:rowH};
        }
      }

      function render(progress=1) { drawAxes(); drawPoints(progress); }

      // initial animation
      let t0 = null;
      function animate(ts) {
        if (!t0) t0 = ts;
        const d = ts - t0; const p = Math.min(1, d/800);
        render(p);
        if (p < 1) requestAnimationFrame(animate);
      }
      requestAnimationFrame(animate);

      // tooltip interactions for bars
      canvas.addEventListener('mousemove', (ev) => {
        const rect = canvas.getBoundingClientRect(); const x = ev.clientX - rect.left; const y = ev.clientY - rect.top;
        let hit = null;
        for (const b of bars) {
          const g = b._geom; if (!g) continue;
          if (x >= g.x && x <= g.x + g.w && y >= g.y && y <= g.y + g.h) { hit = b; break; }
        }
        if (hit) {
          tip.style.display = 'block'; tip.style.left = (x + 12) + 'px'; tip.style.top = (y - 8) + 'px';
          if (mode === 'reject') {
            const rate = (hit.avg*100).toFixed(1)+'%';
            const ntot = hit.n_total ?? totalQuestions;
            tip.innerHTML = `<div><strong>${hit.model}</strong> <span class=\"muted\">(${hit.provider})</span></div><div>Rejections: <strong>${rate}</strong> (empty=${hit.n_reject||0}, total=${ntot})</div><div class=\"muted\">Higher is worse</div>`;
          } else if (mode === 'zeroed') {
            const ntot = hit.n_total ?? (hit.n + (hit.n_reject||0));
            tip.innerHTML = `<div><strong>${hit.model}</strong> <span class=\"muted\">(${hit.provider})</span></div><div>Avg (zeros for rejects): <strong>${hit.avg.toFixed(3)}</strong> (answered=${hit.n}, rejects=${hit.n_reject||0}, total=${ntot})</div>`;
          } else {
            tip.innerHTML = `<div><strong>${hit.model}</strong> <span class=\"muted\">(${hit.provider})</span></div><div>Average: <strong>${hit.avg.toFixed(3)}</strong> (answered=${hit.n})</div>`;
          }
        } else { tip.style.display = 'none'; }
      });
      canvas.addEventListener('mouseleave', () => { tip.style.display = 'none'; });

      // Mode toggle controls
      const titleEl = document.getElementById('chartTitle');
      const hintEl = document.getElementById('chartHint');
      function setActive(btnId) {
        for (const id of ['mode-score','mode-zeroed','mode-reject']) {
          const el = document.getElementById(id); if (!el) continue;
          if (id === btnId) el.classList.add('active'); else el.classList.remove('active');
        }
      }
      function setMode(newMode) {
        mode = newMode;
        if (mode === 'reject') {
          bars = barsReject;
          titleEl.textContent = 'Rejection Percentage (ranked)';
          hintEl.textContent = 'Higher is worse — hover for details';
          setActive('mode-reject');
          document.body.classList.remove('hide-rejects');
        } else if (mode === 'zeroed') {
          bars = barsZeroed;
          titleEl.textContent = 'All Questions Accounted (ranked)';
          hintEl.textContent = 'Counts rejections as 0 — hover for details';
          setActive('mode-zeroed');
          document.body.classList.remove('hide-rejects');
        } else {
          bars = barsScore;
          titleEl.textContent = 'Answered Only (ranked)';
          hintEl.textContent = 'Excludes rejections — hover for details';
          setActive('mode-score');
          document.body.classList.add('hide-rejects');
        }
        render(1);
      }
      document.getElementById('mode-score')?.addEventListener('click', () => setMode('score'));
      document.getElementById('mode-zeroed')?.addEventListener('click', () => setMode('zeroed'));
      document.getElementById('mode-reject')?.addEventListener('click', () => setMode('reject'));
      // Initialize default (All questions, rejects as 0)
      setMode('zeroed');

      // Images lazy-toggle with details-open and fallback path
      document.addEventListener('click', (e) => {
        const btn = e.target.closest('button.toggle'); if (!btn) return; e.preventDefault(); e.stopPropagation();
        const id = btn.getAttribute('data-target'); const panel = document.getElementById(id); if (!panel) return;
        const det = btn.closest('details'); if (det && !det.open) det.open = true;
        const wasHidden = getComputedStyle(panel).display === 'none'; panel.style.display = wasHidden ? 'block' : 'none';
        if (wasHidden) {
          for (const img of panel.querySelectorAll('img[data-src]')) {
            if (!img.src) {
              img.onerror = () => { if (img.dataset.alt) { img.onerror = null; img.src = img.dataset.alt; } };
              img.src = img.getAttribute('data-src');
            }
          }
          btn.textContent = 'Hide images';
        } else {
          const cnt = panel.querySelectorAll('img').length; btn.textContent = `Show ${cnt} image${cnt>1?'s':''}`;
        }
      });

      // Theme toggle with persistence
      const themeToggle = document.getElementById('themeToggle');
      const applyTheme = (t) => { document.documentElement.setAttribute('data-theme', t); localStorage.setItem('theme', t); };
      const initial = localStorage.getItem('theme') || 'light';
      applyTheme(initial);
      themeToggle && themeToggle.addEventListener('click', () => {
        const cur = document.documentElement.getAttribute('data-theme') || 'light';
        applyTheme(cur === 'light' ? 'dark' : 'light');
      });
    </script>

  </div>
</body>
</html>
"""

def _read_dataset(dataset_path: Path) -> Dict[str, Dict[str, Any]]:
    qmap: Dict[str, Dict[str, Any]] = {}
    if not dataset_path.exists():
        return qmap
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        try:
            obj = json.loads(line)
            qmap[obj["qid"]] = obj
        except Exception:
            continue
    return qmap

def _safe_list(val: Any) -> List[str]:
    if isinstance(val, list):
        return [str(x) for x in val]
    if val is None:
        return []
    try:
        out = ast.literal_eval(str(val))
        if isinstance(out, list):
            return [str(x) for x in out]
        return []
    except Exception:
        return []

def emit_report(csv_path: Path, html_path: Path, dataset_path: Optional[Path] = None, empty_stats_path: Optional[Path] = None):
    base = Path(csv_path)
    if base.is_dir():
        csv_files = sorted(base.glob("scores__*.csv"))
        if not csv_files:
            # backward compatibility
            legacy = base / "scores.csv"
            csv_files = [legacy] if legacy.exists() else []
        frames = []
        for fp in csv_files:
            try:
                frames.append(pd.read_csv(fp))
            except Exception:
                continue
        if frames:
            df = pd.concat(frames, ignore_index=True)
        else:
            df = pd.DataFrame(columns=["provider","model","qid","answer","grader","score","justification","missed","harmful"])
        base_dir = base
    else:
        df = pd.read_csv(base)
        base_dir = base.parent
    # If dataset path not provided, try default relative to CSVs dir
    if dataset_path is None:
        dataset_path = (base_dir.parent / "dataset.jsonl") if base_dir.name == "graded" else (base_dir / "dataset.jsonl")
    qmap = _read_dataset(dataset_path)

    # Load empty answer statistics if available
    empty_stats = {}  # model -> count
    empty_qids_by_model: Dict[str, Set[str]] = {}
    provider_for_model: Dict[str, str] = {}
    total_empty = 0
    if empty_stats_path:
        ep = Path(empty_stats_path)
        if ep.exists():
            files: List[Path]
            if ep.is_dir():
                files = sorted(ep.glob("empty_answers__*.csv"))
                if not files:
                    # backward compat
                    legacy = ep / "empty_answers.csv"
                    files = [legacy] if legacy.exists() else []
            else:
                files = [ep]
            for fp in files:
                try:
                    empty_df = pd.read_csv(fp)
                except Exception:
                    continue
                for _, row in empty_df.iterrows():
                    model = str(row.get("model", ""))
                    provider = str(row.get("provider", ""))
                    empty_stats[model] = empty_stats.get(model, 0) + 1
                    qid_val = str(row.get("qid", "")).strip()
                    if qid_val:
                        empty_qids_by_model.setdefault(model, set()).add(qid_val)
                    if model and provider and model not in provider_for_model:
                        provider_for_model[model] = provider
                    total_empty += 1

    # Resolve images relative path from HTML dir to images folder
    html_dir = html_path.parent
    images_dir = dataset_path.parent / "images"
    rel_images_base = os.path.relpath(images_dir, html_dir)

    # Prepare rows grouped by model with enriched question/answer data
    rows_by_model: Dict[str, List[Dict[str, Any]]] = {}
    sum_by_model: Dict[str, float] = {}
    provider_by_model: Dict[str, str] = {}
    for _, row in df.iterrows():
        qid = str(row["qid"])
        model = str(row["model"]) if "model" in row else ""
        provider = str(row.get("provider", ""))
        if model and provider and model not in provider_by_model:
            provider_by_model[model] = provider
        # Map CSV row to enriched record
        qi = qmap.get(qid, {})
        imgs = [str(x) for x in qi.get("images", [])]
        # Fix image paths and add absolute-like fallback
        fixed_imgs: List[Dict[str, str]] = []
        for p in imgs:
            base = os.path.basename(p)
            relp = str(Path(rel_images_base) / base)
            absp = "/out/images/" + base
            fixed_imgs.append({"rel": relp, "abs": absp})
        # harmful flag normalization
        hraw = row.get("harmful", False)
        if isinstance(hraw, float) and pd.isna(hraw):
            harmful = False
        elif isinstance(hraw, (bool, int)):
            harmful = bool(hraw)
        else:
            harmful = str(hraw).strip().lower() in ("1", "true", "yes", "y")

        model_slug = re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_") or "model"

        rec = {
            "provider": provider,
            "model": model,
            "qid": qid,
            "score": float(row.get("score", 0.0)),
            "justification": str(row.get("justification", "")),
            "answer": str(row.get("answer", "")),
            "grader": str(row.get("grader", "")),
            "harmful": harmful,
            "missed": _safe_list(row.get("missed", [])),
            "question_text": str(qi.get("question_text", "")),
            "answer_text": str(qi.get("answer_text", "")),
            "page_start": int(qi.get("page_start", 0) or 0),
            "page_end": int(qi.get("page_end", 0) or 0),
            "images": fixed_imgs,
            "model_slug": model_slug,
            "rejected": False,
        }
        rows_by_model.setdefault(model, []).append(rec)
        # aggregate
        sum_by_model[model] = sum_by_model.get(model, 0.0) + float(rec["score"])

    # Sort rows in each model by QID
    def _qid_key(q: str) -> Tuple[int, int, str]:
        m = re.match(r"Q(\d+)\.(\d+)", str(q))
        if m:
            return (int(m.group(1)), int(m.group(2)), str(q))
        return (999999, 999999, str(q))

    for m in rows_by_model:
        rows_by_model[m].sort(key=lambda r: _qid_key(r["qid"]))

    # Compute per-model averages and chart points
    model_avgs: Dict[str, float] = {}
    points: List[Dict[str, Any]] = []
    # Include models that only have empty answers
    models_from_empty = list(empty_stats.keys())
    # prefer provider from graded, else from empty stats
    for m, prov in provider_for_model.items():
        if m not in provider_by_model:
            provider_by_model[m] = prov
    models = sorted(set(list(rows_by_model.keys()) + models_from_empty))
    qids = sorted({r["qid"] for rows in rows_by_model.values() for r in rows} | set(qmap.keys()), key=_qid_key)
    for m, rows in rows_by_model.items():
        if rows:
            model_avgs[m] = sum(r["score"] for r in rows) / len(rows)
        else:
            model_avgs[m] = 0.0
        for r in rows:
            points.append({"model": m, "provider": r["provider"], "qid": r["qid"], "score": r["score"]})

    # Ranked bars: best to worst (exclude rejections)
    bars_exclude = sorted(
        (
            {
                "model": m,
                "provider": provider_by_model.get(m, (rows_by_model[m][0]["provider"] if rows_by_model.get(m) else "")),
                "avg": model_avgs.get(m, 0.0),
                "n": len(rows_by_model.get(m, [])),
            }
            for m in models
        ),
        key=lambda x: x["avg"], reverse=True
    )

    # Zeroed bars: count rejections as score 0
    bars_zeroed_raw = []
    for m in models:
        n_answered = len(rows_by_model.get(m, []))
        n_reject = int(empty_stats.get(m, 0))
        n_total = n_answered + n_reject
        total_score = sum_by_model.get(m, 0.0)
        avg_zeroed = (total_score / n_total) if n_total > 0 else 0.0
        bars_zeroed_raw.append({
            "model": m,
            "provider": provider_by_model.get(m, (rows_by_model[m][0]["provider"] if rows_by_model.get(m) else "")),
            "avg": avg_zeroed,
            "n": n_answered,
            "n_reject": n_reject,
            "n_total": n_total,
        })
    bars_zeroed = sorted(bars_zeroed_raw, key=lambda x: x["avg"], reverse=True)

    # Rejection bars: fraction rejected
    bars_reject_raw = []
    for m in models:
        n_answered = len(rows_by_model.get(m, []))
        n_reject = int(empty_stats.get(m, 0))
        n_total = n_answered + n_reject
        frac_reject = (n_reject / n_total) if n_total > 0 else 0.0
        bars_reject_raw.append({
            "model": m,
            "provider": provider_by_model.get(m, (rows_by_model[m][0]["provider"] if rows_by_model.get(m) else "")),
            "avg": frac_reject,
            "n": n_answered,
            "n_reject": n_reject,
            "n_total": n_total,
        })
    # Sort rejection from worst to best (higher first)
    bars_reject = sorted(bars_reject_raw, key=lambda x: x["avg"], reverse=True)

    data_json = json.dumps({
        "meta": {
            "qids": qids,
            "models": models,
            "total_questions": len(qids),
        },
        "points": points,
        "bars": bars_exclude,  # backward compat
        "bars_exclude": bars_exclude,
        "bars_zeroed": bars_zeroed,
        "bars_reject": bars_reject,
    })

    # Add rejected questions to per-model rows so the main view lists all questions.
    # These entries are tagged as rejected and hidden when excluding rejections.
    if empty_qids_by_model:
        for m in models:
            rej_qs = empty_qids_by_model.get(m, set())
            if not rej_qs:
                continue
            answered_qs = {r["qid"] for r in rows_by_model.get(m, [])}
            provider = provider_by_model.get(m, provider_for_model.get(m, ""))
            for qid in sorted(rej_qs - answered_qs, key=_qid_key):
                qi = qmap.get(qid, {})
                imgs = [str(x) for x in qi.get("images", [])]
                fixed_imgs: List[Dict[str, str]] = []
                for p in imgs:
                    base = os.path.basename(p)
                    relp = str(Path(rel_images_base) / base)
                    absp = "/out/images/" + base
                    fixed_imgs.append({"rel": relp, "abs": absp})
                model_slug = re.sub(r"[^a-zA-Z0-9]+", "_", m).strip("_") or "model"
                rec = {
                    "provider": provider,
                    "model": m,
                    "qid": qid,
                    "score": 0.0,
                    "justification": "",
                    "answer": "",
                    "grader": "",
                    "harmful": False,
                    "missed": [],
                    "question_text": str(qi.get("question_text", "")),
                    "answer_text": str(qi.get("answer_text", "")),
                    "page_start": int(qi.get("page_start", 0) or 0),
                    "page_end": int(qi.get("page_end", 0) or 0),
                    "images": fixed_imgs,
                    "model_slug": model_slug,
                    "rejected": True,
                }
                rows_by_model.setdefault(m, []).append(rec)
        # Resort rows to keep QIDs ordered
        for m in rows_by_model:
            rows_by_model[m].sort(key=lambda r: _qid_key(r["qid"]))
        # Ensure averages map has entries for any models added only via rejections
        for m in rows_by_model.keys():
            if m not in model_avgs:
                model_avgs[m] = 0.0

    # Determine grader name (if consistent)
    grader_name = ""
    if "grader" in df.columns and not df["grader"].isna().all():
        vals = [v for v in df["grader"].unique() if isinstance(v, str)]
        grader_name = vals[0] if vals else ""

    tpl = Template(HTML)
    html = tpl.render(
        total=len(qids),
        rows_by_model=rows_by_model,
        model_avgs=model_avgs,
        models=models,
        data_json=data_json,
        grader_name=grader_name,
        empty_stats=empty_stats,
        total_empty=total_empty,
    )
    html_path.write_text(html, encoding="utf-8")
