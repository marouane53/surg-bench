#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODEL_LABELS = {
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "claude-sonnet-4-5-20250929": "Claude Sonnet 4.5",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-3-flash-preview": "Gemini 3 Flash",
    "gemini-3-pro-preview": "Gemini 3 Pro",
    "gpt-4o": "GPT-4o",
    "gpt-5": "GPT-5",
    "gpt-5-mini": "GPT-5 Mini",
    "gpt-5-nano": "GPT-5 Nano",
    "gpt-5.1": "GPT-5.1",
    "gpt-5.2": "GPT-5.2",
    "meta-llama/llama-4-scout-17b-16e-instruct": "Llama 4 Scout",
    "qwen/qwen3-vl-235b-a22b-thinking": "Qwen3 VL 235B",
    "x-ai/grok-4-fast": "Grok 4 Fast",
}

PROVIDER_LABELS = {
    "anthropic": "Anthropic",
    "gemini": "Google Gemini",
    "groq": "Groq",
    "openai": "OpenAI",
    "openai-reasoning": "OpenAI reasoning",
    "openrouter": "OpenRouter",
}

NUMBERED_PROMPT_RE = re.compile(r"(?m)^\s*\d+\.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a GitHub Pages-ready public benchmark site payload."
    )
    parser.add_argument(
        "--report-data",
        default="data/out/graded/report_data.json",
        help="Path to report_data.json",
    )
    parser.add_argument(
        "--runs-dir",
        default="data/out/runs",
        help="Directory containing per-model run jsonl files",
    )
    parser.add_argument(
        "--out",
        default="docs/assets/public-benchmark-data.js",
        help="Output JS path consumed by docs/index.html",
    )
    return parser.parse_args()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def model_label(value: str) -> str:
    return MODEL_LABELS.get(value, value.replace("-", " ").replace("_", " ").title())


def provider_label(value: str) -> str:
    return PROVIDER_LABELS.get(value, value.replace("-", " ").title())


def clean_category_name(value: str) -> str:
    return re.sub(r"\s+\d+$", "", value).strip()


def category_abbr(value: str) -> str:
    cleaned = clean_category_name(value)
    replacements = {
        "Trauma and ICU": "Trauma / ICU",
        "Head and Neck": "Head / Neck",
        "Paediatric Surgery": "Paediatric",
    }
    return replacements.get(cleaned, cleaned)


def round_value(value: float | int) -> float | int:
    if isinstance(value, int):
        return value
    return round(float(value), 4)


def count_numbered_prompts(text: str) -> int:
    return len(NUMBERED_PROMPT_RE.findall(text or ""))


def compute_dataset_counts(dataset_path: Path) -> dict[str, Any]:
    case_count = 0
    sub_prompt_count = 0
    answer_fallback_cases = 0

    with dataset_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            question_count = count_numbered_prompts(record.get("question_text", ""))
            answer_count = count_numbered_prompts(record.get("answer_text", ""))
            prompt_count = max(question_count, answer_count)

            case_count += 1
            sub_prompt_count += prompt_count

            if answer_count > question_count:
                answer_fallback_cases += 1

    avg_sub_prompts = (sub_prompt_count / case_count) if case_count else 0
    return {
        "caseCount": case_count,
        "subPromptCount": sub_prompt_count,
        "avgSubPromptsPerCase": round(avg_sub_prompts, 2),
        "answerFallbackCases": answer_fallback_cases,
    }


def percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0

    index = (len(sorted_values) - 1) * fraction
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return sorted_values[lower]

    lower_value = sorted_values[lower]
    upper_value = sorted_values[upper]
    return lower_value + (upper_value - lower_value) * (index - lower)


