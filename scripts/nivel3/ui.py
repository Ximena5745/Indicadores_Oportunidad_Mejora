import streamlit as st
import pandas as pd
from scripts.nivel3 import data, om, frequency, trace, qc
from scripts.plot_templates import kanban_counts, sparkline_series
import plotly.graph_objects as go
import plotly.express as px


def render_cmi_by_process(latest: pd.DataFrame, mapping: pd.DataFrame):
    """Renderiza una vista CMI agregada por proceso: treemap + scorecards por proceso."""
    st.subheader('CMI por Proceso')
    if latest is None or latest.empty:
        st.info('No hay datos consolidados para CMI')
        return
    # Asegurar tipos
    df = latest.copy()
    if 'Proceso' not in df.columns:
        st.info('No hay columna `Proceso` en los datos consolidados')
        return
    # Coerce numeric cumplimiento
    if 'Cumplimiento' in df.columns:
        df['Cumplimiento'] = pd.to_numeric(df['Cumplimiento'], errors='coerce')
    else:
        df['Cumplimiento'] = None

    agg = df.groupby('Proceso').agg(
        indicadores_count=('Id', 'nunique'),
        cumplimiento_mean=('Cumplimiento', 'mean'),
    ).reset_index()
    agg['cumplimiento_mean'] = agg['cumplimiento_mean'].round(2)

    # Scorecards: mostrar primeros 4 procesos
    top4 = agg.sort_values('indicadores_count', ascending=False).head(4)
    cols = st.columns(len(top4) if len(top4) > 0 else 1)
    for i, row in enumerate(top4.to_dict(orient='records')):
        with cols[i]:
            st.metric(row['Proceso'], f"{row['cumplimiento_mean']}%", delta=None)

    # Treemap
    # Si el mapping contiene Objetivo/Linea, mostrar treemap jerárquico PDI (Lineas -> Objetivos)
    try:
        if mapping is not None and 'Id' in mapping.columns and 'Linea' in mapping.columns:
            merged = df.merge(mapping[['Id'] + [c for c in ['Linea', 'Objetivo'] if c in mapping.columns]], on='Id', how='left')
            if 'Objetivo' in merged.columns:
                counts = merged.groupby(['Linea', 'Objetivo']).agg(indicadores_count=('Id', 'nunique'), cumplimiento_mean=('Cumplimiento', 'mean')).reset_index()
                counts['cumplimiento_mean'] = counts['cumplimiento_mean'].round(2)
                n_lineas = counts['Linea'].nunique()
                n_obj = counts['Objetivo'].nunique()
                st.markdown(f"**PDI detectado:** {n_lineas} líneas estratégicas, {n_obj} objetivos estratégicos")
                fig = px.treemap(counts, path=['Linea', 'Objetivo'], values='indicadores_count', color='cumplimiento_mean', color_continuous_scale='RdYlGn', hover_data=['indicadores_count','cumplimiento_mean'])
                st.plotly_chart(fig, use_container_width=True)
                return
    except Exception:
        pass

    if not agg.empty:
        fig = px.treemap(agg, path=['Proceso'], values='indicadores_count', color='cumplimiento_mean', color_continuous_scale='RdYlGn', hover_data=['indicadores_count','cumplimiento_mean'])
        st.plotly_chart(fig, use_container_width=True)


def render_cmi_estrategico(latest: pd.DataFrame, mapping: pd.DataFrame):
    """Renderiza el CMI Estratégico (PDI): Linea -> Objetivo -> Meta estratégica y desglose de indicadores."""
    st.subheader('CMI Estratégico (PDI)')
    if mapping is None or mapping.empty:
        st.info('No hay mapeo CMI disponible (indicadores_cmi_mapping_v2.csv)')
        return

    # Asegurar columnas clave
    have = mapping.columns.tolist()
    for req in ['Linea', 'Objetivo', 'Meta']:
        if req not in have:
            st.info(f'El mapeo no contiene la columna `{req}`; revisar `Indicadores por CMI.xlsx`.')
            return

    # Agrupar por Linea/Objetivo
    map_df = mapping.copy()
    map_df['Meta'] = pd.to_numeric(map_df['Meta'], errors='coerce')
    agg = map_df.groupby(['Linea', 'Objetivo']).agg(indicadores_count=('Id', 'nunique'), meta_mean=('Meta', 'mean')).reset_index()
    agg['meta_mean'] = agg['meta_mean'].round(2)

    # Treemap por Linea -> Objetivo (valor = cantidad de indicadores)
    fig = px.treemap(agg, path=['Linea', 'Objetivo'], values='indicadores_count', color='meta_mean', color_continuous_scale='Blues', hover_data=['indicadores_count','meta_mean'])
    st.plotly_chart(fig, use_container_width=True)

    # Desglose: al seleccionar Linea y Objetivo mostrar indicadores y su último cumplimiento
    linea_sel = st.selectbox('Seleccionar Línea estratégica', options=sorted(map_df['Linea'].dropna().unique()))
    objetivos = sorted(map_df.loc[map_df['Linea'] == linea_sel, 'Objetivo'].dropna().unique())
    objetivo_sel = st.selectbox('Seleccionar Objetivo estratégico', options=objetivos)

    subset = map_df[(map_df['Linea'] == linea_sel) & (map_df['Objetivo'] == objetivo_sel)]
    ids = subset['Id'].astype(str).tolist()

    # Tomar último cumplimiento desde latest
    latest_df = latest.copy() if latest is not None else pd.DataFrame()
    if not latest_df.empty and 'Id' in latest_df.columns:
        latest_df['Id'] = latest_df['Id'].astype(str)
        sel = latest_df[latest_df['Id'].isin(ids)][['Id','Indicador'] + ([c for c in ['Cumplimiento','Fecha','Meta'] if c in latest_df.columns])]
        st.markdown(f'Indicadores en {linea_sel} → {objetivo_sel}: {len(sel)}')
        st.dataframe(sel.sort_values(by=['Cumplimiento'], ascending=True).head(200))
    else:
        st.write(subset[['Id','Indicador','Meta']].rename(columns={'Meta':'Meta Estratégica'}))


