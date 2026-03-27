#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import html
import json
import math
import re
import shutil
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

SHOWCASE_EXAMPLE = {
    "qid": "Q1.2",
    "title": "Example case: posterior neck lump",
    "deck": (
        "This is the kind of open-ended, image-based case Surg Bench uses. Models had to "
        "describe the lesion, interpret the ultrasound, identify the diagnosis, and explain "
        "how the lesion behaves over time."
    ),
    "imageCaptions": ["Clinical photo", "Ultrasound", "Excised specimen"],
    "rubric": [
        {
            "id": "appearance",
            "label": "Clinical appearance",
            "description": (
                "Describe a well-circumscribed posterior-neck lump and note the lack of "
                "inflammatory skin changes."
            ),
        },
        {
            "id": "ultrasound",
            "label": "Ultrasound findings",
            "description": (
                "Recognize that ultrasound was used and describe a cystic lesion with "
                "internal echogenic material and a hypoechoic rim."
            ),
        },
        {
            "id": "diagnosis",
            "label": "Diagnosis",
            "description": "Identify the lesion as an epidermal or epidermoid cyst.",
        },
        {
            "id": "natural_history",
            "label": "Natural history",
            "description": (
                "Explain that the cyst may stay the same, enlarge, or shrink, and that it can "
                "become infected and form an abscess."
            ),
        },
    ],
}

SHOWCASE_GRADER = "gemini-2.5-flash"


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


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_numbered_sections(text: str) -> tuple[str, list[str]]:
    compact = compact_text(text)
    if not compact:
        return "", []

    matches = list(re.finditer(r"(\d+\.)\s*", compact))
    if not matches:
        return compact, []

    lead = compact[: matches[0].start()].strip()
    items = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(compact)
        item = compact[start:end].strip()
        if item:
            items.append(item)

    return lead, items


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


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def pearson_correlation(first_values: list[float], second_values: list[float]) -> float:
    if not first_values or len(first_values) != len(second_values):
        return 0.0

    first_mean = average(first_values)
    second_mean = average(second_values)

    numerator = sum(
        (first - first_mean) * (second - second_mean)
        for first, second in zip(first_values, second_values)
    )
    first_variance = sum((value - first_mean) ** 2 for value in first_values)
    second_variance = sum((value - second_mean) ** 2 for value in second_values)
    denominator = math.sqrt(first_variance * second_variance)

    if denominator == 0:
        return 0.0

    return numerator / denominator


