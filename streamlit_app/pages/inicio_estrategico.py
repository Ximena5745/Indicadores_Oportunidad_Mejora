"""
Página principal: Inicio Estratégico

Contiene layout principal con sidebar, topbar, KPI cards, banner IA, tabs y gráficos Plotly.
"""
import streamlit as st
import pandas as pd
from components import topbar, sidebar, kpi_card, banner_ia, modal, plotly_vis, exporter
from utils import data_mocks, styles


def run():
    styles.load_css()
    filters = sidebar.get_filters()
    topbar.render_topbar("Inicio Estratégico")

    # Cargar mocks
    irip = data_mocks.get_irip_data()
    dad = data_mocks.get_dad_data()
    cmi = data_mocks.get_cmi_data()
    units_geo = data_mocks.get_units_geo()

    # Aplicar filtros a datasets por unidad y rango de fechas
    selected_units = filters.get('unidades', [])
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')

    if selected_units:
        irip = irip[irip['unidad'].isin(selected_units)]
        dad = dad[dad['unidad'].isin(selected_units)]
        cmi = cmi[cmi['unidad'].isin(selected_units)]

    if start_date and end_date:
        irip = irip[(irip['fecha'].dt.date >= start_date) & (irip['fecha'].dt.date <= end_date)]
        dad = dad[(dad['fecha'].dt.date >= start_date) & (dad['fecha'].dt.date <= end_date)]
        cmi = cmi[(cmi['fecha'].dt.date >= start_date) & (cmi['fecha'].dt.date <= end_date)]

    # Primera fila: KPIs
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        kpi_card.kpi_card("IRIP - Cumplimiento", f"{irip['cumplimiento'].mean():.1f}%", "+1.2%")
    with kpi_cols[1]:
        kpi_card.kpi_card("DAD - Avance", f"{dad['avance'].mean():.1f}%", "-0.5%")
    with kpi_cols[2]:
        kpi_card.kpi_card("CMI - Score", f"{cmi['score'].mean():.1f}", "+0.8")
    with kpi_cols[3]:
        banner_ia.banner_ia("Recomendación IA: Revisar indicadores con caída sostenida")

    st.markdown("---")

    # Tabs con visualizaciones
    tabs = st.tabs(["Visión General", "Tendencias", "Riesgos / Alertas"])

    with tabs[0]:
        st.subheader("Visión General por conjunto")
        fig = plotly_vis.plot_overview(irip, dad, cmi)
        st.plotly_chart(fig, use_container_width=True)
        # Mostrar mapa de unidades
        st.subheader("Mapa de Unidades")
        map_fig = plotly_vis.plot_map(units_geo, value_col='valor')
        st.plotly_chart(map_fig, use_container_width=True)

        # Export buttons para la vista general
        exporter.download_csv(pd.concat([irip.head(10), dad.head(10), cmi.head(10)], ignore_index=True), filename='vista_general.csv')
        exporter.download_pdf([fig, map_fig], filename='vista_general.pdf')

    with tabs[1]:
        st.subheader("Tendencias IRIP")
        fig2 = plotly_vis.plot_trend(irip, index_col='fecha', value_col='cumplimiento')
        st.plotly_chart(fig2, use_container_width=True)
        # Heatmap de cumplimiento por unidad y fecha (resumido)
        st.subheader("Heatmap - Cumplimiento por Unidad / Fecha")
        if not irip.empty:
            heat = plotly_vis.plot_heatmap(irip.assign(fecha=irip['fecha'].dt.date), x='fecha', y='unidad', z='cumplimiento')
            st.plotly_chart(heat, use_container_width=True)
            exporter.download_pdf([fig2, heat], filename='tendencias_irip.pdf')

    with tabs[2]:
        st.subheader("Indicadores en riesgo")
        riesgos_df = data_mocks.get_riesgos_table(irip, dad, cmi)
        st.dataframe(riesgos_df)
        exporter.download_csv(riesgos_df, filename='riesgos.csv')

        # Drill-down por indicador
        st.markdown('---')
        st.subheader('Drill-down por indicador')
        indicadores = riesgos_df['indicador'].tolist()
        if indicadores:
            sel = st.selectbox('Seleccionar indicador', opciones := indicadores)
            if sel:
                detalle = data_mocks.get_indicator_detail(sel, days=60)
                st.markdown(f"### {detalle['nombre']}")
                st.write(detalle['descripcion'])
                # plot tendencia
                fig_detail = plotly_vis.plot_trend(detalle['valores'], index_col='fecha', value_col='valor')
                st.plotly_chart(fig_detail, use_container_width=True)
                st.write(detalle['valores'].head(20))
                # Exportes para indicador
                exporter.download_csv(detalle['valores'], filename=f"detalle_{sel}.csv")
                metadata = {'Indicador': sel, 'Periodo': f"{start_date} - {end_date}", 'Unidades': ','.join(selected_units) if selected_units else 'Todas'}
                exporter.download_pdf([fig_detail], filename=f"detalle_{sel}.pdf", title=f"Detalle {sel}", table_df=detalle['valores'], metadata=metadata)

    # Modal de detalle por indicador (ejemplo usando st.modal)
    if st.button("Ver detalle ejemplo - Indicador X"):
        with st.modal("Detalle del Indicador"):
            detalle = data_mocks.get_indicator_detail()
            modal.show_indicator_modal(detalle)
