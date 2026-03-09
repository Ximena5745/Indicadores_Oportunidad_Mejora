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
from datetime import date as _date, timedelta as _td

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.charts import exportar_excel, panel_detalle_indicador
from utils.data_loader import cargar_dataset
from utils.niveles import NIVEL_COLOR, NIVEL_BG, NIVEL_ICON, nivel_desde_pct

# ── Rutas ─────────────────────────────────────────────────────────────────────
from pathlib import Path
_DATA_OUTPUT = Path(__file__).parent.parent / "data" / "output"
_DATA_RAW    = Path(__file__).parent.parent / "data" / "raw"
_RUTA_CONSOLIDADOS = _DATA_OUTPUT / "Resultados Consolidados.xlsx"
_RUTA_MAPA         = _DATA_RAW / "Subproceso-Proceso-Area.xlsx"
_RUTA_KAWAK_DIR    = _DATA_RAW / "Kawak"

# Meses en español para selección
MESES_OPCIONES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
_MES_NUM = {m: i+1 for i, m in enumerate(MESES_OPCIONES)}

# ── Niveles extendidos ─────────────────────────────────────────────────────────
_NO_APLICA   = "No aplica"
_PEND        = "Pendiente de reporte"

_NIVEL_COLOR = {
    **NIVEL_COLOR,
    _NO_APLICA: "#78909C",
    _PEND:      "#BDBDBD",
}
_NIVEL_BG = {
    **NIVEL_BG,
    _NO_APLICA: "#ECEFF1",
    _PEND:      "#F5F5F5",
}
_NIVEL_ICON = {
    **NIVEL_ICON,
    _NO_APLICA: "⚫",
    _PEND:      "⚪",
}
_NIVEL_ORDEN = [
    "Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento",
    _NO_APLICA, _PEND,
]
# Orden de severidad para detectar deterioro/mejora
_ORDEN_NUM = {
    "Peligro": 0, "Alerta": 1, "Cumplimiento": 2, "Sobrecumplimiento": 3,
    _NO_APLICA: -1, _PEND: -1,
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
    resultado = str(row.get("Resultado", "")).strip().upper() if "Resultado" in row else ""
    
    if resultado in ("N/A", "NA", "NO APLICA", "NO", ""):
        return _NO_APLICA
    
    c = _to_num(row.get("cumplimiento", ""))
    if c is None:
        return _PEND
    
    sentido = str(row.get("Sentido", "Positivo")).strip().lower()
    
    if sentido == "negativo":
        return _nivel_negativo(c)
    
    return nivel_desde_pct(c * 100)


def _nivel_negativo(cumplimiento: float) -> str:
    """Para indicadores de sentido negativo: menor cumplimiento es mejor."""
    try:
        c = float(cumplimiento)
    except (TypeError, ValueError):
        return _PEND
    pct = c * 100
    if pct > 100:
        return "Peligro"
    if pct > 80:
        return "Alerta"
    return "Cumplimiento"


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


# ── Periodicidad → fecha de corte ─────────────────────────────────────────────
def _corte_periodicidad(periodicidad: str, hoy: _date) -> pd.Timestamp:
    p = str(periodicidad).strip().lower()
    y, m = hoy.year, hoy.month

    def _fin(yr, mo):
        return pd.Timestamp(yr, mo, calendar.monthrange(yr, mo)[1], 23, 59, 59)

    if any(x in p for x in ("anual", "annual", "año")):
        return pd.Timestamp(y - 1, 12, 31, 23, 59, 59)
    if any(x in p for x in ("semestral", "bianual", "semest")):
        return pd.Timestamp(y - 1, 12, 31, 23, 59, 59) if m <= 6 \
               else pd.Timestamp(y, 6, 30, 23, 59, 59)
    if any(x in p for x in ("cuatrimestral", "cuatrim")):
        if m <= 4:
            return pd.Timestamp(y - 1, 12, 31, 23, 59, 59)
        if m <= 8:
            return pd.Timestamp(y, 4, 30, 23, 59, 59)
        return pd.Timestamp(y, 8, 31, 23, 59, 59)
    if any(x in p for x in ("trimestral", "trim", "quarter")):
        q = (m - 1) // 3
        if q == 0:
            return pd.Timestamp(y - 1, 12, 31, 23, 59, 59)
        return _fin(y, q * 3)
    if any(x in p for x in ("bimestral", "bimest")):
        b = (m - 1) // 2
        if b == 0:
            return pd.Timestamp(y - 1, 12, 31, 23, 59, 59)
        return _fin(y, b * 2)
    if any(x in p for x in ("mensual", "monthly", "mes")):
        return pd.Timestamp(y - 1, 12, 31, 23, 59, 59) if m == 1 \
               else _fin(y, m - 1)
    return pd.Timestamp(y - 1, 12, 31, 23, 59, 59)


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=600, show_spinner=False)
def _cargar_mapa() -> pd.DataFrame:
    if not _RUTA_MAPA.exists():
        return pd.DataFrame()
    df = pd.read_excel(str(_RUTA_MAPA), engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    col_sub    = next((c for c in df.columns if c.lower() == "subproceso"), None)
    col_proc   = next((c for c in df.columns if c.lower() == "proceso"), None)
    col_area   = next((c for c in df.columns
                       if "rea" in c.lower() and "vicerr" not in c.lower()), None)
    col_vicerr = next((c for c in df.columns if "icerrector" in c.lower()), None)
    if not col_sub or not col_proc:
        return pd.DataFrame()
    rename = {col_sub: "Subproceso", col_proc: "Proceso"}
    if col_area:   rename[col_area]   = "Area"
    if col_vicerr: rename[col_vicerr] = "Vicerrectoria"
    df = df.rename(columns=rename)
    cols_k = [c for c in ["Subproceso", "Proceso", "Area", "Vicerrectoria"] if c in df.columns]
    return (df[cols_k]
            .dropna(subset=["Subproceso"])
            .drop_duplicates(subset=["Subproceso"])
            .reset_index(drop=True))


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
        "Meta": "Meta", "Ejecucion": "Ejecucion", "Cumplimiento": "cumplimiento",
        "Cumplimiento Real": "cumplimiento_real",
    }
    
    for col in df.columns:
        col_lower = col.lower()
        if "año" in col_lower or "aio" in col_lower:
            col_renames[col] = "Anio"
    
    df = df.rename(columns={k: v for k, v in col_renames.items() if k in df.columns})
    
    if "Anio" in df.columns:
        df["Anio"] = pd.to_numeric(df["Anio"], errors="coerce")
    
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_limpio)
    for col in ["Indicador", "Proceso", "Periodicidad", "Sentido", "Mes", "Periodo"]:
        if col in df.columns:
            df[col] = df[col].apply(_limpiar)
    
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    
    # Primero calcular cumplimiento desde Ejecución y Meta
    if "Ejecucion" in df.columns and "Meta" in df.columns:
        df["cumplimiento"] = df.apply(
            lambda r: r["Ejecucion"] / r["Meta"] 
            if pd.notna(r["Ejecucion"]) and pd.notna(r["Meta"]) and r["Meta"] != 0 
            else None, 
            axis=1
        )
    
    # Sobrescribir con Cumplimiento Real si tiene más valores válidos
    if "Cumplimiento Real" in df.columns:
        mask_real = df["Cumplimiento Real"].notna()
        mask_cum = df["cumplimiento"].isna()
        df.loc[mask_real & mask_cum, "cumplimiento"] = df.loc[mask_real & mask_cum, "Cumplimiento Real"]
    
    # Sobrescribir con Cumplimiento si tiene más valores válidos
    if "Cumplimiento" in df.columns:
        mask_cum = df["Cumplimiento"].notna()
        mask_null = df["cumplimiento"].isna()
        df.loc[mask_cum & mask_null, "cumplimiento"] = df.loc[mask_cum & mask_null, "Cumplimiento"]
    
    return df


