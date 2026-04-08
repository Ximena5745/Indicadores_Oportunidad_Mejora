"""
pages/5_Seguimiento_de_reportes.py  (v2 — formato largo)
=========================================================
Fuente: data/output/Seguimiento_Reporte.xlsx → hoja "Tracking Mensual"
Generada por generar_reporte.py (construir_tracking_largo).

Estructura del DataFrame de entrada:
  Id | [meta LMI] | Periodicidad | Año | Mes | Mes_Nombre | Periodo | Estado | Fuente

Valores de Estado: "Reportado" | "Pendiente" | "No aplica"
Valores de Fuente: "Kawak"     | "LMI"       | "—"
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import exportar_excel

# ── Rutas ──────────────────────────────────────────────────────────────────────
_RUTA_XLSX = Path(__file__).parent.parent / "data" / "output" / "Seguimiento_Reporte.xlsx"

# ── Paleta corporativa ─────────────────────────────────────────────────────────
CORP = {
    "reportado":  "#1FB2DE",
    "pendiente":  "#EC0677",
    "no_aplica":  "#9E9E9E",
    "primario":   "#0F385A",
    "secundario": "#1FB2DE",
    "alerta":     "#FBAF17",
}
COLOR_ESTADO = {
    "Reportado": "#EDF7D6",
    "Pendiente": "#FDE8F3",
    "No aplica": "#EEEEEE",
}

# ── Columnas internas ──────────────────────────────────────────────────────────
COL_ESTADO = "Estado"
COL_FUENTE = "Fuente"
COL_PERIO  = "Periodicidad"

_MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _id_limpio(x) -> str:
    if pd.isna(x):
        return ""
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x)


def _cols_pres(df, preferidas):
    return [c for c in preferidas if c in df.columns]


def _col_nombre(df):
    for c in ["Indicador", "Nombre", "Descripcion", "Descripción"]:
        if c in df.columns:
            return c
    return None


def _estilo_estado(row):
    """Colorea la celda de Estado según su valor."""
    estilos = []
    for col in row.index:
        if col == COL_ESTADO:
            bg = COLOR_ESTADO.get(str(row[col]).strip(), "")
            estilos.append(f"background-color: {bg}" if bg else "")
        else:
            estilos.append("")
    return estilos


def _agg_estado(df: pd.DataFrame, col_cat: str) -> pd.DataFrame:
    """
    Agrupa df por col_cat y cuenta Reportado / Pendiente.
    Excluye filas "No aplica" del conteo.
    """
    if COL_ESTADO not in df.columns or col_cat not in df.columns:
        return pd.DataFrame()
    df = df[df[COL_ESTADO] != "No aplica"].copy()
    df[col_cat] = df[col_cat].astype(str).str.strip()
    df = df[df[col_cat].notna() & (df[col_cat] != "nan")]
    stats = (
        df.groupby(col_cat)[COL_ESTADO]
        .value_counts().unstack(fill_value=0).reset_index()
    )
    stats["_t"] = stats.drop(columns=[col_cat]).sum(axis=1)
    stats = stats.sort_values("_t", ascending=False).drop(columns="_t")
    return stats


def _bar_h(df_stats: pd.DataFrame, col_cat: str, height=None):
    """Barras horizontales apiladas Reportado / Pendiente."""
    col_rep = "Reportado" if "Reportado" in df_stats.columns else None
    col_pen = "Pendiente"  if "Pendiente"  in df_stats.columns else None

    cats = list(df_stats[col_cat].astype(str))
    fig = go.Figure()
    if col_rep:
        vals = df_stats[col_rep].tolist()
        fig.add_trace(go.Bar(
            y=cats, x=vals, orientation="h", name="Reportado",
            marker_color=CORP["reportado"],
            customdata=["Reportado"] * len(cats),
            text=[v if v > 0 else "" for v in vals],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color="white"),
        ))
    if col_pen:
        vals = df_stats[col_pen].tolist()
        fig.add_trace(go.Bar(
            y=cats, x=vals, orientation="h", name="Pendiente",
            marker_color=CORP["pendiente"],
            customdata=["Pendiente"] * len(cats),
            text=[v if v > 0 else "" for v in vals],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color="white"),
        ))

    h = height or max(320, len(df_stats) * 42 + 70)
    max_len = max((len(str(c)) for c in cats), default=10)
    margin_l = min(max(max_len * 6, 120), 340)
    fig.update_layout(
        barmode="stack", height=h,
        xaxis_title="Indicadores", yaxis_title="",
        yaxis=dict(categoryorder="array", categoryarray=cats,
                   autorange="reversed", tickfont=dict(size=10)),
        uniformtext_minsize=9, uniformtext_mode="hide",
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.12),
        margin=dict(t=15, b=50, l=margin_l, r=30),
    )
    return fig


def _aplicar_filtros_tabla(df: pd.DataFrame, txt_id: str, txt_nombre: str,
                            sel_proc: str, sel_estado: str) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if txt_id.strip() and "Id" in df.columns:
        mask &= df["Id"].astype(str).str.contains(txt_id.strip(), case=False, na=False)
    if txt_nombre.strip():
        col_nom = next((c for c in ["Indicador", "Nombre"] if c in df.columns), None)
        if col_nom:
            mask &= df[col_nom].astype(str).str.contains(
                txt_nombre.strip(), case=False, na=False)
    if sel_proc and "Proceso" in df.columns:
        mask &= df["Proceso"] == sel_proc
    if sel_estado and COL_ESTADO in df.columns:
        mask &= df[COL_ESTADO] == sel_estado
    return df[mask].reset_index(drop=True)


def _filtros_tabla_ui(df: pd.DataFrame, prefix: str):
    """Widget de filtros: ID, Nombre, Proceso, Estado."""
    with st.expander("🔍 Filtros", expanded=False):
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            txt_id = st.text_input("ID", key=f"{prefix}_id",
                                   placeholder="Buscar ID...")
        with r1c2:
            txt_nom = st.text_input("Indicador", key=f"{prefix}_nom",
                                    placeholder="Buscar nombre...")
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            opts_proc = [""] + (
                sorted(df["Proceso"].dropna().unique().tolist())
                if "Proceso" in df.columns else [])
            sel_proc = st.selectbox("Proceso", opts_proc, key=f"{prefix}_proc",
                                    format_func=lambda x: "— Todos —" if x == "" else x)
        with r2c2:
            opts_est = [""] + (
                sorted(df[COL_ESTADO].dropna().unique().tolist())
                if COL_ESTADO in df.columns else [])
            sel_est = st.selectbox("Estado", opts_est, key=f"{prefix}_est",
                                   format_func=lambda x: "— Todos —" if x == "" else x)
    return txt_id, txt_nom, sel_proc, sel_est


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner="Cargando Tracking Mensual...")
def _cargar_datos() -> pd.DataFrame:
    if not _RUTA_XLSX.exists():
        return pd.DataFrame()
    xl = pd.ExcelFile(str(_RUTA_XLSX), engine="openpyxl")
    if "Tracking Mensual" not in xl.sheet_names:
        return pd.DataFrame()
    df = xl.parse("Tracking Mensual")
    df.columns = [str(c).strip() for c in df.columns]
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_limpio)
    # Asegurar tipos correctos
    for col in ("Año", "Mes"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


# ── Cargar ─────────────────────────────────────────────────────────────────────
df_tracking = _cargar_datos()

if df_tracking.empty:
    st.error(
        "No se encontró la hoja **'Tracking Mensual'** en `data/output/Seguimiento_Reporte.xlsx`. "
        "Ejecuta primero `generar_reporte.py`."
    )
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# ENCABEZADO Y FILTROS GLOBALES (Año + Mes)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# 📊 Seguimiento de Reporte de Indicadores")

_años_disp = sorted(df_tracking["Año"].dropna().unique().tolist()) \
             if "Año" in df_tracking.columns else []
_años_disp = [int(a) for a in _años_disp]

_fc1, _fc2 = st.columns(2)
with _fc1:
    _año_sel = st.selectbox("Año", _años_disp,
                            index=len(_años_disp) - 1 if _años_disp else 0,
                            key="seg_año")
with _fc2:
    _meses_del_año = sorted(
        df_tracking[df_tracking["Año"] == _año_sel]["Mes"].dropna().unique().tolist()
    ) if "Mes" in df_tracking.columns else []
    _meses_del_año = [int(m) for m in _meses_del_año]
    _mes_opts  = [""] + [_MESES_ES[m] for m in _meses_del_año if m in _MESES_ES]
    _mes_sel_t = st.selectbox("Mes", _mes_opts, key="seg_mes",
                              format_func=lambda x: "— Todos —" if x == "" else x)
    _mes_sel_n = {v: k for k, v in _MESES_ES.items()}.get(_mes_sel_t)

st.markdown("---")

# ── Filtrar tracking por Año + Mes ─────────────────────────────────────────────
_mask = df_tracking["Año"] == _año_sel
if _mes_sel_n is not None:
    _mask &= df_tracking["Mes"] == _mes_sel_n
df_sel = df_tracking[_mask].copy()

# Solo indicadores "activos" (excluye No aplica para KPIs)
df_active = df_sel[df_sel[COL_ESTADO] != "No aplica"].copy() if COL_ESTADO in df_sel.columns \
            else df_sel.copy()

# ── KPIs globales ──────────────────────────────────────────────────────────────
_total_global = len(df_active)
_rep_global   = int((df_active[COL_ESTADO] == "Reportado").sum()) \
                if COL_ESTADO in df_active.columns else 0
_pen_global   = int((df_active[COL_ESTADO] == "Pendiente").sum()) \
                if COL_ESTADO in df_active.columns else 0
_no_apl_global = int((df_sel[COL_ESTADO] == "No aplica").sum()) \
                 if COL_ESTADO in df_sel.columns else 0
_pct_global   = round(_rep_global / _total_global * 100, 1) if _total_global else 0

# ── Periodicidades disponibles ─────────────────────────────────────────────────
_perios_disp = sorted(df_active[COL_PERIO].dropna().unique().tolist()) \
               if COL_PERIO in df_active.columns else []

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
nombres_tabs = ["📋 Resumen", "📊 Consolidado"] + [f"📅 {p}" for p in _perios_disp]
tabs = st.tabs(nombres_tabs)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 0 — RESUMEN
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    st.markdown("<div class='section-panel'>", unsafe_allow_html=True)
    st.markdown("### Vista Resumen")

    # ── KPIs ────────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total indicadores", _total_global)
    with c2:
        st.metric("✅ Reportados", _rep_global,
                  delta=f"{_pct_global}%" if _total_global else None)
    with c3:
        st.metric("⏳ Pendientes", _pen_global,
                  delta=f"{round(_pen_global / _total_global * 100, 1)}%" if _total_global else None,
                  delta_color="inverse")
    with c4:
        st.metric("% Reporte", f"{_pct_global}%",
                  delta_color="normal" if _pct_global >= 80 else "inverse")

    st.markdown("---")

    # ── Pie + Por Periodicidad ──────────────────────────────────────────────────
    gc1, gc2 = st.columns([1, 2])
    with gc1:
        st.markdown("#### Estado general")
        if _rep_global + _pen_global > 0:
            fig_pie = go.Figure(go.Pie(
                labels=["Reportados", "Pendientes"],
                values=[_rep_global, _pen_global],
                hole=0.52,
                marker=dict(colors=[CORP["reportado"], CORP["pendiente"]],
                            line=dict(color="white", width=2)),
                textinfo="label+percent", textfont=dict(size=13),
                hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
            ))
            fig_pie.update_layout(
                height=280, showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="white",
                annotations=[dict(text=f"<b>{_total_global}</b><br>total",
                                  x=0.5, y=0.5, font_size=16, showarrow=False)],
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with gc2:
        st.markdown("#### Por Periodicidad")
        if COL_PERIO in df_active.columns:
            _per_agg = (
                df_active.groupby(COL_PERIO)[COL_ESTADO]
                .value_counts().unstack(fill_value=0).reset_index()
            )
            _per_agg.columns.name = None
            for col in ("Reportado", "Pendiente"):
                if col not in _per_agg.columns:
                    _per_agg[col] = 0
            _per_agg["Total"] = _per_agg["Reportado"] + _per_agg.get("Pendiente", 0)
            _per_agg["% Reporte"] = (
                _per_agg["Reportado"] / _per_agg["Total"].replace(0, 1) * 100
            ).round(1).astype(str) + "%"

            fig_per = go.Figure()
            fig_per.add_trace(go.Bar(
                x=_per_agg[COL_PERIO], y=_per_agg["Reportado"],
                name="Reportados", marker_color=CORP["reportado"],
                text=_per_agg["Reportado"], textposition="outside",
            ))
            if "Pendiente" in _per_agg.columns:
                fig_per.add_trace(go.Bar(
                    x=_per_agg[COL_PERIO], y=_per_agg["Pendiente"],
                    name="Pendientes", marker_color=CORP["pendiente"],
                    text=_per_agg["Pendiente"], textposition="outside",
                ))
            fig_per.update_layout(
                barmode="group", height=280,
                xaxis_title="Periodicidad", yaxis_title="Indicadores",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.35),
                margin=dict(t=15, b=80),
            )
            st.plotly_chart(fig_per, use_container_width=True)

            _cols_t = [c for c in [COL_PERIO, "Total", "Reportado", "Pendiente", "% Reporte"]
                       if c in _per_agg.columns]
            st.dataframe(_per_agg[_cols_t], use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Por Proceso ─────────────────────────────────────────────────────────────
    _COL_PROC = "Proceso"
    _KEY_SEL_PROC = "t0_sel_proc"
    _KEY_SEL_EST  = "t0_sel_est"

    if _COL_PROC in df_active.columns and COL_ESTADO in df_active.columns:
        st.markdown("#### Por Proceso")
        st.caption("💡 Haz clic en una barra para filtrar la tabla inferior.")

        proc_stats = _agg_estado(df_active, _COL_PROC)
        fig_proc   = _bar_h(proc_stats, _COL_PROC)
        ev_proc    = st.plotly_chart(fig_proc, on_select="rerun",
                                     key="t0_chart_proc", use_container_width=True)

        if ev_proc.selection and ev_proc.selection.get("points"):
            pt = ev_proc.selection["points"][0]
            _cp = pt.get("y")
            _ce = pt.get("customdata")
            if (_cp != st.session_state.get(_KEY_SEL_PROC) or
                    _ce != st.session_state.get(_KEY_SEL_EST)):
                st.session_state[_KEY_SEL_PROC] = _cp
                st.session_state[_KEY_SEL_EST]  = _ce

        sel_proc_t0 = st.session_state.get(_KEY_SEL_PROC)
        sel_est_t0  = st.session_state.get(_KEY_SEL_EST)

        if sel_proc_t0 or sel_est_t0:
            hh1, hh2 = st.columns([7, 1])
            with hh1:
                partes = []
                if sel_proc_t0: partes.append(f"Proceso: **{sel_proc_t0}**")
                if sel_est_t0:  partes.append(f"Estado: **{sel_est_t0}**")
                st.info("📊 Filtro activo: " + " · ".join(partes))
            with hh2:
                if st.button("✖ Todos", key="t0_clear_proc"):
                    st.session_state[_KEY_SEL_PROC] = None
                    st.session_state[_KEY_SEL_EST]  = None
                    st.rerun()

        # Subproceso drill-down si existe la columna
        if sel_proc_t0 and "Subproceso" in df_active.columns:
            df_drill = df_active[df_active[_COL_PROC] == sel_proc_t0]
            sub_agg = (
                df_drill.groupby("Subproceso")
                .agg(Total=(COL_ESTADO, "count"),
                     Reportados=(COL_ESTADO, lambda x: (x == "Reportado").sum()),
                     Pendientes=(COL_ESTADO, lambda x: (x == "Pendiente").sum()))
                .reset_index()
                .sort_values("Total", ascending=False)
            )
            sub_agg["% Reporte"] = (
                sub_agg["Reportados"] / sub_agg["Total"].replace(0, 1) * 100
            ).round(1).astype(str) + "%"
            st.markdown(f"**Subprocesos de {sel_proc_t0}**")
            st.dataframe(sub_agg, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Ranking sin reporte ─────────────────────────────────────────────────────
    _col_rank = _COL_PROC if _COL_PROC in df_active.columns else None
    if _col_rank and COL_ESTADO in df_active.columns:
        df_pen_r = df_active[df_active[COL_ESTADO] == "Pendiente"]
        if not df_pen_r.empty:
            st.markdown("#### 🚨 Ranking sin reporte")
            ranking = (
                df_pen_r.groupby(_col_rank).size()
                .reset_index(name="Sin reporte")
                .sort_values("Sin reporte", ascending=False)
            )
            tot_r = df_active.groupby(_col_rank).size().reset_index(name="Total")
            ranking = ranking.merge(tot_r, on=_col_rank, how="left")
            ranking["% Sin reporte"] = (
                ranking["Sin reporte"] / ranking["Total"].replace(0, 1) * 100
            ).round(1)

            cr1, cr2 = st.columns([3, 2])
            with cr1:
                fig_rank = go.Figure(go.Bar(
                    x=ranking["Sin reporte"], y=ranking[_col_rank],
                    orientation="h",
                    marker=dict(
                        color=ranking["% Sin reporte"],
                        colorscale=[[0, CORP["reportado"]], [0.5, CORP["alerta"]],
                                    [1, CORP["pendiente"]]],
                        showscale=True,
                        colorbar=dict(title="% sin<br>reporte", ticksuffix="%"),
                    ),
                    text=[f"{n}  ({p}%)" for n, p in
                          zip(ranking["Sin reporte"], ranking["% Sin reporte"])],
                    textposition="outside",
                    hovertemplate="<b>%{y}</b><br>Sin reporte: %{x}<br>%{marker.color:.1f}%<extra></extra>",
                ))
                fig_rank.update_layout(
                    height=max(300, len(ranking) * 36 + 60),
                    xaxis_title="Sin reporte",
                    yaxis=dict(title="", autorange="reversed", tickfont=dict(size=11)),
                    plot_bgcolor="white", paper_bgcolor="white",
                    margin=dict(t=10, b=40, l=10, r=80),
                )
                st.plotly_chart(fig_rank, use_container_width=True)
            with cr2:
                df_rk = ranking.rename(columns={_col_rank: "Categoría"}).copy()
                df_rk["% Sin reporte"] = df_rk["% Sin reporte"].astype(str) + "%"

                def _color_rank(row):
                    try:
                        pct = float(str(row["% Sin reporte"]).replace("%", ""))
                    except ValueError:
                        pct = 0
                    bg = "#FDE8F3" if pct >= 80 else "#FEF3D0" if pct >= 50 else "#EDF7D6"
                    return ["", f"background-color:{bg}", "", f"background-color:{bg}"]

                st.dataframe(
                    df_rk[["Categoría", "Sin reporte", "Total", "% Sin reporte"]]
                    .style.apply(_color_rank, axis=1),
                    use_container_width=True, hide_index=True,
                )
                st.download_button(
                    "📥 Exportar ranking",
                    data=exportar_excel(
                        df_rk[["Categoría", "Sin reporte", "Total", "% Sin reporte"]],
                        "Sin reporte"),
                    file_name="procesos_sin_reporte.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="exp_rank_proc",
                )
        else:
            st.success("✅ No hay indicadores pendientes de reporte en el período seleccionado.")
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — CONSOLIDADO
# ─────────────────────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown("<div class='section-panel'>", unsafe_allow_html=True)
    st.markdown("### Tabla Consolidada")
    st.caption(
        f"**{len(df_sel):,}** registros para "
        f"{_MESES_ES.get(_mes_sel_n, 'todos los meses')} {_año_sel}  "
        f"(incluye No aplica)"
    )

    # Gráfico interactivo por Proceso
    _KEY_CON_P = "con_sel_proc"
    _KEY_CON_E = "con_sel_est"

    if _COL_PROC in df_active.columns:
        st.markdown("#### Por Proceso")
        st.caption("💡 Haz clic en una barra para filtrar la tabla.")
        vs_con = _agg_estado(df_active, _COL_PROC)
        fig_con = _bar_h(vs_con, _COL_PROC)
        ev_con  = st.plotly_chart(fig_con, use_container_width=True,
                                  on_select="rerun", key="con_chart_proc")

        if ev_con.selection and ev_con.selection.get("points"):
            pt = ev_con.selection["points"][0]
            _cp, _ce = pt.get("y"), pt.get("customdata")
            if (_cp != st.session_state.get(_KEY_CON_P) or
                    _ce != st.session_state.get(_KEY_CON_E)):
                st.session_state[_KEY_CON_P] = _cp
                st.session_state[_KEY_CON_E] = _ce

        sel_con_p = st.session_state.get(_KEY_CON_P)
        sel_con_e = st.session_state.get(_KEY_CON_E)
        if sel_con_p or sel_con_e:
            hv1, hv2 = st.columns([7, 1])
            with hv1:
                partes = []
                if sel_con_p: partes.append(f"Proceso: **{sel_con_p}**")
                if sel_con_e: partes.append(f"Estado: **{sel_con_e}**")
                st.info("📊 Filtro activo: " + " · ".join(partes))
            with hv2:
                if st.button("✖ Todos", key="con_clear"):
                    st.session_state[_KEY_CON_P] = None
                    st.session_state[_KEY_CON_E] = None
                    st.rerun()
        st.markdown("---")

    df_con_base = df_sel.copy()
    _sel_con_p = st.session_state.get(_KEY_CON_P)
    _sel_con_e = st.session_state.get(_KEY_CON_E)
    if _sel_con_p and _COL_PROC in df_con_base.columns:
        df_con_base = df_con_base[df_con_base[_COL_PROC] == _sel_con_p]
    if _sel_con_e and COL_ESTADO in df_con_base.columns:
        df_con_base = df_con_base[df_con_base[COL_ESTADO] == _sel_con_e]

    fid, fnom, fproc, fest = _filtros_tabla_ui(df_con_base, "con")
    df_con_fil = _aplicar_filtros_tabla(df_con_base, fid, fnom, fproc, fest)
    st.caption(f"Mostrando **{len(df_con_fil):,}** de **{len(df_sel):,}** registros")

    _DISPLAY_CON = ["Id", "Indicador", "Proceso", "Subproceso", COL_PERIO,
                    "Año", "Mes_Nombre", "Periodo", COL_ESTADO, COL_FUENTE,
                    "Tipo", "Sentido"]
    cols_con = _cols_pres(df_con_fil, _DISPLAY_CON) or list(df_con_fil.columns)[:12]
    df_tabla_con = df_con_fil[cols_con].copy()

    col_cfg_con = {}
    if "Indicador" in df_tabla_con.columns:
        col_cfg_con["Indicador"] = st.column_config.TextColumn("Indicador", width="large")
    if COL_ESTADO in df_tabla_con.columns:
        col_cfg_con[COL_ESTADO] = st.column_config.TextColumn("Estado", width="medium")

    st.dataframe(
        df_tabla_con.style.apply(_estilo_estado, axis=1),
        use_container_width=True, hide_index=True,
        column_config=col_cfg_con,
    )
    st.download_button(
        "📥 Exportar Excel",
        data=exportar_excel(df_tabla_con, "Consolidado"),
        file_name="seguimiento_consolidado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="exp_consolidado",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS DE PERIODICIDAD (tabs[2+])
# ─────────────────────────────────────────────────────────────────────────────
for tab_idx, perio_nombre in enumerate(_perios_disp, 2):
    df_p = df_active[df_active[COL_PERIO] == perio_nombre].copy()

    with tabs[tab_idx]:
        st.markdown("<div class='section-panel'>", unsafe_allow_html=True)
        st.markdown(f"### {perio_nombre}")

        if df_p.empty:
            st.info(f"No hay indicadores **{perio_nombre}** con período aplicable "
                    f"en {_MESES_ES.get(_mes_sel_n, str(_año_sel))} {_año_sel}.")
            continue

        # KPIs
        n_tot_p = len(df_p)
        n_rep_p = int((df_p[COL_ESTADO] == "Reportado").sum())
        n_pen_p = int((df_p[COL_ESTADO] == "Pendiente").sum())
        pct_p   = round(n_rep_p / n_tot_p * 100, 1) if n_tot_p else 0

        kc1, kc2, kc3, kc4 = st.columns(4)
        with kc1: st.metric("Total indicadores", n_tot_p)
        with kc2: st.metric("✅ Reportados", n_rep_p, delta=f"{pct_p}%")
        with kc3: st.metric("⏳ Pendientes", n_pen_p,
                            delta=f"{round(n_pen_p / n_tot_p * 100, 1)}%" if n_tot_p else None,
                            delta_color="inverse")
        with kc4: st.metric("% Reporte", f"{pct_p}%",
                            delta_color="normal" if pct_p >= 80 else "inverse")

        # Gráfico por Proceso
        _key_chart_p = f"chart_{perio_nombre}"
        _key_sel_p   = f"sel_proc_{perio_nombre}"
        _key_sel_ep  = f"sel_est_{perio_nombre}"

        if _COL_PROC in df_p.columns:
            proc_p_stats = _agg_estado(df_p, _COL_PROC)
            if not proc_p_stats.empty:
                fig_pg = _bar_h(proc_p_stats, _COL_PROC)
                ev_pg  = st.plotly_chart(fig_pg, use_container_width=True,
                                         on_select="rerun", key=_key_chart_p)
                if ev_pg.selection and ev_pg.selection.get("points"):
                    pt = ev_pg.selection["points"][0]
                    _cp, _ce = pt.get("y"), pt.get("customdata")
                    if (_cp != st.session_state.get(_key_sel_p) or
                            _ce != st.session_state.get(_key_sel_ep)):
                        st.session_state[_key_sel_p]  = _cp
                        st.session_state[_key_sel_ep] = _ce

        st.markdown("---")
        chart_proc_p = st.session_state.get(_key_sel_p)
        chart_est_p  = st.session_state.get(_key_sel_ep)

        if chart_proc_p or chart_est_p:
            hc1, hc2 = st.columns([7, 1])
            with hc1:
                partes = []
                if chart_proc_p: partes.append(f"Proceso: *{chart_proc_p}*")
                if chart_est_p:  partes.append(f"Estado: **{chart_est_p}**")
                st.markdown(f"#### Detalle — {' · '.join(partes)}")
            with hc2:
                if st.button("✖ Todos", key=f"clear_{perio_nombre}"):
                    st.session_state[_key_sel_p]  = None
                    st.session_state[_key_sel_ep] = None
                    st.rerun()
        else:
            st.markdown("#### Detalle de Indicadores")
            st.caption("💡 Haz clic en una barra para filtrar por proceso y estado.")

        df_p_base = df_p.copy()
        if chart_proc_p and _COL_PROC in df_p_base.columns:
            df_p_base = df_p_base[df_p_base[_COL_PROC] == chart_proc_p]
        if chart_est_p and COL_ESTADO in df_p_base.columns:
            df_p_base = df_p_base[df_p_base[COL_ESTADO] == chart_est_p]

        fid_p, fnom_p, fproc_p, fest_p = _filtros_tabla_ui(df_p_base, f"p_{perio_nombre}")
        df_p_fil = _aplicar_filtros_tabla(df_p_base, fid_p, fnom_p, fproc_p, fest_p)
        st.caption(f"Mostrando **{len(df_p_fil):,}** de **{n_tot_p}** indicadores")

        _DISPLAY_P = ["Id", "Indicador", "Proceso", "Subproceso",
                      "Periodo", COL_ESTADO, COL_FUENTE, "Tipo", "Sentido"]
        cols_p_show = _cols_pres(df_p_fil, _DISPLAY_P) or list(df_p_fil.columns)[:10]
        df_tabla_p  = df_p_fil[cols_p_show].copy()

        col_cfg_p = {}
        if "Indicador" in df_tabla_p.columns:
            col_cfg_p["Indicador"] = st.column_config.TextColumn("Indicador", width="large")
        if COL_ESTADO in df_tabla_p.columns:
            col_cfg_p[COL_ESTADO] = st.column_config.TextColumn("Estado", width="medium")

        event_p = st.dataframe(
            df_tabla_p.style.apply(_estilo_estado, axis=1),
            use_container_width=True, hide_index=True,
            column_config=col_cfg_p,
            on_select="rerun", selection_mode="single-row",
            key=f"tabla_{perio_nombre}",
        )

        # Panel de detalle al clic en fila
        if event_p and event_p.selection and event_p.selection.get("rows"):
            idx_sel    = event_p.selection["rows"][0]
            fila       = df_tabla_p.iloc[idx_sel]
            id_ind     = str(fila.get("Id", ""))
            col_nom    = _col_nombre(df_tabla_p)
            nombre_ind = str(fila.get(col_nom, "")) if col_nom else ""
            proceso_i  = str(fila.get("Proceso", "—"))
            estado_i   = str(fila.get(COL_ESTADO, "—"))
            fuente_i   = str(fila.get(COL_FUENTE, "—"))
            badge_c    = COLOR_ESTADO.get(estado_i, "#9E9E9E")

            @st.dialog(f"{id_ind} — {nombre_ind[:60]}", width="large")
            def _panel_detalle_p():
                st.markdown(
                    f"**Proceso:** {proceso_i}  \n"
                    f"**Subproceso:** {fila.get('Subproceso', '—')}  \n"
                    f"**Tipo:** {fila.get('Tipo', '—')} &nbsp;|&nbsp; "
                    f"**Sentido:** {fila.get('Sentido', '—')}"
                )
                st.markdown(
                    f"<span style='background:{badge_c};padding:4px 14px;"
                    f"border-radius:12px'>"
                    f"<b>Estado: {estado_i}</b>"
                    f"</span> &nbsp; Fuente: <b>{fuente_i}</b>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")
                # Histórico del indicador en el tracking
                hist = df_tracking[df_tracking["Id"] == id_ind].sort_values(
                    ["Año", "Mes"]) if "Id" in df_tracking.columns else pd.DataFrame()
                if not hist.empty:
                    st.markdown("**Histórico de períodos**")
                    _hist_cols = _cols_pres(hist, ["Periodo", "Año", "Mes_Nombre",
                                                    COL_ESTADO, COL_FUENTE])
                    st.dataframe(
                        hist[_hist_cols].style.apply(_estilo_estado, axis=1),
                        use_container_width=True, hide_index=True,
                    )
                st.markdown("---")
                st.markdown("**Ficha técnica**")
                for fc in ["Id", "Indicador", "Proceso", "Subproceso",
                           "Periodicidad", "Tipo", "Sentido"]:
                    if fc in fila.index and pd.notna(fila.get(fc)):
                        st.markdown(f"- **{fc}:** {fila.get(fc, '—')}")

            _panel_detalle_p()

        st.download_button(
            f"📥 Exportar {perio_nombre}",
            data=exportar_excel(df_tabla_p, perio_nombre[:31]),
            file_name=f"seguimiento_{perio_nombre.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"exp_{perio_nombre}",
        )
        st.markdown("</div>", unsafe_allow_html=True)
