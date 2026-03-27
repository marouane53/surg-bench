# Report Generation

This document explains how the HTML and Markdown reports are generated.

## Overview

The reporting system now emits six artifacts from the graded CSV files:

1. **HTML Report (Full)** (`data/out/graded/report.html`) – Complete interactive report with all details
2. **HTML Report (Compact)** (`data/out/graded/report_compact.html`) – Question text + scores, without model answers, justifications, images, or grader comparisons
3. **HTML Report (Public)** (`data/out/graded/report_public.html`) – Public-friendly version without copyrighted questions
4. **Markdown Summary** (`data/out/reports/grading_stats_summary.md`) – Static text summary
5. **Structured Data Bundle** (`data/out/graded/report_data.json`) – Machine-readable dump of every ranking, statistic, and graded record
6. **Rankings CSV** (`data/out/graded/report_rankings.csv`) – Flat table of model rankings per view/metric for quick spreadsheet work

All reports contain the **same numerical statistics** and are generated from the same underlying data.

## Data Included in All Reports

### Aggregate Statistics
- Total questions, models evaluated, graders included
- Weighted mean scores (zeroed and answered-only)
- Score spread (population standard deviation)
- Empty answer counts

### Per-Model Metrics
- Answered-only averages (excludes rejections)
- Zeroed averages (with rejects scored as zero)
- Rejection rates and percentages
- Provider information

### Category Breakdown
- Category leaders for each metric type (exclude, zeroed, reject)
- Per-category performance for each model
- Model rankings with per-category averages

### Per-Grader Views
All statistics above are broken down by grader (e.g., gemini-2.5-flash, gpt-5-mini)

### Interactive Features (HTML only)
- **Interactive visualizations** - Charts and rankings
- **Sorting and filtering** - Interactive data exploration
- **Empty answer summaries** - Per-model empty answer tracking

## Additional Data in Full HTML Report Only

The **full HTML report** (`report.html`) also includes copyrighted content:
- **Per-question details** - Individual question scores for each model
- **Question text and reference answers**
- **Model answers and justifications**
- **Grader comparisons** - Side-by-side comparison showing where graders disagree on specific questions
- **Images** - Associated question images

## Compact HTML Report

The **compact HTML report** (`report_compact.html`) is designed for sharing when the full report is too large:

✅ **Includes:**
- Aggregate statistics, rankings, and category breakdowns
- Per-question scores and question text

❌ **Omits:**
- Model answers, justifications, missed points
- Images
- Grader comparison drilldowns

## Public HTML Report

The **public HTML report** (`report_public.html`) is designed for sharing and publication:

✅ **Includes:**
- All aggregate statistics and model rankings
- Interactive charts and visualizations
- Category breakdowns
- Model comparison metrics
- Empty answer summaries

❌ **Excludes (for copyright protection):**
- Individual question text and answers
- Per-question model responses
- Question-level grader comparisons
- Associated images

This makes it much smaller and safe to publish without copyright concerns.

## Structured Data Bundle (`report_data.json`)

Every time `emit_report()` runs, it now writes `report_data.json` next to the HTML reports. This JSON file is designed for downstream analysis or sharing with AI assistants when the HTML is too large. It includes:

- **Metadata**: generation timestamp, source paths, model/question counts, and the high-agreement thresholds
- **Per-view statistics**: model averages, rejection stats, category breakdowns, and empty-answer counts for each grader view (including the "All graders" aggregate)
- **Flattened graded records**: one entry per `(grader, model, question)` containing the question text, reference answer, model answer, justification, and score (images are intentionally omitted)
- **High-agreement findings**: questions where at least two graders scored ≥0.8 on the same model answer, along with their justifications
- **Comparison pairs**: grader disagreement entries without embedded image payloads

Because it is pure JSON (≈5–8 MB for the full benchmark), it is easy to version, diff, or feed to other tooling.

## Rankings CSV (`report_rankings.csv`)

For spreadsheet workflows, every ranking table that appears in the HTML is emitted as a tidy CSV. Each row captures: view ID/label, metric (`zeroed`, `answered_only`, or `reject_rate`), rank, model, provider, average score, answered count, and reject count. Analysts can filter/sort in Excel, Sheets, or pandas without parsing HTML.

## Generating Reports

### Using the Standalone Script
```bash
python3 generate_report.py
```

This automatically:
- Finds all `scores__*.csv` files in `data/out/graded/`
- Includes empty answer data from `empty_answers__*.csv` files
- Generates all report artifacts (HTML, markdown, JSON, CSV) simultaneously
- Shows all output paths in the console:
  ```
  Reports generated:
    HTML (full): data/out/graded/report.html
    HTML (compact): data/out/graded/report_compact.html
    HTML (public): data/out/graded/report_public.html
    Markdown: data/out/reports/grading_stats_summary.md
    Data bundle: data/out/graded/report_data.json
    Rankings CSV: data/out/graded/report_rankings.csv
  ```

### Using the CLI
```bash
python -m src.evalsys.cli report \
  --scores data/out/graded \
  --dataset data/out/dataset.jsonl \
  --out-html data/out/graded/report.html
```

## Data Consistency

All report artifacts are generated from the same data pipeline using the `emit_report()` function in `src/evalsys/reporting.py`. This ensures:

✅ All numerical statistics are identical across reports
✅ Same calculation methods for averages, percentages, and scores
✅ Consistent model ordering and ranking
✅ Synchronized updates when data changes
✅ Public report has exact same statistics as full report (just without questions)

## Report Locations

- **HTML Report (Full)**: `data/out/graded/report.html` (largest; includes per-question answers + images)
- **HTML Report (Compact)**: `data/out/graded/report_compact.html` (shareable; question text + scores only)
- **HTML Report (Public)**: `data/out/graded/report_public.html` (shareable; no question text)
- **Markdown Summary**: `data/out/reports/grading_stats_summary.md`
- **Structured Data Bundle**: `data/out/graded/report_data.json` (largest data export)
- **Rankings CSV**: `data/out/graded/report_rankings.csv`
- **Source Data**: `data/out/graded/scores__*.csv` and `empty_answers__*.csv`
