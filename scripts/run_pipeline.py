"""
scripts/run_pipeline.py
Orquestador del pipeline (Fase 1).

Ejecuta, en orden:
  1) scripts/consolidar_api.py
  2) scripts/actualizar_consolidado.py
  3) generar_reporte.py

Genera artefactos en ./artifacts:
  - pipeline_run_YYYYmmdd_HHMMSS.json
  - pipeline_run_YYYYmmdd_HHMMSS.log

Uso (PowerShell):
  python scripts/run_pipeline.py
  python scripts/run_pipeline.py --settings config/settings.toml
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_toml(path: Path) -> dict:
    try:
        import tomllib  # py 3.11+
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]  # pip install tomli
        except ModuleNotFoundError:
            raise RuntimeError(
                "No se pudo importar tomllib/tomli. "
                "Usa Python >= 3.11 o instala: pip install tomli"
            )
    return tomllib.loads(path.read_text(encoding="utf-8"))

def _load_contract_yaml_minimal(path: Path) -> dict:
    """
    Parser YAML minimal (sin dependencias) para el formato actual de:
      resultados_consolidados: { path, required_sheets: [..] }
      seguimiento_reporte:    { path, required_sheets: [..] }
      fuentes_consolidadas:   { ... }

    Nota: no es un YAML parser completo; solo soporta el sub-conjunto usado
    en `config/data_contract.yaml`.
    """
    if not path.exists():
        return {}

    current_top_key: str | None = None
    in_required_sheets: bool = False
    contract: dict = {}

    def _strip_comment(line: str) -> str:
        # Quita comentarios (#) que no estén dentro de strings (para este caso,
        # asumimos que no hay strings con #).
        if "#" in line:
            return line.split("#", 1)[0]
        return line

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = _strip_comment(raw).rstrip("\n")
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        # Key top-level: "resultados_consolidados:"
        if indent == 0 and content.endswith(":"):
            current_top_key = content[:-1].strip()
            contract[current_top_key] = {}
            in_required_sheets = False
            continue

        if current_top_key is None:
            continue

        # Path: "path: data/output/..."
        if indent >= 2 and content.startswith("path:"):
            contract[current_top_key]["path"] = content[len("path:"):].strip()
            continue

        # required_sheets: [...]
        if indent >= 2 and content.startswith("required_sheets:"):
            in_required_sheets = True
            contract[current_top_key]["required_sheets"] = []
            continue

        # Lista: "- Consolidado Historico"
        if in_required_sheets and indent >= 4 and content.startswith("- "):
            sheet = content[2:].strip()
            if sheet:
                contract[current_top_key]["required_sheets"].append(sheet)
            continue

        # Si cambia de bloque, salimos de required_sheets
        if indent < 4 and content.endswith(":"):
            in_required_sheets = False

    return contract


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", errors="replace")


def _append_text(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8", errors="replace") as f:
        f.write(text)


def _rel(p: Path, base: Path) -> str:
    try:
        return str(p.relative_to(base))
    except Exception:
        return str(p)


@dataclass
class StepResult:
    name: str
    command: List[str]
    cwd: str
    ok: bool
    returncode: int | None
    elapsed_s: float
    stdout_tail: str
    stderr_tail: str


def _run_step(
    name: str,
    command: List[str],
    cwd: Path,
    log_path: Path,
    env: Dict[str, str] | None = None,
    tail_chars: int = 8000,
) -> StepResult:
    t0 = time.perf_counter()
    _append_text(log_path, f"\n---\n[STEP] {name}\nCMD: {' '.join(command)}\nCWD: {cwd}\n")

    proc = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    elapsed = time.perf_counter() - t0
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    _append_text(log_path, f"[EXIT] {proc.returncode}  elapsed_s={elapsed:.2f}\n")
    if stdout.strip():
        _append_text(log_path, f"\n[STDOUT]\n{stdout}\n")
    if stderr.strip():
        _append_text(log_path, f"\n[STDERR]\n{stderr}\n")

    def _tail(s: str) -> str:
        if len(s) <= tail_chars:
            return s
        return s[-tail_chars:]

    return StepResult(
        name=name,
        command=command,
        cwd=str(cwd),
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        elapsed_s=elapsed,
        stdout_tail=_tail(stdout),
        stderr_tail=_tail(stderr),
    )


def _excel_sheetnames(path: Path) -> List[str]:
    import pandas as pd

    xl = pd.ExcelFile(str(path), engine="openpyxl")
    return list(xl.sheet_names)


def _check_required_sheets(path: Path, required: List[str]) -> Tuple[bool, List[str], List[str]]:
    if not path.exists():
        return False, [], required
    try:
        sheets = _excel_sheetnames(path)
    except Exception:
        return False, [], required
    missing = [s for s in required if s not in sheets]
    return len(missing) == 0, sheets, missing


def main() -> int:
    ap = argparse.ArgumentParser(description="Orquestador del pipeline (Fase 1).")
    ap.add_argument(
        "--settings",
        default="config/settings.toml",
        help="Ruta al archivo TOML de configuracion.",
    )
    ap.add_argument(
        "--no-exec",
        action="store_true",
        help="No ejecuta scripts; solo corre validaciones + QA sobre outputs existentes.",
    )
    args = ap.parse_args()

    base_dir = Path(__file__).parent.parent.resolve()
    settings_path = (base_dir / args.settings).resolve()
    if not settings_path.exists():
        print(f"[ERROR] No existe settings: {_rel(settings_path, base_dir)}")
        return 2

    settings = _load_toml(settings_path)
    artifacts_dir = base_dir / settings.get("run", {}).get("artifacts_dir", "artifacts")
    _ensure_dir(artifacts_dir)
    # Archivo centinela para confirmar que la carpeta se crea en el repo
    try:
        (artifacts_dir / ".keep").write_text("", encoding="utf-8")
    except Exception:
        # No abortar la corrida solo por esto, pero quedará reflejado en el log si falla escribir.
        pass

    stamp = _now_stamp()
    log_path = artifacts_dir / f"pipeline_run_{stamp}.log"
    report_path = artifacts_dir / f"pipeline_run_{stamp}.json"

    _write_text(
        log_path,
        f"Pipeline run: {stamp}\nSettings: {_rel(settings_path, base_dir)}\nBase: {base_dir}\n",
    )

    steps_cfg = settings.get("pipeline", {}).get("steps", [])
    if not steps_cfg:
        print("[ERROR] settings.pipeline.steps esta vacio.")
        return 2

    # Construir comandos
    # Nota: usamos sys.executable para asegurar el mismo Python del entorno.
    cmd_map: Dict[str, List[str]] = {
        "consolidar_api": [sys.executable, str(base_dir / "scripts" / "consolidar_api.py")],
        "actualizar_consolidado": [sys.executable, str(base_dir / "scripts" / "actualizar_consolidado.py")],
        "generar_reporte": [sys.executable, str(base_dir / "scripts" / "generar_reporte.py")],
    }

    results: List[StepResult] = []
    t0 = time.perf_counter()

    # Pre-check + ejecucion (opcional)
    checks_cfg = settings.get("checks", {})
    if not args.no_exec:
        # Pre-check: archivos fuente criticos si existen en settings
        precheck_inputs = [
            settings.get("paths", {}).get("input_fuente_consolidado"),
            settings.get("paths", {}).get("kawak_dir"),
            settings.get("paths", {}).get("api_dir"),
        ]
        precheck_inputs = [p for p in precheck_inputs if p]
        missing_inputs = []
        for p in precheck_inputs:
            path = base_dir / str(p)
            if not path.exists():
                missing_inputs.append(_rel(path, base_dir))
        if missing_inputs:
            _append_text(
                log_path,
                f"\n[PRECHECK] FALTAN INSUMOS:\n- " + "\n- ".join(missing_inputs) + "\n",
            )
            print("[ERROR] Faltan insumos de entrada. Ver log:", _rel(log_path, base_dir))
            # No cortamos con codigo 2 para diferenciar de errores de ejecucion
            return 3

        # Ejecutar pasos
        for step_name in steps_cfg:
            if step_name not in cmd_map:
                _append_text(log_path, f"\n[ERROR] Paso desconocido en settings: {step_name}\n")
                print(f"[ERROR] Paso desconocido: {step_name}")
                return 2

            res = _run_step(
                step_name,
                cmd_map[step_name],
                cwd=base_dir,
                log_path=log_path,
                env=os.environ.copy(),
            )
            results.append(res)
            if not res.ok:
                break

        elapsed_total = time.perf_counter() - t0
    else:
        _append_text(log_path, "\n[NO-EXEC] Ejecutando solo validaciones + QA.\n")
        elapsed_total = 0.0

    # Post-checks: outputs y hojas
    required_outputs = [base_dir / p for p in (checks_cfg.get("required_outputs") or [])]
    missing_outputs = [_rel(p, base_dir) for p in required_outputs if not p.exists()]

    sheets_checks: Dict[str, Any] = {}

    # Fase 2: validacion desde data_contract.yaml (si existe)
    contract_path = base_dir / settings.get("checks", {}).get("data_contract_path", "config/data_contract.yaml")
    contract = _load_contract_yaml_minimal(contract_path)

    # Si hay contract, ampliamos validacion de outputs segun los paths definidos
    if contract:
        for _, sec_def in contract.items():
            out_path = sec_def.get("path")
            if not out_path:
                continue
            p = base_dir / str(out_path)
            rel = _rel(p, base_dir)
            if rel not in missing_outputs and not p.exists():
                missing_outputs.append(rel)

    def _sheet_check_for_section(section: str) -> None:
        sec = contract.get(section, {}) or {}
        out_path = sec.get("path")
        required_sheets = sec.get("required_sheets") or []
        if not out_path:
            return
        p = base_dir / str(out_path)
        if not required_sheets:
            sheets_checks[section] = {
                "path": _rel(p, base_dir),
                "ok": bool(p.exists()),
                "sheet_count": None,
                "missing_sheets": [],
            }
            return

        ok, sheets, missing = _check_required_sheets(p, list(required_sheets))
        sheets_checks[section] = {
            "path": _rel(p, base_dir),
            "ok": ok,
            "sheet_count": len(sheets),
            "missing_sheets": missing,
        }

    # Intentar contract; si no hay contrato, caer a settings.
    if contract:
        for sec_name in contract.keys():
            _sheet_check_for_section(sec_name)
    else:
        # Resultados Consolidados
        rc_path = base_dir / settings.get(
            "paths",
            {},
        ).get("out_resultados_consolidados", "data/output/Resultados Consolidados.xlsx")
        ok_rc, rc_sheets, rc_missing = _check_required_sheets(
            rc_path,
            list(checks_cfg.get("resultados_consolidados_required_sheets") or []),
        )
        sheets_checks["resultados_consolidados"] = {
            "path": _rel(rc_path, base_dir),
            "ok": ok_rc,
            "sheet_count": len(rc_sheets),
            "missing_sheets": rc_missing,
        }
        # Seguimiento Reporte
        sr_path = base_dir / settings.get(
            "paths",
            {},
        ).get("out_seguimiento_reporte", "data/output/Seguimiento_Reporte.xlsx")
        ok_sr, sr_sheets, sr_missing = _check_required_sheets(
            sr_path,
            list(checks_cfg.get("seguimiento_reporte_required_sheets") or []),
        )
        sheets_checks["seguimiento_reporte"] = {
            "path": _rel(sr_path, base_dir),
            "ok": ok_sr,
            "sheet_count": len(sr_sheets),
            "missing_sheets": sr_missing,
        }

    # QA Fase 2: validar columnas y conteos (solo hojas primarias para no matar el tiempo)
    qa = {"enabled": True, "primary_checks": {}, "previous_run": None}
    try:
        qa_primary = {
            "resultados_consolidados": ["Consolidado Historico"],
            "seguimiento_reporte": ["Tracking Mensual"],
        }
        import pandas as pd

        # Buscar corrida anterior (latest json)
        prev_report: Path | None = None
        try:
            jsons = sorted(
                [p for p in artifacts_dir.glob("pipeline_run_*.json") if p != report_path],
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )
            if jsons:
                prev_report = jsons[0]
        except Exception:
            prev_report = None

        prev_payload = None
        if prev_report and prev_report.exists():
            try:
                prev_payload = json.loads(prev_report.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                prev_payload = None
        if prev_payload:
            qa["previous_run"] = {"run_id": prev_payload.get("run_id"), "report": _rel(prev_report, base_dir)}

        for sec, primary_sheets in qa_primary.items():
            sec_def = contract.get(sec, {}) if contract else {}
            out_path = sec_def.get("path")
            if not out_path:
                continue
            p = base_dir / str(out_path)
            if not p.exists():
                continue
            qa["primary_checks"][sec] = []
            for sh in primary_sheets:
                # sheet may not exist yet; rely on sheet_checks
                try:
                    if sh not in (sheets_checks.get(sec, {}) or {}).get("missing_sheets", []):
                        xl = pd.ExcelFile(str(p), engine="openpyxl")
                        if sh not in xl.sheet_names:
                            continue
                    df_sh = pd.read_excel(str(p), sheet_name=sh, engine="openpyxl", keep_default_na=False, na_values=[""])
                    cols = [str(c).strip() for c in df_sh.columns]
                    cols_ci = {c.lower() for c in cols}
                    n_rows = int(len(df_sh))
                    required_ci = []
                    if sec == "resultados_consolidados":
                        # Acepta variantes comunes (case-insensitive)
                        required_ci = ["id", "indicador", "cumplimiento"]
                    elif sec == "seguimiento_reporte":
                        required_ci = ["id", "estado", "periodicidad"]

                    missing_cols = [c for c in required_ci if c not in cols_ci]
                    qa["primary_checks"][sec].append(
                        {
                            "sheet": sh,
                            "rows": n_rows,
                            "cols_count": len(cols),
                            "missing_required_columns_ci": missing_cols,
                        }
                    )
                except Exception:
                    # QA no aborta el pipeline; queda en el reporte
                    qa["primary_checks"][sec].append(
                        {"sheet": sh, "rows": None, "cols_count": None, "error": "no se pudo leer"}
                    )

        # Comparacion simple si hay previous QA
        if prev_payload and prev_payload.get("qa"):
            qa_prev = prev_payload.get("qa", {}).get("primary_checks", {})
            deltas = {}
            for sec, checks in qa.get("primary_checks", {}).items():
                prev_checks = (qa_prev or {}).get(sec, [])
                # comparacion por sheet (asumiendo 1 check principal)
                for check in checks:
                    sh = check.get("sheet")
                    prev_match = next((x for x in prev_checks if x.get("sheet") == sh), None)
                    if prev_match and prev_match.get("rows") is not None and check.get("rows") is not None:
                        deltas.setdefault(sec, {})[sh] = {
                            "rows_delta": check["rows"] - prev_match["rows"],
                            "rows_prev": prev_match["rows"],
                        }
            qa["deltas_vs_previous"] = deltas
    except Exception:
        qa["enabled"] = False

    ok_steps = True if args.no_exec else (all(r.ok for r in results) and (len(results) == len(steps_cfg)))
    ok_outputs = len(missing_outputs) == 0
    ok_sheets = True
    # sheets_checks[sec]["ok"] puede existir para varias secciones (contract)
    if sheets_checks:
        ok_sheets = all(v.get("ok", True) for v in sheets_checks.values())

    report = {
        "run_id": stamp,
        "settings": _rel(settings_path, base_dir),
        "base_dir": str(base_dir),
        "elapsed_total_s": round(elapsed_total, 3),
        "ok": bool(ok_steps and ok_outputs and ok_sheets),
        "steps": [
            {
                "name": r.name,
                "ok": r.ok,
                "returncode": r.returncode,
                "elapsed_s": round(r.elapsed_s, 3),
                "command": r.command,
            }
            for r in results
        ],
        "checks": {
            "missing_outputs": missing_outputs,
            "sheets": sheets_checks,
        },
        "qa": qa,
        "artifacts": {
            "log": _rel(log_path, base_dir),
            "report": _rel(report_path, base_dir),
        },
    }

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if report["ok"]:
        print("[OK] Pipeline completado.")
        print("  Log   :", _rel(log_path, base_dir))
        print("  Report:", _rel(report_path, base_dir))
        return 0

    print("[WARN] Pipeline termino con alertas o errores.")
    print("  Log   :", _rel(log_path, base_dir))
    print("  Report:", _rel(report_path, base_dir))
    if not ok_steps:
        return 10
    if not ok_outputs:
        return 11
    if not ok_sheets:
        return 12
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

