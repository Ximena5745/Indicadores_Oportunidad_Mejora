"""
consolidation/core/__init__.py
"""

from .constants import (
    get_project_paths,
    AÑO_CIERRE_ACTUAL,
    MESES_ES,
    KW_EJEC,
    KW_META,
    SIGNO_NA,
    EXT_SERIES_TIPOS,
    COL_ALIASES,
)

from .utils import (
    make_llave,
    calcular_cumplimiento,
    es_registro_na,
    id_str,
    es_vacio,
    nan2none,
    parse_json_safe,
    limpiar_html,
    ValidationError,
    DataError,
)

from .logging_config import setup_logging

__all__ = [
    'get_project_paths',
    'AÑO_CIERRE_ACTUAL',
    'MESES_ES',
    'KW_EJEC',
    'KW_META',
    'SIGNO_NA',
    'EXT_SERIES_TIPOS',
    'COL_ALIASES',
    'make_llave',
    'calcular_cumplimiento',
    'es_registro_na',
    'id_str',
    'es_vacio',
    'nan2none',
    'parse_json_safe',
    'limpiar_html',
    'ValidationError',
    'DataError',
    'setup_logging',
]
