"""
Script para actualizar Resultados Consolidados.xlsx
Versión 5 - Manejo correcto de registros "No Aplica"

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
BASE_PATH   = _ROOT / "data" / "raw"
INPUT_FILE  = BASE_PATH / "Resultados Consolidados.xlsx"
OUTPUT_DIR  = _ROOT / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "Resultados Consolidados.xlsx"

AÑO_CIERRE_ACTUAL = 2025

KW_EJEC = ['real', 'ejecutado', 'recaudado', 'ahorrado', 'consumo', 'generado',
           'actual', 'logrado', 'obtenido', 'reportado', 'hoy']
KW_META = ['planeado', 'presupuestado', 'propuesto', 'programado', 'objetivo',
           'esperado', 'previsto', 'estimado', 'acumulado plan']

SIGNO_NA = 'No Aplica'   # valor a escribir en Ejecucion_Signo cuando no hay dato


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


def determinar_meta_ejec(row_api, hist_meta_escala):
    """
    Determina (meta, ejec, fuente, es_na) para un registro.

    Retorna:
      fuente = 'api_directo' | 'variables' | 'series_sum' | 'series_sum_fallback'
               | 'na_record' | 'skip'
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

def cargar_api(years=(2022, 2023, 2024, 2025)):
    frames = []
    for y in years:
        path = BASE_PATH / "API" / f"{y}.xlsx"
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
        'ID': 'Id', 'nombre': 'Indicador', 'proceso': 'Proceso',
        'frecuencia': 'Periodicidad', 'sentido': 'Sentido',
    })
    df['LLAVE'] = df.apply(lambda r: make_llave(r['Id'], r['fecha']), axis=1)
    return df


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
    meta = {}
    for y in [2021, 2022, 2023, 2024]:
        path = BASE_PATH / "Kawak" / f"{y}.xlsx"
        if not path.exists():
            continue
        df      = pd.read_excel(path)
        id_col  = 'ID' if 'ID' in df.columns else 'Id'
        per_col = ('frecuencia' if 'frecuencia' in df.columns else
                   'Periodicidad' if 'Periodicidad' in df.columns else None)
        for _, row in df.drop_duplicates(id_col).iterrows():
            id_val = row.get(id_col)
            if pd.isna(id_val):
                continue
            ids = _id_str(id_val)
            meta[ids] = {
                'nombre':        limpiar_html(str(row.get('nombre', row.get('Indicador', '')))),
                'clasificacion': limpiar_clasificacion(
                                     str(row.get('clasificacion', row.get('Clasificacion', '')))),
                'proceso':       limpiar_html(str(row.get('proceso', row.get('Proceso', '')))),
                'periodicidad':  str(row.get(per_col, '')) if per_col else '',
                'sentido':       str(row.get('sentido', row.get('Sentido', ''))),
                'tipo_calculo':  '',
            }
    path25 = BASE_PATH / "Kawak" / "2025.xlsx"
    if path25.exists():
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
# CATÁLOGO
# ─────────────────────────────────────────────────────────────────────

