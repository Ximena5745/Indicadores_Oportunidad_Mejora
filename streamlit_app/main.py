import streamlit as st
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Sistema de Indicadores", layout="wide")

def main():
    # Configuración del sidebar
    with st.sidebar:
        st.title("Sistema de Indicadores")
        st.markdown("Politécnico Grancolombiano · v2.0 Estratégico")
        st.markdown("---")

        # Menú principal actualizado con solo 3 opciones
        menu = option_menu(
            menu_title="Navegación",
            options=["Inicio estratégico", "Resumen por procesos", "Seguimiento operativo"],
            icons=["house", "bar-chart", "clipboard-check"],
            menu_icon="cast",
            default_index=0,
        )

    # Lógica de navegación actualizada
    if menu == "Inicio estratégico":
        st.title("Inicio estratégico")
        st.write("Esta sección proporciona un resumen estratégico del sistema.")

    elif menu == "Resumen por procesos":
        st.title("Resumen por procesos")
        st.write("Esta sección proporciona un resumen por procesos.")

    import streamlit as st
    from streamlit_option_menu import option_menu
    import pandas as pd
    import plotly.express as px
    import numpy as np


    st.set_page_config(page_title="Sistema de Indicadores", layout="wide")


    def _topbar():
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


    def _banner_ia():
        container = st.container()
        with container:
            c1, c2 = st.columns([8, 1])
            with c1:
                st.markdown(
                    "**IA detectó:** 9 indicadores con riesgo alto (IRIP >70%) · 3 anomalías (z-score>3) · 7 metas fuera de rango"
                )
            with c2:
                if st.button("Ver detalle IA ↗"):
                    st.session_state.show_ia = True


    def _kpi_row():
        kpis = [
            ("Total indicadores", 387, "Kawak + API", "#04122e"),
            ("En peligro", 20, "+19 vs ant. · 5.2%", "#ff3b30"),
            ("En alerta", 24, "+21 vs ant. · 6.2%", "#ffab00"),
            ("Cumplimiento", 85, "+70 vs ant. · 22%", "#00c853"),
            ("Sobrecumplimiento", 115, "+108 vs ant. · 29.7%", "#00b8d4"),
        ]
        cols = st.columns(5)
        for col, (title, value, sub, color) in zip(cols, kpis):
            with col:
                st.markdown(f"**{title}**")
                st.markdown(f"<div style='font-size:24px;color:{color};font-weight:700'>{value}</div>", unsafe_allow_html=True)
                st.caption(sub)


    def _mock_timeseries():
        dates = pd.date_range(end=pd.Timestamp("2026-04-07"), periods=12, freq="M")
        df = pd.DataFrame({"date": dates, "value": np.random.randint(60, 100, size=len(dates))})
        return df


    def _draw_charts():
        df = _mock_timeseries()
        fig = px.bar(df, x="date", y="value", labels={"value": "Desempeño"}, title="Curva de desempeño institucional")
        st.plotly_chart(fig, use_container_width=True)

        # Semáforo
        st.markdown("### Semáforo global")
        sem = pd.DataFrame({"estado": ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento"], "valor": [20, 24, 85, 115]})
        fig2 = px.pie(sem, names="estado", values="valor", color_discrete_map={"Peligro": "#ff3b30", "Alerta": "#ffab00", "Cumplimiento": "#00c853", "Sobrecumplimiento": "#00b8d4"})
        st.plotly_chart(fig2, use_container_width=True)


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
        main()
