"""
config.py — Re-export de core/config.py para compatibilidad con imports legacy.

Usar preferentemente: `from core.config import ...`
"""
from core.config import *  # noqa: F401, F403
from core.config import (
    BASE_DIR, DATA_RAW, DATA_OUTPUT, DATA_DB, DB_PATH,
    COLORES, COLOR_CATEGORIA, COLOR_CATEGORIA_CLARO,
    UMBRAL_PELIGRO, UMBRAL_ALERTA, UMBRAL_SOBRECUMPLIMIENTO,
    ORDEN_CATEGORIAS, ICONOS_CATEGORIA,
    COLS_TABLA_RESUMEN, COLS_TABLA_RIESGO, COLS_TABLA_OM,
    CACHE_TTL,
)
