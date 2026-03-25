"""
pages/1_Resumen_General.py — Reporte de Cumplimiento.

Fuente: data/output/Resultados Consolidados.xlsx (hoja Consolidado Historico)
  · Selección de año y mes para análisis
  · Niveles: Sobrecumplimiento | Cumplimiento | Alerta | Peligro | No aplica | Pendiente de reporte

Mejoras:
  · Selector de año y mes
  · KPIs con comparativa vs período anterior
  · Caption de tendencia (mejoraron/empeoraron)
  · Desglose por Clasificación
  · Dialog de detalle al seleccionar fila en tabla consolidada
"""
import calendar
import html as _html
import math
from datetime import date as _date

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from components.charts import exportar_excel, panel_detalle_indicador
from services.data_loader import cargar_dataset, _cargar_mapa_proceso_padre, _ascii_lower
from core.niveles import (NIVEL_COLOR, NIVEL_BG, NIVEL_ICON, nivel_desde_pct,
                          UMBRAL_SOBRECUMPLIMIENTO_DEC)

# ── Rutas ─────────────────────────────────────────────────────────────────────
from pathlib import Path
_DATA_OUTPUT = Path(__file__).parent.parent / "data" / "output"
_DATA_RAW    = Path(__file__).parent.parent / "data" / "raw"
_RUTA_CONSOLIDADOS = _DATA_OUTPUT / "Resultados Consolidados.xlsx"
_RUTA_MAPA         = _DATA_RAW / "Subproceso-Proceso-Area.xlsx"
_RUTA_CMI          = _DATA_RAW / "Indicadores por CMI.xlsx"
_RUTA_KAWAK_DIR    = _DATA_RAW / "Kawak"

# Vicerrectorías excluidas de todos los filtros de Unidad / Vicerrectoría
VICERR_EXCLUIR: set = {"Gerencia Medellín"}

# Meses en español para selección
MESES_OPCIONES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
_MES_NUM = {m: i+1 for i, m in enumerate(MESES_OPCIONES)}

# ── Niveles extendidos ─────────────────────────────────────────────────────────
_NO_APLICA   = "No aplica"
_PEND        = "Pendiente de reporte"
_METRICA     = "Métrica"

_NIVEL_COLOR = {
    **NIVEL_COLOR,
    _NO_APLICA: "#78909C",
    _PEND:      "#BDBDBD",
    _METRICA:   "#5C6BC0",
}
_NIVEL_BG = {
    **NIVEL_BG,
    _NO_APLICA: "#ECEFF1",
    _PEND:      "#F5F5F5",
    _METRICA:   "#E8EAF6",
}
_NIVEL_ICON = {
    **NIVEL_ICON,
    _NO_APLICA: "⚫",
    _PEND:      "⚪",
    _METRICA:   "📐",
}
_NIVEL_ORDEN = [
    "Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento",
    _NO_APLICA, _PEND, _METRICA,
]
# Orden de severidad para detectar deterioro/mejora
_ORDEN_NUM = {
    "Peligro": 0, "Alerta": 1, "Cumplimiento": 2, "Sobrecumplimiento": 3,
    _NO_APLICA: -1, _PEND: -1, _METRICA: -1,
}


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _is_null(v) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    try:
        f = float(str(v).strip())
        return math.isnan(f)
    except (ValueError, TypeError):
        pass
    return str(v).strip().lower() in ("", "nan", "none")


def _to_num(v):
    if _is_null(v):
        return None
    try:
        f = float(str(v).strip())
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def _nivel(row) -> str:
    """Determina el nivel de cumplimiento del indicador."""
    tipo = str(row.get("Tipo_Registro", "") or "").strip().lower()
    if tipo == "metrica":
        return _METRICA

    if "Resultado" in row:
        resultado = str(row.get("Resultado", "")).strip().upper()
        if resultado in ("N/A", "NA", "NO APLICA", "NO"):
            return _NO_APLICA

    # Umbral Kawak: comparar Ejecucion (valor absoluto) contra peligro/alerta del año
    peligro_kwk = _to_num(row.get("peligro_kwk"))
    alerta_kwk  = _to_num(row.get("alerta_kwk"))
    ejec        = _to_num(row.get("Ejecucion"))
    if peligro_kwk is not None and ejec is not None:
        if ejec < peligro_kwk:
            return "Peligro"
        if alerta_kwk is not None and ejec < alerta_kwk:
            return "Alerta"
        # Verificar sobrecumplimiento por porcentaje
        c_kwk = _to_num(row.get("cumplimiento", ""))
        if c_kwk is not None and c_kwk >= UMBRAL_SOBRECUMPLIMIENTO_DEC:
            return "Sobrecumplimiento"
        return "Cumplimiento"

    # Fallback estándar: cumplimiento porcentual
    c = _to_num(row.get("cumplimiento", ""))
    if c is None:
        return _PEND
    if c >= UMBRAL_SOBRECUMPLIMIENTO_DEC:
        return "Sobrecumplimiento"
    return nivel_desde_pct(c * 100)


def _limpiar(v) -> str:
    if _is_null(v):
        return ""
    return _html.unescape(str(v)).strip()


def _id_limpio(x) -> str:
    if _is_null(x):
        return ""
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x).strip()


def _fmt_num(v) -> str:
    n = _to_num(v)
    if n is None:
        s = str(v).strip()
        return s if s and s.lower() not in ("nan", "none", "") else "—"
    return f"{n:,.2f}".rstrip("0").rstrip(".")


def _fmt_valor(v, signo, decimales) -> str:
    """Formatea un valor numérico concatenando signo y decimales.
    signo: '%' | '$' | 'ENT' | otro texto
    decimales: int o float indicando dígitos decimales
    """
    n = _to_num(v)
    if n is None:
        return "—"
    try:
        d = max(0, int(float(decimales))) if not _is_null(decimales) else 2
    except (ValueError, TypeError):
        d = 2
    s = str(signo).strip() if not _is_null(signo) else "%"
    su = s.upper()
    if s == "%":
        return f"{n:,.{d}f}%"
    elif s == "$":
        # Formato colombiano: . miles, , decimales (ej. $1.234.567,89)
        formatted = f"{n:,.{d}f}"  # "1,234,567.89"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"${formatted}"
    elif su in ("ENT", "N", "", "METRICA", "MÉTRICA"):
        return f"{int(round(n)):,}" if d == 0 else f"{n:,.{d}f}"
    elif su == "DEC":
        return f"{n:,.{d}f}"
    elif su in ("NO APLICA", "SIN REPORTE", "NA"):
        # Etiqueta de estado, no unidad — mostrar solo el número
        return f"{n:,.{d}f}" if d > 0 else f"{int(round(n)):,}"
    else:
        return f"{n:,.{d}f} {s}"


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

_INVALIDOS_MAPA = {"", "NAN", "NO APLICA", "N/A", "NONE", "SIN DATO"}


@st.cache_data(ttl=600, show_spinner=False)
def _cargar_mapa() -> pd.DataFrame:
    """Lee Subproceso-Proceso-Area.xlsx.
    La llave de cruce es SIEMPRE el Subproceso:
      data["Proceso"] contiene valores de Subproceso (ej: "Servicio", "Contabilidad")
      que se cruzan con mapa["Subproceso"] para obtener Proceso y Vicerrectoría.
    Solo se retornan filas con Subproceso y Proceso reales (sin 'No Aplica').
    """
    if not _RUTA_MAPA.exists():
        return pd.DataFrame()
    df = pd.read_excel(str(_RUTA_MAPA), engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    col_sub    = next((c for c in df.columns if "subproceso" in c.lower() and ".1" not in c.lower()), None)
    col_proc   = next((c for c in df.columns if c.lower() == "proceso"), None)
    col_vicerr = next((c for c in df.columns if "icerrector" in c.lower()), None)
    if not col_sub or not col_proc:
        return pd.DataFrame()
    rename = {col_sub: "Subproceso", col_proc: "Proceso"}
    if col_vicerr: rename[col_vicerr] = "Vicerrectoria"
    df = df.rename(columns=rename)
    cols_k = [c for c in ["Subproceso", "Proceso", "Vicerrectoria"] if c in df.columns]
    df = df[cols_k].copy()
    for c in ["Subproceso", "Proceso"]:
        df[c] = df[c].astype(str).str.strip()
    # Solo filas con Subproceso y Proceso válidos
    df = df[~df["Subproceso"].str.upper().isin(_INVALIDOS_MAPA)]
    df = df[~df["Proceso"].str.upper().isin(_INVALIDOS_MAPA)]
    return df.reset_index(drop=True)


@st.cache_data(ttl=600, show_spinner=False)
def _cargar_cmi() -> pd.DataFrame:
    """Retorna Id → Subproceso desde Indicadores por CMI.xlsx (fuente autoritativa)."""
    if not _RUTA_CMI.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(str(_RUTA_CMI), sheet_name="Worksheet", engine="openpyxl")
    except Exception:
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    col_id  = next((c for c in df.columns if c.lower() == "id"), None)
    col_sub = next((c for c in df.columns if c.lower() == "subproceso"), None)
    if not col_id or not col_sub:
        return pd.DataFrame()
    result = df[[col_id, col_sub]].copy()
    result = result.rename(columns={col_id: "Id", col_sub: "Subproceso_CMI"})
    result["Id"] = result["Id"].apply(_id_limpio)
    result["Subproceso_CMI"] = result["Subproceso_CMI"].astype(str).str.strip()
    _inv = {"", "NAN", "NO APLICA", "N/A", "NONE", "SIN DATO"}
    result = result[result["Id"] != ""]
    result = result[~result["Subproceso_CMI"].str.upper().isin(_inv)]
    return result.drop_duplicates(subset=["Id"], keep="first").reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner="Cargando Resultados Consolidados.xlsx...")
