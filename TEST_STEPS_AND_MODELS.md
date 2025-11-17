# Benchmark Steps & Tested Models

_Last updated: 2025-11-09 (Pacific Time)_

This note captures the exact workflow we followed for the most recent full benchmark pass and lists every model whose outputs currently live under `data/out/runs/` and `data/out/graded/`.

## Steps we ran
1. **Ingested the textbook PDF** using `python -m src.evalsys.cli ingest --pdf data/surgical.pdf`, which rebuilt `data/out/dataset.jsonl` and refreshed the cropped images in `data/out/images/`.
2. **Ran the full 290-question set** for each model via `python -m src.evalsys.cli run --models "<provider>:<model>"`. We kept the default resume behavior so re-runs would skip completed question IDs and logged timings to `data/out/runs/run_history.log` automatically.
3. **Graded every run twice**—first with `gemini:gemini-2.5-flash`, then with `openai:gpt-5-mini`—using `python -m src.evalsys.cli grade --grader "gemini:gemini-2.5-flash,openai:gpt-5-mini"`. This produced paired `scores__*.csv` and `empty_answers__*.csv` files inside `data/out/graded/`.
4. **Regenerated the interactive HTML report** with `python -m src.evalsys.cli report --scores data/out/graded --dataset data/out/dataset.jsonl --out-html data/out/graded/report.html`, which is what backs both `report.html` (internal) and `report_public.html` (shareable) today.

## Models we tested on 2025-11-01 (full 290-Q set)
| Provider | Model | Output file (`data/out/runs/…`) | Elapsed (hh:mm:ss) | Notes |
| --- | --- | --- | --- | --- |
| groq | meta-llama/llama-4-scout-17b-16e-instruct | `groq__meta-llama_llama-4-scout-17b-16e-instruct.jsonl` | 00:15:01 | Groq vision beta enabled; multimodal inputs consumed directly. |
| gemini | gemini-2.5-flash-lite | `gemini__gemini-2.5-flash-lite.jsonl` | 00:15:21 | Fast baseline; useful for smoke checks. |
| openai-reasoning | gpt-5-mini | `openai-reasoning__gpt-5-mini.jsonl` | 00:51:40 | Reasoning mode, default effort; doubled as secondary grader afterwards. |
| gemini | gemini-2.5-flash | `gemini__gemini-2.5-flash.jsonl` | 00:47:18 | Primary grader model; this run captures its answering quality. |
| anthropic | claude-sonnet-4-5-20250929 | `anthropic__claude-sonnet-4-5-20250929.jsonl` | 01:06:39 | Thinking mode left at default budget (no override). |
| gemini | gemini-2.5-pro | `gemini__gemini-2.5-pro.jsonl` | 01:48:42 | Slowest Gemini tier; best reasoning depth among Gemini runs. |
| openrouter | qwen/qwen3-vl-235b-a22b-thinking | `openrouter__qwen_qwen3-vl-235b-a22b-thinking.jsonl` | 02:06:46 | Multimodal thinking variant via OpenRouter. |
| openai-reasoning | gpt-5 | `openai-reasoning__gpt-5.jsonl` | 04:34:26 | Flagship reasoning model; default effort. |
| openrouter | x-ai/grok-4-fast | `openrouter__x-ai_grok-4-fast.jsonl` | 00:27:14 | Fast Grok vision-capable endpoint proxied through OpenRouter. |
| openai-reasoning | gpt-5-nano | `openai-reasoning__gpt-5-nano.jsonl` | 00:27:31 | Budget reasoning configuration; good latency comparison point. |
| anthropic | claude-haiku-4-5-20251001 | `anthropic__claude-haiku-4-5-20251001.jsonl` | 00:27:03 | Lightweight Claude tier; no thinking budget set. |
| openai | gpt-4o | `openai__gpt-4o.jsonl` | 00:37:38 | Pure chat mode (non-reasoning) baseline. |

_All timings and ordering mirror `data/out/runs/run_history.log` and assume the dataset size of 290 questions._

## Where to look next
- Raw model answers: `data/out/runs/<provider>__<model>.jsonl`
- Graded CSVs: `data/out/graded/scores__<model>__<grader>.csv`
- Empty answer tracking: `data/out/graded/empty_answers__<model>__<grader>.csv`
- HTML report (interactive): `data/out/graded/report.html`

Add future runs to this table (include timestamp, any special flags, and grading status) so we can trace regressions quickly.
