"""
Benchmark full pipeline con corridas consecutivas comparables.

Uso:
  python scripts/benchmark_full_pipeline.py --runs 3
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, List


SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

PIPELINE_STEPS = [
    {"name": "consolidar_api", "script": SCRIPT_DIR / "consolidar_api.py"},
    {"name": "actualizar_consolidado", "script": SCRIPT_DIR / "actualizar_consolidado.py"},
    {"name": "generar_reporte", "script": SCRIPT_DIR / "generar_reporte.py"},
]


def _run_step(step_script: Path, timeout_sec: int) -> tuple[float, bool, str | None]:
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, str(step_script)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        elapsed = round(time.perf_counter() - t0, 3)
        if result.returncode == 0:
            return elapsed, True, None
        msg = (result.stderr or result.stdout or "").strip()
        return elapsed, False, f"Exit code {result.returncode}: {msg[:500]}"
    except subprocess.TimeoutExpired:
        elapsed = round(time.perf_counter() - t0, 3)
        return elapsed, False, f"Timeout after {timeout_sec}s"


def _run_once(timeout_sec: int) -> Dict[str, Any]:
    run_data: Dict[str, Any] = {}
    total_t0 = time.perf_counter()
    run_ok = True

    for step in PIPELINE_STEPS:
        elapsed, ok, err = _run_step(step["script"], timeout_sec)
        run_data[f"{step['name']}_s"] = elapsed
        run_data[f"{step['name']}_ok"] = ok
        run_ok = run_ok and ok
        if err:
            run_data[f"{step['name']}_error"] = err

    run_data["total_s"] = round(time.perf_counter() - total_t0, 3)
    run_data["run_ok"] = run_ok
    return run_data


def _summary(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    totals = [r["total_s"] for r in runs]
    summary: Dict[str, Any] = {
        "total_min_s": round(min(totals), 3),
        "total_median_s": round(float(median(totals)), 3),
        "total_max_s": round(max(totals), 3),
        "total_runs": len(runs),
        "successful_runs": sum(1 for r in runs if r.get("run_ok") is True),
    }

    ok_totals = [r["total_s"] for r in runs if r.get("run_ok") is True]
    if ok_totals:
        summary["successful_total_min_s"] = round(min(ok_totals), 3)
        summary["successful_total_median_s"] = round(float(median(ok_totals)), 3)
        summary["successful_total_max_s"] = round(max(ok_totals), 3)
    else:
        summary["successful_total_min_s"] = None
        summary["successful_total_median_s"] = None
        summary["successful_total_max_s"] = None

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark full pipeline")
    parser.add_argument("--runs", type=int, default=3, help="Cantidad de corridas consecutivas")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout por script en segundos")
    parser.add_argument("--output", type=str, default="", help="Ruta de salida JSON opcional")
    args = parser.parse_args()

    if args.runs < 1:
        raise ValueError("--runs debe ser >= 1")

    started = datetime.now()
    runs: List[Dict[str, Any]] = []
    for i in range(1, args.runs + 1):
        run_data = _run_once(timeout_sec=args.timeout)
        run_data["run"] = i
        runs.append(run_data)

    payload: Dict[str, Any] = {
        "timestamp": started.isoformat(timespec="seconds"),
        "method": "benchmark_full_pipeline",
        "runs": runs,
        "summary": _summary(runs),
        "all_runs_ok": all(r.get("run_ok") is True for r in runs),
    }

    if args.output:
        out_file = REPO_ROOT / args.output
    else:
        ts = started.strftime("%Y%m%d_%H%M%S")
        out_file = ARTIFACTS_DIR / f"benchmark_full_pipeline_{args.runs}runs_{ts}.json"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(str(out_file.relative_to(REPO_ROOT)))

    if not payload["all_runs_ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
