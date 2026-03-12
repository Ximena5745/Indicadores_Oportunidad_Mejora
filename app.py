"""
app.py — Entrada principal del Dashboard de Desempeño Institucional.
"""
import streamlit as st

# Configuración global (debe ser la primera llamada a Streamlit)
st.set_page_config(
    page_title="Dashboard de Desempeño Institucional",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personalizado ─────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Sidebar institucional */
    [data-testid="stSidebar"] {
        background-color: #1A3A5C;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    [data-testid="stSidebar"] .stMultiSelect > div > div {
        background-color: #1E4A72;
    }
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #1E4A72;
    }
    [data-testid="stSidebar"] label {
        color: #B3D9FF !important;
        font-weight: 500;
    }

    /* Tarjetas de métricas */
    [data-testid="metric-container"] {
        background: white;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #1A3A5C;
    }

    /* Fondo de la app */
    .stApp {
        background-color: #F4F6F9;
    }

    /* Usar todo el ancho — Streamlit 1.44+ usa stMainBlockContainer */
    .stMainBlockContainer {
        max-width: none !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-top: 0.5rem !important;
    }

    /* Encabezados */
    h1 { color: #1A3A5C; }
    h2, h3 { color: #1565C0; }

    /* Botones de acción */
    div[data-testid="stDownloadButton"] button {
        background-color: #1A3A5C;
        color: white;
        border: none;
        border-radius: 6px;
    }
    div[data-testid="stDownloadButton"] button:hover {
        background-color: #1565C0;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Separador */
    hr {
        border: none;
        border-top: 1px solid #DEE2E6;
        margin: 1rem 0;
    }

    /* Botón Actualizar datos en sidebar */
    [data-testid="stSidebar"] div[data-testid="stButton"] button {
        background-color: #1565C0;
        color: white !important;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }
    [data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
        background-color: #0D47A1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Botón de actualización en sidebar ────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.success("Datos actualizados.")
    st.markdown("---")

# ── Navegación multipágina ────────────────────────────────────────────────────
pages = {
    "Dashboard": [
        st.Page("pages/5_Reporte_Seguimiento.py",    title="Reporte Seguimiento",      icon="📊"),
        st.Page("pages/1_Resumen_General.py",        title="Reporte de Cumplimiento",  icon="🏠"),
        st.Page("pages/2_Indicadores_en_Riesgo.py",  title="Indicadores en Riesgo",    icon="⚠️"),
        st.Page("pages/3_Acciones_de_Mejora.py",     title="Oportunidades de Mejora",  icon="📋"),
        st.Page("pages/4_Registro_OM.py",             title="Registro de OM",           icon="📝"),
    ]
}

pg = st.navigation(pages)
pg.run()
