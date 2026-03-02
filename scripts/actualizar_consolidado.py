#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
actualizar_consolidado.py
=========================
Actualiza periódicamente las hojas de 'Resultados Consolidados.xlsx'
a partir de las fuentes oficiales:

  - lmi_reporte.xlsx          : maestro de indicadores (atributos fijos)
  - indicadores_kawak.xlsx    : valores de ejecución / meta por período
  - Indicadores por CMI.xlsx  : línea estratégica y flag PDI

Hojas actualizadas:
  - Consolidado Historico   (una fila por indicador × período reportado)
  - Consolidado Semestral   (acumulado/promedio al corte de jun/dic)
  - Consolidado Cierres     (acumulado/promedio al cierre anual diciembre)
  - Config_Indicadores      (hoja de configuración, creada si no existe)

Uso:
  python scripts/actualizar_consolidado.py
"""

import sys, io, ast, html, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import numpy as np

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent

# Entradas: archivos fuente oficiales (solo lectura)
DATA_INPUT  = BASE_DIR / "data" / "raw"
RUTA_LMI    = DATA_INPUT / "lmi_reporte.xlsx"
RUTA_KAWAK  = DATA_INPUT / "indicadores_kawak.xlsx"
RUTA_CMI    = DATA_INPUT / "Indicadores por CMI.xlsx"

# Salida: archivo consolidado actualizado (lectura + escritura)
DATA_OUTPUT = BASE_DIR / "data" / "output"
RUTA_CONSOL = DATA_OUTPUT / "Resultados Consolidados.xlsx"

# Migración automática: si el archivo de salida aún está en raw/, lo mueve a output/
_CONSOL_RAW = DATA_INPUT / "Resultados Consolidados.xlsx"


def _inicializar_output():
    """Crea data/output/ y migra Resultados Consolidados.xlsx desde raw/ si es necesario."""
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
    if not RUTA_CONSOL.exists() and _CONSOL_RAW.exists():
        shutil.copy2(str(_CONSOL_RAW), str(RUTA_CONSOL))
        print(f"    INFO: Resultados Consolidados.xlsx copiado de data/raw/ → data/output/")
        print(f"    Puedes eliminar la copia de data/raw/ cuando lo consideres.")

# ── Tablas de referencia ───────────────────────────────────────────────────────
MESES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
         7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

# Normalización de Líneas Estratégicas (typos entre fuentes)
LINEA_NORM = {
    "Trasformación Organizacional" : "Transformación_Organizacional",
    "Transformación Organizacional": "Transformación_Organizacional",
    "Calidad"                      : "Calidad",
    "Experiencia"                  : "Experiencia",
    "Sostenibilidad"               : "Sostenibilidad",
    "Expansión"                    : "Expansión",
    "Educación para toda la vida"  : "Educación_para_toda_la_vida",
}

# Columnas destino para cada hoja (en orden exacto)
COLS_HISTORICO = [
    "Id","Indicador","Proceso","Periodicidad","Sentido","Fecha",
    "Meta","Ejecución","Cumplimiento","Cumplimiento Real",
    "Meta s","Ejecución s","Año","Mes","Semestre",
    "Decimales_Meta","Decimales_Ejecucion","PDI","linea","LLAVE","dd",
]
COLS_SEMESTRAL = [
    "Id","Indicador","Proceso","Periodicidad","Sentido","Fecha",
    "Año","Mes","Periodo","Meta","Ejecución",
    "Cumplimiento","Cumplimiento Real","Meta s","Ejecución s",
    "LLAVE","Decimales_Meta","Decimales_Ejecucion",
]
COLS_CIERRES = [
    "Id","Indicador","Clasificación","Proceso","Periodicidad","Sentido","Fecha",
    "Año","Mes","Periodo","Meta","Ejecución",
    "Cumplimiento","Cumplimiento Real","Meta s","Ejecución s",
    "Llave","Decimales","DecimalesEje",
]
COLS_CONFIG = [
    "Id","Indicador","Clasificación","Proceso",
    "Signo_Meta","Decimales_Meta","Signo_Ejec","Decimales_Ejec",
    "Tipo_Agregacion","Tope",
]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def id_a_str(x) -> str:
    """Convierte un Id (posiblemente float) a string limpio sin '.0'."""
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except (TypeError, ValueError):
        pass
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x).strip()


def parse_campos_adicionales(s) -> dict:
    """
    Parsea el campo 'campos_adicionales' de kawak.
    Es una lista Python con comillas simples: [{'campo': ..., 'respuesta': ...}, ...]
    Retorna dict {campo: respuesta} o {} si falla.
    """
    if not s or pd.isna(s):
        return {}
    try:
        lista = ast.literal_eval(str(s))
        return {item.get("campo", ""): item.get("respuesta") for item in lista if isinstance(item, dict)}
    except Exception:
        return {}


def calc_cumplimiento_real(meta, ejec, sentido: str) -> float:
    """
    Calcula Cumplimiento Real según sentido del indicador.
    Retorna 0.0 si meta es 0 o NaN, o si la división no es posible.
    """
    try:
        m = float(meta)
        e = float(ejec)
        if pd.isna(m) or m == 0:
            return 0.0
        if pd.isna(e):
            return 0.0
        if str(sentido).strip().lower() == "negativo":
            return m / e
        return e / m
    except Exception:
        return 0.0


def calc_cumplimiento(raw: float, tope: float = 1.30) -> float:
    """Aplica cota inferior (0) y superior (tope). Sin datos negativos."""
    try:
        return max(0.0, min(float(raw), float(tope)))
    except Exception:
        return 0.0


def extraer_signo_y_decimales(valor_s) -> tuple:
    """
    Extrae el signo/unidad y el número de decimales de un valor formateado como string.
    Retorna (signo: str, decimales: int).

    Ejemplos:
      "85.0%"    → ("%", 1)      "1,200"    → ("ENT", 0)
      "$1,200.5" → ("$", 1)     "5 Días"   → ("Días", 0)
      ""         → ("", 0)
    """
    s = str(valor_s).strip() if valor_s is not None else ""
    if not s or s.lower() in ("nan", "none", "-"):
        return ("", 0)

    # % al final
    if s.endswith("%"):
        num = s[:-1].replace(",", "").strip()
        dec = len(num.split(".")[-1]) if "." in num else 0
        return ("%", dec)

    # $ al inicio
    if s.startswith("$"):
        num = s[1:].replace(",", "").strip()
        dec = len(num.split(".")[-1]) if "." in num else 0
        return ("$", dec)

    # Unidades al final (con espacio)
    _UNITS = [("M³","M3"),("M3","M3"),("Veces","Veces"),("veces","Veces"),
              ("Días","Días"),("días","Días"),("Kg","Kg"),("kg","Kg")]
    for patron, canonical in _UNITS:
        if s.endswith(f" {patron}") or s == patron:
            num = s[: -len(patron)].replace(",", "").strip()
            dec = len(num.split(".")[-1]) if "." in num else 0
            return (canonical, dec)

    # Número puro
    num = s.replace(",", "").strip()
    try:
        float(num)
        if "." in num:
            return ("DEC", len(num.split(".")[-1]))
        return ("ENT", 0)
    except ValueError:
        return ("", 0)


def extraer_formatos_de_historico(df_hist: pd.DataFrame) -> dict:
    """
    Para cada Id, devuelve el signo/unidad y decimales más frecuentes
    en las columnas 'Meta s' y 'Ejecución s' del histórico existente.

    Retorna dict {id_str: {"Signo_Meta":str, "Decimales_Meta":int,
                           "Signo_Ejec":str, "Decimales_Ejec":int}}
    """
    from collections import Counter
    resultado = {}
    if df_hist.empty:
        return resultado

    df = df_hist.copy()
    df["Id"] = df["Id"].apply(id_a_str)

    for id_str, grupo in df.groupby("Id"):
        info = {}
        for col_s, key_signo, key_dec in [
            ("Meta s",     "Signo_Meta",  "Decimales_Meta"),
            ("Ejecución s","Signo_Ejec",  "Decimales_Ejec"),
        ]:
            vals = grupo[col_s].dropna() if col_s in grupo.columns else pd.Series(dtype=str)
            vals = vals[vals.astype(str).str.strip() != ""]
            if vals.empty:
                info[key_signo] = ""
                info[key_dec]   = 0
            else:
                pares   = [extraer_signo_y_decimales(v) for v in vals]
                signos  = Counter(p[0] for p in pares)
                signo   = signos.most_common(1)[0][0]
                decs    = Counter(p[1] for p in pares if p[0] == signo)
                info[key_signo] = signo
                info[key_dec]   = decs.most_common(1)[0][0] if decs else 0
        resultado[id_str] = info
    return resultado


def formatear_con_signo(valor, signo: str, decimales: int) -> str:
    """
    Formatea un valor numérico usando el signo/unidad y decimales de la Config.
    Retorna "" si signo está vacío o si el valor no es numérico.
    """
    signo = str(signo).strip() if signo else ""
    if not signo:
        return ""
    try:
        v = float(valor)
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        return ""

    d = int(decimales)
    if signo == "%":
        return f"{round(v, d)}%"
    elif signo == "ENT":
        return f"{int(round(v))}"
    elif signo == "$":
        return f"${v:,.{d}f}"
    elif signo == "Días":
        return f"{round(v, d)} Días"
    elif signo == "Kg":
        return f"{round(v, d)} Kg"
    elif signo == "M3":
        return f"{round(v, d)} M³"
    elif signo == "Veces":
        return f"{round(v, d)} Veces"
    else:  # DEC u otro
        return f"{round(v, d)}"


def mes_nombre(n: int) -> str:
    return MESES.get(int(n), "")


def semestre_str(fecha) -> str:
    """Retorna 'YYYY-1' o 'YYYY-2' según el mes de la fecha."""
    ts = pd.Timestamp(fecha)
    s = 1 if ts.month <= 6 else 2
    return f"{ts.year}-{s}"


def fecha_fin_semestre(anio: int, semestre: int) -> date:
    """Retorna June 30 (sem=1) o December 31 (sem=2)."""
    if semestre == 1:
        return date(anio, 6, 30)
    return date(anio, 12, 31)


def ultimo_dia_mes(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE FUENTES
# ══════════════════════════════════════════════════════════════════════════════

def cargar_lmi() -> pd.DataFrame:
    """
    Carga lmi_reporte.xlsx (maestro de indicadores).
    Retorna un DataFrame con un registro por indicador único (Revisar=1 equivalente),
    deduplicado por Id tomando la primera aparición.
    Incluye Tipo_Calculo auto-detectado para la Config.
    """
    print(f"    Leyendo {RUTA_LMI.name}...")
    df = pd.read_excel(RUTA_LMI, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    # Columnas requeridas
    keep = ["Id", "Indicador", "Clasificación", "Proceso", "Tipo",
            "Periodicidad", "Sentido"]
    # Columna opcional para detectar tipo de agregación
    tipo_calc_col = next((c for c in df.columns if "Tipo de calculo" in c), None)
    if tipo_calc_col:
        keep.append(tipo_calc_col)

    df = df[[c for c in keep if c in df.columns]].copy()
    df["Id"] = df["Id"].apply(id_a_str)
    df = df[df["Id"] != ""].copy()

    # Deduplicar por Id (lmi tiene múltiples filas por indicador: series)
    # Conservar la primera fila de cada Id (encabezado del indicador)
    df = df.drop_duplicates(subset=["Id"], keep="first").reset_index(drop=True)

    # Crear columna Tipo_Calculo normalizada
    if tipo_calc_col:
        def _tipo_agg(row):
            tc = str(row.get(tipo_calc_col, "")).lower()
            tipo = str(row.get("Tipo", "")).lower()
            if "sumar" in tc:
                return "SUM"
            if "promediar" in tc:
                return "AVG"
            if tipo == "metrica":
                return "LAST"
            return "AVG"
        df["Tipo_Calculo"] = df.apply(_tipo_agg, axis=1)
        df = df.drop(columns=[tipo_calc_col])
    else:
        df["Tipo_Calculo"] = "AVG"

    print(f"    LMI: {len(df)} indicadores únicos")
    return df


def cargar_kawak() -> pd.DataFrame:
    """
    Carga indicadores_kawak.xlsx.
    Extrae la Línea Estratégica de campos_adicionales.
    Decodifica clasificacion (HTML entities).
    """
    print(f"    Leyendo {RUTA_KAWAK.name}...")
    df = pd.read_excel(RUTA_KAWAK, engine="openpyxl", keep_default_na=False, na_values=[""])
    df.columns = [str(c).strip() for c in df.columns]

    # Columna Id
    df["Id"] = df["ID"].apply(id_a_str)

    # Fecha_corte → datetime
    df["Fecha"] = pd.to_datetime(df["fecha_corte"], errors="coerce")
    df = df.dropna(subset=["Fecha"]).copy()

    # Extraer línea estratégica del JSON
    def _linea(s):
        campos = parse_campos_adicionales(s)
        linea_raw = campos.get("Línea Estratégica") or campos.get("Linea Estrategica") or ""
        if not linea_raw:
            return ""
        return LINEA_NORM.get(str(linea_raw).strip(), str(linea_raw).strip())

    df["linea_kawak"] = df["campos_adicionales"].apply(_linea)

    # Decodificar clasificacion HTML
    if "clasificacion" in df.columns:
        df["clasificacion"] = df["clasificacion"].apply(
            lambda x: html.unescape(str(x)) if pd.notna(x) and x != "" else x
        )

    # Seleccionar columnas de interés
    cols_out = ["Id", "Fecha", "resultado", "meta", "frecuencia", "linea_kawak"]
    df = df[[c for c in cols_out if c in df.columns]].copy()

    print(f"    Kawak: {len(df)} registros "
          f"(fecha_corte: {df['Fecha'].min().date()} → {df['Fecha'].max().date()})")
    return df


def cargar_cmi() -> pd.DataFrame:
    """
    Carga Indicadores por CMI.xlsx (hoja Worksheet).
    Extrae Id, Linea, PDI (flag 'Indicadores Plan estrategico').
    """
    print(f"    Leyendo {RUTA_CMI.name}...")
    df = pd.read_excel(RUTA_CMI, sheet_name="Worksheet", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    df["Id"] = df["Id"].apply(id_a_str)
    df = df[df["Id"] != ""].copy()

    # Flag PDI
    pdi_col = next((c for c in df.columns if "Plan estrategico" in c or "plan estrategico" in c.lower()), None)
    if pdi_col:
        df["PDI"] = pd.to_numeric(df[pdi_col], errors="coerce").fillna(0).astype(int)
    else:
        df["PDI"] = 0

    # Línea estratégica normalizada
    if "Linea" in df.columns:
        df["linea_cmi"] = df["Linea"].apply(
            lambda x: LINEA_NORM.get(str(x).strip(), str(x).strip()) if pd.notna(x) and str(x).strip() else ""
        )
    else:
        df["linea_cmi"] = ""

    df = df[["Id", "linea_cmi", "PDI"]].drop_duplicates(subset=["Id"], keep="first")
    print(f"    CMI: {len(df)} indicadores  |  PDI marcados: {df['PDI'].sum()}")
    return df


def cargar_hoja_consolidado(nombre_hoja: str) -> pd.DataFrame:
    """Lee una hoja de Resultados Consolidados. Retorna DF vacío si no existe."""
    try:
        df = pd.read_excel(RUTA_CONSOL, sheet_name=nombre_hoja, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()


def cargar_config() -> pd.DataFrame:
    """Lee Config_Indicadores si existe. Retorna DF vacío si no."""
    return cargar_hoja_consolidado("Config_Indicadores")


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def crear_config_base(df_lmi: pd.DataFrame, df_config_actual: pd.DataFrame,
                      df_hist_actual: pd.DataFrame = None) -> pd.DataFrame:
    """
    Construye Config_Indicadores.
    - Signo_Meta / Decimales_Meta / Signo_Ejec / Decimales_Ejec: extraídos del
      histórico existente (columnas Meta s / Ejecución s). Vacío si no hay historial.
    - Tipo_Agregacion: auto-detectado desde lmi_reporte. Usuario puede editar.
    - Tope: 1.30 por defecto. Cambiar a 1.00 para indicadores con tope 100%.
    """
    base = df_lmi[["Id","Indicador","Clasificación","Proceso","Tipo_Calculo"]].copy()
    base = base.rename(columns={"Tipo_Calculo": "Tipo_Agregacion"})
    base["Signo_Meta"]     = ""
    base["Decimales_Meta"] = 0
    base["Signo_Ejec"]     = ""
    base["Decimales_Ejec"] = 0
    base["Tope"]           = 1.30

    # Extraer formatos del histórico actual
    formatos = extraer_formatos_de_historico(df_hist_actual) if df_hist_actual is not None else {}
    if formatos:
        for campo in ("Signo_Meta","Decimales_Meta","Signo_Ejec","Decimales_Ejec"):
            base[campo] = base["Id"].apply(lambda i: formatos.get(i, {}).get(campo, "" if "Signo" in campo else 0))

    if not df_config_actual.empty and "Id" in df_config_actual.columns:
        df_config_actual = df_config_actual.copy()
        df_config_actual["Id"] = df_config_actual["Id"].apply(id_a_str)

        # Añadir columnas nuevas si la config vieja no las tiene, poblándolas desde histórico
        for campo in ("Signo_Meta","Decimales_Meta","Signo_Ejec","Decimales_Ejec"):
            if campo not in df_config_actual.columns:
                df_config_actual[campo] = df_config_actual["Id"].apply(
                    lambda i: formatos.get(i, {}).get(campo, "" if "Signo" in campo else 0)
                )
            else:
                # Rellenar vacíos con lo extraído del histórico
                mask_vacio = df_config_actual[campo].isna() | (df_config_actual[campo].astype(str).str.strip() == "")
                df_config_actual.loc[mask_vacio, campo] = df_config_actual.loc[mask_vacio, "Id"].apply(
                    lambda i: formatos.get(i, {}).get(campo, "" if "Signo" in campo else 0)
                )

        ya_config = set(df_config_actual["Id"].tolist())
        nuevos = base[~base["Id"].isin(ya_config)].copy()
        config_final = pd.concat([df_config_actual, nuevos], ignore_index=True)
    else:
        config_final = base.copy()

    # Garantizar que todas las columnas existen
    defaults = {"Signo_Meta":"","Decimales_Meta":0,"Signo_Ejec":"","Decimales_Ejec":0,
                "Tipo_Agregacion":"AVG","Tope":1.30}
    for col in COLS_CONFIG:
        if col not in config_final.columns:
            config_final[col] = defaults.get(col, "")

    config_final["Id"] = config_final["Id"].apply(id_a_str)
    config_final = config_final[COLS_CONFIG].drop_duplicates(subset=["Id"], keep="first")
    return config_final.reset_index(drop=True)


def config_para_id(df_config: pd.DataFrame, id_str: str) -> dict:
    """Retorna dict con Signo_Meta, Decimales_Meta, Signo_Ejec, Decimales_Ejec,
    Tipo_Agregacion y Tope para un Id dado."""
    _DEF = {"Signo_Meta":"","Decimales_Meta":0,"Signo_Ejec":"","Decimales_Ejec":0,
            "Tipo_Agregacion":"AVG","Tope":1.30}
    fila = df_config[df_config["Id"] == id_str]
    if fila.empty:
        return _DEF.copy()
    row = fila.iloc[0]
    return {
        "Signo_Meta"      : str(row.get("Signo_Meta",  "") or ""),
        "Decimales_Meta"  : int(row.get("Decimales_Meta", 0) or 0),
        "Signo_Ejec"      : str(row.get("Signo_Ejec",  "") or ""),
        "Decimales_Ejec"  : int(row.get("Decimales_Ejec", 0) or 0),
        "Tipo_Agregacion" : str(row.get("Tipo_Agregacion","AVG") or "AVG"),
        "Tope"            : float(row.get("Tope", 1.30) or 1.30),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DE HISTORICO
# ══════════════════════════════════════════════════════════════════════════════

def construir_historico(df_kawak: pd.DataFrame,
                        df_lmi:   pd.DataFrame,
                        df_cmi:   pd.DataFrame,
                        df_config: pd.DataFrame) -> pd.DataFrame:
    """
    Construye las filas nuevas para Consolidado Historico a partir de kawak.
    Cada fila = un indicador × un período (fecha_corte).
    """
    # Merge kawak ← lmi
    df = df_kawak.merge(df_lmi, on="Id", how="left")
    # Merge ← cmi
    df = df.merge(df_cmi, on="Id", how="left")

    # Línea: preferir kawak, fallback cmi
    df["linea"] = df["linea_kawak"].where(
        df["linea_kawak"].str.strip() != "", df["linea_cmi"]
    )
    df["linea"] = df["linea"].fillna("")

    # PDI
    df["PDI"] = df["PDI"].fillna(0).astype(int)

    rows = []
    for _, r in df.iterrows():
        id_str = r["Id"]
        fecha  = r["Fecha"]
        meta   = r.get("meta")
        ejec   = r.get("resultado")

        # Omitir si ambos son NaN
        if pd.isna(meta) and pd.isna(ejec):
            continue

        cfg = config_para_id(df_config, id_str)
        unidad   = cfg["Unidad"]
        tope     = cfg["Tope"]
        dec_meta = DECIMALES_POR_UNIDAD.get(unidad, 2)
        dec_eje  = DECIMALES_POR_UNIDAD.get(unidad, 2)

        sentido  = str(r.get("Sentido", "Positivo") or "Positivo").strip()
        cum_real = calc_cumplimiento_real(meta, ejec, sentido)
        cumplim  = calc_cumplimiento(cum_real, tope)

        ts = pd.Timestamp(fecha)
        sem_num = 1 if ts.month <= 6 else 2
        llave = f"{id_str}-{ts.strftime('%Y-%m-%d')}"

        rows.append({
            "Id"               : id_str,
            "Indicador"        : r.get("Indicador", ""),
            "Proceso"          : r.get("Proceso", ""),
            "Periodicidad"     : r.get("Periodicidad", r.get("frecuencia", "")),
            "Sentido"          : sentido,
            "Fecha"            : ts,
            "Meta"             : meta,
            "Ejecución"        : ejec,
            "Cumplimiento"     : cumplim,
            "Cumplimiento Real": cum_real,
            "Meta s"           : formatear_s(meta, unidad, dec_meta),
            "Ejecución s"      : formatear_s(ejec, unidad, dec_eje),
            "Año"              : ts.year,
            "Mes"              : mes_nombre(ts.month),
            "Semestre"         : f"{ts.year}-{sem_num}",
            "Decimales_Meta"   : dec_meta,
            "Decimales_Ejecucion": dec_eje,
            "PDI"              : r.get("PDI", 0),
            "linea"            : r.get("linea", ""),
            "LLAVE"            : llave,
            "dd"               : float(ts.day),
        })

    return pd.DataFrame(rows, columns=COLS_HISTORICO)


# ══════════════════════════════════════════════════════════════════════════════
# UPSERT GENÉRICO
# ══════════════════════════════════════════════════════════════════════════════

def upsert(df_existente: pd.DataFrame, df_nuevo: pd.DataFrame, key: str) -> pd.DataFrame:
    """
    Combina existente + nuevo, conservando los nuevos cuando hay conflicto de key.
    Ordena por Id + Fecha.
    """
    if df_existente.empty:
        return df_nuevo.reset_index(drop=True)
    if df_nuevo.empty:
        return df_existente.reset_index(drop=True)

    # Normalizar clave en existente
    if key not in df_existente.columns:
        df_existente[key] = ""

    combined = pd.concat([df_existente, df_nuevo], ignore_index=True)
    combined = combined.drop_duplicates(subset=[key], keep="last")

    # Ordenar
    sort_cols = ["Id", "Fecha"] if "Fecha" in combined.columns else ["Id"]
    try:
        combined = combined.sort_values(sort_cols).reset_index(drop=True)
    except Exception:
        combined = combined.reset_index(drop=True)

    return combined


# ══════════════════════════════════════════════════════════════════════════════
# CÁLCULO SEMESTRAL
# ══════════════════════════════════════════════════════════════════════════════

def calcular_semestral(df_hist: pd.DataFrame, df_config: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega Consolidado Historico a nivel semestral (corte jun/dic).
    Una fila por Id × Semestre.
    """
    if df_hist.empty:
        return pd.DataFrame(columns=COLS_SEMESTRAL)

    df = df_hist.copy()
    df["Fecha"]     = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Meta"]      = pd.to_numeric(df["Meta"], errors="coerce")
    df["Ejecución"] = pd.to_numeric(df["Ejecución"], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    df["Id"] = df["Id"].apply(id_a_str)

    rows = []
    for (id_str, sem), grupo in df.groupby(["Id", "Semestre"], sort=False):
        grupo = grupo.sort_values("Fecha")

        cfg = config_para_id(df_config, id_str)
        tipo_agg = cfg["Tipo_Agregacion"]
        unidad   = cfg["Unidad"]
        tope     = cfg["Tope"]

        meta_vals = grupo["Meta"].dropna()
        ejec_vals = grupo["Ejecución"].dropna()

        if tipo_agg == "SUM":
            meta_agg = meta_vals.sum() if not meta_vals.empty else np.nan
            ejec_agg = ejec_vals.sum() if not ejec_vals.empty else np.nan
        elif tipo_agg == "LAST":
            meta_agg = grupo["Meta"].iloc[-1]
            ejec_agg = grupo["Ejecución"].iloc[-1]
        else:  # AVG (default)
            meta_agg = meta_vals.mean() if not meta_vals.empty else np.nan
            ejec_agg = ejec_vals.mean() if not ejec_vals.empty else np.nan

        # Fecha semestral y Periodo
        try:
            anio, s_num = int(sem.split("-")[0]), int(sem.split("-")[1])
        except Exception:
            continue
        fecha_sem = fecha_fin_semestre(anio, s_num)
        ts_sem    = pd.Timestamp(fecha_sem)
        llave     = f"{id_str}-{ts_sem.strftime('%Y-%m-%d')}"

        sentido  = str(grupo["Sentido"].iloc[-1] or "Positivo").strip()
        cum_real = calc_cumplimiento_real(meta_agg, ejec_agg, sentido)
        cumplim  = calc_cumplimiento(cum_real, tope)

        dec_meta = DECIMALES_POR_UNIDAD.get(unidad, 2)
        dec_eje  = DECIMALES_POR_UNIDAD.get(unidad, 2)

        rows.append({
            "Id"               : id_str,
            "Indicador"        : grupo["Indicador"].iloc[-1],
            "Proceso"          : grupo["Proceso"].iloc[-1],
            "Periodicidad"     : grupo["Periodicidad"].iloc[-1],
            "Sentido"          : sentido,
            "Fecha"            : ts_sem,
            "Año"              : anio,
            "Mes"              : mes_nombre(ts_sem.month),
            "Periodo"          : sem,
            "Meta"             : meta_agg,
            "Ejecución"        : ejec_agg,
            "Cumplimiento"     : cumplim,
            "Cumplimiento Real": cum_real,
            "Meta s"           : formatear_s(meta_agg, unidad, dec_meta),
            "Ejecución s"      : formatear_s(ejec_agg, unidad, dec_eje),
            "LLAVE"            : llave,
            "Decimales_Meta"   : dec_meta,
            "Decimales_Ejecucion": dec_eje,
        })

    return pd.DataFrame(rows, columns=COLS_SEMESTRAL)


# ══════════════════════════════════════════════════════════════════════════════
# CÁLCULO CIERRES
# ══════════════════════════════════════════════════════════════════════════════

def calcular_cierres(df_hist: pd.DataFrame, df_config: pd.DataFrame,
                     df_lmi: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega Consolidado Historico a nivel anual (cierre diciembre).
    Una fila por Id × Año.
    """
    if df_hist.empty:
        return pd.DataFrame(columns=COLS_CIERRES)

    df = df_hist.copy()
    df["Fecha"]     = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Meta"]      = pd.to_numeric(df["Meta"], errors="coerce")
    df["Ejecución"] = pd.to_numeric(df["Ejecución"], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    df["Id"] = df["Id"].apply(id_a_str)
    df["Año"] = df["Fecha"].dt.year

    # Mapa Clasificación desde lmi
    clas_map = dict(zip(df_lmi["Id"], df_lmi.get("Clasificación", pd.Series(dtype=str))))

    rows = []
    for (id_str, anio), grupo in df.groupby(["Id", "Año"], sort=False):
        grupo = grupo.sort_values("Fecha")

        cfg = config_para_id(df_config, id_str)
        tipo_agg = cfg["Tipo_Agregacion"]
        unidad   = cfg["Unidad"]
        tope     = cfg["Tope"]

        meta_vals = grupo["Meta"].dropna()
        ejec_vals = grupo["Ejecución"].dropna()

        if tipo_agg == "SUM":
            meta_agg = meta_vals.sum() if not meta_vals.empty else np.nan
            ejec_agg = ejec_vals.sum() if not ejec_vals.empty else np.nan
        elif tipo_agg == "LAST":
            meta_agg = grupo["Meta"].iloc[-1]
            ejec_agg = grupo["Ejecución"].iloc[-1]
        else:  # AVG
            meta_agg = meta_vals.mean() if not meta_vals.empty else np.nan
            ejec_agg = ejec_vals.mean() if not ejec_vals.empty else np.nan

        fecha_cierre = date(int(anio), 12, 31)
        ts_cierre    = pd.Timestamp(fecha_cierre)
        llave        = f"{id_str}-{anio}-12-31"

        sentido  = str(grupo["Sentido"].iloc[-1] or "Positivo").strip()
        cum_real = calc_cumplimiento_real(meta_agg, ejec_agg, sentido)
        cumplim  = calc_cumplimiento(cum_real, tope)

        dec_meta = DECIMALES_POR_UNIDAD.get(unidad, 2)
        dec_eje  = DECIMALES_POR_UNIDAD.get(unidad, 2)

        rows.append({
            "Id"               : id_str,
            "Indicador"        : grupo["Indicador"].iloc[-1],
            "Clasificación"    : clas_map.get(id_str, ""),
            "Proceso"          : grupo["Proceso"].iloc[-1],
            "Periodicidad"     : grupo["Periodicidad"].iloc[-1],
            "Sentido"          : sentido,
            "Fecha"            : ts_cierre,
            "Año"              : str(anio),           # dtype object en la hoja original
            "Mes"              : "Diciembre",
            "Periodo"          : f"{anio}-2",
            "Meta"             : meta_agg,
            "Ejecución"        : ejec_agg,
            "Cumplimiento"     : cumplim,
            "Cumplimiento Real": cum_real,
            "Meta s"           : formatear_s(meta_agg, unidad, dec_meta),
            "Ejecución s"      : formatear_s(ejec_agg, unidad, dec_eje),
            "Llave"            : llave,
            "Decimales"        : dec_meta,
            "DecimalesEje"     : dec_eje,
        })

    return pd.DataFrame(rows, columns=COLS_CIERRES)


# ══════════════════════════════════════════════════════════════════════════════
# ESCRITURA EN EXCEL
# ══════════════════════════════════════════════════════════════════════════════

def escribir_excel(df_hist: pd.DataFrame, df_sem: pd.DataFrame,
                   df_cie: pd.DataFrame, df_config: pd.DataFrame) -> None:
    """
    Escribe las cuatro hojas actualizadas en Resultados Consolidados.xlsx.
    Preserva todas las demás hojas intactas (mode='a', if_sheet_exists='replace').
    """
    print(f"    Guardando en {RUTA_CONSOL.name}...")
    with pd.ExcelWriter(
        str(RUTA_CONSOL),
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace",
    ) as writer:
        df_hist.to_excel(writer,   sheet_name="Consolidado Historico",  index=False)
        df_sem.to_excel(writer,    sheet_name="Consolidado Semestral",   index=False)
        df_cie.to_excel(writer,    sheet_name="Consolidado Cierres",     index=False)
        df_config.to_excel(writer, sheet_name="Config_Indicadores",      index=False)

    print("    OK -> archivo actualizado.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    sep = "=" * 62
    print(sep)
    print("  actualizar_consolidado.py")
    print(sep)

    # ── 0. Inicializar carpeta de salida ──────────────────────────────────────
    _inicializar_output()
    print(f"\n    Entradas : {DATA_INPUT}")
    print(f"    Salida   : {DATA_OUTPUT}")

    # ── 1. Cargar fuentes ─────────────────────────────────────────────────────
    print("\n[1] Cargando fuentes...")
    for ruta in (RUTA_LMI, RUTA_KAWAK, RUTA_CMI):
        if not ruta.exists():
            sys.exit(f"    ERROR: No se encontró {ruta}")
    if not RUTA_CONSOL.exists():
        sys.exit(f"    ERROR: No se encontró {RUTA_CONSOL}\n"
                 f"    Coloca el archivo en data/output/ o en data/raw/ para migración automática.")

    df_lmi   = cargar_lmi()
    df_kawak = cargar_kawak()
    df_cmi   = cargar_cmi()

    # ── 2. Cargar historico existente ────────────────────────────────────────
    print("\n[2] Cargando datos actuales...")
    df_hist_actual   = cargar_hoja_consolidado("Consolidado Historico")
    df_sem_actual    = cargar_hoja_consolidado("Consolidado Semestral")
    df_cie_actual    = cargar_hoja_consolidado("Consolidado Cierres")
    df_config_actual = cargar_config()

    print(f"    Historico actual : {len(df_hist_actual)} filas")
    print(f"    Semestral actual : {len(df_sem_actual)} filas")
    print(f"    Cierres actual   : {len(df_cie_actual)} filas")

    # ── 3. Configuración ─────────────────────────────────────────────────────
    print("\n[3] Actualizando Config_Indicadores...")
    df_config = crear_config_base(df_lmi, df_config_actual)
    print(f"    Config_Indicadores: {len(df_config)} indicadores")
    nuevos_en_config = len(df_config) - (len(df_config_actual) if not df_config_actual.empty else 0)
    if nuevos_en_config > 0:
        print(f"    Nuevos indicadores añadidos a Config: {nuevos_en_config}")
    print("    NOTA: revisa Config_Indicadores y ajusta Unidad, Tipo_Agregacion y Tope según corresponda.")

    # ── 4. Construir nuevas filas para Historico ──────────────────────────────
    print("\n[4] Construyendo nuevos registros de Historico...")
    df_hist_nuevo = construir_historico(df_kawak, df_lmi, df_cmi, df_config)
    print(f"    Registros generados desde Kawak: {len(df_hist_nuevo)}")

    # Upsert
    if not df_hist_actual.empty and "Id" in df_hist_actual.columns:
        df_hist_actual["Id"] = df_hist_actual["Id"].apply(id_a_str)
    df_hist_final = upsert(df_hist_actual, df_hist_nuevo, key="LLAVE")

    nuevos_hist   = len(df_hist_nuevo[~df_hist_nuevo["LLAVE"].isin(
        df_hist_actual["LLAVE"] if not df_hist_actual.empty else pd.Series(dtype=str)
    )])
    actuals_hist  = len(df_hist_nuevo) - nuevos_hist
    print(f"    Insertados: {nuevos_hist}  |  Actualizados: {actuals_hist}  |  Total: {len(df_hist_final)}")

    # ── 5. Calcular Semestral ─────────────────────────────────────────────────
    print("\n[5] Calculando Consolidado Semestral...")
    df_sem_nuevo  = calcular_semestral(df_hist_final, df_config)

    # Upsert preservando registros históricos anteriores a kawak
    df_sem_final  = upsert(df_sem_actual, df_sem_nuevo, key="LLAVE")
    print(f"    Semestral: {len(df_sem_final)} registros")

    # ── 6. Calcular Cierres ───────────────────────────────────────────────────
    print("\n[6] Calculando Consolidado Cierres...")
    df_cie_nuevo  = calcular_cierres(df_hist_final, df_config, df_lmi)

    # Upsert cierres (clave = Llave, minúscula en la hoja original)
    df_cie_final  = upsert(df_cie_actual, df_cie_nuevo, key="Llave")
    print(f"    Cierres: {len(df_cie_final)} registros")

    # ── 7. Guardar ────────────────────────────────────────────────────────────
    print("\n[7] Guardando Excel...")
    escribir_excel(df_hist_final, df_sem_final, df_cie_final, df_config)

    print(f"\n{sep}")
    print("  Proceso completado exitosamente.")
    print(f"  Archivo: {RUTA_CONSOL}")
    print(sep)


if __name__ == "__main__":
    main()
