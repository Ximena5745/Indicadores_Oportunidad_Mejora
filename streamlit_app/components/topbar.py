import streamlit as st


def render_topbar(title: str):
    """Renderiza un topbar simple con título y espacio para acciones."""
    cols = st.columns([1, 4, 1])
    with cols[1]:
        st.markdown(f"### {title}")
