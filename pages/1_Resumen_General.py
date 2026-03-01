"""
pages/1_Resumen_General.py — Reporte de Cumplimiento.

Fuente: data/raw/indicadores_kawak.xlsx (último reporte por indicador).
Tabs:
  📊 Resumen     — KPIs + gráficas principales (estáticas)
  📋 Consolidado — Vicerrectoría → filtra Proceso → filtra tabla + todos los filtros
"""
import html as _html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.charts import exportar_excel
from utils.niveles import NIVEL_COLOR, NIVEL_BG, NIVEL_ICON, nivel_desde_pct

# ── Rutas ─────────────────────────────────────────────────────────────────────
_DATA_RAW   = Path(__file__).parent.parent / "data" / "raw"
_RUTA_KAWAK = _DATA_RAW / "indicadores_kawak.xlsx"
_RUTA_MAPA  = _DATA_RAW / "Subproceso-Proceso-Area.xlsx"

# ── Niveles locales: "Sin dato" → "Pendiente de reporte" ─────────────────────
_PEND        = "Pendiente de reporte"
_NIVEL_COLOR = {**NIVEL_COLOR, _PEND: "#BDBDBD"}
_NIVEL_BG    = {**NIVEL_BG,    _PEND: "#F5F5F5"}
_NIVEL_ICON  = {**NIVEL_ICON,  _PEND: "⚪"}
_NIVEL_ORDEN = ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento", _PEND]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _to_num(v):
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return None


def _nivel(row) -> str:
    """Umbrales fijos; sin dato → Pendiente de reporte."""
    c = _to_num(row.get("cumplimiento", ""))
    if c is None:
        return _PEND
    return nivel_desde_pct(c)


def _limpiar(v) -> str:
    if pd.isna(v) if not isinstance(v, str) else False:
        return ""
    return _html.unescape(str(v)).strip()


def _id_limpio(x) -> str:
    if pd.isna(x) if not isinstance(x, str) else False:
        return ""
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x).strip()


def _fmt_num(v) -> str:
    n = _to_num(v)
    if n is None:
        return str(v) if str(v).strip() not in ("", "nan") else "—"
    return f"{n:,.2f}".rstrip("0").rstrip(".")


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
def _cargar_kawak() -> pd.DataFrame:
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
    for col in ["Indicador", "Clasificacion", "Sentido", "Subproceso"]:
        if col in df.columns:
            df[col] = df[col].apply(_limpiar)

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.sort_values("fecha", ascending=True)
    df = df.groupby("Id", as_index=False).last()

    # Nivel con "Pendiente de reporte" para indicadores sin cumplimiento
    df["Nivel de cumplimiento"] = df.apply(_nivel, axis=1)

    df["Cumplimiento"] = df["cumplimiento"].apply(_fmt_num)
    df["Resultado"]    = df["Resultado"].apply(
        lambda v: _fmt_num(v) if _to_num(v) is not None else str(v)
    )
    df["Fecha reporte"] = df["fecha"].dt.strftime("%d/%m/%Y").fillna("—")

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
        textinfo="label+value",
        textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>%{value} indicadores (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        height=320, showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.5),
        margin=dict(t=10, b=10, l=10, r=140),
        paper_bgcolor="white",
        annotations=[dict(text=f"<b>{total}</b><br>total",
                          x=0.5, y=0.5, font_size=16, showarrow=False)],
    )
    return fig


