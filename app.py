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

    /* Ancho completo — override del emotion-cache generado por Streamlit */
    div[data-testid="stMainBlockContainer"],
    .stMainBlockContainer.block-container {
        max-width: none !important;
        padding-top: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
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

# ── Botón de actualización + modo oscuro en sidebar ──────────────────────────
with st.sidebar:
    st.markdown("---")
    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.success("Datos actualizados.")
    dark_mode = st.toggle("🌙 Modo oscuro (tarjetas)", value=False, key="global_dark_mode")
    st.markdown("---")

# CSS dinámico según modo oscuro
if dark_mode:
    st.markdown(
        """
        <style>
        /* Tarjetas de métricas — modo oscuro */
        [data-testid="metric-container"] {
            background: #1E2A3A !important;
            border-left: 4px solid #4FC3F7 !important;
            box-shadow: 0 2px 10px rgba(0,0,0,0.35) !important;
        }
        [data-testid="metric-container"] [data-testid="stMetricLabel"] {
            color: #90CAF9 !important;
        }
        [data-testid="metric-container"] [data-testid="stMetricValue"] {
            color: #E3F2FD !important;
        }
        [data-testid="metric-container"] [data-testid="stMetricDelta"] {
            color: #80DEEA !important;
        }
        /* Fondo de la app — modo oscuro */
        .stApp {
            background-color: #0F1923 !important;
        }
        /* Texto general */
        .stApp p, .stApp span, .stApp div:not([class*="stSidebar"]) {
            color: #CFD8DC;
        }
        h1 { color: #90CAF9 !important; }
        h2, h3 { color: #64B5F6 !important; }
        /* Contenedores Plotly */
        .js-plotly-plot .plotly .bg {
            fill: #1E2A3A !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ── Navegación multipágina ────────────────────────────────────────────────────
pages = {
    "Dashboard": [
        st.Page("pages/5_Seguimiento_de_reportes.py",      title="Seguimiento de reportes",       icon="📊"),
        st.Page("pages/1_Resumen_General.py",              title="Reporte de Cumplimiento",       icon="🏠"),
        st.Page("pages/2_Gestion_OM.py",                   title="Gestión de Oportunidades (OM)", icon="⚠️"),
    ],
    "Informes especiales": [
        st.Page("pages/6_Direccionamiento_Estrategico.py", title="Direccionamiento Estratégico",  icon="🏛️"),
    ],
}

pg = st.navigation(pages)
pg.run()
