"""
scripts/etl/no_aplica.py
Detección de registros "No Aplica" en la fuente API.

Un indicador marca "No Aplica" cuando NO corresponde medirlo en ese
período específico.  No es un dato faltante: es una decisión explícita.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from .normalizacion import parse_json_safe

SIGNO_NA = "No Aplica"


def _tiene_datos_utiles(row: Dict[str, Any]) -> bool:
    """True si la fila tiene algún valor recuperable en variables o series."""
    vars_list   = parse_json_safe(row.get("variables"))
    series_list = parse_json_safe(row.get("series"))

    if vars_list:
        for v in vars_list:
            val = v.get("valor")
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                return True

    if series_list:
        for s in series_list:
            for key in ("resultado", "meta"):
                val = s.get(key)
                if val is not None and not (isinstance(val, float) and np.isnan(val)):
                    return True

    return False


def is_na_record(row: Dict[str, Any]) -> bool:
    """
    True si el registro no tiene ejecución medible para ese período.

    Criterios:
      1. El campo 'analisis' contiene 'no aplica' (escrito por el responsable).
      2. resultado=NaN  Y  sin datos en variables/series.
    """
    analisis = str(row.get("analisis", "") or "")
    if "no aplica" in analisis.lower():
        return True

    resultado_num = pd.to_numeric(row.get("resultado"), errors="coerce")
    if resultado_num is not None and not (
        isinstance(resultado_num, float) and np.isnan(resultado_num)
    ):
        return False   # tiene resultado numérico → no es N/A

    return not _tiene_datos_utiles(row)
