from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Set
from jinja2 import Template
import json, ast, os, re, copy, math
from collections import defaultdict, Counter
from itertools import combinations

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
    header { display:flex; align-items:center; justify-content:space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 10px; }
    header h1 { font-size: 22px; font-weight: 700; margin: 0; letter-spacing: 0.3px; }
    header .meta { color: var(--muted); font-size: 13px; }
    header .actions { display:flex; gap:8px; align-items:center; flex-wrap: wrap; }

    .card { background: linear-gradient(180deg, var(--panel), var(--panel-2)); border: 1px solid #232845; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); overflow: hidden; }
    .card .hd { padding: 14px 16px; border-bottom: 1px solid #262b49; display:flex; align-items:center; justify-content:space-between; gap:10px; }
    .card .bd { padding: 16px; }

    .card.note { border-style: dashed; background: var(--panel-2); }

    .controls { display:flex; gap:10px; align-items:center; flex-wrap: wrap; }
    .btn { padding: 6px 10px; border-radius: 8px; border: 1px solid #cfd6ff33; background: var(--chip); color: var(--chip-text); cursor: pointer; font-size: 12px; }
    .btn:hover { filter: brightness(1.03); }
    .btn.active { outline: 2px solid var(--accent); }
    select, option { font-size: 12px; padding: 6px 10px; border-radius: 8px; background: var(--panel-2); color: var(--text); border:1px solid #2b3156; }

    #chartWrap { position: relative; }
    #scoreCanvas { width: 100%; height: 360px; display:block; }
    .tooltip { position: absolute; pointer-events:none; background:#0d1022; color:#dce1ff; border:1px solid #2b3156; padding:8px 10px; border-radius:8px; font-size:12px; box-shadow:0 6px 20px rgba(0,0,0,0.15); display:none; z-index: 10; }

    .sect { margin-top: 22px; }
    .sect h2 { font-size: 16px; margin: 0 0 10px 0; font-weight: 600; color: #dce1ff; }

    details.mcard { border: 1px solid #262b49; border-radius: 12px; margin: 12px 0; background: #151a30; }
    details.mcard > summary { list-style:none; cursor:pointer; padding: 12px 14px; display:flex; align-items:center; justify-content:space-between; gap:10px; }
    details.mcard > summary::-webkit-details-marker { display:none; }
    .hdr-left { display:flex; gap:8px; align-items:center; }
    .model-name { font-weight: 700; }
    .muted { color: var(--muted); }
    .avg-badge { padding: 4px 8px; border-radius: 999px; background:#1a2145; border: 1px solid #2e3867; font-size: 12px; color:#c8d2ff; }

    details.qd { background: #151a30; border: 1px solid #262b49; border-radius: 10px; margin: 10px 0; }
    details.qd summary { list-style: none; cursor: pointer; padding: 12px 14px; display:flex; align-items:center; gap:10px; }
    details.qd summary::-webkit-details-marker { display:none; }
    .qid { font: 600 13px/1 ui-sans-serif,system-ui; color:#b9c2ff; padding: 3px 8px; background:#202652; border-radius: 8px; border:1px solid #2e3867; }
    .cat { font: 600 11px/1 ui-sans-serif,system-ui; color:#a7f3d0; padding: 3px 6px; background:#0f2e26; border-radius: 8px; border:1px solid #1d4b41; }
    .scorechip { padding:2px 8px; border-radius: 999px; border:1px solid #2e375f; background:#22284a; color:#d8ddff; font-size:12px; }
    .score-ok { background:#173626; border-color:#245c3e; color:#98f2c9; }
    .score-warn { background:#3a341a; border-color:#6a5e2a; color:#ffe9a6; }
    .score-bad { background:#3a1a1a; border-color:#6a2a2a; color:#ffb0b0; }

    .kv { display:grid; grid-template-columns: 140px 1fr; gap: 10px; padding: 10px 14px; border-top:1px solid #202545; }
    .kv .k { color:#9aa2c0; font-size:12px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:12px; white-space: pre-wrap; }
    .answer, .question, .just { padding: 10px 14px; border-top:1px solid #202545; }
    .gallery { padding: 10px 14px; border-top:1px solid #202545; display:none; }
    .gallery .thumbs { display:flex; flex-wrap:wrap; gap:10px; }
    .gallery img { width: 180px; max-height: 200px; object-fit: contain; background:#0d1022; border:1px solid #2b3156; border-radius:8px; padding:6px; }
    .toggle { margin-left:auto; }

    a, button { color: inherit; }

    table.cat { width: 100%; border-collapse: collapse; }
    table.cat th, table.cat td { border-bottom: 1px solid #262b49; padding: 8px 10px; text-align: left; font-size: 12px; }
    table.cat tbody tr { border-left: 4px solid transparent; transition: background 0.25s ease, border-color 0.25s ease, color 0.25s ease, filter 0.2s ease; }
    table.cat tbody tr td { transition: color 0.25s ease; }
    table.cat tbody tr:hover { filter: brightness(1.05); }

    .empty-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
    .empty-card { padding: 8px 12px; background: var(--panel-2); border-radius: 8px; border: 1px solid var(--grid); }

    .view-block { width: 100%; }

    .comparison-controls { display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin-bottom:12px; }
    .comparison-controls label { display:flex; align-items:center; gap:6px; font-size:12px; color: var(--muted); }
    .comparison-controls input[type="range"] { width: 180px; }
    .comparison-results { margin-top: 8px; }
    .comparison-results details { background: #151a30; border: 1px solid #262b49; border-radius: 10px; margin-bottom: 12px; }
    .comparison-results details:last-child { margin-bottom: 0; }
    .comparison-results summary { list-style: none; cursor: pointer; padding: 12px 14px; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
    .comparison-results summary::-webkit-details-marker { display:none; }
    .comparison-body { padding: 0 14px 14px 14px; }
    .comparison-body .comp-question { margin-bottom: 12px; }
    .comp-text { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:12px; white-space: pre-wrap; background:#11152b; border:1px solid #202545; border-radius:8px; padding:8px; color:#d8ddff; }
    .comp-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:12px; }
    .comp-side { border:1px solid #202545; border-radius:8px; background:#161c33; padding:10px; }
    .comp-side h4 { margin:0 0 6px 0; font-size:13px; color:#dce1ff; }
    .comp-meta { font-size:12px; color: var(--muted); margin-bottom:6px; }
    .comp-meta strong { color: var(--text); }
    .comp-empty { font-size:12px; color: var(--muted); padding:12px 0; }
    .diff-chip { padding:3px 8px; border-radius:999px; background:#3a1a1a; border:1px solid #6a2a2a; color:#ffb0b0; font-size:12px; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Surgical Benchmark</h1>
      <div class="actions">
        <div class="meta">Questions: {{ total }} · Models: {{ models|length }} · Grader: <span id="metaGrader">{{ default_view.label }}</span><span id="metaEmpty">{% if default_view.total_empty > 0 %} · Empty answers: {{ default_view.total_empty }}{% endif %}</span></div>
        <label style="display:flex; align-items:center; gap:6px;">
          <span class="muted">Grader</span>
          <select id="graderSelect">
            {% for view in views %}
              <option value="{{ view.id }}" {% if view.active %}selected{% endif %}>{{ view.label }}</option>
            {% endfor %}
          </select>
        </label>
        <label style="display:flex; align-items:center; gap:6px;">
          <span class="muted">Category</span>
          <select id="categorySelect">
            <option value="">All</option>
            {% for cat in category_options %}
              <option value="{{ cat.id }}">{{ cat.id }} · {{ cat.name }}</option>
            {% endfor %}
          </select>
        </label>
        <button class="btn" id="expandAll" type="button">Expand All</button>
        <button class="btn" id="collapseAll" type="button">Collapse All</button>
        <button class="btn" id="themeToggle" type="button">Toggle Theme</button>
      </div>
    </header>

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

    {% if show_empty_section %}
    <section class="card" id="emptySummary">
      <div class="hd">
        <strong>Empty Answers Summary</strong>
        <div class="muted">Empty submissions tracked per grader</div>
      </div>
      <div class="bd">
        {% for view in views %}
          <div class="view-block" data-grader-view="{{ view.id }}" data-section="empty" {% if not view.active %}style="display:none"{% endif %}>
            {% if view.total_empty > 0 %}
              <div class="empty-grid">
                {% for model, count in view.empty_stats|dictsort %}
                  <div class="empty-card">
                    <div style="font-weight: 600;">{{ model }}</div>
                    <div class="muted">{{ count }} empty answer{{ 's' if count != 1 else '' }}</div>
                  </div>
                {% endfor %}
              </div>
            {% else %}
              <div class="muted">No empty answers recorded for this grader.</div>
            {% endif %}
          </div>
        {% endfor %}
      </div>
    </section>
    {% endif %}

    <section class="card" id="categoryCard" style="margin:12px 0;">
      <div class="hd">
        <strong>By Category</strong>
        <div class="muted">Averages per category (answered-only and zeroed)</div>
      </div>
      <div class="bd">
        {% for view in views %}
          <div class="view-block" data-grader-view="{{ view.id }}" data-section="categories" {% if not view.active %}style="display:none"{% endif %}>
            {% if view.categories %}
              {% for cat in view.categories %}
                <details class="qd">
                  <summary>
                    <span class="qid">{{ "Q" ~ cat.id ~ ".x" }}</span>
                    <span class="cat">{{ cat.name }}</span>
                    <span class="muted">Questions: {{ cat.total_qs }}</span>
                  </summary>
                  <div class="answer">
                    <table class="cat">
                      <thead>
                        <tr><th>Model</th><th>Provider</th><th>Avg (answered)</th><th>Avg (zeroed)</th><th>Answered</th><th>Rejects</th><th>Total</th></tr>
                      </thead>
                      <tbody>
                      {% for row in cat.model_rows %}
                        <tr data-score="{{ "%.4f"|format(row.avg_zeroed) }}">
                          <td>{{ row.model }}</td>
                          <td class="muted">{{ row.provider }}</td>
                          <td>{{ "%.3f"|format(row.avg_answered) }}</td>
                          <td>{{ "%.3f"|format(row.avg_zeroed) }}</td>
                          <td>{{ row.n_answered }}</td>
                          <td>{{ row.n_reject }}</td>
                          <td>{{ row.n_total }}</td>
                        </tr>
                      {% endfor %}
                      </tbody>
                    </table>
                  </div>
                </details>
              {% endfor %}
            {% else %}
              <div class="muted">No category statistics for this grader yet.</div>
            {% endif %}
          </div>
        {% endfor %}
      </div>
    </section>

    <section class="sect">
      <h2>Per-Question Details</h2>
      {% for view in views %}
        <div class="view-block" data-grader-view="{{ view.id }}" data-section="questions" {% if not view.active %}style="display:none"{% endif %}>
          {% if view.is_all %}
            <div class="card note">
              <div class="bd">
                <p>This view shows averages across all graders ({{ view.source_graders|join(', ') }}).</p>
                <p class="muted">Select a specific grader from the dropdown above to inspect model answers and rationales.</p>
              </div>
            </div>
            {% if has_comparisons %}
            <div class="card" id="comparisonCard">
              <div class="hd">
                <strong>Grader Comparison</strong>
                <div class="muted">Highlight questions where graders disagree</div>
              </div>
              <div class="bd">
                <div class="comparison-controls">
                  <label>
                    <span class="muted">Grader pair</span>
                    <select id="comparisonPair"></select>
                  </label>
                  <label>
                    <span class="muted">Score gap ≥</span>
                    <span id="comparisonValue">0.20</span>
                  </label>
                  <input type="range" id="comparisonSlider" min="0" max="1" step="0.01" value="0.20">
                  <button class="btn" type="button" id="comparisonSortToggle">Sort by model</button>
                </div>
                <div id="comparisonResults" class="comparison-results"></div>
              </div>
            </div>
            {% endif %}
          {% elif view.model_order %}
            {% for model_name in view.model_order %}
              {% set rows = view.rows_by_model.get(model_name, []) %}
              {% if rows %}
              <details class="mcard">
                <summary>
                  <div class="hdr-left">
                    <span class="model-name">{{ model_name }}</span>
                    <span class="muted">Provider: {{ view.provider_by_model.get(model_name, "") }}</span>
                  </div>
                  <span class="avg-badge">Average: {{ "%.3f"|format(view.model_avgs.get(model_name, 0.0)) }}</span>
                </summary>
                <div class="bd">
                  {% for r in rows %}
                    {% set bucket = 'score-ok' if r.score >= 0.7 else ('score-warn' if r.score >= 0.4 else 'score-bad') %}
                    <details class="qd {{ 'rejected' if r.rejected else '' }}" data-cat="{{ r.category_id }}">
                      <summary>
                        <span class="qid">{{ r.qid }}</span>
                        <span class="cat">{{ r.category_name }}</span>
                        <span class="muted">page {{ r.page_start }}–{{ r.page_end }}</span>
                        {% if r.rejected %}
                          <span class="scorechip score-bad">Rejected{% if r.rejection_count and r.rejection_count > 1 %} × {{ r.rejection_count }}{% endif %}</span>
                        {% else %}
                          <span class="scorechip {{ bucket }}">Score: {{ "%.3f"|format(r.score) }}</span>
                        {% endif %}
                        {% if r.harmful %}<span class="scorechip score-bad">Harmful</span>{% endif %}
                        {% if r.images and r.images|length > 0 %}
                          <button class="btn toggle" type="button" data-target="img-{{ view.id }}-{{ r.model_slug }}-{{ r.qid|replace('.', '_') }}">Show {{ r.images|length }} image{{ 's' if r.images|length>1 else '' }}</button>
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
                        <div class="gallery" id="img-{{ view.id }}-{{ r.model_slug }}-{{ r.qid|replace('.', '_') }}">
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
              </details>
              {% endif %}
            {% endfor %}
          {% else %}
            <div class="card note">
              <div class="bd">
                <p class="muted">No graded questions available for this grader yet.</p>
              </div>
            </div>
          {% endif %}
        </div>
      {% endfor %}
    </section>

    <script id="report-data" type="application/json">{{ data_json | safe }}</script>

    <script>
      const DATA = JSON.parse(document.getElementById('report-data').textContent);
      const canvas = document.getElementById('scoreCanvas');
      const ctx = canvas.getContext('2d');
      const DPR = window.devicePixelRatio || 1;
      canvas.width = canvas.clientWidth * DPR;
      canvas.height = canvas.clientHeight * DPR;
      ctx.scale(DPR, DPR);

      const PADDING = {l: 180, r: 40, t: 20, b: 30};
      const W = canvas.clientWidth, H = canvas.clientHeight;
      const innerW = W - PADDING.l - PADDING.r;
      const innerH = H - PADDING.t - PADDING.b;

      const categories = DATA.meta.categories || [];
      const GRADERS = DATA.graders || {};
      const COMPARISON_PAIRS = (DATA.comparisons && DATA.comparisons.pairs) || [];
      const ORDER = DATA.order || Object.keys(GRADERS);
      let currentGrader = DATA.default || (ORDER.length ? ORDER[0] : null);
      let currentCat = '';
      let mode = 'zeroed';

      let barsScore = [];
      let barsZeroed = [];
      let barsReject = [];

      const tip = document.getElementById('tip');
      const graderSelect = document.getElementById('graderSelect');
      const catSelect = document.getElementById('categorySelect');
      const titleEl = document.getElementById('chartTitle');
      const hintEl = document.getElementById('chartHint');
      const metaGraderEl = document.getElementById('metaGrader');
      const metaEmptyEl = document.getElementById('metaEmpty');
      const comparisonCard = document.getElementById('comparisonCard');
      const comparisonPairSelect = document.getElementById('comparisonPair');
      const comparisonSlider = document.getElementById('comparisonSlider');
      const comparisonValue = document.getElementById('comparisonValue');
      const comparisonResults = document.getElementById('comparisonResults');
      const comparisonSortToggle = document.getElementById('comparisonSortToggle');
      let comparisonSortMode = 'qid';

      const colorForIdx = (i) => {
        const hue = (i * 137.508) % 360;
        return `hsl(${hue}deg 70% 55%)`;
      };

      const escapeHtml = (value) => {
        if (value === null || value === undefined) return '';
        return String(value)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#39;');
      };

      const sanitizeId = (value) => (
        (value || '')
          .toString()
          .replace(/[^a-zA-Z0-9_-]+/g, '_')
      );

      const qidKey = (qid) => {
        if (!qid) return [Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER];
        const match = /Q(\d+)\.(\d+)/i.exec(qid);
        if (!match) return [Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER];
        return [parseInt(match[1], 10) || 0, parseInt(match[2], 10) || 0];
      };

      function resolveGrader(id) {
        if (id && GRADERS[id]) return id;
        for (const key of ORDER) {
          if (GRADERS[key]) return key;
        }
        const keys = Object.keys(GRADERS);
        return keys.length ? keys[0] : null;
      }

      function drawAxes() {
        ctx.clearRect(0, 0, W, H);
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--panel-2') || '#f4f6ff';
        ctx.fillRect(PADDING.l, PADDING.t, innerW, innerH);
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
        const bars = (mode === 'reject') ? barsReject : (mode === 'zeroed' ? barsZeroed : barsScore);
        if (!bars.length) {
          return;
        }
        const rowH = Math.max(18, Math.min(40, innerH / bars.length));
        const gap = 8;
        const totalH = bars.length * (rowH + gap) - gap;
        const offsetY = PADDING.t + Math.max(0, (innerH - totalH)/2);
        bars.forEach((b, i) => {
          const y = offsetY + i*(rowH+gap);
          const w = Math.max(0, b.avg) * innerW * progress;
          const color = colorForIdx(i);
          ctx.fillStyle = color;
          ctx.fillRect(PADDING.l, y, Math.max(2, w), rowH);
          ctx.save();
          ctx.beginPath();
          ctx.rect(0, y, PADDING.l - 8, rowH);
          ctx.clip();
          ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text');
          ctx.fillText(b.model, 12, y + rowH*0.7, PADDING.l - 24);
          ctx.restore();
          const chipW = 60;
          ctx.fillStyle = '#0008';
          ctx.fillRect(PADDING.l + Math.max(2,w) - chipW, y, chipW, rowH);
          ctx.fillStyle = '#fff';
          const disp = (mode === 'reject') ? (b.avg*100).toFixed(1)+'%' : (b.avg).toFixed(3);
          ctx.fillText(disp, PADDING.l + Math.max(2,w) - chipW + 6, y + rowH*0.7);
          b._geom = {x:PADDING.l, y, w:(Math.max(0, b.avg))*innerW, h:rowH};
        });
      }

      function render(progress=1) {
        drawAxes();
        drawPoints(progress);
      }

      let animStart = null;
      function animateBars(ts) {
        if (animStart === null) animStart = ts;
        const d = ts - animStart;
        const p = Math.min(1, d/800);
        render(p);
        if (p < 1) requestAnimationFrame(animateBars);
      }

      function scoreToPalette(score) {
        const s = Math.min(1, Math.max(0, Number.isFinite(score) ? score : 0));
        const sat = 82;
        let hue;
        if (s <= 0.5) {
          const t = s / 0.5;
          hue = 0 + (50 * t);
        } else {
          const t = (s - 0.5) / 0.5;
          hue = 50 + (75 * t);
        }
        const light = (18 + s * 35);
        const borderLight = Math.min(78, light + 18);
        const alpha = (0.22 + s * 0.18).toFixed(2);
        const bg = `hsla(${hue.toFixed(1)}, ${sat}%, ${light.toFixed(0)}%, ${alpha})`;
        const border = `hsl(${hue.toFixed(1)}, ${sat + 4}%, ${borderLight.toFixed(0)}%)`;
        const text = light < 40 ? '#f5f6ff' : '';
        const muted = light < 40 ? '#d8ddff' : '';
        return { bg, border, text, muted };
      }

      function refreshCategoryColorsFor(viewId) {
        const scope = document.querySelector(`[data-grader-view="${viewId}"][data-section="categories"]`);
        if (!scope) return;
        scope.querySelectorAll('table.cat tbody tr[data-score]').forEach((row) => {
          const score = parseFloat(row.dataset.score || '0');
          if (!Number.isFinite(score)) return;
          const palette = scoreToPalette(score);
          row.style.background = palette.bg;
          row.style.borderLeftColor = palette.border;
          const cells = row.querySelectorAll('td');
          if (palette.text) {
            row.style.color = palette.text;
            cells.forEach((cell, idx) => {
              cell.style.color = (idx === 1 && palette.muted) ? palette.muted : palette.text;
            });
          } else {
            row.style.removeProperty('color');
            cells.forEach((cell) => cell.style.removeProperty('color'));
          }
        });
      }

      function updateBarsForSelection() {
        const gData = GRADERS[currentGrader] || {};
        let base = gData;
        if (currentCat && gData.cat_bars && gData.cat_bars[currentCat]) {
          base = gData.cat_bars[currentCat];
        }
        barsScore = (base.bars_exclude || base.exclude || base.bars || []).map((b) => ({...b}));
        barsZeroed = (base.bars_zeroed || base.zeroed || []).map((b) => ({...b}));
        barsReject = (base.bars_reject || base.reject || []).map((b) => ({...b}));
      }

      function updateMeta() {
        const gData = GRADERS[currentGrader] || {};
        if (metaGraderEl && gData.label) metaGraderEl.textContent = gData.label;
        if (metaEmptyEl) {
          if (gData.total_empty && gData.total_empty > 0) {
            metaEmptyEl.textContent = ` · Empty answers: ${gData.total_empty}`;
          } else {
            metaEmptyEl.textContent = '';
          }
        }
      }

      function setViewVisibility(graderId) {
        document.querySelectorAll('[data-grader-view]').forEach((el) => {
          if (el.dataset.graderView === graderId) {
            el.style.display = '';
          } else {
            el.style.display = 'none';
          }
        });
      }

      function updateQuestionVisibility() {
        const scope = document.querySelector(`[data-grader-view="${currentGrader}"][data-section="questions"]`);
        if (!scope) return;
        const blocks = scope.querySelectorAll('details.qd[data-cat]');
        blocks.forEach((el) => {
          const cat = el.getAttribute('data-cat');
          if (!currentCat || !cat) {
            el.style.display = '';
          } else {
            el.style.display = (cat === currentCat) ? '' : 'none';
          }
        });
      }

      function applyCategory(catId, animate=true) {
        currentCat = catId || '';
        updateBarsForSelection();
        if (!currentCat) {
          titleEl.textContent = 'All Questions Accounted (ranked)';
        } else {
          const found = categories.find((c) => c.id === currentCat);
          titleEl.textContent = `Category ${currentCat}${found ? ' · ' + found.name : ''}`;
        }
        if (mode === 'reject') {
          hintEl.textContent = 'Higher is worse — hover for details';
        } else if (mode === 'zeroed') {
          hintEl.textContent = 'Counts rejections as 0 — hover for details';
        } else {
          hintEl.textContent = 'Excludes rejections — hover for details';
        }
        updateQuestionVisibility();
        if (animate) {
          animStart = null;
          requestAnimationFrame(animateBars);
        } else {
          render(1);
        }
        refreshCategoryColorsFor(currentGrader);
      }

      function setActive(btnId) {
        ['mode-score','mode-zeroed','mode-reject'].forEach((id) => {
          const el = document.getElementById(id);
          if (!el) return;
          if (id === btnId) el.classList.add('active'); else el.classList.remove('active');
        });
      }

      function setMode(newMode) {
        mode = newMode;
        setActive('mode-' + newMode);
        applyCategory(currentCat, false);
      }

      function setGrader(graderId) {
        const resolved = resolveGrader(graderId);
        if (!resolved) {
          currentGrader = null;
          barsScore = [];
          barsZeroed = [];
          barsReject = [];
          render(1);
          return;
        }
        currentGrader = resolved;
        if (graderSelect && graderSelect.value !== resolved) {
          graderSelect.value = resolved;
        }
        updateMeta();
        setViewVisibility(currentGrader);
        const gData = GRADERS[currentGrader] || {};
        if (currentCat && !(gData.cat_bars && gData.cat_bars[currentCat])) {
          currentCat = '';
          if (catSelect) catSelect.value = '';
        }
        setActive('mode-' + mode);
        applyCategory(currentCat, false);
      }

      canvas.addEventListener('mousemove', (ev) => {
        const rect = canvas.getBoundingClientRect(); const x = ev.clientX - rect.left; const y = ev.clientY - rect.top;
        const bars = (mode === 'reject') ? barsReject : (mode === 'zeroed' ? barsZeroed : barsScore);
        let hit = null;
        for (const b of bars) {
          const g = b._geom; if (!g) continue;
          if (x >= g.x && x <= g.x + g.w && y >= g.y && y <= g.y + g.h) { hit = b; break; }
        }
        if (hit) {
          tip.style.display = 'block'; tip.style.left = (x + 12) + 'px'; tip.style.top = (y - 8) + 'px';
          if (mode === 'reject') {
            const rate = (hit.avg*100).toFixed(1)+'%';
            const ntot = hit.n_total ?? (hit.n + (hit.n_reject||0));
            tip.innerHTML = `<div><strong>${hit.model}</strong> <span class="muted">(${hit.provider || ''})</span></div><div>Rejections: <strong>${rate}</strong> (empty=${hit.n_reject||0}, total=${ntot||0})</div><div class="muted">Higher is worse</div>`;
          } else if (mode === 'zeroed') {
            const ntot = hit.n_total ?? (hit.n + (hit.n_reject||0));
            tip.innerHTML = `<div><strong>${hit.model}</strong> <span class="muted">(${hit.provider || ''})</span></div><div>Avg (zeros for rejects): <strong>${hit.avg.toFixed(3)}</strong> (answered=${hit.n||0}, rejects=${hit.n_reject||0}, total=${ntot||0})</div>`;
          } else {
            tip.innerHTML = `<div><strong>${hit.model}</strong> <span class="muted">(${hit.provider || ''})</span></div><div>Average: <strong>${hit.avg.toFixed(3)}</strong> (answered=${hit.n||0})</div>`;
          }
        } else { tip.style.display = 'none'; }
      });
      canvas.addEventListener('mouseleave', () => { tip.style.display = 'none'; });

      document.getElementById('mode-score')?.addEventListener('click', () => setMode('score'));
      document.getElementById('mode-zeroed')?.addEventListener('click', () => setMode('zeroed'));
      document.getElementById('mode-reject')?.addEventListener('click', () => setMode('reject'));

      graderSelect?.addEventListener('change', (e) => setGrader(e.target.value));
      catSelect?.addEventListener('change', (e) => applyCategory(e.target.value, true));

      function toggleImages(e) {
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
      }
      document.addEventListener('click', toggleImages);

      const themeToggle = document.getElementById('themeToggle');
      const applyTheme = (t) => { document.documentElement.setAttribute('data-theme', t); localStorage.setItem('theme', t); };
      const initialTheme = localStorage.getItem('theme') || 'light';
      applyTheme(initialTheme);
      themeToggle && themeToggle.addEventListener('click', () => {
        const cur = document.documentElement.getAttribute('data-theme') || 'light';
        applyTheme(cur === 'light' ? 'dark' : 'light');
      });

      const expandAll = document.getElementById('expandAll');
      const collapseAll = document.getElementById('collapseAll');
      expandAll?.addEventListener('click', () => {
        const scope = document.querySelector(`[data-grader-view="${currentGrader}"][data-section="questions"]`);
        scope?.querySelectorAll('details.mcard').forEach((d) => d.open = true);
      });
      collapseAll?.addEventListener('click', () => {
        const scope = document.querySelector(`[data-grader-view="${currentGrader}"][data-section="questions"]`);
        scope?.querySelectorAll('details.mcard').forEach((d) => d.open = false);
      });

      function renderComparisonSide(sideData, baseId, suffix) {
        const rec = sideData?.record || {};
        const score = Number(rec.score || 0);
        const rejected = !!rec.rejected;
        const harmful = !!rec.harmful;
        let status = rejected ? `Rejected${rec.rejection_count && rec.rejection_count > 1 ? ` × ${rec.rejection_count}` : ''}` : 'Answered';
        if (harmful) {
          status += rejected ? ', Harmful' : ' (harmful)';
        }
        const showImages = Array.isArray(rec.images) && rec.images.length > 0;
        const galleryId = `${baseId}-${suffix}-gallery`;
        const imageBtn = showImages ? `<button class="btn toggle" type="button" data-target="${galleryId}">Show ${rec.images.length} image${rec.images.length > 1 ? 's' : ''}</button>` : '';
        const imagesHtml = showImages ? `<div class="gallery" id="${galleryId}"><div class="k">Images</div><div class="thumbs">${rec.images.map((img, idx) => `<img data-src="${escapeHtml(img.rel || '')}" data-alt="${escapeHtml(img.abs || '')}" alt="${escapeHtml(rec.qid || rec.model || '')} image ${idx + 1}" loading="lazy" />`).join('')}</div></div>` : '';
        const missed = Array.isArray(rec.missed) && rec.missed.length > 0
          ? `<div class="comp-meta"><strong>Missed points</strong></div><ul class="mono">${rec.missed.map((m) => `<li>${escapeHtml(m)}</li>`).join('')}</ul>`
          : '';
        const answerBlock = rejected
          ? `<div class="comp-meta"><strong>Model Answer</strong></div><div class="comp-text">∅ No answer (rejected)</div>`
          : `<div class="comp-meta"><strong>Model Answer</strong></div><div class="comp-text">${escapeHtml(rec.answer || '')}</div><div class="comp-meta"><strong>Justification</strong></div><div class="comp-text">${escapeHtml(rec.justification || '')}</div>`;
        return `
          <div class="comp-side">
            <h4>${escapeHtml(sideData?.label || '')}</h4>
            <div class="comp-meta"><strong>Score:</strong> ${score.toFixed(3)}</div>
            <div class="comp-meta"><strong>Status:</strong> ${escapeHtml(status)}</div>
            ${imageBtn}
            ${answerBlock}
            ${missed}
            ${imagesHtml}
          </div>
        `;
      }

      function renderComparisonEntry(pair, entry, index) {
        const pairId = sanitizeId(pair.id || `${pair.first.view}-${pair.second.view}`);
        const baseId = sanitizeId(`${pairId}-${entry.model}-${entry.qid}-${index}`);
        const diffLabel = Number(entry.diff || 0).toFixed(3);
        const questionText = entry.question_text ? `<div class="comp-meta"><strong>Question</strong></div><div class="comp-text">${escapeHtml(entry.question_text)}</div>` : '';
        const referenceText = entry.answer_text ? `<div class="comp-meta"><strong>Reference Answer</strong></div><div class="comp-text">${escapeHtml(entry.answer_text)}</div>` : '';
        const category = entry.category_name ? `<span class="cat">${escapeHtml(entry.category_name)}</span>` : '';
        const sideA = renderComparisonSide(entry.first, baseId, 'a');
        const sideB = renderComparisonSide(entry.second, baseId, 'b');
        return `
          <details class="comp-entry">
            <summary>
              <span class="qid">${escapeHtml(entry.qid)}</span>
              ${category}
              <span class="muted">Model: ${escapeHtml(entry.model)}</span>
              <span class="diff-chip">Δ ${diffLabel}</span>
            </summary>
            <div class="comparison-body">
              <div class="comp-question">
                ${questionText}
                ${referenceText}
              </div>
              <div class="comp-grid">
                ${sideA}
                ${sideB}
              </div>
            </div>
          </details>
        `;
      }

      if (comparisonCard && (!COMPARISON_PAIRS || COMPARISON_PAIRS.length === 0)) {
        comparisonCard.style.display = 'none';
      }

      if (comparisonPairSelect && COMPARISON_PAIRS.length) {
        const pairMap = new Map();
        COMPARISON_PAIRS.forEach((pair, idx) => {
          pairMap.set(pair.id, pair);
          const option = document.createElement('option');
          option.value = pair.id;
          option.textContent = `${pair.first.label} vs ${pair.second.label}`;
          if (idx === 0) option.selected = true;
          comparisonPairSelect.appendChild(option);
        });

        const renderComparison = () => {
          const threshold = comparisonSlider ? parseFloat(comparisonSlider.value) : 1;
          if (comparisonValue && !Number.isNaN(threshold)) {
            comparisonValue.textContent = threshold.toFixed(2);
          }
          const pairId = comparisonPairSelect.value;
          const pair = pairMap.get(pairId);
          if (!comparisonResults) {
            return;
          }
          if (!pair) {
            comparisonResults.innerHTML = '<div class="comp-empty">No grader pair selected.</div>';
            return;
          }
          const thresholdValue = Number.isNaN(threshold) ? 0 : threshold;
          const entries = pair.entries
            .filter((entry) => Number(entry.diff || 0) >= thresholdValue)
            .sort((a, b) => {
              if (comparisonSortMode === 'model') {
                const mCompare = (a.model || '').localeCompare(b.model || '');
                if (mCompare !== 0) return mCompare;
                const [am, aq] = qidKey(a.qid);
                const [bm, bq] = qidKey(b.qid);
                if (am !== bm) return am - bm;
                return aq - bq;
              }
              const [am, aq] = qidKey(a.qid);
              const [bm, bq] = qidKey(b.qid);
              if (am !== bm) return am - bm;
              if (aq !== bq) return aq - bq;
              if (a.model && b.model) return a.model.localeCompare(b.model);
              return 0;
            });
          if (!entries.length) {
            comparisonResults.innerHTML = '<div class="comp-empty">No questions within this score gap.</div>';
            return;
          }
          const html = entries.map((entry, index) => renderComparisonEntry(pair, entry, index)).join('');
          comparisonResults.innerHTML = html;
        };

        comparisonPairSelect.addEventListener('change', renderComparison);
        if (comparisonSlider) {
          comparisonSlider.addEventListener('input', renderComparison);
          const threshold = parseFloat(comparisonSlider.value);
          if (comparisonValue && !Number.isNaN(threshold)) {
            comparisonValue.textContent = threshold.toFixed(2);
          }
        }
        if (comparisonSortToggle) {
          comparisonSortToggle.addEventListener('click', () => {
            comparisonSortMode = comparisonSortMode === 'qid' ? 'model' : 'qid';
            comparisonSortToggle.textContent = comparisonSortMode === 'qid' ? 'Sort by model' : 'Sort by question';
            renderComparison();
          });
        }
        if (comparisonSortToggle) {
          comparisonSortToggle.textContent = comparisonSortMode === 'qid' ? 'Sort by model' : 'Sort by question';
        }
        renderComparison();
      }

      currentGrader = resolveGrader(currentGrader);
      setActive('mode-zeroed');
      setGrader(currentGrader);
      refreshCategoryColorsFor(currentGrader);
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

def _qid_key(q: str) -> Tuple[int, int, str]:
    m = re.match(r"Q(\d+)\.(\d+)", str(q))
    if m:
        return (int(m.group(1)), int(m.group(2)), str(q))
    return (999999, 999999, str(q))

def _major_of(qid: str) -> Optional[int]:
    m = re.match(r"Q(\d+)\.", str(qid))
    return int(m.group(1)) if m else None

def _canonical_categories(qmap: Dict[str, Dict[str, Any]]) -> Dict[int, str]:
    """
    Build a mapping {major_number -> display_name} using dataset chapter names.
    Falls back to 'Chapter <n>' if no chapter discovered.
    """
    buckets: Dict[int, Counter] = defaultdict(Counter)
    for qid, obj in qmap.items():
        maj = _major_of(qid)
        if maj is None:
            continue
        chap = str(obj.get("chapter", "") or "").strip()
        if chap:
            # normalize small variations (trim punctuation / ellipses)
            chap = re.sub(r"\s+", " ", chap).strip(" .\u00a0\t\r\n")
            buckets[maj][chap] += 1
    cats: Dict[int, str] = {}
    for maj in sorted({_major_of(q) for q in qmap.keys() if _major_of(q) is not None}):
        if buckets.get(maj):
            name, _ = buckets[maj].most_common(1)[0]
            cats[maj] = name
        else:
            cats[maj] = f"Chapter {maj}"
    return cats


def _compact_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    missed = rec.get("missed", [])
    if not isinstance(missed, list):
        missed = [str(missed)] if missed is not None else []
    images = rec.get("images", [])
    if not isinstance(images, list):
        images = []
    return {
        "provider": rec.get("provider", ""),
        "model": rec.get("model", ""),
        "score": float(rec.get("score", 0.0) or 0.0),
        "rejected": bool(rec.get("rejected", False)),
        "rejection_count": int(rec.get("rejection_count", 0) or 0),
        "justification": rec.get("justification", ""),
        "answer": rec.get("answer", ""),
        "question_text": rec.get("question_text", ""),
        "answer_text": rec.get("answer_text", ""),
        "missed": [str(m) for m in missed],
        "images": [{"rel": im.get("rel", ""), "abs": im.get("abs", "")} for im in images if isinstance(im, dict)],
        "harmful": bool(rec.get("harmful", False)),
        "grader": rec.get("grader", ""),
        "category_name": rec.get("category_name", ""),
        "category_id": rec.get("category_id", ""),
        "model_slug": rec.get("model_slug", ""),
        "page_start": int(rec.get("page_start", 0) or 0),
        "page_end": int(rec.get("page_end", 0) or 0),
    }


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "")).strip("-").lower()
    return value or "view"

def _display_grader_name(name: str) -> str:
    text = str(name or "").strip()
    return text if text else "Unknown grader"

def _build_view(
    models: List[str],
    base_rows_by_model: Dict[str, List[Dict[str, Any]]],
    empty_counter_by_model: Dict[str, Counter],
    empty_counts_by_model: Dict[str, int],
    provider_by_model: Dict[str, str],
    qmap: Dict[str, Dict[str, Any]],
    categories_by_major: Dict[int, str],
    qs_by_cat: Dict[int, Set[str]],
    rel_images_base: str,
    grader_label: str,
) -> Dict[str, Any]:
    rows_by_model: Dict[str, List[Dict[str, Any]]] = {}
    provider_map: Dict[str, str] = {}
    for m in models:
        base_rows = base_rows_by_model.get(m, [])
        copied = [copy.deepcopy(r) for r in base_rows]
        for r in copied:
            r.setdefault("rejected", False)
            r.setdefault("rejection_count", 0)
        rows_by_model[m] = copied
        if provider_by_model.get(m):
            provider_map[m] = provider_by_model[m]
        elif copied:
            provider_map[m] = copied[0].get("provider", "")
        else:
            provider_map[m] = provider_by_model.get(m, "")
    empty_counts = {m: int(empty_counts_by_model.get(m, 0)) for m in models}

    model_avgs: Dict[str, float] = {}
    bars_exclude: List[Dict[str, Any]] = []
    bars_zeroed: List[Dict[str, Any]] = []
    bars_reject: List[Dict[str, Any]] = []

    for m in models:
        rows = rows_by_model[m]
        answered = [r for r in rows if not r.get("rejected")]
        sum_score = sum(float(r.get("score", 0.0)) for r in answered)
        n_answered = len(answered)
        avg_answered = (sum_score / n_answered) if n_answered else 0.0
        model_avgs[m] = avg_answered
        n_reject = empty_counts.get(m, 0)
        n_total = n_answered + n_reject
        avg_zeroed = (sum_score / n_total) if n_total else 0.0
        frac_reject = (n_reject / n_total) if n_total else 0.0
        provider = provider_map.get(m, "")
        bars_exclude.append({"model": m, "provider": provider, "avg": avg_answered, "n": n_answered})
        bars_zeroed.append({
            "model": m,
            "provider": provider,
            "avg": avg_zeroed,
            "n": n_answered,
            "n_reject": n_reject,
            "n_total": n_total,
        })
        bars_reject.append({
            "model": m,
            "provider": provider,
            "avg": frac_reject,
            "n": n_answered,
            "n_reject": n_reject,
            "n_total": n_total,
        })

    bars_exclude.sort(key=lambda x: x["avg"], reverse=True)
    bars_zeroed.sort(key=lambda x: x["avg"], reverse=True)
    bars_reject.sort(key=lambda x: x["avg"], reverse=True)

    cat_list: List[Dict[str, Any]] = []
    cat_bars: Dict[str, Dict[str, Any]] = {}
    for maj in sorted(categories_by_major.keys()):
        cat_name = categories_by_major.get(maj, f"Chapter {maj}")
        rows_for_cat: List[Dict[str, Any]] = []
        bars_exclude_cat: List[Dict[str, Any]] = []
        bars_zeroed_cat: List[Dict[str, Any]] = []
        bars_reject_cat: List[Dict[str, Any]] = []
        for m in models:
            rows = rows_by_model[m]
            answered = [r for r in rows if not r.get("rejected") and r.get("category_id") == str(maj)]
            sum_score = sum(float(r.get("score", 0.0)) for r in answered)
            n_answered = len(answered)
            counter = empty_counter_by_model.get(m, Counter())
            rejects_in_cat = 0
            if counter:
                for qid, count in counter.items():
                    if _major_of(qid) == maj:
                        rejects_in_cat += int(count)
            total = n_answered + rejects_in_cat
            avg_answered = (sum_score / n_answered) if n_answered else 0.0
            avg_zeroed = (sum_score / total) if total else 0.0
            frac_reject = (rejects_in_cat / total) if total else 0.0
            provider = provider_map.get(m, "")
            rows_for_cat.append({
                "model": m,
                "provider": provider,
                "avg_answered": avg_answered,
                "avg_zeroed": avg_zeroed,
                "n_answered": n_answered,
                "n_reject": rejects_in_cat,
                "n_total": total,
            })
            bars_exclude_cat.append({"model": m, "provider": provider, "avg": avg_answered, "n": n_answered})
            bars_zeroed_cat.append({
                "model": m,
                "provider": provider,
                "avg": avg_zeroed,
                "n": n_answered,
                "n_reject": rejects_in_cat,
                "n_total": total,
            })
            bars_reject_cat.append({
                "model": m,
                "provider": provider,
                "avg": frac_reject,
                "n": n_answered,
                "n_reject": rejects_in_cat,
                "n_total": total,
            })
        rows_for_cat.sort(key=lambda r: r["avg_zeroed"], reverse=True)
        bars_exclude_cat.sort(key=lambda r: r["avg"], reverse=True)
        bars_zeroed_cat.sort(key=lambda r: r["avg"], reverse=True)
        bars_reject_cat.sort(key=lambda r: r["avg"], reverse=True)
        cat_list.append({
            "id": str(maj),
            "name": cat_name,
            "total_qs": len(qs_by_cat.get(maj, set())),
            "model_rows": rows_for_cat,
        })
        cat_bars[str(maj)] = {
            "exclude": bars_exclude_cat,
            "zeroed": bars_zeroed_cat,
            "reject": bars_reject_cat,
        }

    for m in models:
        counter = empty_counter_by_model.get(m, Counter())
        if not counter:
            continue
        answered_qs = {r["qid"] for r in rows_by_model[m]}
        provider = provider_map.get(m, "")
        for qid, count in counter.items():
            if qid in answered_qs:
                continue
            qi = qmap.get(qid, {})
            imgs = [str(x) for x in qi.get("images", [])]
            fixed_imgs: List[Dict[str, str]] = []
            for p in imgs:
                base = os.path.basename(p)
                relp = str(Path(rel_images_base) / base)
                absp = "/out/images/" + base
                fixed_imgs.append({"rel": relp, "abs": absp})
            model_slug = re.sub(r"[^a-zA-Z0-9]+", "_", m).strip("_") or "model"
            maj = _major_of(qid)
            cat_name = categories_by_major.get(maj, f"Chapter {maj}" if maj is not None else "")
            rows_by_model[m].append({
                "provider": provider,
                "model": m,
                "qid": qid,
                "score": 0.0,
                "justification": "",
                "answer": "",
                "grader": grader_label,
                "harmful": False,
                "missed": [],
                "question_text": str(qi.get("question_text", "")),
                "answer_text": str(qi.get("answer_text", "")),
                "page_start": int(qi.get("page_start", 0) or 0),
                "page_end": int(qi.get("page_end", 0) or 0),
                "images": fixed_imgs,
                "model_slug": model_slug,
                "rejected": True,
                "rejection_count": int(count),
                "category_id": str(maj) if maj is not None else "",
                "category_name": cat_name,
            })

    for m in models:
        rows_by_model[m].sort(key=lambda r: _qid_key(r["qid"]))

    model_order = [m for m in models if rows_by_model[m]]
    empty_stats = {m: empty_counts[m] for m in models if empty_counts[m] > 0}
    total_empty = sum(empty_counts.values())

    return {
        "rows_by_model": rows_by_model,
        "model_avgs": model_avgs,
        "bars_exclude": bars_exclude,
        "bars_zeroed": bars_zeroed,
        "bars_reject": bars_reject,
        "cat_list": cat_list,
        "cat_bars": cat_bars,
        "empty_stats": empty_stats,
        "total_empty": total_empty,
        "provider_by_model": provider_map,
        "model_order": model_order,
    }

def emit_report(csv_path: Path, html_path: Path, dataset_path: Optional[Path] = None, empty_stats_path: Optional[Path] = None):
    base = Path(csv_path)
    if base.is_dir():
        csv_files = sorted(base.glob("scores__*.csv"))
        if not csv_files:
            legacy = base / "scores.csv"
            csv_files = [legacy] if legacy.exists() else []
        frames: List[pd.DataFrame] = []
        for fp in csv_files:
            try:
                df_part = pd.read_csv(fp)
            except Exception:
                continue
            parts = fp.stem.split("__")
            file_model = parts[1].replace("_", "/") if len(parts) >= 2 else ""
            file_grader = parts[2].replace("_", "/") if len(parts) >= 3 else ""
            if "model" not in df_part.columns:
                df_part["model"] = file_model
            else:
                df_part["model"] = df_part["model"].fillna(file_model)
            if "grader" not in df_part.columns:
                df_part["grader"] = file_grader
            else:
                df_part["grader"] = df_part["grader"].fillna(file_grader)
            frames.append(df_part)
        if frames:
            df = pd.concat(frames, ignore_index=True)
        else:
            df = pd.DataFrame(columns=["provider","model","qid","answer","grader","score","justification","missed","harmful"])
        base_dir = base
    else:
        try:
            df = pd.read_csv(base)
        except Exception:
            df = pd.DataFrame(columns=["provider","model","qid","answer","grader","score","justification","missed","harmful"])
        parts = base.stem.split("__")
        file_model = parts[1].replace("_", "/") if len(parts) >= 2 else ""
        file_grader = parts[2].replace("_", "/") if len(parts) >= 3 else ""
        if "model" not in df.columns:
            df["model"] = file_model
        else:
            df["model"] = df["model"].fillna(file_model)
        if "grader" not in df.columns:
            df["grader"] = file_grader
        else:
            df["grader"] = df["grader"].fillna(file_grader)
        base_dir = base.parent

    df["model"] = df["model"].fillna("").astype(str)
    df["grader"] = df["grader"].fillna("").astype(str)

    if dataset_path is None:
        dataset_path = (base_dir.parent / "dataset.jsonl") if base_dir.name == "graded" else (base_dir / "dataset.jsonl")
    dataset_path = Path(dataset_path)

    if empty_stats_path is None:
        empty_stats_path = base_dir
    empty_stats_path = Path(empty_stats_path)

    html_dir = html_path.parent
    html_dir.mkdir(parents=True, exist_ok=True)

    qmap = _read_dataset(dataset_path)
    categories_by_major = _canonical_categories(qmap)

    images_dir = dataset_path.parent / "images" if dataset_path else base_dir / "images"
    if not images_dir.exists():
        alt = base_dir / "images"
        if alt.exists() or True:
            images_dir = alt
    rel_images_base = os.path.relpath(images_dir, html_dir)

    rows_by_grader_model: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    provider_by_grader_model: Dict[str, Dict[str, str]] = defaultdict(dict)
    empty_counter_by_grader_model: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    empty_counts_by_grader_model: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    agg_rows_by_model: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    agg_provider_by_model: Dict[str, str] = {}
    agg_empty_counter: Dict[str, Counter] = defaultdict(Counter)
    agg_empty_counts: Dict[str, int] = defaultdict(int)

    models_set: Set[str] = set()
    grader_names: Set[str] = set()

    for _, row in df.iterrows():
        qid = str(row.get("qid", "")).strip()
        if not qid:
            continue
        model = str(row.get("model", "")).strip()
        if not model:
            continue
        provider = str(row.get("provider", "") or "").strip()
        grader = str(row.get("grader", "") or "").strip()
        answer = str(row.get("answer", "") or "")
        score_val = row.get("score", 0.0)
        try:
            score = float(score_val)
        except Exception:
            score = 0.0
        if not math.isfinite(score):
            score = 0.0
        justification = str(row.get("justification", "") or "")
        missed = _safe_list(row.get("missed", []))
        h_raw = row.get("harmful", False)
        if isinstance(h_raw, float) and math.isnan(h_raw):
            harmful = False
        elif isinstance(h_raw, (bool, int)):
            harmful = bool(h_raw)
        else:
            harmful = str(h_raw).strip().lower() in {"1", "true", "yes", "y"}

        qi = qmap.get(qid, {})
        imgs = [str(x) for x in qi.get("images", [])]
        fixed_imgs: List[Dict[str, str]] = []
        for p in imgs:
            base = os.path.basename(p)
            relp = str(Path(rel_images_base) / base)
            absp = "/out/images/" + base
            fixed_imgs.append({"rel": relp, "abs": absp})

        model_slug = re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_") or "model"
        maj = _major_of(qid)
        cat_name = categories_by_major.get(maj, f"Chapter {maj}" if maj is not None else "")

        record = {
            "provider": provider,
            "model": model,
            "qid": qid,
            "score": score,
            "justification": justification,
            "answer": answer,
            "grader": grader,
            "harmful": harmful,
            "missed": missed,
            "question_text": str(qi.get("question_text", "")),
            "answer_text": str(qi.get("answer_text", "")),
            "page_start": int(qi.get("page_start", 0) or 0),
            "page_end": int(qi.get("page_end", 0) or 0),
            "images": fixed_imgs,
            "model_slug": model_slug,
            "rejected": False,
            "rejection_count": 0,
            "category_id": str(maj) if maj is not None else "",
            "category_name": cat_name,
        }

        rows_by_grader_model[grader][model].append(record)
        agg_rows_by_model[model].append(copy.deepcopy(record))

        if provider and not provider_by_grader_model[grader].get(model):
            provider_by_grader_model[grader][model] = provider
        if provider and not agg_provider_by_model.get(model):
            agg_provider_by_model[model] = provider

        models_set.add(model)
        grader_names.add(grader)

    empty_files: List[Path] = []
    if empty_stats_path.is_dir():
        empty_files = sorted(empty_stats_path.glob("empty_answers__*.csv"))
        if not empty_files:
            legacy = empty_stats_path / "empty_answers.csv"
            if legacy.exists():
                empty_files = [legacy]
    else:
        if empty_stats_path.exists():
            empty_files = [empty_stats_path]

    for fp in empty_files:
        try:
            empty_df = pd.read_csv(fp)
        except Exception:
            continue
        parts = fp.stem.split("__")
        file_model = parts[1].replace("_", "/") if len(parts) >= 2 else ""
        file_grader = parts[2].replace("_", "/") if len(parts) >= 3 else ""
        if "model" not in empty_df.columns:
            empty_df["model"] = file_model
        else:
            empty_df["model"] = empty_df["model"].fillna(file_model)
        if "grader" not in empty_df.columns:
            empty_df["grader"] = file_grader
        else:
            empty_df["grader"] = empty_df["grader"].fillna(file_grader)
        if "provider" not in empty_df.columns:
            empty_df["provider"] = ""
        else:
            empty_df["provider"] = empty_df["provider"].fillna("")
        for _, row in empty_df.iterrows():
            model = str(row.get("model", "") or "").strip()
            if not model:
                continue
            grader = str(row.get("grader", "") or "").strip()
            qid = str(row.get("qid", "") or "").strip()
            if not qid:
                continue
            provider = str(row.get("provider", "") or "").strip()
            empty_counter_by_grader_model[grader][model][qid] += 1
            empty_counts_by_grader_model[grader][model] += 1
            agg_empty_counter[model][qid] += 1
            agg_empty_counts[model] += 1
            if provider and not provider_by_grader_model[grader].get(model):
                provider_by_grader_model[grader][model] = provider
            if provider and not agg_provider_by_model.get(model):
                agg_provider_by_model[model] = provider
            models_set.add(model)
            grader_names.add(grader)

    for grader_map in provider_by_grader_model.values():
        for model, provider in grader_map.items():
            if provider and not agg_provider_by_model.get(model):
                agg_provider_by_model[model] = provider

    models = sorted(models_set)

    majors_from_data: Set[int] = set()
    for rows_list in agg_rows_by_model.values():
        for rec in rows_list:
            maj = _major_of(rec.get("qid"))
            if maj is not None:
                majors_from_data.add(maj)
    for counter in agg_empty_counter.values():
        for qid in counter.keys():
            maj = _major_of(qid)
            if maj is not None:
                majors_from_data.add(maj)
    for maj in majors_from_data:
        categories_by_major.setdefault(maj, f"Chapter {maj}")

    qs_by_cat: Dict[int, Set[str]] = defaultdict(set)
    if qmap:
        for qid in qmap.keys():
            maj = _major_of(qid)
            if maj is not None:
                qs_by_cat[maj].add(qid)
    else:
        for rows_list in agg_rows_by_model.values():
            for rec in rows_list:
                maj = _major_of(rec.get("qid"))
                if maj is not None:
                    qs_by_cat[maj].add(rec["qid"])
        for counter in agg_empty_counter.values():
            for qid in counter.keys():
                maj = _major_of(qid)
                if maj is not None:
                    qs_by_cat[maj].add(qid)

    all_majors = sorted(categories_by_major.keys())
    category_options = [{"id": str(maj), "name": categories_by_major.get(maj, f"Chapter {maj}")} for maj in all_majors]

    grader_labels = {g: _display_grader_name(g) for g in grader_names}
    sorted_graders = sorted(grader_names, key=lambda g: grader_labels[g])
    source_graders = []
    for g in sorted_graders:
        label = grader_labels[g]
        if label not in source_graders:
            source_graders.append(label)

    agg_metrics = _build_view(
        models,
        {m: agg_rows_by_model.get(m, []) for m in models},
        {m: Counter(agg_empty_counter.get(m, Counter())) for m in models},
        {m: int(agg_empty_counts.get(m, 0)) for m in models},
        agg_provider_by_model,
        qmap,
        categories_by_major,
        qs_by_cat,
        rel_images_base,
        "All graders (avg)",
    )

    views: List[Dict[str, Any]] = []
    views.append({
        "id": "all",
        "label": "All graders (avg)",
        "active": True,
        "is_all": True,
        "grader_key": None,
        "source_graders": source_graders,
        "rows_by_model": agg_metrics["rows_by_model"],
        "model_avgs": agg_metrics["model_avgs"],
        "provider_by_model": agg_metrics["provider_by_model"],
        "categories": agg_metrics["cat_list"],
        "cat_bars": agg_metrics["cat_bars"],
        "bars_exclude": agg_metrics["bars_exclude"],
        "bars_zeroed": agg_metrics["bars_zeroed"],
        "bars_reject": agg_metrics["bars_reject"],
        "empty_stats": agg_metrics["empty_stats"],
        "total_empty": agg_metrics["total_empty"],
        "model_order": agg_metrics["model_order"],
    })

    for grader in sorted_graders:
        label = grader_labels[grader]
        view_id = _slugify(f"{label}-{grader}" if grader else label)
        rows_map = rows_by_grader_model.get(grader, {})
        counter_map = empty_counter_by_grader_model.get(grader, {})
        counts_map = empty_counts_by_grader_model.get(grader, {})
        provider_map = provider_by_grader_model.get(grader, {})
        metrics = _build_view(
            models,
            {m: rows_map.get(m, []) for m in models},
            {m: Counter(counter_map.get(m, Counter())) for m in models},
            {m: int(counts_map.get(m, 0)) for m in models},
            provider_map,
            qmap,
            categories_by_major,
            qs_by_cat,
            rel_images_base,
            label,
        )
        views.append({
            "id": view_id,
            "label": label,
            "grader_key": grader,
            "active": False,
            "is_all": False,
            "rows_by_model": metrics["rows_by_model"],
            "model_avgs": metrics["model_avgs"],
            "provider_by_model": metrics["provider_by_model"],
            "categories": metrics["cat_list"],
            "cat_bars": metrics["cat_bars"],
            "bars_exclude": metrics["bars_exclude"],
            "bars_zeroed": metrics["bars_zeroed"],
            "bars_reject": metrics["bars_reject"],
            "empty_stats": metrics["empty_stats"],
            "total_empty": metrics["total_empty"],
            "model_order": metrics["model_order"],
        })

    comparison_pairs: List[Dict[str, Any]] = []
    grader_view_list = [v for v in views if not v.get("is_all")]
    if len(grader_view_list) >= 2:
        for view_a, view_b in combinations(grader_view_list, 2):
            entries: List[Dict[str, Any]] = []
            models_union = set(view_a["rows_by_model"].keys()) | set(view_b["rows_by_model"].keys())
            for model in sorted(models_union):
                rows_a = {r["qid"]: r for r in view_a["rows_by_model"].get(model, [])}
                rows_b = {r["qid"]: r for r in view_b["rows_by_model"].get(model, [])}
                common_qids = set(rows_a.keys()) & set(rows_b.keys())
                for qid in sorted(common_qids, key=_qid_key):
                    rec_a = rows_a[qid]
                    rec_b = rows_b[qid]
                    diff = abs(float(rec_a.get("score", 0.0) or 0.0) - float(rec_b.get("score", 0.0) or 0.0))
                    entry = {
                        "model": model,
                        "qid": qid,
                        "diff": round(diff, 6),
                        "category_name": rec_a.get("category_name") or rec_b.get("category_name", ""),
                        "category_id": rec_a.get("category_id") or rec_b.get("category_id", ""),
                        "first": {
                            "view": view_a["id"],
                            "label": view_a["label"],
                            "record": _compact_record(rec_a),
                        },
                        "second": {
                            "view": view_b["id"],
                            "label": view_b["label"],
                            "record": _compact_record(rec_b),
                        },
                    }
                    entry["question_text"] = entry["first"]["record"].get("question_text") or entry["second"]["record"].get("question_text", "")
                    entry["answer_text"] = entry["first"]["record"].get("answer_text") or entry["second"]["record"].get("answer_text", "")
                    entries.append(entry)
            if entries:
                entries.sort(key=lambda e: _qid_key(e["qid"]))
                comparison_pairs.append({
                    "id": f"{view_a['id']}__{view_b['id']}",
                    "first": {"view": view_a["id"], "label": view_a["label"]},
                    "second": {"view": view_b["id"], "label": view_b["label"]},
                    "entries": entries,
                })

    has_comparisons = bool(comparison_pairs)

    show_empty_section = any(view["total_empty"] > 0 for view in views)

    if qmap:
        qids = sorted(qmap.keys(), key=_qid_key)
    else:
        qid_set: Set[str] = set()
        for rows_list in agg_rows_by_model.values():
            for rec in rows_list:
                qid_set.add(rec["qid"])
        for counter in agg_empty_counter.values():
            qid_set.update(counter.keys())
        qids = sorted(qid_set, key=_qid_key)

    data_json = json.dumps({
        "meta": {
            "qids": qids,
            "models": models,
            "total_questions": len(qids),
            "categories": category_options,
        },
        "order": [view["id"] for view in views],
        "default": views[0]["id"] if views else "",
        "graders": {
            view["id"]: {
                "label": view["label"],
                "bars_exclude": view["bars_exclude"],
                "bars_zeroed": view["bars_zeroed"],
                "bars_reject": view["bars_reject"],
                "cat_bars": view["cat_bars"],
                "total_empty": view["total_empty"],
            }
            for view in views
        },
        "comparisons": {
            "pairs": comparison_pairs,
        },
    })

    default_view = views[0] if views else {"label": "All graders (avg)", "total_empty": 0}

    tpl = Template(HTML)
    html = tpl.render(
        total=len(qids),
        models=models,
        views=views,
        data_json=data_json,
        default_view=default_view,
        default_view_id=views[0]["id"] if views else "",
        category_options=category_options,
        show_empty_section=show_empty_section,
        comparison_pairs=comparison_pairs,
        has_comparisons=has_comparisons,
    )
    html_path.write_text(html, encoding="utf-8")
