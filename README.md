# AI Surgical Evaluation System

A comprehensive evaluator that ingests surgical PDF documents, extracts Q&A with images into structured datasets, runs questions across multiple AI providers, and grades responses using GPT-5 Mini and Gemini 2.5 Flash.

## Features

- **PDF Extraction**: Converts surgical PDFs into structured Q&A datasets with associated images
- **Multi-Provider Support**: OpenAI, Gemini, Anthropic, Groq, xAI, OpenRouter (Mistral & Cohere optional)
- **Switchable Graders**: GPT-5 Mini or Gemini 2.5 Flash for consistent evaluation
- **Comprehensive Reporting**: CSV output and HTML reports with scoring analytics
  - Chart modes: exclude rejections, count rejections as 0, or show rejection rate (bigger is worse)

## Requirements

- Python 3.9+ (Python 3.10+ recommended for all optional providers)
- API keys for desired providers

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
python -m src.evalsys.cli grade --grader "openai:gpt-5-mini"
```
This creates per-model CSVs in `data/out/graded/` and a unified report:
- `scores__<model>.csv` for graded answers per model
- `empty_answers__<model>.csv` for empty answers per model (if any)
- `report.html` combining all per-model results

### Regenerate Report Only
Rebuild the HTML report from existing graded outputs (no re-grading). Point to the graded directory with per-model CSVs:
```bash
python -m src.evalsys.cli report \
  --scores data/out/graded \
  --dataset data/out/dataset.jsonl
```
You can also pass explicit files or an explicit `--empty-answers` path (file or directory) if needed.

## Quick Testing Example

To quickly test multiple models and generate a comparative report with just 5 questions:

```bash
# Step 1: Extract Q&A from PDF (if not done already)
python -m src.evalsys.cli ingest --pdf data/surgical.pdf

# Step 2: Run multiple models at once (Gemini 2.5 Flash, Pro, and GPT-5)
python -m src.evalsys.cli run --models "gemini:gemini-2.5-flash,gemini:gemini-2.5-pro,openai-reasoning:gpt-5" --limit 5

# Step 3: Grade all responses using Gemini 2.5 Flash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"

# View results
# - CSV: data/out/graded/scores.csv  
# - HTML: data/out/graded/report.html
```

This will:
1. Run 3 different models on the first 5 questions
2. Generate comparative responses in `data/out/runs/`
3. Grade all responses using Gemini 2.5 Flash as the evaluator
4. Create an HTML report grouped by model with full justifications

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
- `data/out/graded/scores__<model>.csv` - Graded results per model
- `data/out/graded/empty_answers__<model>.csv` - Empty answers per model (if any)
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
python -m src.evalsys.cli run --models "groq:llama-3.3-70b-versatile" --limit 10
```

### Batch Processing
Process larger datasets:
```bash
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --limit 200
```

### Gemini Testing Examples

Test **Gemini 2.5 Flash** as both model and grader on 5 samples:
```bash
python -m src.evalsys.cli run --models "gemini:gemini-2.5-flash" --limit 5 && python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

Test **Gemini 2.5 Pro** as model with **Gemini 2.5 Flash** as grader on 5 samples:
```bash
python -m src.evalsys.cli run --models "gemini:gemini-2.5-pro" --limit 5 && python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

Test **both Gemini models** together with **Flash as grader**:
```bash
python -m src.evalsys.cli run --models "gemini:gemini-2.5-flash,gemini:gemini-2.5-pro" --limit 5 && python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

Test **GPT-5** as model with **Gemini 2.5 Flash** as grader on 5 samples:
```bash
python -m src.evalsys.cli run --models "openai:gpt-5" --limit 5 && python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

## Security Notes

- All API keys are stored in environment variables
- No sensitive data is logged
- Graders penalize harmful or unsafe advice
- This system is for educational/benchmarking purposes only

## License

MIT License - see LICENSE file for details