def build_grader_agreement_payload(
    report_data: dict[str, Any],
    category_meta: list[dict[str, Any]],
) -> dict[str, Any]:
    comparison_pairs = report_data.get("comparison_pairs") or []
    if not comparison_pairs:
        return {}

    pair = comparison_pairs[0]
    first_label = model_label(pair["first"]["label"])
    second_label = model_label(pair["second"]["label"])
    bin_count = 20
    density_matrix = [[0 for _ in range(bin_count)] for _ in range(bin_count)]
    first_scores: list[float] = []
    second_scores: list[float] = []
    absolute_gaps: list[float] = []
    signed_gaps: list[float] = []

    category_lookup = {category["label"]: category for category in category_meta}
    category_buckets: dict[str, dict[str, Any]] = {}

    for entry in pair["entries"]:
        first_score = float(entry["first"]["record"].get("score", 0.0) or 0.0)
        second_score = float(entry["second"]["record"].get("score", 0.0) or 0.0)
        absolute_gap = abs(first_score - second_score)
        signed_gap = first_score - second_score

        first_scores.append(first_score)
        second_scores.append(second_score)
        absolute_gaps.append(absolute_gap)
        signed_gaps.append(signed_gap)

        x_bin = min(bin_count - 1, max(0, int(first_score * bin_count)))
        y_bin = min(bin_count - 1, max(0, int(second_score * bin_count)))
        density_matrix[y_bin][x_bin] += 1

        cleaned_category = clean_category_name(entry.get("category_name", ""))
        category_info = category_lookup.get(cleaned_category)
        if not category_info:
            continue

        bucket = category_buckets.setdefault(
            category_info["id"],
            {
                "categoryId": category_info["id"],
                "label": category_info["label"],
                "count": 0,
                "absoluteGaps": [],
                "signedGaps": [],
            },
        )
        bucket["count"] += 1
        bucket["absoluteGaps"].append(absolute_gap)
        bucket["signedGaps"].append(signed_gap)

    sorted_absolute_gaps = sorted(absolute_gaps)
    mean_absolute_gap = average(absolute_gaps)
    median_absolute_gap = percentile(sorted_absolute_gaps, 0.5)
    mean_signed_gap = average(signed_gaps)
    within_point_one_share = average([1.0 if gap <= 0.1 else 0.0 for gap in absolute_gaps])
    over_point_two_share = average([1.0 if gap >= (0.2 - 1e-12) else 0.0 for gap in absolute_gaps])
    correlation = pearson_correlation(first_scores, second_scores)
    second_grader_higher = mean_signed_gap < 0
    leniency_gap = abs(mean_signed_gap)

    category_gaps = [
        {
            "categoryId": bucket["categoryId"],
            "label": bucket["label"],
            "meanAbsoluteGap": round_value(average(bucket["absoluteGaps"])),
            "meanSignedGap": round_value(average(bucket["signedGaps"])),
            "count": bucket["count"],
        }
        for bucket in category_buckets.values()
    ]
    category_gaps.sort(
        key=lambda item: (-float(item["meanAbsoluteGap"]), item["label"])
    )

    summary = (
        f"Responses were scored independently by {first_label} and {second_label}. "
        f"Across {len(first_scores):,} paired scores, the graders were strongly aligned overall "
        f"(r = {correlation:.3f}), with a mean absolute gap of {mean_absolute_gap:.3f} and a median gap of "
        f"{median_absolute_gap:.3f}. "
        f"{second_label if second_grader_higher else first_label} scored responses "
        f"{leniency_gap:.3f} higher on average, and the full benchmark analysis also tracks the largest "
        f"question-level disagreements; this page summarizes the aggregate pattern."
    )

    return {
        "firstGrader": {
            "id": pair["first"]["view"],
            "label": first_label,
        },
        "secondGrader": {
            "id": pair["second"]["view"],
            "label": second_label,
        },
        "pairedScoreCount": len(first_scores),
        "correlation": round_value(correlation),
        "meanAbsoluteGap": round_value(mean_absolute_gap),
        "medianAbsoluteGap": round_value(median_absolute_gap),
        "meanSignedGap": round_value(mean_signed_gap),
        "withinPointOneShare": round_value(within_point_one_share),
        "overPointTwoShare": round_value(over_point_two_share),
        "summary": summary,
        "densityGrid": {
            "binCount": bin_count,
            "matrix": density_matrix,
            "maxCellCount": max(max(row) for row in density_matrix) if density_matrix else 0,
        },
        "categoryGaps": category_gaps,
    }


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


def parse_missed_points(raw_value: str) -> list[str]:
    if not raw_value:
        return []

    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(raw_value)
            break
        except (json.JSONDecodeError, SyntaxError, ValueError):
            parsed = None
    else:
        parsed = None

    if parsed is None:
        return [compact_text(raw_value)] if compact_text(raw_value) else []

    if isinstance(parsed, list):
        return [compact_text(str(item)) for item in parsed if compact_text(str(item))]

    return [compact_text(str(parsed))] if compact_text(str(parsed)) else []