@st.cache_data(ttl=300, show_spinner=False)
def _obtener_anios_disponibles() -> list:
    """Retorna lista de años disponibles en el dataset."""
    df = _cargar_consolidados()
    if df.empty or "Anio" not in df.columns:
        return []
    anios = sorted(df["Anio"].dropna().unique().tolist())
    return [int(a) for a in anios if not pd.isna(a)]


@st.cache_data(ttl=600, show_spinner="Cargando IDs de Kawak...")
def _obtener_ids_kawak() -> set:
    """Retorna conjunto de IDs únicos de los archivos Kawak."""
    if not _RUTA_KAWAK_DIR.exists():
        return set()
    archivos = list(_RUTA_KAWAK_DIR.glob("*.xlsx"))
    ids_kawak = set()
    for arch in archivos:
        try:
            df = pd.read_excel(arch, engine="openpyxl")
            id_col = "ID" if "ID" in df.columns else ("Id" if "Id" in df.columns else None)
            if id_col:
                ids = df[id_col].dropna().astype(str).unique()
                ids_kawak.update(ids)
        except Exception:
            pass
    return ids_kawak


# Dataset_Unificado para el dialog de detalle (histórico completo)
@st.cache_data(ttl=300, show_spinner=False)
def _cargar_historico_detalle() -> pd.DataFrame:
    return cargar_dataset()


