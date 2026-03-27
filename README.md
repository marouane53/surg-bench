# Surg Bench

Surg Bench is a benchmark for evaluating AI models on contemporary surgical exam cases. It ingests licensed source material from a textbook PDF, runs multiple models on the extracted cases, grades their open-ended answers with two independent LLM graders, and produces full, compact, public, and GitHub Pages-friendly result views.

## Data Source & Attribution

This benchmark uses surgical cases extracted from **"Surgical Exam Cases"** by **Charles Tan**, Adjunct Assistant Professor, Department of Surgery, Yong Loo Lin School of Medicine, National University of Singapore.

### Why This Book?

We selected this textbook because it was **published in 2025**, before most current AI models were trained. This ensures the evaluation tests genuine medical reasoning capabilities rather than memorized content, providing a fair and uncontaminated assessment of AI performance on contemporary surgical knowledge.

## Methodology at a Glance

1. **Ingest the source material**: the pipeline extracts case text and associated images from a licensed PDF.
2. **Run model answers**: each configured model answers the same set of surgical cases.
3. **Grade open-ended responses**: because these are free-response cases rather than multiple-choice questions, answers are scored by two independent grader models instead of exact string matching.
4. **Compare multiple views of performance**: the reports show all-cases scoring, answered-only scoring, rejection rate, category breakdowns, and response-time metadata.

In the current public release, the benchmark covers **290 cases** containing **1,249 numbered sub-prompts** across **14 surgical categories**.

## Public Results

