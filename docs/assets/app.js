(function () {
  const DATA = window.PUBLIC_BENCHMARK_DATA;
  if (!DATA) {
    throw new Error("Missing public benchmark data.");
  }

  const state = {
    viewId: DATA.views[0].id,
    metric: "zeroed",
  };

  const providerColors = {
    gemini: "oklch(0.57 0.12 164)",
    "openai-reasoning": "oklch(0.65 0.12 84)",
    openai: "oklch(0.7 0.11 52)",
    anthropic: "oklch(0.63 0.11 36)",
    openrouter: "oklch(0.6 0.07 238)",
    groq: "oklch(0.62 0.09 126)",
  };

  const metricConfig = {
    zeroed: {
      label: "All cases",
      title: "All cases counted",
      note: "Empty or rejected answers are scored as zero.",
      valueKey: "zeroed",
      formatter: formatScore,
    },
    answered: {
      label: "Answered only",
      title: "Answered-only quality",
      note: "Only non-empty answers are counted.",
      valueKey: "answered",
      formatter: formatScore,
    },
    rejectRate: {
      label: "Reject rate",
      title: "Failure and refusal rate",
      note: "Lower is better. Values are shown as percentages.",
      valueKey: "rejectRate",
      formatter: formatPercent,
    },
  };

  const refs = {
    metaCases: document.getElementById("meta-cases"),
    metaSubprompts: document.getElementById("meta-subprompts"),
    metaModels: document.getElementById("meta-models"),
    metaCategories: document.getElementById("meta-categories"),
    metaGenerated: document.getElementById("meta-generated"),
    footerStamp: document.getElementById("footer-stamp"),
    heroSummary: document.getElementById("hero-summary"),
    methodBenchmarkCopy: document.getElementById("method-benchmark-copy"),
    showcaseTitle: document.getElementById("showcase-title"),
    showcaseDeck: document.getElementById("showcase-deck"),
    showcaseMeta: document.getElementById("showcase-meta"),
    showcaseQuestionLead: document.getElementById("showcase-question-lead"),
    showcaseQuestionList: document.getElementById("showcase-question-list"),
    showcaseImageToggle: document.getElementById("showcase-image-toggle"),
    showcaseImagePanel: document.getElementById("showcase-image-panel"),
    showcaseImageRail: document.getElementById("showcase-image-rail"),
    showcaseReferenceList: document.getElementById("showcase-reference-list"),
    showcaseRubricList: document.getElementById("showcase-rubric-list"),
    showcaseSummary: document.getElementById("showcase-summary"),
    showcaseModelGrid: document.getElementById("showcase-model-grid"),
    viewControls: document.getElementById("view-controls"),
    metricControls: document.getElementById("metric-controls"),
    resultsContext: document.getElementById("results-context"),
    rankingTitle: document.getElementById("ranking-title"),
    rankingNote: document.getElementById("ranking-note"),
    rankingChart: document.getElementById("ranking-chart"),
    takeawayCards: document.getElementById("takeaway-cards"),
    topTableBody: document.querySelector("#top-table tbody"),
    scatterChart: document.getElementById("scatter-chart"),
    latencyChart: document.getElementById("latency-chart"),
    heatmapTitle: document.getElementById("heatmap-title"),
    heatmapLegend: document.getElementById("heatmap-legend"),
    heatmapChart: document.getElementById("heatmap-chart"),
    leaderChart: document.getElementById("leader-chart"),
    leaderCards: document.getElementById("leader-cards"),
    tooltip: document.getElementById("tooltip"),
  };

  function formatScore(value) {
    return Number(value).toFixed(3);
  }

  function formatPercent(value) {
    return `${(Number(value) * 100).toFixed(1)}%`;
  }

  function formatDuration(valueMs) {
    const seconds = Number(valueMs) / 1000;
    if (seconds >= 60) {
      const minutes = Math.floor(seconds / 60);
      const remaining = seconds - minutes * 60;
      if (remaining >= 10) {
        return `${minutes}m ${remaining.toFixed(0)}s`;
      }
      return `${minutes}m ${remaining.toFixed(1)}s`;
    }

    if (seconds >= 10) {
      return `${seconds.toFixed(0)}s`;
    }

    return `${seconds.toFixed(1)}s`;
  }

  function formatDate(value) {
    const date = new Date(value);
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      timeZone: "UTC",
    }).format(date);
  }

  function formatCount(value) {
    return new Intl.NumberFormat("en-US").format(Number(value));
  }

  function truncateText(value, maxLength) {
    const compact = String(value || "").replace(/\s+/g, " ").trim();
    if (compact.length <= maxLength) {
      return compact;
    }
    return `${compact.slice(0, maxLength - 1).trimEnd()}…`;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replaceAll("\n", "&#10;");
  }

  function tooltipText(lines) {
    return lines.join("\n");
  }

  function getCurrentView() {
    return DATA.views.find((view) => view.id === state.viewId) || DATA.views[0];
  }

  function sortModels(models) {
    const key = metricConfig[state.metric].valueKey;
    const sorted = [...models];

    sorted.sort((a, b) => {
      if (state.metric === "rejectRate") {
        const delta = a.overall[key] - b.overall[key];
        if (delta !== 0) {
          return delta;
        }
        const qualityDelta = b.overall.zeroed - a.overall.zeroed;
        if (qualityDelta !== 0) {
          return qualityDelta;
        }
      } else {
        const delta = b.overall[key] - a.overall[key];
        if (delta !== 0) {
          return delta;
        }
        const rejectDelta = a.overall.rejectRate - b.overall.rejectRate;
        if (rejectDelta !== 0) {
          return rejectDelta;
        }
      }
      return a.label.localeCompare(b.label);
    });

    return sorted;
  }

  function scoreColor(provider) {
    return providerColors[provider] || "oklch(0.64 0.08 160)";
  }

  function heatColor(value, metric) {
    if (metric === "rejectRate") {
      const normalized = Math.max(0, Math.min(1, value / 0.3));
      const hue = 152 - normalized * 124;
      const lightness = 0.95 - normalized * 0.24;
      const chroma = 0.03 + normalized * 0.11;
      return `oklch(${lightness} ${chroma} ${hue})`;
    }

    const normalized = Math.max(0, Math.min(1, value));
    const hue = 28 + normalized * 126;
    const lightness = 0.96 - normalized * 0.28;
    const chroma = 0.03 + normalized * 0.11;
    return `oklch(${lightness} ${chroma} ${hue})`;
  }

  function showTooltip(event) {
    const content = event.currentTarget.dataset.tooltip;
    if (!content) {
      return;
    }

    refs.tooltip.innerHTML = escapeHtml(content).replaceAll("\n", "<br>");
    refs.tooltip.classList.add("is-visible");
    moveTooltip(event);
  }

  function moveTooltip(event) {
    if (!refs.tooltip.classList.contains("is-visible")) {
      return;
    }

    const x = Math.min(event.clientX + 18, window.innerWidth - refs.tooltip.offsetWidth - 12);
    const y = Math.min(event.clientY + 18, window.innerHeight - refs.tooltip.offsetHeight - 12);
    refs.tooltip.style.left = `${x}px`;
    refs.tooltip.style.top = `${y}px`;
  }

  function hideTooltip() {
    refs.tooltip.classList.remove("is-visible");
  }

  function attachTooltips(root) {
    root.querySelectorAll("[data-tooltip]").forEach((node) => {
      node.addEventListener("pointerenter", showTooltip);
      node.addEventListener("pointermove", moveTooltip);
      node.addEventListener("pointerleave", hideTooltip);
    });
  }

  function renderMeta() {
    refs.metaCases.textContent = formatCount(DATA.meta.caseCount);
    refs.metaSubprompts.textContent = formatCount(DATA.meta.subPromptCount);
    refs.metaModels.textContent = DATA.meta.modelCount;
    refs.metaCategories.textContent = DATA.meta.categoryCount;
    refs.metaGenerated.textContent = formatDate(DATA.meta.generatedAt);
    refs.footerStamp.textContent = `Generated from graded benchmark outputs on ${formatDate(DATA.meta.generatedAt)}.`;
    refs.heroSummary.textContent = `Surg Bench evaluates ${formatCount(DATA.meta.modelCount)} AI models on ${formatCount(DATA.meta.caseCount)} cases drawn from the 2025 textbook Surgical Exam Cases by Charles Tan. Some cases include images and many contain multiple numbered tasks, adding up to ${formatCount(DATA.meta.subPromptCount)} sub-prompts. This page introduces the benchmark, shows the public results, and includes one illustrative case so visitors can see how the evaluation works on a real prompt.`;
    refs.methodBenchmarkCopy.innerHTML = `
      <p>
        Surg Bench evaluates AI models on ${formatCount(DATA.meta.caseCount)} cases from the 2025 textbook
        <em>Surgical Exam Cases</em> by Charles Tan. Some cases include images, and many include multiple
        numbered tasks, yielding ${formatCount(DATA.meta.subPromptCount)} sub-prompts in this release.
      </p>
      <p>
        The recent publication date matters because it reduces the chance that strong results come from memorized
        training data. In practice, that makes the benchmark more about reasoning on contemporary surgical material.
      </p>
      <p>
        Each model answer was graded independently by two grader models. This page lets you inspect each grader
        separately or use the averaged view to see where rankings stay consistent.
      </p>
      <p>
        Because the cases are open-ended rather than multiple-choice, grading is not based on exact answer matching.
        Instead, two independent model graders score each response against the reference answer and the expected
        clinical reasoning. One representative case is shown on this page so readers can see that scoring process in context.
      </p>
    `;
  }

  function renderShowcase() {
    const example = DATA.showcaseExample;
    if (!example) {
      return;
    }

    refs.showcaseTitle.textContent = example.title;
    refs.showcaseDeck.textContent = example.deck;
    refs.showcaseMeta.innerHTML = `
      <span>${escapeHtml(example.qid)}</span>
      <span>${escapeHtml(example.category)}</span>
      <span>${escapeHtml(example.pageRange)}</span>
      <span>${escapeHtml(example.grader.label)} grading</span>
    `;
    refs.showcaseQuestionLead.textContent = example.questionLead;

    refs.showcaseQuestionList.innerHTML = example.questionItems
      .map(
        (item, index) => `
          <div class="showcase-list__item">
            <span class="showcase-list__index">${index + 1}</span>
            <p>${escapeHtml(item)}</p>
          </div>
        `
      )
      .join("");

    refs.showcaseImageRail.innerHTML = example.images
      .map((image, index) => {
        const wideClass = index === example.images.length - 1 ? " showcase-image-card--wide" : "";
        return `
          <figure class="showcase-image-card${wideClass}">
            <img src="${escapeAttribute(image.src)}" alt="${escapeAttribute(image.alt)}">
            <figcaption>${escapeHtml(image.caption)}</figcaption>
          </figure>
        `;
      })
      .join("");
    refs.showcaseImagePanel.hidden = true;
    refs.showcaseImageToggle.setAttribute("aria-expanded", "false");
    refs.showcaseImageToggle.textContent = "Show images from this case";

    refs.showcaseReferenceList.innerHTML = example.referenceItems
      .map(
        (item, index) => `
          <div class="showcase-list__item">
            <span class="showcase-list__index">${index + 1}</span>
            <p>${escapeHtml(item)}</p>
          </div>
        `
      )
      .join("");

    refs.showcaseRubricList.innerHTML = example.rubric
      .map(
        (item, index) => `
          <div class="showcase-rubric">
            <span class="showcase-list__index">${index + 1}</span>
            <div class="showcase-rubric__body">
              <p class="showcase-rubric__title">${escapeHtml(item.label)}</p>
              <p>${escapeHtml(item.description)}</p>
            </div>
          </div>
        `
      )
      .join("");

    refs.showcaseSummary.textContent = example.summary;
    refs.showcaseModelGrid.innerHTML = example.models
      .map((model) => {
        const scoreClass = model.empty ? " showcase-score--empty" : "";
        const preview = model.empty
          ? `No answer returned after ${model.retryAttempts || 0} retries.`
          : truncateText(model.answerPreview || model.answer, 210);
        const grades = model.graderScores
          .map((item) => {
            const suffix = item.empty ? "empty" : formatScore(item.score);
            return `<span class="showcase-grade">${escapeHtml(item.label)} ${escapeHtml(suffix)}</span>`;
          })
          .join("");
        const checks = model.checks
          .map(
            (item) =>
              `<span class="showcase-check" data-status="${escapeAttribute(item.status)}">${escapeHtml(item.label)}</span>`
          )
          .join("");
        const missed = model.missedPoints.length
          ? `
            <div>
              <p class="showcase-body-heading">What the graders marked missing</p>
              <ul class="showcase-missed">
                ${model.missedPoints
                  .slice(0, 8)
                  .map((item) => `<li>${escapeHtml(item)}</li>`)
                  .join("")}
              </ul>
            </div>
          `
          : `
            <p class="showcase-empty-note">No missed points were flagged by the graders.</p>
          `;
        const answerBody = model.empty
          ? `<p class="showcase-empty-note">The benchmark run recorded no answer for this case.</p>`
          : `
            <div>
              <p class="showcase-body-heading">Model answer</p>
              <pre class="showcase-answer">${escapeHtml(model.answer)}</pre>
            </div>
          `;

        return `
          <details class="showcase-model">
            <summary>
              <div class="showcase-model__top">
                <div>
                  <span class="showcase-model__name"><span class="provider-dot" style="background:${scoreColor(model.provider)}"></span>${escapeHtml(model.label)}</span>
                </div>
                <span class="showcase-score${scoreClass}">${model.empty ? "No answer" : formatScore(model.averageScore)}</span>
              </div>
              <p class="showcase-headline" data-tone="${escapeAttribute(model.headlineTone)}">${escapeHtml(model.headline)}</p>
              <div class="showcase-checks">${checks}</div>
              <p class="showcase-preview">${escapeHtml(preview)}</p>
            </summary>
            <div class="showcase-model__body">
              <div>
                <p class="showcase-body-heading">Reviewer grade</p>
                <div class="showcase-grades">${grades}</div>
              </div>
              <div>
                <p class="showcase-body-heading">Reviewer summary</p>
                <p class="showcase-review-note">${escapeHtml(model.reviewExcerpt || model.headline)}</p>
              </div>
              ${answerBody}
              ${missed}
            </div>
          </details>
        `;
      })
      .join("");
  }

  function setupShowcaseImageToggle() {
    if (!refs.showcaseImageToggle || !refs.showcaseImagePanel) {
      return;
    }

    refs.showcaseImageToggle.addEventListener("click", () => {
      const isExpanded = refs.showcaseImageToggle.getAttribute("aria-expanded") === "true";
      const nextExpanded = !isExpanded;
      refs.showcaseImageToggle.setAttribute("aria-expanded", String(nextExpanded));
      refs.showcaseImageToggle.textContent = nextExpanded
        ? "Hide images from this case"
        : "Show images from this case";
      refs.showcaseImagePanel.hidden = !nextExpanded;
    });
  }

  function renderControls() {
    refs.viewControls.innerHTML = DATA.views
      .map((view) => {
        const active = view.id === state.viewId ? " is-active" : "";
        return `<button class="pill${active}" type="button" data-view="${view.id}">${view.label}</button>`;
      })
      .join("");

    refs.metricControls.innerHTML = Object.entries(metricConfig)
      .map(([id, config]) => {
        const active = id === state.metric ? " is-active" : "";
        return `<button class="pill${active}" type="button" data-metric="${id}">${config.label}</button>`;
      })
      .join("");

    refs.viewControls.querySelectorAll("[data-view]").forEach((button) => {
      button.addEventListener("click", () => {
        state.viewId = button.dataset.view;
        render();
      });
    });

    refs.metricControls.querySelectorAll("[data-metric]").forEach((button) => {
      button.addEventListener("click", () => {
        state.metric = button.dataset.metric;
        render();
      });
    });
  }

  function renderContext(view) {
    const sourceGraderText = view.sourceGraders.length
      ? view.sourceGraders.length > 1
        ? `This view averages the independent graders: ${view.sourceGraders.join(" + ")}.`
        : `This view shows one independent grader: ${view.sourceGraders[0]}.`
      : "This view shows one independent grader.";

    refs.resultsContext.textContent =
      `Surg Bench compares model performance across ${formatCount(DATA.meta.caseCount)} cases and ${formatCount(DATA.meta.subPromptCount)} numbered sub-prompts. ${sourceGraderText}`;
    refs.rankingTitle.textContent = metricConfig[state.metric].title;
    refs.rankingNote.textContent = metricConfig[state.metric].note;
    refs.heatmapTitle.textContent = `${metricConfig[state.metric].label} by category`;
    refs.heatmapLegend.style.background =
      state.metric === "rejectRate"
        ? "linear-gradient(90deg, oklch(0.95 0.03 152), oklch(0.71 0.13 28))"
        : "linear-gradient(90deg, oklch(0.96 0.03 28), oklch(0.68 0.14 154))";
  }

  function renderTakeaways(view, models) {
    const highlights = view.highlights;
    refs.takeawayCards.innerHTML = `
      <div class="takeaway-card">
        <strong>Best overall</strong>
        <span>${highlights.bestOverall.model} at ${formatScore(highlights.bestOverall.score)}</span>
      </div>
      <div class="takeaway-card">
        <strong>Best fully reliable</strong>
        <span>${highlights.bestReliable.model} with ${formatScore(highlights.bestReliable.score)} and no rejects</span>
      </div>
      <div class="takeaway-card">
        <strong>Largest refusal penalty</strong>
        <span>${highlights.largestPenalty.model} lost ${formatScore(highlights.largestPenalty.penalty)} to rejects</span>
      </div>
      <div class="takeaway-card">
        <strong>Most category wins</strong>
        <span>${highlights.mostCategoryWins.model} leads ${highlights.mostCategoryWins.wins} specialties</span>
      </div>
    `;

    refs.topTableBody.innerHTML = models
      .slice(0, 5)
      .map((model) => {
        const value = model.overall[metricConfig[state.metric].valueKey];
        return `
          <tr>
            <td><span class="provider-dot" style="background:${scoreColor(model.provider)}"></span>${model.label}</td>
            <td>${metricConfig[state.metric].formatter(value)}</td>
            <td>${formatPercent(model.overall.rejectRate)}</td>
            <td>${model.wins.zeroed}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderRankingChart(models) {
    const width = Math.max(refs.rankingChart.clientWidth, 640);
    const rowHeight = 34;
    const labelWidth = width < 820 ? 170 : 230;
    const valueWidth = 76;
    const left = 12;
    const top = 18;
    const plotWidth = width - labelWidth - valueWidth - left * 2;
    const height = top + models.length * rowHeight + 46;
    const maxValue =
      state.metric === "rejectRate"
        ? Math.max(0.05, Math.max(...models.map((item) => item.overall.rejectRate)) * 1.18)
        : 1;
    const ticks = state.metric === "rejectRate" ? 4 : 5;

    const axis = Array.from({ length: ticks + 1 }, (_, index) => {
      const value = maxValue * (index / ticks);
      const x = left + labelWidth + plotWidth * (index / ticks);
      const label = state.metric === "rejectRate" ? formatPercent(value) : value.toFixed(1);
      return `<g>
        <line x1="${x}" y1="${top - 10}" x2="${x}" y2="${height - 26}" stroke="color-mix(in srgb, var(--ink) 8%, transparent)" />
        <text x="${x}" y="${height - 6}" text-anchor="middle" fill="var(--muted)" font-size="11">${label}</text>
      </g>`;
    }).join("");

    const bars = models
      .map((model, index) => {
        const y = top + index * rowHeight;
        const value = model.overall[metricConfig[state.metric].valueKey];
        const widthValue = plotWidth * (value / maxValue);
        const tooltip = tooltipText([
          model.label,
          `${metricConfig[state.metric].label}: ${metricConfig[state.metric].formatter(value)}`,
          `Answered only: ${formatScore(model.overall.answered)}`,
          `Reject rate: ${formatPercent(model.overall.rejectRate)}`,
        ]);

        return `
          <g data-tooltip="${escapeAttribute(tooltip)}">
            <text x="${left}" y="${y + 21}" fill="var(--ink)" font-size="12">${escapeHtml(model.shortLabel)}</text>
            <rect x="${left + labelWidth}" y="${y + 8}" rx="999" ry="999" width="${plotWidth}" height="14" fill="color-mix(in srgb, var(--ink) 5%, white)" />
            <rect x="${left + labelWidth}" y="${y + 8}" rx="999" ry="999" width="${Math.max(widthValue, 2)}" height="14" fill="${scoreColor(model.provider)}" />
            <text x="${left + labelWidth + plotWidth + 10}" y="${y + 20}" fill="var(--ink)" font-size="12">${metricConfig[state.metric].formatter(value)}</text>
          </g>
        `;
      })
      .join("");

    refs.rankingChart.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Ranked model chart">
        ${axis}
        ${bars}
      </svg>
    `;
    attachTooltips(refs.rankingChart);
  }

  function renderScatter(models) {
    const width = Math.max(refs.scatterChart.clientWidth, 440);
    const height = 360;
    const margin = { top: 18, right: 22, bottom: 44, left: 56 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const maxReject = Math.max(0.03, ...models.map((model) => model.overall.rejectRate)) * 1.15;
    const minAnswered = Math.max(
      0.35,
      Math.floor((Math.min(...models.map((model) => model.overall.answered)) - 0.04) * 10) / 10
    );
    const maxAnswered = 0.98;
    const averageReject = models.reduce((sum, model) => sum + model.overall.rejectRate, 0) / models.length;
    const averageAnswered = models.reduce((sum, model) => sum + model.overall.answered, 0) / models.length;

    const x = (value) => margin.left + (value / maxReject) * plotWidth;
    const y = (value) =>
      margin.top + plotHeight - ((value - minAnswered) / (maxAnswered - minAnswered)) * plotHeight;

    const gridLines = Array.from({ length: 5 }, (_, index) => {
      const value = minAnswered + ((maxAnswered - minAnswered) * index) / 4;
      const py = y(value);
      return `
        <g>
          <line x1="${margin.left}" y1="${py}" x2="${margin.left + plotWidth}" y2="${py}" stroke="color-mix(in srgb, var(--ink) 8%, transparent)" />
          <text x="${margin.left - 10}" y="${py + 4}" text-anchor="end" fill="var(--muted)" font-size="11">${value.toFixed(2)}</text>
        </g>
      `;
    }).join("");

    const axisLines = Array.from({ length: 5 }, (_, index) => {
      const value = (maxReject * index) / 4;
      const px = x(value);
      return `
        <g>
          <line x1="${px}" y1="${margin.top}" x2="${px}" y2="${margin.top + plotHeight}" stroke="color-mix(in srgb, var(--ink) 8%, transparent)" />
          <text x="${px}" y="${height - 10}" text-anchor="middle" fill="var(--muted)" font-size="11">${formatPercent(value)}</text>
        </g>
      `;
    }).join("");

    const annotated = new Set();
    const topOverall = [...models].sort((a, b) => b.overall.zeroed - a.overall.zeroed)[0];
    const topReject = [...models].sort((a, b) => b.overall.rejectRate - a.overall.rejectRate)[0];
    annotated.add(topOverall.model);
    annotated.add(topReject.model);

    const points = models
      .map((model) => {
        const px = x(model.overall.rejectRate);
        const py = y(model.overall.answered);
        const tooltip = tooltipText([
          model.label,
          `Answered only: ${formatScore(model.overall.answered)}`,
          `Reject rate: ${formatPercent(model.overall.rejectRate)}`,
          `Zeroed: ${formatScore(model.overall.zeroed)}`,
        ]);
        const label = annotated.has(model.model)
          ? `<text x="${px + 10}" y="${py - 10}" fill="var(--ink)" font-size="11">${escapeHtml(model.shortLabel)}</text>`
          : "";
        return `
          <g data-tooltip="${escapeAttribute(tooltip)}">
            <circle cx="${px}" cy="${py}" r="6.5" fill="${scoreColor(model.provider)}" stroke="white" stroke-width="2"></circle>
            ${label}
          </g>
        `;
      })
      .join("");

    refs.scatterChart.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Answered score against reject rate">
        ${gridLines}
        ${axisLines}
        <line x1="${x(averageReject)}" y1="${margin.top}" x2="${x(averageReject)}" y2="${margin.top + plotHeight}" stroke="color-mix(in srgb, var(--rust) 45%, transparent)" stroke-dasharray="4 4"></line>
        <line x1="${margin.left}" y1="${y(averageAnswered)}" x2="${margin.left + plotWidth}" y2="${y(averageAnswered)}" stroke="color-mix(in srgb, var(--forest) 45%, transparent)" stroke-dasharray="4 4"></line>
        ${points}
        <text x="${width / 2}" y="${height - 2}" text-anchor="middle" fill="var(--muted)" font-size="12">Reject rate</text>
        <text x="16" y="${height / 2}" transform="rotate(-90 16 ${height / 2})" text-anchor="middle" fill="var(--muted)" font-size="12">Answered-only score</text>
      </svg>
    `;
    attachTooltips(refs.scatterChart);
  }

  function buildLogTicks(minValue, maxValue) {
    const ticks = [];
    const startExp = Math.floor(Math.log10(minValue));
    const endExp = Math.ceil(Math.log10(maxValue));

    for (let exp = startExp; exp <= endExp; exp += 1) {
      [1, 2, 5].forEach((multiplier) => {
        const tick = multiplier * 10 ** exp;
        if (tick >= minValue * 0.96 && tick <= maxValue * 1.04) {
          ticks.push(tick);
        }
      });
    }

    return ticks.length ? ticks : [minValue, maxValue];
  }

  function renderLatencyScatter(models) {
    const timedModels = models.filter((model) => model.latency && model.latency.medianMs > 0);

    if (!timedModels.length) {
      refs.latencyChart.innerHTML = '<p class="module-note">Response-time data is not available for this view.</p>';
      return;
    }

    const width = Math.max(refs.latencyChart.clientWidth, 440);
    const height = 360;
    const margin = { top: 18, right: 22, bottom: 48, left: 56 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const rawMinSeconds = Math.min(...timedModels.map((model) => model.latency.medianMs / 1000));
    const rawMaxSeconds = Math.max(...timedModels.map((model) => model.latency.medianMs / 1000));
    const minSeconds = Math.max(1, rawMinSeconds * 0.82);
    const maxSeconds = rawMaxSeconds * 1.16;
    let logMin = Math.log10(minSeconds);
    let logMax = Math.log10(maxSeconds);

    if (logMax - logMin < 0.35) {
      logMin -= 0.175;
      logMax += 0.175;
    }

    const minAnswered = Math.max(
      0.35,
      Math.floor((Math.min(...timedModels.map((model) => model.overall.answered)) - 0.04) * 10) / 10
    );
    const maxAnswered = 0.98;
    const averageSeconds =
      timedModels.reduce((sum, model) => sum + model.latency.medianMs / 1000, 0) / timedModels.length;
    const averageAnswered =
      timedModels.reduce((sum, model) => sum + model.overall.answered, 0) / timedModels.length;

    const x = (value) =>
      margin.left + ((Math.log10(value) - logMin) / (logMax - logMin)) * plotWidth;
    const y = (value) =>
      margin.top + plotHeight - ((value - minAnswered) / (maxAnswered - minAnswered)) * plotHeight;

    const gridLines = Array.from({ length: 5 }, (_, index) => {
      const value = minAnswered + ((maxAnswered - minAnswered) * index) / 4;
      const py = y(value);
      return `
        <g>
          <line x1="${margin.left}" y1="${py}" x2="${margin.left + plotWidth}" y2="${py}" stroke="color-mix(in srgb, var(--ink) 8%, transparent)" />
          <text x="${margin.left - 10}" y="${py + 4}" text-anchor="end" fill="var(--muted)" font-size="11">${value.toFixed(2)}</text>
        </g>
      `;
    }).join("");

    const axisLines = buildLogTicks(minSeconds, maxSeconds)
      .map((value) => {
        const px = x(value);
        return `
          <g>
            <line x1="${px}" y1="${margin.top}" x2="${px}" y2="${margin.top + plotHeight}" stroke="color-mix(in srgb, var(--ink) 8%, transparent)" />
            <text x="${px}" y="${height - 10}" text-anchor="middle" fill="var(--muted)" font-size="11">${formatDuration(value * 1000)}</text>
          </g>
        `;
      })
      .join("");

    const annotated = new Set();
    const bestAnswered = [...timedModels].sort(
      (a, b) => b.overall.answered - a.overall.answered || a.latency.medianMs - b.latency.medianMs
    )[0];
    const fastest = [...timedModels].sort(
      (a, b) => a.latency.medianMs - b.latency.medianMs || b.overall.answered - a.overall.answered
    )[0];
    annotated.add(bestAnswered.model);
    annotated.add(fastest.model);

    const points = timedModels
      .map((model) => {
        const medianSeconds = model.latency.medianMs / 1000;
        const px = x(medianSeconds);
        const py = y(model.overall.answered);
        const tooltip = tooltipText([
          model.label,
          `Answered only: ${formatScore(model.overall.answered)}`,
          `Median time: ${formatDuration(model.latency.medianMs)}`,
          `P90 time: ${formatDuration(model.latency.p90Ms)}`,
          `Mean time: ${formatDuration(model.latency.meanMs)}`,
          `Timed cases: ${formatCount(model.latency.timedCaseCount)} / ${formatCount(model.latency.totalCaseCount)}`,
        ]);
        const label = annotated.has(model.model)
          ? `<text x="${px + 10}" y="${py - 10}" fill="var(--ink)" font-size="11">${escapeHtml(model.shortLabel)}</text>`
          : "";
        return `
          <g data-tooltip="${escapeAttribute(tooltip)}">
            <circle cx="${px}" cy="${py}" r="6.5" fill="${scoreColor(model.provider)}" stroke="white" stroke-width="2"></circle>
            ${label}
          </g>
        `;
      })
      .join("");

    refs.latencyChart.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Answered score against response time">
        ${gridLines}
        ${axisLines}
        <line x1="${x(averageSeconds)}" y1="${margin.top}" x2="${x(averageSeconds)}" y2="${margin.top + plotHeight}" stroke="color-mix(in srgb, var(--rust) 45%, transparent)" stroke-dasharray="4 4"></line>
        <line x1="${margin.left}" y1="${y(averageAnswered)}" x2="${margin.left + plotWidth}" y2="${y(averageAnswered)}" stroke="color-mix(in srgb, var(--forest) 45%, transparent)" stroke-dasharray="4 4"></line>
        ${points}
        <text x="${width / 2}" y="${height - 2}" text-anchor="middle" fill="var(--muted)" font-size="12">Median answered-case time (log scale)</text>
        <text x="16" y="${height / 2}" transform="rotate(-90 16 ${height / 2})" text-anchor="middle" fill="var(--muted)" font-size="12">Answered-only score</text>
      </svg>
    `;
    attachTooltips(refs.latencyChart);
  }

  function renderHeatmap(models) {
    const metricKey = metricConfig[state.metric].valueKey;
    const headers = DATA.meta.categories
      .map((category) => `<th scope="col">${escapeHtml(category.shortLabel)}</th>`)
      .join("");

    const rows = models
      .map((model) => {
        const cells = DATA.meta.categories
          .map((category) => {
            const cell = model.categories[category.id];
            const value = cell ? cell[metricKey] : 0;
            const text = state.metric === "rejectRate" ? formatPercent(value) : formatScore(value);
            const tooltip = tooltipText([
              model.label,
              category.label,
              `${metricConfig[state.metric].label}: ${text}`,
            ]);
            return `
              <td>
                <div class="heatmap-cell" style="background:${heatColor(value, state.metric)}" data-tooltip="${escapeAttribute(tooltip)}">${text}</div>
              </td>
            `;
          })
          .join("");

        return `
          <tr>
            <th scope="row">${escapeHtml(model.shortLabel)}</th>
            ${cells}
          </tr>
        `;
      })
      .join("");

    refs.heatmapChart.innerHTML = `
      <table class="heatmap-table">
        <thead>
          <tr>
            <th scope="col"></th>
            ${headers}
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    attachTooltips(refs.heatmapChart);
  }

  function renderLeaders(view, models) {
    const leaderModels = [...models]
      .filter((model) => model.wins.zeroed > 0)
      .sort((a, b) => b.wins.zeroed - a.wins.zeroed);
    const maxWins = Math.max(...leaderModels.map((model) => model.wins.zeroed), 1);

    refs.leaderChart.innerHTML = leaderModels
      .map(
        (model) => `
          <div class="leader-row">
            <span>${model.label}</span>
            <div class="leader-row__track">
              <div class="leader-row__fill" style="width:${(model.wins.zeroed / maxWins) * 100}%"></div>
            </div>
            <strong>${model.wins.zeroed}</strong>
          </div>
        `
      )
      .join("");

    refs.leaderCards.innerHTML = view.categoryLeaders
      .map(
        (leader) => `
          <div class="leader-card">
            <span class="leader-card__label">${leader.label}</span>
            <strong>${leader.zeroed.label}</strong>
            <span>${leader.zeroed.provider}</span>
            <span>Zeroed score ${formatScore(leader.zeroed.score)}</span>
          </div>
        `
      )
      .join("");
  }

  function render() {
    const view = getCurrentView();
    const rankedModels = sortModels(view.models);

    renderControls();
    renderContext(view);
    renderTakeaways(view, rankedModels);
    renderRankingChart(rankedModels);
    renderScatter(view.models);
    renderLatencyScatter(view.models);
    renderHeatmap(rankedModels);
    renderLeaders(view, view.models);
  }

  function setupReveal() {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.05 }
    );

    document.querySelectorAll(".reveal").forEach((node) => observer.observe(node));
  }

  function init() {
    renderMeta();
    renderShowcase();
    setupShowcaseImageToggle();
    render();
    setupReveal();

    let resizeFrame = null;
    window.addEventListener("resize", () => {
      if (resizeFrame) {
        cancelAnimationFrame(resizeFrame);
      }
      resizeFrame = requestAnimationFrame(() => render());
    });
  }

  init();
})();
