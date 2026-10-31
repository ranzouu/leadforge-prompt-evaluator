from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import httpx

PROMPT_VARIANTS = {
    "v1_short": "Classifique o lead como 'quente', 'morno' ou 'frio'. Responda só com a classificação.",
    "v2_structured": "Lead: {lead_name} ({category}) em {city}. Responda em JSON com campos: label (quente|morno|frio), confidence (0-100), reasoning (1 frase).",
    "v3_criteria": "Classifique este lead seguindo critérios de fit para prospecção B2B. Responda JSON: {label, confidence, reasoning}. Critérios: fit_high se cliente final claramente definido; fit_medium se segmento promissor; fit_low se muito genérico.",
}


@dataclass
class Lead:
    id: str
    name: str
    category: str
    city: str
    notes: str = ""


@dataclass
class RunRecord:
    lead_id: str
    variant: str
    model: str
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    label: str = ""
    confidence: str = ""
    reasoning: str = ""
    raw: str = ""


def _load_leads() -> list[Lead]:
    path = Path(__file__).resolve().parents[2] / "data" / "sample_leads.json"
    with open(path, "r", encoding="utf-8") as f:
        return [Lead(**item) for item in json.load(f)]


def _render_prompt(template: str, lead: Lead) -> str:
    return template.replace("{lead_name}", lead.name).replace("{category}", lead.category).replace("{city}", lead.city)


def _call_llm(model: str, prompt: str) -> tuple[str, dict]:
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    timeout = httpx.Timeout(30.0)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Responda de forma objetiva."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 200,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    with httpx.Client(timeout=timeout) as client:
        start = time.perf_counter()
        resp = client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
        latency_ms = (time.perf_counter() - start) * 1000

    if resp.status_code >= 400:
        raise RuntimeError(f"LLM error {resp.status_code}: {resp.text[:200]}")

    body = resp.json()
    text = body["choices"][0]["message"]["content"]
    usage = body.get("usage", {})
    return text, {
        "latency_ms": latency_ms,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }


_DEMO_RESPONSES = {
    "v1_short": {"text": "quente", "prompt_tokens": 18, "completion_tokens": 1},
    "v2_structured": {"text": '{"label": "quente", "confidence": 92, "reasoning": "Perfil com demanda local clara."}', "prompt_tokens": 62, "completion_tokens": 25},
    "v3_criteria": {"text": '{"label": "quente", "confidence": 95, "reasoning": "Cliente final bem definido e segmento com demanda."}', "prompt_tokens": 74, "completion_tokens": 28},
}


def _call_llm_demo(model: str, prompt: str, variant: str) -> tuple[str, dict]:
    base = _DEMO_RESPONSES.get(variant, _DEMO_RESPONSES["v2_structured"])
    return base["text"], {
        "latency_ms": 120.0,
        "prompt_tokens": base["prompt_tokens"],
        "completion_tokens": base["completion_tokens"],
    }


def _extract_json_fields(raw: str) -> tuple[str, str, str]:
    label = ""
    confidence = ""
    reasoning = raw
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        data = json.loads(raw[start:end])
        label = str(data.get("label", "")).strip()
        confidence = str(data.get("confidence", "")).strip()
        reasoning = str(data.get("reasoning", "")).strip()
    except Exception:
        lowered = raw.lower()
        for candidate in ["quente", "morno", "frio"]:
            if candidate in lowered:
                label = candidate
                break
    return label, confidence, reasoning


def run_experiment(models: Iterable[str], runs_dir: str = "runs") -> list[RunRecord]:
    leads = _load_leads()
    runs: list[RunRecord] = []
    Path(runs_dir).mkdir(parents=True, exist_ok=True)

    for model in models:
        for variant_name, template in PROMPT_VARIANTS.items():
            for lead in leads:
                prompt = _render_prompt(template, lead)
                try:
                    if os.getenv("LLM_API_KEY"):
                        raw, meta = _call_llm(model=model, prompt=prompt)
                    else:
                        raw, meta = _call_llm_demo(model=model, prompt=prompt, variant=variant_name)
                    label, confidence, reasoning = _extract_json_fields(raw)
                    runs.append(
                        RunRecord(
                            lead_id=lead.id,
                            variant=variant_name,
                            model=model,
                            latency_ms=round(meta["latency_ms"], 2),
                            prompt_tokens=meta.get("prompt_tokens"),
                            completion_tokens=meta.get("completion_tokens"),
                            label=label,
                            confidence=confidence,
                            reasoning=reasoning,
                            raw=raw,
                        )
                    )
                except Exception as exc:
                    runs.append(
                        RunRecord(
                            lead_id=lead.id,
                            variant=variant_name,
                            model=model,
                            latency_ms=-1.0,
                            raw=str(exc),
                        )
                    )
    return runs


def save_runs(runs: list[RunRecord], runs_dir: str = "runs") -> tuple[Path, Path]:
    latest_path = Path(runs_dir) / "latest.csv"
    summary_path = Path(runs_dir) / "summary.csv"
    latest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(latest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(RunRecord.__dataclass_fields__.keys()))
        writer.writeheader()
        for r in runs:
            writer.writerow(asdict(r))

    by_variant: dict[str, list[RunRecord]] = {}
    for r in runs:
        by_variant.setdefault(r.variant, []).append(r)

    summary_rows = []
    for variant, items in by_variant.items():
        latencies = [r.latency_ms for r in items if r.latency_ms > 0]
        labeled = [r for r in items if r.label]
        summary_rows.append(
            {
                "variant": variant,
                "runs": len(items),
                "errors": sum(1 for r in items if r.latency_ms < 0),
                "labeled": len(labeled),
                "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else "",
                "labels": ", ".join(sorted({r.label for r in labeled})),
            }
        )

    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()) if summary_rows else ["variant"])
        writer.writeheader()
        writer.writerows(summary_rows)

    return latest_path, summary_path
