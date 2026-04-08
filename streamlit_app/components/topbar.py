import streamlit as st

class Topbar:
    def __init__(self, title="Inicio estratégico", subtitle="Dic 2025 · 387 indicadores · Generado 07/04/2026"):
        self.title = title
        self.subtitle = subtitle

    def render(self):
        st.markdown(
            "<div class='topbar-card'>"
            "<div class='topbar-left'><div class='title'>{}</div><div class='muted'>{}</div></div>"
            "</div>".format(self.title, self.subtitle),
            unsafe_allow_html=True,
        )
        cols = st.columns([2.2, 1, 1, 1, 1])
        with cols[0]:
            st.markdown("<div class='topbar-actions'>Filtros de vista</div>", unsafe_allow_html=True)
        with cols[1]:
            year = st.selectbox("Año", [2026, 2025, 2024], index=0, key='topbar_year')
        with cols[2]:
            month = st.selectbox("Mes", ["Todos", "Ene", "Feb", "Mar", "Abr"], index=0, key='topbar_month')
        with cols[3]:
            area = st.selectbox("Área", ["Todas las áreas", "Académica", "Administrativa"], index=0, key='topbar_area')
        with cols[4]:
            if st.button("Actualizar datos", key='topbar_refresh'):
                st.experimental_rerun()
        return dict(year=year, month=month, area=area)


def render_topbar(default_year=2026):
    return Topbar().render()
