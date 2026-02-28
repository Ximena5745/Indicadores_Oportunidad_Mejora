"""
pages/2_Indicadores_en_Riesgo.py — Indicadores en Riesgo con semáforo interactivo.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import cargar_dataset, construir_opciones_indicadores
from utils.calculos import obtener_ultimo_registro
from utils.charts import (
    grafico_historico_indicador,
    tabla_historica_indicador,
    exportar_excel,
    panel_detalle_indicador,
    COLOR_CAT,
)
from config import COLORES

# ── Carga de datos ────────────────────────────────────────────────────────────
df_raw = cargar_dataset()

if df_raw.empty:
    st.error("No se pudo cargar Dataset_Unificado.xlsx.")
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
if "categoria_activa" not in st.session_state:
    st.session_state.categoria_activa = "Peligro"
if "indicador_detalle_p2" not in st.session_state:
    st.session_state.indicador_detalle_p2 = None

# ── Sidebar — Filtros ─────────────────────────────────────────────────────────
st.sidebar.markdown("## Filtros")

anios_disp = sorted(df_raw["Anio"].dropna().unique().tolist()) if "Anio" in df_raw.columns else []
anios_sel = st.sidebar.multiselect("Año", options=anios_disp, default=[])

period_disp = sorted(df_raw["Periodicidad"].dropna().unique().tolist()) if "Periodicidad" in df_raw.columns else []
period_sel = st.sidebar.multiselect("Periodicidad", options=period_disp, default=[])

# ── Aplicar filtros ───────────────────────────────────────────────────────────
df = df_raw.copy()
if anios_sel:
    df = df[df["Anio"].isin(anios_sel)]
if period_sel:
    df = df[df["Periodicidad"].isin(period_sel)]

df_ultimo = obtener_ultimo_registro(df)
df_con_datos = df_ultimo[df_ultimo["Cumplimiento_norm"].notna()]
total = len(df_con_datos)

# ── Título ────────────────────────────────────────────────────────────────────
st.markdown("# ⚠️ Indicadores en Riesgo")
st.markdown("---")

# ── Semáforo ──────────────────────────────────────────────────────────────────
st.markdown("### Semáforo de Desempeño")
st.caption("Haz clic en una categoría para filtrar todas las visualizaciones.")

semaforo_config = [
    ("Sobrecumplimiento", "🔵", COLORES["sobrecumplimiento"]),
    ("Cumplimiento",      "🟢", COLORES["cumplimiento"]),
    ("Alerta",            "🟡", COLORES["alerta"]),
    ("Peligro",           "🔴", COLORES["peligro"]),
]

col_sems = st.columns(4)
for i, (cat, icon, color) in enumerate(semaforo_config):
    n_cat = (df_con_datos["Categoria"] == cat).sum()
    pct   = round(n_cat / total * 100, 1) if total > 0 else 0
    activa = st.session_state.categoria_activa == cat
    borde  = f"3px solid {color}" if activa else f"1px solid {color}"
    bg     = f"{color}22" if activa else "white"

    with col_sems[i]:
        st.markdown(
            f"""<div style="border:{borde};border-radius:10px;padding:14px;
                text-align:center;background:{bg};cursor:pointer;">
                <span style="font-size:2rem">{icon}</span><br>
                <strong style="font-size:1.4rem;color:{color}">{n_cat}</strong><br>
                <span style="font-size:0.85rem;color:#555">{cat}</span><br>
                <span style="font-size:0.8rem;color:#888">{pct}% del total</span>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button(f"Ver {cat}", key=f"sem_{cat}", use_container_width=True):
            st.session_state.categoria_activa = cat
            st.rerun()

st.markdown("---")

# ── Filtrar por categoría activa ──────────────────────────────────────────────
cat_act = st.session_state.categoria_activa
df_cat = df_con_datos[df_con_datos["Categoria"] == cat_act].copy()
df_cat["Cumplimiento%"] = (df_cat["Cumplimiento_norm"] * 100).round(1)

# ── Gráficos (4) ──────────────────────────────────────────────────────────────
st.markdown(f"### Visualizaciones para: {cat_act}")

col_g1, col_g2 = st.columns(2)

