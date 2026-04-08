import streamlit as st

class KPIRow:
    def __init__(self, kpis=None):
        self.kpis = kpis or [
            ("Total indicadores", 387, "Kawak + API", "info"),
            ("En peligro", 20, "+19 vs ant. · 5.2%", "danger"),
            ("En alerta", 24, "+21 vs ant. · 6.2%", "warning"),
            ("Cumplimiento", 85, "+70 vs ant. · 22%", "success"),
            ("Sobrecumplimiento", 115, "+108 vs ant. · 29.7%", "info"),
        ]

    def render(self):
        cols = st.columns(len(self.kpis))
        for col, (title, value, sub, tone) in zip(cols, self.kpis):
            with col:
                st.markdown(
                    f"<div class='kpi-card {tone}'><div class='label'>{title}</div><div class='value'>{value}</div><div class='sub'>{sub}</div></div>",
                    unsafe_allow_html=True,
                )


def render_kpi_row(kpis=None):
    return KPIRow(kpis).render()
