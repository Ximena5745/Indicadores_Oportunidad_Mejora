"""
pages/3_Acciones_de_Mejora.py — Oportunidades de Mejora.

Mejoras:
  · Badge numérico en tab Retrasadas
  · Organización del Tab Análisis en sub-secciones
  · Scatter con Id y Descripción en hover
  · Tasa de cierre en plazo como KPI
  · Filtro compartido (Proceso) entre Tab Análisis y Tab Información
"""
import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import cargar_om, cargar_plan_accion
from utils.charts import exportar_excel
from config import COLORES

# ── Paleta ─────────────────────────────────────────────────────────────────────
_C = {
    "Cerrada":   COLORES["cumplimiento"],
    "Ejecución": "#1976D2",
    "Abierta":   COLORES["alerta"],
    "Retrasada": COLORES["peligro"],
    "primary":   COLORES["primario"],
    "light":     "#E3EAF4",
}

# ── Carga ──────────────────────────────────────────────────────────────────────
st.markdown("# 📋 Oportunidades de Mejora")
st.caption("Fuente: **OM.xlsx** · Plan de Acción consolidado")
st.markdown("---")

df_om = cargar_om()
df_pa = cargar_plan_accion()

if df_om.empty:
    st.error("No se encontró **OM.xlsx** en `data/raw/`.")
    st.stop()

# ── Detectar columnas clave ────────────────────────────────────────────────────
_COL_AV       = next((c for c in df_om.columns if "avance"           in c.lower()), None)
_COL_ESTADO   = next((c for c in df_om.columns if c.lower() == "estado"),           None)
_COL_DIAS     = next((c for c in df_om.columns if "días vencida"    in c.lower()
                                               or "dias vencida"    in c.lower()), None)
_COL_MESES    = next((c for c in df_om.columns if "meses sin"       in c.lower()), None)
_COL_PROC     = next((c for c in df_om.columns if c.lower() == "procesos"),        None)
_COL_FUENTE   = next((c for c in df_om.columns if c.lower() == "fuente"),          None)
_COL_TIPO_O   = next((c for c in df_om.columns if "tipo de oportunidad" in c.lower()), None)
_COL_TIPO_A   = next((c for c in df_om.columns if "tipo de acción"  in c.lower()
                                               or "tipo de accion"  in c.lower()), None)
_COL_FECHA_ID = next((c for c in df_om.columns if "identificación"  in c.lower()
                                               or "identificacion"  in c.lower()), None)
_COL_FECHA_EST = next((c for c in df_om.columns if "estimada" in c.lower() and "cierre" in c.lower()), None)
_COL_FECHA_REAL= next((c for c in df_om.columns if "real"     in c.lower() and "cierre" in c.lower()), None)
_COL_DESC     = next((c for c in df_om.columns if "descrip"         in c.lower()), None)

_COL_PA_ID    = next((c for c in df_pa.columns if "id oportunidad"         in c.lower()), None) if not df_pa.empty else None
_COL_FECHA_LIM= next((c for c in df_pa.columns if "fecha límite de ejecución" in c.lower()
                                               or "fecha limite de ejecucion" in c.lower()), None) if not df_pa.empty else None
_COL_ESTADO_PA= next((c for c in df_pa.columns if "estado (plan"            in c.lower()), None) if not df_pa.empty else None
_COL_PROC_RESP= next((c for c in df_pa.columns if "proceso responsable"     in c.lower()), None) if not df_pa.empty else None

# ── Pre-calcular retrasadas (necesario antes de st.tabs) ──────────────────────
hoy = pd.Timestamp(datetime.date.today())
n_retrasadas = 0
if not df_pa.empty and _COL_FECHA_LIM and _COL_ESTADO_PA:
    mask_ret = (
        pd.to_datetime(df_pa[_COL_FECHA_LIM], errors="coerce") < hoy
    ) & (
        df_pa[_COL_ESTADO_PA].astype(str).str.strip() != "Ejecutado"
    )
    n_retrasadas = int(mask_ret.sum())