def _preparar_datos_por_fecha(df_all: pd.DataFrame, anio: int, mes: str) -> pd.DataFrame:
    """
    Selecciona los datos según el año y mes seleccionados.
    Para cada indicador, toma el último registro disponible hasta esa fecha.
    Solo incluye indicadores que existen en los archivos de Kawak.
    """
    if df_all.empty:
        return df_all
    
    ids_kawak = _obtener_ids_kawak()
    
    mes_num = _MES_NUM.get(mes, 12)
    ultimo_dia_mes = calendar.monthrange(anio, mes_num)[1]
    fecha_corte = pd.Timestamp(anio, mes_num, ultimo_dia_mes, 23, 59, 59)
    
    df_filtrado = df_all[df_all["fecha"].notna() & (df_all["fecha"] <= fecha_corte)].copy()
    
    if df_filtrado.empty:
        df_filtrado = df_all.copy()
    
    if ids_kawak:
        df_filtrado = df_filtrado[df_filtrado["Id"].isin(ids_kawak)]
    
    df = (df_filtrado.sort_values("fecha")
          .groupby("Id", as_index=False)
          .last())
    
    df["Nivel de cumplimiento"] = df.apply(_nivel, axis=1)
    df["Cumplimiento"] = df["cumplimiento"].apply(_fmt_num)
    if "cumplimiento_real" in df.columns:
        df["Cumplimiento Real"] = df["cumplimiento_real"].apply(_fmt_num)
    df["Fecha reporte"] = df["fecha"].dt.strftime("%d/%m/%Y").fillna("—") \
                          if "fecha" in df.columns else "—"
    
    mapa = _cargar_mapa()
    if not mapa.empty:
        if "Proceso" in df.columns:
            mapa_cols = list(mapa.columns)
            proc_col = next((c for c in mapa_cols if "proceso" in c.lower()), "Proceso")
            vic_col = next((c for c in mapa_cols if "icerrector" in c.lower()), None)
            sub_col = next((c for c in mapa_cols if "subproceso" in c.lower()), None)
            
            merge_cols = {}
            if sub_col:
                merge_cols["Subproceso"] = sub_col
            if proc_col:
                merge_cols["Proceso_mapa"] = proc_col
            if vic_col:
                merge_cols["Vicerrectoria"] = vic_col
            
            if merge_cols:
                df = df.merge(mapa[list(merge_cols.keys())].drop_duplicates(), 
                             left_on="Proceso", 
                             right_on=proc_col if proc_col else "Proceso", 
                             how="left")
                if vic_col and vic_col in df.columns:
                    df = df.rename(columns={vic_col: "Vicerrectoria"})
    
    return df


def _corte_periodicidad_per(periodicidad: str, anio: int, mes: int) -> pd.Timestamp:
    """Retorna la fecha de corte según periodicidad para el año/mes dado."""
    p = str(periodicidad).strip().lower()
    
    def _fin(yr, mo):
        return pd.Timestamp(yr, mo, calendar.monthrange(yr, mo)[1], 23, 59, 59)
    
    if any(x in p for x in ("anual", "annual", "año")):
        return pd.Timestamp(anio - 1, 12, 31, 23, 59, 59)
    if any(x in p for x in ("semestral", "bianual", "semest")):
        if mes <= 6:
            return pd.Timestamp(anio - 1, 12, 31, 23, 59, 59)
        else:
            return pd.Timestamp(anio, 6, 30, 23, 59, 59)
    if any(x in p for x in ("trimestral", "trim", "quarter")):
        q = (mes - 1) // 3
        if q == 0:
            return pd.Timestamp(anio - 1, 12, 31, 23, 59, 59)
        return _fin(anio, q * 3)
    if any(x in p for x in ("bimestral", "bimest")):
        b = (mes - 1) // 2
        if b == 0:
            return pd.Timestamp(anio - 1, 12, 31, 23, 59, 59)
        return _fin(anio, b * 2)
    if any(x in p for x in ("mensual", "monthly", "mes")):
        if mes == 1:
            return pd.Timestamp(anio - 1, 12, 31, 23, 59, 59)
        return _fin(anio, mes - 1)
    return pd.Timestamp(anio - 1, 12, 31, 23, 59, 59)


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


