# AI Surgical Evaluation System

A comprehensive benchmark that extracts surgical Q&A with images from PDF documents, runs questions across multiple AI providers, and grades responses using LLM-based evaluators.

## Data Source & Attribution

This benchmark uses questions extracted from **"Surgical Exam Cases"** by **Charles Tan**, Adjunct Assistant Professor, Department of Surgery, Yong Loo Lin School of Medicine, National University of Singapore.

### Why This Book?

We selected this textbook because it was **published in 2025**, before most current AI models were trained. This ensures the evaluation tests genuine medical reasoning capabilities rather than memorized content, providing a fair and uncontaminated assessment of AI performance on contemporary surgical knowledge.

### Running the Benchmark

**To run this evaluation, you must purchase the book.** The PDF (`data/surgical.pdf`) is not included in this repository. You can obtain the book from major medical publishers or academic bookstores. Once acquired, place the PDF in the `data/` directory to begin extraction and evaluation.

## Features

- **PDF Extraction**: Converts surgical PDFs into structured Q&A datasets with associated images
- **Multi-Provider Support**: OpenAI, Gemini, Anthropic, Groq, xAI, OpenRouter (Mistral & Cohere optional)
- **Switchable Graders**: GPT-5 Mini or Gemini 2.5 Flash for consistent evaluation
- **Comprehensive Reporting**: CSV output and HTML reports with scoring analytics
- **Resume Support**: Stop and continue runs or grading without losing progress

## Requirements

- Python 3.9+ (Python 3.10+ recommended for all optional providers)
- API keys for desired providers
- The "Surgical Exam Cases" textbook PDF (not included - must be purchased)

## Project Structure

```
surg-bench/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.template
├── providers.yaml
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

### 1. Extract Q&A from PDF
```bash
python -m src.evalsys.cli ingest --pdf data/surgical.pdf
```
This creates `data/out/dataset.jsonl` and extracts images to `data/out/images/`

### 2. Run AI Models
```bash
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5,gemini:gemini-2.5-flash,anthropic:claude-3-5-sonnet-latest" --limit 50
```
This generates model responses in `data/out/runs/`

### 3. Grade Responses
```bash
# run both default graders (GPT-5 Mini, then Gemini 2.5 Flash)
python -m src.evalsys.cli grade --grader

# or target a specific grader / list
python -m src.evalsys.cli grade --grader "openai:gpt-5-mini"
python -m src.evalsys.cli grade --grader "openai:gpt-5-mini,gemini:gemini-2.5-flash"
```
This creates per-model CSVs in `data/out/graded/` and a unified report:
- `scores__<model>__<grader>.csv` for graded answers per model/grader pair
- `empty_answers__<model>__<grader>.csv` for empty answers per model/grader pair (if any)
- `report.html` combining all per-model results

`--grader` accepts:

- *No value* (flag only): runs GPT-5 Mini first, then Gemini 2.5 Flash sequentially.
- `provider:model`: grades with a single grader (e.g. `openai:gpt-5-mini`).
- Comma-separated list: grades once per entry in order (e.g. `openai:gpt-5-mini,gemini:gemini-2.5-flash`).
- Literal `all`: identical to the flag-only shorthand.

## Reporting

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
- Generates `data/out/graded/report.html` with comprehensive analytics
- Works with any Python version (bypasses package installation requirements)

The generated report includes:
- **Model Comparison**: Side-by-side performance metrics
- **Score Distribution**: Histograms and statistical summaries  
- **Question Analysis**: Per-question breakdowns with justifications
- **Empty Answer Tracking**: Models that failed to respond
- **Interactive Charts**: Sortable tables and visual analytics

### Report Options
- `--scores`: Path to CSV file or directory containing `scores__*.csv` files
- `--dataset`: Path to `dataset.jsonl` file (for question context)
- `--empty-answers`: Optional path to empty answers CSV or directory
- `--out-html`: Output HTML file path (defaults to same directory as scores)

## Resume Runs and Grading (Stop/Continue)

You can pause and resume both model runs and grading without losing progress. The CLI skips QIDs already completed and appends only new results, then refreshes the report.

- `run --resume`: Skips QIDs already present in `data/out/runs/<provider>__<model>.jsonl` and appends new answers.
- `grade --resume`: Skips QIDs already graded in `data/out/graded/scores__<model>__<grader>.csv` or recorded as empty in `empty_answers__<model>__<grader>.csv`, appends new rows, and regenerates `report.html`.

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
- `grade` always regenerates `data/out/graded/report.html` so your report stays current after each incremental run.

## Quick Testing Example

Test multiple models and generate a comparative report with just 5 questions:

```bash
# Step 1: Extract Q&A from PDF (if not done already)
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

- `data/out/dataset.jsonl` - Extracted Q&A items
- `data/out/images/` - Extracted images from PDF
- `data/out/runs/*.jsonl` - Raw model responses
- `data/out/graded/scores__<model>__<grader>.csv` - Graded results per model/grader pair
- `data/out/graded/empty_answers__<model>__<grader>.csv` - Empty answers per model/grader pair (if any)
- `data/out/graded/report.html` - Unified HTML report

## Architecture

The system has four main layers:

1. **Ingest**: PDF extraction with image mapping using PyMuPDF
2. **Runners**: Standardized prompting across multiple AI providers
3. **Graders**: LLM-based grading with configurable rubrics
4. **Analytics**: CSV and HTML reporting with scoring breakdowns

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

## Security Notes

- All API keys are stored in environment variables
- No sensitive data is logged
- Graders penalize harmful or unsafe advice
- This system is for educational/benchmarking purposes only

## License

MIT License - see LICENSE file for details