def _cargar_consolidados() -> pd.DataFrame:
    """Carga datos desde Resultados Consolidados.xlsx hoja Consolidado Historico."""
    if not _RUTA_CONSOLIDADOS.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(str(_RUTA_CONSOLIDADOS), sheet_name="Consolidado Historico",
                           engine="openpyxl", keep_default_na=False, na_values=[""])
    except Exception:
        return pd.DataFrame()
    
    df.columns = [str(c).strip() for c in df.columns]
    
    col_renames = {
        "Id": "Id", "Indicador": "Indicador", "Proceso": "Proceso",
        "Periodicidad": "Periodicidad", "Sentido": "Sentido",
        "Fecha": "fecha", "Mes": "Mes", "Periodo": "Periodo",
        "Meta": "Meta",
        "Ejecucion": "Ejecucion", "Ejecución": "Ejecucion",   # con y sin acento
        "Cumplimiento": "cumplimiento",
        "Cumplimiento Real": "cumplimiento_real",
        "Tipo_Registro": "Tipo_Registro",
        "Decimales_Meta": "Dec_Meta", "Decimales_Ejecucion": "Dec_Ejec",
    }
    # Signo de Meta y Ejecución — pueden tener variantes: 'Meta s', 'Ejecución s',
    # 'Meta Signo', 'Ejecucion Signo', etc.
    for col in df.columns:
        col_lower = col.lower().strip()
        col_norm  = col_lower.replace("ó", "o").replace("ú", "u").replace("á", "a")
        if "año" in col_lower or "aio" in col_lower:
            col_renames[col] = "Anio"
        elif col_norm in ("meta s", "meta signo", "meta_signo"):
            col_renames[col] = "Meta_Signo"
        elif "meta" in col_norm and "signo" in col_norm:
            col_renames[col] = "Meta_Signo"
        elif col_norm in ("ejecucion s", "ejecuci\u00f3n s", "ejecucion signo"):
            col_renames[col] = "Ejec_Signo"
        elif ("ejec" in col_norm or "ejecuci" in col_norm) and ("signo" in col_norm or col_norm.endswith(" s")):
            col_renames[col] = "Ejec_Signo"

    df = df.rename(columns={k: v for k, v in col_renames.items() if k in df.columns})

    # Garantizar que las columnas de signo/tipo existan
    for col in ("Tipo_Registro", "Meta_Signo", "Ejec_Signo", "Dec_Meta", "Dec_Ejec"):
        if col not in df.columns:
            df[col] = None
    
    if "Anio" in df.columns:
        df["Anio"] = pd.to_numeric(df["Anio"], errors="coerce")
    
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_limpio)
    for col in ["Indicador", "Proceso", "Periodicidad", "Sentido", "Mes", "Periodo"]:
        if col in df.columns:
            df[col] = df[col].apply(_limpiar)
    
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        # Derivar Anio/Mes/Periodo desde Fecha — las fórmulas Excel no tienen caché al guardar
        _fecha_s = df["fecha"]
        df["Anio"] = _fecha_s.dt.year
        _MESES_ES_P1 = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
                        7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",
                        11:"Noviembre",12:"Diciembre"}
        df["Mes"] = _fecha_s.dt.month.map(_MESES_ES_P1)
        df["Periodo"] = (_fecha_s.dt.year.astype("Int64").astype(str) + "-" +
                         _fecha_s.dt.month.apply(lambda m: "1" if pd.notna(m) and m <= 6 else "2"))

    # Normalizar columnas de cumplimiento (pueden venir vacías si son fórmulas Excel sin caché)
    if "cumplimiento" in df.columns:
        df["cumplimiento"] = pd.to_numeric(df["cumplimiento"], errors="coerce")
    else:
        df["cumplimiento"] = None

    if "cumplimiento_real" in df.columns:
        df["cumplimiento_real"] = pd.to_numeric(df["cumplimiento_real"], errors="coerce")
    else:
        df["cumplimiento_real"] = None

    # Si cumplimiento está vacío (fórmulas Excel sin caché), calcular desde Meta/Ejecucion
    ejec_col = next((c for c in df.columns
                     if c.lower().replace("ó", "o").replace("ú", "u")
                        in ("ejecucion", "ejecución")), None)
    if ejec_col and "Meta" in df.columns and "Sentido" in df.columns:
        meta_n = pd.to_numeric(df["Meta"], errors="coerce")
        ejec_n = pd.to_numeric(df[ejec_col], errors="coerce")
        valid  = meta_n.notna() & ejec_n.notna() & (meta_n != 0)
        sentido_neg = df["Sentido"].str.strip().str.lower() == "negativo"

        from core.config import IDS_PLAN_ANUAL, IDS_TOPE_100
        ratio_real = (ejec_n / meta_n).clip(lower=0).where(~sentido_neg,
                      (meta_n / ejec_n).clip(lower=0))
        # Plan Anual y Tope_100: tope 1.0;  resto: tope 1.3
        ids_str = df["Id"].astype(str).str.strip()
        tope = pd.Series(1.3, index=df.index)
        tope[ids_str.isin(IDS_PLAN_ANUAL | IDS_TOPE_100)] = 1.0
        ratio_cap  = ratio_real.clip(upper=tope)

        # Métricas: nunca calcular cumplimiento (no tienen meta objetivo)
        es_metrica_mask = df["Tipo_Registro"].astype(str).str.strip().str.lower() == "metrica" \
            if "Tipo_Registro" in df.columns else pd.Series(False, index=df.index)
        # Para Sentido=Negativo el Excel calcula ejec/meta (sin invertir),
        # por eso siempre se recalcula con la fórmula correcta meta/ejec.
        mask_calc = (df["cumplimiento"].isna() | sentido_neg) & valid & ~es_metrica_mask
        df.loc[mask_calc, "cumplimiento"]      = ratio_cap[mask_calc]
        df.loc[mask_calc, "cumplimiento_real"] = ratio_real[mask_calc]

    # Si cumplimiento aún vacío, rellenar desde cumplimiento_real
    mask_fill = df["cumplimiento"].isna() & df["cumplimiento_real"].notna()
    df.loc[mask_fill, "cumplimiento"] = df.loc[mask_fill, "cumplimiento_real"]

    # ── Agregar ProcesoPadre (subproceso → proceso padre) ─────────────────
    if "Proceso" in df.columns:
        _mapa = _cargar_mapa_proceso_padre()
        df["ProcesoPadre"] = df["Proceso"].apply(
            lambda x: _mapa.get(_ascii_lower(str(x)), str(x).strip())
        )

    # ── Enriquecer Clasificacion desde Catalogo Indicadores ────────────────
    if "Clasificacion" not in df.columns and _RUTA_CONSOLIDADOS.exists():
        try:
            df_cat = pd.read_excel(str(_RUTA_CONSOLIDADOS),
                                   sheet_name="Catalogo Indicadores", engine="openpyxl")
            df_cat.columns = [str(c).strip() for c in df_cat.columns]
            if "Id" in df_cat.columns and "Clasificacion" in df_cat.columns:
                df_cat["Id"] = df_cat["Id"].apply(_id_limpio)
                df = df.merge(
                    df_cat[["Id", "Clasificacion"]].drop_duplicates("Id"),
                    on="Id", how="left",
                )
        except Exception:
            pass

    return df


@st.cache_data(ttl=300, show_spinner=False)
def _obtener_anios_disponibles() -> list:
    """Retorna lista de años disponibles en el dataset."""
    df = _cargar_consolidados()
    if df.empty or "Anio" not in df.columns:
        return []
    anios = sorted(df["Anio"].dropna().unique().tolist())
    return [int(a) for a in anios if not pd.isna(a)]


@st.cache_data(ttl=600, show_spinner=False)
def _cargar_kawak_por_anio(anio: int) -> pd.DataFrame:
    """Carga IDs y umbrales (peligro/alerta) del archivo Kawak del año indicado.
    Si no existe el año, une todos los archivos disponibles como fallback.
    Retorna DataFrame con columnas: Id, peligro_kwk, alerta_kwk.
    """
    if not _RUTA_KAWAK_DIR.exists():
        return pd.DataFrame()

    path = _RUTA_KAWAK_DIR / f"{anio}.xlsx"
    archivos = [path] if path.exists() else list(_RUTA_KAWAK_DIR.glob("*.xlsx"))

    frames = []
    for arch in archivos:
        try:
            df = pd.read_excel(str(arch), engine="openpyxl")
            df.columns = [str(c).strip() for c in df.columns]
            id_col = "ID" if "ID" in df.columns else ("Id" if "Id" in df.columns else None)
            if not id_col:
                continue
            cols = {id_col: "Id"}
            if "peligro" in df.columns: cols["peligro"] = "peligro_kwk"
            if "alerta"  in df.columns: cols["alerta"]  = "alerta_kwk"
            sub = df[[c for c in cols]].rename(columns=cols).copy()
            sub["Id"] = sub["Id"].apply(_id_limpio)
            sub = sub[sub["Id"] != ""]
            frames.append(sub)
        except Exception:
            pass

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    for col in ["peligro_kwk", "alerta_kwk"]:
        if col not in result.columns:
            result[col] = None
        else:
            result[col] = pd.to_numeric(result[col], errors="coerce")
    return result.drop_duplicates(subset=["Id"], keep="first").reset_index(drop=True)


# Dataset_Unificado para el dialog de detalle (histórico completo)
@st.cache_data(ttl=300, show_spinner=False)
def _cargar_historico_detalle() -> pd.DataFrame:
    return cargar_dataset()