# Gráfico 1 — Top 10 menor/mayor cumplimiento
with col_g1:
    st.markdown("**Top 10 — Cumplimiento**")
    if cat_act in ("Peligro", "Alerta"):
        df_top = df_cat.nsmallest(10, "Cumplimiento_norm")
        titulo_top = "10 indicadores con menor cumplimiento"
    else:
        df_top = df_cat.nlargest(10, "Cumplimiento_norm")
        titulo_top = "10 indicadores con mayor cumplimiento"

    if not df_top.empty:
        etiquetas = (df_top["Id"] + " — " + df_top["Indicador"].str[:40]).tolist()
        fig_top = go.Figure(go.Bar(
            x=df_top["Cumplimiento%"].tolist(),
            y=etiquetas,
            orientation="h",
            marker_color=COLOR_CAT.get(cat_act, "#9E9E9E"),
            text=df_top["Cumplimiento%"].round(1).astype(str) + "%",
            textposition="outside",
            customdata=df_top["Id"].tolist(),
            hovertemplate="<b>%{y}</b><br>Cumplimiento: %{x:.1f}%<extra></extra>",
        ))
        fig_top.update_layout(
            height=400,
            xaxis=dict(title="Cumplimiento (%)", ticksuffix="%"),
            yaxis=dict(title=""),
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=10, r=10, t=30, b=30),
            title=titulo_top,
        )
        event_top = st.plotly_chart(fig_top, use_container_width=True, on_select="rerun",
                                    selection_mode="points", key="fig_top10")

        # Click en barra → detalle
        if event_top and event_top.selection and event_top.selection.get("points"):
            pt_idx = event_top.selection["points"][0].get("point_index", None)
            if pt_idx is not None:
                id_click = df_top["Id"].iloc[pt_idx]
                st.session_state.indicador_detalle_p2 = id_click
    else:
        st.info("Sin datos para esta categoría.")

# Gráfico 2 — Distribución por Proceso (dona)
with col_g2:
    st.markdown("**Distribución por Proceso**")
    if not df_cat.empty and "Proceso" in df_cat.columns:
        proc_counts = df_cat.groupby("Proceso").size().reset_index(name="count")
        fig_dona = go.Figure(go.Pie(
            labels=proc_counts["Proceso"],
            values=proc_counts["count"],
            hole=0.4,
            marker=dict(colors=[
                "#1A3A5C", "#1565C0", "#0277BD", "#0288D1", "#0097A7",
                "#00897B", "#43A047", "#7CB342", "#C0CA33", "#FDD835",
            ]),
            hovertemplate="<b>%{label}</b><br>%{value} indicadores<br>%{percent}<extra></extra>",
        ))
        fig_dona.update_layout(
            height=400,
            legend=dict(orientation="v", x=1.02),
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig_dona, use_container_width=True)
    else:
        st.info("Sin datos.")

col_g3, col_g4 = st.columns(2)

