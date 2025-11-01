from __future__ import annotations
import json, os, time
from pathlib import Path
from typing import List, Dict, Any, Optional
import typer
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import load_config
from .logging_setup import info, warn, error
from .pdf_extractor import extract
from .prompting import pack_messages_for_question, build_grading_prompt
from .dataset import QAItem, ModelResponse, GradedResponse
from .reporting import emit_report

from ..providers.openai_provider import OpenAIProvider
from ..providers.openai_reasoning_provider import OpenAIReasoningProvider
from ..providers.gemini_provider import GeminiProvider
from ..providers.anthropic_provider import AnthropicProvider
from ..providers.groq_provider import GroqProvider
from ..providers.xai_provider import XAIProvider
from ..providers.openrouter_provider import OpenRouterProvider
from ..providers.mistral_provider import MistralProvider
from ..providers.cohere_provider import CohereProvider

from ..grading.llm_grader import OpenAIGrader, GeminiGrader


def _load_env_file(path: str = ".env") -> None:
    """Lightweight .env loader to populate os.environ if present.
    Avoids adding a new dependency.
    Supports KEY=VALUE with optional quotes. Ignores comments/blanks.
    """
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # allow inline comments only if preceded by whitespace
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("\"'").strip()  # strip quotes and spaces
        if key and val and key not in os.environ:
            os.environ[key] = val

app = typer.Typer(add_completion=False)

def _provider_factory(name: str, model: str, cfg, **kwargs) -> Any:
    if name == "openai":
        return OpenAIProvider(model, cfg.base_url or None)
    if name == "openai-reasoning":
        effort = kwargs.get("effort") or "minimal"
        return OpenAIReasoningProvider(model, cfg.base_url or None, effort=effort)
    if name == "gemini":
        return GeminiProvider(model)
    if name == "anthropic":
        return AnthropicProvider(model)
    if name == "groq":
        return GroqProvider(model)
    if name == "xai":
        return XAIProvider(model, cfg.base_url or None)
    if name == "openrouter":
        return OpenRouterProvider(model)
    if name == "mistral":
        return MistralProvider(model)
    if name == "cohere":
        return CohereProvider(model)
    raise ValueError(f"Unknown provider {name}")

@app.command()
def ingest(pdf: str = typer.Option("data/surgical.pdf", help="Path to PDF"),
           out_dir: str = typer.Option("data/out", help="Output directory")):
    items = extract(pdf, out_dir=out_dir, images_dir=f"{out_dir}/images")
    dataset_path = Path(out_dir) / "dataset.jsonl"
    with dataset_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(it.model_dump_json() + "\n")
    info(f"Wrote dataset to {dataset_path}")

