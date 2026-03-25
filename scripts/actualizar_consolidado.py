"""
Script para actualizar Resultados Consolidados.xlsx
Versión 7 - Lee desde Fuentes Consolidadas (consolidar_api.py)

REQUISITO: ejecutar primero  python scripts/consolidar_api.py
  → genera data/raw/Fuentes Consolidadas/Indicadores Kawak.xlsx
  → genera data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx

═══════════════════════════════════════════════════════════════════════
QUÉ ES "No Aplica":
  Un indicador marca "No Aplica" cuando NO corresponde medirlo en ese
  período específico (por diseño, estacionalidad, fase del proyecto, etc.)
  No es un dato faltante ni un error: es una decisión explícita.

CÓMO SE DETECTA en la fuente API:
  1. El campo 'analisis' contiene el texto "no aplica" (escrito por el
     responsable): "Este periodo no aplica medición", "Para este caso
     no aplica ya que...", etc. → 123 registros en la fuente real.
  2. resultado=NaN  Y  sin datos en variables/series → indicador sin
     ningún valor reportable para ese período → 10,122 registros.

CÓMO SE ESCRIBE en el consolidado:
  - Col K  (Ejecucion)        → None  (celda vacía)
  - Col O  (Ejecucion_Signo)  → "No Aplica"
  - Col L  (Cumplimiento)     → ""  via fórmula =IFERROR(IF(OR(J=0,K=""),"",...),"")
  - Col M  (Cumplimiento Real)→ ""  igual
  - Col J  (Meta)             → se conserva si existe, None si no

COMPATIBILIDAD CON DATOS EXISTENTES:
  El archivo ya tenía 20 filas con Ejecución Signo = "No Aplica".
  obtener_signos() las normaliza y las respeta al leer el archivo base.
═══════════════════════════════════════════════════════════════════════
"""

import pandas as pd
import numpy as np
import ast
import warnings
import calendar
import openpyxl
import shutil
from pathlib import Path
from collections import defaultdict

warnings.filterwarnings('ignore')

_ROOT       = Path(__file__).parent.parent
import sys
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
BASE_PATH   = _ROOT / "data" / "raw"
INPUT_FILE  = BASE_PATH / "Resultados_Consolidados_Fuente.xlsx"
OUTPUT_DIR  = _ROOT / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "Resultados Consolidados.xlsx"
KAWAK_CAT_FILE    = BASE_PATH / "Fuentes Consolidadas" / "Indicadores Kawak.xlsx"
CONSOLIDADO_API_KW = BASE_PATH / "Fuentes Consolidadas" / "Consolidado_API_Kawak.xlsx"

AÑO_CIERRE_ACTUAL = 2025

# Importar IDs Plan Anual desde config (tope cumplimiento = 1.0)
try:
    from core.config import IDS_PLAN_ANUAL
except ImportError:
    IDS_PLAN_ANUAL = {"373", "390", "414", "415", "416", "417", "418", "420", "469", "470", "471"}

KW_EJEC = ['real', 'ejecutado', 'recaudado', 'ahorrado', 'consumo', 'generado',
           'actual', 'logrado', 'obtenido', 'reportado', 'hoy']
KW_META = ['planeado', 'presupuestado', 'propuesto', 'programado', 'objetivo',
           'esperado', 'previsto', 'estimado', 'acumulado plan']

SIGNO_NA = 'No Aplica'   # valor a escribir en Ejecucion_Signo cuando no hay dato

MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}

