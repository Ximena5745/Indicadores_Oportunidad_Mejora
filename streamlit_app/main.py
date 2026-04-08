import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_app.components import Topbar, Banner, KPIRow, Charts
from streamlit_app.services.data_service import DataService

st.set_page_config(page_title="Sistema de Indicadores", layout="wide")


def _topbar(service=None):
    tb = Topbar()
    return tb.render()


def _banner_ia():
    b = Banner()
    return b.render()


def _kpi_row(service=None):
    kpi = KPIRow()
    return kpi.render()


def _draw_charts():
    charts = Charts(service=DataService())
    charts.draw_performance_chart()
    st.markdown("### ")
    charts.draw_semaforo()


def _indicator_modal(ind_name="Indicador ejemplo"):
    if st.button(f"Abrir detalle: {ind_name}"):
        with st.modal("Detalle indicador"):
            st.header(ind_name)
            st.write("Código: IND-001")
            st.write("Proceso: Gestión Académica")
            st.write("Meta: 90")
            st.write("Valor actual: 73")
            st.write("Responsable: Coordinador X")


def main():
    # Sidebar
    with st.sidebar:
        st.title("Sistema de Indicadores")
        st.markdown("Politécnico Grancolombiano · v2.0 Estratégico")
        st.markdown("---")
        menu = option_menu(
            menu_title="Navegación",
            options=["Inicio estratégico", "Resumen por procesos", "Seguimiento operativo"],
            icons=["house", "bar-chart", "clipboard-check"],
            menu_icon="cast",
            default_index=0,
        )

    # Page content
    if menu == "Inicio estratégico":
        _topbar()
        _banner_ia()
        _kpi_row()
        st.markdown("---")
        # Subnavigation tabs
        tab = st.tabs(["Resumen ejecutivo", "Por proceso", "Analítica IA", "Auditorías"])
        with tab[0]:
            _draw_charts()
            _indicator_modal()
        with tab[1]:
            st.write("Vista Resumen por proceso (mock)")
        with tab[2]:
            st.write("Vista Analítica IA (mock)")
        with tab[3]:
            st.write("Vista Auditorías (mock)")

    elif menu == "Resumen por procesos":
        st.title("Resumen por procesos")
        st.write("Esta sección proporciona un resumen por procesos.")

    elif menu == "Seguimiento operativo":
        st.title("Seguimiento operativo")
        st.write("Panel de seguimiento operativo.")


if __name__ == "__main__":
    # initialize session flags
    if "show_ia" not in st.session_state:
        st.session_state.show_ia = False
    # inject styles
    try:
        with open("streamlit_app/styles/styles.css", "r", encoding="utf-8") as f:
            css = f.read()
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception:
        pass
    main()