def extract_showcase_report_meta(report_html_path: Path, qid: str) -> dict[str, Any]:
    report_html = report_html_path.read_text(encoding="utf-8")
    summary_match = re.search(
        rf"<summary>\s*<span class=\"qid\">{re.escape(qid)}</span>\s*"
        r"<span class=\"cat\">([^<]+)</span>\s*<span class=\"muted\">([^<]+)</span>",
        report_html,
        re.S,
    )
    gallery_match = re.search(
        rf"<span class=\"qid\">{re.escape(qid)}</span>.*?<div class=\"gallery\".*?"
        r"<div class=\"thumbs\">(.*?)</div>",
        report_html,
        re.S,
    )

    image_names: list[str] = []
    if gallery_match:
        image_names = re.findall(r'data-src="\.\./images/([^"]+)"', gallery_match.group(1))

    return {
        "category": clean_category_name(html.unescape(summary_match.group(1))) if summary_match else "",
        "pageRange": html.unescape(summary_match.group(2)) if summary_match else "",
        "imageNames": image_names,
    }


def copy_showcase_images(
    image_names: list[str],
    source_images_dir: Path,
    docs_assets_dir: Path,
    qid: str,
    captions: list[str],
) -> list[dict[str, Any]]:
    showcase_dir = docs_assets_dir / "showcase"
    showcase_dir.mkdir(parents=True, exist_ok=True)

    copied_images = []
    for index, image_name in enumerate(image_names, start=1):
        source_path = source_images_dir / image_name
        if not source_path.exists():
            continue

        destination_name = f"{slugify(qid)}-{index}{source_path.suffix.lower()}"
        destination_path = showcase_dir / destination_name
        shutil.copy2(source_path, destination_path)

        copied_images.append(
            {
                "src": f"./assets/showcase/{destination_name}",
                "alt": f"{qid} image {index}",
                "caption": captions[index - 1] if index - 1 < len(captions) else f"Image {index}",
            }
        )

    return copied_images


def has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def identify_showcase_diagnosis(answer: str) -> tuple[str, str]:
    lowered = answer.lower()
    normalized = f" {re.sub(r'[^a-z0-9]+', ' ', lowered)} "

    if "madelung" in lowered or "lipomatosis" in lowered:
        return "Madelung disease", "wrong"
    if "cystic hygroma" in lowered or "lymphangioma" in lowered:
        return "cystic hygroma", "wrong"
    if "thyroglossal" in lowered:
        return "thyroglossal duct cyst", "wrong"
    if "branchial cyst" in lowered:
        return "branchial cyst", "wrong"
    if " lipoma " in normalized:
        return "lipoma", "wrong"
    if " pilar " in normalized or " trichilemmal " in normalized:
        return "pilar cyst", "correct_specific"
    if (
        re.search(r"\bepiderm(?:al|oid)\b", normalized)
        or " sebaceous " in normalized
        or " skin cyst " in normalized
    ) and " lipoma " not in normalized and " madelung " not in normalized:
        return "epidermal cyst", "correct"
    if " cutaneous cyst " in normalized or " cyst " in normalized:
        return "benign cyst", "generic"
    return "", "unknown"