# ── Tasa de cierre en plazo ────────────────────────────────────────────────────
def _tasa_cierre_plazo(df, col_estado, col_fecha_est, col_fecha_real):
    if not all([col_estado, col_fecha_est, col_fecha_real]):
        return None, None, None
    df_cerr = df[df[col_estado] == "Cerrada"].copy()
    if df_cerr.empty:
        return 0, 0, None
    f_est  = pd.to_datetime(df_cerr[col_fecha_est],  errors="coerce")
    f_real = pd.to_datetime(df_cerr[col_fecha_real], errors="coerce")
    validos = f_est.notna() & f_real.notna()
    if not validos.any():
        return len(df_cerr), 0, None
    n_a_tiempo = int((f_real[validos] <= f_est[validos]).sum())
    n_tarde    = int(validos.sum()) - n_a_tiempo
    pct        = round(n_a_tiempo / validos.sum() * 100, 1) if validos.any() else None
    return n_a_tiempo, n_tarde, pct


n_atiempo, n_tarde, pct_plazo = _tasa_cierre_plazo(
    df_om, _COL_ESTADO, _COL_FECHA_EST, _COL_FECHA_REAL
)

# ── KPIs ───────────────────────────────────────────────────────────────────────
total        = len(df_om)
cnt_cerradas = int((df_om[_COL_ESTADO] == "Cerrada").sum()) if _COL_ESTADO else 0
cnt_abiertas = total - cnt_cerradas
avance_prom  = float(df_om[_COL_AV].mean())                  if _COL_AV    else 0.0
cnt_vencidas = int((df_om[_COL_DIAS] > 0).sum())             if _COL_DIAS  else 0
cnt_pa       = len(df_pa)

k = st.columns(6)
k[0].metric("Total OM",         total)
k[1].metric("Abiertas",         cnt_abiertas)
k[2].metric("Cerradas",         cnt_cerradas)
k[3].metric("Avance promedio",  f"{avance_prom:.1f}%")
k[4].metric("OM vencidas",      cnt_vencidas)
k[5].metric("Acciones de plan", cnt_pa)

