"""
Entrypoint unificado: integra la nueva página `Inicio Estratégico` junto con
las páginas existentes del proyecto (excepto Nivel 3 que se omite).
"""
import streamlit as st

# Configuración de página
st.set_page_config(page_title="Sistema de Indicadores", layout="wide")

# Reusar estilos y CSS institucionales del `app.py` original
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

    /* Tarjetas de métricas — fondo oscuro, texto claro (contraste visual) */
    [data-testid="metric-container"],
    [data-testid="stMetric"] {
        background: #1A3A5C !important;
        border-radius: 10px !important;
        padding: 16px 20px !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.25) !important;
        border-left: 4px solid #4FC3F7 !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricLabel"] p,
    [data-testid="metric-container"] label,
    [data-testid="stMetric"] [data-testid="stMetricLabel"] p,
    [data-testid="stMetric"] label {
        color: #B3D9FF !important;
        font-weight: 500;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"],
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #E3F2FD !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricDelta"],
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: #80DEEA !important;
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
    "",
    unsafe_allow_html=True,
)


def main():
    # Botón de actualización en sidebar (igual comportamiento que antes)
    with st.sidebar:
        st.markdown("---")
        if st.button("🔄 Actualizar datos", use_container_width=True):
            st.cache_data.clear()
            st.success("Datos actualizados.")
    # Navegación simplificada:
    # - Resumen estratégico: CMI, PDI, Plan
    # - Resumen por procesos: Mapa de procesos con tabs (el motor analítico/IA se integra aquí)
    # - Seguimiento operativo: Reportes, Gestión OM, Registro OM
    # - Direccionamiento y Auditorías se eliminan del menú → su estructura se integra
    #   como tabs dentro de "Resumen por procesos" (selección multi-proceso)
    # - Nivel 3 se elimina del menú.
    pages = {
        "Resumen estratégico": [
            st.Page("pages/cmi_estrategico.py",       title="CMI Estratégico",      icon="📈"),
            st.Page("pages/pdi_acreditacion.py",      title="PDI / Acreditación",   icon="🏛️"),
            st.Page("pages/plan_mejoramiento.py",     title="Plan de Mejoramiento", icon="📋"),
        ],
        "Resumen por procesos": [
            st.Page("pages/resumen_por_proceso.py",   title="Mapa de procesos",     icon="🗺️"),
        ],
        "Seguimiento operativo": [
            st.Page("pages/5_Seguimiento_de_reportes.py", title="Seguimiento reportes", icon="📊"),
            st.Page("pages/2_Gestion_OM.py",               title="Gestión de OM",         icon="⚠️"),
            st.Page("pages/4_Registro_OM.py",              title="Registro OM",           icon="📝"),
        ],
    }

    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