def _fig_barras_nivel(df, col_cat):
    if col_cat not in df.columns or df.empty:
        return go.Figure()
    tmp = df.copy()
    tmp[col_cat] = tmp[col_cat].astype(str).str.strip()
    tmp = tmp[tmp[col_cat].notna() & (tmp[col_cat] != "nan")]

    stats = (tmp.groupby([col_cat, "Nivel de cumplimiento"])
             .size().unstack(fill_value=0).reset_index())

    niveles = [n for n in _NIVEL_ORDEN if n in stats.columns]
    stats["_t"] = stats[niveles].sum(axis=1)
    stats = stats.sort_values("_t", ascending=False).drop(columns="_t")
    cats  = list(stats[col_cat].astype(str))

    max_len  = max((len(c) for c in cats), default=10)
    margin_l = min(max(max_len * 6, 120), 360)
    h        = max(300, len(stats) * 44 + 70)

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
            opts_v = [""] + sorted(df_opciones["Vicerrectoria"].dropna().unique().tolist()) \
                     if "Vicerrectoria" in df_opciones.columns else [""]
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

st.markdown("---")

# ── KPIs con comparativa ──────────────────────────────────────────────────────
total = len(df_raw)
cnts  = df_raw["Nivel de cumplimiento"].value_counts()

# Previos
cnts_p = df_prev["Nivel de cumplimiento"].value_counts() if not df_prev.empty else pd.Series(dtype=int)

kc = st.columns(6)
metricas = [
    ("Total",              total,                                                  None, "off"),
    ("🔴 Peligro",         int(cnts.get("Peligro", 0)),         int(cnts_p.get("Peligro", 0)),         "inverse"),
    ("🟡 Alerta",          int(cnts.get("Alerta", 0)),           int(cnts_p.get("Alerta", 0)),           "off"),
    ("🔵 Cumplimiento",    int(cnts.get("Cumplimiento", 0))
                         + int(cnts.get("Sobrecumplimiento", 0)),
                           int(cnts_p.get("Cumplimiento", 0))
                         + int(cnts_p.get("Sobrecumplimiento", 0)),                                    "normal"),
    ("⚫ No aplica",       int(cnts.get(_NO_APLICA, 0)),         int(cnts_p.get(_NO_APLICA, 0)),         "off"),
    ("⚪ Pendiente",       int(cnts.get(_PEND, 0)),              int(cnts_p.get(_PEND, 0)),              "off"),
]

for i, (label, val, val_prev, dc) in enumerate(metricas):
    with kc[i]:
        if val_prev is not None and label != "Total":
            delta    = val - val_prev
            delta_str = f"{delta:+d} vs período ant."
            st.metric(label, val, delta=delta_str, delta_color=dc)
        else:
            pct = f"{round(val/total*100,1)}%" if total and label != "Total" else None
            st.metric(label, val, delta=pct, delta_color=dc)

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
tab_res, tab_con = st.tabs(["📊 Resumen", "📋 Consolidado"])


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
    if "Proceso" in df_raw.columns:
        st.plotly_chart(_fig_barras_nivel(df_raw, "Proceso"),
                        use_container_width=True, key="res_proceso")

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