@st.cache_data(ttl=300, show_spinner=False)
def _cargar_consolidado_cierres() -> pd.DataFrame:
    """Lee Consolidado Cierres de Resultados Consolidados.xlsx."""
    if not _RUTA_CONSOLIDADOS.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(str(_RUTA_CONSOLIDADOS),
                           sheet_name="Consolidado Cierres", engine="openpyxl")
    except Exception:
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_limpio)
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    for col in ("Cumplimiento", "Cumplimiento Real"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Columna Año puede venir con encoding roto ("A?o")
    anio_col = next((c for c in df.columns
                     if c.startswith("A") and c.endswith("o") and len(c) <= 4), None)
    if anio_col and anio_col != "Año":
        df = df.rename(columns={anio_col: "Año"})
    return df


# Umbrales de cumplimiento para la matriz de calor (alineados con core/config.py)
_U_PELIGRO  = 0.80
_U_ALERTA   = 1.00
_U_SOBRE    = 1.05
_NIVEL_BG_C = {
    "Sobrecumplimiento": "#D0E4FF",
    "Cumplimiento":      "#E8F5E9",
    "Alerta":            "#FEF3D0",
    "Peligro":           "#FFCDD2",
    "Sin dato":          "#F5F5F5",
}
_COLORSCALE_C = [
    [0.000,          "#FFCDD2"],
    [_U_PELIGRO/1.35, "#EF9A9A"],
    [_U_ALERTA/1.35,  "#FEF3D0"],
    [(_U_ALERTA+0.001)/1.35, "#C8E6C9"],
    [_U_SOBRE/1.35,   "#81C784"],
    [1.000,           "#1A3A5C"],
]


def _nivel_c(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "Sin dato"
    if f >= _U_SOBRE:   return "Sobrecumplimiento"
    if f >= _U_ALERTA:  return "Cumplimiento"
    if f >= _U_PELIGRO: return "Alerta"
    return "Peligro"


def _estilo_cierres(row):
    estilos = []
    for col in row.index:
        if col in ("Nivel", "Cumplimiento %"):
            bg = _NIVEL_BG_C.get(row.get("Nivel", "Sin dato"), "")
            estilos.append(f"background-color:{bg}" if bg else "")
        else:
            estilos.append("")
    return estilos


def _mes_cierre_periodo(month: int, periodicidad: str) -> int:
    """Retorna el mes de CIERRE del período al que pertenece el mes dado."""
    perio = str(periodicidad or "").strip()
    if perio == "Mensual":    return month
    if perio == "Bimestral":  return month if month % 2 == 0 else month + 1
    if perio == "Trimestral":
        return 3 if month <= 3 else 6 if month <= 6 else 9 if month <= 9 else 12
    if perio == "Semestral":  return 6 if month <= 6 else 12
    if perio == "Anual":      return 12
    return month  # periodicidad desconocida → sin normalizar


def _preparar_datos_por_fecha(df_all: pd.DataFrame, anio: int, mes: str) -> pd.DataFrame:
    """
    Selecciona indicadores que tienen un registro en el mes+año indicados.
    Usa el mes de CIERRE del período (según Periodicidad) para el filtro,
    no el mes exacto de la fecha — así un Anual que reportó en octubre aparece
    como "Reportado" en diciembre, no como "Pendiente".
    Los IDs de Kawak sin ningún registro en el período se agregan como
    "Pendiente de reporte".
    """
    if df_all.empty:
        return df_all

    # Kawak del año seleccionado: IDs activos + umbrales por indicador
    kawak_df = _cargar_kawak_por_anio(anio)

    mes_num = _MES_NUM.get(mes, 12)

    # Filtrar año y calcular mes de cierre de cada registro según su Periodicidad
    df_anio = df_all[
        df_all["fecha"].notna() & (df_all["fecha"].dt.year == anio)
    ].copy()

    if df_anio.empty:
        return df_all.head(0)

    df_anio["_mes_cierre"] = df_anio.apply(
        lambda r: _mes_cierre_periodo(
            r["fecha"].month,
            r.get("Periodicidad", "") if "Periodicidad" in df_anio.columns else ""
        ),
        axis=1,
    )

    df_filtrado = df_anio[df_anio["_mes_cierre"] == mes_num].drop(columns=["_mes_cierre"])

    if df_filtrado.empty:
        # Fallback: semestre completo (no hay datos con mes de cierre exacto)
        semestre = 1 if mes_num <= 6 else 2
        meses_sem = list(range(1, 7)) if semestre == 1 else list(range(7, 13))
        df_filtrado = df_anio[
            df_anio["fecha"].dt.month.isin(meses_sem)
        ].drop(columns=["_mes_cierre"])

    if df_filtrado.empty:
        return df_all.head(0)

    if not kawak_df.empty:
        df_filtrado = df_filtrado[df_filtrado["Id"].isin(kawak_df["Id"].tolist())]

    df = (df_filtrado.sort_values("fecha")
          .groupby("Id", as_index=False)
          .last())

    # ── IDs de Kawak sin registro en el período → "Pendiente de reporte" ────────
    if not kawak_df.empty:
        ids_con_dato = set(df["Id"].tolist())
        ids_sin_dato = [kid for kid in kawak_df["Id"].tolist() if kid not in ids_con_dato]
        if ids_sin_dato:
            df_meta = (
                df_all[df_all["Id"].isin(ids_sin_dato)]
                .sort_values("fecha", na_position="last")
                .groupby("Id", as_index=False)
                .last()
            )
            if df_meta.empty:
                df_meta = pd.DataFrame({"Id": ids_sin_dato})
            df_meta["cumplimiento"]      = None
            df_meta["cumplimiento_real"] = None
            df_meta["fecha"]             = None
            df = pd.concat([df, df_meta], ignore_index=True)

    # Agregar umbrales Kawak al dataframe para que _nivel() pueda usarlos
    if not kawak_df.empty:
        df = df.merge(kawak_df[["Id", "peligro_kwk", "alerta_kwk"]], on="Id", how="left")

    import unicodedata as _ud
    def _norm_key(v):
        return _ud.normalize("NFD", str(v).strip()).encode("ascii", "ignore").decode().upper()

    # ── Paso 1: Subproceso autoritativo desde Indicadores por CMI (por Id) ───
    cmi = _cargar_cmi()
    if not cmi.empty and "Id" in df.columns:
        df = df.merge(cmi[["Id", "Subproceso_CMI"]], on="Id", how="left")
        _inv_mask = (
            df["Subproceso_CMI"].isna()
            | (df["Subproceso_CMI"].str.upper().isin(_INVALIDOS_MAPA))
        )
        fallback = df["Proceso"] if "Proceso" in df.columns else pd.Series("", index=df.index)
        df["Subproceso"] = df["Subproceso_CMI"].where(~_inv_mask, other=fallback)
        df = df.drop(columns=["Subproceso_CMI"], errors="ignore")
    elif "Proceso" in df.columns:
        df["Subproceso"] = df["Proceso"]

    # ── SST: tope de cumplimiento al 100% ────────────────────────────────────
    # Indicadores de GESTIÓN DE SEGURIDAD Y SALUD EN EL TRABAJO no pueden
    # superar el 100%. Se recalcula desde cumplimiento_real (valor sin tope).
    if "Subproceso" in df.columns and "cumplimiento_real" in df.columns:
        sst_mask = df["Subproceso"].str.upper().str.contains(
            r"SEGURIDAD.*SALUD|SST", na=False, regex=True)
        df.loc[sst_mask, "cumplimiento"] = (
            df.loc[sst_mask, "cumplimiento_real"].clip(upper=1.0))

    df["Nivel de cumplimiento"] = df.apply(_nivel, axis=1)
    _cum_display = "cumplimiento_real" if "cumplimiento_real" in df.columns else "cumplimiento"

    # Cumplimiento: Métrica no tiene → mostrar "—"; resto como porcentaje + icono nivel
    def _fmt_cum(row):
        niv = str(row.get("Nivel de cumplimiento", ""))
        if niv == _METRICA:
            return "—"
        v = _to_num(row.get(_cum_display))
        if v is None:
            return "—"
        # SST: mostrar máximo 100%
        sub = str(row.get("Subproceso", "")).upper()
        import re
        if re.search(r"SEGURIDAD.*SALUD|SST", sub):
            v = min(v, 1.0)
        icon = NIVEL_ICON.get(niv, "")
        pct  = f"{v * 100:,.2f}%"
        return f"{icon} {pct}" if icon else pct

    df["Cumplimiento"] = df.apply(_fmt_cum, axis=1)

    if "cumplimiento_real" in df.columns:
        def _fmt_cum_real(row):
            if str(row.get("Nivel de cumplimiento", "")) == _METRICA:
                return "—"
            v = _to_num(row.get("cumplimiento_real"))
            return f"{v * 100:,.2f}%" if v is not None else "—"
        df["Cumplimiento Real"] = df.apply(_fmt_cum_real, axis=1)

    # Meta y Ejecución formateadas con signo y decimales
    # Métricas: signo siempre "ENT" (nunca concatenar el texto "Metrica" ni "%")
    def _signo_fmt(r, col_signo):
        if str(r.get("Tipo_Registro", "")).strip().lower() == "metrica":
            return "ENT"
        return r.get(col_signo)

    df["Meta_fmt"] = df.apply(
        lambda r: _fmt_valor(r.get("Meta"), _signo_fmt(r, "Meta_Signo"), r.get("Dec_Meta")), axis=1)
    df["Ejecucion_fmt"] = df.apply(
        lambda r: _fmt_valor(r.get("Ejecucion"), _signo_fmt(r, "Ejec_Signo"), r.get("Dec_Ejec")), axis=1)

    df["Fecha reporte"] = df["fecha"].dt.strftime("%d/%m/%Y").fillna("—") \
                          if "fecha" in df.columns else "—"

    # ── Paso 2: Join mapa → Proceso real + Vicerrectoría ────────────────────
    mapa = _cargar_mapa()
    if not mapa.empty and "Subproceso" in df.columns:
        has_vic = "Vicerrectoria" in mapa.columns
        lookup_cols = ["Subproceso", "Proceso"] + (["Vicerrectoria"] if has_vic else [])
        lookup = (mapa[lookup_cols]
                  .drop_duplicates(subset=["Subproceso"], keep="first")
                  .copy())
        lookup["_key"] = lookup["Subproceso"].apply(_norm_key)
        lookup = lookup.drop(columns=["Subproceso"])
        df["_key"] = df["Subproceso"].apply(_norm_key)
        df = df.merge(lookup, on="_key", how="left")
        df = df.drop(columns=["_key"], errors="ignore")
        if "Proceso" not in df.columns:
            df["Proceso"] = df["Subproceso"]
    
    return df


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICOS
# ══════════════════════════════════════════════════════════════════════════════

def _fig_donut(df):
    counts = df["Nivel de cumplimiento"].value_counts()
    labels = [n for n in _NIVEL_ORDEN if n in counts.index]
    values = [int(counts[n]) for n in labels]
    colors = [_NIVEL_COLOR[n] for n in labels]
    total  = sum(values)
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+value", textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>%{value} indicadores (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        height=340, showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.5),
        margin=dict(t=10, b=10, l=10, r=160),
        paper_bgcolor="white",
        annotations=[dict(text=f"<b>{total}</b><br>total",
                          x=0.5, y=0.5, font_size=16, showarrow=False)],
    )
    return fig


def _fig_barras_nivel(df, col_cat, max_items=None):
    if col_cat not in df.columns or df.empty:
        return go.Figure()
    tmp = df.copy()
    tmp[col_cat] = tmp[col_cat].astype(str).str.strip()
    tmp = tmp[tmp[col_cat].notna() & (tmp[col_cat] != "nan")]

    stats = (tmp.groupby([col_cat, "Nivel de cumplimiento"])
             .size().unstack(fill_value=0).reset_index())

    niveles = [n for n in _NIVEL_ORDEN if n in stats.columns]
    # Ordenar: primero por Peligro+Alerta (criticidad), luego por total
    for _n in ("Peligro", "Alerta"):
        if _n not in stats.columns:
            stats[_n] = 0
    stats["_critico"] = stats["Peligro"] + stats["Alerta"]
    stats["_t"] = stats[niveles].sum(axis=1)
    stats = stats.sort_values(["_critico", "_t"], ascending=False).drop(columns=["_critico", "_t"])

    if max_items and len(stats) > max_items:
        stats = stats.head(max_items)

    cats  = list(stats[col_cat].astype(str))

    max_len  = max((len(c) for c in cats), default=10)
    margin_l = min(max(max_len * 6, 120), 360)
    h        = max(300, len(stats) * 36 + 70)

    fig = go.Figure()
    for nivel in niveles:
        if nivel not in stats.columns:
            continue
        vals = stats[nivel].tolist()
        fig.add_trace(go.Bar(
            y=cats, x=vals, orientation="h", name=nivel,
            marker_color=_NIVEL_COLOR.get(nivel, "#BDBDBD"),
            customdata=[nivel] * len(cats),
            text=[v if v > 0 else "" for v in vals],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=10, color="white"),
        ))

    fig.update_layout(
        barmode="stack", height=h,
        xaxis_title="Indicadores", yaxis_title="",
        yaxis=dict(categoryorder="array", categoryarray=cats,
                   autorange="reversed", tickfont=dict(size=10)),
        uniformtext_minsize=9, uniformtext_mode="hide",
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.12),
        margin=dict(t=10, b=55, l=margin_l, r=30),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# FILTROS
