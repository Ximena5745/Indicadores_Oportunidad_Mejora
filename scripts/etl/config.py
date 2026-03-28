"""
scripts/etl/config.py
Configuración centralizada del ETL.

Lee desde config/settings.toml (sección [business]) para que el cambio anual
NO requiera editar código Python.

Fallback: core/config.py → valores hardcodeados por defecto.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import FrozenSet

_ROOT = Path(__file__).parent.parent.parent  # raíz del proyecto


# ── Lector de settings.toml ────────────────────────────────────────
def _load_toml(path: Path) -> dict:
    try:
        try:
            import tomllib          # Python 3.11+
        except ImportError:
            import tomli as tomllib  # pip install tomli  (Python 3.8-3.10)
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


_SETTINGS: dict = _load_toml(_ROOT / "config" / "settings.toml")
_BIZ: dict = _SETTINGS.get("business", {})

# ── AÑO_CIERRE_ACTUAL ─────────────────────────────────────────────
AÑO_CIERRE_ACTUAL: int = int(_BIZ.get("año_cierre", 2025))

# ── IDs especiales ────────────────────────────────────────────────
_DEFAULT_PLAN_ANUAL = [
    "373", "390", "414", "415", "416", "417",
    "418", "420", "469", "470", "471",
]
_DEFAULT_TOPE_100 = ["208", "218"]

# Intentar importar desde core/config.py primero (fuente de verdad de la app)
_core_plan: FrozenSet[str] | None = None
_core_tope: FrozenSet[str] | None = None
try:
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from core.config import IDS_PLAN_ANUAL as _cp, IDS_TOPE_100 as _ct
    _core_plan = _cp
    _core_tope = _ct
except ImportError:
    pass

if _core_plan is not None:
    IDS_PLAN_ANUAL: FrozenSet[str] = _core_plan
else:
    IDS_PLAN_ANUAL = frozenset(
        str(x) for x in _BIZ.get("ids_plan_anual", _DEFAULT_PLAN_ANUAL)
    )

if _core_tope is not None:
    IDS_TOPE_100: FrozenSet[str] = _core_tope
else:
    IDS_TOPE_100 = frozenset(
        str(x) for x in _BIZ.get("ids_tope_100", _DEFAULT_TOPE_100)
    )

# ── Rutas ─────────────────────────────────────────────────────────
BASE_PATH = _ROOT / "data" / "raw"
OUTPUT_DIR = _ROOT / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE        = BASE_PATH / "Resultados_Consolidados_Fuente.xlsx"
OUTPUT_FILE       = OUTPUT_DIR / "Resultados Consolidados.xlsx"
KAWAK_CAT_FILE    = BASE_PATH / "Fuentes Consolidadas" / "Indicadores Kawak.xlsx"
CONSOLIDADO_API_KW = BASE_PATH / "Fuentes Consolidadas" / "Consolidado_API_Kawak.xlsx"
