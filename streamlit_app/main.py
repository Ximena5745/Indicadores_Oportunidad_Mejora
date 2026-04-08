import streamlit as st
from streamlit_option_menu import option_menu

from streamlit_app.components import Topbar, Banner, KPIRow, Charts
from streamlit_app.services.data_service import DataService

from streamlit_app.pages import (
    cmi_estrategico,
    pdi_acreditacion,
    plan_mejoramiento,
    resumen_por_proceso,
    seguimiento_reportes,
    gestion_om,
)

st.set_page_config(page_title="Sistema de Indicadores", layout="wide")


def _inject_styles():
    """Carga e inyecta el CSS local en la cabecera de Streamlit."""
    try:
        css_path = "streamlit_app/styles/styles.css"
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception:
        # No bloquear la app si falla la carga de estilos
        try:
            st.warning("No se pudo cargar estilos locales (styles.css). Usando estilos por defecto.")
        except Exception:
            pass


def main():
    _inject_styles()
    # Configuración del sidebar
    with st.sidebar:
        st.title("Sistema de Indicadores")
        st.markdown("Politécnico Grancolombiano · v2.0 Estratégico")
        st.markdown("---")

        # Menú principal — solo se muestran las secciones principales.
        menu = option_menu(
            menu_title="Navegación",
            options=["Inicio estratégico", "Resumen por procesos", "Seguimiento operativo"],
            icons=["house", "layers", "clipboard-check"],
            menu_icon="cast",
            default_index=0,
        )

    # Routing simple a páginas
    if menu == "Inicio estratégico":
        # Inicio estratégico: mostrar pestañas internas CMI / PDI / Plan (no como páginas en sidebar)
        Topbar().render()
        Banner().render()
        KPIRow().render()
        st.markdown("---")
        # pestañas internas
        tab_cmi, tab_pdi, tab_plan = st.tabs(["CMI Estratégico", "PDI / Acreditación", "Plan de Mejoramiento"])
        with tab_cmi:
            cmi_estrategico.render()
        with tab_pdi:
            pdi_acreditacion.render()
        with tab_plan:
            plan_mejoramiento.render()
        st.markdown("---")
        Charts(service=DataService()).draw_performance_chart()

    elif menu == "CMI Estratégico":
        cmi_estrategico.render()

    elif menu == "PDI / Acreditación":
        pdi_acreditacion.render()

    elif menu == "Plan de Mejoramiento":
        plan_mejoramiento.render()

    elif menu == "Resumen por procesos":
        # Resumen por procesos se renderiza como una vista con sus propias pestañas (ya implementado en el módulo)
        resumen_por_proceso.render()

    elif menu == "Seguimiento operativo":
        # Agrupar vistas operativas en pestañas internas
        tab_a, tab_b = st.tabs(["Seguimiento reportes", "Gestión de OM"])
        with tab_a:
            seguimiento_reportes.render()
        with tab_b:
            gestion_om.render()


if __name__ == "__main__":
    main()
