"""
scripts/etl/periodos.py
Utilidades de fechas y periodicidades.
"""
from __future__ import annotations

import calendar
from typing import Dict, List

import pandas as pd

_MESES_VALIDOS: Dict[str, List[int]] = {
    "Mensual":    list(range(1, 13)),
    "Trimestral": [3, 6, 9, 12],
    "Semestral":  [6, 12],
    "Anual":      [12],
    "Bimestral":  [2, 4, 6, 8, 10, 12],
}


def ultimo_dia_mes(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def fechas_por_periodicidad(periodicidad: str, year: int = 2025) -> List[pd.Timestamp]:
    """Genera lista de fechas (último día) para cada período válido del año."""
    mapa = {
        "Mensual":    [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        "Trimestral": [12, 9, 6, 3],
        "Semestral":  [12, 6],
        "Anual":      [12],
        "Bimestral":  [12, 10, 8, 6, 4, 2],
    }
    meses = mapa.get(periodicidad, [12])
    return [pd.Timestamp(year, m, ultimo_dia_mes(year, m)) for m in meses]


def _fecha_es_periodo_valido(fecha: pd.Timestamp, periodicidad: str) -> bool:
    """True si la fecha cae en un mes de medición válido Y es el último día."""
    meses = _MESES_VALIDOS.get(periodicidad)
    if not meses:
        return True
    if fecha.month not in meses:
        return False
    return fecha.day == ultimo_dia_mes(fecha.year, fecha.month)