# Fila secundaria: cierre en plazo
if pct_plazo is not None:
    st.markdown(
        f"""<div style="background:#E8F5E9;border-radius:6px;padding:8px 16px;
            border-left:3px solid #43A047;margin-top:6px;font-size:0.9rem;">
            ✅ <b>Eficacia de cierre:</b> {pct_plazo}% de las OM se cerraron dentro del plazo estimado
            &nbsp;·&nbsp; {n_atiempo} a tiempo · {n_tarde} con retraso
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Filtros ────────────────────────────────────────────────────────────────────
def _opts(df, col):
    if col is None or col not in df.columns:
        return [""]
    return [""] + sorted(df[col].dropna().astype(str).unique().tolist())

with st.expander("🔍 Filtros", expanded=True):
    fc = st.columns(5)
    f_estado = fc[0].selectbox("Estado",           _opts(df_om, _COL_ESTADO),
                               key="om_estado", format_func=lambda x: "— Todos —" if x == "" else x)
    f_tipo_a = fc[1].selectbox("Tipo de acción",   _opts(df_om, _COL_TIPO_A),
                               key="om_tipo_a", format_func=lambda x: "— Todos —" if x == "" else x)
    f_tipo_o = fc[2].selectbox("Tipo oportunidad", _opts(df_om, _COL_TIPO_O),
                               key="om_tipo_o", format_func=lambda x: "— Todos —" if x == "" else x)
    f_proc   = fc[3].selectbox("Proceso",          _opts(df_om, _COL_PROC),
                               key="om_proc",   format_func=lambda x: "— Todos —" if x == "" else x)
    f_fuente = fc[4].selectbox("Fuente",           _opts(df_om, _COL_FUENTE),
                               key="om_fuente", format_func=lambda x: "— Todos —" if x == "" else x)

df_f = df_om.copy()
if f_estado and _COL_ESTADO: df_f = df_f[df_f[_COL_ESTADO] == f_estado]
if f_tipo_a and _COL_TIPO_A: df_f = df_f[df_f[_COL_TIPO_A] == f_tipo_a]
if f_tipo_o and _COL_TIPO_O: df_f = df_f[df_f[_COL_TIPO_O] == f_tipo_o]
if f_proc   and _COL_PROC:   df_f = df_f[df_f[_COL_PROC]   == f_proc]
if f_fuente and _COL_FUENTE: df_f = df_f[df_f[_COL_FUENTE] == f_fuente]

# ── Session state para filtro compartido entre tabs ────────────────────────────
if "om_filtro_proceso_tab" not in st.session_state:
    st.session_state["om_filtro_proceso_tab"] = None

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_anal, tab_info, tab_ret = st.tabs([
    "📊 Análisis",
    "📋 Información",
    f"⚠️ Retrasadas ({n_retrasadas})" if n_retrasadas > 0 else "✅ Retrasadas (0)",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANÁLISIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_anal:
    if df_f.empty:
        st.info("Sin datos con los filtros aplicados.")
    else:
        # ── SECCIÓN: Estado y Origen ──────────────────────────────────────────
        st.markdown("#### Estado y Origen")
        row1 = st.columns(2)

        with row1[0]:
            if _COL_ESTADO:
                cnt_e = df_f[_COL_ESTADO].value_counts().reset_index()
                cnt_e.columns = ["Estado", "N"]
                fig = go.Figure(go.Pie(
                    labels=cnt_e["Estado"],
                    values=cnt_e["N"],
                    hole=0.55,
                    marker_colors=[_C.get(e, _C["primary"]) for e in cnt_e["Estado"]],
                    textinfo="label+percent",
                    hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
                ))
                fig.update_layout(
                    title="Distribución por Estado",
                    showlegend=True, height=320,
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)

        with row1[1]:
            if _COL_FUENTE:
                cnt_f = df_f[_COL_FUENTE].value_counts().reset_index()
                cnt_f.columns = ["Fuente", "N"]
                fig = px.bar(
                    cnt_f.sort_values("N"),
                    x="N", y="Fuente", orientation="h",
                    color_discrete_sequence=[_C["primary"]],
                    text="N", title="OM por Fuente",
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(
                    height=320, margin=dict(l=10, r=40, t=50, b=10),
                    yaxis_title="", xaxis_title="Cantidad",
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        # ── SECCIÓN: Avance por Proceso ───────────────────────────────────────
        st.markdown("#### Avance por Proceso")
        row2 = st.columns(2)

        with row2[0]:
            if _COL_PROC and _COL_AV:
                av_proc = (
                    df_f.groupby(_COL_PROC)[_COL_AV]
                    .mean().reset_index()
                    .rename(columns={_COL_AV: "Avance promedio"})
                    .sort_values("Avance promedio")
                )
                av_proc["color"] = av_proc["Avance promedio"].apply(
                    lambda v: _C["Retrasada"] if v < 30 else _C["Abierta"] if v < 70 else _C["Cerrada"]
                )
                fig = go.Figure(go.Bar(
                    x=av_proc["Avance promedio"],
                    y=av_proc[_COL_PROC],
                    orientation="h",
                    marker_color=av_proc["color"],
                    text=av_proc["Avance promedio"].apply(lambda v: f"{v:.1f}%"),
                    textposition="outside",
                    customdata=av_proc[_COL_PROC].tolist(),
                    hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
                ))
                fig.update_layout(
                    title="Avance promedio por Proceso",
                    xaxis=dict(range=[0, 115], title="Avance (%)"),
                    yaxis_title="",
                    height=max(300, len(av_proc) * 32 + 80),
                    margin=dict(l=10, r=50, t=50, b=10),
                )
                ev_avproc = st.plotly_chart(fig, use_container_width=True,
                                            on_select="rerun", key="fig_av_proc")
                if ev_avproc and ev_avproc.selection and ev_avproc.selection.get("points"):
                    proc_click = ev_avproc.selection["points"][0].get("y")
                    if proc_click:
                        st.session_state["om_filtro_proceso_tab"] = proc_click
                        st.rerun()

        with row2[1]:
            if _COL_TIPO_O:
                cnt_to = df_f[_COL_TIPO_O].value_counts().reset_index()
                cnt_to.columns = ["Tipo", "N"]
                fig = px.bar(
                    cnt_to.sort_values("N"),
                    x="N", y="Tipo", orientation="h",
                    color_discrete_sequence=["#1976D2"],
                    text="N", title="OM por Tipo de Oportunidad",
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(
                    height=max(300, len(cnt_to) * 32 + 80),
                    margin=dict(l=10, r=40, t=50, b=10),
                    yaxis_title="", xaxis_title="Cantidad",
                )
                st.plotly_chart(fig, use_container_width=True)

        # Estado por Proceso (barras apiladas)
        if _COL_PROC and _COL_ESTADO:
            pivot = (df_f.groupby([_COL_PROC, _COL_ESTADO]).size()
                     .reset_index(name="N"))
            estados = pivot[_COL_ESTADO].unique().tolist()
            fig = go.Figure()
            for est in estados:
                sub = pivot[pivot[_COL_ESTADO] == est]
                fig.add_trace(go.Bar(
                    name=est, x=sub[_COL_PROC], y=sub["N"],
                    marker_color=_C.get(est, _C["primary"]),
                    hovertemplate=f"{est}: %{{y}}<extra></extra>",
                ))
            fig.update_layout(
                barmode="stack", title="Estado de OM por Proceso",
                xaxis_title="", yaxis_title="N° OM",
                xaxis_tickangle=-35, height=380,
                margin=dict(l=10, r=10, t=50, b=120),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        # ── SECCIÓN: Evolución Temporal ───────────────────────────────────────
        st.markdown("#### Evolución Temporal")

        if _COL_PROC and _COL_FECHA_ID and _COL_FECHA_ID in df_f.columns:
            df_hm = df_f[[_COL_PROC, _COL_FECHA_ID]].copy()
            df_hm["_fecha"] = pd.to_datetime(df_hm[_COL_FECHA_ID], errors="coerce")
            df_hm["Mes"]    = df_hm["_fecha"].dt.to_period("M")
            df_hm = df_hm.dropna(subset=["Mes", _COL_PROC])
            if not df_hm.empty:
                pivot_hm = (df_hm.groupby([_COL_PROC, "Mes"])
                            .size().reset_index(name="N"))
                pivot_hm["Mes_str"] = pivot_hm["Mes"].astype(str)
                hm = (pivot_hm.pivot(index=_COL_PROC, columns="Mes_str", values="N").fillna(0))
                hm = hm[sorted(hm.columns)]
                fig = go.Figure(go.Heatmap(
                    z=hm.values, x=hm.columns.tolist(), y=hm.index.tolist(),
                    colorscale=[[0,"#F5F5F5"],[0.01,"#FFF9C4"],[0.4,"#FBAF17"],[1,"#D32F2F"]],
                    text=hm.values.astype(int), texttemplate="%{text}",
                    hovertemplate="Proceso: %{y}<br>Mes: %{x}<br>OM: %{z}<extra></extra>",
                    showscale=True, zmin=0,
                ))
                fig.update_layout(
                    title="Concentración de OM: Proceso × Mes de identificación",
                    xaxis_title="Mes", yaxis_title="",
                    xaxis_tickangle=-45,
                    height=max(350, len(hm) * 30 + 100),
                    margin=dict(l=10, r=10, t=50, b=90),
                )
                st.plotly_chart(fig, use_container_width=True)

        if _COL_FECHA_ID and _COL_FECHA_ID in df_f.columns:
            df_tl_base = df_f.copy()
            df_tl_base["_fecha"] = pd.to_datetime(df_tl_base[_COL_FECHA_ID], errors="coerce")
            df_tl_base = df_tl_base.dropna(subset=["_fecha"])
            if not df_tl_base.empty:
                fecha_min = df_tl_base["_fecha"].min().date()
                fecha_max = df_tl_base["_fecha"].max().date()
                tl_c1, tl_c2, _ = st.columns([1, 1, 3])
                rng_ini = tl_c1.date_input("Desde", value=fecha_min,
                                           min_value=fecha_min, max_value=fecha_max, key="tl_desde")
                rng_fin = tl_c2.date_input("Hasta", value=fecha_max,
                                           min_value=fecha_min, max_value=fecha_max, key="tl_hasta")
                mask_rng = (
                    (df_tl_base["_fecha"].dt.date >= rng_ini)
                    & (df_tl_base["_fecha"].dt.date <= rng_fin)
                )
                df_tl = df_tl_base[mask_rng].copy()
                if df_tl.empty:
                    st.info("Sin datos en el rango de fechas seleccionado.")
                else:
                    df_tl["Mes"] = df_tl["_fecha"].dt.to_period("M")
                    tl = (df_tl.groupby("Mes").size()
                          .reset_index(name="N").sort_values("Mes"))
                    tl["Mes_str"] = tl["Mes"].astype(str)
                    fig = go.Figure(go.Scatter(
                        x=tl["Mes_str"], y=tl["N"],
                        mode="lines+markers+text",
                        text=tl["N"], textposition="top center",
                        line=dict(color=_C["primary"], width=2),
                        marker=dict(size=8, color=_C["primary"]),
                        fill="tozeroy", fillcolor="rgba(26,58,92,0.12)",
                        hovertemplate="Mes %{x}: %{y} OM<extra></extra>",
                    ))
                    fig.update_layout(
                        title=f"OM identificadas por mes  ·  {rng_ini:%b %Y} → {rng_fin:%b %Y}",
                        xaxis_title="Mes", yaxis_title="N° OM",
                        height=300, margin=dict(l=10, r=10, t=50, b=40),
                    )
                    st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        # ── SECCIÓN: Diagnóstico de Retrasos ─────────────────────────────────
        st.markdown("#### Diagnóstico de Retrasos")

        if _COL_AV and _COL_DIAS and _COL_PROC:
            cols_sc = [_COL_PROC, _COL_AV, _COL_DIAS]
            if "Id" in df_f.columns:      cols_sc.append("Id")
            if _COL_DESC and _COL_DESC in df_f.columns: cols_sc.append(_COL_DESC)

            df_sc = df_f[cols_sc].dropna(subset=[_COL_AV, _COL_DIAS]).copy()
            if not df_sc.empty:
                hover_extra = {}
                if "Id" in df_sc.columns:        hover_extra["Id"]         = True
                if _COL_DESC in df_sc.columns:   hover_extra[_COL_DESC]    = True

                fig = px.scatter(
                    df_sc,
                    x=_COL_DIAS, y=_COL_AV,
                    color=_COL_PROC,
                    hover_data=hover_extra or [_COL_PROC],
                    title="Avance vs Días Vencida por Proceso",
                    labels={_COL_DIAS: "Días vencida", _COL_AV: "Avance (%)"},
                    height=380,
                )
                fig.add_vline(x=0, line_dash="dash", line_color="gray",
                              annotation_text="Vence hoy", annotation_position="top right")
                fig.update_layout(margin=dict(l=10, r=10, t=50, b=30))
                st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — INFORMACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
with tab_info:
    _COLS_OM = [
        "Id", "Fecha de identificación", "Avance (%)", "Estado",
        "Tipo de acción", "Tipo de oportunidad", "Procesos", "Fuente",
        "Descripción", "Fecha de creación",
        "Fecha estimada de cierre", "Fecha real de cierre",
        "Días vencida", "Meses sin avance", "Comentario",
    ]
    _COLS_PA = [
        "Id Acción", "Fecha creación", "Clasificación", "Avance (%)",
        "Estado (Plan de Acción)", "Estado (Oportunidad de mejora)", "Aprobado",
        "Comentario", "Id Oportunidad de mejora", "Descripción", "Acción",
        "Proceso responsable", "Responsable de ejecución", "Fecha límite de ejecución",
        "Responsable de seguimiento", "Fecha límite de seguimiento",
        "Responsable de evaluación", "Fuente de Identificación",
        "Fecha límite de evaluación", "Última ejecución", "Último seguimiento",
    ]

    # Filtro compartido desde Tab Análisis
    filtro_proc_tab = st.session_state.get("om_filtro_proceso_tab")
    if filtro_proc_tab and _COL_PROC:
        fpt1, fpt2 = st.columns([7, 1])
        with fpt1:
            st.info(f"📊 Filtro desde Análisis: **{filtro_proc_tab}** (proceso)")
        with fpt2:
            if st.button("✖", key="clear_filtro_tab"):
                st.session_state["om_filtro_proceso_tab"] = None
                st.rerun()
        df_info = df_f[df_f[_COL_PROC] == filtro_proc_tab].copy() if _COL_PROC in df_f.columns else df_f.copy()
    else:
        df_info = df_f.copy()

    cols_show = [c for c in _COLS_OM if c in df_info.columns]
    df_tabla  = df_info[cols_show].copy()

    if _COL_AV and _COL_AV in df_tabla.columns:
        df_tabla[_COL_AV] = df_tabla[_COL_AV].apply(
            lambda v: f"{v:.1f}%" if pd.notna(v) else "—"
        )
    for _fc in ["Fecha de identificación", "Fecha de creación",
                "Fecha estimada de cierre", "Fecha real de cierre"]:
        if _fc in df_tabla.columns:
            df_tabla[_fc] = (pd.to_datetime(df_tabla[_fc], errors="coerce")
                              .dt.strftime("%d/%m/%Y").fillna("—"))

    st.caption(
        f"Mostrando **{len(df_tabla)}** oportunidades — "
        "selecciona una fila para ver el Plan de Acción"
    )
    ev = st.dataframe(
        df_tabla, use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row",
        column_config={
            "Descripción":         st.column_config.TextColumn("Descripción",      width="large"),
            "Comentario":          st.column_config.TextColumn("Comentario",       width="medium"),
            "Procesos":            st.column_config.TextColumn("Procesos",         width="medium"),
            "Tipo de oportunidad": st.column_config.TextColumn("Tipo oportunidad", width="medium"),
            "Días vencida":        st.column_config.NumberColumn("Días vencida",   format="%d"),
            "Meses sin avance":    st.column_config.NumberColumn("Meses sin avance", format="%d"),
        },
    )
    st.download_button(
        "📥 Exportar Oportunidades (Excel)",
        data=exportar_excel(df_tabla, "Oportunidades_de_Mejora"),
        file_name="oportunidades_mejora.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="exp_om",
    )

    if ev.selection and ev.selection.rows:
        row_om = df_info.iloc[ev.selection.rows[0]]
        om_id  = str(row_om.get("Id", "")).strip()

        st.markdown(f"### 📌 Plan de Acción — OM **{om_id}**")

        with st.expander("📄 Detalle de la Oportunidad", expanded=True):
            d1, d2, d3 = st.columns(3)
            d1.write(f"**Tipo de acción:** {row_om.get('Tipo de acción', '—')}")
            d1.write(f"**Tipo de oportunidad:** {row_om.get('Tipo de oportunidad', '—')}")
            d2.write(f"**Proceso:** {row_om.get('Procesos', '—')}")
            d2.write(f"**Fuente:** {row_om.get('Fuente', '—')}")
            d3.write(f"**Estado:** {row_om.get('Estado', '—')}")
            d3.write(f"**Avance:** {row_om.get(_COL_AV, '—') if _COL_AV else '—'}")
            if _COL_DESC:
                st.write(f"**Descripción:** {row_om.get(_COL_DESC, '—')}")
            st.write(f"**Comentario:** {row_om.get('Comentario', '—')}")

        if df_pa.empty or _COL_PA_ID is None:
            st.info("Sin datos de Plan de Acción disponibles.")
        else:
            df_plan = df_pa[df_pa[_COL_PA_ID].astype(str) == om_id].copy()
            if df_plan.empty:
                st.info(f"No hay acciones en el Plan de Acción para la OM **{om_id}**.")
            else:
                cols_pa_show = [c for c in _COLS_PA if c in df_plan.columns]
                df_ps = df_plan[cols_pa_show].copy()
                for col in df_ps.select_dtypes(include="datetime").columns:
                    df_ps[col] = df_ps[col].dt.strftime("%d/%m/%Y").fillna("—")
                col_av_pa = next((c for c in df_ps.columns if "avance" in c.lower()), None)
                if col_av_pa:
                    df_ps[col_av_pa] = df_ps[col_av_pa].apply(
                        lambda v: f"{v:.1f}%" if pd.notna(v) else "—"
                    )
                st.caption(f"**{len(df_ps)}** acción(es) asociada(s)")
                st.dataframe(df_ps, use_container_width=True, hide_index=True,
                             column_config={
                                 "Descripción": st.column_config.TextColumn("Descripción", width="large"),
                                 "Acción":      st.column_config.TextColumn("Acción",      width="large"),
                             })
                st.download_button(
                    "📥 Exportar Plan de Acción (Excel)",
                    data=exportar_excel(df_ps, f"Plan_OM_{om_id}"),
                    file_name=f"plan_accion_om_{om_id}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="exp_pa",
                )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RETRASADAS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_ret:
    if df_pa.empty or not all([_COL_PA_ID, _COL_FECHA_LIM, _COL_ESTADO_PA, _COL_PROC_RESP]):
        st.warning(
            "Faltan columnas en el Plan de Acción: "
            "`Proceso responsable`, `Fecha límite de ejecución`, `Estado (Plan de Acción)`."
        )
    else:
        mask_ret = (
            pd.to_datetime(df_pa[_COL_FECHA_LIM], errors="coerce") < hoy
        ) & (
            df_pa[_COL_ESTADO_PA].astype(str).str.strip() != "Ejecutado"
        )
        df_ret = df_pa[mask_ret].copy()

        r1, r2, r3 = st.columns(3)
        r1.metric("Acciones retrasadas",  len(df_ret))
        r2.metric("Procesos afectados",
                  df_ret[_COL_PROC_RESP].nunique() if not df_ret.empty else 0)
        if _COL_FECHA_LIM and not df_ret.empty:
            dias_max = int(
                (hoy - pd.to_datetime(df_ret[_COL_FECHA_LIM], errors="coerce").min()).days
            )
            r3.metric("Días máx. de retraso", dias_max)

        st.markdown("---")

        if df_ret.empty:
            st.success("✅ No hay acciones retrasadas en el Plan de Acción.")
        else:
            resumen = (
                df_ret.groupby(_COL_PROC_RESP)
                .size().reset_index(name="Acciones retrasadas")
                .sort_values("Acciones retrasadas", ascending=False)
            )
            col_g, col_t = st.columns([3, 2])
            with col_g:
                fig = go.Figure(go.Bar(
                    x=resumen["Acciones retrasadas"],
                    y=resumen[_COL_PROC_RESP],
                    orientation="h",
                    marker_color=_C["Retrasada"],
                    text=resumen["Acciones retrasadas"],
                    textposition="outside",
                    hovertemplate="%{y}: %{x} acciones<extra></extra>",
                ))
                fig.update_layout(
                    title=f"Acciones retrasadas por Proceso ({len(df_ret)} total)",
                    xaxis_title="N° acciones",
                    yaxis={"categoryorder": "total ascending"},
                    height=max(300, len(resumen) * 35 + 80),
                    margin=dict(l=10, r=50, t=50, b=30),
                )
                st.plotly_chart(fig, use_container_width=True)
            with col_t:
                st.dataframe(resumen, use_container_width=True, hide_index=True)

            if _COL_ESTADO_PA:
                cnt_est_ret = df_ret[_COL_ESTADO_PA].value_counts().reset_index()
                cnt_est_ret.columns = ["Estado", "N"]
                fig2 = px.pie(
                    cnt_est_ret, names="Estado", values="N", hole=0.5,
                    title="Estado de acciones retrasadas",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig2.update_layout(height=280, margin=dict(l=10, r=10, t=50, b=10))
                st.plotly_chart(fig2, use_container_width=True)

            with st.expander("📋 Ver detalle completo"):
                _cols_ret = [c for c in [
                    _COL_PA_ID, _COL_PROC_RESP,
                    "Descripción", "Acción", _COL_ESTADO_PA, _COL_FECHA_LIM,
                    "Responsable de ejecución",
                ] if c and c in df_ret.columns]
                df_ret_show = df_ret[_cols_ret].copy()
                if _COL_FECHA_LIM in df_ret_show.columns:
                    df_ret_show[_COL_FECHA_LIM] = (
                        pd.to_datetime(df_ret_show[_COL_FECHA_LIM], errors="coerce")
                        .dt.strftime("%d/%m/%Y").fillna("—")
                    )
                st.dataframe(df_ret_show, use_container_width=True, hide_index=True,
                             column_config={
                                 "Descripción": st.column_config.TextColumn("Descripción", width="large"),
                                 "Acción":      st.column_config.TextColumn("Acción",      width="large"),
                             })
                st.download_button(
                    "📥 Exportar retrasadas (Excel)",
                    data=exportar_excel(df_ret_show, "Acciones_Retrasadas"),
                    file_name="acciones_retrasadas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="exp_ret",
                )
