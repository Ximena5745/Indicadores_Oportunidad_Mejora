"""
core/niveles.py — Niveles de cumplimiento centralizados.

Umbrales FIJOS (aplican en todas las vistas):
  ≥ 100%  → Cumplimiento  (verde    #43A047)
  80–99%  → Alerta        (amarillo #FBAF17)
   < 80%  → Peligro       (rojo     #D32F2F)

Fuente única de umbrales: core/config.py
"""
from core.config import UMBRAL_PELIGRO, UMBRAL_ALERTA, UMBRAL_SOBRECUMPLIMIENTO

# ── Umbrales derivados en escala porcentual ────────────────────────────────────
UMBRAL_PELIGRO_PCT           = UMBRAL_PELIGRO * 100           # 80.0
UMBRAL_ALERTA_PCT            = UMBRAL_ALERTA * 100            # 100.0
UMBRAL_SOBRECUMPLIMIENTO_PCT = UMBRAL_SOBRECUMPLIMIENTO * 100 # 105.0

# ── Aliases decimales (compatibilidad con código existente) ────────────────────
UMBRAL_PELIGRO_DEC           = UMBRAL_PELIGRO
UMBRAL_ALERTA_DEC            = UMBRAL_ALERTA
UMBRAL_SOBRECUMPLIMIENTO_DEC = UMBRAL_SOBRECUMPLIMIENTO

# ── Colores de referencia (sólido) ─────────────────────────────────────────────
NIVEL_COLOR = {
    "Peligro":           "#D32F2F",
    "Alerta":            "#FBAF17",
    "Cumplimiento":      "#43A047",
    "Sobrecumplimiento": "#1A3A5C",
    "Sin dato":          "#BDBDBD",
}

# ── Colores de fondo (celdas de tabla) ─────────────────────────────────────────
NIVEL_BG = {
    "Peligro":           "#FFCDD2",
    "Alerta":            "#FEF3D0",
    "Cumplimiento":      "#E8F5E9",
    "Sobrecumplimiento": "#D0E4FF",
    "Sin dato":          "#F5F5F5",
}

# ── Orden canónico (de peor a mejor) ───────────────────────────────────────────
NIVEL_ORDEN = ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento", "Sin dato"]

# ── Íconos ─────────────────────────────────────────────────────────────────────
NIVEL_ICON = {
    "Peligro":           "🔴",
    "Alerta":            "🟡",
    "Cumplimiento":      "🟢",
    "Sobrecumplimiento": "🟢",  # compatibilidad con datos históricos
    "Sin dato":          "⚪",
}


def nivel_desde_pct(pct) -> str:
    """Clasifica un valor de cumplimiento en escala porcentual (0-100+).
    3 niveles: Peligro (< 80%) | Alerta (80–99.9%) | Cumplimiento (≥ 100%)
    """
    try:
        c = float(pct)
    except (TypeError, ValueError):
        return "Sin dato"
    if c < UMBRAL_PELIGRO_PCT:   # < 80%
        return "Peligro"
    if c < UMBRAL_ALERTA_PCT:    # 80% – 99.9%
        return "Alerta"
    return "Cumplimiento"        # ≥ 100%


def nivel_desde_decimal(dec) -> str:
    """Clasifica un valor de cumplimiento en escala decimal (0-1+)."""
    try:
        c = float(dec)
    except (TypeError, ValueError):
        return "Sin dato"
    return nivel_desde_pct(c * 100)
