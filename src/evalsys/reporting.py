from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from jinja2 import Template
import json, ast, os, re

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Eval Report</title>
  <style>
    :root {
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
    body {
      margin: 0; padding: 24px; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, Noto Sans, "Apple Color Emoji", "Segoe UI Emoji";
      color: var(--text); background: radial-gradient(1200px 800px at 0% -10%, #182043 0%, var(--bg) 60%);
    }
    .container { max-width: 1200px; margin: 0 auto; }
    header { display:flex; align-items:center; justify-content:space-between; margin-bottom: 18px; }
    header h1 { font-size: 22px; font-weight: 700; margin: 0; letter-spacing: 0.3px; }
    header .meta { color: var(--muted); font-size: 13px; }

    .card { background: linear-gradient(180deg, var(--panel), var(--panel-2)); border: 1px solid #232845; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); overflow: hidden; }
    .card .hd { padding: 14px 16px; border-bottom: 1px solid #262b49; display:flex; align-items:center; justify-content:space-between; }
    .card .bd { padding: 16px; }

    /* Chart area */
    #chartWrap { position: relative; }
    #scoreCanvas { width: 100%; height: 280px; display:block; }
    .legend { display:flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
    .legend .item { display:flex; align-items:center; gap: 8px; padding: 6px 8px; background: var(--chip); color: var(--chip-text); border-radius: 999px; cursor: pointer; user-select: none; border: 1px solid #2e375f; }
    .legend .sw { width: 12px; height: 12px; border-radius: 3px; background: #999; border: 1px solid #0006; box-shadow: inset 0 0 0 1px #fff2; }
    .legend .avg { color: var(--muted); font-size: 12px; margin-left: 4px; }
    .controls { display:flex; gap:10px; align-items:center; }
    .btn { padding: 6px 10px; border-radius: 8px; border: 1px solid #2c3356; background: #22284a; color: #d8ddff; cursor: pointer; font-size: 12px; }
    .btn:hover { filter: brightness(1.1); }
    .tooltip { position: absolute; pointer-events:none; background:#0d1022; color:#dce1ff; border:1px solid #2b3156; padding:8px 10px; border-radius:8px; font-size:12px; box-shadow:0 6px 20px rgba(0,0,0,0.3); display:none; z-index: 10; }

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
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>AI Evaluation Report</h1>
      <div class="meta">Questions: {{ total }} · Models: {{ models|length }} · Grader: {{ grader_name }}</div>
    </header>

    <!-- Scores Chart Card -->
    <section class="card" id="chartCard">
      <div class="hd">
        <div class="controls">
          <strong>Scores by Model</strong>
          <button class="btn" id="toggleAll">Toggle All</button>
          <button class="btn" id="resetView">Reset</button>
        </div>
        <div class="muted">Hover points for details</div>
      </div>
      <div class="bd" id="chartWrap">
        <canvas id="scoreCanvas" width="1200" height="320"></canvas>
        <div class="legend" id="legend"></div>
        <div class="tooltip" id="tip"></div>
      </div>
    </section>

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
            <details class="qd">
              <summary>
                <span class="qid">{{ r.qid }}</span>
                <span class="muted">on page {{ r.page_start }}–{{ r.page_end }}</span>
                <span class="scorechip {{ bucket }}">Score: {{ "%.3f"|format(r.score) }}</span>
                {% if r.harmful %}<span class="scorechip score-bad">Harmful</span>{% endif %}
                {% if r.images and r.images|length > 0 %}
                  <button class="btn toggle" data-target="img-{{ r.qid|replace('.', '_') }}-{{ loop.index }}">Show {{ r.images|length }} image{{ 's' if r.images|length>1 else '' }}</button>
                {% endif %}
              </summary>
              <div class="question"><div class="k">Question</div><div class="mono">{{ r.question_text }}</div></div>
              {% if r.answer_text %}<div class="answer"><div class="k">Reference Answer</div><div class="mono">{{ r.answer_text }}</div></div>{% endif %}
              <div class="answer"><div class="k">Model Answer</div><div class="mono">{{ r.answer }}</div></div>
              <div class="just"><div class="k">Justification</div><div class="mono">{{ r.justification }}</div></div>
              {% if r.missed and r.missed|length>0 %}
                <div class="kv"><div class="k">Missed points</div><div>
                  <ul>
                    {% for m in r.missed %}<li class="mono">{{ m }}</li>{% endfor %}
                  </ul>
                </div></div>
              {% endif %}
              {% if r.images and r.images|length > 0 %}
                <div class="gallery" id="img-{{ r.qid|replace('.', '_') }}-{{ loop.index }}">
                  <div class="k">Images</div>
                  <div class="thumbs">
                    {% for im in r.images %}
                      <img data-src="{{ im }}" alt="{{ r.qid }} image {{ loop.index }}" loading="lazy" />
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

      const PADDING = {l: 44, r: 16, t: 18, b: 26};
      const W = canvas.clientWidth, H = canvas.clientHeight;
      const innerW = W - PADDING.l - PADDING.r;
      const innerH = H - PADDING.t - PADDING.b;

      const qids = DATA.meta.qids;
      const models = DATA.meta.models;
      const colorFor = (name) => {
        const i = models.indexOf(name);
        const hue = (i * 137.508) % 360; // golden angle spacing
        return `hsl(${hue}deg 70% 60%)`;
      };

      // Build series points per model
      const byModel = {};
      for (const pt of DATA.points) {
        if (!byModel[pt.model]) byModel[pt.model] = [];
        byModel[pt.model].push({ x: qids.indexOf(pt.qid), y: pt.score, qid: pt.qid, provider: pt.provider });
      }
      Object.keys(byModel).forEach(m => byModel[m].sort((a,b) => a.x - b.x));

      const state = { visible: Object.fromEntries(models.map(m => [m, true])) };

      const legend = document.getElementById('legend');
      const toggleAll = document.getElementById('toggleAll');
      const resetView = document.getElementById('resetView');
      const tip = document.getElementById('tip');

      function drawAxes() {
        ctx.clearRect(0,0,W,H);
        // grid
        ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--grid');
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let i=0;i<=5;i++) {
          const y = PADDING.t + innerH * (i/5);
          ctx.moveTo(PADDING.l, y);
          ctx.lineTo(W - PADDING.r, y);
        }
        ctx.stroke();
        // axes
        ctx.strokeStyle = '#3a4066';
        ctx.beginPath();
        ctx.moveTo(PADDING.l, PADDING.t);
        ctx.lineTo(PADDING.l, PADDING.t + innerH);
        ctx.lineTo(W - PADDING.r, PADDING.t + innerH);
        ctx.stroke();
        // y labels 0..1
        ctx.fillStyle = '#b5bcdf';
        ctx.font = '12px system-ui, -apple-system, Segoe UI, Roboto, Arial';
        for (let i=0;i<=5;i++) {
          const val = (1 - i/5).toFixed(1);
          const y = PADDING.t + innerH * (i/5) + 4;
          ctx.fillText(val, 6, y);
        }
      }

      function toXY(p) {
        const x = PADDING.l + (p.x / Math.max(1, qids.length-1)) * innerW;
        const y = PADDING.t + (1 - p.y) * innerH;
        return {x, y};
      }

      function drawPoints(progress=1) {
        for (const m of models) {
          if (!state.visible[m]) continue;
          const color = colorFor(m);
          // line
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          let started = false;
          for (const p of byModel[m]) {
            const {x, y} = toXY(p);
            const yA = PADDING.t + innerH; // start from zero for animation
            const yE = y;
            const yT = yA + (yE - yA) * progress;
            if (!started) { ctx.moveTo(x, yT); started = true; }
            else { ctx.lineTo(x, yT); }
          }
          ctx.stroke();
          // points
          ctx.fillStyle = color;
          for (const p of byModel[m]) {
            const {x, y} = toXY(p);
            const yA = PADDING.t + innerH;
            const yE = y;
            const yT = yA + (yE - yA) * progress;
            ctx.beginPath();
            ctx.arc(x, yT, 3.2, 0, Math.PI*2);
            ctx.fill();
            ctx.strokeStyle = '#0007';
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
      }

      function render(progress=1) {
        drawAxes();
        drawPoints(progress);
      }

      // initial animation
      let t0 = null;
      function animate(ts) {
        if (!t0) t0 = ts;
        const d = ts - t0;
        const p = Math.min(1, d / 800);
        render(p);
        if (p < 1) requestAnimationFrame(animate);
      }
      requestAnimationFrame(animate);

      // legend build
      function avgFor(m) {
        const arr = DATA.points.filter(p => p.model === m).map(p => p.score);
        return arr.length ? (arr.reduce((a,b)=>a+b,0)/arr.length) : 0;
      }
      function rebuildLegend() {
        legend.innerHTML = '';
        for (const m of models) {
          const el = document.createElement('div');
          el.className = 'item';
          el.dataset.model = m;
          const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = colorFor(m);
          const txt = document.createElement('span'); txt.textContent = m;
          const avg = document.createElement('span'); avg.className = 'avg'; avg.textContent = `avg ${avgFor(m).toFixed(3)}`;
          el.appendChild(sw); el.appendChild(txt); el.appendChild(avg);
          if (!state.visible[m]) el.style.opacity = 0.4;
          el.addEventListener('click', () => { state.visible[m] = !state.visible[m]; rebuildLegend(); render(1); });
          legend.appendChild(el);
        }
      }
      rebuildLegend();

      toggleAll.addEventListener('click', () => {
        const anyOn = Object.values(state.visible).some(v => v);
        for (const m of models) state.visible[m] = !anyOn;
        rebuildLegend(); render(1);
      });
      resetView.addEventListener('click', () => {
        for (const m of models) state.visible[m] = true;
        rebuildLegend(); requestAnimationFrame(animate); t0 = null;
      });

      // tooltip interactions
      canvas.addEventListener('mousemove', (ev) => {
        const rect = canvas.getBoundingClientRect();
        const x = (ev.clientX - rect.left);
        const y = (ev.clientY - rect.top);
        let best = null; let bestD = 9999;
        for (const m of models) {
          if (!state.visible[m]) continue;
          for (const p of byModel[m]) {
            const pt = toXY(p);
            const dx = (pt.x - x), dy = (pt.y - y);
            const d = Math.hypot(dx, dy);
            if (d < bestD && d < 14) { bestD = d; best = {m, ...p, px: pt.x, py: pt.y}; }
          }
        }
        if (best) {
          tip.style.display = 'block';
          tip.style.left = (best.px + 12) + 'px';
          tip.style.top = (best.py - 10) + 'px';
          tip.innerHTML = `<div><strong>${best.m}</strong> <span class="muted">(${best.provider})</span></div>
                           <div>QID: <strong>${best.qid}</strong></div>
                           <div>Score: <strong>${best.y.toFixed(3)}</strong></div>`;
        } else {
          tip.style.display = 'none';
        }
      });
      canvas.addEventListener('mouseleave', () => { tip.style.display = 'none'; });

      // Images lazy-toggle
      document.addEventListener('click', (e) => {
        const btn = e.target.closest('button.toggle');
        if (!btn) return;
        const id = btn.getAttribute('data-target');
        const panel = document.getElementById(id);
        if (!panel) return;
        const wasHidden = getComputedStyle(panel).display === 'none';
        panel.style.display = wasHidden ? 'block' : 'none';
        if (wasHidden) {
          // load images
          for (const img of panel.querySelectorAll('img[data-src]')) {
            if (!img.src) img.src = img.getAttribute('data-src');
          }
          btn.textContent = 'Hide images';
        } else {
          btn.textContent = btn.textContent.replace('Hide', 'Show');
        }
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

def emit_report(csv_path: Path, html_path: Path, dataset_path: Optional[Path] = None):
    df = pd.read_csv(csv_path)
    # If dataset path not provided, try default relative to CSV
    if dataset_path is None:
        dataset_path = (csv_path.parent.parent / "dataset.jsonl") if csv_path.parent.name == "graded" else (csv_path.parent / "dataset.jsonl")
    qmap = _read_dataset(dataset_path)

    # Resolve images relative path from HTML dir to images folder
    html_dir = html_path.parent
    images_dir = dataset_path.parent / "images"
    rel_images_base = os.path.relpath(images_dir, html_dir)

    # Prepare rows grouped by model with enriched question/answer data
    rows_by_model: Dict[str, List[Dict[str, Any]]] = {}
    for _, row in df.iterrows():
        qid = str(row["qid"])
        model = str(row["model"]) if "model" in row else ""
        provider = str(row.get("provider", ""))
        # Map CSV row to enriched record
        qi = qmap.get(qid, {})
        imgs = [str(x) for x in qi.get("images", [])]
        # Fix image paths to be relative to report location
        fixed_imgs: List[str] = []
        for p in imgs:
            base = os.path.basename(p)
            fixed = str(Path(rel_images_base) / base)
            fixed_imgs.append(fixed)
        # harmful flag normalization
        hraw = row.get("harmful", False)
        if isinstance(hraw, float) and pd.isna(hraw):
            harmful = False
        elif isinstance(hraw, (bool, int)):
            harmful = bool(hraw)
        else:
            harmful = str(hraw).strip().lower() in ("1", "true", "yes", "y")

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
        }
        rows_by_model.setdefault(model, []).append(rec)

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
    models = sorted(rows_by_model.keys())
    qids = sorted({r["qid"] for rows in rows_by_model.values() for r in rows}, key=_qid_key)
    for m, rows in rows_by_model.items():
        if rows:
            model_avgs[m] = sum(r["score"] for r in rows) / len(rows)
        else:
            model_avgs[m] = 0.0
        for r in rows:
            points.append({"model": m, "provider": r["provider"], "qid": r["qid"], "score": r["score"]})

    data_json = json.dumps({
        "meta": {
            "qids": qids,
            "models": models,
        },
        "points": points,
    })

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
    )
    html_path.write_text(html, encoding="utf-8")