def load_latency_stats(runs_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    latency_by_model: dict[tuple[str, str], dict[str, Any]] = {}

    for run_file in sorted(runs_dir.glob("*.jsonl")):
        provider = ""
        model = ""
        total_cases = 0
        answered_cases = 0
        timed_latencies: list[float] = []

        with run_file.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue

                row = json.loads(line)
                provider = row.get("provider", provider)
                model = row.get("model", model)
                total_cases += 1

                if row.get("is_empty_answer"):
                    continue

                answered_cases += 1
                latency_ms = row.get("latency_ms")
                if isinstance(latency_ms, (int, float)) and latency_ms > 0:
                    timed_latencies.append(float(latency_ms))

        if not provider or not model or not timed_latencies:
            continue

        timed_latencies.sort()
        latency_by_model[(provider, model)] = {
            "medianMs": round_value(percentile(timed_latencies, 0.5)),
            "p90Ms": round_value(percentile(timed_latencies, 0.9)),
            "meanMs": round_value(sum(timed_latencies) / len(timed_latencies)),
            "minMs": round_value(timed_latencies[0]),
            "maxMs": round_value(timed_latencies[-1]),
            "timedCaseCount": len(timed_latencies),
            "answeredCaseCount": answered_cases,
            "totalCaseCount": total_cases,
        }

    return latency_by_model


def build_category_meta(reference_view: dict[str, Any]) -> list[dict[str, Any]]:
    categories = []
    for category in reference_view["categories"]:
        categories.append(
            {
                "id": category["id"],
                "label": clean_category_name(category["name"]),
                "shortLabel": category_abbr(category["name"]),
                "questionCount": category["total_qs"],
            }
        )
    return categories


def select_best(
    rows: list[dict[str, Any]],
    value_key: str,
    reverse: bool = True,
) -> dict[str, Any]:
    if reverse:
        return max(
            rows,
            key=lambda item: (
                item[value_key],
                item["n_answered"],
                -item["n_reject"],
                model_label(item["model"]),
            ),
        )
    return min(
        rows,
        key=lambda item: (
            item[value_key],
            item["n_reject"],
            -item["n_answered"],
            model_label(item["model"]),
        ),
    )


def build_view_payload(
    view: dict[str, Any],
    latency_stats: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    category_by_model: dict[str, dict[str, Any]] = defaultdict(dict)
    leader_counts_zeroed: Counter[str] = Counter()
    leader_counts_answered: Counter[str] = Counter()
    category_leaders = []

    for category in view["categories"]:
        rows = category["model_rows"]
        best_zeroed = select_best(rows, "avg_zeroed", reverse=True)
        best_answered = select_best(rows, "avg_answered", reverse=True)
        best_reject = select_best(
            [
                {
                    **row,
                    "reject_rate": (row["n_reject"] / row["n_total"]) if row["n_total"] else 0,
                }
                for row in rows
            ],
            "reject_rate",
            reverse=False,
        )

        leader_counts_zeroed[best_zeroed["model"]] += 1
        leader_counts_answered[best_answered["model"]] += 1

        category_leaders.append(
            {
                "categoryId": category["id"],
                "label": clean_category_name(category["name"]),
                "zeroed": {
                    "model": best_zeroed["model"],
                    "label": model_label(best_zeroed["model"]),
                    "provider": best_zeroed["provider"],
                    "score": round_value(best_zeroed["avg_zeroed"]),
                },
                "answered": {
                    "model": best_answered["model"],
                    "label": model_label(best_answered["model"]),
                    "provider": best_answered["provider"],
                    "score": round_value(best_answered["avg_answered"]),
                },
                "rejectRate": {
                    "model": best_reject["model"],
                    "label": model_label(best_reject["model"]),
                    "provider": best_reject["provider"],
                    "score": round_value(best_reject["reject_rate"]),
                },
            }
        )

        for row in rows:
            reject_rate = (row["n_reject"] / row["n_total"]) if row["n_total"] else 0
            category_by_model[row["model"]][category["id"]] = {
                "zeroed": round_value(row["avg_zeroed"]),
                "answered": round_value(row["avg_answered"]),
                "rejectRate": round_value(reject_rate),
                "answeredCount": row["n_answered"],
                "rejectCount": row["n_reject"],
                "totalCount": row["n_total"],
            }

    models = []
    for row in sorted(
        view["rankings"]["rows"], key=lambda item: item["overall_zeroed"], reverse=True
    ):
        total = int(row["n_total"])
        rejects = int(row["n_reject"])
        answered = int(row["n_answered"])
        reject_rate = (rejects / total) if total else 0
        zeroed = float(row["overall_zeroed"])
        answered_avg = float(row["overall_answered"])

        models.append(
            {
                "id": slugify(row["model"]),
                "model": row["model"],
                "label": model_label(row["model"]),
                "shortLabel": model_label(row["model"]),
                "provider": row["provider"],
                "providerLabel": provider_label(row["provider"]),
                "overall": {
                    "zeroed": round_value(zeroed),
                    "answered": round_value(answered_avg),
                    "rejectRate": round_value(reject_rate),
                    "penalty": round_value(max(0.0, answered_avg - zeroed)),
                },
                "counts": {
                    "answered": answered,
                    "rejects": rejects,
                    "total": total,
                },
                "wins": {
                    "zeroed": leader_counts_zeroed.get(row["model"], 0),
                    "answered": leader_counts_answered.get(row["model"], 0),
                },
                "categories": category_by_model.get(row["model"], {}),
                "latency": latency_stats.get((row["provider"], row["model"])),
            }
        )

    best_overall = max(models, key=lambda item: item["overall"]["zeroed"])
    best_answered = max(models, key=lambda item: item["overall"]["answered"])
    best_reliable = max(
        [model for model in models if model["counts"]["rejects"] == 0],
        key=lambda item: item["overall"]["zeroed"],
    )
    largest_penalty = max(models, key=lambda item: item["overall"]["penalty"])
    category_king = max(models, key=lambda item: item["wins"]["zeroed"])

    return {
        "id": view["id"],
        "label": view["label"],
        "judgmentCount": max(model["counts"]["total"] for model in models),
        "sourceGraders": view.get("source_graders") or [],
        "models": models,
        "categoryLeaders": category_leaders,
        "highlights": {
            "bestOverall": {
                "model": best_overall["label"],
                "provider": best_overall["providerLabel"],
                "score": best_overall["overall"]["zeroed"],
            },
            "bestAnswered": {
                "model": best_answered["label"],
                "provider": best_answered["providerLabel"],
                "score": best_answered["overall"]["answered"],
            },
            "bestReliable": {
                "model": best_reliable["label"],
                "provider": best_reliable["providerLabel"],
                "score": best_reliable["overall"]["zeroed"],
            },
            "largestPenalty": {
                "model": largest_penalty["label"],
                "provider": largest_penalty["providerLabel"],
                "penalty": largest_penalty["overall"]["penalty"],
                "rejectRate": largest_penalty["overall"]["rejectRate"],
            },
            "mostCategoryWins": {
                "model": category_king["label"],
                "provider": category_king["providerLabel"],
                "wins": category_king["wins"]["zeroed"],
            },
        },
    }


def main() -> None:
    args = parse_args()
    report_data_path = Path(args.report_data)
    runs_dir = Path(args.runs_dir)
    out_path = Path(args.out)

    report_data = json.loads(report_data_path.read_text(encoding="utf-8"))
    report_views = report_data["views"]
    dataset_path = Path(report_data["meta"]["dataset_source"])
    dataset_counts = compute_dataset_counts(dataset_path)

    reference_view = next((view for view in report_views if not view.get("is_all")), report_views[0])
    category_meta = build_category_meta(reference_view)
    latency_stats = load_latency_stats(runs_dir)

    payload = {
        "meta": {
            "title": "Surgical Benchmark Public Results",
            "generatedAt": report_data["meta"]["generated_at"],
            "caseCount": dataset_counts["caseCount"],
            "subPromptCount": dataset_counts["subPromptCount"],
            "avgSubPromptsPerCase": dataset_counts["avgSubPromptsPerCase"],
            "answerFallbackCases": dataset_counts["answerFallbackCases"],
            "totalQuestions": report_data["meta"]["total_questions"],
            "modelCount": report_data["meta"]["model_count"],
            "graderCount": len(
                {
                    grader
                    for view in report_views
                    for grader in (view.get("source_graders") or [])
                    if grader
                }
            )
            or max(report_data["meta"].get("grader_count", 0) - 1, 0),
            "categories": category_meta,
            "categoryCount": len(category_meta),
            "sourceBook": "Surgical Exam Cases",
            "countingMethod": "Cases are benchmark entries. Sub-prompts are counted from numbered prompts in each case, using the reference answer structure when OCR truncates a case prompt.",
            "publicSafe": True,
            "questionTextIncluded": False,
            "answerTextIncluded": False,
            "imageContentIncluded": False,
        },
        "views": [build_view_payload(view, latency_stats) for view in report_views],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "window.PUBLIC_BENCHMARK_DATA = "
        + json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )

    print(f"Wrote public site payload: {out_path}")
    print(
        f"Views: {len(payload['views'])}, models: {payload['meta']['modelCount']}, "
        f"cases: {payload['meta']['caseCount']}, sub-prompts: {payload['meta']['subPromptCount']}"
    )


if __name__ == "__main__":
    main()