# ── Mapeo de nombres de columna Excel → campo interno ─────────────────────────
# Soporta variantes de nombres entre las 3 hojas y versiones anteriores del archivo
_COL_ALIASES = {
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


def _build_col_map(ws):
    """Lee el encabezado de la hoja y devuelve {campo_interno: col_idx (1-based)}."""
    cm = {}
    for cell in next(ws.iter_rows(min_row=1, max_row=1)):
        if cell.value is not None:
            campo = _COL_ALIASES.get(str(cell.value).strip())
            if campo:
                cm[campo] = cell.column
    return cm


def _materializar_cumplimiento(ws):
    """
    Recalcula Cumplimiento y Cumplimiento Real para TODAS las filas usando los
    valores reales de Meta, Ejecucion y Sentido de la misma fila.

    Por qué recalcular todas (no solo las fórmulas):
      - El archivo fuente tiene fórmulas como =IFERROR(IF(OR(J1372=0,K1372=""),...))
      - Tras inserciones/borrados, J1372 puede apuntar a una fila DISTINTA al indicador
        de esa celda → porcentajes incorrectos entre hojas para el mismo dato.
      - La única forma confiable es calcular en Python usando los valores de la misma fila.
    """
    cm = _build_col_map(ws)
    idx_meta    = cm.get('Meta')
    idx_ejec    = cm.get('Ejecucion')
    idx_sentido = cm.get('Sentido')
    idx_cumpl   = cm.get('Cumplimiento')
    idx_cumplr  = cm.get('CumplReal')
    if not (idx_meta and idx_ejec and idx_sentido and idx_cumpl):
        return
    n_ok = n_vacio = 0
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        meta    = row[idx_meta    - 1].value
        ejec    = row[idx_ejec    - 1].value
        sentido = row[idx_sentido - 1].value or 'Positivo'

        # Si Meta o Ejecucion son fórmulas sin evaluar, no podemos computar
        if (isinstance(meta, str) and meta.startswith('=')) or \
           (isinstance(ejec, str) and ejec.startswith('=')):
            continue

        cumpl_capped, cumpl_real = _calc_cumpl(meta, ejec, str(sentido))

        c_cumpl = row[idx_cumpl - 1]
        c_cumpl.value = cumpl_capped   # None cuando no aplica (ejec vacío, meta=0, etc.)
        if cumpl_capped is not None:
            c_cumpl.number_format = '0.00%'

        if idx_cumplr:
            c_cumplr = row[idx_cumplr - 1]
            c_cumplr.value = cumpl_real
            if cumpl_real is not None:
                c_cumplr.number_format = '0.00%'

        if cumpl_capped is not None:
            n_ok += 1
        else:
            n_vacio += 1

    print(f"    [{ws.title}] Cumplimiento recalculado: {n_ok} con valor, {n_vacio} vacíos (No Aplica / sin dato).")


def _materializar_formula_año(ws):
    """
    Reemplaza celdas con fórmula en las columnas Año, Mes, Semestre y LLAVE
    por valores calculados desde Fecha e Id.
    openpyxl en modo escritura lee fórmulas como strings; pandas no puede
    usarlas, lo que rompe filtros y joins por esas columnas.
    """
    cm = _build_col_map(ws)
    idx_fecha    = cm.get('Fecha')
    idx_anio     = cm.get('Anio')
    idx_mes      = cm.get('Mes')
    idx_semestre = cm.get('Semestre')
    idx_llave    = cm.get('LLAVE')
    idx_id       = cm.get('Id')
    if not idx_fecha:
        return
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        celda_fecha = row[idx_fecha - 1]
        try:
            fecha = pd.to_datetime(celda_fecha.value)
        except Exception:
            continue
        if idx_anio:
            c = row[idx_anio - 1]
            if isinstance(c.value, str) and c.value.startswith('='):
                c.value = fecha.year
        if idx_mes:
            c = row[idx_mes - 1]
            if isinstance(c.value, str) and c.value.startswith('='):
                c.value = MESES_ES.get(fecha.month, '')
        if idx_semestre:
            c = row[idx_semestre - 1]
            if isinstance(c.value, str) and c.value.startswith('='):
                c.value = f"{fecha.year}-{1 if fecha.month <= 6 else 2}"
        if idx_llave and idx_id:
            c = row[idx_llave - 1]
            if isinstance(c.value, str) and c.value.startswith('='):
                id_val = row[idx_id - 1].value
                c.value = make_llave(id_val, fecha)


def _ensure_tipo_registro_header(ws):
    """Agrega header 'Tipo_Registro' tras la última columna con header, si no existe."""
    header_row = list(next(ws.iter_rows(min_row=1, max_row=1)))
    existing   = {str(c.value).strip() for c in header_row if c.value is not None}
    if 'Tipo_Registro' not in existing:
        last_col = max((c.column for c in header_row if c.value is not None), default=0)
        ws.cell(1, last_col + 1).value = 'Tipo_Registro'


# ─────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────

def make_llave(id_val, fecha):
    try:
        id_str = str(id_val)
        if id_str.endswith('.0'):
            id_str = id_str[:-2]
        d = pd.to_datetime(fecha)
        return f"{id_str}-{d.year}-{str(d.month).zfill(2)}-{str(d.day).zfill(2)}"
    except Exception:
        return None


def ultimo_dia_mes(year, month):
    return calendar.monthrange(year, month)[1]


def fechas_por_periodicidad(periodicidad, year=2025):
    mapa = {
        'Mensual':    [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        'Trimestral': [12, 9, 6, 3],
        'Semestral':  [12, 6],
        'Anual':      [12],
        'Bimestral':  [12, 10, 8, 6, 4, 2],
    }
    meses = mapa.get(periodicidad, [12])
    return [pd.Timestamp(year, m, ultimo_dia_mes(year, m)) for m in meses]


_MESES_VALIDOS = {
    'Mensual':    list(range(1, 13)),
    'Trimestral': [3, 6, 9, 12],
    'Semestral':  [6, 12],
    'Anual':      [12],
    'Bimestral':  [2, 4, 6, 8, 10, 12],
}


def _fecha_es_periodo_valido(fecha, periodicidad):
    """True si la fecha cae en un mes de medición válido Y es el último día del mes."""
    meses = _MESES_VALIDOS.get(periodicidad)
    if not meses:
        return True  # periodicidad desconocida → no filtrar
    if fecha.month not in meses:
        return False
    return fecha.day == ultimo_dia_mes(fecha.year, fecha.month)


def limpiar_clasificacion(val):
    if isinstance(val, str):
        return (val.replace('Estrat&eacute;gico', 'Estratégico')
                   .replace('&eacute;', 'é').replace('&amp;', '&'))
    return val


def parse_json_safe(val):
    if pd.isna(val) or val == '' or val is None:
        return None
    try:
        return ast.literal_eval(str(val))
    except Exception:
        return None


def limpiar_html(val):
    if not isinstance(val, str):
        return val
    return (val.replace('&oacute;', 'ó').replace('&eacute;', 'é')
               .replace('&aacute;', 'á').replace('&iacute;', 'í')
               .replace('&uacute;', 'ú').replace('&ntilde;', 'ñ')
               .replace('&Eacute;', 'É').replace('&amp;', '&'))


def nan2none(v):
    """Convierte NaN/None a None para openpyxl."""
    return None if (v is None or (isinstance(v, float) and np.isnan(v))) else v


def _calc_cumpl(meta, ejec, sentido, tope=1.3):
    """Calcula (cumpl_capped, cumpl_real) a partir de meta, ejec y sentido.

    Retorna (None, None) si no se puede calcular.
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


def _id_str(val):
    s = str(val)
    return s[:-2] if s.endswith('.0') else s


def _es_vacio(val):
    """True si val es None, NaN, string vacío, 'nan', 'None', '[]'."""
    if val is None:
        return True
    if isinstance(val, float) and np.isnan(val):
        return True
    if str(val).strip() in ('', 'nan', 'None', '[]'):
        return True
    return False


# Valores válidos de Formato_Valores en el Catálogo (exactos, tal como vienen del xlsx)
_FORMATOS_VALIDOS = {'%', 'ENT', 'DEC', '$', 'Días', 'm3', 'kWh', 'Kg', 'tCO2e',
                     'No Aplica', 'Sin Reporte'}


def _fmt_val_raw(val):
    """
    Normaliza una celda de la columna Formato_Valores del Catálogo.
    - Valores string reconocidos → se devuelven tal cual (strip)
    - Valor numérico 0            → vacío (se llenará con fallback '%')
    - NaN / None / vacío          → vacío
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ''
    s = str(val).strip()
    if s in ('', 'nan', 'None', '0'):
        return ''
    return s


# ─────────────────────────────────────────────────────────────────────
# DETECCIÓN DE REGISTROS N/A  ← NUEVO
# ─────────────────────────────────────────────────────────────────────

def _tiene_datos_utiles(row):
    """
    True si la fila tiene información recuperable en variables o series
    (es decir, no están vacíos ni son solo ceros).
    """
    vars_list   = parse_json_safe(row.get('variables'))
    series_list = parse_json_safe(row.get('series'))

    if vars_list:
        # Tiene variables con al menos un valor numérico no-cero
        for v in vars_list:
            val = v.get('valor')
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                if val != 0:
                    return True

    if series_list:
        for s in series_list:
            r = s.get('resultado')
            m = s.get('meta')
            for v in (r, m):
                if v is not None and not (isinstance(v, float) and np.isnan(v)):
                    return True

    return False


def is_na_record(row):
    """
    Determina si un registro de la API corresponde a un período donde
    el indicador NO APLICA para medición.

    Criterios (cualquiera es suficiente):
      1. El campo 'analisis' contiene texto 'no aplica' / 'no aplica medición'
         (el responsable explicó explícitamente que no aplica).
      2. resultado=NaN  Y  no hay datos útiles en variables/series
         (el indicador no tiene ningún valor reportable para ese período).

    Retorna True  → escribir Meta (si existe), Ejecucion=None,
                    Ejecucion_Signo='No Aplica', Cumplimiento=vacío.
    Retorna False → el registro tiene dato válido o debe hacerse skip.
    """
    resultado     = row.get('resultado')
    resultado_num = pd.to_numeric(resultado, errors='coerce')

    # ── Criterio 1: texto 'no aplica' en análisis ─────────────────
    analisis = str(row.get('analisis', '') or '')
    if 'no aplica' in analisis.lower():
        return True

    # ── Si tiene resultado numérico válido → NO es N/A ────────────
    if resultado_num is not None and not (isinstance(resultado_num, float)
                                           and np.isnan(resultado_num)):
        return False

    # ── Criterio 2: sin resultado y sin datos útiles ──────────────
    if _tiene_datos_utiles(row):
        return False   # se extraerá de variables/series

    return True


# ─────────────────────────────────────────────────────────────────────
# EXTRACCIÓN META / EJECUCIÓN
# ─────────────────────────────────────────────────────────────────────

def extraer_meta_ejec_variables(vars_list):
    if not vars_list:
        return None, None
    meta_val = ejec_val = None
    for v in vars_list:
        nombre = str(v.get('nombre', '')).lower()
        valor  = v.get('valor', None)
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


def extraer_meta_ejec_series(series_list):
    if not series_list:
        return None, None
    sum_meta = sum_res = 0.0
    has_meta = has_res = False
    for s in series_list:
        m, r = s.get('meta'), s.get('resultado')
        if m is not None and not (isinstance(m, float) and np.isnan(m)):
            sum_meta += float(m); has_meta = True
        if r is not None and not (isinstance(r, float) and np.isnan(r)):
            sum_res  += float(r); has_res  = True
    return (sum_meta if has_meta else None), (sum_res if has_res else None)


def extraer_por_simbolo(vars_list, simbolo):
    """Extrae el valor de una variable específica por su símbolo."""
    if not vars_list or not simbolo:
        return None
    simbolo = str(simbolo).strip().upper()
    for v in vars_list:
        if str(v.get('simbolo', '')).strip().upper() == simbolo:
            val = v.get('valor')
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                return float(val)
    return None


# ─────────────────────────────────────────────────────────────────────
# CONFIG PATRONES
# ─────────────────────────────────────────────────────────────────────

def cargar_config_patrones():
    """
    Lee la hoja 'Config_Patrones' del OUTPUT_FILE si existe.
    Retorna dict: {id_str: {patron, simbolo_ejec, simbolo_meta}}
    Columnas esperadas: Id | Patron_Ejecucion | Simbolo_Ejec | Simbolo_Meta
    """
    if not OUTPUT_FILE.exists():
        return {}
    try:
        xl = pd.ExcelFile(OUTPUT_FILE)
        if 'Config_Patrones' not in xl.sheet_names:
            return {}
        df = pd.read_excel(OUTPUT_FILE, sheet_name='Config_Patrones')
        config = {}
        for _, row in df.iterrows():
            ids = _id_str(row['Id'])
            config[ids] = {
                'patron':       str(row.get('Patron_Ejecucion', 'LAST')).strip().upper(),
                'simbolo_ejec': str(row.get('Simbolo_Ejec', '') or '').strip(),
                'simbolo_meta': str(row.get('Simbolo_Meta', '') or '').strip(),
            }
        return config
    except Exception as e:
        print(f"  [AVISO] Error leyendo Config_Patrones: {e}")
        return {}


def crear_config_patrones_inicial():
    """
    Genera el DataFrame inicial de Config_Patrones a partir del diagnóstico.
    Para indicadores VARIABLES con un símbolo: lo asigna como Simbolo_Ejec.
    Para los demás casos: deja los símbolos vacíos (requieren revisión manual).
    """
    diag_path = OUTPUT_DIR / 'diagnostico_fuente_ejecucion.xlsx'
    if not diag_path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(diag_path, sheet_name='Diagnostico')
    except Exception:
        return pd.DataFrame()

    rows = []
    for _, r in df.iterrows():
        ids    = _id_str(r['ID'])
        patron = str(r.get('Patron_Ejecucion', 'LAST')).strip().upper()
        simbs  = str(r.get('Simbolos_Variables', '') or '').strip()
        lista  = [s.strip() for s in simbs.split(',') if s.strip()] if simbs else []

        simbolo_ejec = ''
        simbolo_meta = ''

        if patron == 'VARIABLES':
            if len(lista) == 1:
                simbolo_ejec = lista[0]
            elif len(lista) == 2:
                # Primera = ejecución, segunda = meta (heurística; editar si es incorrecto)
                simbolo_ejec = lista[0]
                simbolo_meta = lista[1]
            # 3+ símbolos: dejar vacío → el usuario configura

        rows.append({
            'Id':               r['ID'],
            'Indicador':        r.get('Indicador', ''),
            'Patron_Ejecucion': patron,
            'Simbolo_Ejec':     simbolo_ejec,
            'Simbolo_Meta':     simbolo_meta,
            'Simbolos_Disponibles': simbs,
            'Nota': ('Revisar simbolos' if patron == 'VARIABLES' and len(lista) >= 3
                     else ''),
        })

    return pd.DataFrame(rows)


def determinar_meta_ejec(row_api, hist_meta_escala, patron_cfg=None):
    """
    Determina (meta, ejec, fuente, es_na) para un registro.

    patron_cfg (opcional): {'patron': LAST|VARIABLES|SUM_SER|AVG|SUM,
                             'simbolo_ejec': str, 'simbolo_meta': str}

    Retorna:
      fuente = 'api_directo' | 'variables' | 'variables_simbolo' |
               'series_sum' | 'series_sum_fallback' | 'na_record' | 'skip'
      es_na  = True si el registro no tiene ejecución (debe mostrar N/A en signo)
    """
    # ── Detectar N/A antes de cualquier otra lógica ────────────────
    if is_na_record(row_api):
        meta_api = row_api.get('meta')
        meta_val = nan2none(pd.to_numeric(meta_api, errors='coerce')
                            if not _es_vacio(meta_api) else None)
        return meta_val, None, 'na_record', True

    resultado   = row_api.get('resultado')
    meta_api    = row_api.get('meta')
    vars_list   = parse_json_safe(row_api.get('variables'))
    series_list = parse_json_safe(row_api.get('series'))

    # ── Usar patrón configurado explícitamente ─────────────────────
    if patron_cfg:
        patron = patron_cfg.get('patron', 'LAST')

        if patron == 'VARIABLES':
            sim_e = patron_cfg.get('simbolo_ejec', '')
            sim_m = patron_cfg.get('simbolo_meta', '')
            if sim_e and vars_list:
                ejec_v = extraer_por_simbolo(vars_list, sim_e)
                if ejec_v is not None:
                    meta_v = (extraer_por_simbolo(vars_list, sim_m)
                              if sim_m else
                              nan2none(pd.to_numeric(meta_api, errors='coerce')
                                       if not _es_vacio(meta_api) else None))
                    return meta_v, ejec_v, 'variables_simbolo', False
            # Fallback: keyword matching
            if vars_list:
                meta_v, ejec_v = extraer_meta_ejec_variables(vars_list)
                if ejec_v is not None:
                    return meta_v, ejec_v, 'variables', False
            if series_list:
                sum_m, sum_r = extraer_meta_ejec_series(series_list)
                if sum_r is not None:
                    return sum_m, sum_r, 'series_sum', False
            return None, None, 'skip', False

        if patron == 'SUM_SER':
            if series_list:
                sum_m, sum_r = extraer_meta_ejec_series(series_list)
                if sum_r is not None:
                    return sum_m, sum_r, 'series_sum', False
            return None, None, 'skip', False

        if patron == 'LAST':
            resultado_num = pd.to_numeric(resultado, errors='coerce')
            if resultado_num is not None and not (isinstance(resultado_num, float)
                                                   and np.isnan(resultado_num)):
                meta_val = nan2none(pd.to_numeric(meta_api, errors='coerce')
                                    if not _es_vacio(meta_api) else None)
                return meta_val, resultado_num, 'api_directo', False
            return None, None, 'sin_resultado', False

        # AVG/SUM: ya se aplican en la agregación semestral;
        # aquí se usa resultado directo (para el histórico mensual)
        resultado_num = pd.to_numeric(resultado, errors='coerce')
        if resultado_num is not None and not (isinstance(resultado_num, float)
                                               and np.isnan(resultado_num)):
            meta_val = nan2none(pd.to_numeric(meta_api, errors='coerce')
                                if not _es_vacio(meta_api) else None)
            return meta_val, resultado_num, 'api_directo', False
        return None, None, 'sin_resultado', False

    # ── Lógica heurística original (sin config_patrones) ──────────
    es_grande         = (hist_meta_escala is not None and hist_meta_escala > 1000)
    api_es_porcentaje = (not _es_vacio(meta_api) and
                         abs(float(meta_api)) <= 200)

    if es_grande and api_es_porcentaje:
        if vars_list:
            meta_v, ejec_v = extraer_meta_ejec_variables(vars_list)
            if ejec_v is not None:
                return meta_v, ejec_v, 'variables', False
        if series_list:
            sum_m, sum_r = extraer_meta_ejec_series(series_list)
            if sum_r is not None:
                return sum_m, sum_r, 'series_sum', False
        return None, None, 'skip', False

    resultado_num = pd.to_numeric(resultado, errors='coerce')
    if resultado_num is None or (isinstance(resultado_num, float)
                                  and np.isnan(resultado_num)):
        if series_list:
            sum_m, sum_r = extraer_meta_ejec_series(series_list)
            if sum_r is not None:
                return sum_m, sum_r, 'series_sum_fallback', False
        return None, None, 'sin_resultado', False

    meta_val = nan2none(pd.to_numeric(meta_api, errors='coerce')
                        if not _es_vacio(meta_api) else None)
    return meta_val, resultado_num, 'api_directo', False


# ─────────────────────────────────────────────────────────────────────
# CARGA DE FUENTES
# ─────────────────────────────────────────────────────────────────────

def cargar_fuente_consolidada():
    """
    Lee Consolidado_API_Kawak.xlsx (generado por consolidar_api.py) como fuente
    principal de datos.  Reemplaza la lectura directa de data/raw/API/*.xlsx.

    Requisito: ejecutar primero  python scripts/consolidar_api.py
    """
    if not CONSOLIDADO_API_KW.exists():
        print(f"  [ERROR] No se encontró {CONSOLIDADO_API_KW}.\n"
              f"          Ejecutar primero: python scripts/consolidar_api.py")
        return pd.DataFrame()
    df = pd.read_excel(CONSOLIDADO_API_KW)
    df = df.dropna(subset=['fecha'])
    df['fecha'] = pd.to_datetime(df['fecha'])
    if 'clasificacion' in df.columns:
        df['clasificacion'] = df['clasificacion'].apply(limpiar_clasificacion)
    df = df.rename(columns={
        'ID': 'Id', 'nombre': 'Indicador', 'proceso': 'Proceso',
        'frecuencia': 'Periodicidad', 'sentido': 'Sentido',
    })
    df['LLAVE'] = df.apply(lambda r: make_llave(r['Id'], r['fecha']), axis=1)
    return df


def cargar_lmi_reporte():
    """
    Lee lmi_reporte.xlsx y retorna el set de IDs (str) cuyo
    Tipo == 'Metrica' (exacto, case-insensitive) O cuyo nombre de
    Indicador contiene la palabra 'metrica'.
    """
    path = BASE_PATH / "lmi_reporte.xlsx"
    if not path.exists():
        print(f"  [AVISO] No se encontró {path.name}; ids_metrica = vacío")
        return set()
    try:
        df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        # Normalizar nombre de columna Tipo (puede tener tildes u otros chars)
        col_tipo = next((c for c in df.columns if c.lower().startswith('tipo')
                         and 'variable' not in c.lower() and 'calculo' not in c.lower()), None)
        col_ind  = next((c for c in df.columns if c.lower().startswith('indicador')), None)
        col_id   = next((c for c in df.columns if c.lower() == 'id'), 'Id')

        mask = pd.Series(False, index=df.index)
        if col_tipo:
            mask |= df[col_tipo].astype(str).str.strip().str.lower() == 'metrica'
        if col_ind:
            mask |= df[col_ind].astype(str).str.lower().str.contains('metrica', na=False)

        ids = set()
        for val in df.loc[mask, col_id].dropna():
            s = str(val).strip()
            ids.add(s[:-2] if s.endswith('.0') else s)
        return ids
    except Exception as e:
        print(f"  [AVISO] Error leyendo lmi_reporte.xlsx: {e}; ids_metrica = vacío")
        return set()


def cargar_kawak_validos():
    """
    Lee Indicadores Kawak.xlsx (generado por consolidar_api.py) y retorna un set
    de tuplas (id_str, año) que representan los indicadores válidos por año.
    Si el archivo no existe retorna None (sin filtro).
    """
    if not KAWAK_CAT_FILE.exists():
        print(f"  [AVISO] No se encontro {KAWAK_CAT_FILE.name}; "
              f"filtro Kawak desactivado.")
        return None
    try:
        df = pd.read_excel(KAWAK_CAT_FILE)
        df.columns = [str(c).strip() for c in df.columns]
        col_id  = next((c for c in df.columns if c.lower() == 'id'),  None)
        col_año = next((c for c in df.columns if c.lower() in ('año', 'anio', 'year')), None)
        if not col_id or not col_año:
            print(f"  [AVISO] Columnas Id/Año no encontradas en {KAWAK_CAT_FILE.name}.")
            return None
        validos = set()
        for _, row in df.iterrows():
            id_s = _id_str(row[col_id])
            try:
                año = int(float(row[col_año]))
            except (TypeError, ValueError):
                continue
            if id_s:
                validos.add((id_s, año))
        return validos
    except Exception as e:
        print(f"  [AVISO] Error leyendo {KAWAK_CAT_FILE.name}: {e}")
        return None


def cargar_extraccion_map():
    """
    Lee la columna 'Extraccion' del Catalogo Indicadores de INPUT_FILE.
    Retorna dict {id_str: extraccion_str | None}.
    Valores: 'Desglose Variables', 'Consolidado_API_Kawak' o None (vacío).
    """
    if not INPUT_FILE.exists():
        return {}
    try:
        df = pd.read_excel(INPUT_FILE, sheet_name='Catalogo Indicadores')
        df.columns = [str(c).strip() for c in df.columns]
        if 'Extraccion' not in df.columns:
            return {}
        result = {}
        for _, row in df.iterrows():
            id_s = _id_str(row.get('Id', ''))
            val  = row.get('Extraccion')
            if id_s:
                result[id_s] = None if pd.isna(val) else str(val).strip()
        return result
    except Exception as e:
        print(f"  [AVISO] Error leyendo Extraccion del catalogo: {e}")
        return {}


def cargar_consolidado_api_kawak_lookup():
    """
    Carga Consolidado_API_Kawak.xlsx y construye un dict
    {(id_str, fecha_normalizada): (meta, resultado)} para acceso directo.
    """
    if not CONSOLIDADO_API_KW.exists():
        print(f"  [AVISO] No se encontro {CONSOLIDADO_API_KW.name}; "
              f"lookup API_Kawak desactivado.")
        return {}
    try:
        df = pd.read_excel(CONSOLIDADO_API_KW)
        df.columns = [str(c).strip() for c in df.columns]
        col_id   = next((c for c in df.columns if c.upper() == 'ID'), None)
        col_fec  = next((c for c in df.columns if c.lower() == 'fecha'), None)
        col_meta = next((c for c in df.columns if c.lower() == 'meta'), None)
        col_res  = next((c for c in df.columns if c.lower() == 'resultado'), None)
        if not all([col_id, col_fec, col_meta, col_res]):
            print(f"  [AVISO] Columnas faltantes en {CONSOLIDADO_API_KW.name}: "
                  f"id={col_id} fecha={col_fec} meta={col_meta} resultado={col_res}")
            return {}
        df[col_fec] = pd.to_datetime(df[col_fec], errors='coerce')
        lookup = {}
        for _, row in df.iterrows():
            id_s  = _id_str(row[col_id])
            fecha = row[col_fec]
            if pd.isna(fecha) or not id_s:
                continue
            key  = (id_s, fecha.normalize())
            meta = nan2none(row[col_meta])
            res  = nan2none(row[col_res])
            # Si hay duplicados de llave, preferir el que tenga ejecucion
            if key not in lookup or (lookup[key][1] is None and res is not None):
                lookup[key] = (meta, res)
        print(f"  Lookup Consolidado_API_Kawak: {len(lookup):,} registros")
        return lookup
    except Exception as e:
        print(f"  [AVISO] Error leyendo {CONSOLIDADO_API_KW.name}: {e}")
        return {}


def cargar_kawak_old(years=(2021,)):
    frames = []
    for y in years:
        path = BASE_PATH / "Kawak" / f"{y}.xlsx"
        if not path.exists():
            continue
        df = pd.read_excel(path)
        df['año_archivo'] = y
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=['fecha'])
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['clasificacion'] = df['clasificacion'].apply(limpiar_clasificacion)
    df = df.rename(columns={
        'ID': 'Id', 'nombre': 'Indicador', 'proceso': 'Proceso', 'sentido': 'Sentido',
    })
    if 'frecuencia' in df.columns:
        df = df.rename(columns={'frecuencia': 'Periodicidad'})
    elif 'Periodicidad' not in df.columns:
        df['Periodicidad'] = 'Mensual'
    df['LLAVE'] = df.apply(lambda r: make_llave(r['Id'], r['fecha']), axis=1)
    return df


def cargar_kawak_2025():
    path = BASE_PATH / "Kawak" / "2025.xlsx"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_excel(path)
    rename_map = {}
    for col in df.columns:
        if 'Clasificaci' in col:               rename_map[col] = 'clasificacion'
        elif 'Meta' in col and 'ltimo' in col:  rename_map[col] = 'Meta'
        elif 'Tipo de variable' in col:         rename_map[col] = 'Tipo_variable'
        elif 'Tipo de calculo' in col:          rename_map[col] = 'TipoCalculo'
        elif 'Nombre variable' in col:          rename_map[col] = 'NombreVar'
    df = df.rename(columns=rename_map)
    if 'clasificacion' not in df.columns:
        df['clasificacion'] = ''
    df['clasificacion'] = df['clasificacion'].apply(limpiar_clasificacion)

    periodo_cols = [c for c in df.columns if str(c).startswith('Periodo ')]
    df_global = (df[df['NombreVar'].str.contains('Consolidado Global', na=False)].copy()
                 if 'NombreVar' in df.columns else pd.DataFrame())
    ids_sin_global = set(df['Id']) - set(df_global['Id'])
    if ids_sin_global:
        extra = df[df['Id'].isin(ids_sin_global)].drop_duplicates('Id')
        df_global = pd.concat([df_global, extra], ignore_index=True)

    records = []
    for _, row in df_global.iterrows():
        periodicidad = row.get('Periodicidad', 'Mensual')
        fechas       = fechas_por_periodicidad(periodicidad, 2025)
        for i, col in enumerate(periodo_cols):
            if i >= len(fechas):
                break
            valor = row.get(col)
            if pd.isna(valor):
                continue
            records.append({
                'Id': row['Id'], 'Indicador': limpiar_html(str(row.get('Indicador', ''))),
                'clasificacion': row['clasificacion'], 'Proceso': row.get('Proceso', ''),
                'Periodicidad': periodicidad, 'Sentido': row.get('Sentido', ''),
                'TipoCalculo': row.get('TipoCalculo', ''),
                'Meta': row.get('Meta', np.nan), 'resultado': valor,
                'meta': row.get('Meta', np.nan), 'fecha': fechas[i], 'fuente': 'Kawak2025',
            })
    if not records:
        return pd.DataFrame()
    df_k = pd.DataFrame(records)
    df_k['LLAVE'] = df_k.apply(lambda r: make_llave(r['Id'], r['fecha']), axis=1)
    return df_k


# ─────────────────────────────────────────────────────────────────────
# METADATOS KAWAK + CMI
# ─────────────────────────────────────────────────────────────────────

def cargar_metadatos_kawak():
    """
    Lee metadatos desde Indicadores Kawak.xlsx (Fuentes Consolidadas,
    generado por consolidar_api.py) + Kawak/2025.xlsx para TipoCalculo.
    """
    meta = {}

    # Fuente principal: Indicadores Kawak.xlsx (Fuentes Consolidadas)
    if KAWAK_CAT_FILE.exists():
        try:
            df = pd.read_excel(KAWAK_CAT_FILE)
            df.columns = [str(c).strip() for c in df.columns]
            col_id   = next((c for c in df.columns if c.lower() == 'id'), None)
            col_ind  = next((c for c in df.columns if c.lower() == 'indicador'), None)
            col_clas = next((c for c in df.columns if 'clasificaci' in c.lower()), None)
            col_proc = next((c for c in df.columns if c.lower() == 'proceso'), None)
            col_per  = next((c for c in df.columns if c.lower() == 'periodicidad'), None)
            col_sent = next((c for c in df.columns if c.lower() == 'sentido'), None)
            for _, row in df.iterrows():
                id_val = row.get(col_id) if col_id else None
                if pd.isna(id_val):
                    continue
                ids = _id_str(id_val)
                meta[ids] = {
                    'nombre':        limpiar_html(str(row.get(col_ind, '')))  if col_ind  else '',
                    'clasificacion': limpiar_clasificacion(
                                         str(row.get(col_clas, ''))) if col_clas else '',
                    'proceso':       limpiar_html(str(row.get(col_proc, ''))) if col_proc else '',
                    'periodicidad':  str(row.get(col_per, ''))  if col_per  else '',
                    'sentido':       str(row.get(col_sent, '')) if col_sent else '',
                    'tipo_calculo':  '',
                }
        except Exception as e:
            print(f"  [AVISO] Error leyendo {KAWAK_CAT_FILE.name}: {e}")

    # Complementar con Kawak/2025.xlsx para TipoCalculo (no disponible en catálogo)
    path25 = BASE_PATH / "Kawak" / "2025.xlsx"
    if path25.exists():
        try:
            df25     = pd.read_excel(path25)
            clas_col = next((c for c in df25.columns if 'Clasificaci' in c), None)
            tc_col   = next((c for c in df25.columns if 'Tipo de calculo' in c), None)
            for _, row in df25.drop_duplicates('Id').iterrows():
                id_val = row.get('Id')
                if pd.isna(id_val):
                    continue
                ids = _id_str(id_val)
                meta[ids] = {
                    'nombre':        limpiar_html(str(row.get('Indicador', ''))),
                    'clasificacion': limpiar_clasificacion(
                                         str(row.get(clas_col, '')) if clas_col else ''),
                    'proceso':       limpiar_html(str(row.get('Proceso', ''))),
                    'periodicidad':  str(row.get('Periodicidad', '')),
                    'sentido':       str(row.get('Sentido', '')),
                    'tipo_calculo':  str(row.get(tc_col, '')) if tc_col else '',
                }
        except Exception as e:
            print(f"  [AVISO] Error leyendo Kawak/2025.xlsx: {e}")

    return meta


def cargar_metadatos_cmi():
    path = BASE_PATH / "Indicadores por CMI.xlsx"
    if not path.exists():
        return {}
    try:
        df = pd.read_excel(path, sheet_name='Worksheet')
    except Exception:
        return {}
    clas_col = next((c for c in df.columns if 'Clasificaci' in c), None)
    meta = {}
    for _, row in df.iterrows():
        id_val = row.get('Id')
        if pd.isna(id_val):
            continue
        ids = _id_str(id_val)
        meta[ids] = {
            'nombre':        limpiar_html(str(row.get('Indicador', ''))),
            'clasificacion': limpiar_clasificacion(
                                 str(row.get(clas_col, '')) if clas_col else ''),
            'proceso':       limpiar_html(str(row.get('Subproceso', ''))),
            'periodicidad':  str(row.get('Periodicidad', '')),
            'sentido':       str(row.get('Sentido', '')),
            'tipo_calculo':  '',
        }
    return meta


# ─────────────────────────────────────────────────────────────────────
# MAPA SUBPROCESO → PROCESO
# ─────────────────────────────────────────────────────────────────────

def cargar_mapa_procesos():
    """
    Lee Subproceso-Proceso-Area.xlsx y retorna un dict
    {subproceso_lower: proceso_real} para homologar los valores de
    'Proceso' (que en la fuente kawak contiene el Subproceso) al
    Proceso real de la institución.
    """
    path = BASE_PATH / "Subproceso-Proceso-Area.xlsx"
    if not path.exists():
        return {}
    try:
        df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        col_sub  = next((c for c in df.columns if 'Subproceso' in c and '.1' not in c), None)
        col_proc = next((c for c in df.columns if c.lower() == 'proceso'), None)
        if not col_sub or not col_proc:
            return {}
        mapa = {}
        for _, row in df.iterrows():
            sub  = str(row.get(col_sub, '') or '').strip()
            proc = str(row.get(col_proc, '') or '').strip()
            if sub and proc:
                mapa[sub.lower()] = proc
        return mapa
    except Exception as e:
        print(f"  [AVISO] Error leyendo Subproceso-Proceso-Area.xlsx: {e}")
        return {}


def homologar_proceso(subproceso, mapa_procesos):
    """Retorna el Proceso real a partir del Subproceso. Si no hay match,
    devuelve el Subproceso original."""
    if not mapa_procesos or not subproceso:
        return subproceso
    return mapa_procesos.get(str(subproceso).strip().lower(), subproceso)


# ─────────────────────────────────────────────────────────────────────
# CATÁLOGO
# ─────────────────────────────────────────────────────────────────────

def construir_catalogo(df_api, df_hist=None,
                       metadatos_kawak=None, metadatos_cmi=None):
    if metadatos_kawak is None: metadatos_kawak = {}
    if metadatos_cmi   is None: metadatos_cmi   = {}

    # Leer TipoCalculo, Asociacion y Formato_Valores desde la hoja Catalogo
    # del archivo fuente (fuente de verdad curada manualmente).
    # Fallback: output previo para no perder edits si la fuente no tuviera la hoja.
    user_data = {}
    for _src in (INPUT_FILE, OUTPUT_FILE):
        if not _src.exists():
            continue
        try:
            xl = pd.ExcelFile(_src)
            if 'Catalogo Indicadores' not in xl.sheet_names:
                continue
            df_ex = pd.read_excel(_src, sheet_name='Catalogo Indicadores')
            for _, row in df_ex.iterrows():
                ids = _id_str(row['Id'])
                if ids not in user_data:          # fuente tiene prioridad sobre output
                    user_data[ids] = {
                        'TipoCalculo':    str(row.get('TipoCalculo',    '') or '').strip(),
                        'Asociacion':     str(row.get('Asociacion',     '') or '').strip(),
                        'Formato_Valores':_fmt_val_raw(row.get('Formato_Valores')),
                    }
        except Exception:
            pass

    all_ids = {}
    df_last = df_api.sort_values('fecha').groupby('Id').last().reset_index()
    for c in ['Indicador', 'clasificacion', 'Proceso', 'Periodicidad', 'Sentido', 'Tipo', 'estado']:
        if c not in df_last.columns:
            df_last[c] = ''
    for _, row in df_last.iterrows():
        ids = _id_str(row['Id'])
        all_ids[ids] = {
            'Id': row['Id'],
            'Indicador':    limpiar_html(str(row['Indicador'])),
            'Clasificacion':limpiar_clasificacion(str(row['clasificacion'])),
            'Proceso':      limpiar_html(str(row['Proceso'])),
            'Periodicidad': str(row['Periodicidad']),
            'Sentido':      str(row['Sentido']),
            'Tipo_API':     str(row['Tipo']),
            'Estado':       str(row['estado']),
            'Fuente':       'API',
        }

    if df_hist is not None and len(df_hist) > 0:
        df_hc      = df_hist.copy()
        df_hc['Fecha'] = pd.to_datetime(df_hc['Fecha'])
        df_hc_last = df_hc.sort_values('Fecha').groupby('Id').last().reset_index()
        col_ind  = next((c for c in ['Indicador', 'nombre'] if c in df_hc_last.columns), None)
        col_proc = 'Proceso'      if 'Proceso'      in df_hc_last.columns else None
        col_per  = 'Periodicidad' if 'Periodicidad' in df_hc_last.columns else None
        col_sent = 'Sentido'      if 'Sentido'      in df_hc_last.columns else None
        col_clas = next((c for c in ['Clasificacion', 'clasificacion']
                         if c in df_hc_last.columns), None)
        for _, row in df_hc_last.iterrows():
            ids = _id_str(row['Id'])
            if ids not in all_ids:
                all_ids[ids] = {
                    'Id':           row['Id'],
                    'Indicador':    limpiar_html(str(row[col_ind])) if col_ind else '',
                    'Clasificacion':limpiar_clasificacion(str(row[col_clas])) if col_clas else '',
                    'Proceso':      limpiar_html(str(row[col_proc])) if col_proc else '',
                    'Periodicidad': str(row[col_per])  if col_per  else '',
                    'Sentido':      str(row[col_sent]) if col_sent else '',
                    'Tipo_API': '', 'Estado': 'Historico', 'Fuente': 'Historico',
                }

    def _clean(v):
        return '' if (v is None or str(v).strip() in ('', 'nan', 'None')) else str(v).strip()

    rows = []
    for ids, base in all_ids.items():
        kw  = metadatos_kawak.get(ids, {})
        cmi = metadatos_cmi.get(ids, {})
        nombre        = _clean(kw.get('nombre'))        or _clean(cmi.get('nombre'))        or base['Indicador']
        clasificacion = _clean(kw.get('clasificacion')) or _clean(cmi.get('clasificacion')) or base['Clasificacion']
        proceso       = _clean(kw.get('proceso'))       or _clean(cmi.get('proceso'))       or base['Proceso']
        periodicidad  = _clean(kw.get('periodicidad'))  or _clean(cmi.get('periodicidad'))  or base['Periodicidad']
        sentido       = _clean(kw.get('sentido'))       or _clean(cmi.get('sentido'))       or base['Sentido']
        ud             = user_data.get(ids, {})
        tipo_calculo   = _clean(ud.get('TipoCalculo'))     or _clean(kw.get('tipo_calculo', ''))
        asociacion     = _clean(ud.get('Asociacion',    ''))
        formato_valores= _clean(ud.get('Formato_Valores','')) or '%'
        rows.append({
            'Id': base['Id'], 'Indicador': nombre, 'Clasificacion': clasificacion,
            'Proceso': proceso, 'Periodicidad': periodicidad, 'Sentido': sentido,
            'Tipo_API': base['Tipo_API'], 'Estado': base['Estado'], 'Fuente': base['Fuente'],
            'TipoCalculo': tipo_calculo, 'Asociacion': asociacion,
            'Formato_Valores': formato_valores,
        })

    df_cat = pd.DataFrame(rows)
    def sort_key(id_val):
        try:    return (0, float(str(id_val)))
        except: return (1, str(id_val))
    return df_cat.sort_values('Id', key=lambda col: col.map(sort_key)).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────
# SERIES Y ANÁLISIS
# ─────────────────────────────────────────────────────────────────────

def expandir_series(df_api):
    rows = []
    for _, r in df_api.iterrows():
        parsed = parse_json_safe(r.get('series'))
        if not parsed:
            continue
        for s in parsed:
            row_base = {
                'Id': r['Id'], 'Indicador': limpiar_html(str(r.get('Indicador', ''))),
                'Proceso': r.get('Proceso', ''), 'Periodicidad': r.get('Periodicidad', ''),
                'Sentido': r.get('Sentido', ''), 'fecha': r['fecha'], 'LLAVE': r['LLAVE'],
                'serie_nombre': limpiar_html(str(s.get('nombre', ''))),
                'serie_meta': s.get('meta'), 'serie_resultado': s.get('resultado'),
            }
            for v in s.get('variables', []):
                row_base[f"var_{v.get('simbolo', 'X')}"] = v.get('valor')
            rows.append(row_base)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def expandir_variables(df_api):
    rows = []
    for _, r in df_api.iterrows():
        parsed = parse_json_safe(r.get('variables'))
        if not parsed:
            continue
        for v in parsed:
            rows.append({
                'Id':          r['Id'],
                'Indicador':   limpiar_html(str(r.get('Indicador', ''))),
                'Proceso':     r.get('Proceso', ''),
                'Periodicidad':r.get('Periodicidad', ''),
                'Sentido':     r.get('Sentido', ''),
                'fecha':       r['fecha'],
                'LLAVE':       r['LLAVE'],
                'var_simbolo': v.get('simbolo', ''),
                'var_nombre':  limpiar_html(str(v.get('nombre', ''))),
                'var_valor':   v.get('valor'),
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def expandir_analisis(df_api):
    rows = []
    for _, r in df_api.iterrows():
        analisis = r.get('analisis', '')
        if pd.isna(analisis) or not str(analisis).strip():
            continue
        partes = str(analisis).split(' | ', 2)
        rows.append({
            'Id': r['Id'], 'Indicador': limpiar_html(str(r.get('Indicador', ''))),
            'Proceso': r.get('Proceso', ''), 'fecha': r['fecha'], 'LLAVE': r['LLAVE'],
            'analisis_fecha': partes[0].strip() if len(partes) > 0 else '',
            'analisis_autor': partes[1].strip() if len(partes) > 1 else '',
            'analisis_texto': limpiar_html(partes[2].strip() if len(partes) > 2
                                           else str(analisis).strip()),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────
# SIGNOS
# ─────────────────────────────────────────────────────────────────────

def obtener_signos(df_hist, df_sem, df_cierres):
    signos = {}
    col_ejec_candidates = ['Ejecucion_Signo', 'Ejecución Signo', 'Ejecucion Signo', 'Ejecución s', 'Ejecucion s']
    col_ms_candidates   = ['Meta_Signo', 'Meta Signo', 'Meta s']
    for df, col_ms_c, col_es_c in [
        (df_hist,    col_ms_candidates, col_ejec_candidates),
        (df_sem,     col_ms_candidates, col_ejec_candidates),
        (df_cierres, col_ms_candidates, col_ejec_candidates),
    ]:
        col_ms = next((c for c in col_ms_c if c in df.columns), None)
        col_es = next((c for c in col_es_c if c in df.columns), None)
        col_dm = 'Decimales_Meta'      if 'Decimales_Meta'      in df.columns else None
        col_de = 'Decimales_Ejecucion' if 'Decimales_Ejecucion' in df.columns else None
        for _, row in df.sort_values('Fecha').iterrows():
            id_s = str(row['Id'])
            ejec_signo_raw = row.get(col_es, '%') if col_es else '%'
            # Normalizar variantes de "No Aplica" que ya existan en el archivo
            if str(ejec_signo_raw).strip().lower() in ('no aplica', 'n/a', 'no aplica'):
                ejec_signo_raw = SIGNO_NA
            # No sobreescribir un signo real con No Aplica (conservar el último real)
            if ejec_signo_raw == SIGNO_NA and id_s in signos and signos[id_s]['ejec_signo'] != SIGNO_NA:
                continue
            signos[id_s] = {
                'meta_signo': row.get(col_ms, '%') if col_ms else '%',
                'ejec_signo': ejec_signo_raw,
                'dec_meta':   row.get(col_dm, 0)   if col_dm else 0,
                'dec_ejec':   row.get(col_de, 0)   if col_de else 0,
            }
    return signos


# ─────────────────────────────────────────────────────────────────────
# FÓRMULAS EXCEL
# ─────────────────────────────────────────────────────────────────────
# Nota sobre cumplimiento con N/A:
#   Cuando K (Ejecución) es None/vacío, =IFERROR(...,"") devuelve ""
#   porque la división K/J falla → IFERROR captura el error → ""
#   Esto es correcto: no se muestra 0% sino celda vacía.
#
# IMPORTANTE: openpyxl NO ajusta referencias de fórmulas al eliminar filas.
#   Si se borra la fila 50, la celda que estaba en fila 100 pasa a fila 99,
#   pero su fórmula sigue diciendo =YEAR(F100) → apunta a datos de OTRA fila.
#   Por eso _reescribir_formulas() debe ejecutarse DESPUÉS de toda
#   eliminación/inserción de filas.

def formula_G(r): return f"=YEAR(F{r})"
def formula_H(r): return f'=PROPER(TEXT(F{r},"mmmm"))'
def formula_I(r):
    return (f'=IF(OR(H{r}="Enero",H{r}="Febrero",H{r}="Marzo",'
            f'H{r}="Abril",H{r}="Mayo",H{r}="Junio"),'
            f'G{r}&"-1",'
            f'IF(OR(H{r}="Julio",H{r}="Agosto",H{r}="Septiembre",'
            f'H{r}="Octubre",H{r}="Noviembre",H{r}="Diciembre"),'
            f'G{r}&"-2"))')
def formula_L(r, tope=1.3):
    # IFERROR devuelve "" cuando K=vacío (división por cero o con vacío)
    # También devuelve "" cuando J=0 para evitar #DIV/0!
    # tope: 1.3 para indicadores generales, 1.0 para Plan Anual
    return (f'=IFERROR(IF(OR(J{r}=0,K{r}=""),"",IF(E{r}="Positivo",'
            f'MIN(MAX(K{r}/J{r},0),{tope}),'
            f'MIN(MAX(J{r}/K{r},0),{tope}))),"")' )
def formula_M(r, tope=None):
    # Cumplimiento Real: sin tope (muestra el valor real completo)
    return (f'=IFERROR(IF(OR(J{r}=0,K{r}=""),"",IF(E{r}="Positivo",'
            f'MAX(K{r}/J{r},0),'
            f'MAX(J{r}/K{r},0))),"")' )
def formula_R(r):
    return (f'=A{r}&"-"&YEAR(F{r})&"-"'
            f'&IF(LEN(MONTH(F{r}))=1,"0"&MONTH(F{r}),MONTH(F{r}))'
            f'&"-"&IF(LEN(DAY(F{r}))=1,"0"&DAY(F{r}),DAY(F{r}))')


def _reescribir_formulas(ws):
    """
    Reescribe las fórmulas de las 6 columnas derivadas (Año, Mes, Periodo,
    Cumplimiento, Cumplimiento Real, LLAVE) usando el número de fila ACTUAL.

    OBLIGATORIO ejecutar después de TODA eliminación/inserción de filas,
    porque openpyxl NO ajusta las referencias de fórmulas al borrar filas.

    Indicadores Plan Anual (IDS_PLAN_ANUAL) usan tope=1.0 en Cumplimiento.
    """

    cm = _build_col_map(ws)
    idx_id     = cm.get('Id')
    idx_anio   = cm.get('Anio')
    idx_mes    = cm.get('Mes')
    idx_sem    = cm.get('Semestre')
    idx_cumpl  = cm.get('Cumplimiento')
    idx_cumplr = cm.get('CumplReal')
    idx_llave  = cm.get('LLAVE')

    n = 0
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        r = row[0].row

        # Determinar tope según Id del indicador
        id_val = _id_str(row[idx_id - 1].value) if idx_id else None
        tope = 1.0 if id_val in IDS_PLAN_ANUAL else 1.3

        if idx_anio:
            ws.cell(r, idx_anio).value = formula_G(r)
        if idx_mes:
            ws.cell(r, idx_mes).value = formula_H(r)
        if idx_sem:
            ws.cell(r, idx_sem).value = formula_I(r)
        if idx_cumpl:
            c = ws.cell(r, idx_cumpl)
            c.value = formula_L(r, tope=tope)
            c.number_format = '0.00%'
        if idx_cumplr:
            c = ws.cell(r, idx_cumplr)
            c.value = formula_M(r)
            c.number_format = '0.00%'
        if idx_llave:
            ws.cell(r, idx_llave).value = formula_R(r)
        n += 1

    print(f"    [{ws.title}] Fórmulas reescritas en {n:,} filas.")


# ─────────────────────────────────────────────────────────────────────
# LLAVES CALCULADAS Y DEDUPLICACIÓN
# ─────────────────────────────────────────────────────────────────────

def llaves_de_df(df, id_col='Id', fecha_col='Fecha'):
    """
    Calcula LLAVEs desde Id+Fecha (valores reales).
    NO usa la columna LLAVE porque openpyxl guarda fórmulas sin cachear
    → pandas lee NaN → la deduplicación falla.
    """
    llaves = set()
    for _, row in df.iterrows():
        if pd.isna(row.get(fecha_col)):
            continue
        llave = make_llave(row[id_col], row[fecha_col])
        if llave:
            llaves.add(llave)
    return llaves


def _ejec_score(val):
    if val is None:
        return 0
    try:
        return 2 if float(val) != 0.0 else 1
    except Exception:
        return 1 if str(val).strip() not in ('', 'nan', 'None') else 0


def deduplicar_sheet(ws, nombre=''):
    """
    Elimina filas con LLAVE duplicada (mismo Id+Fecha), conservando la que
    tenga ejecución más completa (no nula, no cero).
    Usa el mapa de columnas real de la hoja.
    """
    cm = _build_col_map(ws)
    idx_fecha = cm.get('Fecha',    6) - 1   # 0-based
    idx_ejec  = cm.get('Ejecucion', 11) - 1  # 0-based

    filas = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        try:
            llave = make_llave(row[0].value, row[idx_fecha].value)
        except Exception:
            llave = None
        ejec_val = row[idx_ejec].value if len(row) > idx_ejec else None
        filas.append({'row_idx': row[0].row, 'llave': llave, 'ejec': ejec_val})

    grupos = defaultdict(list)
    for f in filas:
        grupos[f['llave']].append(f)

    filas_a_borrar = []
    for llave, grupo in grupos.items():
        if llave is None or len(grupo) <= 1:
            continue
        mejor = max(grupo, key=lambda f: _ejec_score(f['ejec']))
        filas_a_borrar.extend(
            f['row_idx'] for f in grupo if f['row_idx'] != mejor['row_idx'])

    for r_idx in sorted(filas_a_borrar, reverse=True):
        ws.delete_rows(r_idx)

    print(f"  [{nombre}] {len(filas_a_borrar)} duplicados eliminados.")
    return len(filas_a_borrar)


# ─────────────────────────────────────────────────────────────────────
# ANCLA CONFIABLE DE ÚLTIMA FILA
# ─────────────────────────────────────────────────────────────────────

def get_last_data_row(ws):
    """
    Última fila con valor en columna A. NO usar ws.max_row.
    """
    last = 1
    for row in ws.iter_rows(min_col=1, max_col=1, values_only=False):
        if row[0].value is not None:
            last = row[0].row
    return last


# ─────────────────────────────────────────────────────────────────────
# LIMPIAR CIERRES EXISTENTES
# ─────────────────────────────────────────────────────────────────────

def purgar_filas_invalidas(ws, nombre="hoja", kawak_validos=None):
    """
    Elimina filas donde:
      - La fecha es futura (año > AÑO_CIERRE_ACTUAL)
      - El campo Año contiene texto inválido como 'Avance'
      - El par (Id, año) no existe en el catálogo Indicadores Kawak
        (solo si kawak_validos no es None)
    """
    cm = _build_col_map(ws)
    idx_id    = cm.get('Id',    1) - 1
    idx_fecha = cm.get('Fecha', 6) - 1
    idx_anio  = cm.get('Anio',  7) - 1

    filas_a_borrar = []
    n_kawak = 0
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        fecha_raw = row[idx_fecha].value if len(row) > idx_fecha else None
        año_fila  = None
        try:
            fecha = pd.to_datetime(fecha_raw)
            año_fila = fecha.year
            if fecha.year > AÑO_CIERRE_ACTUAL:
                filas_a_borrar.append(row[0].row)
                continue
        except Exception:
            pass
        anio_val = row[idx_anio].value if len(row) > idx_anio else None
        if anio_val is not None:
            if isinstance(anio_val, str) and anio_val.startswith('='):
                pass
            else:
                try:
                    año_fila = int(float(anio_val))
                except (TypeError, ValueError):
                    filas_a_borrar.append(row[0].row)
                    continue
        # Filtro Kawak: eliminar si (Id, año) no aparece en el catálogo
        if kawak_validos is not None and año_fila is not None:
            id_val = row[idx_id].value if len(row) > idx_id else None
            id_s   = _id_str(id_val) if id_val is not None else None
            if id_s and (id_s, año_fila) not in kawak_validos:
                filas_a_borrar.append(row[0].row)
                n_kawak += 1

    for r_idx in sorted(set(filas_a_borrar), reverse=True):
        ws.delete_rows(r_idx)
    total = len(set(filas_a_borrar))
    if total:
        print(f"  [{nombre}] {total} filas eliminadas "
              f"({n_kawak} por no estar en Indicadores Kawak).")
    return total


def limpiar_cierres_existentes(ws):
    """
    Elimina cortes no-diciembre para años <= AÑO_CIERRE_ACTUAL.
    Reconstruye fórmulas post-eliminación.
    """
    filas = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        fecha_raw = row[5].value
        try:    fecha = pd.to_datetime(fecha_raw)
        except: fecha = None
        filas.append({
            'row_idx': row[0].row,
            'Id':      row[0].value,
            'fecha':   fecha,
            'mes':     fecha.month if fecha else None,
            'año':     fecha.year  if fecha else None,
        })

    if not filas:
        return 0

    grupos = defaultdict(list)
    for f in filas:
        if f['año'] is None:
            continue
        grupos[(str(f['Id']), f['año'])].append(f)

    filas_a_conservar = set()
    for (id_val, año), grupo in grupos.items():
        if año > AÑO_CIERRE_ACTUAL:
            for f in grupo:
                filas_a_conservar.add(f['row_idx'])
        else:
            dic = [f for f in grupo if f['mes'] == 12]
            keep = sorted(dic if dic else grupo, key=lambda f: f['fecha'])[-1]
            filas_a_conservar.add(keep['row_idx'])

    for f in filas:
        if f['año'] is None:
            filas_a_conservar.add(f['row_idx'])

    filas_a_borrar = sorted(
        [f['row_idx'] for f in filas if f['row_idx'] not in filas_a_conservar],
        reverse=True
    )
    for r_idx in filas_a_borrar:
        ws.delete_rows(r_idx)

    print(f"  limpiar_cierres: {len(filas_a_borrar)} filas eliminadas.")
    return len(filas_a_borrar)


def _dedup_cierres_por_año(ws):
    """
    Garantiza UN solo registro por Id+Año en Consolidado Cierres.
    Conserva el registro con la fecha más reciente; elimina los demás.
    """
    cm = _build_col_map(ws)
    idx_fecha = cm.get('Fecha', 6) - 1   # 0-based
    idx_ejec  = cm.get('Ejecucion', 11) - 1

    filas = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        fecha_raw = row[idx_fecha].value
        try:
            fecha = pd.to_datetime(fecha_raw)
        except Exception:
            fecha = None
        ejec_val = row[idx_ejec].value if len(row) > idx_ejec else None
        filas.append({
            'row_idx': row[0].row,
            'Id':      _id_str(row[0].value),
            'fecha':   fecha,
            'año':     fecha.year if fecha else None,
            'ejec':    ejec_val,
        })

    if not filas:
        print("  _dedup_cierres_por_año: sin filas.")
        return 0

    grupos = defaultdict(list)
    for f in filas:
        if f['año'] is None:
            continue
        grupos[(f['Id'], f['año'])].append(f)

    filas_a_borrar = []
    for (id_val, año), grupo in grupos.items():
        if len(grupo) <= 1:
            continue
        # Conservar el más reciente; si empatan, el que tenga mejor ejecución
        mejor = max(grupo, key=lambda f: (f['fecha'] or pd.Timestamp.min,
                                          _ejec_score(f['ejec'])))
        filas_a_borrar.extend(
            f['row_idx'] for f in grupo if f['row_idx'] != mejor['row_idx'])

    for r_idx in sorted(filas_a_borrar, reverse=True):
        ws.delete_rows(r_idx)

    print(f"  _dedup_cierres_por_año: {len(filas_a_borrar)} duplicados eliminados "
          f"({len(grupos)} grupos Id+Año).")
    return len(filas_a_borrar)


# ─────────────────────────────────────────────────────────────────────
# REPARAR META VACÍA EN FILAS EXISTENTES
# ─────────────────────────────────────────────────────────────────────

def reparar_meta_vacia(ws, api_kawak_lookup, nombre=''):
    """
    Recorre filas existentes de la hoja y, para aquellas donde Meta es vacía
    pero existe un valor en api_kawak_lookup, rellena la celda Meta.

    También rellena Ejecucion cuando está vacía pero la fuente tiene dato.
    Retorna el número de celdas Meta reparadas.
    """
    if not api_kawak_lookup:
        return 0

    cm = _build_col_map(ws)
    idx_id    = cm.get('Id')
    idx_fecha = cm.get('Fecha')
    idx_meta  = cm.get('Meta')
    idx_ejec  = cm.get('Ejecucion')
    if not all([idx_id, idx_fecha, idx_meta, idx_ejec]):
        return 0

    n_meta = 0
    n_ejec = 0
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        id_raw    = row[idx_id    - 1].value
        fecha_raw = row[idx_fecha - 1].value
        meta_cell = row[idx_meta  - 1]
        ejec_cell = row[idx_ejec  - 1]

        meta_val = meta_cell.value
        ejec_val = ejec_cell.value

        # Solo actuar si meta está vacía
        if meta_val is not None and not (isinstance(meta_val, float) and np.isnan(meta_val)):
            continue

        try:
            fecha_key = pd.to_datetime(fecha_raw).normalize()
        except Exception:
            continue

        id_s = _id_str(id_raw)
        vals = api_kawak_lookup.get((id_s, fecha_key))
        if vals is None:
            continue

        meta_lookup, ejec_lookup = vals
        if meta_lookup is not None:
            meta_cell.value = meta_lookup
            meta_cell.number_format = 'General'
            n_meta += 1

        # Reparar ejecucion si también está vacía
        if (ejec_val is None or (isinstance(ejec_val, float) and np.isnan(ejec_val))) \
                and ejec_lookup is not None:
            ejec_cell.value = ejec_lookup
            n_ejec += 1

    if n_meta or n_ejec:
        print(f"  [{nombre}] Meta reparada: {n_meta} celdas | Ejecucion reparada: {n_ejec} celdas")
    else:
        print(f"  [{nombre}] Sin Meta vacía reparable desde el lookup.")
    return n_meta


# ─────────────────────────────────────────────────────────────────────
# ESCRITURA DE FILAS
# ─────────────────────────────────────────────────────────────────────

def _validar_col_formulas(cm, nombre_hoja=''):
    """
    Verifica que las columnas usadas por las fórmulas Excel coincidan
    con las posiciones hardcodeadas (A=Id, E=Sentido, F=Fecha, G=Año,
    H=Mes, I=Semestre, J=Meta, K=Ejecucion, R=LLAVE).
    Lanza error si hay desalineación para evitar fórmulas corruptas.
    """
    esperado = {
        'Id': 1, 'Sentido': 5, 'Fecha': 6, 'Anio': 7, 'Mes': 8,
        'Semestre': 9, 'Meta': 10, 'Ejecucion': 11, 'Cumplimiento': 12,
        'CumplReal': 13, 'LLAVE': 18,
    }
    errores = []
    for campo, col_esperada in esperado.items():
        col_real = cm.get(campo)
        if col_real is not None and col_real != col_esperada:
            errores.append(f"    {campo}: esperada col {col_esperada}, "
                           f"encontrada col {col_real}")
    if errores:
        msg = (f"  [ERROR] Columnas desalineadas en [{nombre_hoja}] — "
               f"las fórmulas Excel usan letras fijas (A,E,F,G,H,I,J,K,R):\n"
               + '\n'.join(errores))
        raise ValueError(msg)


def escribir_filas(ws, filas, signos, start_row=None, ids_metrica=None):
    """
    Escribe filas nuevas usando el mapa de columnas real de la hoja (no índices fijos).

    Estructura esperada del INPUT (18 cols):
      1=Id, 2=Indicador, 3=Proceso, 4=Periodicidad, 5=Sentido, 6=Fecha,
      7=Año, 8=Mes, 9=Semestre/Periodo, 10=Meta, 11=Ejecucion,
      12=Cumplimiento, 13=Cumplimiento Real, 14=Meta_Signo, 15=Ejecucion_Signo,
      16=Decimales_Meta, 17=Decimales_Ejecucion, 18=LLAVE
      +19=Tipo_Registro (agregado por el script)
    """
    cm = _build_col_map(ws)
    _validar_col_formulas(cm, ws.title)

    def _set(r, campo, value, fmt=None):
        col = cm.get(campo)
        if col is None:
            return
        ws.cell(r, col).value = value
        if fmt and value is not None:
            ws.cell(r, col).number_format = fmt

    if start_row is None:
        start_row = get_last_data_row(ws) + 1

    r = start_row
    for fila in filas:
        id_str = str(fila.get('Id', ''))
        sg = signos.get(id_str, {
            'meta_signo': '%', 'ejec_signo': '%',
            'dec_meta': 0, 'dec_ejec': 0,
        })

        fecha_raw = fila.get('fecha')
        fecha_dt  = pd.to_datetime(fecha_raw) if fecha_raw is not None else None
        fecha_val = fecha_dt.to_pydatetime().date() if fecha_dt is not None else None

        meta    = nan2none(fila.get('Meta'))
        ejec    = nan2none(fila.get('Ejecucion'))
        es_na   = fila.get('es_na', False)
        sentido = str(fila.get('Sentido', 'Positivo'))
        es_metrica = ids_metrica is not None and id_str in ids_metrica

        if es_na:
            ejec = None

        ejec_signo = SIGNO_NA if es_na else sg['ejec_signo']

        if es_metrica:
            tipo_registro = 'Metrica'
        elif es_na:
            tipo_registro = SIGNO_NA
        else:
            tipo_registro = ''

        cumpl_capped, cumpl_real = _calc_cumpl(meta, ejec, sentido)
        llave = (fila.get('LLAVE') or make_llave(fila.get('Id'), fecha_val))

        _set(r, 'Id',          fila.get('Id'))
        _set(r, 'Indicador',   fila.get('Indicador', ''))
        _set(r, 'Proceso',     fila.get('Proceso', ''))
        _set(r, 'Periodicidad', fila.get('Periodicidad', ''))
        _set(r, 'Sentido',     sentido)
        _set(r, 'Fecha',       fecha_val, 'YYYY-MM-DD')

        # Columnas derivadas: se escriben como fórmulas Excel (igual que las filas existentes)
        # para mantener consistencia visual al abrir el archivo en Excel.
        # data_loader.py las recalcula en Python cuando las lee como NaN.
        _set(r, 'Anio',    formula_G(r))
        _set(r, 'Mes',     formula_H(r))
        _set(r, 'Semestre', formula_I(r))

        _set(r, 'Meta',        meta)
        _set(r, 'Ejecucion',   ejec)
        # Plan Anual: tope=1.0;  resto: tope=1.3
        _tope = 1.0 if _id_str(fila.get('Id')) in IDS_PLAN_ANUAL else 1.3
        _set(r, 'Cumplimiento', formula_L(r, tope=_tope), '0.00%')
        _set(r, 'CumplReal',   formula_M(r), '0.00%')
        _set(r, 'MetaS',       sg['meta_signo'])
        _set(r, 'EjecS',       ejec_signo)
        _set(r, 'DecMeta',     sg.get('dec_meta', 0))
        _set(r, 'DecEjec',     sg.get('dec_ejec', 0))
        _set(r, 'LLAVE',       formula_R(r))
        _set(r, 'TipoRegistro', tipo_registro)

        r += 1

    return r - 1


def escribir_hoja_nueva(wb, nombre, df):
    if nombre in wb.sheetnames:
        del wb[nombre]
    ws = wb.create_sheet(nombre)
    for j, col in enumerate(df.columns, 1):
        ws.cell(1, j).value = col
    for i, (_, row) in enumerate(df.iterrows(), 2):
        for j, col in enumerate(df.columns, 1):
            val = row[col]
            if isinstance(val, pd.Timestamp):
                val = val.to_pydatetime().date()
            elif isinstance(val, float) and np.isnan(val):
                val = None
            ws.cell(i, j).value = val


# ─────────────────────────────────────────────────────────────────────
# CONSTRUIR REGISTROS PARA CADA HOJA
# ─────────────────────────────────────────────────────────────────────

def _extraer_registro(row, hist_escalas, config_patrones=None,
                      extraccion_map=None, api_kawak_lookup=None):
    """
    Extrae (meta, ejec, fuente, es_na) para una fila de fuente.

    Lógica según columna 'Extraccion' del Catalogo Indicadores:
      - 'Desglose Variables' → usa determinar_meta_ejec con patron VARIABLES
      - 'Consolidado_API_Kawak' o vacío → usa meta/resultado directo
        del lookup de Consolidado_API_Kawak.xlsx
    Kawak2025 siempre usa su propio flujo.
    """
    id_val = row.get('Id', row.get('ID'))
    id_s   = _id_str(id_val)
    id_num = pd.to_numeric(id_val, errors='coerce')
    hist_meta_escala = hist_escalas.get(id_num) or hist_escalas.get(str(id_val))

    if 'fuente' in row and row.get('fuente') == 'Kawak2025':
        meta = nan2none(row.get('Meta'))
        ejec = nan2none(row.get('resultado'))
        return meta, ejec, 'Kawak2025', False

    extraccion = (extraccion_map or {}).get(id_s)

    # ── Caso: Consolidado_API_Kawak (o vacío) ─────────────────────
    if extraccion != 'Desglose Variables':
        if api_kawak_lookup:
            fecha_raw = row.get('fecha')
            try:
                fecha_key = pd.to_datetime(fecha_raw).normalize()
            except Exception:
                fecha_key = None
            if fecha_key is not None:
                vals = api_kawak_lookup.get((id_s, fecha_key))
                if vals is not None:
                    meta, res = vals
                    if is_na_record(row.to_dict() if hasattr(row, 'to_dict') else row):
                        return meta, None, 'na_record', True
                    return meta, res, 'api_kawak_directo', res is None
        # Fallback: heurística normal si no hay lookup o no se encontró la llave
        patron_cfg = config_patrones.get(id_s) if config_patrones else None
        meta, ejec, fuente, es_na = determinar_meta_ejec(
            row.to_dict() if hasattr(row, 'to_dict') else row,
            hist_meta_escala,
            patron_cfg=patron_cfg,
        )
        return meta, ejec, fuente, es_na

    # ── Caso: Desglose Variables ───────────────────────────────────
    patron_cfg = config_patrones.get(id_s) if config_patrones else None
    # Forzar patron VARIABLES si no está configurado explícitamente
    if patron_cfg is None:
        patron_cfg = {'patron': 'VARIABLES', 'simbolo_ejec': '', 'simbolo_meta': ''}
    meta, ejec, fuente, es_na = determinar_meta_ejec(
        row.to_dict() if hasattr(row, 'to_dict') else row,
        hist_meta_escala,
        patron_cfg=patron_cfg,
    )
    return meta, ejec, fuente, es_na


def construir_registros_historico(df_fuente, llaves_existentes, hist_escalas,
                                  config_patrones=None, mapa_procesos=None,
                                  kawak_validos=None, extraccion_map=None,
                                  api_kawak_lookup=None):
    registros = []
    skipped   = 0
    conteo_na = 0
    df = df_fuente[~df_fuente['LLAVE'].isin(llaves_existentes)].dropna(subset=['LLAVE'])
    for _, row in df.iterrows():
        # Filtro Kawak: solo procesar si (Id, año) existe en el catálogo
        if kawak_validos is not None:
            id_s  = _id_str(row.get('Id', row.get('ID', '')))
            fecha = row.get('fecha')
            try:
                año = pd.to_datetime(fecha).year
            except Exception:
                año = None
            if año is not None and (id_s, año) not in kawak_validos:
                skipped += 1
                continue
        meta, ejec, fuente, es_na = _extraer_registro(
            row, hist_escalas, config_patrones=config_patrones,
            extraccion_map=extraccion_map, api_kawak_lookup=api_kawak_lookup)
        if fuente == 'skip' or fuente == 'sin_resultado':
            skipped += 1
            continue
        if es_na:
            periodicidad = str(row.get('Periodicidad', ''))
            fecha_row = row['fecha']
            if periodicidad and not _fecha_es_periodo_valido(fecha_row, periodicidad):
                skipped += 1
                continue
            conteo_na += 1
        # Conservar el subproceso tal como viene (col Proceso de las fuentes),
        # para mantener consistencia con los registros históricos existentes.
        proceso = row.get('Proceso', '')
        registros.append({
            'Id': row['Id'], 'Indicador': limpiar_html(str(row.get('Indicador', ''))),
            'Proceso': proceso, 'Periodicidad': row.get('Periodicidad', ''),
            'Sentido': row.get('Sentido', ''), 'fecha': row['fecha'],
            'Meta': meta, 'Ejecucion': ejec, 'LLAVE': row['LLAVE'],
            'es_na': es_na,
        })
    return registros, skipped, conteo_na


def construir_registros_semestral(df_fuente, llaves_existentes, hist_escalas,
                                  config_patrones=None, mapa_procesos=None,
                                  kawak_validos=None, extraccion_map=None,
                                  api_kawak_lookup=None):
    """
    Genera registros para Consolidado Semestral.
    Para indicadores con patrón AVG o SUM, agrega resultados mensuales
    del semestre en lugar de tomar el dato puntual de junio/diciembre.
    """
    # IDs con agregación temporal (AVG/SUM)
    ids_avg = set()
    ids_sum = set()
    if config_patrones:
        for ids, cfg in config_patrones.items():
            if cfg['patron'] == 'AVG':
                ids_avg.add(ids)
            elif cfg['patron'] == 'SUM':
                ids_sum.add(ids)

    df_base = df_fuente.copy()
    df_base['_ids'] = df_base['Id'].apply(_id_str)
    df_base['_sem'] = df_base['fecha'].apply(
        lambda d: f"{d.year}-{'1' if d.month <= 6 else '2'}"
    )

    partes = []

    # ── Indicadores sin agregación: filtrar jun/dic ─────────────────
    ids_agg = ids_avg | ids_sum
    df_std = df_base[~df_base['_ids'].isin(ids_agg)].copy()
    df_std = df_std[df_std['fecha'].dt.month.isin([6, 12])]
    df_std = df_std[df_std['fecha'] == df_std['fecha'].apply(
        lambda d: pd.Timestamp(d.year, d.month, ultimo_dia_mes(d.year, d.month)))]
    partes.append(df_std)

    # ── Indicadores AVG/SUM: agregar por Id + semestre ─────────────
    if ids_agg:
        df_agg_src = df_base[df_base['_ids'].isin(ids_agg)].copy()
        agg_rows = []
        for (id_val, sem_label), grupo in df_agg_src.groupby(['Id', '_sem']):
            ids = _id_str(id_val)
            patron = 'AVG' if ids in ids_avg else 'SUM'
            resultados = pd.to_numeric(grupo['resultado'], errors='coerce').dropna()
            if len(resultados) == 0:
                continue
            ejec_agg = resultados.mean() if patron == 'AVG' else resultados.sum()
            # Fecha = último día del mes de cierre del semestre
            year, sem = int(sem_label.split('-')[0]), int(sem_label.split('-')[1])
            end_month = 6 if sem == 1 else 12
            end_fecha = pd.Timestamp(year, end_month, ultimo_dia_mes(year, end_month))
            # Tomar la última fila del grupo como base para los metadatos
            last = grupo.sort_values('fecha').iloc[-1].copy()
            last['resultado'] = ejec_agg
            last['fecha']     = end_fecha
            last['LLAVE']     = make_llave(id_val, end_fecha)
            agg_rows.append(last)
        if agg_rows:
            partes.append(pd.DataFrame(agg_rows))

    df_sem = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    df_sem = df_sem.drop(columns=['_ids', '_sem'], errors='ignore')

    return construir_registros_historico(
        df_sem, llaves_existentes, hist_escalas,
        config_patrones=config_patrones, mapa_procesos=mapa_procesos,
        kawak_validos=kawak_validos, extraccion_map=extraccion_map,
        api_kawak_lookup=api_kawak_lookup,
    )


def construir_registros_cierres(df_fuente, hist_escalas,
                                config_patrones=None, mapa_procesos=None,
                                kawak_validos=None, extraccion_map=None,
                                api_kawak_lookup=None):
    df = df_fuente.copy()
    df['año'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    registros = []
    skipped   = 0
    conteo_na = 0

    for (id_val, año), grupo in df.groupby(['Id', 'año']):
        # Filtro Kawak: saltar el año completo si (Id, año) no está en el catálogo
        if kawak_validos is not None:
            id_s = _id_str(id_val)
            if (id_s, int(año)) not in kawak_validos:
                skipped += len(grupo)
                continue

        if año > AÑO_CIERRE_ACTUAL:
            # Solo el registro más reciente del año
            candidatos = grupo.sort_values('fecha').tail(1)
        else:
            dic = grupo[grupo['mes'] == 12]
            candidatos = dic.sort_values('fecha').tail(1) if len(dic) > 0 else grupo.sort_values('fecha').tail(1)

        for _, row in candidatos.iterrows():
            meta, ejec, fuente, es_na = _extraer_registro(
                row, hist_escalas, config_patrones=config_patrones,
                extraccion_map=extraccion_map, api_kawak_lookup=api_kawak_lookup)
            if fuente == 'skip' or fuente == 'sin_resultado':
                skipped += 1
                continue
            if es_na:
                conteo_na += 1
            proceso = row.get('Proceso', '')
            registros.append({
                'Id': id_val, 'Indicador': limpiar_html(str(row.get('Indicador', ''))),
                'Proceso': proceso, 'Periodicidad': row.get('Periodicidad', ''),
                'Sentido': row.get('Sentido', ''), 'fecha': row['fecha'],
                'Meta': meta, 'Ejecucion': ejec, 'LLAVE': row['LLAVE'],
                'es_na': es_na,
            })

    return registros, skipped, conteo_na


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("ACTUALIZANDO RESULTADOS CONSOLIDADOS - v7 (Fuentes Consolidadas)")
    print("=" * 65)

    # ── 1. Cargar fuentes (desde Fuentes Consolidadas) ─────────────
    # Requisito: ejecutar primero  python scripts/consolidar_api.py
    print("\n[1] Cargando fuentes de datos (Fuentes Consolidadas)...")
    df_api = cargar_fuente_consolidada()
    print(f"  Consolidado API:  {len(df_api):,} registros")
    df_kawak25 = cargar_kawak_2025()
    print(f"  Kawak 2025:       {len(df_kawak25):,} registros")

    cols_base = ['Id', 'Indicador', 'Proceso', 'Periodicidad', 'Sentido',
                 'resultado', 'meta', 'fecha', 'LLAVE', 'variables', 'series', 'analisis']
    for c in cols_base:
        if c not in df_api.columns:
            df_api[c] = np.nan

    df_fuente_api = (df_api[cols_base].copy()
                       .drop_duplicates('LLAVE', keep='first')
                       .dropna(subset=['LLAVE']))
    print(f"  Fuente unificada: {len(df_fuente_api):,} registros")

    # ── 2. Cargar consolidado existente ───────────────────────────
    print("\n[2] Cargando Resultados Consolidados...")
    df_hist    = pd.read_excel(INPUT_FILE, sheet_name='Consolidado Historico')
    df_sem     = pd.read_excel(INPUT_FILE, sheet_name='Consolidado Semestral')
    df_cierres = pd.read_excel(INPUT_FILE, sheet_name='Consolidado Cierres')
    for df_ in [df_hist, df_sem, df_cierres]:
        df_['Fecha'] = pd.to_datetime(df_['Fecha'])

    # Filtrar fechas fuera de rango (año > AÑO_CIERRE_ACTUAL) solo para cálculos derivados
    n_fuera_rango = (df_hist['Fecha'].dt.year > AÑO_CIERRE_ACTUAL).sum()
    if n_fuera_rango:
        print(f"  [AVISO] {n_fuera_rango} filas con Fecha > {AÑO_CIERRE_ACTUAL} en Histórico "
              f"(se excluyen del cálculo de escalas pero se conservan en el OUTPUT).")
    df_hist_rango = df_hist[df_hist['Fecha'].dt.year <= AÑO_CIERRE_ACTUAL]

    df_hist_rango = df_hist_rango.copy()
    df_hist_rango['Meta_num'] = pd.to_numeric(df_hist_rango['Meta'], errors='coerce')
    hist_escalas = df_hist_rango.groupby('Id')['Meta_num'].median().to_dict()
    signos       = obtener_signos(df_hist, df_sem, df_cierres)
    # Calcular LLAVEs desde Id+Fecha (col LLAVE del archivo es confiable, pero por seguridad
    # también calculamos desde Id+Fecha para no depender de la columna T)
    llave_hist = llaves_de_df(df_hist)
    llave_sem  = llaves_de_df(df_sem)
    print(f"  Histórico: {len(df_hist):,} | Semestral: {len(df_sem):,} | "
          f"Cierres: {len(df_cierres):,}")

    # ── 3. Catálogo Kawak válidos + Metadatos maestros ────────────
    print("\n[3] Cargando catálogo Kawak e indicadores válidos por año...")
    kawak_validos = cargar_kawak_validos()
    if kawak_validos:
        print(f"  Pares (Id, Año) válidos: {len(kawak_validos):,}")
    print("\n[3b] Cargando metadatos maestros...")
    meta_kawak    = cargar_metadatos_kawak()
    meta_cmi      = cargar_metadatos_cmi()
    mapa_procesos = cargar_mapa_procesos()
    print(f"  Kawak: {len(meta_kawak)} IDs | CMI: {len(meta_cmi)} IDs | "
          f"Mapa procesos: {len(mapa_procesos)} subprocesos")

    def _apply_meta(row, field, fallback):
        ids = _id_str(row['Id'])
        v   = (meta_kawak.get(ids, {}).get(field) or
               meta_cmi.get(ids, {}).get(field) or '').strip()
        return v if v and v not in ('nan', 'None') else fallback(row)

    df_fuente_api['Indicador']    = df_fuente_api.apply(
        lambda r: _apply_meta(r, 'nombre',       lambda r: limpiar_html(str(r['Indicador']))), axis=1)
    df_fuente_api['Periodicidad'] = df_fuente_api.apply(
        lambda r: _apply_meta(r, 'periodicidad', lambda r: str(r['Periodicidad'])), axis=1)
    df_fuente_api['Proceso']      = df_fuente_api.apply(
        lambda r: _apply_meta(r, 'proceso',      lambda r: str(r['Proceso'])), axis=1)
    if len(df_kawak25) > 0:
        df_kawak25['Indicador']    = df_kawak25.apply(
            lambda r: _apply_meta(r, 'nombre',       lambda r: limpiar_html(str(r['Indicador']))), axis=1)
        df_kawak25['Periodicidad'] = df_kawak25.apply(
            lambda r: _apply_meta(r, 'periodicidad', lambda r: str(r['Periodicidad'])), axis=1)

    # ── 4. Series / Análisis ──────────────────────────────────────
    print("\n[4] Expandiendo variables, series y análisis...")
    df_variables = expandir_variables(df_api)
    df_series    = expandir_series(df_api)
    df_analisis  = expandir_analisis(df_api)
    print(f"  Variables: {len(df_variables):,} | Series: {len(df_series):,} | Analisis: {len(df_analisis):,}")

    # ── 4b. Lookups de extracción ─────────────────────────────────
    print("\n[4b] Cargando mapa de Extraccion y lookup Consolidado_API_Kawak...")
    extraccion_map   = cargar_extraccion_map()
    api_kawak_lookup = cargar_consolidado_api_kawak_lookup()
    n_dv = sum(1 for v in extraccion_map.values() if v == 'Desglose Variables')
    n_ak = sum(1 for v in extraccion_map.values() if v == 'Consolidado_API_Kawak')
    print(f"  Extraccion: {n_dv} Desglose Variables | {n_ak} Consolidado_API_Kawak | "
          f"{len(extraccion_map)-n_dv-n_ak} sin valor (usa API_Kawak)")

    # ── 5. Catálogo ───────────────────────────────────────────────
    print("\n[5] Construyendo catálogo...")
    df_cat = construir_catalogo(df_api, df_hist,
                                metadatos_kawak=meta_kawak, metadatos_cmi=meta_cmi)
    print(f"  Catálogo: {len(df_cat):,} indicadores")

    # Identificar IDs de tipo "Métrica" desde lmi_reporte.xlsx
    # (columna Tipo == 'Metrica' o nombre Indicador contiene 'metrica')
    ids_metrica = cargar_lmi_reporte()
    if ids_metrica:
        print(f"  Indicadores tipo Metrica: {len(ids_metrica)} IDs -> "
              f"col Tipo_Registro='Metrica'; signos sin cambio")

    # ── 5b. Config_Patrones ───────────────────────────────────────
    print("\n[5b] Cargando Config_Patrones...")
    config_patrones = cargar_config_patrones()
    if config_patrones:
        n_var = sum(1 for c in config_patrones.values() if c['patron'] == 'VARIABLES')
        n_agg = sum(1 for c in config_patrones.values() if c['patron'] in ('AVG', 'SUM'))
        print(f"  {len(config_patrones)} indicadores configurados "
              f"({n_var} VARIABLES, {n_agg} AVG/SUM)")
    else:
        print("  Sin Config_Patrones — se usará heurística. "
              "(Se creará la hoja en el output para configuración futura.)")

    # ── 6. Abrir workbook ─────────────────────────────────────────
    print("\n[6] Copiando base a outputs...")
    shutil.copy(INPUT_FILE, OUTPUT_FILE)
    wb = openpyxl.load_workbook(OUTPUT_FILE)

    # NOTA: Las columnas Año, Mes, Periodo, Cumplimiento, Cumplimiento Real y LLAVE
    # conservan sus fórmulas Excel (no se convierten a valores estáticos).
    # data_loader.py recalcula esas columnas en Python a partir de Meta/Ejecucion/Sentido/Fecha
    # cuando pandas las lee como NaN (openpyxl no evalúa fórmulas al guardar).

    # Asegurar header Tipo_Registro al final de cada hoja (después de la última col con header)
    for nombre_hoja in ('Consolidado Historico', 'Consolidado Semestral', 'Consolidado Cierres'):
        _ensure_tipo_registro_header(wb[nombre_hoja])

    # Purgar filas inválidas/futuras y las que no están en el catálogo Kawak
    print("\n[6b] Purgando filas invalidas/futuras y sin catalogo Kawak...")
    for _nombre_hoja in ('Consolidado Historico', 'Consolidado Semestral', 'Consolidado Cierres'):
        purgar_filas_invalidas(wb[_nombre_hoja], _nombre_hoja,
                               kawak_validos=kawak_validos)

    # Limpiar cierres existentes ANTES de escribir
    print("\n[6c] Limpiando Consolidado Cierres (solo 31/12 por Id+Año)...")
    ws_cierres = wb['Consolidado Cierres']
    limpiar_cierres_existentes(ws_cierres)

    # ── 6d. Reparar Meta vacía en filas existentes ─────────────────
    print("\n[6d] Reparando celdas Meta vacías en filas existentes...")
    for _nombre_hoja in ('Consolidado Historico', 'Consolidado Semestral', 'Consolidado Cierres'):
        reparar_meta_vacia(wb[_nombre_hoja], api_kawak_lookup, _nombre_hoja)

    # ── 7. Histórico ──────────────────────────────────────────────
    print("\n[7] Nuevos registros Historico...")
    regs_hist, skip_hist, na_hist = construir_registros_historico(
        df_fuente_api, llave_hist, hist_escalas,
        config_patrones=config_patrones, mapa_procesos=mapa_procesos,
        kawak_validos=kawak_validos, extraccion_map=extraccion_map,
        api_kawak_lookup=api_kawak_lookup)
    print(f"  Nuevos: {len(regs_hist):,} | N/A: {na_hist:,} | Omitidos: {skip_hist:,}")
    if len(df_kawak25) > 0:
        llaves_usadas = llave_hist | {r['LLAVE'] for r in regs_hist}
        regs_k25, sk25, na_k25 = construir_registros_historico(
            df_kawak25, llaves_usadas, hist_escalas,
            config_patrones=config_patrones, mapa_procesos=mapa_procesos,
            kawak_validos=kawak_validos, extraccion_map=extraccion_map,
            api_kawak_lookup=api_kawak_lookup)
        regs_hist += regs_k25
        print(f"  + Kawak 2025: {len(regs_k25):,} adicionales (N/A: {na_k25}, omitidos: {sk25})")
    regs_hist.sort(key=lambda x: (str(x['Id']), x['fecha']))
    ws_hist = wb['Consolidado Historico']
    if regs_hist:
        ultima = escribir_filas(ws_hist, regs_hist, signos, ids_metrica=ids_metrica)
        print(f"  Ultima fila: {ultima}")
    else:
        print("  Sin filas nuevas.")

    # ── 8. Semestral ──────────────────────────────────────────────
    print("\n[8] Nuevos registros Semestral...")
    regs_sem, skip_sem, na_sem = construir_registros_semestral(
        df_fuente_api, llave_sem, hist_escalas,
        config_patrones=config_patrones, mapa_procesos=mapa_procesos,
        kawak_validos=kawak_validos, extraccion_map=extraccion_map,
        api_kawak_lookup=api_kawak_lookup)
    print(f"  Nuevos: {len(regs_sem):,} | N/A: {na_sem:,} | Omitidos: {skip_sem:,}")
    regs_sem.sort(key=lambda x: (str(x['Id']), x['fecha']))
    ws_sem = wb['Consolidado Semestral']
    if regs_sem:
        ultima = escribir_filas(ws_sem, regs_sem, signos, ids_metrica=ids_metrica)
        print(f"  Ultima fila: {ultima}")
    else:
        print("  Sin filas nuevas.")

    # ── 9. Cierres ────────────────────────────────────────────────
    print("\n[9] Nuevos registros Cierres...")
    regs_cierres, skip_c, na_c = construir_registros_cierres(
        df_fuente_api, hist_escalas,
        config_patrones=config_patrones, mapa_procesos=mapa_procesos,
        kawak_validos=kawak_validos, extraccion_map=extraccion_map,
        api_kawak_lookup=api_kawak_lookup)
    if len(df_kawak25) > 0:
        regs_k25_c, sk25_c, na_k25_c = construir_registros_cierres(
            df_kawak25, hist_escalas,
            config_patrones=config_patrones, mapa_procesos=mapa_procesos,
            kawak_validos=kawak_validos, extraccion_map=extraccion_map,
            api_kawak_lookup=api_kawak_lookup)
        llaves_c = {r['LLAVE'] for r in regs_cierres}
        regs_k25_c = [r for r in regs_k25_c if r['LLAVE'] not in llaves_c]
        regs_cierres += regs_k25_c
        skip_c += sk25_c
        na_c   += na_k25_c

    # Filtrar contra llaves que ya quedaron en el sheet limpio
    llaves_cierres_limpias = set()
    for row in ws_cierres.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        llave_m = make_llave(row[0].value, row[5].value)
        if llave_m:
            llaves_cierres_limpias.add(llave_m)

    regs_cierres_nuevos = [r for r in regs_cierres
                           if r['LLAVE'] not in llaves_cierres_limpias]
    regs_cierres_nuevos.sort(key=lambda x: (str(x['Id']), x['fecha']))

    print(f"  Candidatos: {len(regs_cierres):,} | Ya existentes: "
          f"{len(regs_cierres)-len(regs_cierres_nuevos):,} | "
          f"Nuevos: {len(regs_cierres_nuevos):,} | N/A: {na_c:,} | Omitidos: {skip_c:,}")
    if regs_cierres_nuevos:
        ultima = escribir_filas(ws_cierres, regs_cierres_nuevos, signos, ids_metrica=ids_metrica)
        print(f"  Última fila: {ultima}")
    else:
        print("  Sin filas nuevas.")

    # ── 10. Hojas nuevas ──────────────────────────────────────────
    print("\n[10] Escribiendo hojas nuevas...")
    if len(df_variables) > 0:
        escribir_hoja_nueva(wb, 'Desglose Variables', df_variables)
        print(f"  Desglose Variables:   {len(df_variables):,} filas")
    if len(df_series)   > 0:
        escribir_hoja_nueva(wb, 'Desglose Series',   df_series)
        print(f"  Desglose Series:      {len(df_series):,} filas")
    if len(df_analisis) > 0:
        escribir_hoja_nueva(wb, 'Desglose Analisis', df_analisis)
        print(f"  Desglose Analisis:    {len(df_analisis):,} filas")
    escribir_hoja_nueva(wb, 'Catalogo Indicadores', df_cat)
    print(f"  Catalogo Indicadores: {len(df_cat):,} filas")
    df_base = df_fuente_api[['Id', 'Indicador', 'Proceso', 'Periodicidad',
                              'Sentido', 'fecha', 'resultado', 'meta', 'LLAVE']].copy()
    df_base['fecha'] = df_base['fecha'].dt.date
    escribir_hoja_nueva(wb, 'Base Normalizada', df_base)
    print(f"  Base Normalizada:     {len(df_base):,} filas")

    # Config_Patrones: crear hoja inicial si no existe aún en el output
    if 'Config_Patrones' not in wb.sheetnames:
        df_cfg_inicial = crear_config_patrones_inicial()
        if not df_cfg_inicial.empty:
            escribir_hoja_nueva(wb, 'Config_Patrones', df_cfg_inicial)
            print(f"  Config_Patrones:      {len(df_cfg_inicial):,} filas "
                  f"(NUEVA — revisar simbolos VARIABLES antes del proximo reporte)")
        else:
            print("  Config_Patrones:      no se pudo crear (falta diagnostico_fuente_ejecucion.xlsx)")
    else:
        print("  Config_Patrones:      ya existe en el archivo — no se sobreescribe")

    # ── 11. Deduplicar los tres consolidados ──────────────────────
    print("\n[11] Eliminando duplicados por LLAVE en los consolidados...")
    deduplicar_sheet(wb['Consolidado Historico'], 'Historico')
    deduplicar_sheet(wb['Consolidado Semestral'], 'Semestral')
    deduplicar_sheet(wb['Consolidado Cierres'],   'Cierres')

    # ── 11b. Cierres: solo 1 registro por Id+Año (el más reciente) ──
    print("\n[11b] Cierres: dejando solo el registro más reciente por Id+Año...")
    _dedup_cierres_por_año(wb['Consolidado Cierres'])

    # ── 12. Reescribir fórmulas (CRÍTICO) ─────────────────────────
    # openpyxl NO ajusta las referencias de fórmulas cuando se eliminan filas.
    # Tras las purgas (paso 6b/6c) y deduplicación (paso 11), las fórmulas
    # existentes apuntan a filas incorrectas.  Se reescriben TODAS con el
    # número de fila actual para garantizar consistencia.
    print("\n[12] Reescribiendo fórmulas con referencias correctas...")
    for _nombre_hoja in ('Consolidado Historico', 'Consolidado Semestral', 'Consolidado Cierres'):
        _reescribir_formulas(wb[_nombre_hoja])

    # ── 13. Guardar ───────────────────────────────────────────────
    print(f"\nGuardando: {OUTPUT_FILE}")
    wb.save(OUTPUT_FILE)
    print("[OK] Guardado exitosamente.")

    total_na = na_hist + na_sem + na_c
    print("\n" + "=" * 65)
    print("RESUMEN FINAL:")
    print(f"  Histórico:  +{len(regs_hist):,} filas  ({na_hist:,} N/A)")
    print(f"  Semestral:  +{len(regs_sem):,} filas  ({na_sem:,} N/A)")
    print(f"  Cierres:    +{len(regs_cierres_nuevos):,} filas  ({na_c:,} N/A)")
    print(f"  Total 'No Aplica' marcados: {total_na:,} "
          f"(Ejecucion=vacío, Signo='No Aplica', Cumplimiento='')")
    print(f"  Hojas nuevas: Desglose Variables, Desglose Series, Desglose Analisis,")
    print(f"                Catalogo Indicadores, Base Normalizada")
    print("=" * 65)


if __name__ == '__main__':
    main()