def showcase_headline(
    *,
    answer: str,
    score: float,
    justification: str,
    missed_points: list[str],
    is_empty: bool,
) -> tuple[str, str]:
    if is_empty or not compact_text(answer):
        return "No answer returned", "empty"

    lowered_justification = justification.lower()
    diagnosis_label, diagnosis_kind = identify_showcase_diagnosis(answer)

    if "more precise diagnosis of 'pilar cyst'" in lowered_justification or diagnosis_kind == "correct_specific":
        return "Reviewer accepted the more specific pilar-cyst diagnosis", "strong"
    if diagnosis_kind == "wrong" and diagnosis_label:
        article = "an" if diagnosis_label[0].lower() in "aeiou" else "a"
        return f"Reviewer judged this as {article} {diagnosis_label} misdiagnosis", "missed"
    if score >= 0.98:
        return "Reviewer judged this as exceptionally strong", "strong"
    if score >= 0.9 and diagnosis_kind in {"correct", "correct_specific"}:
        return "Reviewer judged this as highly accurate, with only minor misses", "strong"
    if score >= 0.9 and diagnosis_kind == "generic":
        return "Reviewer judged this as highly accurate despite slightly imprecise cyst wording", "strong"
    if score >= 0.75 and diagnosis_kind in {"correct", "correct_specific", "generic"}:
        return "Reviewer judged this as mostly correct, but missing some case detail", "mixed"
    if score >= 0.5 and diagnosis_kind in {"correct", "correct_specific", "generic"}:
        return "Reviewer judged the diagnosis right, but the answer was thinner than the strongest ones", "mixed"
    if diagnosis_kind == "generic":
        return "Reviewer judged this as an imprecise cyst answer", "mixed"
    if "misdiagnosis" in lowered_justification or "fundamentally misinterpreted" in lowered_justification:
        return "Reviewer flagged a major diagnostic miss", "missed"

    return "Reviewer judged this as a weak match to the case", "missed"


def showcase_review_excerpt(
    justification: str,
    is_empty: bool,
    score: float,
    diagnosis_label: str,
    diagnosis_kind: str,
) -> str:
    if is_empty:
        return "The benchmark run recorded no answer for this case after retries."

    compact = compact_text(justification)
    if not compact:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", compact)
    if diagnosis_kind == "wrong":
        diagnosis_tokens = [token for token in diagnosis_label.lower().split() if token]
        critical_markers = (
            "misdiagn",
            "fundamental error",
            "fundamentally misinterpreted",
            "incorrect diagnosis",
            "completely different diagnosis",
            "core issue",
            "significant misdiagnosis",
            "incorrect premise",
        )
        for sentence in sentences:
            lowered_sentence = sentence.lower()
            if diagnosis_tokens and all(token in lowered_sentence for token in diagnosis_tokens):
                return sentence
            if any(marker in lowered_sentence for marker in critical_markers):
                return sentence

    if score < 0.75:
        limitation_markers = (
            "however",
            "lacked",
            "lack of detail",
            "omits",
            "could have",
            "noted in the reference",
            "thin",
            "less specific",
        )
        for sentence in sentences:
            lowered_sentence = sentence.lower()
            if any(marker in lowered_sentence for marker in limitation_markers):
                return sentence

    return sentences[0]


def showcase_checks(
    *,
    answer: str,
    score: float,
    missed_points: list[str],
    is_empty: bool,
) -> list[dict[str, str]]:
    statuses = []
    if is_empty or not compact_text(answer):
        return [
            {"id": item["id"], "label": item["label"], "status": "empty"}
            for item in SHOWCASE_EXAMPLE["rubric"]
        ]

    lowered_missed = [point.lower() for point in missed_points]
    diagnosis_label, diagnosis_kind = identify_showcase_diagnosis(answer)

    rubric_keywords = {
        "appearance": ["q1", "erythema", "skin changes", "circular", "well-circumscribed", "neck"],
        "ultrasound": ["ultrasound", "usg", "hypoechoic", "hyperechoic", "cystic", "echo", "rim", "focus"],
        "diagnosis": ["diagnosis", "epiderm", "pilar", "trichilemmal", "lipoma", "madelung", "hygroma", "thyroglossal", "branchial"],
        "natural_history": ["natural history", "infect", "abscess", "decrease", "increase", "remain", "rupture", "enlarge"],
    }

    raw_statuses: dict[str, str] = {}
    for rubric_id, keywords in rubric_keywords.items():
        matched = any(any(keyword in point for keyword in keywords) for point in lowered_missed)
        if rubric_id == "diagnosis":
            if diagnosis_kind in {"correct", "correct_specific"} and not matched:
                raw_statuses[rubric_id] = "strong"
            elif diagnosis_kind in {"correct", "correct_specific", "generic"}:
                raw_statuses[rubric_id] = "mixed"
            elif diagnosis_label:
                raw_statuses[rubric_id] = "missed"
            else:
                raw_statuses[rubric_id] = "mixed" if matched and score >= 0.5 else "missed"
            continue

        if not matched:
            raw_statuses[rubric_id] = "strong"
        elif score >= 0.75:
            raw_statuses[rubric_id] = "mixed"
        else:
            raw_statuses[rubric_id] = "missed"

    for item in SHOWCASE_EXAMPLE["rubric"]:
        statuses.append(
            {
                "id": item["id"],
                "label": item["label"],
                "status": raw_statuses[item["id"]],
            }
        )

    return statuses


