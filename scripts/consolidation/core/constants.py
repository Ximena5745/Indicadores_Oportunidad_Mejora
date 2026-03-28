"""
consolidation/core/constants.py
Constantes centralizadas extraídas de actualizar_consolidado.py
"""

from pathlib import Path
from typing import Dict, Set, FrozenSet

# ── Rutas ─────────────────────────────────────────────────────────────
def get_project_paths() -> Dict[str, Path]:
    """Retorna rutas del proyecto calculadas dinámicamente."""
    root = Path(__file__).parent.parent.parent.parent
    base_path = root / "data" / "raw"
    output_dir = root / "data" / "output"
    
    return {
        'ROOT': root,
        'BASE_PATH': base_path,
        'INPUT_FILE': base_path / "Resultados_Consolidados_Fuente.xlsx",
        'OUTPUT_DIR': output_dir,
        'OUTPUT_FILE': output_dir / "Resultados Consolidados.xlsx",
        'KAWAK_CAT_FILE': base_path / "Fuentes Consolidadas" / "Indicadores Kawak.xlsx",
        'CONSOLIDADO_API_KW': base_path / "Fuentes Consolidadas" / "Consolidado_API_Kawak.xlsx",
    }

# ── Configuración Temporal ────────────────────────────────────────────
def _leer_año_cierre() -> int:
    """Lee AÑO_CIERRE_ACTUAL desde config/settings.toml; usa 2025 como fallback."""
    try:
        _toml_path = Path(__file__).parent.parent.parent.parent / "config" / "settings.toml"
        if _toml_path.exists():
            try:
                import tomllib
            except ModuleNotFoundError:
                import tomli as tomllib  # type: ignore[no-redef]
            data = tomllib.loads(_toml_path.read_text(encoding="utf-8"))
            return int(data.get("business", {}).get("año_cierre", 2025))
    except Exception:
        pass
    return 2025


AÑO_CIERRE_ACTUAL: int = _leer_año_cierre()

MESES_ES: Dict[int, str] = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}

_MESES_VALIDOS: Dict[str, list] = {
    'Mensual':    list(range(1, 13)),
    'Trimestral': [3, 6, 9, 12],
    'Semestral':  [6, 12],
    'Anual':      [12],
    'Bimestral':  [2, 4, 6, 8, 10, 12],
}

# ── Keywords para Extracción ──────────────────────────────────────────
KW_EJEC: list = ['real', 'ejecutado', 'recaudado', 'ahorrado', 'consumo', 'generado',
                  'actual', 'logrado', 'obtenido', 'reportado', 'hoy']
KW_META: list = ['planeado', 'presupuestado', 'propuesto', 'programado', 'objetivo',
                  'esperado', 'previsto', 'estimado', 'acumulado plan']

SIGNO_NA: str = 'No Aplica'

# ── Tipos de Extracción ───────────────────────────────────────────────
EXT_SER_SUM_VAR: str = 'Sumar las variables de las series y luego a aplicar la fórmula'
EXT_SER_AVG_RES: str = 'Aplicar la fórmula a cada serie y luego promediar los resultados'
EXT_SER_AVG_VAR: str = 'Promediar las variables de las series y luego a aplicar la fórmula'
EXT_SER_SUM_RES: str = 'Aplicar la fórmula a cada serie y luego sumar los resultados'

EXT_SERIES_TIPOS: FrozenSet[str] = frozenset([
    EXT_SER_SUM_VAR, EXT_SER_AVG_RES, EXT_SER_AVG_VAR, EXT_SER_SUM_RES
])

EXT_DESGLOSE_SERIES: str = 'Desglose Series'

IDS_DESGLOSE_VAR_DIRECTO: FrozenSet[str] = frozenset({'122'})

# ── Mapeo de Columnas ─────────────────────────────────────────────────
COL_ALIASES: Dict[str, str] = {
    'Id': 'Id', 'Indicador': 'Indicador',
    'Proceso': 'Proceso', 'Periodicidad': 'Periodicidad',
    'Sentido': 'Sentido', 'Fecha': 'Fecha',
    'Año': 'Anio', 'Anio': 'Anio',
    'Mes': 'Mes',
    'Semestre': 'Semestre', 'Periodo': 'Semestre',
    'Meta': 'Meta',
    'Ejecucion': 'Ejecucion', 'Ejecución': 'Ejecucion',
    'Cumplimiento': 'Cumplimiento',
    'Cumplimiento Real': 'CumplReal',
    'Meta_Signo': 'MetaS', 'Meta s': 'MetaS', 'Meta Signo': 'MetaS',
    'Ejecucion_Signo': 'EjecS', 'Ejecucion s': 'EjecS',
    'Ejecución s': 'EjecS', 'Ejecución Signo': 'EjecS',
    'Decimales_Meta': 'DecMeta', 'Decimales': 'DecMeta',
    'Decimales_Ejecucion': 'DecEjec', 'DecimalesEje': 'DecEjec',
    'PDI': 'PDI', 'linea': 'linea', 'Linea': 'linea',
    'LLAVE': 'LLAVE', 'Llave': 'LLAVE',
    'Tipo_Registro': 'TipoRegistro',
}

_FORMATOS_VALIDOS: Set[str] = {'%', 'ENT', 'DEC', '$', 'Días', 'm3', 'kWh', 'Kg', 'tCO2e',
                                'No Aplica', 'Sin Reporte'}
