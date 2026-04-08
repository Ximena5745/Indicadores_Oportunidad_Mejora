import streamlit as st
from streamlit_option_menu import option_menu

from streamlit_app.components import Topbar, Banner, KPIRow, Charts
from streamlit_app.services.data_service import DataService

from streamlit_app.pages import (
    cmi_estrategico,
    pdi_acreditacion,
    plan_mejoramiento,
    resumen_por_proceso,
    _5_Seguimiento_de_reportes,
    _2_Gestion_OM,
)

st.set_page_config(page_title="Sistema de Indicadores", layout="wide")


def main():
    # Configuración del sidebar
    with st.sidebar:
        st.title("Sistema de Indicadores")
        st.markdown("Politécnico Grancolombiano · v2.0 Estratégico")
        st.markdown("---")

        # Menú principal extendido
        menu = option_menu(
            menu_title="Navegación",
            options=[
                "Inicio estratégico",
                "CMI Estratégico",
                "PDI / Acreditación",
                "Plan de Mejoramiento",
                "Resumen por procesos",
                "Seguimiento reportes",
                "Gestión de OM",
            ],
            icons=["house", "bar-chart-2", "book", "list-task", "layers", "file-earmark-text", "clipboard-check"],
            menu_icon="cast",
            default_index=0,
        )

    # Routing simple a páginas
    if menu == "Inicio estratégico":
        # render main dashboard using components
        Topbar().render()
        Banner().render()
        KPIRow().render()
        st.markdown("---")
        Charts(service=DataService()).draw_performance_chart()

    elif menu == "CMI Estratégico":
        cmi_estrategico.render()

    elif menu == "PDI / Acreditación":
        pdi_acreditacion.render()

    elif menu == "Plan de Mejoramiento":
        plan_mejoramiento.render()

    elif menu == "Resumen por procesos":
        resumen_por_proceso.render()

    elif menu == "Seguimiento reportes":
        _5_Seguimiento_de_reportes.render()

    elif menu == "Gestión de OM":
        _2_Gestion_OM.render()


if __name__ == "__main__":
    main()