def render_summary(kpis: dict):
    cols = st.columns(len(kpis))
    for i, (k, v) in enumerate(kpis.items()):
        with cols[i]:
            st.metric(k, v)


def render_kanban(df_status: pd.DataFrame):
    # df_status must contain 'Estado'
    if df_status is None or df_status.empty:
        st.info('No hay datos para el Kanban')
        return
    fig = kanban_counts(df_status.rename(columns={'Estado':'Status'}))
    st.plotly_chart(fig, use_container_width=True)


def render_table(df: pd.DataFrame):
    if df is None or df.empty:
        st.info('No hay registros para mostrar')
        return
    cols = ['Id','Indicador','Linea','Proceso','Periodicidad','Fecha','Cumplimiento']
    present = [c for c in cols if c in df.columns]
    st.dataframe(df[present].head(200))


def render_om_dashboard():
    st.subheader('Gestión OM')
    oms = om.list_oms()
    st.write(f'Total OM: {len(oms)}')
    with st.expander('Crear nueva OM'):
        with st.form('form_new_om'):
            id_ind = st.text_input('ID Indicador')
            titulo = st.text_input('Título')
            desc = st.text_area('Descripción')
            resp = st.text_input('Responsable')
            fc = st.date_input('Fecha compromiso', value=None)
            submitted = st.form_submit_button('Crear OM')
            if submitted:
                fc_s = fc.isoformat() if fc else None
                obj = om.create_om(id_ind, titulo, desc, resp, fecha_compromiso=fc_s)
                st.success('OM creada')
    if oms:
        for o in oms[:50]:
            st.write(f"- {o.get('id_om')} | {o.get('indicador_id')} | {o.get('titulo')} | {o.get('estado')}")


def render_qc_panel():
    st.subheader('Control de Calidad (QC)')
    df_qc = qc.aggregate_qc()
    if df_qc.empty:
        st.info('No hay artefactos de QC disponibles')
        return
    st.dataframe(df_qc)


def main():
    # Deshabilitando configuración de página para evitar interferencias
    # st.set_page_config(layout='wide', page_title='Tablero Estratégico Operativo (Nivel 3)')
    st.title('Tablero Estratégico Operativo — Nivel 3')

    # Cargar datos
    ts = data.load_timeseries_csv()
    latest = data.load_latest_csv()
    mapping = data.load_mapping()

    # Calcular expected ids y estado de reporte
    expected = frequency.compute_expected_ids_for_period(0,0,mapping)
    status_df = frequency.compute_reporting_status(latest, expected, window_months=3)

    # KPIs básicos
    kpis = {
        '% reportados': f"{(status_df['Estado']=='Actualizado').sum()}/{len(status_df)}" if not status_df.empty else '0/0',
        '% OM abiertos': '—',
        '% registros fallidos QC': '—',
    }

    tab_cmi_estr, tab_cmi_proc, tab_res, tab_kanban, tab_tabla, tab_om, tab_qc = st.tabs(['CMI Estratégico (PDI)','CMI por Proceso','Resumen','Kanban','Consolidado','OM','QC'])

    with tab_cmi_estr:
        render_cmi_estrategico(latest, mapping)

    with tab_cmi_proc:
        render_cmi_by_process(latest, mapping)

    with tab_res:
        render_summary(kpis)
        st.markdown('#### Mapa de cobertura (por Linea)')
        if mapping is not None and 'Linea' in mapping.columns:
            counts = mapping['Linea'].value_counts().reset_index()
            counts.columns = ['Linea','count']
            fig = go.Figure(go.Bar(x=counts['Linea'], y=counts['count']))
            st.plotly_chart(fig, use_container_width=True)

    with tab_kanban:
        render_kanban(status_df)

    with tab_tabla:
        render_table(latest)

    with tab_om:
        render_om_dashboard()

    with tab_qc:
        render_qc_panel()
