"""
pages/1_Resumen_General.py — Reporte de Cumplimiento.

Fuente: data/raw/indicadores_kawak.xlsx
  · Último reporte habilitado por periodicidad (no simplemente el último registro)
  · Niveles: Sobrecumplimiento | Cumplimiento | Alerta | Peligro | No aplica | Pendiente de reporte

Mejoras:
  · Banner de fecha de corte visible
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
_DATA_RAW   = Path(__file__).parent.parent / "data" / "raw"
_RUTA_KAWAK = _DATA_RAW / "indicadores_kawak.xlsx"
_RUTA_MAPA  = _DATA_RAW / "Subproceso-Proceso-Area.xlsx"

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
    res = str(row.get("Resultado", "")).strip().upper()
    if res in ("N/A", "NA"):
        return _NO_APLICA
    c = _to_num(row.get("cumplimiento", ""))
    if c is None:
        return _PEND
    return nivel_desde_pct(c)


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


@st.cache_data(ttl=300, show_spinner="Cargando indicadores_kawak.xlsx...")
def _cargar_kawak_raw() -> pd.DataFrame:
    if not _RUTA_KAWAK.exists():
        return pd.DataFrame()
    df = pd.read_excel(str(_RUTA_KAWAK), engine="openpyxl",
                       keep_default_na=False, na_values=[""])
    df.columns = [str(c).strip() for c in df.columns]
    _rename = {
        "ID": "Id", "nombre": "Indicador", "clasificacion": "Clasificacion",
        "sentido": "Sentido", "proceso": "Subproceso", "frecuencia": "Periodicidad",
        "resultado": "Resultado", "meta": "Meta",
        "fecha": "fecha", "fecha_corte": "fecha_corte",
    }
    df = df.rename(columns={k: v for k, v in _rename.items() if k in df.columns})
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_limpio)
    for col in ["Indicador", "Clasificacion", "Sentido", "Subproceso", "Resultado"]:
        if col in df.columns:
            df[col] = df[col].apply(_limpiar)
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    return df


# Dataset_Unificado para el dialog de detalle (histórico completo)
@st.cache_data(ttl=300, show_spinner=False)
def _cargar_historico_detalle() -> pd.DataFrame:
    return cargar_dataset()


def _preparar_kawak_en_fecha(df_all: pd.DataFrame, hoy: _date) -> pd.DataFrame:
    """
    Selecciona el último reporte habilitado por periodicidad para la fecha `hoy`.
    Versión parametrizada para permitir comparación vs período anterior.
    """
    if df_all.empty:
        return df_all

    def _ultimo_valido(group):
        per   = str(group["Periodicidad"].iloc[0]) if "Periodicidad" in group.columns else ""
        corte = _corte_periodicidad(per, hoy)
        en_periodo = group[group["fecha"].notna() & (group["fecha"] <= corte)]
        if en_periodo.empty:
            fila = group.sort_values("fecha").iloc[[-1]].copy()
            fila["cumplimiento"] = None
            fila["Resultado"]    = ""
            return fila
        return en_periodo.sort_values("fecha").iloc[[-1]]

    col_per = "Periodicidad" if "Periodicidad" in df_all.columns else None
    if col_per and "fecha" in df_all.columns:
        df = (df_all.sort_values("fecha")
              .groupby("Id", group_keys=False)
              .apply(_ultimo_valido)
              .reset_index(drop=True))
    else:
        df = (df_all.sort_values("fecha")
              .groupby("Id", as_index=False)
              .last())

    df["Nivel de cumplimiento"] = df.apply(_nivel, axis=1)
    df["Cumplimiento"]  = df["cumplimiento"].apply(_fmt_num)
    if "Resultado" in df.columns:
        df["Resultado"] = df["Resultado"].apply(
            lambda v: _fmt_num(v) if _to_num(v) is not None
            else (str(v) if str(v).strip() else "—")
        )
    df["Fecha reporte"] = df["fecha"].dt.strftime("%d/%m/%Y").fillna("—") \
                          if "fecha" in df.columns else "—"

    mapa = _cargar_mapa()
    if not mapa.empty and "Subproceso" in df.columns:
        df = df.merge(mapa, on="Subproceso", how="left")

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
st.caption("Último reporte habilitado por periodicidad · Fuente: **indicadores_kawak.xlsx**")

# Carga
_raw = _cargar_kawak_raw()
if _raw.empty:
    st.error("No se encontró **indicadores_kawak.xlsx** en `data/raw/`.")
    st.stop()

hoy = _date.today()

with st.spinner("Procesando niveles de cumplimiento..."):
    df_raw = _preparar_kawak_en_fecha(_raw, hoy)

# ── Período anterior para comparativa ────────────────────────────────────────
# Retroceder ~1 mes para obtener el snapshot del período previo
if hoy.month == 1:
    hoy_prev = _date(hoy.year - 1, 12, 1)
else:
    hoy_prev = _date(hoy.year, hoy.month - 1, 1)

df_prev = _preparar_kawak_en_fecha(_raw, hoy_prev)

# Calcular corte actual (mensual como referencia)
corte_actual = _corte_periodicidad("mensual", hoy)
MESES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

# ── Banner de fecha de corte ──────────────────────────────────────────────────
st.markdown(
    f"""<div style="background:#E3EAF4;border-radius:8px;padding:10px 18px;
        border-left:4px solid #1A3A5C;margin-bottom:12px;">
        📅 <b>Corte de análisis:</b> {MESES_ES[corte_actual.month-1]} {corte_actual.year}
        &nbsp;·&nbsp; Datos al <b>{corte_actual.strftime('%d/%m/%Y')}</b>
        &nbsp;·&nbsp; Generado: {hoy.strftime('%d/%m/%Y')}
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
# TAB CONSOLIDADO — Drill-down interactivo + tabla + dialog
# ─────────────────────────────────────────────────────────────────────────────
with tab_con:
    st.markdown("### Vista Consolidada")
    st.caption("💡 Clic en un segmento de color para filtrar. Clic en una fila de la tabla para ver el detalle.")

    _KEY_V     = "rc_con_vicerr"
    _KEY_V_NIV = "rc_con_vicerr_niv"
    _KEY_P     = "rc_con_proc"
    _KEY_P_NIV = "rc_con_proc_niv"
    _KEY_S     = "rc_con_sub"
    _KEY_S_NIV = "rc_con_sub_niv"
    _KEY_DET   = "rc_con_det_id"

    for _k in [_KEY_V, _KEY_V_NIV, _KEY_P, _KEY_P_NIV, _KEY_S, _KEY_S_NIV, _KEY_DET]:
        if _k not in st.session_state:
            st.session_state[_k] = None

    # ── Nivel 1: Vicerrectoría ──────────────────────────────────────────────
    col_v, col_p = st.columns(2)
    with col_v:
        st.markdown("#### Por Vicerrectoría")
        if "Vicerrectoria" in df_raw.columns:
            ev_cv = st.plotly_chart(
                _fig_barras_nivel(df_raw, "Vicerrectoria"),
                use_container_width=True, on_select="rerun", key="con_vicerr_chart",
            )
            if ev_cv.selection and ev_cv.selection.get("points"):
                pt = ev_cv.selection["points"][0]
                st.session_state[_KEY_V]     = pt.get("y")
                st.session_state[_KEY_V_NIV] = pt.get("customdata")
                st.session_state[_KEY_P]     = None
                st.session_state[_KEY_P_NIV] = None
                st.session_state[_KEY_S]     = None
        sel_v     = st.session_state.get(_KEY_V)
        sel_v_niv = st.session_state.get(_KEY_V_NIV)
        if sel_v or sel_v_niv:
            parts = []
            if sel_v:     parts.append(f"**{sel_v}**")
            if sel_v_niv: parts.append(f"*{sel_v_niv}*")
            hv1, hv2 = st.columns([7, 1])
            with hv1:
                st.info(f"Filtro: {' · '.join(parts)}")
            with hv2:
                if st.button("✖", key="con_clear_v"):
                    for k in [_KEY_V, _KEY_V_NIV, _KEY_P, _KEY_P_NIV, _KEY_S, _KEY_S_NIV]:
                        st.session_state[k] = None
                    st.rerun()

    # Filtrar por Vicerrectoría seleccionada
    sel_v     = st.session_state.get(_KEY_V)
    sel_v_niv = st.session_state.get(_KEY_V_NIV)
    df_por_vicerr = df_raw.copy()
    if sel_v and "Vicerrectoria" in df_por_vicerr.columns:
        df_por_vicerr = df_por_vicerr[df_por_vicerr["Vicerrectoria"] == sel_v]
    if sel_v_niv:
        df_por_vicerr = df_por_vicerr[df_por_vicerr["Nivel de cumplimiento"] == sel_v_niv]

    # ── Nivel 2: Proceso ────────────────────────────────────────────────────
    with col_p:
        st.markdown("#### Por Proceso")
        if "Proceso" in df_por_vicerr.columns:
            ev_cp = st.plotly_chart(
                _fig_barras_nivel(df_por_vicerr, "Proceso"),
                use_container_width=True, on_select="rerun", key="con_proc_chart",
            )
            if ev_cp.selection and ev_cp.selection.get("points"):
                pt = ev_cp.selection["points"][0]
                st.session_state[_KEY_P]     = pt.get("y")
                st.session_state[_KEY_P_NIV] = pt.get("customdata")
                st.session_state[_KEY_S]     = None
        sel_p     = st.session_state.get(_KEY_P)
        sel_p_niv = st.session_state.get(_KEY_P_NIV)
        if sel_p or sel_p_niv:
            parts = []
            if sel_p:     parts.append(f"**{sel_p}**")
            if sel_p_niv: parts.append(f"*{sel_p_niv}*")
            hp1, hp2 = st.columns([7, 1])
            with hp1:
                st.info(f"Filtro: {' · '.join(parts)}")
            with hp2:
                if st.button("✖", key="con_clear_p"):
                    for k in [_KEY_P, _KEY_P_NIV, _KEY_S, _KEY_S_NIV]:
                        st.session_state[k] = None
                    st.rerun()

    # ── Nivel 3: Subproceso (drill-down tras selección de Proceso) ───────────
    sel_p = st.session_state.get(_KEY_P)
    sel_p_niv = st.session_state.get(_KEY_P_NIV)
    df_por_proc = df_por_vicerr.copy()
    if sel_p and "Proceso" in df_por_proc.columns:
        df_por_proc = df_por_proc[df_por_proc["Proceso"] == sel_p]
    if sel_p_niv:
        df_por_proc = df_por_proc[df_por_proc["Nivel de cumplimiento"] == sel_p_niv]

    if sel_p and "Subproceso" in df_por_proc.columns and not df_por_proc.empty:
        st.markdown(f"#### Por Subproceso — *{sel_p}*")
        ev_cs = st.plotly_chart(
            _fig_barras_nivel(df_por_proc, "Subproceso"),
            use_container_width=True, on_select="rerun", key="con_sub_chart",
        )
        if ev_cs.selection and ev_cs.selection.get("points"):
            pt = ev_cs.selection["points"][0]
            st.session_state[_KEY_S]     = pt.get("y")
            st.session_state[_KEY_S_NIV] = pt.get("customdata")
        sel_s     = st.session_state.get(_KEY_S)
        sel_s_niv = st.session_state.get(_KEY_S_NIV)
        if sel_s or sel_s_niv:
            parts = []
            if sel_s:     parts.append(f"**{sel_s}**")
            if sel_s_niv: parts.append(f"*{sel_s_niv}*")
            hs1, hs2 = st.columns([7, 1])
            with hs1:
                st.info(f"Filtro subproceso: {' · '.join(parts)}")
            with hs2:
                if st.button("✖", key="con_clear_s"):
                    st.session_state[_KEY_S]     = None
                    st.session_state[_KEY_S_NIV] = None
                    st.rerun()

    st.markdown("---")

    # ── Filtros UI ──────────────────────────────────────────────────────────
    # Aplicar todos los filtros gráficos primero
    sel_v     = st.session_state.get(_KEY_V)
    sel_v_niv = st.session_state.get(_KEY_V_NIV)
    sel_p     = st.session_state.get(_KEY_P)
    sel_p_niv = st.session_state.get(_KEY_P_NIV)
    sel_s     = st.session_state.get(_KEY_S)
    sel_s_niv = st.session_state.get(_KEY_S_NIV)

    df_chart_filt = df_raw.copy()
    if sel_v and "Vicerrectoria" in df_chart_filt.columns:
        df_chart_filt = df_chart_filt[df_chart_filt["Vicerrectoria"] == sel_v]
    if sel_v_niv:
        df_chart_filt = df_chart_filt[df_chart_filt["Nivel de cumplimiento"] == sel_v_niv]
    if sel_p and "Proceso" in df_chart_filt.columns:
        df_chart_filt = df_chart_filt[df_chart_filt["Proceso"] == sel_p]
    if sel_p_niv:
        df_chart_filt = df_chart_filt[df_chart_filt["Nivel de cumplimiento"] == sel_p_niv]
    if sel_s and "Subproceso" in df_chart_filt.columns:
        df_chart_filt = df_chart_filt[df_chart_filt["Subproceso"] == sel_s]
    if sel_s_niv:
        df_chart_filt = df_chart_filt[df_chart_filt["Nivel de cumplimiento"] == sel_s_niv]

    f_id, f_nom, f_vicerr_ui, f_proc_ui, f_sub, f_niv = _filtros_ui(df_raw, "con")
    df_tabla = _aplicar_filtros(df_chart_filt, f_id, f_nom, f_vicerr_ui, f_proc_ui, f_sub, f_niv)

    st.caption(f"Mostrando **{len(df_tabla)}** de **{total}** indicadores · clic en fila para detalle")
    st.markdown("---")

    # ── Tabla ───────────────────────────────────────────────────────────────
    COLS_TABLA = [
        "Id", "Indicador", "Nivel de cumplimiento", "Cumplimiento",
        "Resultado", "Meta", "Fecha reporte",
        "Vicerrectoria", "Area", "Proceso", "Subproceso",
        "Clasificacion", "Sentido", "Periodicidad",
    ]
    cols_show  = [c for c in COLS_TABLA if c in df_tabla.columns]
    df_mostrar = df_tabla[cols_show].copy()

    col_cfg = {
        "Indicador":             st.column_config.TextColumn("Indicador",             width="large"),
        "Nivel de cumplimiento": st.column_config.TextColumn("Nivel de cumplimiento", width="medium"),
        "Cumplimiento":          st.column_config.TextColumn("Cumplimiento",          width="small"),
        "Resultado":             st.column_config.TextColumn("Resultado",             width="small"),
        "Meta":                  st.column_config.TextColumn("Meta",                  width="small"),
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

    # Dialog de detalle al seleccionar fila
    if ev_tabla.selection and ev_tabla.selection.get("rows"):
        idx_det = ev_tabla.selection["rows"][0]
        id_det  = df_tabla["Id"].iloc[idx_det]
        st.session_state[_KEY_DET] = id_det

    id_det = st.session_state.get(_KEY_DET)
    if id_det:
        # Cargar histórico (Dataset_Unificado tiene más historia que kawak)
        df_hist = _cargar_historico_detalle()
        if not df_hist.empty and "Id" in df_hist.columns:
            df_ind_det = df_hist[df_hist["Id"] == id_det].copy()
        else:
            # Fallback: usar kawak_raw completo
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