def _load_dataset(path: str) -> List[QAItem]:
    return [QAItem.model_validate_json(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def _safe_ask(pv, messages, **kwargs):
    return pv.ask(messages, **kwargs)

@app.command()
def run(models: str = typer.Option("openai-reasoning:gpt-5,gemini:gemini-2.5-flash,anthropic:claude-3-5-sonnet-latest",
                                   help="Comma sep provider:model pairs"),
        dataset: str = typer.Option("data/out/dataset.jsonl"),
        limit: int = typer.Option(0, help="Number of questions to run (0 = full dataset)"),
        out_dir: str = typer.Option("data/out/runs"),
        max_tokens: int = typer.Option(0, help="Max output tokens (provider-specific). 0 = auto (8192 for OpenAI reasoning)"),
        reasoning_effort: Optional[str] = typer.Option(None, help="OpenAI reasoning effort for GPT-5: minimal, low, medium, high"),
        anthropic_thinking_budget: Optional[int] = typer.Option(None, help="Enable Anthropic 'thinking' with a budget in tokens (e.g., 16000)"),
        resume: bool = typer.Option(True, help="Resume from existing runs: skip QIDs already answered and append new results")):
    # ensure env vars from .env are available for providers (OPENAI_API_KEY, GEMINI_API_KEY, ...)
    _load_env_file()
    cfg = load_config()
    all_items = _load_dataset(dataset)
    if isinstance(limit, int) and limit > 0:
        items = all_items[:limit]
    else:
        items = all_items
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    pairs = [m.strip() for m in models.split(",") if m.strip()]
    for pair in pairs:
        provider_name, model = pair.split(":", 1)
        # Allow explicit chat path via "gpt-5-chat" shim; otherwise auto-route to reasoning
        if provider_name == "openai" and model.endswith("-chat"):
            model = model[:-5]
        elif provider_name == "openai" and model.startswith("gpt-5"):
            provider_name = "openai-reasoning"
        pv_cfg = getattr(cfg, provider_name.replace("-", "_"))
        if not pv_cfg.enabled:
            warn(f"{provider_name} disabled in config")
            continue

        eff = None
        if provider_name == "openai-reasoning":
            if reasoning_effort:
                eff = reasoning_effort.strip().lower()
                if eff not in {"minimal", "low", "medium", "high"}:
                    warn(f"Unknown reasoning effort '{reasoning_effort}', defaulting to 'minimal'")
                    eff = "minimal"
            else:
                eff = "minimal"

        pv = _provider_factory(provider_name, model, pv_cfg, effort=eff)
        # Announce Anthropic thinking if requested
        if provider_name == "anthropic" and anthropic_thinking_budget:
            info(f"Enabling Anthropic thinking with budget_tokens={anthropic_thinking_budget}")
        # Allow CLI to override reasoning effort for reasoning models post-instantiation
        if provider_name == "openai-reasoning" and reasoning_effort:
            eff_cli = reasoning_effort.strip().lower()
            if eff_cli in {"minimal", "low", "medium", "high"}:
                try:
                    pv.effort = eff_cli
                    info(f"Using reasoning_effort={eff_cli}")
                except Exception:
                    # If provider doesn't expose .effort, ignore gracefully
                    warn(f"Could not set reasoning_effort on provider; using default '{getattr(pv, 'effort', 'minimal')}'")
            else:
                warn(f"Unknown reasoning_effort '{reasoning_effort}', using provider default '{getattr(pv, 'effort', 'minimal')}'")
        # Determine output path and existing completed QIDs if resuming
        out_path = Path(out_dir) / f"{provider_name}__{model.replace('/','_')}.jsonl"
        completed_qids = set()
        if resume and out_path.exists():
            try:
                for line in out_path.read_text(encoding="utf-8").splitlines():
                    try:
                        prev = ModelResponse.model_validate_json(line)
                        if prev.qid:
                            completed_qids.add(prev.qid)
                    except Exception:
                        continue
                if completed_qids:
                    info(f"Resuming {provider_name}:{model} — found {len(completed_qids)} completed QIDs")
            except Exception:
                warn(f"Could not read existing run file {out_path}; starting fresh")

        info(f"Running {provider_name}:{model} on {len(items)} items")
        if not resume or not out_path.exists():
            # Truncate to start fresh so progress is written incrementally
            with out_path.open("w", encoding="utf-8"):
                pass
        written = 0
        with out_path.open("a", encoding="utf-8") as run_file:
            for it in items:
                if resume and it.qid in completed_qids:
                    # Skip already answered question
                    info(f"Skipping {it.qid} (already answered)")
                    continue
                # Log which question is being asked
                q_preview = it.question_text if len(it.question_text) <= 120 else (it.question_text[:117] + "...")
                info(f"Asking {provider_name}:{model} {it.qid} — {q_preview}")
                msg = pack_messages_for_question(it)
                if not pv.supports_images():
                    # remove images
                    if isinstance(msg["messages"][1]["content"], list):
                        msg["messages"][1]["content"] = [x for x in msg["messages"][1]["content"] if x.get("type")=="text"]

                # Retry logic for empty answers
                text = ""
                total_ms = 0
                retry_count = 0
                max_retries = cfg.empty_answer_retries

                for attempt in range(max_retries + 1):  # +1 for initial attempt
                    call_kwargs = {}
                    if isinstance(max_tokens, int) and max_tokens > 0:
                        call_kwargs["max_tokens"] = max_tokens
                    if provider_name == "anthropic" and anthropic_thinking_budget:
                        call_kwargs["thinking"] = {"type": "enabled", "budget_tokens": int(anthropic_thinking_budget)}
                    text, ms = _safe_ask(pv, msg["messages"], **call_kwargs)
                    total_ms += ms

                    # Check if answer is empty (only whitespace)
                    if text and text.strip():
                        break  # Got a non-empty answer, stop retrying

                    if attempt < max_retries:  # Don't increment on last attempt
                        retry_count += 1
                        warn(f"Empty answer from {provider_name}:{model} for {it.qid}, retrying ({retry_count}/{max_retries})")

                # Mark as empty if final answer is still empty
                is_empty = not (text and text.strip())
                if is_empty:
                    warn(f"Final answer is empty for {provider_name}:{model} {it.qid} after {retry_count} retries")
                    info(f"Answered {it.qid}: empty")
                else:
                    ans_len = len(text.strip()) if text else 0
                    info(f"Answered {it.qid}: non-empty ({ans_len} chars)")

                record = ModelResponse(
                    provider=provider_name,
                    model=model,
                    qid=it.qid,
                    answer=text,
                    latency_ms=total_ms,
                    used_images=len(it.images),
                    retry_attempts=retry_count,
                    is_empty_answer=is_empty,
                )
                run_file.write(record.model_dump_json() + "\n")
                run_file.flush()
                written += 1
        if written:
            info(f"Persisted {written} new records to {out_path}")
        else:
            info(f"No new records to write for {provider_name}:{model}")

_ALL_GRADERS_SENTINEL = "__ALL_GRADERS__"


@app.command()
def grade(dataset: str = typer.Option("data/out/dataset.jsonl"),
          runs_dir: str = typer.Option("data/out/runs"),
          grader: Optional[str] = typer.Option(
              None,
              "--grader",
              help="Target grader(s). Provide provider:model, a comma-separated list, or pass --grader with no value to run GPT-5 Mini and Gemini 2.5 Flash sequentially.",
              flag_value=_ALL_GRADERS_SENTINEL,
          ),
          out_dir: str = typer.Option("data/out/graded"),
          label: Optional[str] = typer.Option(None, help="Optional label to append to model names in outputs, e.g., 'chat' or 'minimal'"),
          resume: bool = typer.Option(True, help="Resume grading: skip QIDs already graded or recorded as empty and append new results")):
    # ensure env vars from .env are available for graders
    _load_env_file()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    items = {it.qid: it for it in _load_dataset(dataset)}

    def _resolve_graders(raw: Optional[str]) -> List[str]:
        if not raw or raw.strip() == "":
            return ["openai:gpt-5-mini"]
        if raw == _ALL_GRADERS_SENTINEL:
            return ["openai:gpt-5-mini", "gemini:gemini-2.5-flash"]
        raw_lower = raw.strip().lower()
        if raw_lower == "all":
            return ["openai:gpt-5-mini", "gemini:gemini-2.5-flash"]
        parts = [part.strip() for part in raw.split(",") if part.strip()]
        return parts if parts else ["openai:gpt-5-mini"]

    grader_specs = _resolve_graders(grader)

    def _slug(s: str) -> str:
        return s.replace('/', '_')

    def run_for_spec(grader_spec: str) -> None:
        if ":" not in grader_spec:
            error(f"Grader spec '{grader_spec}' must be provider:model")
            return
        provider_name, model_name = grader_spec.split(":", 1)
        provider_name = provider_name.strip()
        model_name = model_name.strip()
        if not provider_name or not model_name:
            error(f"Invalid grader spec '{grader_spec}'")
            return

        if provider_name == "openai":
            g = OpenAIGrader(model=model_name)
        elif provider_name == "gemini":
            g = GeminiGrader(model=model_name)
        else:
            error(f"Unknown grader provider '{provider_name}'")
            return

        # Preload existing graded QIDs and empty QIDs if resuming
        existing_graded: Dict[tuple[str, str], set] = {}
        existing_empty: Dict[tuple[str, str], set] = {}
        if resume:
            for fp in Path(out_dir).glob("scores__*.csv"):
                try:
                    df_prev = pd.read_csv(fp)
                except Exception:
                    continue
                for _, row in df_prev.iterrows():
                    m = str(row.get("model", ""))
                    q = str(row.get("qid", ""))
                    grader_name = str(row.get("grader", "")) or "__unknown__"
                    if m and q:
                        existing_graded.setdefault((m, grader_name), set()).add(q)
            for fp in Path(out_dir).glob("empty_answers__*.csv"):
                try:
                    df_prev = pd.read_csv(fp)
                except Exception:
                    continue
                for _, row in df_prev.iterrows():
                    m = str(row.get("model", ""))
                    q = str(row.get("qid", ""))
                    grader_name = str(row.get("grader", "")) or "__unknown__"
                    if m and q:
                        existing_empty.setdefault((m, grader_name), set()).add(q)

        rows_by_model: Dict[tuple[str, str], list] = {}
        empty_by_model: Dict[tuple[str, str], list] = {}
        for path in Path(runs_dir).glob("*.jsonl"):
            prov, model_slug = path.stem.split("__", 1)
            model = model_slug.replace("_", "/")
            for line in path.read_text(encoding="utf-8").splitlines():
                r = ModelResponse.model_validate_json(line)
                it = items[r.qid]

                is_empty = getattr(r, 'is_empty_answer', False) or not (r.answer and r.answer.strip())

                model_key = f"{r.model} [{label}]" if label else r.model
                grader_name = g.name

                if is_empty:
                    if resume and r.qid in existing_empty.get((model_key, grader_name), set()):
                        info(f"Skipping empty record (already recorded): {r.provider}:{model_key} {r.qid} (grader={g.name})")
                        continue
                    empty_by_model.setdefault((model_key, grader_name), []).append({
                        "provider": r.provider,
                        "model": model_key,
                        "qid": r.qid,
                        "retry_attempts": getattr(r, 'retry_attempts', 0),
                        "grader": grader_name,
                    })
                    info(f"Skipping grading for empty answer: {r.provider}:{model_key} {r.qid} (grader={g.name})")
                    continue

                info(f"Grading {r.provider}:{r.model} {r.qid} with {g.name}")
                if resume and r.qid in existing_graded.get((model_key, g.name), set()):
                    info(f"Already graded {r.provider}:{model_key} {r.qid} (grader={g.name}); skipping")
                    continue
                prompt = build_grading_prompt(it.question_text, it.answer_text or "", r.answer)
                try:
                    score, just, missed, harmful = g.grade(prompt)
                except Exception as e:
                    warn(f"Grading failed for {r.provider}:{r.model} {r.qid}: {e}; skipping")
                    continue
                info(f"Scored {r.provider}:{r.model} {r.qid} = {score:.3f} (grader={g.name})")
                gr = GradedResponse(provider=r.provider, model=model_key, qid=r.qid, answer=r.answer,
                                    grader=g.name, score=score, justification=just, missed=missed, harmful=harmful)
                row_payload = gr.model_dump()
                row_payload["grader"] = g.name
                rows_by_model.setdefault((model_key, g.name), []).append(row_payload)

        total_rows = 0
        total_empties = 0
        for (model, grader_name), rows in rows_by_model.items():
            grader_slug = _slug(grader_name)
            csv_path = Path(out_dir) / f"scores__{_slug(model)}__{grader_slug}.csv"
            df_new = pd.DataFrame(rows)
            if resume and csv_path.exists():
                try:
                    df_prev = pd.read_csv(csv_path)
                    df_all = pd.concat([df_prev, df_new], ignore_index=True)
                    df_all = df_all.drop_duplicates(subset=["qid"], keep="first")
                except Exception:
                    df_all = df_new
            else:
                df_all = df_new
            df_all.to_csv(csv_path, index=False)
            total_rows += len(df_new)
            info(f"Wrote {csv_path} ({len(df_new)} new rows)")

        for (model, grader_name), rows in empty_by_model.items():
            if rows:
                grader_slug = _slug(grader_name)
                empty_path = Path(out_dir) / f"empty_answers__{_slug(model)}__{grader_slug}.csv"
                empty_df_new = pd.DataFrame(rows)
                if resume and empty_path.exists():
                    try:
                        empty_prev = pd.read_csv(empty_path)
                        empty_all = pd.concat([empty_prev, empty_df_new], ignore_index=True)
                        empty_all = empty_all.drop_duplicates(subset=["qid"], keep="first")
                    except Exception:
                        empty_all = empty_df_new
                else:
                    empty_all = empty_df_new
                empty_all.to_csv(empty_path, index=False)
                total_empties += len(rows)
                info(f"Wrote empty answer stats to {empty_path} ({len(rows)} new)")

        if total_rows + total_empties > 0:
            info(f"Empty answers: {total_empties}/{total_rows + total_empties} ({(total_empties/(total_rows+total_empties))*100:.1f}%)")

    for spec in grader_specs:
        run_for_spec(spec)

    from .reporting import emit_report
    html_path = Path(out_dir) / "report.html"
    emit_report(Path(out_dir), html_path, Path(dataset), Path(out_dir))
    info(f"Wrote {html_path}")

@app.command()
def report(scores: str = typer.Option("data/out/graded", help="Path to scores.csv or directory with per-model CSVs"),
           dataset: str = typer.Option("data/out/dataset.jsonl", help="Path to dataset.jsonl"),
           empty_answers: str = typer.Option(None, help="Optional path to empty_answers.csv or directory with per-model files"),
           out_html: str = typer.Option(None, help="Optional output HTML path (defaults next to scores input)")):
    """Regenerate the HTML report from existing scores.csv and optional empty_answers.csv.

    This does not rerun grading or model inference.
    """
    csv_path = Path(scores)
    if not csv_path.exists():
        error(f"Scores path not found: {csv_path}")
        raise typer.Exit(code=2)
    base_for_html = csv_path if csv_path.is_dir() else csv_path.parent
    html_path = Path(out_html) if out_html else (base_for_html / "report.html")
    if empty_answers:
        empty_path = Path(empty_answers)
    else:
        empty_path = base_for_html
    ds_path = Path(dataset)
    info(f"Generating report from {csv_path} (empty path: {empty_path})")
    emit_report(csv_path, html_path, ds_path, empty_path)
    info(f"Wrote {html_path}")

if __name__ == "__main__":
    app()
