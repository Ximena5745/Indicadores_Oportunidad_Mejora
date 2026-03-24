"""
core/config.py — Constantes globales del dashboard.

Fuente única de verdad para colores, umbrales, rutas y columnas de visualización.
Importar SIEMPRE desde aquí: `from core.config import ...`
"""
from pathlib import Path

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent        # raíz del proyecto
DATA_RAW   = BASE_DIR / "data" / "raw"
DATA_OUTPUT = BASE_DIR / "data" / "output"
DATA_DB    = BASE_DIR / "data" / "db"
DB_PATH    = DATA_DB / "registros_om.db"

# ── Paleta de colores institucional ───────────────────────────────────────────
COLORES = {
    "peligro":                "#D32F2F",
    "peligro_claro":          "#FFCDD2",
    "alerta":                 "#FBAF17",
    "alerta_claro":           "#FEF3D0",
    "cumplimiento":           "#43A047",
    "cumplimiento_claro":     "#E8F5E9",
    "sobrecumplimiento":      "#1A3A5C",
    "sobrecumplimiento_claro":"#D0E4FF",
    "sin_dato":               "#BDBDBD",
    "primario":               "#1A3A5C",
    "secundario":             "#1565C0",
    "fondo":                  "#F4F6F9",
    "texto":                  "#212121",
}

COLOR_CATEGORIA = {
    "Peligro":           COLORES["peligro"],
    "Alerta":            COLORES["alerta"],
    "Cumplimiento":      COLORES["cumplimiento"],
    "Sobrecumplimiento": COLORES["sobrecumplimiento"],
    "Sin dato":          COLORES["sin_dato"],
}

COLOR_CATEGORIA_CLARO = {
    "Peligro":           COLORES["peligro_claro"],
    "Alerta":            COLORES["alerta_claro"],
    "Cumplimiento":      COLORES["cumplimiento_claro"],
    "Sobrecumplimiento": COLORES["sobrecumplimiento_claro"],
    "Sin dato":          "#EEEEEE",
}

# ── Umbrales de cumplimiento ───────────────────────────────────────────────────
# Generales:  0–79.9% Peligro | 80–99.9% Alerta | 100–104.99% Cumplimiento | ≥105% Sobrecumplimiento
UMBRAL_PELIGRO           = 0.80
UMBRAL_ALERTA            = 1.00
UMBRAL_SOBRECUMPLIMIENTO = 1.05

# ── Indicadores Plan Anual (PA) — umbrales especiales ─────────────────────────
# Cumplen desde 95% y su tope de cumplimiento es 100% (no hay sobrecumplimiento).
IDS_PLAN_ANUAL = {"373", "390", "414", "415", "416", "417", "418", "420", "469", "470", "471"}
UMBRAL_ALERTA_PA            = 0.95   # PA cumple desde 95%
UMBRAL_SOBRECUMPLIMIENTO_PA = 1.00   # tope 100%

# ── Orden y visualización de categorías ───────────────────────────────────────
ORDEN_CATEGORIAS = ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento", "Sin dato"]

ICONOS_CATEGORIA = {
    "Peligro":           "🔴",
    "Alerta":            "🟡",
    "Cumplimiento":      "🟢",
    "Sobrecumplimiento": "🔵",
}

# ── Columnas de visualización por página ──────────────────────────────────────
COLS_TABLA_RESUMEN = [
    "Id", "Indicador", "Proceso", "Subproceso",
    "Cumplimiento%", "Categoria", "Clasificacion", "Periodicidad",
]

COLS_TABLA_RIESGO = [
    "Id", "Indicador", "Proceso", "Subproceso",
    "Periodicidad", "Periodo", "Cumplimiento%", "Categoria",
]

COLS_TABLA_OM = [
    "id_indicador", "nombre_indicador", "proceso", "periodo",
    "anio", "tiene_om", "numero_om", "comentario", "fecha_registro",
]

# ── Cache TTL (segundos) ───────────────────────────────────────────────────────
CACHE_TTL = 300
