"""
scripts/etl/cumplimiento.py
Cálculo de cumplimiento (lógica de negocio pura, sin I/O).
"""
from __future__ import annotations

from typing import Optional, Tuple


def _calc_cumpl(
    meta: object,
    ejec: object,
    sentido: str,
    tope: float = 1.3,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcula (cumpl_capped, cumpl_real) a partir de meta, ejec y sentido.

    Retorna (None, None) si no se puede calcular:
      - meta o ejec son None/no numéricos
      - meta == 0
      - Sentido Negativo con ejec == 0
    """
    if meta is None or ejec is None:
        return None, None
    try:
        m, e = float(meta), float(ejec)
    except (TypeError, ValueError):
        return None, None
    if m == 0:
        return None, None
    if sentido == "Positivo":
        raw = e / m
    else:
        if e == 0:
            return None, None
        raw = m / e
    raw = max(raw, 0.0)
    return min(raw, tope), raw


# Alias público con nombre más descriptivo
calcular_cumplimiento = _calc_cumpl