def _fig_barras_nivel(df, col_cat):
    """Barras horizontales apiladas por Nivel de cumplimiento."""
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
    cats = list(stats[col_cat].astype(str))

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
    """df_opciones: dataset completo, usado para poblar los dropdowns con todas las opciones."""
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
            if sel_vicerr and "Vicerrectoria" in df_opciones.columns and "Proceso" in df_opciones.columns:
                proc_pool = df_opciones.loc[df_opciones["Vicerrectoria"] == sel_vicerr,
                                            "Proceso"].dropna().unique().tolist()
            else:
                proc_pool = df_opciones["Proceso"].dropna().unique().tolist() \
                            if "Proceso" in df_opciones.columns else []
            opts_p = [""] + sorted(proc_pool)
            sel_proc = st.selectbox("Proceso", opts_p, key=f"{prefix}_proc",
                                    format_func=lambda x: "— Todos —" if x == "" else x)

        with r2c3:
            if sel_proc and "Proceso" in df_opciones.columns and "Subproceso" in df_opciones.columns:
                sub_pool = df_opciones.loc[df_opciones["Proceso"] == sel_proc,
                                           "Subproceso"].dropna().unique().tolist()
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


# ══════════════════════════════════════════════════════════════════════════════
# ESTILO TABLA
# ══════════════════════════════════════════════════════════════════════════════

def _estilo_nivel(row):
    bg = _NIVEL_BG.get(str(row.get("Nivel de cumplimiento", "")), "")
    return [f"background-color: {bg}" if c == "Nivel de cumplimiento" else ""
            for c in row.index]


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("# 🏠 Reporte de Cumplimiento")
st.caption("Último reporte por indicador · Fuente: **indicadores_kawak.xlsx**")
st.markdown("---")

df_raw = _cargar_kawak()

if df_raw.empty:
    st.error("No se encontró **indicadores_kawak.xlsx** en `data/raw/`.")
    st.stop()

total = len(df_raw)
cnts  = df_raw["Nivel de cumplimiento"].value_counts()
n_pend = int(cnts.get(_PEND, 0))

# ── KPIs (nivel de página, fuera de tabs) ─────────────────────────────────────
kc = st.columns(6)
with kc[0]:
    st.metric("Total indicadores", total)
for i, (niv, d_color) in enumerate([
        ("Peligro",           "inverse"),
        ("Alerta",            "off"),
        ("Cumplimiento",      "normal"),
        ("Sobrecumplimiento", "normal"),
], 1):
    n   = int(cnts.get(niv, 0))
    pct = round(n / total * 100, 1) if total else 0
    with kc[i]:
        st.metric(f"{_NIVEL_ICON[niv]} {niv}", n,
                  delta=f"{pct}%", delta_color=d_color)
with kc[5]:
    pct_p = round(n_pend / total * 100, 1) if total else 0
    st.metric(f"{_NIVEL_ICON[_PEND]} Pend. reporte", n_pend,
              delta=f"{pct_p}%", delta_color="off")

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_res, tab_con = st.tabs(["📊 Resumen", "📋 Consolidado"])


# ─────────────────────────────────────────────────────────────────────────────
# TAB RESUMEN — Gráficas principales (sin tabla)
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


