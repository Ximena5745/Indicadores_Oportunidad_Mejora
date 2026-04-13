"""
Ejemplo de integración de componentes visuales en Resumen General
Este archivo muestra cómo usar los nuevos componentes creados
"""

import streamlit as st
import pandas as pd
import numpy as np

# Importar componentes del sistema de diseño
from streamlit_app.styles.design_system import COLORS, ICONS, get_color_for_cumplimiento
from streamlit_app.components.hero_section import render_hero_section, render_alert_banner
from streamlit_app.components.interactive_cards import (
    render_metric_card, 
    render_kpi_row,
    render_indicator_status_card,
    render_expandable_card
)
from streamlit_app.components.heatmap_chart import (
    render_performance_heatmap,
    render_sunburst_hierarchy,
    render_treemap_drilldown,
    render_gauge_chart
)
from streamlit_app.components.modals import render_indicator_detail_modal, show_toast_notification


def render_resumen_general_nuevo():
    """
    Ejemplo de cómo integrar los nuevos componentes visuales
    en la página de Resumen General
    """
    
    # ============================================
    # SECCIÓN 1: HERO CON ISI Y ALERTAS
    # ============================================
    
    # Calcular ISI (ejemplo)
    isi_value = 78.5
    alertas = [
        "5 indicadores en peligro en Línea de Investigación",
        "3 reportes vencidos del proceso de Admisiones",
        "2 acciones de mejora próximas a vencer"
    ]
    
    render_hero_section(isi_value, alertas, linea="Docencia")
    
    # ============================================
    # SECCIÓN 2: KPIs CON CARDS INTERACTIVAS
    # ============================================
    
    st.markdown("### 📊 Métricas Institucionales")
    
    # Definir métricas con datos de ejemplo
    metrics = [
        {
            "title": "Indicadores Activos",
            "value": "142",
            "trend": "up",
            "trend_value": "+5",
            "icon": "🎯",
            "color": COLORS["primary"],
            "sparkline_data": [135, 138, 140, 139, 141, 142]
        },
        {
            "title": "Cumplimiento Promedio",
            "value": "78.5%",
            "trend": "down",
            "trend_value": "-2.3%",
            "icon": "📈",
            "color": COLORS["success"],
            "sparkline_data": [82, 81, 80, 79, 78, 78.5]
        },
        {
            "title": "Alertas Críticas",
            "value": "8",
            "trend": "up",
            "trend_value": "+3",
            "icon": "🚨",
            "color": COLORS["danger"],
            "sparkline_data": [5, 5, 6, 7, 7, 8]
        },
        {
            "title": "Acciones de Mejora",
            "value": "24",
            "trend": "up",
            "trend_value": "+12",
            "icon": "✅",
            "color": COLORS["info"],
            "sparkline_data": [12, 15, 18, 20, 22, 24]
        }
    ]
    
    # Renderizar fila de KPIs
    render_kpi_row(metrics, columns=4)
    
    # ============================================
    # SECCIÓN 3: MAPA DE CALOR DE CUMPLIMIENTO
    # ============================================
    
    st.markdown("---")
    st.markdown("### 🗺️ Mapa de Calor - Cumplimiento por Línea y Período")
    
    # Crear datos de ejemplo para el heatmap
    np.random.seed(42)
    periodos = ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06']
    lineas = ['Docencia', 'Investigación', 'Extensión', 'Gobierno', 'Internacionalización']
    
    heatmap_data = []
    for linea in lineas:
        for periodo in periodos:
            heatmap_data.append({
                'Linea': linea,
                'Periodo': periodo,
                'cumplimiento_pct': np.random.uniform(60, 95)
            })
    
    df_heatmap = pd.DataFrame(heatmap_data)
    
    # Renderizar heatmap
    fig_heatmap = render_performance_heatmap(
        df_heatmap,
        x_col='Periodo',
        y_col='Linea',
        value_col='cumplimiento_pct',
        title="",
        height=400
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # ============================================
    # SECCIÓN 4: TREEMAP JERÁRQUICO
    # ============================================
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🔍 Explorador Jerárquico de Indicadores")
        
        # Datos de ejemplo para treemap
        treemap_data = []
        for linea in lineas:
            objetivos = [f"Objetivo {i+1}" for i in range(3)]
            for objetivo in objetivos:
                indicadores = [f"Indicador {i+1}" for i in range(4)]
                for indicador in indicadores:
                    treemap_data.append({
                        'Linea': linea,
                        'Objetivo': objetivo,
                        'Indicador': indicador,
                        'cumplimiento_pct': np.random.uniform(50, 110)
                    })
        
        df_treemap = pd.DataFrame(treemap_data)
        
        fig_treemap = render_treemap_drilldown(
            df_treemap,
            path=['Linea', 'Objetivo', 'Indicador'],
            value='cumplimiento_pct',
            color='cumplimiento_pct',
            title="",
            height=500
        )
        st.plotly_chart(fig_treemap, use_container_width=True)
    
    with col2:
        st.markdown("### 💡 Insights")
        
        st.markdown(f"""
        **Análisis del período:**
        
        🔴 **Áreas críticas:**
        - Investigación: 65% promedio
        - 3 indicadores en peligro
        
        🟡 **Requieren atención:**
        - Extensión: Tendencia a la baja
        - 5 indicadores en alerta
        
        🟢 **Buen desempeño:**
        - Docencia: 89% cumplimiento
        - Gobierno: Estable
        
        **Recomendaciones:**
        1. Priorizar acciones en Investigación
        2. Revisar procesos de Extensión
        3. Mantener estrategias de Docencia
        """)
        
        # Botón para mostrar notificación
        if st.button("📊 Generar Reporte", type="primary"):
            show_toast_notification(
                "Reporte generado exitosamente",
                type_="success",
                duration=4000
            )
    
    # ============================================
    # SECCIÓN 5: INDICADORES DESTACADOS
    # ============================================
    
    st.markdown("---")
    st.markdown("### ⭐ Indicadores Destacados")
    
    # Mostrar algunos indicadores con cards de estado
    indicadores_ejemplo = [
        {
            "codigo": "IND-DOC-001",
            "nombre": "Tasa de graduación - Pregrado",
            "meta": 85,
            "ejecucion": 87,
            "cumplimiento": 102.4,
            "estado": "Sobrecumplimiento",
            "responsable": "Vicerrectoría Académica",
            "proceso": "Gestión Curricular",
            "linea": "Docencia"
        },
        {
            "codigo": "IND-INV-003",
            "nombre": "Producción científica indexada",
            "meta": 120,
            "ejecucion": 78,
            "cumplimiento": 65.0,
            "estado": "Peligro",
            "responsable": "Vicerrectoría de Investigación",
            "proceso": "Gestión de Investigación",
            "linea": "Investigación"
        },
        {
            "codigo": "IND-EXT-002",
            "nombre": "Participación en proyectos de extensión",
            "meta": 500,
            "ejecucion": 425,
            "cumplimiento": 85.0,
            "estado": "Cumplimiento",
            "responsable": "Vicerrectoría de Extensión",
            "proceso": "Gestión de Extensión",
            "linea": "Extensión"
        }
    ]
    
    cols = st.columns(3)
    for idx, indicador in enumerate(indicadores_ejemplo):
        with cols[idx]:
            render_indicator_status_card(indicador)
            
            # Botón para abrir modal
            if st.button(f"Ver detalle {indicador['codigo']}", key=f"btn_{idx}"):
                # En una implementación real, esto abriría el modal
                st.session_state[f"modal_{idx}"] = True
    
    # ============================================
    # SECCIÓN 6: GAUGES POR LÍNEA ESTRATÉGICA
    # ============================================
    
    st.markdown("---")
    st.markdown("### 🎯 Cumplimiento por Línea Estratégica")
    
    gauge_cols = st.columns(5)
    lineas_data = [
        ("Docencia", 89),
        ("Investigación", 65),
        ("Extensión", 78),
        ("Gobierno", 82),
        ("Internacionalización", 71)
    ]
    
    for col, (linea, valor) in zip(gauge_cols, lineas_data):
        with col:
            fig_gauge = render_gauge_chart(
                value=valor,
                title=linea,
                min_val=0,
                max_val=100,
                threshold=80,
                height=250
            )
            st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
    
    # ============================================
    # SECCIÓN 7: CARD EXPANDIBLE CON DETALLES
    # ============================================
    
    st.markdown("---")
    
    # Contenido para card expandible
    detalle_html = """
    <div style="padding: 1rem;">
        <h4>📈 Análisis Detallado</h4>
        <p>El período actual muestra una mejora general en los indicadores de Docencia, 
        mientras que Investigación requiere atención inmediata.</p>
        
        <ul>
            <li><strong>Docencia:</strong> 89% cumplimiento (+5% vs mes anterior)</li>
            <li><strong>Investigación:</strong> 65% cumplimiento (-8% vs mes anterior)</li>
            <li><strong>Extensión:</strong> 78% cumplimiento (-2% vs mes anterior)</li>
        </ul>
        
        <h4>🎯 Acciones Recomendadas</h4>
        <ol>
            <li>Convocar reunión de seguimiento con Vicerrectoría de Investigación</li>
            <li>Revisar plan de acción del indicador IND-INV-003</li>
            <li>Documentar buenas prácticas de Docencia para replicar</li>
        </ol>
    </div>
    """
    
    render_expandable_card(
        title="Análisis Detallado y Recomendaciones",
        content_html=detalle_html,
        icon="📋",
        default_expanded=False
    )
    
    # ============================================
    # SECCIÓN 8: ALERTAS Y NOTIFICACIONES
    # ============================================
    
    st.markdown("---")
    st.markdown("### 🔔 Alertas del Sistema")
    
    # Mostrar alertas con el componente de banner
    render_alert_banner(
        message="Se detectaron 3 indicadores con tendencia a la baja en los últimos 2 meses",
        type_="warning",
        dismissible=True
    )
    
    render_alert_banner(
        message="El proceso de acreditación está al día con el 95% de indicadores reportados",
        type_="success",
        dismissible=True
    )
    
    # Botones para probar notificaciones
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("✅ Éxito", type="secondary"):
            show_toast_notification("Operación completada", type_="success")
    
    with col2:
        if st.button("⚠️ Advertencia", type="secondary"):
            show_toast_notification("Revisar configuración", type_="warning")
    
    with col3:
        if st.button("🚨 Error", type="secondary"):
            show_toast_notification("Error al procesar datos", type_="danger")
    
    with col4:
        if st.button("ℹ️ Info", type="secondary"):
            show_toast_notification("Nueva actualización disponible", type_="info")


# Ejecutar si se corre directamente
if __name__ == "__main__":
    st.set_page_config(
        page_title="Resumen General - Sistema de Indicadores",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    render_resumen_general_nuevo()