# ══════════════════════════════════════════════════════════════════════════════

def _aplicar_filtros(df, txt_id, txt_nom, sel_vicerr, sel_proc, sel_sub, sel_nivel):
    mask = pd.Series(True, index=df.index)
    if txt_id.strip():
        mask &= df["Id"].astype(str).str.contains(txt_id.strip(), case=False, na=False)
    if txt_nom.strip() and "Indicador" in df.columns:
        mask &= df["Indicador"].astype(str).str.contains(txt_nom.strip(), case=False, na=False)
    if sel_vicerr and "Vicerrectoria" in df.columns:
        mask &= df["Vicerrectoria"] == sel_vicerr
    if sel_proc and "Proceso" in df.columns:
        mask &= df["Proceso"] == sel_proc
    if sel_sub and "Subproceso" in df.columns:
        mask &= df["Subproceso"] == sel_sub
    if sel_nivel:
        mask &= df["Nivel de cumplimiento"] == sel_nivel
    return df[mask].reset_index(drop=True)


def _filtros_ui(df_opciones, prefix):
    with st.expander("🔍 Filtros", expanded=True):
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            txt_id = st.text_input("ID", key=f"{prefix}_id", placeholder="Buscar ID...")
        with r1c2:
            txt_nom = st.text_input("Nombre del indicador", key=f"{prefix}_nom",
                                    placeholder="Buscar nombre...")
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1:
            opts_v = [""] + sorted(
                v for v in (df_opciones["Vicerrectoria"].dropna().unique().tolist()
                            if "Vicerrectoria" in df_opciones.columns else [])
                if v not in VICERR_EXCLUIR
            )
            sel_vicerr = st.selectbox("Vicerrectoría", opts_v, key=f"{prefix}_vicerr",
                                      format_func=lambda x: "— Todas —" if x == "" else x)
        with r2c2:
            if sel_vicerr and "Vicerrectoria" in df_opciones.columns:
                proc_pool = df_opciones.loc[df_opciones["Vicerrectoria"] == sel_vicerr,
                                            "Proceso"].dropna().unique().tolist() \
                            if "Proceso" in df_opciones.columns else []
            else:
                proc_pool = df_opciones["Proceso"].dropna().unique().tolist() \
                            if "Proceso" in df_opciones.columns else []
            opts_p = [""] + sorted(proc_pool)
            sel_proc = st.selectbox("Proceso", opts_p, key=f"{prefix}_proc",
                                    format_func=lambda x: "— Todos —" if x == "" else x)
        with r2c3:
            if sel_proc and "Proceso" in df_opciones.columns:
                sub_pool = df_opciones.loc[df_opciones["Proceso"] == sel_proc,
                                           "Subproceso"].dropna().unique().tolist() \
                           if "Subproceso" in df_opciones.columns else []
            else:
                sub_pool = df_opciones["Subproceso"].dropna().unique().tolist() \
                           if "Subproceso" in df_opciones.columns else []
            opts_s = [""] + sorted(sub_pool)
            sel_sub = st.selectbox("Subproceso", opts_s, key=f"{prefix}_sub",
                                   format_func=lambda x: "— Todos —" if x == "" else x)
        with r2c4:
            niv_opts = [""] + [n for n in _NIVEL_ORDEN
                               if n in df_opciones["Nivel de cumplimiento"].unique()]
            sel_niv = st.selectbox("Nivel de cumplimiento", niv_opts, key=f"{prefix}_niv",
                                   format_func=lambda x: "— Todos —" if x == "" else x)
    return txt_id, txt_nom, sel_vicerr, sel_proc, sel_sub, sel_niv


def _estilo_nivel(row):
    bg = _NIVEL_BG.get(str(row.get("Nivel de cumplimiento", "")), "")
    return [f"background-color: {bg}" if c == "Nivel de cumplimiento" else ""
            for c in row.index]


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("# 🏠 Reporte de Cumplimiento")
st.caption("Fuente: **Resultados Consolidados.xlsx** · Hoja: Consolidado Historico · Solo indicadores de Kawak")

# Carga de datos
_raw = _cargar_consolidados()
if _raw.empty:
    st.error("No se encontró **Resultados Consolidados.xlsx** en `data/output/`.")
    st.stop()

# Obtener años disponibles
anios_disponibles = _obtener_anios_disponibles()
if not anios_disponibles:
    st.error("No se encontraron años en los datos.")
    st.stop()

# ── Selector de Año y Mes ─────────────────────────────────────────────────────
st.markdown("### 📅 Selección de Período")

col_sel1, col_sel2 = st.columns(2)
with col_sel1:
    anio_default = 2025 if 2025 in anios_disponibles else (anios_disponibles[-1] if anios_disponibles else 2024)
    anio_seleccionado = st.selectbox(
        "Año",
        options=anios_disponibles,
        index=anios_disponibles.index(anio_default) if anio_default in anios_disponibles else 0,
        key="anio_seleccionado"
    )
with col_sel2:
    mes_seleccionado = st.selectbox(
        "Mes",
        options=MESES_OPCIONES,
        index=11,  # Diciembre por defecto
        key="mes_seleccionado"
    )

# Calcular mes anterior para comparativa
mes_num = _MES_NUM[mes_seleccionado]
if mes_num == 1:
    anio_prev = anio_seleccionado - 1
    mes_prev = 12
else:
    anio_prev = anio_seleccionado
    mes_prev = mes_num - 1

with st.spinner("Procesando niveles de cumplimiento..."):
    df_raw = _preparar_datos_por_fecha(_raw, anio_seleccionado, mes_seleccionado)
    df_prev = _preparar_datos_por_fecha(_raw, anio_prev, MESES_OPCIONES[mes_prev - 1])

# Calcular fecha de corte
corte_actual = pd.Timestamp(anio_seleccionado, mes_num, 1)

# ── Banner de fecha de corte ──────────────────────────────────────────────────
st.markdown(
    f"""<div style="background:#E3EAF4;border-radius:8px;padding:10px 18px;
        border-left:4px solid #1A3A5C;margin-bottom:12px;">
        📅 <b>Corte de análisis:</b> {mes_seleccionado} {anio_seleccionado}
        &nbsp;·&nbsp; Generado: {_date.today().strftime('%d/%m/%Y')}
    </div>""",
    unsafe_allow_html=True,
)

# ── Filtros globales (siempre visibles) ───────────────────────────────────────
# Fila 1: Unidad → Proceso → Subproceso (dependientes en cascada)
_col_padre_f = "ProcesoPadre" if "ProcesoPadre" in df_raw.columns else "Proceso"

_fR1, _fR2, _fR3 = st.columns(3)
with _fR1:
    _vic_all = sorted(
        v for v in (df_raw["Vicerrectoria"].dropna().unique().tolist()
                    if "Vicerrectoria" in df_raw.columns else [])
        if v not in VICERR_EXCLUIR
    )
    _vic_opts = [""] + _vic_all
    _f_vic = st.selectbox("Unidad / Vicerrectoría", _vic_opts, key="rc_filt_vic",
                          format_func=lambda x: "— Todas —" if x == "" else x)

with _fR2:
    # Procesos filtrados por Unidad seleccionada
    if _f_vic and "Vicerrectoria" in df_raw.columns:
        _proc_pool = df_raw.loc[df_raw["Vicerrectoria"] == _f_vic, _col_padre_f] \
                     .dropna().unique().tolist() if _col_padre_f in df_raw.columns else []
    else:
        _proc_pool = df_raw[_col_padre_f].dropna().unique().tolist() \
                     if _col_padre_f in df_raw.columns else []
    _proc_opts = [""] + sorted(_proc_pool)
    _f_proc = st.selectbox("Proceso", _proc_opts, key="rc_filt_proc",
                           format_func=lambda x: "— Todos —" if x == "" else x)

with _fR3:
    # Subprocesos filtrados por Proceso seleccionado (y por Unidad si aplica)
    _df_for_sub = df_raw.copy()
    if _f_vic and "Vicerrectoria" in _df_for_sub.columns:
        _df_for_sub = _df_for_sub[_df_for_sub["Vicerrectoria"] == _f_vic]
    if _f_proc and _col_padre_f in _df_for_sub.columns:
        _df_for_sub = _df_for_sub[_df_for_sub[_col_padre_f] == _f_proc]
    _sub_pool = _df_for_sub["Subproceso"].dropna().unique().tolist() \
                if "Subproceso" in _df_for_sub.columns else []
    _sub_opts = [""] + sorted(_sub_pool)
    _f_sub = st.selectbox("Subproceso", _sub_opts, key="rc_filt_sub",
                          format_func=lambda x: "— Todos —" if x == "" else x)

# Fila 2: ID, Indicador, Tipo de indicador
_fR4, _fR5, _fR6 = st.columns(3)
with _fR4:
    _f_id = st.text_input("ID", key="rc_filt_id", placeholder="Buscar ID...")
with _fR5:
    _f_nom = st.text_input("Indicador", key="rc_filt_nom", placeholder="Buscar nombre...")
with _fR6:
    _tipo_opts = [""] + (sorted(df_raw["Tipo_Registro"].dropna().astype(str).str.strip()
                                .loc[lambda s: s != ""].unique().tolist())
                        if "Tipo_Registro" in df_raw.columns else [])
    _f_tipo = st.selectbox("Tipo de indicador", _tipo_opts, key="rc_filt_tipo",
                           format_func=lambda x: "— Todos —" if x == "" else x)

# ── Aplicar filtros globales a df_raw ────────────────────────────────────────
if _f_vic and "Vicerrectoria" in df_raw.columns:
    df_raw = df_raw[df_raw["Vicerrectoria"] == _f_vic]
if _f_proc and _col_padre_f in df_raw.columns:
    df_raw = df_raw[df_raw[_col_padre_f] == _f_proc]
if _f_sub and "Subproceso" in df_raw.columns:
    df_raw = df_raw[df_raw["Subproceso"] == _f_sub]
if _f_id.strip():
    df_raw = df_raw[df_raw["Id"].astype(str).str.contains(_f_id.strip(), case=False, na=False)]
if _f_nom.strip() and "Indicador" in df_raw.columns:
    df_raw = df_raw[df_raw["Indicador"].astype(str).str.contains(_f_nom.strip(), case=False, na=False)]
if _f_tipo and "Tipo_Registro" in df_raw.columns:
    df_raw = df_raw[df_raw["Tipo_Registro"].astype(str).str.strip() == _f_tipo]