# ─────────────────────────────────────────────────────────────────────────────
# TAB CONSOLIDADO — Cascada interactiva + todos los filtros + tabla
# ─────────────────────────────────────────────────────────────────────────────
with tab_con:
    st.markdown("### Vista Consolidada")

    _KEY_V = "rc_con_vicerr"
    _KEY_P = "rc_con_proc"

    # ── Gráfico Vicerrectoría → filtra gráfico Proceso y tabla ───────────────
    if "Vicerrectoria" in df_raw.columns:
        st.markdown("#### Por Vicerrectoría")
        st.caption("💡 Clic en una barra para filtrar el gráfico de Proceso y la tabla.")

        ev_cv = st.plotly_chart(_fig_barras_nivel(df_raw, "Vicerrectoria"),
                                use_container_width=True,
                                on_select="rerun", key="con_vicerr_chart")

        if ev_cv.selection and ev_cv.selection.get("points"):
            clicked_v = ev_cv.selection["points"][0].get("y")
            if clicked_v != st.session_state.get(_KEY_V):
                st.session_state[_KEY_V] = clicked_v
                st.session_state[_KEY_P] = None   # resetear Proceso al cambiar Vicerrectoría
                st.rerun()

        sel_v = st.session_state.get(_KEY_V)
        if sel_v:
            hv1, hv2 = st.columns([7, 1])
            with hv1:
                st.info(f"📊 Vicerrectoría seleccionada: **{sel_v}**")
            with hv2:
                if st.button("✖ Todos", key="con_clear_vicerr"):
                    st.session_state[_KEY_V] = None
                    st.session_state[_KEY_P] = None
                    st.rerun()

        st.markdown("---")

    # df pre-filtrado por Vicerrectoría del gráfico
    sel_v = st.session_state.get(_KEY_V)
    df_por_vicerr = df_raw[df_raw["Vicerrectoria"] == sel_v].copy() \
                    if sel_v and "Vicerrectoria" in df_raw.columns else df_raw.copy()

    # ── Gráfico Proceso → filtra tabla ───────────────────────────────────────
    if "Proceso" in df_por_vicerr.columns:
        st.markdown("#### Por Proceso")
        st.caption("💡 Clic en una barra para filtrar la tabla.")

        ev_cp = st.plotly_chart(_fig_barras_nivel(df_por_vicerr, "Proceso"),
                                use_container_width=True,
                                on_select="rerun", key="con_proc_chart")

        if ev_cp.selection and ev_cp.selection.get("points"):
            clicked_p = ev_cp.selection["points"][0].get("y")
            if clicked_p != st.session_state.get(_KEY_P):
                st.session_state[_KEY_P] = clicked_p
                st.rerun()

        sel_p = st.session_state.get(_KEY_P)
        if sel_p:
            hp1, hp2 = st.columns([7, 1])
            with hp1:
                st.info(f"📊 Proceso seleccionado: **{sel_p}**")
            with hp2:
                if st.button("✖ Todos", key="con_clear_proc"):
                    st.session_state[_KEY_P] = None
                    st.rerun()

        st.markdown("---")

    # df pre-filtrado también por Proceso del gráfico
    sel_p = st.session_state.get(_KEY_P)
    df_por_proc = df_por_vicerr[df_por_vicerr["Proceso"] == sel_p].copy() \
                  if sel_p and "Proceso" in df_por_vicerr.columns else df_por_vicerr

    # ── Todos los filtros UI (se aplican sobre el df ya filtrado por gráficos) ─
    f_id, f_nom, f_vicerr_ui, f_proc_ui, f_sub, f_niv = _filtros_ui(df_raw, "con")

    df_tabla = _aplicar_filtros(df_por_proc, f_id, f_nom, f_vicerr_ui, f_proc_ui, f_sub, f_niv)

    st.caption(f"Mostrando **{len(df_tabla)}** de **{total}** indicadores")
    st.markdown("---")

    # ── Tabla ─────────────────────────────────────────────────────────────────
    COLS_TABLA = [
        "Id", "Indicador", "Nivel de cumplimiento", "Cumplimiento",
        "Resultado", "Meta", "Fecha reporte",
        "Vicerrectoria", "Area", "Proceso", "Subproceso",
        "Clasificacion", "Sentido", "Periodicidad",
    ]
    cols_show = [c for c in COLS_TABLA if c in df_tabla.columns]
    df_mostrar = df_tabla[cols_show].copy()

    col_cfg = {
        "Indicador":             st.column_config.TextColumn("Indicador",            width="large"),
        "Nivel de cumplimiento": st.column_config.TextColumn("Nivel de cumplimiento", width="medium"),
        "Cumplimiento":          st.column_config.TextColumn("Cumplimiento",          width="small"),
        "Resultado":             st.column_config.TextColumn("Resultado",             width="small"),
        "Meta":                  st.column_config.TextColumn("Meta",                 width="small"),
    }

    st.dataframe(
        df_mostrar.style.apply(_estilo_nivel, axis=1),
        use_container_width=True, hide_index=True,
        column_config=col_cfg,
    )

    st.download_button(
        "📥 Exportar Excel",
        data=exportar_excel(df_mostrar, "Cumplimiento"),
        file_name="reporte_cumplimiento.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="exp_cumplimiento",
    )
