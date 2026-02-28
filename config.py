"""
config.py — Constantes globales del dashboard.
"""
from pathlib import Path

# ── Rutas ────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
DATA_RAW  = BASE_DIR / "data" / "raw"
DATA_DB   = BASE_DIR / "data" / "db"
DB_PATH   = DATA_DB / "registros_om.db"

# ── Paleta de colores institucional ──────────────────────────────────────────
COLORES = {
    "peligro":                "#C62828",
    "peligro_claro":          "#FFCDD2",
    "alerta":                 "#F57F17",
    "alerta_claro":           "#FFF9C4",
    "cumplimiento":           "#2E7D32",
    "cumplimiento_claro":     "#C8E6C9",
    "sobrecumplimiento":      "#0277BD",
    "sobrecumplimiento_claro":"#B3E5FC",
    "sin_dato":               "#9E9E9E",
    "primario":               "#1A3A5C",
    "secundario":             "#1565C0",
    "fondo":                  "#F4F6F9",
    "texto":                  "#212121",
}

COLOR_CATEGORIA = {
    "Peligro":          COLORES["peligro"],
    "Alerta":           COLORES["alerta"],
    "Cumplimiento":     COLORES["cumplimiento"],
    "Sobrecumplimiento": COLORES["sobrecumplimiento"],
    "Sin dato":         COLORES["sin_dato"],
}

COLOR_CATEGORIA_CLARO = {
    "Peligro":          COLORES["peligro_claro"],
    "Alerta":           COLORES["alerta_claro"],
    "Cumplimiento":     COLORES["cumplimiento_claro"],
    "Sobrecumplimiento": COLORES["sobrecumplimiento_claro"],
    "Sin dato":         "#EEEEEE",
}

# ── Umbrales de cumplimiento ──────────────────────────────────────────────────
UMBRAL_PELIGRO = 0.80
UMBRAL_ALERTA  = 1.00

# ── Orden de categorías ──────────────────────────────────────────────────────
ORDEN_CATEGORIAS = ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento", "Sin dato"]

# ── Íconos semáforo ───────────────────────────────────────────────────────────
ICONOS_CATEGORIA = {
    "Peligro":          "🔴",
    "Alerta":           "🟡",
    "Cumplimiento":     "🟢",
    "Sobrecumplimiento": "🔵",
}

# ── Columnas de visualización por página ─────────────────────────────────────
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

# ── Cache TTL (segundos) ──────────────────────────────────────────────────────
CACHE_TTL = 300
