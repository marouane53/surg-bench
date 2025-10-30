# Model Commands Reference

This document lists all supported models with commands to run evaluations on 20 questions or the full dataset (290 questions).

## Command Format

```bash
python -m src.evalsys.cli run --models "provider:model" --limit <number>
```

---

```bash
python -m src.evalsys.cli report --scores data/out/graded --dataset data/out/dataset.jsonl
```



## OpenAI Models

### GPT-5 (Reasoning Mode)

#### High Reasoning Effort
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --limit 20 --reasoning-effort high
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --reasoning-effort high
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

#### Medium Reasoning Effort
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --limit 20 --reasoning-effort medium
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --reasoning-effort medium
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

### GPT-5 (Chat Mode)
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "openai:gpt-5" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "openai:gpt-5"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

### GPT-5 Mini
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "openai:gpt-5-mini" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "openai:gpt-5-mini"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

### GPT-4o
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "openai:gpt-4o" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "openai:gpt-4o"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

---

## Google Gemini Models

### Gemini 2.5 Flash Lite
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "gemini:gemini-2.5-flash-lite" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "gemini:gemini-2.5-flash-lite"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

### Gemini 2.5 Flash
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "gemini:gemini-2.5-flash" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "gemini:gemini-2.5-flash"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

**Grade with GPT-5 Mini:**
```bash
python -m src.evalsys.cli grade --grader "openai:gpt-5-mini"
```

### Gemini 2.5 Pro
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "gemini:gemini-2.5-pro" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "gemini:gemini-2.5-pro"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

---

## Anthropic Models

### Claude Sonnet 4.5
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "anthropic:claude-sonnet-4-5-20250929" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "anthropic:claude-sonnet-4-5-20250929"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

### Claude Opus 4.1
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "anthropic:claude-opus-4-1-20250805" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "anthropic:claude-opus-4-1-20250805"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

---

## Groq Models

### Llama 3.3 70B Versatile
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "groq:llama-3.3-70b-versatile" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "groq:llama-3.3-70b-versatile"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

### Llama 3 8B
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "groq:llama3-8b-8192" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "groq:llama3-8b-8192"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

---

## xAI Models

### Grok Beta
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "xai:grok-beta" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "xai:grok-beta"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

---

## OpenRouter Models

### OpenAI GPT-4o (via OpenRouter)
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "openrouter:openai/gpt-4o" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "openrouter:openai/gpt-4o"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

---

## Mistral Models (⚠️ Currently Disabled)

To enable, set `enabled: true` in `providers.yaml` under `mistral`.

### Mistral Small Latest
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "mistral:mistral-small-latest" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "mistral:mistral-small-latest"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

---

## Cohere Models (⚠️ Currently Disabled)

To enable, set `enabled: true` in `providers.yaml` under `cohere`.

### Command R+ 03-2025
**Run 20 questions:**
```bash
python -m src.evalsys.cli run --models "cohere:command-a-03-2025" --limit 20
```

**Run full set (290 questions):**
```bash
python -m src.evalsys.cli run --models "cohere:command-a-03-2025"
```

**Grade the results:**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

---

## Running Multiple Models

You can run multiple models in a single command by separating them with commas:

**Example - Run 20 questions on multiple models:**
```bash
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5,gemini:gemini-2.5-flash,anthropic:claude-sonnet-4-5-20250929" --limit 20
```

**Example - Run full set on multiple models:**
```bash
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5,gemini:gemini-2.5-flash,anthropic:claude-sonnet-4-5-20250929"
```

---

## Additional Options

### Reasoning Effort (OpenAI Reasoning Models)
Control the reasoning effort level (see GPT-5 Reasoning Mode section for examples):
```bash
# Example with high reasoning effort
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --limit 20 --reasoning-effort high

# Example with medium reasoning effort  
python -m src.evalsys.cli run --models "openai-reasoning:gpt-5" --limit 20 --reasoning-effort medium
```
Available options: `minimal`, `low`, `medium`, `high`

### Anthropic Thinking Mode
Enable extended thinking with a token budget (recommended: 16000 tokens):
```bash
# With thinking budget (recommended for Claude Sonnet 4.5 and Opus 4.1)
python -m src.evalsys.cli run --models "anthropic:claude-sonnet-4-5-20250929" --limit 20 --anthropic-thinking-budget 16000

# Or set as environment variable for all Anthropic runs
export ANTHROPIC_THINKING_BUDGET_TOKENS=16000
python -m src.evalsys.cli run --models "anthropic:claude-sonnet-4-5-20250929" --limit 20
```

**Note:** Thinking mode requires `budget_tokens >= 1024` and `< max_tokens`. The budget is automatically adjusted if needed.

### Max Output Tokens
Specify maximum output tokens:
```bash
python -m src.evalsys.cli run --models "openai:gpt-4o" --limit 20 --max-tokens 4096
```

### Resume Mode
By default, resume is enabled. Disable it with:
```bash
python -m src.evalsys.cli run --models "openai:gpt-5" --limit 20 --no-resume
```

---

## Grading Commands

After running models, grade the outputs:

**Using Gemini 2.5 Flash as grader (recommended):**
```bash
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash"
```

**Using OpenAI GPT-5 Mini as grader:**
```bash
python -m src.evalsys.cli grade --grader "openai:gpt-5-mini"
```

**Add a custom label to distinguish runs in the HTML report:**
```bash
# Example: Label a run with thinking mode enabled
python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash" --label "with-thinking"

# This will display as "claude-sonnet-4-5-20250929 [with-thinking]" in the report
```

The `--label` parameter is useful when comparing different configurations of the same model (e.g., with/without thinking, different reasoning efforts, etc.)

---

## Notes

- The `--limit` parameter is **only needed when testing with a subset of questions** (e.g., `--limit 20`). When running the full dataset (290 questions), omit the `--limit` parameter entirely
- Output files are saved to `data/out/runs/` by default
- Graded results are saved to `data/out/graded/` by default
- Reports are generated automatically after grading in `data/out/graded/report.html`
- Make sure to set appropriate API keys in your `.env` file before running

