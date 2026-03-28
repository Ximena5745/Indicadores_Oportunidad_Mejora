"""
scripts/etl/normalizacion.py
Utilidades de normalización: IDs, texto HTML, NaN, LLAVE, columnas.
Sin dependencias de otros módulos etl/.
"""
from __future__ import annotations

import ast
import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Mapas de meses ────────────────────────────────────────────────
MESES_ES: Dict[int, str] = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

# ── Mapa de columnas Excel → campo interno ────────────────────────
COL_ALIASES: Dict[str, str] = {
    "Id": "Id", "Indicador": "Indicador",
    "Proceso": "Proceso", "Periodicidad": "Periodicidad",
    "Sentido": "Sentido", "Fecha": "Fecha",
    "Año": "Anio", "Anio": "Anio",
    "Mes": "Mes",
    "Semestre": "Semestre", "Periodo": "Semestre",
    "Meta": "Meta",
    "Ejecucion": "Ejecucion", "Ejecución": "Ejecucion",
    "Cumplimiento": "Cumplimiento",
    "Cumplimiento Real": "CumplReal",
    "Meta_Signo": "MetaS", "Meta s": "MetaS", "Meta Signo": "MetaS",
    "Ejecucion_Signo": "EjecS", "Ejecucion s": "EjecS",
    "Ejecución s": "EjecS", "Ejecución Signo": "EjecS",
    "Decimales_Meta": "DecMeta", "Decimales": "DecMeta",
    "Decimales_Ejecucion": "DecEjec", "DecimalesEje": "DecEjec",
    "PDI": "PDI", "linea": "linea", "Linea": "linea",
    "LLAVE": "LLAVE", "Llave": "LLAVE",
    "Tipo_Registro": "TipoRegistro",
}

_FORMATOS_VALIDOS = {
    "%", "ENT", "DEC", "$", "Días", "m3", "kWh", "Kg", "tCO2e",
    "No Aplica", "Sin Reporte",
}


# ── Funciones ──────────────────────────────────────────────────────

def _id_str(val: Any) -> str:
    """Normaliza ID a string quitando decimales .0"""
    s = str(val)
    return s[:-2] if s.endswith(".0") else s


# Alias público sin guión bajo
id_str = _id_str


def make_llave(id_val: Any, fecha: Any) -> Optional[str]:
    """Genera llave única 'id-año-mm-dd'."""
    try:
        id_s = _id_str(id_val)
        d = pd.to_datetime(fecha)
        return f"{id_s}-{d.year}-{str(d.month).zfill(2)}-{str(d.day).zfill(2)}"
    except Exception:
        return None


def nan2none(v: Any) -> Any:
    """Convierte NaN/None → None para openpyxl."""
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    return v


def _es_vacio(val: Any) -> bool:
    """True si val es None, NaN, '', 'nan', 'None', '[]'."""
    if val is None:
        return True
    if isinstance(val, float) and np.isnan(val):
        return True
    return str(val).strip() in ("", "nan", "None", "[]")


# Alias público
es_vacio = _es_vacio


def limpiar_html(val: Any) -> Any:
    """Decodifica entidades HTML comunes."""
    if not isinstance(val, str):
        return val
    return (
        val.replace("&oacute;", "ó").replace("&eacute;", "é")
           .replace("&aacute;", "á").replace("&iacute;", "í")
           .replace("&uacute;", "ú").replace("&ntilde;", "ñ")
           .replace("&Eacute;", "É").replace("&amp;", "&")
    )


def limpiar_clasificacion(val: Any) -> Any:
    """Limpia entidades HTML en texto de clasificación."""
    if isinstance(val, str):
        return (
            val.replace("Estrat&eacute;gico", "Estratégico")
               .replace("&eacute;", "é")
               .replace("&amp;", "&")
        )
    return val


def parse_json_safe(val: Any) -> Any:
    """Parsea JSON/Python literal de forma segura; retorna None si falla."""
    if pd.isna(val) or val == "" or val is None:
        return None
    try:
        return ast.literal_eval(str(val))
    except Exception:
        return None


def _fmt_val_raw(val: Any) -> str:
    """Normaliza celda Formato_Valores del Catálogo."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    s = str(val).strip()
    return "" if s in ("", "nan", "None", "0") else s
