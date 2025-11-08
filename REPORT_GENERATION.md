# Report Generation

This document explains how the HTML and Markdown reports are generated.

## Overview

The reporting system generates three types of reports from the graded CSV files:

1. **HTML Report (Full)** (`data/out/graded/report.html`) - Complete interactive report with all details
2. **HTML Report (Public)** (`data/out/graded/report_public.html`) - Public-friendly version without copyrighted questions
3. **Markdown Summary** (`data/out/reports/grading_stats_summary.md`) - Static text summary

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

This makes it **~55% smaller** (33MB vs 74MB) and safe to publish without copyright concerns.

## Generating Reports

### Using the Standalone Script
```bash
python3 generate_report.py
```

This automatically:
- Finds all `scores__*.csv` files in `data/out/graded/`
- Includes empty answer data from `empty_answers__*.csv` files
- Generates all three reports simultaneously
- Shows all output paths in the console:
  ```
  Reports generated:
    HTML (full): data/out/graded/report.html
    HTML (public): data/out/graded/report_public.html
    Markdown: data/out/reports/grading_stats_summary.md
  ```

### Using the CLI
```bash
python -m src.evalsys.cli report \
  --scores data/out/graded \
  --dataset data/out/dataset.jsonl \
  --out-html data/out/graded/report.html
```

## Data Consistency

All three reports are generated from the same data pipeline using the `emit_report()` function in `src/evalsys/reporting.py`. This ensures:

✅ All numerical statistics are identical across reports
✅ Same calculation methods for averages, percentages, and scores
✅ Consistent model ordering and ranking
✅ Synchronized updates when data changes
✅ Public report has exact same statistics as full report (just without questions)

## Report Locations

- **HTML Report (Full)**: `data/out/graded/report.html` (~74MB)
- **HTML Report (Public)**: `data/out/graded/report_public.html` (~33MB)
- **Markdown Summary**: `data/out/reports/grading_stats_summary.md` (~15KB)
- **Source Data**: `data/out/graded/scores__*.csv` and `empty_answers__*.csv`

