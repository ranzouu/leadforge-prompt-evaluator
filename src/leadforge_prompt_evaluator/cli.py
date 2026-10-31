from __future__ import annotations

import os
import sys
from pathlib import Path

from leadforge_prompt_evaluator.experiment import run_experiment, save_runs


def main() -> int:
    model = os.getenv("MODEL_DEFAULT", "gpt-4o-mini")
    runs_dir = Path("runs")
    print(f"Rodando experimento com modelo={model}...")
    runs = run_experiment(models=[model], runs_dir=str(runs_dir))
    latest_path, summary_path = save_runs(runs, runs_dir=str(runs_dir))
    print(f"Salvo: {latest_path}")
    print(f"Resumo: {summary_path}")
    return 0