# ── Aplicar los mismos filtros a df_prev para comparativa coherente ──────────
if _f_vic and "Vicerrectoria" in df_prev.columns:
    df_prev = df_prev[df_prev["Vicerrectoria"] == _f_vic]
if _f_proc:
    _cpf = "ProcesoPadre" if "ProcesoPadre" in df_prev.columns else "Proceso"
    if _cpf in df_prev.columns:
        df_prev = df_prev[df_prev[_cpf] == _f_proc]
if _f_sub and "Subproceso" in df_prev.columns:
    df_prev = df_prev[df_prev["Subproceso"] == _f_sub]
if _f_id.strip():
    df_prev = df_prev[df_prev["Id"].astype(str).str.contains(_f_id.strip(), case=False, na=False)]
if _f_nom.strip() and "Indicador" in df_prev.columns:
    df_prev = df_prev[df_prev["Indicador"].astype(str).str.contains(_f_nom.strip(), case=False, na=False)]
if _f_tipo and "Tipo_Registro" in df_prev.columns:
    df_prev = df_prev[df_prev["Tipo_Registro"].astype(str).str.strip() == _f_tipo]

st.markdown("---")

# ── KPIs con comparativa ──────────────────────────────────────────────────────
total = len(df_raw)
cnts  = df_raw["Nivel de cumplimiento"].value_counts()

# Previos
cnts_p = df_prev["Nivel de cumplimiento"].value_counts() if not df_prev.empty else pd.Series(dtype=int)

_CARD_COLORS = {
    "Total":              ("#1A3A5C", "#D0E4FF"),
    "Peligro":            ("#D32F2F", "#FFCDD2"),
    "Alerta":             ("#F57F17", "#FFF8E1"),
    "Cumplimiento":       ("#43A047", "#E8F5E9"),
    "Sobrecumplimiento":  ("#6699FF", "#EEF2FF"),
    "No aplica":          ("#BDBDBD", "#F9F9F9"),
    "Pendiente":          ("#9E9E9E", "#F5F5F5"),
}
metricas = [
    ("Total",              total,                                  None),
    ("Peligro",            int(cnts.get("Peligro", 0)),           int(cnts_p.get("Peligro", 0))),
    ("Alerta",             int(cnts.get("Alerta", 0)),            int(cnts_p.get("Alerta", 0))),
    ("Cumplimiento",       int(cnts.get("Cumplimiento", 0)),      int(cnts_p.get("Cumplimiento", 0))),
    ("Sobrecumplimiento",  int(cnts.get("Sobrecumplimiento", 0)), int(cnts_p.get("Sobrecumplimiento", 0))),
    ("No aplica",          int(cnts.get(_NO_APLICA, 0)),          int(cnts_p.get(_NO_APLICA, 0))),
    ("Pendiente",          int(cnts.get(_PEND, 0)),               int(cnts_p.get(_PEND, 0))),
]

kc = st.columns(len(metricas))
for i, (label, val, val_prev) in enumerate(metricas):
    border_c, bg_c = _CARD_COLORS.get(label, ("#9E9E9E", "#F5F5F5"))
    _lines = [
        f'<span style="font-size:0.8rem;color:{border_c};font-weight:600">{label}</span>',
        f'<span style="font-size:1.8rem;font-weight:700;color:{border_c}">{val}</span>',
    ]
    if total and label != "Total":
        _lines.append(f'<span style="font-size:0.75rem;color:#666">{round(val/total*100,1)}%</span>')
    if val_prev is not None and label != "Total":
        delta = val - val_prev
        d_color = "#43A047" if delta <= 0 and label in ("Peligro",) else (
                  "#D32F2F" if delta > 0 and label in ("Peligro",) else (
                  "#43A047" if delta > 0 and label in ("Cumplimiento", "Sobrecumplimiento") else (
                  "#D32F2F" if delta < 0 and label in ("Cumplimiento", "Sobrecumplimiento") else "#666")))
        _lines.append(f'<span style="font-size:0.75rem;color:{d_color}">{delta:+d} vs ant.</span>')
    _body = "<br>".join(_lines)
    with kc[i]:
        st.markdown(
            f'<div style="border-left:4px solid {border_c};background:{bg_c};'
            f'border-radius:8px;padding:12px;text-align:center;">'
            f'{_body}</div>',
            unsafe_allow_html=True,
        )