def build_showcase_models(
    graded_dir: Path,
    report_models: list[str],
    qid: str,
    grader: str,
) -> list[dict[str, Any]]:
    records_by_model: dict[str, dict[str, Any]] = {
        model: {
            "model": model,
            "provider": "",
            "answer": "",
            "graderScores": [],
            "justification": "",
            "missedPoints": [],
            "retryAttempts": 0,
            "empty": False,
        }
        for model in report_models
    }

    for score_path in sorted(graded_dir.glob("scores__*__*.csv")):
        with score_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row.get("qid") != qid or row.get("grader") != grader:
                    continue

                entry = records_by_model[row["model"]]
                entry["provider"] = row["provider"]
                entry["empty"] = False
                if not entry["answer"]:
                    entry["answer"] = row["answer"].strip()
                if not entry["justification"]:
                    entry["justification"] = compact_text(row.get("justification", ""))
                entry["graderScores"].append(
                    {
                        "grader": row["grader"],
                        "label": model_label(row["grader"]),
                        "score": round_value(float(row["score"])),
                    }
                )
                entry["missedPoints"].extend(parse_missed_points(row.get("missed", "")))

    for empty_path in sorted(graded_dir.glob("empty_answers__*__*.csv")):
        with empty_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row.get("qid") != qid or row.get("grader") != grader:
                    continue

                entry = records_by_model[row["model"]]
                entry["provider"] = row["provider"]
                entry["empty"] = True
                entry["retryAttempts"] = max(entry["retryAttempts"], int(row.get("retry_attempts") or 0))
                entry["graderScores"].append(
                    {
                        "grader": row["grader"],
                        "label": model_label(row["grader"]),
                        "score": 0,
                        "empty": True,
                    }
                )

    models = []
    for model in report_models:
        entry = records_by_model[model]
        unique_missed = sorted(set(entry["missedPoints"]), key=str.lower)
        answer_text = entry["answer"]
        justification = entry["justification"]
        average_score = round_value(float(entry["graderScores"][0]["score"])) if entry["graderScores"] else 0
        diagnosis_label, diagnosis_kind = identify_showcase_diagnosis(answer_text)
        headline, tone = showcase_headline(
            answer=answer_text,
            score=float(average_score),
            justification=justification,
            missed_points=unique_missed,
            is_empty=entry["empty"],
        )

        models.append(
            {
                "id": slugify(model),
                "model": model,
                "label": model_label(model),
                "provider": entry["provider"],
                "providerLabel": provider_label(entry["provider"]) if entry["provider"] else "",
                "averageScore": average_score,
                "empty": entry["empty"],
                "retryAttempts": entry["retryAttempts"],
                "headline": headline,
                "headlineTone": tone,
                "diagnosisLabel": diagnosis_label,
                "diagnosisKind": diagnosis_kind,
                "reviewExcerpt": showcase_review_excerpt(
                    justification,
                    entry["empty"],
                    float(average_score),
                    diagnosis_label,
                    diagnosis_kind,
                ),
                "answer": answer_text,
                "answerPreview": compact_text(answer_text)[:260],
                "graderScores": sorted(entry["graderScores"], key=lambda item: item["label"]),
                "missedPoints": unique_missed,
                "checks": showcase_checks(
                    answer=answer_text,
                    score=float(average_score),
                    missed_points=unique_missed,
                    is_empty=entry["empty"],
                ),
            }
        )

    models.sort(key=lambda item: (item["empty"], -float(item["averageScore"]), item["label"]))
    return models


