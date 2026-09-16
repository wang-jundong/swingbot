"""Write backtest summary and trades under var/backtest."""

from __future__ import annotations

import json
from pathlib import Path

from src.config.bindings.paths import BACKTEST_PATH


def write_results(payload: dict) -> Path:
    folder = Path(BACKTEST_PATH)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "last.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    summary_path = folder / "summary.json"
    summary_path.write_text(json.dumps(payload.get("summary") or {}, indent=2) + "\n")
    return path
