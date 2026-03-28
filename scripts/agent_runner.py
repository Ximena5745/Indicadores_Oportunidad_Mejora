"""
scripts/agent_runner.py
Agente Claude para orquestación inteligente del pipeline ETL.

Flujo:
  1. Ejecuta cada paso del pipeline (consolidar_api → actualizar_consolidado → generar_reporte)
  2. Si un paso falla: envía los logs a Claude para diagnóstico
  3. Claude analiza el error y devuelve: causa raíz + pasos correctivos
  4. El agente decide si reintentar (hotfix simple) o reportar el fallo con contexto
  5. Genera artifacts/agent_run_YYYYMMDD_HHMMSS.json con el informe completo

Uso:
  python scripts/agent_runner.py
  python scripts/agent_runner.py --settings config/settings.toml --dry-run

Variables de entorno:
  ANTHROPIC_API_KEY  — requerida para diagnóstico inteligente (opcional si --no-agent)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────

def _load_toml(path: Path) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError:
            raise RuntimeError("Instala tomli: pip install tomli  (Python < 3.11)")
    return tomllib.loads(path.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────

@dataclass
class StepResult:
    name:        str
    ok:          bool
    returncode:  int | None
    elapsed_s:   float
    stdout:      str = ""
    stderr:      str = ""
    diagnosis:   dict = field(default_factory=dict)   # respuesta del agente


@dataclass
class AgentRun:
    run_id:      str
    started_at:  str
    finished_at: str = ""
    ok:          bool = False
    steps:       list[StepResult] = field(default_factory=list)
    summary:     str = ""
    model_used:  str = ""


# ─────────────────────────────────────────────────────────────────
# Claude diagnosis
# ─────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Eres un experto en ETL de datos institucionales con Python.
Recibirás logs de un pipeline que falló.
Tu respuesta debe ser JSON con exactamente estas claves:
{
  "causa_raiz": "descripción concisa del error (1-2 oraciones)",
  "tipo_error": "FileNotFoundError | PermissionError | KeyError | ValueError | ImportError | Other",
  "archivo_afectado": "ruta o módulo donde ocurre (si se puede inferir)",
  "pasos_correctivos": ["paso 1", "paso 2", ...],
  "es_hotfix_simple": true/false,
  "hotfix_descripcion": "qué haría el hotfix (si aplica, sino null)"
}
Responde SOLO con JSON válido, sin texto adicional."""

_USER_TEMPLATE = """\
Pipeline step: {step_name}
Returncode: {returncode}

=== STDOUT (últimos {n} chars) ===
{stdout}

=== STDERR (últimos {n} chars) ===
{stderr}
"""


