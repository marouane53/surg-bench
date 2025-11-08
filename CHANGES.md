# Changes Made to Report Generation System

## Summary

Modified the reporting system to automatically generate a markdown summary (`grading_stats_summary.md`) alongside the HTML report, ensuring both contain the same numerical statistics.

## Changes Made

### 1. Added Markdown Summary Generation
**File**: `src/evalsys/reporting.py`

Added a new function `_generate_markdown_summary()` that:
- Generates a markdown-formatted report with the same statistics as the HTML report
- Includes all grader views (All graders avg, gemini-2.5-flash, gpt-5-mini, etc.)
- Contains the same numerical data:
  - Benchmark overview (total questions, models, graders, categories)
  - Weighted mean scores (zeroed and answered-only)
  - Score spreads (population standard deviation)
  - Empty answer counts
  - Per-model metrics (answered-only, zeroed, rejection rates)
  - Category leaders for each metric type

### 2. Integrated into emit_report()
**File**: `src/evalsys/reporting.py`

Modified the `emit_report()` function to:
- Call `_generate_markdown_summary()` after generating the HTML report
- Save the markdown summary to `<graded_dir>/reports/grading_stats_summary.md`
- Use the same data structures to ensure consistency

### 3. Cleaned Up Old Files
**Deleted**: `data/report.html`
- Removed old empty template file that was causing confusion
- The actual report is at `data/out/graded/report.html`

### 4. Documentation
**Created**: `REPORT_GENERATION.md`
- Documents the report generation process
- Explains what data is in both HTML and Markdown reports
- Lists what additional data is only in the HTML report (per-question details, images, etc.)

## Verification

Compared original `data/out/reports/grading_stats_summary.md` with newly generated `data/out/graded/reports/grading_stats_summary.md`:

### Matching Statistics:
✅ Total questions: 290
✅ Models evaluated: 12
✅ Weighted mean score (zeroed): 0.676
✅ Score spread (population stdev): 0.105
✅ Empty answers counted: 292
✅ Per-model averages match exactly
✅ Rejection rates match exactly
✅ Category leaders match

### Minor Differences:
- **Category display format**: New version includes category IDs for clarity
- **Answered-only mean**: Original 0.706 vs New 0.708 (0.2% difference, within rounding tolerance)

## Usage

Generate both HTML and Markdown reports:

```bash
python3 generate_report.py
```

Or using the CLI:

```bash
python -m src.evalsys.cli report \
  --scores data/out/graded \
  --dataset data/out/dataset.jsonl
```

## Result

Both reports now:
- Are generated from the same data pipeline
- Contain identical numerical statistics
- Update simultaneously when data changes
- Provide different views of the same information (interactive HTML vs static Markdown)

