"""
Hero Section Component
Muestra el Índice de Salud Institucional (ISI) con alertas y gauge interactivo
"""

import streamlit as st
import plotly.graph_objects as go
try:
    from ..styles.design_system import COLORS, GRADIENTS, ICONS, get_line_color
except (ImportError, ValueError):
    from styles.design_system import COLORS, GRADIENTS, ICONS, get_line_color


def render_hero_section(isi_value, alertas, subtitle="Politécnico Grancolombiano", linea=None):
    """
    Renderiza la sección hero con ISI, alertas y gauge semicircular.
    
    Args:
        isi_value: float - Valor del ISI (0-100)
        alertas: list - Lista de mensajes de alerta
        subtitle: str - Subtítulo institucional
    """
    
    # Determinar color según valor ISI
    if isi_value >= 80:
        isi_color = COLORS["success"]
        isi_status = "Saludable"
        isi_icon = "✅"
    elif isi_value >= 60:
        isi_color = COLORS["warning"]
        isi_status = "Requiere atención"
        isi_icon = "⚠️"
    else:
        isi_color = COLORS["danger"]
        isi_status = "Crítico"
        isi_icon = "🚨"

    # Color de acento por línea (si se proporciona) — prioriza identidad de línea
    accent = get_line_color(linea) if linea else isi_color
    
    # CSS personalizado para el hero
    st.markdown(f"""
    <style>
    .hero-container {{
        background: linear-gradient(135deg, {accent} 0%, {COLORS['primary']} 100%);
        border-radius: 20px;
        padding: 2.5rem;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(26, 58, 92, 0.3);
        position: relative;
        overflow: hidden;
    }}
    
    .hero-container::before {{
        content: "";
        position: absolute;
        top: -50%;
        right: -20%;
        width: 60%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        pointer-events: none;
    }}
    
    .hero-title {{
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }}
    
    .hero-subtitle {{
        font-size: 1.1rem;
        opacity: 0.9;
        margin-bottom: 2rem;
        font-weight: 400;
    }}
    
    .isi-display {{
        display: flex;
        align-items: baseline;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }}
    
    .isi-value {{
        font-size: 4rem;
        font-weight: 800;
        line-height: 1;
    }}
    
    .isi-label {{
        font-size: 1rem;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    .isi-status {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(255,255,255,0.2);
        padding: 0.5rem 1rem;
        border-radius: 50px;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
    }}
    
    .alert-ticker {{
        background: rgba(255,255,255,0.15);
        border-radius: 12px;
        padding: 1.25rem;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.2);
    }}
    
    .alert-header {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        font-size: 0.95rem;
    }}
    
    .alert-item {{
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        font-size: 0.9rem;
        opacity: 0.95;
    }}
    
    .alert-item:last-child {{
        border-bottom: none;
    }}
    
    .alert-icon {{
        font-size: 1.1rem;
        flex-shrink: 0;
    }}
    
    .quick-actions {{
        display: flex;
        gap: 0.75rem;
        margin-top: 1.5rem;
        flex-wrap: wrap;
    }}
    
    .quick-action-btn {{
        background: rgba(255,255,255,0.2);
        border: 1px solid rgba(255,255,255,0.3);
        color: white;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }}
    
    .quick-action-btn:hover {{
        background: rgba(255,255,255,0.3);
        transform: translateY(-2px);
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Layout en dos columnas
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Contenido del hero
        alertas_html = ""
        for alerta in alertas[:3]:  # Mostrar máximo 3 alertas
            alertas_html += f'<div class="alert-item"><span class="alert-icon">🔴</span><span>{alerta}</span></div>'
        
        st.markdown(f"""
        <div class="hero-container">
            <div class="hero-title">🏛️ Sistema de Indicadores</div>
            <div class="hero-subtitle">{subtitle}</div>
            
            <div class="isi-display">
                <span class="isi-value">{isi_value:.1f}</span>
                <span class="isi-label">/ 100<br>ISI</span>
            </div>
            
            <div class="isi-status">
                {isi_icon} {isi_status}
            </div>
            
            <div class="alert-ticker">
                <div class="alert-header">
                    🔔 Alertas que requieren atención
                </div>
                {alertas_html}
            </div>
            
            <div class="quick-actions">
                    <a href="#" class="quick-action-btn">📊 Ver detalles</a>
                    <a href="#" class="quick-action-btn">📥 Exportar reporte</a>
                    <a href="#" class="quick-action-btn">⚡ Acciones urgentes</a>
                </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Gauge semicircular con Plotly
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=isi_value,
            number={
                'suffix': "%",
                'font': {'size': 48, 'color': 'white', 'family': 'Inter, sans-serif'},
                'valueformat': '.1f'
            },
            delta={
                'reference': 75,
                'relative': False,
                'valueformat': '.1f',
                'increasing': {'color': COLORS["success"]},
                'decreasing': {'color': COLORS["danger"]},
                'font': {'size': 20, 'color': 'white'}
            },
            gauge={
                'axis': {
                    'range': [0, 100],
                    'tickwidth': 1,
                    'tickcolor': 'rgba(255,255,255,0.5)',
                    'tickfont': {'color': 'rgba(255,255,255,0.7)'}
                },
                'bar': {
                    'color': isi_color,
                    'thickness': 0.75
                },
                'bgcolor': 'rgba(255,255,255,0.1)',
                'borderwidth': 2,
                'bordercolor': 'rgba(255,255,255,0.3)',
                'steps': [
                    {'range': [0, 60], 'color': 'rgba(211,47,47,0.3)'},
                    {'range': [60, 80], 'color': 'rgba(251,175,23,0.3)'},
                    {'range': [80, 100], 'color': 'rgba(67,160,71,0.3)'}
                ],
                'threshold': {
                    'line': {'color': 'white', 'width': 4},
                    'thickness': 0.8,
                    'value': isi_value
                }
            }
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font={'color': 'white', 'family': 'Inter, sans-serif'},
            height=350,
            margin=dict(l=20, r=20, t=50, b=20),
            showlegend=False
        )
        
        # Contenedor con fondo del gradiente
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {accent} 0%, {COLORS['primary']} 100%);
            border-radius: 20px;
            padding: 1rem;
            box-shadow: 0 20px 40px rgba(26, 58, 92, 0.3);
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        ">
        """, unsafe_allow_html=True)
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("</div>", unsafe_allow_html=True)


def render_mini_kpi_card(title, value, trend=None, trend_value=None, icon="📊", color=None):
    """
    Renderiza una mini tarjeta KPI para usar en el hero o secciones.
    
    Args:
        title: str - Título de la métrica
        value: str - Valor a mostrar
        trend: str - 'up', 'down', o None
        trend_value: str - Valor de la tendencia
        icon: str - Emoji o icono
        color: str - Color de acento (hex)
    """
    if color is None:
        color = COLORS["primary"]
    
    trend_html = ""
    if trend:
        trend_icon = "↑" if trend == "up" else "↓"
        trend_color = COLORS["success"] if trend == "up" else COLORS["danger"]
        trend_html = f'<span style="color: {trend_color}; font-weight: 600;">{trend_icon} {trend_value}</span>'
    
    st.markdown(f"""
    <div style="
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 4px solid {color};
        transition: all 0.3s ease;
    " onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 10px 25px rgba(0,0,0,0.15)'" 
    onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.1)'">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
        <div style="font-size: 0.85rem; color: {COLORS["text_secondary"]}; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;">
            {title}
        </div>
        <div style="font-size: 1.75rem; font-weight: 700; color: {COLORS["text_primary"]}; margin-bottom: 0.25rem;">
            {value}
        </div>
        {trend_html}
    </div>
    """, unsafe_allow_html=True)


def render_alert_banner(message, type_="warning", dismissible=True):
    """
    Renderiza un banner de alerta flotante.
    
    Args:
        message: str - Mensaje de alerta
        type_: str - 'success', 'warning', 'danger', 'info'
        dismissible: bool - Si se puede cerrar
    """
    colors = {
        "success": (COLORS["success"], "✅"),
        "warning": (COLORS["warning"], "⚠️"),
        "danger": (COLORS["danger"], "🚨"),
        "info": (COLORS["info"], "ℹ️")
    }
    
    color, icon = colors.get(type_, colors["info"])
    
    st.markdown(f"""
    <div style="
        background: {color}15;
        border-left: 4px solid {color};
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    ">
        <span style="font-size: 1.25rem;">{icon}</span>
        <span style="color: {COLORS["text_primary"]}; flex: 1;">{message}</span>
        {f'<button style="background: none; border: none; cursor: pointer; font-size: 1.25rem; color: {COLORS["gray_500"]};">×</button>' if dismissible else ''}
    </div>
    """, unsafe_allow_html=True)


# Exportar funciones
__all__ = [
    "render_hero_section",
    "render_mini_kpi_card",
    "render_alert_banner",
]
