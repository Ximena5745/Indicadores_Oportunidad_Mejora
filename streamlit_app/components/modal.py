import streamlit as st


def show_indicator_modal(detail: dict):
    """Muestra detalles de un indicador dentro de un modal simple."""
    st.markdown(f"### {detail.get('nombre')}")
    st.write(detail.get('descripcion'))
    st.write("Últimos valores:")
    st.table(detail.get('valores').head())