# ─────────────────────────────────────────────────────────────────────────────
# TAB CONSOLIDADO — Vista simplificada con filtros
# ─────────────────────────────────────────────────────────────────────────────
with tab_con:
    st.markdown("### Vista Consolidada")
    st.caption("💡 Seleccione filtros y clic en una fila para ver el detalle.")
    
    # ── Filtros de Período ─────────────────────────────────────────────────
    with st.expander("🔍 Filtros de Período", expanded=False):
        fc1, fc2 = st.columns(2)
        with fc1:
            anio_con = st.selectbox(
                "Año",
                options=anios_disponibles,
                index=anios_disponibles.index(anio_seleccionado) if anio_seleccionado in anios_disponibles else 0,
                key="anio_consolidado"
            )
        with fc2:
            mes_con = st.selectbox(
                "Mes",
                options=MESES_OPCIONES,
                index=MESES_OPCIONES.index(mes_seleccionado),
                key="mes_consolidado"
            )
    
    # Recalcular datos para consolidado con los valores seleccionados
    df_consolidado = _preparar_datos_por_fecha(_raw, anio_con, mes_con)

    # ── Gráfica de nivel de cumplimiento ─────────────────────────────────
    st.markdown("#### Distribución por Nivel de Cumplimiento")
    if not df_consolidado.empty:
        st.plotly_chart(_fig_donut(df_consolidado), use_container_width=True, key="con_donut")

    # ── Filtros de Vicerrectoría y Proceso ────────────────────────────────
    st.markdown("---")
    st.markdown("#### Filtros de Vista")
    
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        vicerrectorias = ["Todas"]
        if "Vicerrectoria" in df_consolidado.columns:
            vicerrectorias.extend(sorted(df_consolidado["Vicerrectoria"].dropna().unique()))
        sel_vicerrectoria = st.selectbox("Vicerrectoría", vicerrectorias, key="sel_vicerrectoria")
    
    with col_f2:
        procesos = ["Todos"]
        df_filt_vicerrectoria = df_consolidado
        if sel_vicerrectoria != "Todas" and "Vicerrectoria" in df_consolidado.columns:
            df_filt_vicerrectoria = df_consolidado[df_consolidado["Vicerrectoria"] == sel_vicerrectoria]
        if "Proceso" in df_filt_vicerrectoria.columns:
            procesos.extend(sorted(df_filt_vicerrectoria["Proceso"].dropna().unique()))
        sel_proceso = st.selectbox("Proceso", procesos, key="sel_proceso")
    
    # Aplicar filtros
    df_filt = df_consolidado.copy()
    if sel_vicerrectoria != "Todas" and "Vicerrectoria" in df_filt.columns:
        df_filt = df_filt[df_filt["Vicerrectoria"] == sel_vicerrectoria]
    if sel_proceso != "Todos" and "Proceso" in df_filt.columns:
        df_filt = df_filt[df_filt["Proceso"] == sel_proceso]

    st.markdown("---")

    total_consolidado = len(df_consolidado)
    st.caption(f"Mostrando **{len(df_filt)}** de **{total_consolidado}** indicadores · clic en fila para detalle")

    # ── Tabla ───────────────────────────────────────────────────────────────
    COLS_TABLA = [
        "Id", "Indicador", "Nivel de cumplimiento", "Cumplimiento",
        "Resultado", "Meta", "Fecha reporte",
        "Vicerrectoria", "Proceso", "Periodicidad",
    ]
    cols_show = [c for c in COLS_TABLA if c in df_filt.columns]
    df_mostrar = df_filt[cols_show].copy()

    col_cfg = {
        "Indicador": st.column_config.TextColumn("Indicador", width="large"),
        "Nivel de cumplimiento": st.column_config.TextColumn("Nivel de cumplimiento", width="medium"),
        "Cumplimiento": st.column_config.TextColumn("Cumplimiento", width="small"),
    }

    _KEY_DET = "rc_con_det_id"
    if _KEY_DET not in st.session_state:
        st.session_state[_KEY_DET] = None

    ev_tabla = st.dataframe(
        df_mostrar.style.apply(_estilo_nivel, axis=1),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config=col_cfg,
        key="con_tabla_detalle",
    )

    # Dialog de detalle
    if ev_tabla.selection and ev_tabla.selection.get("rows"):
        idx_det = ev_tabla.selection["rows"][0]
        id_det = df_filt["Id"].iloc[idx_det]
        st.session_state[_KEY_DET] = id_det

    id_det = st.session_state.get(_KEY_DET)
    if id_det:
        df_hist = _cargar_historico_detalle()
        if not df_hist.empty and "Id" in df_hist.columns:
            df_ind_det = df_hist[df_hist["Id"] == id_det].copy()
        else:
            df_ind_det = _raw[_raw["Id"] == id_det].copy()
            if "Cumplimiento_norm" not in df_ind_det.columns and "cumplimiento" in df_ind_det.columns:
                df_ind_det["Cumplimiento_norm"] = df_ind_det["cumplimiento"].apply(
                    lambda v: float(v) / 100 if v is not None and float(str(v).replace("%","") or 0) > 2
                    else float(v) if v is not None else float("nan")
                )
            if "Fecha" not in df_ind_det.columns and "fecha" in df_ind_det.columns:
                df_ind_det = df_ind_det.rename(columns={"fecha": "Fecha"})

        @st.dialog(f"Detalle del indicador: {id_det}", width="large")
        def _dialog_detalle():
            if st.button("✖ Cerrar"):
                st.session_state[_KEY_DET] = None
                st.rerun()
            panel_detalle_indicador(df_ind_det, id_det, df_ind_det)

        _dialog_detalle()

    st.download_button(
        "📥 Exportar Excel",
        data=exportar_excel(df_mostrar, "Cumplimiento"),
        file_name="reporte_cumplimiento.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="exp_cumplimiento",
    )