def build_showcase_summary(models: list[dict[str, Any]]) -> str:
    empty_count = sum(1 for model in models if model["empty"])
    wrong_calls = []
    for model in models:
        if model["empty"] or model["headlineTone"] != "missed" or not model.get("diagnosisLabel"):
            continue
        label = str(model["diagnosisLabel"]).lower()
        wrong_calls.append(label)

    pieces = [
        "On this example, the reviewer marked the strongest answers as correctly connecting the clinical photo, ultrasound, and specimen to an epidermal cyst."
    ]
    if empty_count:
        pieces.append(f"{empty_count} models returned no answer.")
    if wrong_calls:
        ranked_wrong_calls = [call for call, _ in Counter(wrong_calls).most_common(3)]
        if len(ranked_wrong_calls) == 1:
            diagnosis_phrase = ranked_wrong_calls[0]
        elif len(ranked_wrong_calls) == 2:
            diagnosis_phrase = " or ".join(ranked_wrong_calls)
        else:
            diagnosis_phrase = ", ".join(ranked_wrong_calls[:-1]) + f", or {ranked_wrong_calls[-1]}"
        pieces.append(
            "The weakest non-empty answers instead called it "
            + diagnosis_phrase
            + "."
        )

    return " ".join(pieces)


def build_showcase_payload(
    dataset_path: Path,
    report_html_path: Path,
    graded_dir: Path,
    docs_assets_dir: Path,
    report_models: list[str],
) -> dict[str, Any]:
    qid = SHOWCASE_EXAMPLE["qid"]
    dataset_row = None
    with dataset_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("qid") == qid:
                dataset_row = row
                break

    if dataset_row is None:
        raise ValueError(f"Could not find showcase case {qid} in {dataset_path}")

    report_meta = extract_showcase_report_meta(report_html_path, qid)
    question_lead, question_items = split_numbered_sections(dataset_row.get("question_text", ""))
    _, reference_items = split_numbered_sections(dataset_row.get("answer_text", ""))
    images = copy_showcase_images(
        report_meta["imageNames"],
        report_html_path.parent.parent / "images",
        docs_assets_dir,
        qid,
        SHOWCASE_EXAMPLE["imageCaptions"],
    )
    models = build_showcase_models(graded_dir, report_models, qid, SHOWCASE_GRADER)

    return {
        "qid": qid,
        "title": SHOWCASE_EXAMPLE["title"],
        "deck": SHOWCASE_EXAMPLE["deck"],
        "category": report_meta["category"],
        "pageRange": report_meta["pageRange"],
        "questionLead": question_lead,
        "questionItems": question_items,
        "referenceItems": reference_items,
        "rubric": SHOWCASE_EXAMPLE["rubric"],
        "images": images,
        "grader": {
            "id": SHOWCASE_GRADER,
            "label": model_label(SHOWCASE_GRADER),
        },
        "summary": build_showcase_summary(models),
        "models": models,
    }


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
    grader_agreement = build_grader_agreement_payload(report_data, category_meta)
    showcase_payload = build_showcase_payload(
        dataset_path=dataset_path,
        report_html_path=Path(report_data["meta"]["html_report"]),
        graded_dir=report_data_path.parent,
        docs_assets_dir=out_path.parent,
        report_models=report_data["meta"]["models"],
    )

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
            "showcaseCaseIncluded": True,
            "fullQuestionCorpusIncluded": False,
            "fullAnswerCorpusIncluded": False,
            "fullImageCorpusIncluded": False,
        },
        "graderAgreement": grader_agreement,
        "showcaseExample": showcase_payload,
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
