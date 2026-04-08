import streamlit as st
from streamlit_app.components import KPIRow
from streamlit_app.services.data_service import DataService


def _indicator_modal(ind_name="Indicador ejemplo"):
    if st.button(f"Abrir detalle: {ind_name}", key=f"modal_btn_{ind_name}"):
        with st.modal("Detalle indicador"):
            st.header(ind_name)
            tabs = st.tabs(["IRIP", "DAD", "Coherencia", "Eficiencia OM"])
            with tabs[0]:
                st.write("Contenido IRIP (mock)")
            with tabs[1]:
                st.write("Contenido DAD (mock)")
            with tabs[2]:
                st.write("Contenido Coherencia (mock)")
            with tabs[3]:
                st.write("Contenido Eficiencia OM (mock)")


def render():
    st.title("Resumen por procesos")
    st.write("Seleccione un proceso para ver detalle. Esta vista contiene 6 tabs por proceso.")

    processes = ["Gestión del Talento Humano", "Gestión Académica", "Investigación", "Administrativo"]
    proc = st.selectbox("Proceso", processes)

    tabs = st.tabs(["📊 Indicadores", "📋 Reporte", "✅ Calidad", "🔍 Auditoría", "💡 Propuestos", "🤖 Análisis IA"])
    with tabs[0]:
        st.markdown("### Indicadores")
        KPIRow().render()
        ds = DataService()
        df = ds.get_timeseries()
        st.dataframe(df.head())
        _indicator_modal("Indicador ejemplo 1")

    with tabs[1]:
        st.write("Reporte de indicadores (mock): exportar, filtrar y descargar CSV")

    with tabs[2]:
        st.write("Heatmap de calidad (mock)")

    with tabs[3]:
        st.write("Resultados de auditoría integrados (mock)")

    with tabs[4]:
        st.write("Indicadores propuestos y notas")

    with tabs[5]:
        st.write("Análisis IA: IRIP / DAD / CMI (gráficas mock)")
