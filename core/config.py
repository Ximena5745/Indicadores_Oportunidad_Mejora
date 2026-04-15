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

# Colores específicos por Unidad / Vicerrectoría. Definir colores fijos
# para vicerrectorías clave y dejar un color por defecto para las demás.
VICERRECTORIA_COLORS = {
    # Vicerrectorías solicitadas con color fijo
    "Calidad":    "#1A3A5C",
    "Expansión":  "#1565C0",
    "Experiencia": "#43A047",
    # Puede ampliarse con más mapeos explícitos según se requiera
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

# ── Indicadores con tope de cumplimiento 100% (no sobrecumplimiento) ──────────
# Indicadores de sentido Negativo cuyo cumplimiento no debe superar el 100%.
IDS_TOPE_100 = {"208", "218"}

# ── Aliases de colores para compatibilidad heredada ──────────────────────────
# (core/niveles.py usaba estos nombres)
NIVEL_COLOR = COLOR_CATEGORIA
NIVEL_BG = COLOR_CATEGORIA_CLARO

NIVEL_ICON = {
    "Peligro":           "🔴",
    "Alerta":            "🟡",
    "Cumplimiento":      "🟢",
    "Sobrecumplimiento": "🟢",  # compat con datos históricos (antes usaba 🔵)
    "Sin dato":          "⚪",
}

# ── Orden y visualización de categorías ───────────────────────────────────────
ORDEN_CATEGORIAS = ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento", "Sin dato"]

ICONOS_CATEGORIA = {
    "Peligro":           "🔴",
    "Alerta":            "🟡",
    "Cumplimiento":      "🟢",
    "Sobrecumplimiento": "🔵",
}

# ── Alias para compatibilidad ──────────────────────────────────────────────────
NIVEL_ORDEN = ORDEN_CATEGORIAS

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

# ── Strings de estado / dominio — FUENTE ÚNICA DE VERDAD ──────────────────────
# Usar siempre estas constantes; nunca strings literales en el código.
ESTADO_NO_APLICA  = "No Aplica"
ESTADO_PENDIENTE  = "Pendiente de reporte"
ESTADO_SIN_DATO   = "Sin dato"

SENTIDO_POSITIVO  = "Positivo"
SENTIDO_NEGATIVO  = "Negativo"

TIPO_METRICA      = "metrica"
TIPO_NO_APLICA    = "no aplica"