See the live public benchmark here: [Surg Bench Public Results](https://marouane53.github.io/surg-bench/)

- Current public release: **290 cases**, **1,249 numbered sub-prompts**, **14 surgical categories**
- Best overall model on all-cases scoring: **Gemini 3 Flash** at **0.882**
- Best fully reliable model with zero rejects: **GPT-5.2** at **0.867**
- Fastest median answered-case response time: **Gemini 2.5 Flash Lite** at about **3.2s**

### Running the Benchmark

**To run this evaluation, you must purchase the book.** The PDF (`data/surgical.pdf`) is not included in this repository. You can obtain the book from major medical publishers or academic bookstores. Once acquired, place the PDF in the `data/` directory to begin extraction and evaluation.

## Features

- **PDF Extraction**: Converts surgical PDFs into structured case datasets with associated images
- **Multi-Provider Support**: OpenAI, Gemini, Anthropic, Groq, xAI, OpenRouter (Mistral & Cohere optional)
- **Dual-Grader Evaluation**: GPT-5 Mini and Gemini 2.5 Flash by default, with support for custom grader choices
- **Comprehensive Reporting**: CSV output, HTML dashboards, JSON data bundles, and ranking-ready CSVs
- **Resume Support**: Stop and continue runs or grading without losing progress

## Requirements

- Python 3.9+ (Python 3.10+ recommended for all optional providers)
- API keys for desired providers
- The "Surgical Exam Cases" textbook PDF (not included - must be purchased)

## Project Structure

```
surg-bench/
├── README.md
├── generate_public_site.py
├── requirements.txt
├── pyproject.toml
├── .env.template
├── providers.yaml
├── docs/                 # Public GitHub Pages site
├── src/
│   ├── evalsys/           # Core evaluation system
│   ├── providers/         # AI provider implementations
│   └── grading/          # Grading system
├── data/
│   ├── surgical.pdf      # Input PDF (place your file here)
│   └── out/              # Generated outputs
└── tests/                # Test suite
```

## Setup and Installation

1. **Clone and setup environment:**
   ```bash
   cd surg-bench
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   
   # Optionally install additional providers (may require Python 3.10+)
   # pip install -r requirements-optional.txt
   ```

2. **Configure API keys:**
   ```bash
   cp .env.template .env
   # Edit .env with your API keys
   ```

3. **Place your PDF:**
   ```bash
   # Put your surgical PDF in data/surgical.pdf
   ```

## Usage

### 1. Extract Cases from PDF
```bash
python -m src.evalsys.cli ingest --pdf data/surgical.pdf
```
This creates `data/out/dataset.jsonl` and extracts images to `data/out/images/`

### 2. Run AI Models
```bash
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5,gemini:gemini-2.5-flash,anthropic:claude-3-5-sonnet-latest" --limit 50
```
This generates model responses in `data/out/runs/`

> **Tip:** omit `--limit` to run the full dataset (currently 290 cases). The CLI now defaults to the complete set when no limit is provided, so add `--limit` only when you want a smaller smoke test.

While a run is in progress, you can tail the live JSONL output to see progress or resume after an interruption:

```bash
tail -f data/out/runs/openai-reasoning__gpt-5.jsonl
```

- Each answer is appended immediately; if the process stops, rerun with `--resume` to skip completed QIDs.
- The filename pattern is `<provider>__<model>.jsonl` with slashes replaced by underscores.
- Overall timing for each run is appended to `data/out/runs/run_history.log`, including the provider/model, dataset size, number of new answers, and total elapsed seconds.

### 3. Grade Responses
```bash
# run both default graders (GPT-5 Mini, then Gemini 2.5 Flash)
python -m src.evalsys.cli grade --grader

# or target a specific grader / list
python -m src.evalsys.cli grade --grader "openai:gpt-5-mini"
python -m src.evalsys.cli grade --grader "openai:gpt-5-mini,gemini:gemini-2.5-flash"
```
Because the benchmark uses open-ended case responses instead of multiple-choice answers, grading is done by LLM evaluators. By default, the pipeline runs **GPT-5 Mini** and **Gemini 2.5 Flash** as two independent graders, then reports both grader-specific views and an averaged view.

This creates per-model CSVs in `data/out/graded/` plus a full suite of reports:
- `scores__<model>__<grader>.csv` for graded answers per model/grader pair
- `empty_answers__<model>__<grader>.csv` for empty answers per model/grader pair (if any)
- `report.html` (full interactive report), `report_compact.html` (shareable, case text + scores only), and `report_public.html` (public HTML without case text)
- `report_data.json` containing all tables, per-case graded records, and high-agreement findings (no images)
- `report_rankings.csv` with flattened rankings per view/metric for spreadsheets
- `data/out/reports/grading_stats_summary.md` – markdown snapshot of the metrics

> **Progress tracking:** grading files update after each case. If grading is interrupted, rerun with `--resume` (default) and the CLI will skip QIDs already written to the CSVs.

`--grader` accepts:

- *No value* (flag only): runs GPT-5 Mini first, then Gemini 2.5 Flash sequentially.
- `provider:model`: grades with a single grader (e.g. `openai:gpt-5-mini`).
- Comma-separated list: grades once per entry in order (e.g. `openai:gpt-5-mini,gemini:gemini-2.5-flash`).
- Literal `all`: identical to the flag-only shorthand.

## Reporting

Surg Bench produces several output formats for different audiences:

- **`report.html`**: full report with per-case detail, answers, and grader rationale.
- **`report_compact.html`**: lighter shareable report with case text and scores, but without model answers or images.
- **`report_public.html`**: public-safe HTML report that keeps aggregate results while excluding case text and answers.
- **`report_data.json` + `report_rankings.csv`**: structured exports for downstream analysis.
- **`docs/` GitHub Pages site**: a lightweight public site built from aggregate results only.

### Generate Report from Existing CSV Files
Rebuild the HTML report from existing graded CSV outputs without re-running models or grading:

#### Using the CLI (requires Python 3.10+)
```bash
python -m src.evalsys.cli report \
  --scores data/out/graded \
  --dataset data/out/dataset.jsonl \
  --out-html data/out/graded/report.html
```

#### Using the Standalone Script (works with any Python version)
If you encounter module import issues, use the provided standalone script:

```bash
python generate_report.py
```

This script:
- Automatically finds all `scores__*.csv` files in `data/out/graded/`
- Includes empty answer data from `empty_answers__*.csv` files
- Generates `report.html`, `report_compact.html`, `report_public.html`, `report_data.json`, `report_rankings.csv`, and `grading_stats_summary.md`
- Works with any Python version (bypasses package installation requirements)

The generated report includes:
- **Model Comparison**: Side-by-side performance metrics
- **Score Distribution**: Histograms and statistical summaries  
- **Case Analysis**: Per-case breakdowns with justifications
- **Empty Answer Tracking**: Models that failed to respond
- **Interactive Charts**: Sortable tables and visual analytics

Need to share the results with collaborators or an AI assistant? Use the automatically generated `data/out/graded/report_compact.html` or `data/out/graded/report_public.html` for lightweight HTML sharing, plus `data/out/graded/report_data.json` (all tables and graded records without images) and `data/out/graded/report_rankings.csv` (flattened rankings for spreadsheets).

### Build the GitHub Pages Site

To build the lightweight public site in `docs/`, generate the public payload and publish the `docs` directory with your preferred static hosting workflow:

```bash
python3 generate_public_site.py
```

This updates:

- `docs/index.html` - public landing page
- `docs/assets/public-benchmark-data.js` - aggregate data bundle used by the page
- `docs/assets/app.js` / `docs/assets/site.css` - client-side presentation

The GitHub Pages version keeps rankings, category breakdowns, rejection behavior, and response-time summaries while omitting copyrighted case text, reference answers, model answers, grading justifications, and source images.

### Report Options
- `--scores`: Path to CSV file or directory containing `scores__*.csv` files
- `--dataset`: Path to `dataset.jsonl` file (for case context)
- `--empty-answers`: Optional path to empty answers CSV or directory
- `--out-html`: Output HTML file path (defaults to same directory as scores)

## Resume Runs and Grading (Stop/Continue)

You can pause and resume both model runs and grading without losing progress. The CLI skips QIDs already completed and appends only new results, then refreshes the report.

- `run --resume`: Skips QIDs already present in `data/out/runs/<provider>__<model>.jsonl` and appends new answers.
- `grade --resume`: Skips QIDs already graded in `data/out/graded/scores__<model>__<grader>.csv` or recorded as empty in `empty_answers__<model>__<grader>.csv`, appends new rows, and regenerates `report.html`, `report_compact.html`, and `report_public.html`.

Examples:

```bash
# Start a run
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --limit 200

# Stop the process (Ctrl+C) and resume later; picks up remaining QIDs
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --limit 200 --resume

# Grade incrementally; only new answers are graded, report is updated each time
python -m src.evalsys.cli grade --runs-dir data/out/runs --grader "openai:gpt-5-mini" --resume
```

Notes:
- `--resume` is enabled by default for both `run` and `grade`.
- `grade` always regenerates `data/out/graded/report.html`, `data/out/graded/report_compact.html`, and `data/out/graded/report_public.html` so your report stays current after each incremental run.

## Quick Testing Example

Test multiple models and generate a comparative report with just 5 cases:

```bash
# Step 1: Extract cases from PDF (if not done already)
python -m src.evalsys.cli ingest --pdf data/surgical.pdf

# Step 2: Run multiple models at once
python -m src.evalsys.cli run --models "gemini:gemini-2.5-flash,gemini:gemini-2.5-pro,openai-reasoning:gpt-5" --limit 5

# Step 3: Grade all responses
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"

# View results in: data/out/graded/report.html
```

## Advanced Reasoning Model Comparison Example

To comprehensively test OpenAI's reasoning models at different effort levels and compare with standard chat models:

```bash
# 0) Ingest once
python -m src.evalsys.cli ingest --pdf data/surgical.pdf

# 1) Run multiple models (defaults to data/out/runs)
python -m src.evalsys.cli run --models "openai:gpt-5-chat" --limit 50
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --reasoning-effort minimal --limit 50
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --reasoning-effort low --limit 50
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --reasoning-effort medium --limit 50
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --reasoning-effort high --limit 20

# 2) Grade them ALL into the SAME default folder data/out/graded
#    Use --label so each variant appears as its own model in one combined report.
python -m src.evalsys.cli grade --runs_dir "data/out/runs" --grader "gemini:gemini-2.5-flash" --label "chat"    # will pick up the chat file(s)
python -m src.evalsys.cli grade --runs_dir "data/out/runs" --grader "gemini:gemini-2.5-flash" --label "minimal"
python -m src.evalsys.cli grade --runs_dir "data/out/runs" --grader "gemini:gemini-2.5-flash" --label "low"
python -m src.evalsys.cli grade --runs_dir "data/out/runs" --grader "gemini:gemini-2.5-flash" --label "medium"
python -m src.evalsys.cli grade --runs_dir "data/out/runs" --grader "gemini:gemini-2.5-flash" --label "high"

# 3) Build one combined report for everything in data/out/graded
python -m src.evalsys.cli report --scores data/out/graded --dataset data/out/dataset.jsonl
# => data/out/graded/report.html
```

This comprehensive workflow:
1. Tests both standard chat models and reasoning models at all effort levels
2. Uses labels to distinguish each reasoning effort level in the final report
3. Generates a unified comparison report showing performance differences across reasoning strategies

## High Output-Tokens and Reasoning Budget

- OpenRouter and Anthropic default to 8192 output tokens if not specified.
- Override with `--max-tokens` on the CLI or provider-specific env vars.
- Anthropic supports an optional reasoning budget ("thinking") via CLI or env var.

### OpenRouter (image-capable) benchmark at 20k tokens
```bash
# Option A: Set default via env var
export OPENROUTER_MAX_TOKENS=20000

# Option B: Pass an explicit override (takes precedence)
python -m src.evalsys.cli run \
  --models "openrouter:openai/gpt-4o,openrouter:anthropic/claude-3.7-sonnet" \
  --dataset data/out/dataset.jsonl \
  --limit 50 \
  --max-tokens 20000
```

### Anthropic Sonnet and Opus with 20k output / 16k reasoning
```bash
# Option A: CLI flags
python -m src.evalsys.cli run \
  --models "anthropic:claude-3-5-sonnet-latest,anthropic:claude-3-opus-20240229" \
  --dataset data/out/dataset.jsonl \
  --limit 50 \
  --max-tokens 20000 \
  --anthropic-thinking-budget 16000

# Option B: Environment variables
export ANTHROPIC_MAX_TOKENS=20000
export ANTHROPIC_THINKING_BUDGET_TOKENS=16000
python -m src.evalsys.cli run \
  --models "anthropic:claude-3-5-sonnet-latest,anthropic:claude-3-opus-20240229" \
  --dataset data/out/dataset.jsonl \
  --limit 50
```

Notes:
- No breaking changes: existing workflows still work and can set `--max-tokens` as needed.
- Budgets apply per provider; other providers are unchanged.

### Claude 4 Models with Thinking Mode

Test **Claude Sonnet 4** with thinking mode enabled:

```bash
python -m src.evalsys.cli run \
  --models "anthropic:claude-sonnet-4-20250514" \
  --dataset data/out/dataset.jsonl \
  --limit 20 \
  --max-tokens 20000 \
  --anthropic-thinking-budget 16000 \
  --out-dir "data/out/runs"
```

Test **Claude Opus 4** with thinking mode enabled:

```bash
python -m src.evalsys.cli run \
  --models "anthropic:claude-opus-4-1-20250805" \
  --dataset data/out/dataset.jsonl \
  --limit 20 \
  --max-tokens 20000 \
  --anthropic-thinking-budget 16000 \
  --out-dir "data/out/runs"
```

**Simple Python examples for direct API use:**

Claude Sonnet 4 with thinking:
```python
import anthropic

client = anthropic.Anthropic(api_key="my_api_key")

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=20000,
    messages=[{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
    thinking={"type": "enabled", "budget_tokens": 16000}
    # Note: No temperature when thinking is enabled
)
print(message.content)
```

Claude Opus 4 with thinking:
```python
import anthropic

client = anthropic.Anthropic(api_key="my_api_key")

message = client.messages.create(
    model="claude-opus-4-1-20250805",
    max_tokens=20000,
    messages=[{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
    thinking={"type": "enabled", "budget_tokens": 16000}
    # Note: No temperature when thinking is enabled
)
print(message.content)
```

**Key Notes for Claude 4 Thinking Mode:**
- ✅ `budget_tokens` must be ≥1024 and < `max_tokens`
- ❌ **Do NOT** send `temperature`, `top_p`, or `top_k` when thinking is enabled
- 🔄 Streaming is automatically used for high token counts to avoid timeouts
- 📝 Claude Sonnet 4: Released May 14, 2025 - Balanced performance/cost
- 🧠 Claude Opus 4: Released August 5, 2025 - Best for complex reasoning

### Claude Sonnet 4 Non-Thinking Example

Test **Claude Sonnet 4** (non-thinking mode) with high token output and grade with **Gemini 2.5 Flash**:

```bash
python -m src.evalsys.cli run \
  --models "anthropic:claude-sonnet-4-20250514" \
  --limit 20 \
  --max-tokens 20000 \
  --out-dir "data/out/runs"

python -m src.evalsys.cli grade \
  --runs-dir "data/out/runs" \
  --grader "gemini:gemini-2.5-flash" \
  --out-dir "data/out/graded" \
  --label "claude-sonnet-4-20250514-Non-Thinking"
```

## Provider Configuration

Edit `providers.yaml` to enable/disable providers and set models:

```yaml
openai:
  enabled: true
  models:
    - gpt-4o
openai-reasoning:
  enabled: true
  models:
    - gpt-5
    - gpt-5-mini
gemini:
  enabled: true
  models:
    - gemini-2.5-flash
    - gemini-2.5-pro
# ... etc
```

## API Keys Required

Set these environment variables in your `.env` file (the CLI now auto-loads `.env`):

- `OPENAI_API_KEY` - For OpenAI models
- `GEMINI_API_KEY` - For Google Gemini models  
- `ANTHROPIC_API_KEY` - For Claude models
- `GROQ_API_KEY` - For Groq models
- `XAI_API_KEY` - For xAI/Grok models
- `OPENROUTER_API_KEY` - For OpenRouter
- `MISTRAL_API_KEY` - For Mistral models (optional)
- `COHERE_API_KEY` - For Cohere models (optional)

Optional provider-specific token controls:

- `OPENROUTER_MAX_TOKENS` - Default output-token cap for OpenRouter (e.g., 8192, 20000)
- `ANTHROPIC_MAX_TOKENS` - Default output-token cap for Anthropic (e.g., 8192, 20000)
- `ANTHROPIC_THINKING_BUDGET_TOKENS` - Enable Anthropic reasoning and set budget (e.g., 16000)

## Testing

```bash
# Basic functionality test (if pytest not installed)
python -c "from src.evalsys.prompting import pack_messages_for_question; print('✓ Import successful')"

# Run specific tests manually
python -m tests.test_prompt_packing
```

## Output Files

- `data/out/dataset.jsonl` - Extracted benchmark cases
- `data/out/images/` - Extracted images from PDF
- `data/out/runs/*.jsonl` - Raw model responses
- `data/out/graded/scores__<model>__<grader>.csv` - Graded results per model/grader pair
- `data/out/graded/empty_answers__<model>__<grader>.csv` - Empty answers per model/grader pair (if any)
- `data/out/graded/report.html` - Full HTML report (includes per-case details)
- `data/out/graded/report_compact.html` - Compact HTML report (case text + scores)
- `data/out/graded/report_public.html` - Public HTML report (no case text)
- `data/out/graded/report_data.json` - Structured report export for downstream analysis
- `data/out/graded/report_rankings.csv` - Flat rankings export across views and metrics
- `docs/index.html` - Public GitHub Pages site
- `docs/assets/public-benchmark-data.js` - Public aggregate data payload for the site

## Architecture

The system has four main layers:

1. **Ingest**: PDF extraction with image mapping using PyMuPDF
2. **Runners**: Standardized prompting across multiple AI providers
3. **Graders**: LLM-based grading for open-ended responses using configurable rubrics
4. **Analytics**: CSV, HTML, JSON, and public-site reporting with scoring breakdowns

## Advanced Usage

### Custom Grading
Use different graders:
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

### Specific Provider Testing
Test individual providers:
```bash
python -m src.evalsys.cli run --models "groq:meta-llama/llama-4-scout-17b-16e-instruct" --limit 10
```

### Batch Processing
Process larger datasets:
```bash
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --limit 200
```

## License

MIT License - see LICENSE file for details
