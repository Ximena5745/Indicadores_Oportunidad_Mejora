"""
pages/3_Acciones_de_Mejora.py — Seguimiento de Acciones de Mejora.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import cargar_acciones_mejora
from utils.charts import exportar_excel
from config import COLORES

# ── Carga de datos ────────────────────────────────────────────────────────────
df_raw = cargar_acciones_mejora()

if df_raw.empty:
    st.error("No se pudo cargar acciones_mejora.xlsx. Verifica que el archivo exista en data/raw/.")
    st.stop()

# ── Colores Estado_Tiempo ─────────────────────────────────────────────────────
COLOR_ESTADO = {
    "Vencida":   "#C62828",
    "Por vencer":"#F57F17",
    "A tiempo":  "#2E7D32",
    "Cerrada":   "#424242",
}

# ── KPIs (sobre df completo, antes de filtros) ────────────────────────────────
st.markdown("# 📋 Acciones de Mejora")
st.markdown("---")

total_am = len(df_raw)

kpi_data = {
    "En Ejecución": (df_raw["ESTADO"] == "Ejecución").sum() if "ESTADO" in df_raw.columns else 0,
    "Vencidas":     (df_raw["Estado_Tiempo"] == "Vencida").sum(),
    "Por Vencer":   (df_raw["Estado_Tiempo"] == "Por vencer").sum(),
    "A Tiempo":     (df_raw["Estado_Tiempo"] == "A tiempo").sum(),
    "Cerradas":     (df_raw["ESTADO"] == "Cerrada").sum() if "ESTADO" in df_raw.columns else 0,
    "Sin Avance":   (df_raw["MESES_SIN_AVANCE"] > 2).sum() if "MESES_SIN_AVANCE" in df_raw.columns else 0,
}

kpi_icons = {
    "En Ejecución": "⚙️",
    "Vencidas":     "🔴",
    "Por Vencer":   "🟡",
    "A Tiempo":     "🟢",
    "Cerradas":     "✅",
    "Sin Avance":   "⚠️",
}

kpi_cols = st.columns(6)
for i, (label, val) in enumerate(kpi_data.items()):
    with kpi_cols[i]:
        st.metric(f"{kpi_icons[label]} {label}", val)

st.markdown("---")

# ── Sidebar — Filtros ─────────────────────────────────────────────────────────
st.sidebar.markdown("## Filtros Acciones")

estados_disp = sorted(df_raw["ESTADO"].dropna().unique().tolist()) if "ESTADO" in df_raw.columns else []
estados_sel = st.sidebar.multiselect("Estado", options=estados_disp, default=[])

procesos_disp = sorted(df_raw["PROCESOS"].dropna().unique().tolist()) if "PROCESOS" in df_raw.columns else []
procesos_sel = st.sidebar.multiselect("Proceso", options=procesos_disp, default=[])

fuentes_disp = sorted(df_raw["FUENTE"].dropna().unique().tolist()) if "FUENTE" in df_raw.columns else []
fuente_default = ["Indicadores"] if "Indicadores" in fuentes_disp else []
fuentes_sel = st.sidebar.multiselect("Fuente", options=fuentes_disp, default=fuente_default)

tipos_disp = sorted(df_raw["TIPO_ACCION"].dropna().unique().tolist()) if "TIPO_ACCION" in df_raw.columns else []
tipos_sel = st.sidebar.multiselect("Tipo", options=tipos_disp, default=[])

# ── Aplicar filtros ───────────────────────────────────────────────────────────
df = df_raw.copy()
if estados_sel:
    df = df[df["ESTADO"].isin(estados_sel)]
if procesos_sel:
    df = df[df["PROCESOS"].isin(procesos_sel)]
if fuentes_sel:
    df = df[df["FUENTE"].isin(fuentes_sel)]
if tipos_sel:
    df = df[df["TIPO_ACCION"].isin(tipos_sel)]

if df.empty:
    st.info("No hay acciones de mejora con los filtros seleccionados.")
    st.stop()

# ── Gráficos ──────────────────────────────────────────────────────────────────
col_g1, col_g2, col_g3 = st.columns([3, 2, 2])

# Gráfico 1 — Barras apiladas Proceso × Estado_Tiempo
with col_g1:
    st.markdown("**AM por Estado y Proceso**")
    if "PROCESOS" in df.columns:
        estados_orden = ["Vencida", "Por vencer", "A tiempo", "Cerrada"]
        fig_stack = go.Figure()
        for estado in estados_orden:
            df_est = df[df["Estado_Tiempo"] == estado]
            if df_est.empty:
                continue
            cnt = df_est.groupby("PROCESOS").size().reset_index(name="count")
            fig_stack.add_trace(go.Bar(
                x=cnt["PROCESOS"],
                y=cnt["count"],
                name=estado,
                marker_color=COLOR_ESTADO.get(estado, "#9E9E9E"),
                hovertemplate=f"<b>{estado}</b><br>Proceso: %{{x}}<br>Cantidad: %{{y}}<extra></extra>",
            ))
        fig_stack.update_layout(
            barmode="stack",
            height=400,
            xaxis=dict(title="Proceso", tickangle=-30),
            yaxis=dict(title="Cantidad"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend=dict(orientation="h", y=-0.3),
            margin=dict(t=20, b=80),
        )
        st.plotly_chart(fig_stack, use_container_width=True)
    else:
        st.info("Sin columna PROCESOS.")

# Gráfico 2 — Gauge avance promedio
with col_g2:
    st.markdown("**Avance Promedio**")
    avance_prom = float(df["AVANCE"].mean()) if "AVANCE" in df.columns else 0

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(avance_prom, 1),
        number={"suffix": "%", "font": {"size": 36}},
        gauge={
            "axis": {"range": [0, 100], "ticksuffix": "%"},
            "bar":  {"color": COLORES["primario"], "thickness": 0.25},
            "steps": [
                {"range": [0,  50], "color": "#FFCDD2"},
                {"range": [50, 80], "color": "#FFF9C4"},
                {"range": [80, 100],"color": "#C8E6C9"},
            ],
            "threshold": {
                "line": {"color": COLORES["cumplimiento"], "width": 4},
                "thickness": 0.75,
                "value": 80,
            },
        },
    ))
    fig_gauge.update_layout(
        height=300,
        margin=dict(t=30, b=20, l=20, r=20),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

# Gráfico 3 — Dona Estado de Tiempo
with col_g3:
    st.markdown("**Estado de Tiempo**")
    et_counts = df["Estado_Tiempo"].value_counts().reset_index()
    et_counts.columns = ["Estado", "Cantidad"]

    fig_dona = go.Figure(go.Pie(
        labels=et_counts["Estado"],
        values=et_counts["Cantidad"],
        hole=0.45,
        marker=dict(
            colors=[COLOR_ESTADO.get(e, "#9E9E9E") for e in et_counts["Estado"]]
        ),
        hovertemplate="<b>%{label}</b><br>%{value} acciones<br>%{percent}<extra></extra>",
    ))
    fig_dona.update_layout(
        height=300,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=20, b=40),
    )
    st.plotly_chart(fig_dona, use_container_width=True)

st.markdown("---")

# ── Tabla ─────────────────────────────────────────────────────────────────────
st.markdown("### Tabla de Acciones")

cols_show = [
    "ID", "DESCRIPCION", "PROCESOS", "FUENTE", "TIPO_ACCION", "TIPO_HALLAZGO",
    "ESTADO", "Estado_Tiempo", "AVANCE", "FECHA_ESTIMADA_CIERRE",
    "DIAS_VENCIDA", "MESES_SIN_AVANCE",
]
cols_disp = [c for c in cols_show if c in df.columns]
df_tabla = df[cols_disp].copy()

# Formato AVANCE
if "AVANCE" in df_tabla.columns:
    df_tabla["AVANCE"] = df_tabla["AVANCE"].apply(
        lambda x: f"{int(x)}%" if pd.notna(x) else "—"
    )
# Formato fecha
if "FECHA_ESTIMADA_CIERRE" in df_tabla.columns:
    df_tabla["FECHA_ESTIMADA_CIERRE"] = pd.to_datetime(
        df_tabla["FECHA_ESTIMADA_CIERRE"], errors="coerce"
    ).dt.strftime("%Y-%m-%d").fillna("—")

def _estilo_accion(row):
    est = row.get("Estado_Tiempo", "")
    bg = {"Vencida": "#FFCDD2", "Por vencer": "#FFF9C4"}.get(est, "")
    return [f"background-color: {bg}" if bg else "" for _ in row]

styled = df_tabla.style.apply(_estilo_accion, axis=1)

st.dataframe(
    styled,
    use_container_width=True,
    hide_index=True,
    column_config={
        "DESCRIPCION": st.column_config.TextColumn("Descripción", width="large"),
        "AVANCE": st.column_config.TextColumn("Avance"),
    },
)

col_exp, _ = st.columns([1, 4])
with col_exp:
    st.download_button(
        label="📥 Exportar Excel",
        data=exportar_excel(df[cols_disp], "Acciones de Mejora"),
        file_name="acciones_mejora.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