# Caption de tendencia general
if not df_prev.empty:
    # Comparar nivel por indicador (solo indicadores presentes en ambos)
    merge_niv = df_raw[["Id", "Nivel de cumplimiento"]].merge(
        df_prev[["Id", "Nivel de cumplimiento"]].rename(
            columns={"Nivel de cumplimiento": "Nivel_prev"}),
        on="Id", how="inner",
    )
    merge_niv["ord_act"]  = merge_niv["Nivel de cumplimiento"].map(_ORDEN_NUM)
    merge_niv["ord_prev"] = merge_niv["Nivel_prev"].map(_ORDEN_NUM)
    validos = merge_niv[(merge_niv["ord_act"] >= 0) & (merge_niv["ord_prev"] >= 0)]
    n_mejor  = int((validos["ord_act"] > validos["ord_prev"]).sum())
    n_peor   = int((validos["ord_act"] < validos["ord_prev"]).sum())
    if n_mejor or n_peor:
        st.caption(
            f"📈 **{n_mejor}** indicadores mejoraron de categoría · "
            f"📉 **{n_peor}** empeoraron · respecto al período anterior"
        )

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_res, tab_con, tab_calor, tab_cierres = st.tabs([
    "📊 Resumen", "📋 Consolidado", "🌡️ Matriz de Calor", "📂 Consolidado Cierres"
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB RESUMEN — Gráficas principales
# ─────────────────────────────────────────────────────────────────────────────
with tab_res:
    st.markdown("### Distribución General de Cumplimiento")
    gr1, gr2 = st.columns([1, 2])
    with gr1:
        st.markdown("#### Por Nivel")
        st.plotly_chart(_fig_donut(df_raw), use_container_width=True, key="res_donut")
    with gr2:
        st.markdown("#### Por Vicerrectoría")
        if "Vicerrectoria" in df_raw.columns:
            st.plotly_chart(_fig_barras_nivel(df_raw, "Vicerrectoria"),
                            use_container_width=True, key="res_vicerr")
        else:
            st.info("No hay datos de Vicerrectoría disponibles.")

    st.markdown("---")
    st.markdown("#### Por Proceso")
    _SK_RES_PROC = "res_sel_proceso"
    if _SK_RES_PROC not in st.session_state:
        st.session_state[_SK_RES_PROC] = ""

    _col_padre = "ProcesoPadre" if "ProcesoPadre" in df_raw.columns else "Proceso"
    _col_sub   = "Proceso"   # original = subproceso

    if _col_padre in df_raw.columns:
        n_proc = df_raw[_col_padre].nunique()
        st.caption("Haz clic en una barra para ver el desglose por Subproceso.")
        ev_res_proc = st.plotly_chart(
            _fig_barras_nivel(df_raw, _col_padre, max_items=25),
            use_container_width=True, key="res_proceso",
            on_select="rerun", selection_mode="points",
        )
        if n_proc > 25:
            with st.expander(f"Ver los {n_proc} procesos completos"):
                st.plotly_chart(_fig_barras_nivel(df_raw, _col_padre),
                                use_container_width=True, key="res_proceso_all")

        # Leer selección del gráfico
        _pts_res = (ev_res_proc.selection or {}).get("points", [])
        if _pts_res:
            _clicked = str(_pts_res[0].get("y", "")).strip()
            if _clicked and _clicked != st.session_state[_SK_RES_PROC]:
                st.session_state[_SK_RES_PROC] = _clicked
                st.rerun()
        else:
            if st.session_state[_SK_RES_PROC]:
                st.session_state[_SK_RES_PROC] = ""
                st.rerun()

        # Nivel 2: Subprocesos del proceso seleccionado
        if st.session_state[_SK_RES_PROC]:
            _proc_sel = st.session_state[_SK_RES_PROC]
            df_sub = df_raw[df_raw[_col_padre] == _proc_sel]
            if not df_sub.empty and _col_sub in df_sub.columns:
                st.markdown(f"**Subprocesos de: {_proc_sel}**")
                st.plotly_chart(
                    _fig_barras_nivel(df_sub, _col_sub),
                    use_container_width=True, key="res_subproceso",
                )

    st.markdown("---")
    st.markdown("#### Por Clasificación")
    if "Clasificacion" in df_raw.columns:
        df_clasif = df_raw[df_raw["Clasificacion"].notna() &
                           (df_raw["Clasificacion"].astype(str).str.strip() != "")]
        if not df_clasif.empty:
            st.plotly_chart(_fig_barras_nivel(df_clasif, "Clasificacion"),
                            use_container_width=True, key="res_clasif")
        else:
            st.info("Sin datos de Clasificación disponibles.")
    else:
        st.info("Columna Clasificación no encontrada. Verifique el Catálogo de Indicadores.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB CONSOLIDADO — Gráficas interactivas como filtros + tabla
# ─────────────────────────────────────────────────────────────────────────────
with tab_con:
    # Usar los mismos datos del período seleccionado en el encabezado
    df_con = df_raw.copy()

    # ── Claves de sesión para selecciones de gráficas ─────────────────────
    _SK_VC = "con_sel_vicerr"
    _SK_PR = "con_sel_proc"
    _KEY_DET = "rc_con_det_id"
    for _k in (_SK_VC, _SK_PR, _KEY_DET):
        if _k not in st.session_state:
            st.session_state[_k] = "" if _k != _KEY_DET else None

    # ── Gráficas clicables ────────────────────────────────────────────────
    st.markdown("### Distribución por Vicerrectoría y Proceso")
    st.caption("Haz clic en una barra para filtrar la tabla. Haz clic fuera para deseleccionar.")

    col_vc, col_pr = st.columns(2)

    with col_vc:
        st.markdown("#### Por Vicerrectoría")
        if "Vicerrectoria" in df_con.columns:
            fig_vc = _fig_barras_nivel(df_con, "Vicerrectoria")
            ev_vc = st.plotly_chart(
                fig_vc, use_container_width=True, key="con_chart_vicerr",
                on_select="rerun", selection_mode="points",
            )
            pts_vc = (ev_vc.selection or {}).get("points", [])
            if pts_vc:
                clicked_vc = str(pts_vc[0].get("y", "")).strip()
                if clicked_vc and clicked_vc != st.session_state[_SK_VC]:
                    st.session_state[_SK_VC] = clicked_vc
                    st.session_state[_SK_PR] = ""
                    st.rerun()
            else:
                # Sin puntos seleccionados → limpiar selección de vicerrectoría
                if st.session_state[_SK_VC]:
                    st.session_state[_SK_VC] = ""
                    st.session_state[_SK_PR] = ""
                    st.rerun()

    # Filtrar procesos según vicerrectoría seleccionada
    df_para_proc = (
        df_con[df_con["Vicerrectoria"] == st.session_state[_SK_VC]]
        if st.session_state[_SK_VC] and "Vicerrectoria" in df_con.columns
        else df_con
    )

    with col_pr:
        st.markdown("#### Por Proceso")
        _col_pr_chart = "ProcesoPadre" if "ProcesoPadre" in df_para_proc.columns else "Proceso"
        if _col_pr_chart in df_para_proc.columns:
            _n_proc_con = df_para_proc[_col_pr_chart].nunique()
            fig_pr = _fig_barras_nivel(df_para_proc, _col_pr_chart, max_items=25)
            ev_pr = st.plotly_chart(
                fig_pr, use_container_width=True, key="con_chart_proc",
                on_select="rerun", selection_mode="points",
            )
            if _n_proc_con > 25:
                st.caption(f"Mostrando 25 de {_n_proc_con} procesos (más críticos). Selecciona una Vicerrectoría para filtrar.")
            pts_pr = (ev_pr.selection or {}).get("points", [])
            if pts_pr:
                clicked_pr = str(pts_pr[0].get("y", "")).strip()
                if clicked_pr and clicked_pr != st.session_state[_SK_PR]:
                    st.session_state[_SK_PR] = clicked_pr
                    st.rerun()
            else:
                if st.session_state[_SK_PR]:
                    st.session_state[_SK_PR] = ""
                    st.rerun()

    # ── Chips de filtros activos ──────────────────────────────────────────
    activos = []
    if st.session_state[_SK_VC]:
        activos.append(f"Vicerrectoría: **{st.session_state[_SK_VC]}**")
    if st.session_state[_SK_PR]:
        activos.append(f"Proceso: **{st.session_state[_SK_PR]}**")

    inf_col, btn_col = st.columns([5, 1])
    with inf_col:
        if activos:
            st.info("🔍 " + " · ".join(activos))
    with btn_col:
        if activos and st.button("✖ Limpiar", key="con_clear_btn"):
            st.session_state[_SK_VC] = ""
            st.session_state[_SK_PR] = ""
            st.rerun()

    st.markdown("---")

    # ── Filtros adicionales de texto y nivel ──────────────────────────────
    with st.expander("🔍 Filtros adicionales", expanded=False):
        fa1, fa2, fa3 = st.columns(3)
        with fa1:
            txt_id  = st.text_input("ID", key="con_txt_id",  placeholder="Buscar ID...")
        with fa2:
            txt_nom = st.text_input("Indicador", key="con_txt_nom", placeholder="Buscar nombre...")
        with fa3:
            niv_opts = [""] + [n for n in _NIVEL_ORDEN
                               if n in df_con["Nivel de cumplimiento"].unique()]
            sel_niv = st.selectbox("Nivel de cumplimiento", niv_opts, key="con_niv",
                                   format_func=lambda x: "— Todos —" if x == "" else x)

    # ── Aplicar todos los filtros ─────────────────────────────────────────
    df_filt = df_con.copy()
    if st.session_state[_SK_VC] and "Vicerrectoria" in df_filt.columns:
        df_filt = df_filt[df_filt["Vicerrectoria"] == st.session_state[_SK_VC]]
    if st.session_state[_SK_PR]:
        _col_filt_pr = "ProcesoPadre" if "ProcesoPadre" in df_filt.columns else "Proceso"
        if _col_filt_pr in df_filt.columns:
            df_filt = df_filt[df_filt[_col_filt_pr] == st.session_state[_SK_PR]]
    if txt_id.strip():
        df_filt = df_filt[df_filt["Id"].astype(str).str.contains(txt_id.strip(), case=False, na=False)]
    if txt_nom.strip() and "Indicador" in df_filt.columns:
        df_filt = df_filt[df_filt["Indicador"].astype(str).str.contains(txt_nom.strip(), case=False, na=False)]
    if sel_niv:
        df_filt = df_filt[df_filt["Nivel de cumplimiento"] == sel_niv]

    st.caption(f"Mostrando **{len(df_filt)}** de **{len(df_con)}** indicadores · clic en una fila para ver el detalle histórico")

    # ── Tabla ─────────────────────────────────────────────────────────────
    _COLS_CON = [
        "Id", "Indicador", "Nivel de cumplimiento",
        "Meta_fmt", "Ejecucion_fmt", "Cumplimiento",
        "Fecha reporte",
        "Vicerrectoria", "Proceso", "Subproceso", "Periodicidad", "Sentido", "linea",
    ]
    cols_show = [c for c in _COLS_CON if c in df_filt.columns]
    df_mostrar = df_filt[cols_show].copy()

    col_cfg = {
        "Id":                    st.column_config.TextColumn("ID",           width="small"),
        "Indicador":             st.column_config.TextColumn("Indicador",    width="large"),
        "Nivel de cumplimiento": st.column_config.TextColumn("Nivel",        width="medium"),
        "Meta_fmt":              st.column_config.TextColumn("Meta",         width="small"),
        "Ejecucion_fmt":         st.column_config.TextColumn("Ejecución",    width="small"),
        "Cumplimiento":          st.column_config.TextColumn("Cumplimiento", width="small"),
        "Fecha reporte":         st.column_config.TextColumn("Fecha",        width="small"),
        "Vicerrectoria":         st.column_config.TextColumn("Vicerrectoría", width="medium"),
        "Proceso":               st.column_config.TextColumn("Proceso",      width="medium"),
        "Subproceso":            st.column_config.TextColumn("Subproceso",   width="medium"),
        "Periodicidad":          st.column_config.TextColumn("Periodicidad", width="small"),
        "Sentido":               st.column_config.TextColumn("Sentido",      width="small"),
        "linea":                 st.column_config.TextColumn("Línea",        width="medium"),
    }

    ev_tabla = st.dataframe(
        df_mostrar.style.apply(_estilo_nivel, axis=1),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config=col_cfg,
        key="con_tabla_detalle",
    )

    # ── Dialog de detalle ─────────────────────────────────────────────────
    if ev_tabla.selection and ev_tabla.selection.get("rows"):
        idx_det = ev_tabla.selection["rows"][0]
        st.session_state[_KEY_DET] = df_filt["Id"].iloc[idx_det]

    id_det = st.session_state.get(_KEY_DET)
    if id_det:
        df_hist = _cargar_historico_detalle()
        if not df_hist.empty and "Id" in df_hist.columns:
            df_ind_det = df_hist[df_hist["Id"] == id_det].copy()
        else:
            df_ind_det = _raw[_raw["Id"] == id_det].copy()
            if "Fecha" not in df_ind_det.columns and "fecha" in df_ind_det.columns:
                df_ind_det = df_ind_det.rename(columns={"fecha": "Fecha"})

        @st.dialog(f"Detalle: {id_det}", width="large")
        def _dialog_detalle():
            if st.button("✖ Cerrar"):
                st.session_state[_KEY_DET] = None
                st.rerun()
            panel_detalle_indicador(df_ind_det, id_det, df_ind_det)

        _dialog_detalle()

    # ── Exportar ──────────────────────────────────────────────────────────
    st.download_button(
        "📥 Exportar Excel",
        data=exportar_excel(df_mostrar, "Cumplimiento"),
        file_name="reporte_cumplimiento.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="exp_cumplimiento",
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB MATRIZ DE CALOR
# ─────────────────────────────────────────────────────────────────────────────
with tab_calor:
    # Fuente: Consolidado Historico (= _raw), ya cargado al inicio de la página.
    # Renombrar columnas a los nombres que espera este tab.
    _df_cierres = (
        _raw
        .rename(columns={"fecha": "Fecha", "cumplimiento": "Cumplimiento"})
        .copy()
    )

    if _df_cierres.empty:
        st.info("Sin datos de cierres históricos.")
    else:
        # Enriquecer con Subproceso desde CMI
        _cmi_c = _cargar_cmi()
        _dfc_all = _df_cierres.copy()
        if not _cmi_c.empty and "Id" in _dfc_all.columns:
            _dfc_all = _dfc_all.merge(_cmi_c[["Id", "Subproceso_CMI"]], on="Id", how="left")
            _dfc_all["Subproceso"] = _dfc_all["Subproceso_CMI"].where(
                _dfc_all["Subproceso_CMI"].notna()
                & ~_dfc_all["Subproceso_CMI"].str.upper().isin(_INVALIDOS_MAPA),
                other=_dfc_all["Proceso"] if "Proceso" in _dfc_all.columns else "",
            )
            _dfc_all = _dfc_all.drop(columns=["Subproceso_CMI"], errors="ignore")

        # Año de cada cierre
        if "Fecha" in _dfc_all.columns:
            _dfc_all["_año"] = _dfc_all["Fecha"].dt.year
            _anios_disp_c = sorted(_dfc_all["_año"].dropna().astype(int).unique().tolist())
        else:
            _anios_disp_c = []

        # Filtros globales: Año + Proceso + Subproceso
        # La periodicidad se usa como agrupación (pestañas), no como filtro
        _hc1, _hc2, _hc3 = st.columns(3)
        with _hc1:
            _sel_anios = st.multiselect(
                "Año",
                options=_anios_disp_c,
                default=[anio_seleccionado] if anio_seleccionado in _anios_disp_c else _anios_disp_c[-1:],
                key="cal_anios",
            )
        with _hc2:
            _procs_c = ["Todos"] + sorted(_dfc_all["Proceso"].dropna().unique().tolist()) \
                       if "Proceso" in _dfc_all.columns else ["Todos"]
            _proc_c = st.selectbox("Proceso", _procs_c, key="cal_proc")
        with _hc3:
            if _proc_c != "Todos" and "Proceso" in _dfc_all.columns and "Subproceso" in _dfc_all.columns:
                _sub_pool_c = _dfc_all.loc[_dfc_all["Proceso"] == _proc_c,
                                           "Subproceso"].dropna().unique().tolist()
            else:
                _sub_pool_c = _dfc_all["Subproceso"].dropna().unique().tolist() \
                              if "Subproceso" in _dfc_all.columns else []
            _subs_c = ["Todos"] + sorted(_sub_pool_c)
            _sub_c = st.selectbox("Subproceso", _subs_c, key="cal_sub")

        # Aplicar filtros (excepto periodicidad — esa define las pestañas)
        _dfc = _dfc_all.copy()
        if _sel_anios and "_año" in _dfc.columns:
            _dfc = _dfc[_dfc["_año"].isin(_sel_anios)]
        if _proc_c != "Todos" and "Proceso" in _dfc.columns:
            _dfc = _dfc[_dfc["Proceso"] == _proc_c]
        if _sub_c != "Todos" and "Subproceso" in _dfc.columns:
            _dfc = _dfc[_dfc["Subproceso"] == _sub_c]

        if _dfc.empty or "Fecha" not in _dfc.columns:
            st.info("Sin datos de cierres para los filtros seleccionados.")
        else:
            _MESES_ABREV_C = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                               "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

            # Meses de cierre canónicos por periodicidad
            _CIERRE_MESES = {
                "Anual":      [12],
                "Semestral":  [6, 12],
                "Trimestral": [3, 6, 9, 12],
                "Bimestral":  [2, 4, 6, 8, 10, 12],
                "Mensual":    list(range(1, 13)),
            }

            # Colorscale discreta (0=gris, 1=rojo, 2=amarillo, 3=verde, 4=azul)
            _DISC_CS = [
                [0.000, "#BDBDBD"], [0.125, "#BDBDBD"],
                [0.125, "#D32F2F"], [0.375, "#D32F2F"],
                [0.375, "#FBAF17"], [0.625, "#FBAF17"],
                [0.625, "#43A047"], [0.875, "#43A047"],
                [0.875, "#6699FF"], [1.000, "#6699FF"],
            ]

            def _nivel_code_c(v):
                if pd.isna(v): return 0
                try:
                    f = float(v)
                except (TypeError, ValueError):
                    return 0
                if f >= _U_SOBRE:   return 4
                if f >= _U_ALERTA:  return 3
                if f >= _U_PELIGRO: return 2
                return 1

            # Leyenda global (mostrar una sola vez)
            _lc = st.columns(5)
            for _col_l, (_lbl, _bg) in zip(_lc, [
                ("Sin dato",                 "#E0E0E0"),
                ("🔴 Peligro < 80%",         _NIVEL_BG_C["Peligro"]),
                ("🟡 Alerta 80–99%",         _NIVEL_BG_C["Alerta"]),
                ("🟢 Cumplimiento ≥ 100%",   _NIVEL_BG_C["Cumplimiento"]),
                ("🔵 Sobrecumplimiento ≥105%", _NIVEL_BG_C["Sobrecumplimiento"]),
            ]):
                _col_l.markdown(
                    f"<div style='background:{_bg};padding:6px 8px;border-radius:6px;"
                    f"text-align:center;font-size:11px;font-weight:500'>{_lbl}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("")

            # ── Resumen general de cumplimiento (último período por indicador) ──
            _last_all = _dfc.sort_values("Fecha").groupby("Id")["Cumplimiento"].last()
            _niv_all  = _last_all.apply(_nivel_code_c)
            _cnt_all  = _niv_all.value_counts()
            _avg_pct  = float(_last_all.dropna().mean() * 100) if not _last_all.dropna().empty else None
            _total_all = len(_last_all)

            _rc = st.columns([1, 1, 1, 1, 1, 1.2])
            for _ci, (_code, _bg, _lbl_g) in enumerate([
                (None,  "#F0F4F8", "Total"),
                (1,     "#FFCDD2", "🔴 Peligro"),
                (2,     "#FEF3D0", "🟡 Alerta"),
                (3,     "#E8F5E9", "🟢 Cumplimiento"),
                (4,     "#E8EEFF", "🔵 Sobrecumpl."),
            ]):
                _val = _total_all if _code is None else int(_cnt_all.get(_code, 0))
                _pct_lbl = f"<br><span style='font-size:10px;color:#666'>{_val/_total_all*100:.1f}%</span>" \
                           if _code is not None and _total_all else ""
                _rc[_ci].markdown(
                    f"<div style='background:{_bg};border-radius:8px;padding:10px 6px;"
                    f"text-align:center;border:1px solid #E0E6EF'>"
                    f"<b style='font-size:1.3rem'>{_val}</b>{_pct_lbl}"
                    f"<br><span style='font-size:10px'>{_lbl_g}</span></div>",
                    unsafe_allow_html=True,
                )
            if _avg_pct is not None:
                _color_avg = ("#43A047" if _avg_pct >= 100 else "#FBAF17" if _avg_pct >= 80 else "#D32F2F")
                _rc[5].markdown(
                    f"<div style='background:#F8F9FA;border-radius:8px;padding:10px 6px;"
                    f"text-align:center;border:1px solid #E0E6EF'>"
                    f"<b style='font-size:1.3rem;color:{_color_avg}'>{_avg_pct:.1f}%</b>"
                    f"<br><span style='font-size:10px'>Promedio gral.</span></div>",
                    unsafe_allow_html=True,
                )

            # Barra de distribución visual
            if _total_all:
                _bar_parts = ""
                for _code, _clr in [(1,"#D32F2F"),(2,"#FBAF17"),(3,"#43A047"),(4,"#6699FF"),(0,"#BDBDBD")]:
                    _w = int(_cnt_all.get(_code, 0)) / _total_all * 100
                    if _w > 0:
                        _bar_parts += (f"<div style='width:{_w:.1f}%;background:{_clr};"
                                       f"height:10px;display:inline-block;'></div>")
                st.markdown(
                    f"<div style='width:100%;border-radius:4px;overflow:hidden;"
                    f"margin:6px 0 10px 0'>{_bar_parts}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("---")

            # Etiqueta mes-año para cada registro
            _dfc = _dfc.copy()
            if "Periodicidad" in _dfc.columns:
                _dfc["Periodicidad"] = _dfc["Periodicidad"].astype(str).str.strip().str.title()
            _dfc["_col_label"] = _dfc["Fecha"].apply(
                lambda d: f"{_MESES_ABREV_C[d.month - 1]} {int(d.year)}" if pd.notna(d) else None
            )

            # Ordenar periodicidades por frecuencia (de mayor a menor)
            _PERIO_ORDEN = ["Anual", "Semestral", "Trimestral", "Bimestral", "Mensual"]
            _perios_presentes = []
            for _p in _PERIO_ORDEN:
                if "Periodicidad" in _dfc.columns and _p in _dfc["Periodicidad"].values:
                    _perios_presentes.append(_p)
            # Agregar periodicidades no estándar que estén presentes
            if "Periodicidad" in _dfc.columns:
                for _p in sorted(_dfc["Periodicidad"].dropna().unique()):
                    if _p not in _perios_presentes:
                        _perios_presentes.append(_p)

            if not _perios_presentes:
                st.info("No se encontró columna Periodicidad en los datos.")
            else:
                _tab_labels = [f"{_p} ({_dfc[_dfc['Periodicidad']==_p]['Id'].nunique()})" for _p in _perios_presentes]
                _perio_tabs = st.tabs(_tab_labels)

                for _pt, _perio in zip(_perio_tabs, _perios_presentes):
                    with _pt:
                        _dfc_p = _dfc[_dfc["Periodicidad"] == _perio].copy()
                        if _dfc_p.empty:
                            st.info(f"Sin datos para {_perio}.")
                            continue

                        # Columnas: solo meses de cierre de esta periodicidad × años
                        _meses_c = _CIERRE_MESES.get(_perio, list(range(1, 13)))
                        _cols_p = [
                            f"{_MESES_ABREV_C[_m - 1]} {_y}"
                            for _y in sorted(_sel_anios or [])
                            for _m in _meses_c
                        ]

                        # Pivot y reindex a columnas canónicas
                        _all_ids_p = _dfc_p["Id"].unique().tolist()
                        _pivot_p_data = _dfc_p.dropna(subset=["_col_label"])
                        if not _pivot_p_data.empty:
                            _pivot_p = (
                                _pivot_p_data
                                .sort_values("Fecha")
                                .groupby(["Id", "_col_label"])["Cumplimiento"]
                                .last()
                                .unstack()
                                .reindex(columns=_cols_p)
                            )
                        else:
                            _pivot_p = pd.DataFrame(index=pd.Index([], name="Id"), columns=_cols_p)
                        # Incluir todos los IDs de la periodicidad aunque no tengan cierres en el período
                        _pivot_p = _pivot_p.reindex(index=_all_ids_p)
                        if _pivot_p.empty:
                            st.info(f"Sin registros de cierre para {_perio}.")
                            continue

                        # KPI resumen para este grupo
                        _last_cum = _dfc_p.sort_values("Fecha").groupby("Id")["Cumplimiento"].last()
                        _niveles_p = _last_cum.apply(_nivel_code_c)
                        _cnt_p = _niveles_p.value_counts()
                        _kp = st.columns(5)
                        _kp[0].markdown(
                            f"<div style='background:#F0F4F8;border-radius:8px;padding:8px;"
                            f"text-align:center'><b style='font-size:1.2rem'>{len(_pivot_p)}</b>"
                            f"<br><span style='font-size:11px;color:#555'>Indicadores</span></div>",
                            unsafe_allow_html=True)
                        for _ki, (_code, _clr, _lbl_k) in enumerate([
                            (1, "#FFCDD2", "🔴 Peligro"),
                            (2, "#FEF3D0", "🟡 Alerta"),
                            (3, "#E8F5E9", "🟢 Cumplimiento"),
                            (4, "#D0E4FF", "🔵 Sobrecumpl."),
                        ]):
                            _kp[_ki + 1].markdown(
                                f"<div style='background:{_clr};border-radius:8px;padding:8px;"
                                f"text-align:center'><b style='font-size:1.2rem'>"
                                f"{int(_cnt_p.get(_code, 0))}</b>"
                                f"<br><span style='font-size:11px'>{_lbl_k}</span></div>",
                                unsafe_allow_html=True)
                        st.markdown("")

                        _meta_p   = _dfc_p.drop_duplicates("Id", keep="last").set_index("Id")
                        _row_h    = 28 if len(_pivot_p) > 30 else 32
                        _n_cols_p = len(_pivot_p.columns)

                        # ── Filas de datos ────────────────────────────────────
                        _ids_tbl = list(_pivot_p.index)
                        _ind_tbl = [
                            str(_meta_p.loc[k, "Indicador"])
                            if k in _meta_p.index and "Indicador" in _meta_p.columns
                            else str(k)
                            for k in _ids_tbl
                        ]
                        _sub_tbl = [
                            str(_meta_p.loc[k, "Subproceso"])
                            if k in _meta_p.index and "Subproceso" in _meta_p.columns
                            else ""
                            for k in _ids_tbl
                        ]
                        _n_rows  = len(_ids_tbl)
                        _row_fill = [
                            "#F4F6F9" if i % 2 == 0 else "white"
                            for i in range(_n_rows)
                        ]

                        # ── Colores de celdas de cumplimiento ─────────────────
                        _C_FILL = {
                            0: "#E0E0E0",  # Sin dato
                            1: "#D32F2F",  # Peligro
                            2: "#FBAF17",  # Alerta
                            3: "#43A047",  # Cumplimiento
                            4: "#6699FF",  # Sobrecumplimiento
                        }
                        _month_vals, _month_fill, _month_font = [], [], []
                        for _mc in _pivot_p.columns:
                            _vs = _pivot_p[_mc].tolist()
                            _month_vals.append([
                                f"{v * 100:.1f}%" if pd.notna(v) else "—" for v in _vs
                            ])
                            _codes = [_nivel_code_c(v) for v in _vs]
                            _month_fill.append([_C_FILL[c] for c in _codes])
                            _month_font.append([
                                "white" if c > 0 else "#888" for c in _codes
                            ])

                        # ── Anchos de columna ─────────────────────────────────
                        _id_w, _ind_w, _sub_w, _mes_w = 50, 280, 180, 80
                        _total_w = _id_w + _ind_w + _sub_w + _n_cols_p * _mes_w + 20

                        # ── Tabla única: info + datos con mismo encabezado ────
                        _hdr_vals = (
                            ["<b>ID</b>", "<b>Indicador</b>", "<b>Subproceso</b>"]
                            + [f"<b>{c}</b>" for c in _pivot_p.columns.tolist()]
                        )
                        _hdr_align = ["center", "left", "left"] + ["center"] * _n_cols_p
                        _cell_vals  = [_ids_tbl, _ind_tbl, _sub_tbl] + _month_vals
                        _cell_fill  = [_row_fill, _row_fill, _row_fill] + _month_fill
                        _cell_font_color = (
                            [["#1A3A5C"] * _n_rows,
                             ["#222"]    * _n_rows,
                             ["#555"]    * _n_rows]
                            + _month_font
                        )
                        _cell_align = ["center", "left", "left"] + ["center"] * _n_cols_p
                        _col_widths = [_id_w, _ind_w, _sub_w] + [_mes_w] * _n_cols_p

                        # Estimar altura de fila según el texto más largo (wrap)
                        # cells.height solo acepta escalar → usamos el máximo
                        import math as _math
                        _fw, _lh = 5.5, 15  # px/char, px/línea a font_size=10
                        _max_lines = 1
                        for _si, _ss in zip(_ind_tbl, _sub_tbl):
                            nl_i = _math.ceil(len(str(_si)) / max(1, int(_ind_w / _fw)))
                            nl_s = _math.ceil(len(str(_ss)) / max(1, int(_sub_w / _fw)))
                            _max_lines = max(_max_lines, nl_i, nl_s)
                        _row_h_unif = max(_row_h, _max_lines * _lh + 6)
                        _fig_h_full = 35 + _n_rows * _row_h_unif + 15

                        _fig_p = go.Figure(go.Table(
                            header=dict(
                                values=_hdr_vals,
                                fill_color="#1A3A5C",
                                font=dict(color="white", size=11),
                                height=35,
                                align=_hdr_align,
                                line=dict(color="#1A3A5C", width=1),
                            ),
                            cells=dict(
                                values=_cell_vals,
                                fill_color=_cell_fill,
                                font=dict(size=10, color=_cell_font_color),
                                height=_row_h_unif,
                                align=_cell_align,
                                line=dict(color="#E8ECF0", width=0.5),
                            ),
                            columnwidth=_col_widths,
                        ))
                        _fig_p.update_layout(
                            width=_total_w,
                            height=_fig_h_full,
                            margin=dict(t=5, b=5, l=5, r=5),
                            paper_bgcolor="white",
                        )
                        # Contenedor con barra de desplazamiento si la tabla es alta
                        _scroll_h = min(_fig_h_full + 20, 700)
                        with st.container(height=_scroll_h):
                            st.plotly_chart(_fig_p, use_container_width=False,
                                            key=f"calor_{_perio}")

                # Exportar datos completos
                st.download_button(
                    "📥 Exportar Excel",
                    data=exportar_excel(
                        _dfc[["Id"] + [c for c in _dfc.columns
                                       if c not in ("_col_label", "_año")]].drop_duplicates(),
                        "Matriz Calor"
                    ),
                    file_name="matriz_calor.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="exp_matriz_c",
                )


# ─────────────────────────────────────────────────────────────────────────────
# TAB CONSOLIDADO CIERRES
# ─────────────────────────────────────────────────────────────────────────────
with tab_cierres:
    _df_cierres_t = _cargar_consolidado_cierres()

    if _df_cierres_t.empty:
        st.info("Sin datos de cierres históricos.")
    else:
        # Enriquecer con signo/decimales desde dataset principal (por Id)
        _sign_cols_t = [c for c in ["Id", "Meta_Signo", "Ejec_Signo", "Dec_Meta", "Dec_Ejec", "Tipo_Registro"]
                        if c in _raw.columns]
        if len(_sign_cols_t) > 1:
            _sign_src = _raw[_sign_cols_t].drop_duplicates("Id")
            _df_cierres_t = _df_cierres_t.merge(_sign_src, on="Id", how="left")

        # Enriquecer con Subproceso desde CMI
        _cmi_t = _cargar_cmi()
        if not _cmi_t.empty and "Id" in _df_cierres_t.columns:
            _df_cierres_t = _df_cierres_t.merge(_cmi_t[["Id", "Subproceso_CMI"]], on="Id", how="left")
            _df_cierres_t["Subproceso"] = _df_cierres_t["Subproceso_CMI"].where(
                _df_cierres_t["Subproceso_CMI"].notna()
                & ~_df_cierres_t["Subproceso_CMI"].str.upper().isin(_INVALIDOS_MAPA),
                other=_df_cierres_t["Proceso"] if "Proceso" in _df_cierres_t.columns else "",
            )
            _df_cierres_t = _df_cierres_t.drop(columns=["Subproceso_CMI"], errors="ignore")

        # Formatear Meta y Ejecución con signo y decimales
        def _signo_fmt_t(r, col_signo):
            if str(r.get("Tipo_Registro", "")).strip().lower() == "metrica":
                return "ENT"
            return r.get(col_signo)

        if "Meta" in _df_cierres_t.columns:
            _df_cierres_t["Meta_fmt"] = _df_cierres_t.apply(
                lambda r: _fmt_valor(r.get("Meta"), _signo_fmt_t(r, "Meta_Signo"), r.get("Dec_Meta")), axis=1)
        if "Ejecucion" in _df_cierres_t.columns:
            _df_cierres_t["Ejecucion_fmt"] = _df_cierres_t.apply(
                lambda r: _fmt_valor(r.get("Ejecucion"), _signo_fmt_t(r, "Ejec_Signo"), r.get("Dec_Ejec")), axis=1)

        _df_cierres_t["Nivel"]          = _df_cierres_t["Cumplimiento"].apply(_nivel_c)
        _df_cierres_t["Cumplimiento %"] = _df_cierres_t["Cumplimiento"].apply(
            lambda v: f"{float(v) * 100:.1f}%" if pd.notna(v) else "—"
        )

        # Filtros: Proceso → Subproceso → ID → Nivel
        _cc1, _cc2, _cc3, _cc4 = st.columns(4)
        with _cc1:
            _procs_cc = ["Todos"] + sorted(_df_cierres_t["Proceso"].dropna().unique().tolist()) \
                        if "Proceso" in _df_cierres_t.columns else ["Todos"]
            _proc_cc = st.selectbox("Proceso", _procs_cc, key="cc_proc")
        with _cc2:
            if _proc_cc != "Todos" and "Subproceso" in _df_cierres_t.columns:
                _sub_pool_cc = _df_cierres_t.loc[
                    _df_cierres_t["Proceso"] == _proc_cc, "Subproceso"
                ].dropna().unique().tolist()
            else:
                _sub_pool_cc = _df_cierres_t["Subproceso"].dropna().unique().tolist() \
                               if "Subproceso" in _df_cierres_t.columns else []
            _subs_cc = ["Todos"] + sorted(_sub_pool_cc)
            _sub_cc = st.selectbox("Subproceso", _subs_cc, key="cc_sub")
        with _cc3:
            _txt_id_cc = st.text_input("ID", key="cc_id", placeholder="Buscar ID…")
        with _cc4:
            _niv_opts_cc = [""] + ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento", "Sin dato"]
            _sel_niv_cc  = st.selectbox("Nivel", _niv_opts_cc, key="cc_niv",
                                        format_func=lambda x: "— Todos —" if x == "" else x)

        _dfc2 = _df_cierres_t.copy()
        if _proc_cc != "Todos" and "Proceso" in _dfc2.columns:
            _dfc2 = _dfc2[_dfc2["Proceso"] == _proc_cc]
        if _sub_cc != "Todos" and "Subproceso" in _dfc2.columns:
            _dfc2 = _dfc2[_dfc2["Subproceso"] == _sub_cc]
        if _txt_id_cc.strip():
            _dfc2 = _dfc2[_dfc2["Id"].astype(str).str.contains(_txt_id_cc.strip(), case=False, na=False)]
        if _sel_niv_cc:
            _dfc2 = _dfc2[_dfc2["Nivel"] == _sel_niv_cc]

        # KPIs
        _cnts_cc = _dfc2["Nivel"].value_counts()
        _kc2 = st.columns(5)
        _kc2[0].metric("Total",              len(_dfc2))
        _kc2[1].metric("🔴 Peligro",          int(_cnts_cc.get("Peligro",           0)))
        _kc2[2].metric("🟡 Alerta",            int(_cnts_cc.get("Alerta",             0)))
        _kc2[3].metric("🟢 Cumplimiento",      int(_cnts_cc.get("Cumplimiento",       0)))
        _kc2[4].metric("🔵 Sobrecumplimiento", int(_cnts_cc.get("Sobrecumplimiento",  0)))

        st.caption(f"**{len(_dfc2):,}** registros · {_dfc2['Id'].nunique()} indicadores")

        _COLS_CC = ["Id", "Indicador", "Proceso", "Subproceso", "Periodicidad", "Sentido",
                    "Fecha", "Periodo", "Meta_fmt", "Ejecucion_fmt", "Cumplimiento %", "Nivel"]
        _cols_cc = [c for c in _COLS_CC if c in _dfc2.columns]
        _df_cc_show = _dfc2[_cols_cc].copy()
        if "Fecha" in _df_cc_show.columns:
            _df_cc_show["Fecha"] = _df_cc_show["Fecha"].dt.strftime("%d/%m/%Y").fillna("—")

        st.dataframe(
            _df_cc_show.style.apply(_estilo_cierres, axis=1),
            use_container_width=True, hide_index=True,
            column_config={
                "Indicador":     st.column_config.TextColumn("Indicador",  width="large"),
                "Subproceso":    st.column_config.TextColumn("Subproceso", width="medium"),
                "Meta_fmt":      st.column_config.TextColumn("Meta",       width="small"),
                "Ejecucion_fmt": st.column_config.TextColumn("Ejecución",  width="small"),
                "Nivel":         st.column_config.TextColumn("Nivel",      width="medium"),
            },
        )
        st.download_button(
            "📥 Exportar Excel",
            data=exportar_excel(_df_cc_show, "Consolidado Cierres"),
            file_name="consolidado_cierres.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="exp_cierres_c",
        )
