from __future__ import annotations
import json, os, time
from pathlib import Path
from typing import List, Dict, Any
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

def _provider_factory(name: str, model: str, cfg) -> Any:
    if name == "openai": return OpenAIProvider(model, cfg.base_url or None)
    if name == "openai-reasoning": return OpenAIReasoningProvider(model, cfg.base_url or None, effort="minimal")
    if name == "gemini": return GeminiProvider(model)
    if name == "anthropic": return AnthropicProvider(model)
    if name == "groq": return GroqProvider(model)
    if name == "xai": return XAIProvider(model, cfg.base_url or None)
    if name == "openrouter": return OpenRouterProvider(model)
    if name == "mistral": return MistralProvider(model)
    if name == "cohere": return CohereProvider(model)
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
        limit: int = typer.Option(50, help="Number of questions to run"),
        out_dir: str = typer.Option("data/out/runs"),
        max_tokens: int = typer.Option(1024, help="Token budget for model output")):
    # ensure env vars from .env are available for providers (OPENAI_API_KEY, GEMINI_API_KEY, ...)
    _load_env_file()
    cfg = load_config()
    items = _load_dataset(dataset)[:limit]
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
        pv = _provider_factory(provider_name, model, pv_cfg)
        info(f"Running {provider_name}:{model} on {len(items)} items")
        recs: List[ModelResponse] = []
        for it in items:
            msg = pack_messages_for_question(it)
            if not pv.supports_images():
                # remove images
                if isinstance(msg["messages"][1]["content"], list):
                    msg["messages"][1]["content"] = [x for x in msg["messages"][1]["content"] if x.get("type")=="text"]
            text, ms = _safe_ask(pv, msg["messages"], max_tokens=max_tokens)
            recs.append(ModelResponse(provider=provider_name, model=model, qid=it.qid, answer=text, latency_ms=ms, used_images=len(it.images)))
        path = Path(out_dir) / f"{provider_name}__{model.replace('/','_')}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in recs:
                f.write(r.model_dump_json() + "\n")
        info(f"Wrote {path}")

@app.command()
def grade(dataset: str = typer.Option("data/out/dataset.jsonl"),
          runs_dir: str = typer.Option("data/out/runs"),
          grader: str = typer.Option("openai:gpt-5-mini", help="openai:gpt-5-mini or gemini:gemini-2.5-flash"),
          out_dir: str = typer.Option("data/out/graded")):
    # ensure env vars from .env are available for graders
    _load_env_file()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    items = {it.qid: it for it in _load_dataset(dataset)}
    # grader
    if grader.startswith("openai:"):
        g = OpenAIGrader(model=grader.split(":",1)[1])
    else:
        g = GeminiGrader(model=grader.split(":",1)[1])

    rows = []
    for path in Path(runs_dir).glob("*.jsonl"):
        prov, model = path.stem.split("__", 1)
        model = model.replace("_", "/")
        for line in path.read_text(encoding="utf-8").splitlines():
            r = ModelResponse.model_validate_json(line)
            it = items[r.qid]
            prompt = build_grading_prompt(it.question_text, it.answer_text or "", r.answer)
            score, just, missed, harmful = g.grade(prompt)
            gr = GradedResponse(provider=r.provider, model=r.model, qid=r.qid, answer=r.answer,
                                grader=g.name, score=score, justification=just, missed=missed, harmful=harmful)
            rows.append(gr.model_dump())

    # save csv and per item jsonl
    df = pd.DataFrame(rows)
    csv_path = Path(out_dir) / "scores.csv"
    df.to_csv(csv_path, index=False)
    info(f"Wrote {csv_path}")

    from .reporting import emit_report
    html_path = Path(out_dir) / "report.html"
    emit_report(csv_path, html_path)
    info(f"Wrote {html_path}")

if __name__ == "__main__":
    app()
