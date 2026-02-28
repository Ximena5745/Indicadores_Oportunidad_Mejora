"""
pages/1_Resumen_General.py — Página de Resumen General del dashboard.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import cargar_dataset, construir_opciones_indicadores
from utils.calculos import (
    calcular_salud_institucional,
    calcular_kpis,
    obtener_ultimo_registro,
)
from utils.charts import (
    grafico_historico_indicador,
    tabla_historica_indicador,
    exportar_excel,
    colorear_tabla_categoria,
    panel_detalle_indicador,
    COLOR_CAT,
)
from config import COLORES, COLOR_CATEGORIA_CLARO

# ── Carga de datos ────────────────────────────────────────────────────────────
df_raw = cargar_dataset()

if df_raw.empty:
    st.error("No se pudo cargar el Dataset_Unificado.xlsx. Verifica que el archivo exista en data/raw/.")
    st.stop()

# ── Sidebar — Filtros ─────────────────────────────────────────────────────────
st.sidebar.markdown("## Filtros")

# Año (multi-select, independiente)
anios_disp = sorted(df_raw["Anio"].dropna().unique().tolist()) if "Anio" in df_raw.columns else []
anios_sel = st.sidebar.multiselect("Año", options=anios_disp, default=[])

# Periodo (multi-select, INDEPENDIENTE del año)
periodos_disp = sorted(df_raw["Periodo"].dropna().unique().tolist()) if "Periodo" in df_raw.columns else []
periodos_sel = st.sidebar.multiselect("Periodo", options=periodos_disp, default=[])

# Indicador (multi-select, búsqueda por Id o nombre)
opciones_ind = construir_opciones_indicadores(df_raw)
ind_labels_sel = st.sidebar.multiselect("Indicador", options=list(opciones_ind.keys()), default=[])
ids_sel = [opciones_ind[l] for l in ind_labels_sel]

# ── Aplicar filtros ───────────────────────────────────────────────────────────
df = df_raw.copy()
if anios_sel:
    df = df[df["Anio"].isin(anios_sel)]
if periodos_sel:
    df = df[df["Periodo"].isin(periodos_sel)]
if ids_sel:
    df = df[df["Id"].isin(ids_sel)]

# ── Título ────────────────────────────────────────────────────────────────────
st.markdown("# 🏠 Resumen General")
st.markdown("---")

# ── KPIs ──────────────────────────────────────────────────────────────────────
df_ultimo = obtener_ultimo_registro(df)
total, conteos = calcular_kpis(df_ultimo)

c0, c1, c2, c3, c4 = st.columns(5)
with c0:
    st.metric("Total con datos", total)
with c1:
    d = conteos.get("Peligro", {})
    st.metric(
        "🔴 En Peligro",
        d.get("n", 0),
        delta=f"{d.get('pct', 0)}%",
        delta_color="inverse",
    )
with c2:
    d = conteos.get("Alerta", {})
    st.metric("🟡 En Alerta", d.get("n", 0), delta=f"{d.get('pct', 0)}%", delta_color="off")
with c3:
    d = conteos.get("Cumplimiento", {})
    st.metric("🟢 Cumplimiento", d.get("n", 0), delta=f"{d.get('pct', 0)}%")
with c4:
    d = conteos.get("Sobrecumplimiento", {})
    st.metric("🔵 Sobrecumplimiento", d.get("n", 0), delta=f"{d.get('pct', 0)}%")

st.markdown("---")

# ── Gráfico Salud Institucional ───────────────────────────────────────────────
st.markdown("### Salud del Desempeño Institucional")

df_salud = calcular_salud_institucional(df)

if not df_salud.empty:
    y_max_s = max(130, float(df_salud["Salud_pct"].max()) + 10)
    fig_salud = go.Figure()

    fig_salud.add_hrect(y0=0,   y1=80,    fillcolor="#FFCDD2", opacity=0.3, line_width=0)
    fig_salud.add_hrect(y0=80,  y1=100,   fillcolor="#FFF9C4", opacity=0.3, line_width=0)
    fig_salud.add_hrect(y0=100, y1=y_max_s, fillcolor="#C8E6C9", opacity=0.3, line_width=0)

    fig_salud.add_trace(go.Scatter(
        x=df_salud["Fecha"],
        y=df_salud["Salud_pct"].round(1),
        mode="lines+markers",
        line=dict(color=COLORES["primario"], width=2.5),
        marker=dict(size=8, color=COLORES["primario"]),
        fill="tozeroy",
        fillcolor="rgba(26,58,92,0.08)",
        name="Salud institucional",
        hovertemplate="<b>Fecha:</b> %{x|%b %Y}<br><b>Salud:</b> %{y:.1f}%<extra></extra>",
    ))

    fig_salud.add_hline(y=100, line_dash="dash", line_color=COLORES["cumplimiento"], line_width=2,
                        annotation_text="Meta 100%", annotation_position="right")
    fig_salud.add_hline(y=80,  line_dash="dot",  line_color=COLORES["peligro"],      line_width=1.5,
                        annotation_text="Umbral peligro", annotation_position="right")

    fig_salud.update_layout(
        yaxis=dict(title="Cumplimiento promedio (%)", ticksuffix="%", range=[0, y_max_s]),
        xaxis_title="Fecha",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.15),
        margin=dict(t=20, b=40),
        height=350,
    )
    st.plotly_chart(fig_salud, use_container_width=True)
else:
    st.info("No hay datos suficientes para construir el gráfico de salud institucional.")

st.markdown("---")

# ── Histórico por indicador ───────────────────────────────────────────────────
st.markdown("### Histórico de Cumplimiento por Indicador")

opciones_historico = construir_opciones_indicadores(df_raw)
label_seleccionado = st.selectbox(
    "Selecciona un indicador",
    options=["— Selecciona un indicador —"] + list(opciones_historico.keys()),
    index=0,
)

if label_seleccionado != "— Selecciona un indicador —":
    id_sel = opciones_historico[label_seleccionado]
    df_ind = df_raw[df_raw["Id"] == id_sel].copy()

    if not df_ind.empty:
        fig_hist = grafico_historico_indicador(df_ind, titulo=label_seleccionado)
        st.plotly_chart(fig_hist, use_container_width=True)

        df_tabla_hist = tabla_historica_indicador(df_ind.sort_values("Fecha"))
        st.dataframe(df_tabla_hist, use_container_width=True, hide_index=True)
    else:
        st.warning("Sin datos para el indicador seleccionado.")

st.markdown("---")

# ── Tabla de detalle ──────────────────────────────────────────────────────────
st.markdown("### Tabla de Detalle")

df_tabla = df_ultimo.copy()
df_tabla["Cumplimiento%"] = (df_tabla["Cumplimiento_norm"] * 100).round(1).astype(str) + "%"

cols_show = ["Id", "Indicador", "Proceso", "Subproceso", "Cumplimiento%", "Categoria", "Clasificacion", "Periodicidad"]
cols_disp = [c for c in cols_show if c in df_tabla.columns]

# Mostrar tabla con selección de fila
event = st.dataframe(
    df_tabla[cols_disp],
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Categoria": st.column_config.TextColumn("Categoría"),
        "Cumplimiento%": st.column_config.TextColumn("Cumplimiento"),
    },
)

# Botón exportar Excel
col_exp, _ = st.columns([1, 4])
with col_exp:
    st.download_button(
        label="📥 Exportar Excel",
        data=exportar_excel(df_tabla[cols_disp], "Resumen General"),
        file_name="resumen_general.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ── Panel de detalle al clic en fila ─────────────────────────────────────────
if event and event.selection and event.selection.get("rows"):
    idx = event.selection["rows"][0]
    fila = df_tabla[cols_disp].iloc[idx]
    id_ind = df_tabla["Id"].iloc[idx] if "Id" in df_tabla.columns else None

    if id_ind:
        df_ind_det = df_raw[df_raw["Id"] == id_ind].copy()

        @st.dialog(f"Detalle: {id_ind}", width="large")
        def mostrar_detalle_resumen():
            panel_detalle_indicador(df_ind_det, id_ind, df_raw)

        mostrar_detalle_resumen()