def _diagnose_with_claude(
    step_name: str,
    returncode: int | None,
    stdout: str,
    stderr: str,
    cfg: dict,
) -> dict:
    """Llama a Claude para diagnosticar el fallo. Retorna dict con diagnóstico."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"causa_raiz": "ANTHROPIC_API_KEY no configurada — diagnóstico no disponible"}

    try:
        import anthropic
    except ImportError:
        return {"causa_raiz": "anthropic SDK no instalado"}

    model      = cfg.get("model", "claude-opus-4-6")
    max_tokens = int(cfg.get("max_tokens", 2048))
    max_chars  = int(cfg.get("max_log_chars", 12000))
    half       = max_chars // 2

    # Truncar logs para no exceder contexto
    stdout_t = stdout[-half:] if len(stdout) > half else stdout
    stderr_t = stderr[-half:] if len(stderr) > half else stderr
    n_chars  = len(stdout_t) + len(stderr_t)

    user_msg = _USER_TEMPLATE.format(
        step_name=step_name,
        returncode=returncode,
        n=n_chars,
        stdout=stdout_t or "(vacío)",
        stderr=stderr_t or "(vacío)",
    )

    logger.info("  Consultando Claude (%s) para diagnóstico…", model)
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = msg.content[0].text.strip()
        # Extraer JSON aunque venga envuelto en ```json
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as exc:
        logger.warning("  Diagnóstico Claude falló: %s", exc)
        return {"causa_raiz": f"Error al consultar Claude: {exc}"}


# ─────────────────────────────────────────────────────────────────
# Pipeline step execution
# ─────────────────────────────────────────────────────────────────

_STEP_SCRIPTS: dict[str, Path] = {
    "consolidar_api":        _ROOT / "scripts" / "consolidar_api.py",
    "actualizar_consolidado": _ROOT / "scripts" / "actualizar_consolidado.py",
    "generar_reporte":        _ROOT / "scripts" / "generar_reporte.py",
}


def _run_step(name: str, dry_run: bool = False) -> StepResult:
    script = _STEP_SCRIPTS.get(name)
    if script is None:
        return StepResult(name=name, ok=False, returncode=-1, elapsed_s=0,
                          stderr=f"Paso desconocido: {name}")
    if not script.exists():
        return StepResult(name=name, ok=False, returncode=-1, elapsed_s=0,
                          stderr=f"Script no encontrado: {script}")

    if dry_run:
        logger.info("  [DRY-RUN] %s — omitido", name)
        return StepResult(name=name, ok=True, returncode=0, elapsed_s=0,
                          stdout="[dry-run]")

    logger.info("  Ejecutando: %s", script.name)
    t0 = time.perf_counter()
    env = {**os.environ, "PYTHONPATH": str(_ROOT)}
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - t0
    ok = proc.returncode == 0

    if ok:
        logger.info("  OK  (%.1fs)", elapsed)
    else:
        logger.error("  FALLO returncode=%s  (%.1fs)", proc.returncode, elapsed)

    return StepResult(
        name=name,
        ok=ok,
        returncode=proc.returncode,
        elapsed_s=round(elapsed, 2),
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


# ─────────────────────────────────────────────────────────────────
# Summary via Claude
# ─────────────────────────────────────────────────────────────────

def _generate_summary(run: AgentRun, cfg: dict) -> str:
    """Pide a Claude un resumen ejecutivo de la corrida."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "Pipeline completado." if run.ok else "Pipeline falló."

    try:
        import anthropic
    except ImportError:
        return "anthropic SDK no instalado."

    pasos_txt = "\n".join(
        f"- {s.name}: {'OK' if s.ok else 'FALLO'} ({s.elapsed_s}s)"
        for s in run.steps
    )
    diagnoses = {
        s.name: s.diagnosis for s in run.steps if s.diagnosis
    }

    prompt = f"""Pipeline ETL de indicadores institucionales.
Estado general: {"EXITOSO" if run.ok else "FALLIDO"}
Pasos:
{pasos_txt}
Diagnósticos: {json.dumps(diagnoses, ensure_ascii=False, indent=2) if diagnoses else "ninguno"}

Genera un resumen ejecutivo de máximo 3 oraciones en español para un director institucional.
Incluye qué funcionó, qué falló (si aplica), y la acción recomendada."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=cfg.get("model", "claude-opus-4-6"),
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        return f"Resumen no disponible: {exc}"


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Agente Claude para el pipeline ETL.")
    ap.add_argument("--settings", default="config/settings.toml")
    ap.add_argument("--dry-run", action="store_true",
                    help="No ejecuta scripts; solo valida configuración.")
    ap.add_argument("--no-agent", action="store_true",
                    help="Deshabilita diagnóstico Claude (útil sin API key).")
    args = ap.parse_args()

    settings_path = (_ROOT / args.settings).resolve()
    if not settings_path.exists():
        logger.error("settings no encontrado: %s", settings_path)
        return 2

    cfg = _load_toml(settings_path)
    agent_cfg  = cfg.get("agent", {})
    steps_cfg  = cfg.get("pipeline", {}).get("steps", [
        "consolidar_api", "actualizar_consolidado", "generar_reporte"
    ])
    art_dir    = _ROOT / cfg.get("run", {}).get("artifacts_dir", "artifacts")
    art_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run   = AgentRun(
        run_id=stamp,
        started_at=datetime.now().isoformat(timespec="seconds"),
        model_used=agent_cfg.get("model", "claude-opus-4-6") if not args.no_agent else "none",
    )

    logger.info("=" * 60)
    logger.info("  AGENT RUNNER  —  %s", stamp)
    logger.info("  Pasos: %s", " → ".join(steps_cfg))
    logger.info("=" * 60)

    overall_ok = True
    for step_name in steps_cfg:
        logger.info("[%s/%s] %s", steps_cfg.index(step_name) + 1, len(steps_cfg), step_name)
        result = _run_step(step_name, dry_run=args.dry_run)

        if not result.ok and not args.no_agent:
            result.diagnosis = _diagnose_with_claude(
                step_name, result.returncode,
                result.stdout, result.stderr,
                agent_cfg,
            )
            causa = result.diagnosis.get("causa_raiz", "desconocida")
            logger.error("  Diagnóstico: %s", causa)
            pasos = result.diagnosis.get("pasos_correctivos", [])
            for i, p in enumerate(pasos, 1):
                logger.info("    %d. %s", i, p)

        run.steps.append(result)

        if not result.ok:
            overall_ok = False
            logger.error("  Pipeline detenido en paso '%s'.", step_name)
            break

    run.ok = overall_ok
    run.finished_at = datetime.now().isoformat(timespec="seconds")

    # Resumen ejecutivo
    if not args.no_agent:
        logger.info("Generando resumen ejecutivo…")
        run.summary = _generate_summary(run, agent_cfg)
        logger.info("Resumen: %s", run.summary)
    else:
        run.summary = "Pipeline completado." if overall_ok else "Pipeline falló."

    # Guardar reporte
    report_path = art_dir / f"agent_run_{stamp}.json"

    def _step_to_dict(s: StepResult) -> dict:
        d = asdict(s)
        # No guardar stdout/stderr completo en el JSON si son muy largos
        if len(d.get("stdout", "")) > 4000:
            d["stdout"] = d["stdout"][-4000:]
        if len(d.get("stderr", "")) > 4000:
            d["stderr"] = d["stderr"][-4000:]
        return d

    payload: dict[str, Any] = {
        "run_id":      run.run_id,
        "started_at":  run.started_at,
        "finished_at": run.finished_at,
        "ok":          run.ok,
        "model_used":  run.model_used,
        "summary":     run.summary,
        "steps":       [_step_to_dict(s) for s in run.steps],
    }
    report_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info("=" * 60)
    if overall_ok:
        logger.info("  PIPELINE EXITOSO — reporte: artifacts/agent_run_%s.json", stamp)
    else:
        logger.error("  PIPELINE FALLIDO — reporte: artifacts/agent_run_%s.json", stamp)
    logger.info("=" * 60)

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
