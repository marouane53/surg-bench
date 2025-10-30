from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Set
from jinja2 import Template
import json, ast, os, re
from collections import defaultdict, Counter

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
    header { display:flex; align-items:center; justify-content:space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 10px; }
    header h1 { font-size: 22px; font-weight: 700; margin: 0; letter-spacing: 0.3px; }
    header .meta { color: var(--muted); font-size: 13px; }
    header .actions { display:flex; gap:8px; align-items:center; flex-wrap: wrap; }

    .card { background: linear-gradient(180deg, var(--panel), var(--panel-2)); border: 1px solid #232845; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); overflow: hidden; }
    .card .hd { padding: 14px 16px; border-bottom: 1px solid #262b49; display:flex; align-items:center; justify-content:space-between; gap:10px; }
    .card .bd { padding: 16px; }

    /* Buttons & chips */
    .controls { display:flex; gap:10px; align-items:center; flex-wrap: wrap; }
    .btn { padding: 6px 10px; border-radius: 8px; border: 1px solid #cfd6ff33; background: var(--chip); color: var(--chip-text); cursor: pointer; font-size: 12px; }
    .btn:hover { filter: brightness(1.03); }
    .btn.active { outline: 2px solid var(--accent); }
    select, option { font-size: 12px; padding: 6px 10px; border-radius: 8px; background: var(--panel-2); color: var(--text); border:1px solid #2b3156; }

    /* Chart area: ranked bar chart */
    #chartWrap { position: relative; }
    #scoreCanvas { width: 100%; height: 360px; display:block; }
    .tooltip { position: absolute; pointer-events:none; background:#0d1022; color:#dce1ff; border:1px solid #2b3156; padding:8px 10px; border-radius:8px; font-size:12px; box-shadow:0 6px 20px rgba(0,0,0,0.15); display:none; z-index: 10; }

    /* Q&A sections */
    .sect { margin-top: 22px; }
    .sect h2 { font-size: 16px; margin: 0 0 10px 0; font-weight: 600; color: #dce1ff; }

    /* Model-level collapsible */
    details.mcard { border: 1px solid #262b49; border-radius: 12px; margin: 12px 0; background: #151a30; }
    details.mcard > summary { list-style:none; cursor:pointer; padding: 12px 14px; display:flex; align-items:center; justify-content:space-between; gap:10px; }
    details.mcard > summary::-webkit-details-marker { display:none; }
    .hdr-left { display:flex; gap:8px; align-items:center; }
    .model-name { font-weight: 700; }
    .muted { color: var(--muted); }
    .avg-badge { padding: 4px 8px; border-radius: 999px; background:#1a2145; border: 1px solid #2e3867; font-size: 12px; color:#c8d2ff; }

    .qcard { border-top: 1px solid #262b49; padding: 12px 0; }
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
    /* Hide rejected QID details when excluding rejections */
    .hide-rejects details.qd.rejected { display: none; }

    /* Category table */
    table.cat { width: 100%; border-collapse: collapse; }
    table.cat th, table.cat td { border-bottom: 1px solid #262b49; padding: 8px 10px; text-align: left; font-size: 12px; }
    table.cat tbody tr { border-left: 4px solid transparent; transition: background 0.25s ease, border-color 0.25s ease, color 0.25s ease, filter 0.2s ease; }
    table.cat tbody tr td { transition: color 0.25s ease; }
    table.cat tbody tr:hover { filter: brightness(1.05); }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Surgical Benchmark</h1>
      <div class="actions">
        <div class="meta">Questions: {{ total }} · Models: {{ models|length }} · Grader: {{ grader_name }}{% if total_empty > 0 %} · Empty answers: {{ total_empty }}{% endif %}</div>
        <label style="display:flex; align-items:center; gap:6px;">
          <span class="muted">Category</span>
          <select id="categorySelect">
            <option value="">All</option>
            {% for cat in categories %}
              <option value="{{ cat.id }}">{{ cat.id }} · {{ cat.name }}</option>
            {% endfor %}
          </select>
        </label>
        <button class="btn" id="expandAll" type="button">Expand All</button>
        <button class="btn" id="collapseAll" type="button">Collapse All</button>
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
              <div class="muted">{{ count }} empty answer{{ 's' if count > 1 else '' }}</div>
            </div>
          {% endfor %}
        </div>
      </div>
    </section>
    {% endif %}

    <!-- Category Breakdown -->
    <section class="card" style="margin:12px 0;">
      <div class="hd">
        <strong>By Category</strong>
        <div class="muted">Averages per category (answered-only and zeroed)</div>
      </div>
      <div class="bd">
        {% for cat in categories %}
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
      </div>
    </section>

    <!-- Q&A Details -->
    <section class="sect">
      <h2>Per-Question Details</h2>
      {% for model_name, rows in rows_by_model.items() %}
      <details class="mcard">
        <summary>
          <div class="hdr-left">
            <span class="model-name">{{ model_name }}</span>
            <span class="muted">Provider: {{ rows[0].provider }}</span>
          </div>
          <span class="avg-badge">Average: {{ "%.3f"|format(model_avgs[model_name]) }}</span>
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
      </details>
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
      const categories = DATA.meta.categories || [];
      const colorForIdx = (i) => {
        const hue = (i * 137.508) % 360; // golden angle spacing
        return `hsl(${hue}deg 70% 55%)`;
      };

      // Build ranked bars for each mode
      let mode = 'zeroed';
      let currentCat = '';
      let barsScore = [...(DATA.bars_exclude || DATA.bars || [])];
      let barsZeroed = [...(DATA.bars_zeroed || [])];
      let barsReject = [...(DATA.bars_reject || [])];
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

      function scoreToPalette(score) {
        const s = Math.min(1, Math.max(0, Number.isFinite(score) ? score : 0));
        const sat = 82;
        let hue;
        if (s <= 0.5) {
          const t = s / 0.5; // 0 → red, 1 → yellow
          hue = 0 + (50 * t);
        } else {
          const t = (s - 0.5) / 0.5; // 0 → yellow, 1 → green
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

      function refreshCategoryColors() {
        document.querySelectorAll('table.cat tbody tr[data-score]').forEach((row) => {
          const score = parseFloat(row.dataset.score || '0');
          if (!Number.isFinite(score)) return;
          const palette = scoreToPalette(score);
          row.style.setProperty('--score-bg', palette.bg);
          row.style.setProperty('--score-border', palette.border);
          row.style.background = palette.bg;
          row.style.borderLeftColor = palette.border;
          const cells = row.querySelectorAll('td');
          if (palette.text) {
            row.style.color = palette.text;
            cells.forEach((cell, idx) => {
              cell.style.color = idx === 1 && palette.muted ? palette.muted : palette.text;
            });
          } else {
            row.style.removeProperty('color');
            cells.forEach((cell) => cell.style.removeProperty('color'));
          }
        });
      }

      function drawPoints(progress=1) {
        const bars = (mode === 'reject') ? barsReject : (mode === 'zeroed' ? barsZeroed : barsScore);
        // bars
        const rowH = Math.max(18, Math.min(40, innerH / Math.max(1,bars.length)));
        const gap = 8;
        const totalH = bars.length * (rowH + gap) - gap;
        const offsetY = PADDING.t + Math.max(0, (innerH - totalH)/2);
        for (let i=0;i<bars.length;i++) {
          const b = bars[i];
          const y = offsetY + i*(rowH+gap);
          const w = (b.avg) * innerW * progress;
          const color = colorForIdx(i);
          ctx.fillStyle = color;
          ctx.fillRect(PADDING.l, y, Math.max(2, w), rowH);
          // label gutter
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
      function animateBars(ts) {
        if (!t0) t0 = ts;
        const d = ts - t0; const p = Math.min(1, d/800);
        render(p);
        if (p < 1) requestAnimationFrame(animateBars);
      }
      requestAnimationFrame(animateBars);

      // tooltip interactions for bars
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
            const ntot = hit.n_total ?? totalQuestions;
            tip.innerHTML = `<div><strong>${hit.model}</strong> <span class="muted">(${hit.provider})</span></div><div>Rejections: <strong>${rate}</strong> (empty=${hit.n_reject||0}, total=${ntot})</div><div class="muted">Higher is worse</div>`;
          } else if (mode === 'zeroed') {
            const ntot = hit.n_total ?? (hit.n + (hit.n_reject||0));
            tip.innerHTML = `<div><strong>${hit.model}</strong> <span class="muted">(${hit.provider})</span></div><div>Avg (zeros for rejects): <strong>${hit.avg.toFixed(3)}</strong> (answered=${hit.n}, rejects=${hit.n_reject||0}, total=${ntot})</div>`;
          } else {
            tip.innerHTML = `<div><strong>${hit.model}</strong> <span class="muted">(${hit.provider})</span></div><div>Average: <strong>${hit.avg.toFixed(3)}</strong> (answered=${hit.n})</div>`;
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
        applyCategory(currentCat, false); // refresh bars only
      }
      document.getElementById('mode-score')?.addEventListener('click', () => setMode('score'));
      document.getElementById('mode-zeroed')?.addEventListener('click', () => setMode('zeroed'));
      document.getElementById('mode-reject')?.addEventListener('click', () => setMode('reject'));

      // Category filter: filter question details + update chart
      const catSelect = document.getElementById('categorySelect');
      function applyCategory(catId, animateTransition=true) {
        currentCat = catId || '';
        // Update buttons
        if (mode === 'reject') {
          setActive('mode-reject');
          hintEl.textContent = 'Higher is worse — hover for details';
        } else if (mode === 'zeroed') {
          setActive('mode-zeroed');
          hintEl.textContent = 'Counts rejections as 0 — hover for details';
        } else {
          setActive('mode-score');
          hintEl.textContent = 'Excludes rejections — hover for details';
        }

        // Update chart title + data
        if (!currentCat) {
          titleEl.textContent = 'All Questions Accounted (ranked)';
          barsScore = [...(DATA.bars_exclude || DATA.bars || [])];
          barsZeroed = [...(DATA.bars_zeroed || [])];
          barsReject = [...(DATA.bars_reject || [])];
        } else {
          const cat = DATA.cat_bars?.[currentCat] || {};
          titleEl.textContent = `Category ${currentCat} · ${(categories.find(c => c.id == currentCat)?.name || '')}`;
          barsScore = [...(cat.exclude || [])];
          barsZeroed = [...(cat.zeroed || [])];
          barsReject = [...(cat.reject || [])];
        }
        // Update details filtering
        document.querySelectorAll('details.qd').forEach((el) => {
          const cat = el.getAttribute('data-cat');
          if (!currentCat || !cat) {
            el.style.display = '';
          } else {
            el.style.display = (cat === currentCat) ? '' : 'none';
          }
        });
        if (animateTransition) {
          t0 = null;
          requestAnimationFrame(animateBars);
        } else {
          render(1);
        }
        refreshCategoryColors();
      }
      catSelect?.addEventListener('change', (e) => applyCategory(e.target.value, true));

      // Initialize defaults
      setMode('zeroed');
      applyCategory('', false);
      refreshCategoryColors();

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

      // Expand/Collapse all models
      const expandAll = document.getElementById('expandAll');
      const collapseAll = document.getElementById('collapseAll');
      expandAll?.addEventListener('click', () => {
        document.querySelectorAll('details.mcard').forEach(d => d.open = true);
      });
      collapseAll?.addEventListener('click', () => {
        document.querySelectorAll('details.mcard').forEach(d => d.open = false);
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

    # Compute canonical categories from dataset
    categories_by_major = _canonical_categories(qmap)
    all_majors = sorted(categories_by_major.keys())
    # Prepare reverse map qid->major
    qid_major: Dict[str, Optional[int]] = {qid: _major_of(qid) for qid in qmap.keys()}

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

        maj = _major_of(qid)
        cat_name = categories_by_major.get(maj, f"Chapter {maj}" if maj is not None else "")

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
            "category_id": str(maj) if maj is not None else "",
            "category_name": cat_name,
        }
        rows_by_model.setdefault(model, []).append(rec)
        # aggregate
        sum_by_model[model] = sum_by_model.get(model, 0.0) + float(rec["score"])

    # Sort rows in each model by QID
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
                maj = _major_of(qid)
                cat_name = categories_by_major.get(maj, f"Chapter {maj}" if maj is not None else "")
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
                    "category_id": str(maj) if maj is not None else "",
                    "category_name": cat_name,
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

    # ----- Build category aggregates -----
    # Per-category per-model stats and per-category bars
    cat_list: List[Dict[str, Any]] = []
    cat_bars: Dict[str, Dict[str, Any]] = {}
    # Precompute total questions per category from dataset
    qs_by_cat: Dict[int, Set[str]] = defaultdict(set)
    for qid in qmap.keys():
        maj = _major_of(qid)
        if maj is not None:
            qs_by_cat[maj].add(qid)

    # Build per-category model stats
    for maj in all_majors:
        cat_name = categories_by_major.get(maj, f"Chapter {maj}")
        # Build stats rows for table
        rows_for_cat: List[Dict[str, Any]] = []
        bars_exclude_cat: List[Dict[str, Any]] = []
        bars_zeroed_cat: List[Dict[str, Any]] = []
        bars_reject_cat: List[Dict[str, Any]] = []
        for m in models:
            answered = [r for r in rows_by_model.get(m, []) if not r["rejected"] and r.get("category_id") == str(maj)]
            n_answered = len(answered)
            sum_score = sum(r["score"] for r in answered)
            rejects_in_cat = 0
            if empty_qids_by_model.get(m):
                rejects_in_cat = sum(1 for qid in empty_qids_by_model[m] if _major_of(qid) == maj)
            n_total = n_answered + rejects_in_cat
            avg_answered = (sum_score / n_answered) if n_answered > 0 else 0.0
            avg_zeroed = (sum_score / n_total) if n_total > 0 else 0.0
            provider = provider_by_model.get(m, (rows_by_model[m][0]["provider"] if rows_by_model.get(m) else ""))
            rows_for_cat.append({
                "model": m,
                "provider": provider,
                "avg_answered": avg_answered,
                "avg_zeroed": avg_zeroed,
                "n_answered": n_answered,
                "n_reject": rejects_in_cat,
                "n_total": n_total,
            })
            bars_exclude_cat.append({
                "model": m,
                "provider": provider,
                "avg": avg_answered,
                "n": n_answered,
            })
            bars_zeroed_cat.append({
                "model": m,
                "provider": provider,
                "avg": avg_zeroed,
                "n": n_answered,
                "n_reject": rejects_in_cat,
                "n_total": n_total,
            })
            frac_reject = (rejects_in_cat / n_total) if n_total > 0 else 0.0
            bars_reject_cat.append({
                "model": m,
                "provider": provider,
                "avg": frac_reject,
                "n": n_answered,
                "n_reject": rejects_in_cat,
                "n_total": n_total,
            })
        # Sort rows by zeroed average
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

    data_json = json.dumps({
        "meta": {
            "qids": qids,
            "models": models,
            "total_questions": len(qids),
            "categories": [{"id": str(m), "name": categories_by_major.get(m, f"Chapter {m}")} for m in all_majors],
        },
        "points": points,
        "bars": bars_exclude,  # backward compat
        "bars_exclude": bars_exclude,
        "bars_zeroed": bars_zeroed,
        "bars_reject": bars_reject,
        "cat_bars": cat_bars,
    })

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
        categories=cat_list,
    )
    html_path.write_text(html, encoding="utf-8")
