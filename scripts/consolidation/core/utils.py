"""
consolidation/core/utils.py
Utilidades comunes extraídas y refactorizadas
"""

import ast
import calendar
import html
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from .constants import KW_EJEC, KW_META, MESES_ES, SIGNO_NA

logger = logging.getLogger(__name__)


def make_llave(id_val: Any, fecha: Any) -> Optional[str]:
    """
    Genera llave única ID-Fecha.
    
    Args:
        id_val: Valor del ID (int, float, str)
        fecha: Fecha (str, datetime, Timestamp)
    
    Returns:
        String con formato "id-año-mes-día" o None si error
    """
    try:
        id_str = str(id_val)
        if id_str.endswith('.0'):
            id_str = id_str[:-2]
        
        d = pd.to_datetime(fecha)
        return f"{id_str}-{d.year}-{str(d.month).zfill(2)}-{str(d.day).zfill(2)}"
    except Exception as e:
        logger.debug(f"Error generando llave para {id_val}, {fecha}: {e}")
        return None


def ultimo_dia_mes(year: int, month: int) -> int:
    """Retorna el último día del mes."""
    return calendar.monthrange(year, month)[1]


def fechas_por_periodicidad(periodicidad: str, year: int = 2025) -> List[pd.Timestamp]:
    """
    Genera lista de fechas válidas según periodicidad.
    
    Args:
        periodicidad: Tipo de periodicidad (Mensual, Trimestral, etc.)
        year: Año de referencia
    
    Returns:
        Lista de timestamps con último día de cada período
    """
    mapa = {
        'Mensual':    [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        'Trimestral': [12, 9, 6, 3],
        'Semestral':  [12, 6],
        'Anual':      [12],
        'Bimestral':  [12, 10, 8, 6, 4, 2],
    }
    meses = mapa.get(periodicidad, [12])
    return [pd.Timestamp(year, m, ultimo_dia_mes(year, m)) for m in meses]


def fecha_es_periodo_valido(fecha: pd.Timestamp, periodicidad: str) -> bool:
    """
    Valida si una fecha corresponde a un período válido.
    
    Args:
        fecha: Timestamp a validar
        periodicidad: Tipo de periodicidad
    
    Returns:
        True si la fecha es válida para la periodicidad
    """
    _MESES_VALIDOS = {
        'Mensual':    list(range(1, 13)),
        'Trimestral': [3, 6, 9, 12],
        'Semestral':  [6, 12],
        'Anual':      [12],
        'Bimestral':  [2, 4, 6, 8, 10, 12],
    }
    
    meses = _MESES_VALIDOS.get(periodicidad)
    if not meses:
        return True
    
    if fecha.month not in meses:
        return False
    
    return fecha.day == ultimo_dia_mes(fecha.year, fecha.month)


def limpiar_clasificacion(val: Any) -> Any:
    """Limpia entidades HTML en clasificaciones."""
    if isinstance(val, str):
        return (val.replace('Estrat&eacute;gico', 'Estratégico')
                   .replace('&eacute;', 'é')
                   .replace('&amp;', '&'))
    return val


def limpiar_html(val: Any) -> Any:
    """Decodifica entidades HTML comunes."""
    if not isinstance(val, str):
        return val
    
    val = html.unescape(val)
    
    replacements = {
        '&oacute;': 'ó', '&eacute;': 'é', '&aacute;': 'á',
        '&iacute;': 'í', '&uacute;': 'ú', '&ntilde;': 'ñ',
        '&Eacute;': 'É', '&amp;': '&'
    }
    
    for old, new in replacements.items():
        val = val.replace(old, new)
    
    return val


def parse_json_safe(val: Any) -> Optional[Any]:
    """
    Parsea string JSON de forma segura.
    
    Args:
        val: String con representación Python/JSON
    
    Returns:
        Objeto parseado o None si error
    """
    if pd.isna(val) or val == '' or val is None:
        return None
    
    try:
        return ast.literal_eval(str(val))
    except (ValueError, SyntaxError, TypeError) as e:
        logger.debug(f"Error parseando JSON: {e}")
        return None


def nan2none(v: Any) -> Any:
    """
    Convierte NaN/None a None estandarizado.
    
    Útil para compatibilidad con openpyxl.
    """
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    return v


def id_str(val: Any) -> str:
    """
    Normaliza ID a string, removiendo decimales .0
    """
    s = str(val)
    return s[:-2] if s.endswith('.0') else s


def es_vacio(val: Any) -> bool:
    """
    Determina si un valor está vacío/inválido.
    
    Criterios: None, NaN, '', 'nan', 'None', '[]'
    """
    if val is None:
        return True
    if isinstance(val, float) and np.isnan(val):
        return True
    if str(val).strip() in ('', 'nan', 'None', '[]'):
        return True
    return False


def fmt_val_raw(val: Any) -> str:
    """
    Normaliza valores de Formato_Valores del catálogo.
    
    Returns:
        String limpio o vacío
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ''
    
    s = str(val).strip()
    if s in ('', 'nan', 'None', '0'):
        return ''
    
    return s


def calcular_cumplimiento(
    meta: Any, 
    ejec: Any, 
    sentido: str, 
    tope: float = 1.3
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcula cumplimiento capped y real.
    
    Args:
        meta: Valor de meta
        ejec: Valor de ejecución
        sentido: 'Positivo' o 'Negativo'
        tope: Límite superior para capped
    
    Returns:
        Tupla (cumpl_capped, cumpl_real) o (None, None) si inválido
    """
    if meta is None or ejec is None:
        return None, None
    
    try:
        m, e = float(meta), float(ejec)
    except (TypeError, ValueError):
        return None, None
    
    if m == 0:
        return None, None
    
    if sentido == 'Positivo':
        raw = e / m
    else:
        if e == 0:
            return None, None
        raw = m / e
    
    raw = max(raw, 0.0)
    return min(raw, tope), raw


def extraer_meta_ejec_variables(vars_list: List[Dict]) -> Tuple[Optional[float], Optional[float]]:
    """
    Extrae meta y ejecución de lista de variables por keywords.
    
    Args:
        vars_list: Lista de dicts con 'nombre' y 'valor'
    
    Returns:
        Tupla (meta, ejec) o (None, None)
    """
    if not vars_list:
        return None, None
    
    meta_val = ejec_val = None
    
    for v in vars_list:
        nombre = str(v.get('nombre', '')).lower()
        valor = v.get('valor', None)
        
        if valor is None or (isinstance(valor, float) and np.isnan(valor)):
            continue
        
        if any(kw in nombre for kw in KW_META) and meta_val is None:
            meta_val = valor
        elif any(kw in nombre for kw in KW_EJEC) and ejec_val is None:
            ejec_val = valor
    
    if meta_val is None and len(vars_list) >= 2:
        meta_val = vars_list[1].get('valor')
    if ejec_val is None and len(vars_list) >= 1:
        ejec_val = vars_list[0].get('valor')
    
    return meta_val, ejec_val


def extraer_por_simbolo(vars_list: List[Dict], simbolo: str) -> Optional[float]:
    """
    Extrae valor de variable por su símbolo exacto.
    
    Args:
        vars_list: Lista de variables
        simbolo: Símbolo a buscar (case-insensitive)
    
    Returns:
        Valor float o None si no encontrado
    """
    if not vars_list or not simbolo:
        return None
    
    simbolo = str(simbolo).strip().upper()
    
    for v in vars_list:
        if str(v.get('simbolo', '')).strip().upper() == simbolo:
            val = v.get('valor')
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                return float(val)
    
    return None


def tiene_datos_utiles(row: Dict) -> bool:
    """
    Verifica si row tiene datos recuperables en variables o series.
    """
    vars_list = parse_json_safe(row.get('variables'))
    series_list = parse_json_safe(row.get('series'))
    
    if vars_list:
        for v in vars_list:
            val = v.get('valor')
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                return True
    
    if series_list:
        for s in series_list:
            for key in ('resultado', 'meta'):
                v = s.get(key)
                if v is not None and not (isinstance(v, float) and np.isnan(v)):
                    return True
    
    return False


def es_registro_na(row: Dict) -> bool:
    """
    Determina si un registro corresponde a período No Aplica.
    
    Criterios:
      1. Campo 'analisis' contiene 'no aplica'
      2. resultado=NaN y sin datos útiles en variables/series
    """
    resultado = row.get('resultado')
    resultado_num = pd.to_numeric(resultado, errors='coerce')
    
    analisis = str(row.get('analisis', '') or '')
    if 'no aplica' in analisis.lower():
        return True
    
    if resultado_num is not None and not np.isnan(resultado_num):
        return False
    
    if tiene_datos_utiles(row):
        return False
    
    return True


class ValidationError(Exception):
    """Excepción para errores de validación."""
    pass


class DataError(Exception):
    """Excepción para errores de datos."""
    pass
