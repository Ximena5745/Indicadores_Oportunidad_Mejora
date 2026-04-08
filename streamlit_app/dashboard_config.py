# Configuración inicial del dashboard para el módulo "Inicio estratégico"

import streamlit as st
import plotly.express as px
import pandas as pd

# Configuración de la barra lateral
st.sidebar.title("Sistema de Indicadores")
st.sidebar.subheader("Politécnico Grancolombiano · v2.0 Estratégico")

# Secciones del menú lateral
menu = st.sidebar.radio("Navegación", [
    "Inicio estratégico",
    "Seg. de reportes",
    "Reporte cumplimiento",
    "Gestión de OM",
    "Tablero operativo",
    "Predicción IRIP",
    "Detector anomalías",
    "CMI Estratégico",
    "Indicadores acreditación",
    "Plan de mejoramiento",
    "Resumen por proceso",
    "Exportar / reportes"
])

# Topbar superior
st.title("Inicio estratégico")
st.subheader("Dic 2025 · 387 indicadores · Generado 07/04/2026")

# Banner de alerta IA
st.markdown(
    """
    <div style="background: linear-gradient(90deg, #6200ea, #325f99, #00b8d4); padding: 10px; border-radius: 5px;">
        <h4 style="color: white;">IA detectó: 9 indicadores con riesgo alto de incumplimiento (IRIP >70%)</h4>
        <p style="color: white;">3 anomalías en datos (z-score >3) · 7 metas fuera de rango estadístico óptimo</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Fila de KPIs globales
def mostrar_kpis():
    kpis = [
        {"label": "Total indicadores", "valor": 387, "subtexto": "Kawak + API", "color": "#00b8d4"},
        {"label": "En peligro", "valor": 20, "subtexto": "+19 vs ant. · 5.2%", "color": "#ff3b30"},
        {"label": "En alerta", "valor": 24, "subtexto": "+21 vs ant. · 6.2%", "color": "#ffab00"},
        {"label": "Cumplimiento", "valor": 85, "subtexto": "+70 vs ant. · 22%", "color": "#00c853"},
        {"label": "Sobrecumplimiento", "valor": 115, "subtexto": "+108 vs ant. · 29.7%", "color": "#00b8d4"}
    ]

    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        col.metric(label=kpi["label"], value=kpi["valor"], delta=kpi["subtexto"])

mostrar_kpis()

# Subnavegación interna del módulo
sub_menu = st.selectbox("Vista detallada", [
    "Resumen ejecutivo",
    "Por proceso",
    "Por vicerrectoría",
    "Analítica IA",
    "PDI / Acreditación",
    "Auditorías"
])

# Contenido dinámico según la selección
if sub_menu == "Resumen ejecutivo":
    st.write("Aquí se mostrará el resumen ejecutivo.")
elif sub_menu == "Por proceso":
    st.write("Vista por proceso.")
# Agregar más vistas según sea necesario

# Propuesta de módulos con gráficas interactivas

import streamlit as st
import plotly.express as px
import pandas as pd

# Datos simulados para las gráficas
data_irip = pd.DataFrame({
    "Indicador": ["Graduación oportuna", "Cobertura banda ancha", "Publicaciones indexadas", "Tasa retención", "Financiación externa"],
    "Riesgo": [87, 82, 79, 73, 71]
})

data_anomalias = pd.DataFrame({
    "Fecha": pd.date_range(start="2026-01-01", periods=10, freq="M"),
    "Anomalías": [3, 5, 2, 4, 6, 3, 7, 5, 4, 6]
})

data_cmi = pd.DataFrame({
    "Perspectiva": ["Formación", "Investigación", "Extensión", "Internacionalización"],
    "Cumplimiento": [85, 78, 92, 88]
})

# Módulo IRIP Predictivo
st.subheader("Módulo IRIP Predictivo")
fig_irip = px.bar(data_irip, x="Riesgo", y="Indicador", orientation="h", color="Riesgo",
                  color_continuous_scale="reds", title="Ranking de Riesgo IRIP")
st.plotly_chart(fig_irip)

# Módulo DAD / Detector de anomalías
st.subheader("Módulo DAD / Detector de anomalías")
fig_anomalias = px.line(data_anomalias, x="Fecha", y="Anomalías", markers=True,
                        title="Tendencia de Anomalías Detectadas")
st.plotly_chart(fig_anomalias)

# Módulo CMI Estratégico
st.subheader("Módulo CMI Estratégico")
fig_cmi = px.bar(data_cmi, x="Perspectiva", y="Cumplimiento", color="Cumplimiento",
                 color_continuous_scale="blues", title="Cumplimiento por Perspectiva CMI")
st.plotly_chart(fig_cmi)

# Footer
st.markdown("---")
st.markdown("Sistema de Indicadores · Politécnico Grancolombiano · 2026")