# Gráfico 3 — Comparativo por Línea Estratégica
with col_g3:
    st.markdown("**Comparativo por Línea Estratégica**")
    col_linea = "Linea" if "Linea" in df_cat.columns else None
    if col_linea and not df_cat.empty:
        linea_avg = (
            df_cat.groupby(col_linea)["Cumplimiento_norm"]
            .mean().reset_index()
            .assign(Cumplimiento_pct=lambda x: x["Cumplimiento_norm"] * 100)
            .sort_values("Cumplimiento_pct")
        )
        fig_linea = go.Figure(go.Bar(
            x=linea_avg[col_linea],
            y=linea_avg["Cumplimiento_pct"].round(1),
            marker_color=COLOR_CAT.get(cat_act, COLORES["primario"]),
            text=linea_avg["Cumplimiento_pct"].round(1).astype(str) + "%",
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Promedio: %{y:.1f}%<extra></extra>",
        ))
        fig_linea.add_hline(y=100, line_dash="dash", line_color="green", line_width=1.5)
        fig_linea.add_hline(y=80,  line_dash="dot",  line_color="red",   line_width=1)
        fig_linea.update_layout(
            height=380,
            yaxis=dict(title="Cumplimiento promedio (%)", ticksuffix="%"),
            xaxis=dict(title="Línea Estratégica"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(t=20, b=60),
        )
        st.plotly_chart(fig_linea, use_container_width=True)
    else:
        st.info("No hay columna Linea en los datos.")

# Gráfico 4 — Mapa de calor Proceso × Periodo
with col_g4:
    st.markdown("**Mapa de Calor — Proceso × Periodo**")
    if not df_cat.empty and "Proceso" in df_cat.columns and "Periodo" in df_cat.columns:
        df_heat_src = df[df["Categoria"] == cat_act].copy() if not df.empty else df_cat
        pivot = (
            df_heat_src.groupby(["Proceso", "Periodo"])["Cumplimiento_norm"]
            .mean()
            .unstack(fill_value=None)
            * 100
        )
        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values.tolist(),
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale="RdYlGn",
            zmid=90,
            zmin=0,
            zmax=130,
            hovertemplate="<b>Proceso:</b> %{y}<br><b>Periodo:</b> %{x}<br><b>Cum:</b> %{z:.1f}%<extra></extra>",
            colorbar=dict(ticksuffix="%"),
        ))
        fig_heat.update_layout(
            height=380,
            xaxis=dict(title="Periodo"),
            yaxis=dict(title="Proceso"),
            margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Sin datos suficientes para el mapa de calor.")

st.markdown("---")

# ── Tabla detallada ───────────────────────────────────────────────────────────
st.markdown(f"### Tabla Detallada — {cat_act}")

df_tabla_det = df_cat.copy()
df_tabla_det["Cumplimiento%"] = df_tabla_det["Cumplimiento_norm"].apply(
    lambda x: f"{round(x*100,1)}%" if pd.notna(x) else "—"
)
cols_show = ["Id", "Indicador", "Proceso", "Subproceso", "Periodicidad", "Periodo", "Cumplimiento%", "Categoria"]
cols_disp = [c for c in cols_show if c in df_tabla_det.columns]

event_tabla = st.dataframe(
    df_tabla_det[cols_disp],
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="tabla_riesgo",
)

col_exp, _ = st.columns([1, 4])
with col_exp:
    st.download_button(
        label="📥 Exportar Excel",
        data=exportar_excel(df_tabla_det[cols_disp], "Indicadores en Riesgo"),
        file_name=f"indicadores_{cat_act.lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# Click en tabla → capturar id
if event_tabla and event_tabla.selection and event_tabla.selection.get("rows"):
    idx = event_tabla.selection["rows"][0]
    if "Id" in df_tabla_det.columns:
        id_click_tabla = df_tabla_det["Id"].iloc[idx]
        st.session_state.indicador_detalle_p2 = id_click_tabla

st.markdown("---")

# ── Panel de detalle (dialog) ─────────────────────────────────────────────────
if st.session_state.indicador_detalle_p2:
    id_det = st.session_state.indicador_detalle_p2
    df_ind_det = df_raw[df_raw["Id"] == id_det].copy()

    @st.dialog(f"Detalle del indicador: {id_det}", width="large")
    def mostrar_detalle_p2():
        if st.button("✖ Cerrar"):
            st.session_state.indicador_detalle_p2 = None
            st.rerun()
        panel_detalle_indicador(df_ind_det, id_det, df_raw)

    mostrar_detalle_p2()

# ── Sección búsqueda manual histórico ─────────────────────────────────────────
st.markdown("### Histórico por Indicador (búsqueda manual)")

opciones_historico = construir_opciones_indicadores(df_raw)
label_hist = st.selectbox(
    "Selecciona un indicador",
    options=["— Selecciona —"] + list(opciones_historico.keys()),
    index=0,
    key="hist_manual_p2",
)

if label_hist != "— Selecciona —":
    id_hist = opciones_historico[label_hist]
    df_ind_hist = df_raw[df_raw["Id"] == id_hist].sort_values("Fecha")

    if not df_ind_hist.empty:
        fig_h = grafico_historico_indicador(df_ind_hist, titulo=label_hist)
        st.plotly_chart(fig_h, use_container_width=True)

        df_th = tabla_historica_indicador(df_ind_hist)
        st.dataframe(df_th, use_container_width=True, hide_index=True)
    else:
        st.warning("Sin datos.")