def construir_catalogo(df_api, df_hist=None,
                       metadatos_kawak=None, metadatos_cmi=None):
    if metadatos_kawak is None: metadatos_kawak = {}
    if metadatos_cmi   is None: metadatos_cmi   = {}

    user_data = {}
    if OUTPUT_FILE.exists():
        try:
            xl = pd.ExcelFile(OUTPUT_FILE)
            if 'Catalogo Indicadores' in xl.sheet_names:
                df_ex = pd.read_excel(OUTPUT_FILE, sheet_name='Catalogo Indicadores')
                for _, row in df_ex.iterrows():
                    ids = _id_str(row['Id'])
                    user_data[ids] = {
                        'TipoCalculo': row.get('TipoCalculo', ''),
                        'Asociacion':  row.get('Asociacion', ''),
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
        ud           = user_data.get(ids, {})
        tipo_calculo = _clean(ud.get('TipoCalculo')) or _clean(kw.get('tipo_calculo', ''))
        asociacion   = _clean(ud.get('Asociacion', ''))
        rows.append({
            'Id': base['Id'], 'Indicador': nombre, 'Clasificacion': clasificacion,
            'Proceso': proceso, 'Periodicidad': periodicidad, 'Sentido': sentido,
            'Tipo_API': base['Tipo_API'], 'Estado': base['Estado'], 'Fuente': base['Fuente'],
            'TipoCalculo': tipo_calculo, 'Asociacion': asociacion,
            'Formato_Valores': 'Porcentaje',
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
    col_ejec_candidates = ['Ejecución Signo', 'Ejecucion Signo']
    for df, col_ms_c, col_es_c in [
        (df_hist,    ['Meta Signo'], col_ejec_candidates),
        (df_sem,     ['Meta Signo'], col_ejec_candidates),
        (df_cierres, ['Meta Signo'], col_ejec_candidates),
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

def formula_G(r): return f"=YEAR(F{r})"
def formula_H(r): return f'=PROPER(TEXT(F{r},"mmmm"))'
def formula_I(r):
    return (f'=IF(OR(H{r}="Enero",H{r}="Febrero",H{r}="Marzo",'
            f'H{r}="Abril",H{r}="Mayo",H{r}="Junio"),'
            f'G{r}&"-1",'
            f'IF(OR(H{r}="Julio",H{r}="Agosto",H{r}="Septiembre",'
            f'H{r}="Octubre",H{r}="Noviembre",H{r}="Diciembre"),'
            f'G{r}&"-2"))')
def formula_L(r):
    # IFERROR devuelve "" cuando K=vacío (división por cero o con vacío)
    # También devuelve "" cuando J=0 para evitar #DIV/0!
    return (f'=IFERROR(IF(OR(J{r}=0,K{r}=""),"",IF(E{r}="Positivo",'
            f'MIN(MAX(K{r}/J{r},0),1.3),'
            f'MIN(MAX(J{r}/K{r},0),1.3))),"")' )
def formula_M(r):
    return (f'=IFERROR(IF(OR(J{r}=0,K{r}=""),"",IF(E{r}="Positivo",'
            f'MAX(K{r}/J{r},0),'
            f'MAX(J{r}/K{r},0))),"")' )
def formula_R(r):
    return (f'=A{r}&"-"&YEAR(F{r})&"-"'
            f'&IF(LEN(MONTH(F{r}))=1,"0"&MONTH(F{r}),MONTH(F{r}))'
            f'&"-"&IF(LEN(DAY(F{r}))=1,"0"&DAY(F{r}),DAY(F{r}))')


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
    Reconstruye las fórmulas G,H,I,L,M,R en todas las filas restantes.
    """
    filas = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        try:
            llave = make_llave(row[0].value, row[5].value)
        except Exception:
            llave = None
        filas.append({'row_idx': row[0].row, 'llave': llave, 'ejec': row[10].value})

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

    # Reconstruir fórmulas con índices físicos actualizados
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        r = row[0].row
        row[6].value  = formula_G(r)
        row[7].value  = formula_H(r)
        row[8].value  = formula_I(r)
        row[11].value = formula_L(r);  row[11].number_format = '0.00%'
        row[12].value = formula_M(r);  row[12].number_format = '0.00%'
        row[17].value = formula_R(r)

    print(f"  [{nombre}] {len(filas_a_borrar)} duplicados eliminados, "
          f"formulas reconstruidas.")
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

    # Reconstruir fórmulas con índices físicos post-eliminación
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        r = row[0].row
        row[6].value  = formula_G(r)
        row[7].value  = formula_H(r)
        row[8].value  = formula_I(r)
        row[11].value = formula_L(r)
        row[11].number_format = '0.00%'
        row[12].value = formula_M(r)
        row[12].number_format = '0.00%'
        row[17].value = formula_R(r)

    print(f"  limpiar_cierres: {len(filas_a_borrar)} filas eliminadas, "
          f"fórmulas reconstruidas en {len(filas_a_conservar)} filas.")
    return len(filas_a_borrar)


# ─────────────────────────────────────────────────────────────────────
# ESCRITURA DE FILAS
# ─────────────────────────────────────────────────────────────────────

def escribir_filas(ws, filas, signos, start_row=None):
    """
    Escribe filas nuevas con fórmulas correctamente referenciadas.

    Manejo No Aplica:
      - Si fila['es_na'] == True → col K (Ejecucion) = None
        y col O (Ejecucion_Signo) = 'No Aplica'
      - Las fórmulas L y M incluyen OR(K{r}="") → devuelven ""
        automáticamente cuando K está vacío (no muestra 0%).

    Columnas:
      A(1)  Id          B(2)  Indicador   C(3)  Proceso
      D(4)  Periodicidad  E(5) Sentido    F(6)  Fecha
      G(7)  =YEAR(F)    H(8)  =mes        I(9)  =semestre
      J(10) Meta         K(11) Ejecución
      L(12) =cumpl.acot  M(13) =cumpl.libre
      N(14) Meta Signo   O(15) Ejec Signo
      P(16) Dec_Meta     Q(17) Dec_Ejec
      R(18) =llave
    """
    if start_row is None:
        start_row = get_last_data_row(ws) + 1

    r = start_row
    for fila in filas:
        id_str = str(fila.get('Id', ''))
        sg = signos.get(id_str, {
            'meta_signo': '%', 'ejec_signo': '%',
            'dec_meta': 0, 'dec_ejec': 0,
        })

        fecha_val = fila.get('fecha')
        if isinstance(fecha_val, pd.Timestamp):
            fecha_val = fecha_val.to_pydatetime().date()

        meta    = nan2none(fila.get('Meta'))
        ejec    = nan2none(fila.get('Ejecucion'))
        es_na   = fila.get('es_na', False)

        # Si es N/A: Ejecucion = None (celda vacía) y signo = 'N/A'
        if es_na:
            ejec        = None
            ejec_signo  = SIGNO_NA
        else:
            ejec_signo  = sg['ejec_signo']

        # A–F: datos base
        ws.cell(r, 1).value = fila.get('Id')
        ws.cell(r, 2).value = fila.get('Indicador', '')
        ws.cell(r, 3).value = fila.get('Proceso', '')
        ws.cell(r, 4).value = fila.get('Periodicidad', '')
        ws.cell(r, 5).value = fila.get('Sentido', '')
        ws.cell(r, 6).value = fecha_val
        ws.cell(r, 6).number_format = 'YYYY-MM-DD'

        # G, H, I: fórmulas año/mes/semestre
        ws.cell(r, 7).value = formula_G(r)
        ws.cell(r, 8).value = formula_H(r)
        ws.cell(r, 9).value = formula_I(r)

        # J, K: Meta y Ejecución
        ws.cell(r, 10).value = meta
        ws.cell(r, 11).value = ejec   # None cuando es N/A → celda vacía

        # L, M: cumplimiento
        # Cuando K=None (vacío), OR(K{r}="") es True → devuelve ""
        ws.cell(r, 12).value         = formula_L(r)
        ws.cell(r, 12).number_format = '0.00%'
        ws.cell(r, 13).value         = formula_M(r)
        ws.cell(r, 13).number_format = '0.00%'

        # N–Q: signos y decimales
        ws.cell(r, 14).value = sg['meta_signo']
        ws.cell(r, 15).value = ejec_signo    # 'N/A' o signo normal
        ws.cell(r, 16).value = sg['dec_meta']
        ws.cell(r, 17).value = sg['dec_ejec']

        # R: llave compuesta
        ws.cell(r, 18).value = formula_R(r)

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

def _extraer_registro(row, hist_escalas):
    """
    Extrae (meta, ejec, fuente, es_na) para una fila de fuente.
    Kawak2025 nunca tiene N/A (los datos ya están limpios).
    """
    id_val = row.get('Id', row.get('ID'))
    id_num = pd.to_numeric(id_val, errors='coerce')
    hist_meta_escala = hist_escalas.get(id_num) or hist_escalas.get(str(id_val))

    if 'fuente' in row and row.get('fuente') == 'Kawak2025':
        meta = nan2none(row.get('Meta'))
        ejec = nan2none(row.get('resultado'))
        return meta, ejec, 'Kawak2025', False

    meta, ejec, fuente, es_na = determinar_meta_ejec(
        row.to_dict() if hasattr(row, 'to_dict') else row,
        hist_meta_escala
    )
    return meta, ejec, fuente, es_na


def construir_registros_historico(df_fuente, llaves_existentes, hist_escalas):
    registros = []
    skipped   = 0
    conteo_na = 0
    df = df_fuente[~df_fuente['LLAVE'].isin(llaves_existentes)].dropna(subset=['LLAVE'])
    for _, row in df.iterrows():
        meta, ejec, fuente, es_na = _extraer_registro(row, hist_escalas)
        if fuente == 'skip' or fuente == 'sin_resultado':
            skipped += 1
            continue
        if es_na:
            conteo_na += 1
        registros.append({
            'Id': row['Id'], 'Indicador': limpiar_html(str(row.get('Indicador', ''))),
            'Proceso': row.get('Proceso', ''), 'Periodicidad': row.get('Periodicidad', ''),
            'Sentido': row.get('Sentido', ''), 'fecha': row['fecha'],
            'Meta': meta, 'Ejecucion': ejec, 'LLAVE': row['LLAVE'],
            'es_na': es_na,
        })
    return registros, skipped, conteo_na


def construir_registros_semestral(df_fuente, llaves_existentes, hist_escalas):
    df = df_fuente[df_fuente['fecha'].dt.month.isin([6, 12])].copy()
    df = df[df['fecha'] == df['fecha'].apply(
        lambda d: pd.Timestamp(d.year, d.month, ultimo_dia_mes(d.year, d.month)))]
    return construir_registros_historico(df, llaves_existentes, hist_escalas)


def construir_registros_cierres(df_fuente, hist_escalas):
    df = df_fuente.copy()
    df['año'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    registros = []
    skipped   = 0
    conteo_na = 0

    for (id_val, año), grupo in df.groupby(['Id', 'año']):
        if año > AÑO_CIERRE_ACTUAL:
            candidatos = grupo
        else:
            dic = grupo[grupo['mes'] == 12]
            candidatos = dic if len(dic) > 0 else grupo.sort_values('fecha').tail(1)

        for _, row in candidatos.iterrows():
            meta, ejec, fuente, es_na = _extraer_registro(row, hist_escalas)
            if fuente == 'skip' or fuente == 'sin_resultado':
                skipped += 1
                continue
            if es_na:
                conteo_na += 1
            registros.append({
                'Id': id_val, 'Indicador': limpiar_html(str(row.get('Indicador', ''))),
                'Proceso': row.get('Proceso', ''), 'Periodicidad': row.get('Periodicidad', ''),
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
    print("ACTUALIZANDO RESULTADOS CONSOLIDADOS - v5")
    print("=" * 65)

    # ── 1. Cargar fuentes ──────────────────────────────────────────
    print("\n[1] Cargando fuentes de datos...")
    df_api = cargar_api()
    print(f"  API (2022-2025):  {len(df_api):,} registros")
    df_kawak21 = cargar_kawak_old((2021,))
    print(f"  Kawak 2021:       {len(df_kawak21):,} registros")
    df_kawak25 = cargar_kawak_2025()
    print(f"  Kawak 2025:       {len(df_kawak25):,} registros")

    cols_base = ['Id', 'Indicador', 'Proceso', 'Periodicidad', 'Sentido',
                 'resultado', 'meta', 'fecha', 'LLAVE', 'variables', 'series', 'analisis']
    for c in cols_base:
        for df_ in [df_api, df_kawak21]:
            if c not in df_.columns:
                df_[c] = np.nan

    partes = [df_api[cols_base]]
    if len(df_kawak21) > 0:
        partes.append(df_kawak21[cols_base])
    df_fuente_api = (pd.concat(partes, ignore_index=True)
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

    df_hist['Meta_num'] = pd.to_numeric(df_hist['Meta'], errors='coerce')
    hist_escalas = df_hist.groupby('Id')['Meta_num'].median().to_dict()
    signos       = obtener_signos(df_hist, df_sem, df_cierres)
    # Calcular LLAVEs desde Id+Fecha (la columna LLAVE es fórmula sin caché → siempre NaN)
    llave_hist = llaves_de_df(df_hist)
    llave_sem  = llaves_de_df(df_sem)
    print(f"  Histórico: {len(df_hist):,} | Semestral: {len(df_sem):,} | "
          f"Cierres: {len(df_cierres):,}")

    # ── 3. Metadatos maestros ─────────────────────────────────────
    print("\n[3] Cargando metadatos maestros...")
    meta_kawak = cargar_metadatos_kawak()
    meta_cmi   = cargar_metadatos_cmi()
    print(f"  Kawak: {len(meta_kawak)} IDs | CMI: {len(meta_cmi)} IDs")

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
    print("\n[4] Expandiendo series y análisis...")
    df_series   = expandir_series(df_api)
    df_analisis = expandir_analisis(df_api)
    print(f"  Series: {len(df_series):,} | Análisis: {len(df_analisis):,}")

    # ── 5. Catálogo ───────────────────────────────────────────────
    print("\n[5] Construyendo catálogo...")
    df_cat = construir_catalogo(df_api, df_hist,
                                metadatos_kawak=meta_kawak, metadatos_cmi=meta_cmi)
    print(f"  Catálogo: {len(df_cat):,} indicadores")

    # ── 6. Abrir workbook ─────────────────────────────────────────
    print("\n[6] Copiando base a outputs...")
    shutil.copy(INPUT_FILE, OUTPUT_FILE)
    wb = openpyxl.load_workbook(OUTPUT_FILE)

    # Limpiar cierres existentes ANTES de escribir
    print("\n[6b] Limpiando Consolidado Cierres (solo 31/12 por Id+Año)...")
    ws_cierres = wb['Consolidado Cierres']
    limpiar_cierres_existentes(ws_cierres)

    # ── 7. Histórico ──────────────────────────────────────────────
    print("\n[7] Nuevos registros Histórico...")
    regs_hist, skip_hist, na_hist = construir_registros_historico(
        df_fuente_api, llave_hist, hist_escalas)
    print(f"  Nuevos: {len(regs_hist):,} | N/A: {na_hist:,} | Omitidos: {skip_hist:,}")
    if len(df_kawak25) > 0:
        llaves_usadas = llave_hist | {r['LLAVE'] for r in regs_hist}
        regs_k25, sk25, na_k25 = construir_registros_historico(
            df_kawak25, llaves_usadas, hist_escalas)
        regs_hist += regs_k25
        print(f"  + Kawak 2025: {len(regs_k25):,} adicionales (N/A: {na_k25}, omitidos: {sk25})")
    regs_hist.sort(key=lambda x: (str(x['Id']), x['fecha']))
    ws_hist = wb['Consolidado Historico']
    if regs_hist:
        ultima = escribir_filas(ws_hist, regs_hist, signos)
        print(f"  Última fila: {ultima}")
    else:
        print("  Sin filas nuevas.")

    # ── 8. Semestral ──────────────────────────────────────────────
    print("\n[8] Nuevos registros Semestral...")
    regs_sem, skip_sem, na_sem = construir_registros_semestral(
        df_fuente_api, llave_sem, hist_escalas)
    print(f"  Nuevos: {len(regs_sem):,} | N/A: {na_sem:,} | Omitidos: {skip_sem:,}")
    regs_sem.sort(key=lambda x: (str(x['Id']), x['fecha']))
    ws_sem = wb['Consolidado Semestral']
    if regs_sem:
        ultima = escribir_filas(ws_sem, regs_sem, signos)
        print(f"  Última fila: {ultima}")
    else:
        print("  Sin filas nuevas.")

    # ── 9. Cierres ────────────────────────────────────────────────
    print("\n[9] Nuevos registros Cierres...")
    regs_cierres, skip_c, na_c = construir_registros_cierres(df_fuente_api, hist_escalas)
    if len(df_kawak25) > 0:
        regs_k25_c, sk25_c, na_k25_c = construir_registros_cierres(df_kawak25, hist_escalas)
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
        ultima = escribir_filas(ws_cierres, regs_cierres_nuevos, signos)
        print(f"  Última fila: {ultima}")
    else:
        print("  Sin filas nuevas.")

    # ── 10. Hojas nuevas ──────────────────────────────────────────
    print("\n[10] Escribiendo hojas nuevas...")
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

    # ── 11. Deduplicar los tres consolidados ──────────────────────
    print("\n[11] Eliminando duplicados por LLAVE en los consolidados...")
    deduplicar_sheet(wb['Consolidado Historico'], 'Historico')
    deduplicar_sheet(wb['Consolidado Semestral'], 'Semestral')
    deduplicar_sheet(wb['Consolidado Cierres'],   'Cierres')

    # ── 12. Guardar ───────────────────────────────────────────────
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
    print(f"  Hojas nuevas: Desglose Series, Desglose Analisis,")
    print(f"                Catalogo Indicadores, Base Normalizada")
    print("=" * 65)


if __name__ == '__main__':
    main()