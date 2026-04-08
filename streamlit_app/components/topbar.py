import streamlit as st

def render_topbar(default_year=2026):
    cols = st.columns([3, 1, 1, 1, 1])
    with cols[0]:
        st.markdown("# Inicio estratégico")
        st.markdown("Dic 2025 · 387 indicadores · Generado 07/04/2026")
    with cols[1]:
        year = st.selectbox("Año", [2026, 2025, 2024], index=0)
    with cols[2]:
        month = st.selectbox("Mes", ["Todos", "Ene", "Feb", "Mar", "Abr"], index=0)
    with cols[3]:
        area = st.selectbox("Área", ["Todas las áreas", "Académica", "Administrativa"], index=0)
    with cols[4]:
        if st.button("Actualizar datos"):
            st.experimental_rerun()
    return dict(year=year, month=month, area=area)
