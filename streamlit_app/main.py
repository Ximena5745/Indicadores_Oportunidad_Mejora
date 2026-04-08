import streamlit as st
from streamlit_option_menu import option_menu

from streamlit_app.components import Topbar, Banner, KPIRow, Charts
from streamlit_app.services.data_service import DataService

from streamlit_app.pages import (
    cmi_estrategico,
    pdi_acreditacion,
    plan_mejoramiento,
    resumen_general,
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


def _get_git_commit_short():
    import subprocess, os
    try:
        p = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        return p.stdout.strip()
    except Exception:
        return os.getenv("GIT_COMMIT", "unknown")


def main():
    _inject_styles()

    # Configuración del sidebar
    with st.sidebar:
        header_html = """
<div class='sidebar-header'>
  <div class='sidebar-logo'>
    <svg width='28' height='28' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'>
      <rect width='24' height='24' rx='4' fill='#ffffff22'/>
      <text x='12' y='16' font-size='10' text-anchor='middle' fill='white' font-family='Arial' font-weight='700'>PG</text>
    </svg>
  </div>
  <div>
    <div class='sidebar-title'>Sistema de Indicadores</div>
    <div class='sidebar-subtitle'>Politécnico Grancolombiano · v2.0 Estratégico</div>
  </div>
</div>
"""
        st.markdown(header_html, unsafe_allow_html=True)
        st.markdown("<div class='sidebar-section-title'>Navegación</div>", unsafe_allow_html=True)

        menu = option_menu(
            menu_title=None,
            options=["Resumen general", "Inicio estratégico", "Resumen por procesos", "Seguimiento operativo"],
            icons=["file-text", "house", "layers", "clipboard-check"],
            menu_icon="cast",
            default_index=0,
        )

        # Mantener sidebar limpio: el foco es la navegación y el encabezado.
        st.markdown("<style>.sidebar-status-card{display:none!important;}.version-box{display:none!important;}</style>", unsafe_allow_html=True)

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
        cols = st.columns([2, 1])
        with cols[0]:
            Charts(service=DataService()).draw_performance_chart()
        with cols[1]:
            Charts(service=DataService()).draw_semaforo()

    elif menu == "CMI Estratégico":
        cmi_estrategico.render()

    elif menu == "PDI / Acreditación":
        pdi_acreditacion.render()

    elif menu == "Plan de Mejoramiento":
        plan_mejoramiento.render()

    elif menu == "Resumen general":
        resumen_general.render()

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
