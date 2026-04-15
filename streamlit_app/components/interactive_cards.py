"""
Interactive Cards Component
Tarjetas interactivas con efectos hover, tendencias y acciones
"""

import streamlit as st
import plotly.graph_objects as go
from ..styles.design_system import (
    COLORS, GRADIENTS, SHADOWS, ICONS, 
    get_color_for_cumplimiento, get_icon_for_estado
)
from ..styles.design_system import get_line_color, get_palette_for_chart


def render_metric_card(
    title, 
    value, 
    subtitle=None,
    trend=None, 
    trend_value=None, 
    icon="📊", 
    color=None,
    linea=None,
    sparkline_data=None,
    on_click=None,
    size="normal"
):
    """
    Renderiza una tarjeta de métrica interactiva con efectos hover.
    
    Args:
        title: str - Título de la métrica
        value: str - Valor principal
        subtitle: str - Subtítulo opcional
        trend: str - 'up', 'down', 'flat' o None
        trend_value: str - Valor de tendencia (ej: "+5%")
        icon: str - Emoji o icono
        color: str - Color de acento (hex)
        sparkline_data: list - Datos para sparkline opcional
        on_click: callable - Función al hacer click
        size: str - 'small', 'normal', 'large'
    """
    if color is None:
        # Priorizar color de línea si se proporciona
        if linea:
            color = get_line_color(linea)
        else:
            color = COLORS["primary"]
    
    # Determinar icono y color de tendencia
    trend_config = {
        "up": ("↑", COLORS["success"]),
        "down": ("↓", COLORS["danger"]),
        "flat": ("→", COLORS["gray_500"]),
        None: ("", COLORS["gray_500"])
    }
    trend_icon, trend_color = trend_config.get(trend, trend_config[None])
    
    # Tamaños
    sizes = {
        "small": {"padding": "1rem", "title_size": "0.75rem", "value_size": "1.5rem"},
        "normal": {"padding": "1.5rem", "title_size": "0.85rem", "value_size": "2rem"},
        "large": {"padding": "2rem", "title_size": "1rem", "value_size": "2.5rem"}
    }
    size_config = sizes.get(size, sizes["normal"])
    
    # Generar sparkline si hay datos
    sparkline_html = ""
    if sparkline_data and len(sparkline_data) > 1:
        # Crear mini gráfico SVG
        min_val = min(sparkline_data)
        max_val = max(sparkline_data)
        range_val = max_val - min_val if max_val != min_val else 1
        
        points = []
        width = 100
        height = 30
        for i, val in enumerate(sparkline_data):
            x = (i / (len(sparkline_data) - 1)) * width
            y = height - ((val - min_val) / range_val) * height
            points.append(f"{x},{y}")
        
        path = " ".join(points)
        trend_line_color = COLORS["success"] if sparkline_data[-1] >= sparkline_data[0] else COLORS["danger"]
        
        sparkline_html = f"""
        <svg width="{width}" height="{height}" style="margin-top: 0.75rem;">
            <polyline
                fill="none"
                stroke="{trend_line_color}"
                stroke-width="2"
                points="{path}"
            />
            <circle cx="{points[-1].split(',')[0]}" cy="{points[-1].split(',')[1]}" r="3" fill="{trend_line_color}"/>
        </svg>
        """
    
    # HTML de la tarjeta
    card_html = f"""
    <div style="
        background: white;
        border-radius: 16px;
        padding: {size_config['padding']};
        box-shadow: {SHADOWS['md']};
        border-left: 4px solid {color};
        transition: all 0.3s ease;
        cursor: {'pointer' if on_click else 'default'};
        height: 100%;
        position: relative;
        overflow: hidden;
    " 
    onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='{SHADOWS['xl']}';"
    onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='{SHADOWS['md']}';"
    {'onclick="handleCardClick()"' if on_click else ''}
    >
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
            <div style="
                width: 40px;
                height: 40px;
                background: {color}15;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.25rem;
            ">
                {icon}
            </div>
            
            {f'<div style="display: flex; align-items: center; gap: 0.25rem; color: {trend_color}; font-weight: 600; font-size: 0.85rem;"><span>{trend_icon}</span><span>{trend_value}</span></div>' if trend else ''}
        </div>
        
        <div style="
            font-size: {size_config['title_size']};
            color: {COLORS['text_secondary']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
            font-weight: 500;
        ">
            {title}
        </div>
        
        <div style="
            font-size: {size_config['value_size']};
            font-weight: 700;
            color: {COLORS['text_primary']};
            line-height: 1.2;
        ">
            {value}
        </div>
        
        {f'<div style="font-size: 0.85rem; color: {COLORS["text_secondary"]}; margin-top: 0.25rem;">{subtitle}</div>' if subtitle else ''}
        
        {sparkline_html}
        
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)
    
    # Manejar click con session_state
    if on_click:
        if st.button(f"Click {title}", key=f"card_btn_{title}", style="visibility: hidden;"):
            on_click()


def render_indicator_status_card(indicator_data, show_sparkline=True):
    """
    Tarjeta específica para mostrar el estado de un indicador.
    
    Args:
        indicator_data: dict - Datos del indicador
        show_sparkline: bool - Mostrar sparkline de tendencia
    """
    nombre = indicator_data.get('nombre', 'Indicador')
    cumplimiento = indicator_data.get('cumplimiento', 0)
    meta = indicator_data.get('meta', 0)
    ejecucion = indicator_data.get('ejecucion', 0)
    estado = indicator_data.get('estado', 'Sin dato')
    tendencia = indicator_data.get('tendencia', [])
    
    # Determinar color e icono según estado
    # Si el indicador tiene una 'linea' asociada, priorizamos el color de línea
    linea = indicator_data.get('linea')
    if linea:
        color = get_line_color(linea)
    else:
        color = get_color_for_cumplimiento(cumplimiento)
    icon = get_icon_for_estado(estado)
    
    # Calcular brecha
    brecha = ejecucion - meta
    brecha_pct = (brecha / meta * 100) if meta > 0 else 0
    
    st.markdown(f"""
    <div style="
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: {SHADOWS['md']};
        border-left: 4px solid {color};
        transition: all 0.3s ease;
        cursor: pointer;
        margin-bottom: 1rem;
    "
    onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='{SHADOWS['xl']}';"
    onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='{SHADOWS['md']}';"
    >
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
            <div>
                <div style="font-size: 0.8rem; color: {COLORS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;">
                    {indicator_data.get('codigo', 'IND-001')}
                </div>
                <div style="font-size: 1.1rem; font-weight: 600; color: {COLORS['text_primary']}; line-height: 1.3;">
                    {nombre}
                </div>
            </div>
            
            <div style="
                background: {color}15;
                color: {color};
                padding: 0.4rem 0.8rem;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 0.4rem;
            ">
                <span>{icon}</span>
                <span>{estado}</span>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1rem;">
            <div>
                <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">Meta</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: {COLORS['text_primary']};">{meta:,.0f}</div>
            </div>
            
            <div>
                <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">Ejecución</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: {COLORS['text_primary']};">{ejecucion:,.0f}</div>
            </div>
            
            <div>
                <div style="font-size: 0.75rem; color: {COLORS['text_secondary']}; margin-bottom: 0.25rem;">Cumplimiento</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: {color};">{cumplimiento:.1f}%</div>
            </div>
        </div>
        
        <div style="margin-top: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span style="font-size: 0.8rem; color: {COLORS['text_secondary']};">Progreso hacia meta</span>
                <span style="font-size: 0.8rem; font-weight: 600; color: {color};">{min(cumplimiento, 100):.0f}%</span>
            </div>
            
            <div style="
                width: 100%;
                height: 8px;
                background: {COLORS['gray_200']};
                border-radius: 4px;
                overflow: hidden;
            ">
                <div style="
                    width: {min(cumplimiento, 100)}%;
                    height: 100%;
                    background: {color};
                    border-radius: 4px;
                    transition: width 0.5s ease;
                "></div>
            </div>
        </div>
        
    </div>
    """, unsafe_allow_html=True)


def render_action_card(action_data):
    """
    Tarjeta para mostrar acciones de mejora u OM.
    
    Args:
        action_data: dict - Datos de la acción
    """
    codigo = action_data.get('codigo', 'OM-001')
    descripcion = action_data.get('descripcion', 'Sin descripción')
    responsable = action_data.get('responsable', 'Sin asignar')
    fecha_limite = action_data.get('fecha_limite', 'Sin fecha')
    estado = action_data.get('estado', 'Pendiente')
    progreso = action_data.get('progreso', 0)
    
    # Color según estado
    estado_colors = {
        "Completada": COLORS["success"],
        "En progreso": COLORS["info"],
        "Pendiente": COLORS["warning"],
        "Vencida": COLORS["danger"],
        "Cancelada": COLORS["gray_500"]
    }
    color = estado_colors.get(estado, COLORS["warning"])
    
    st.markdown(f"""
    <div style="
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: {SHADOWS['sm']};
        border: 1px solid {COLORS['gray_200']};
        margin-bottom: 0.75rem;
        transition: all 0.2s ease;
    "
    onmouseover="this.style.boxShadow='{SHADOWS['md']}'; this.style.borderColor='{COLORS['gray_300']}';"
    onmouseout="this.style.boxShadow='{SHADOWS['sm']}'; this.style.borderColor='{COLORS['gray_200']}';"
    >
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
            <div style="font-size: 0.85rem; font-weight: 600; color: {COLORS['primary']};">{codigo}</div>
            <div style="
                background: {color}15;
                color: {color};
                padding: 0.25rem 0.6rem;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 600;
            ">{estado}</div>
        </div>
        
        <div style="font-size: 0.95rem; color: {COLORS['text_primary']}; margin-bottom: 0.75rem; line-height: 1.4;">
            {descripcion}
        </div>
        
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: {COLORS['text_secondary']}; margin-bottom: 0.75rem;">
            <span>👤 {responsable}</span>
            <span>📅 {fecha_limite}</span>
        </div>
        
        <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                <span style="font-size: 0.75rem; color: {COLORS['text_secondary']};">Progreso</span>
                <span style="font-size: 0.75rem; font-weight: 600; color: {color};">{progreso}%</span>
            </div>
            
            <div style="
                width: 100%;
                height: 6px;
                background: {COLORS['gray_200']};
                border-radius: 3px;
                overflow: hidden;
            ">
                <div style="
                    width: {progreso}%;
                    height: 100%;
                    background: {color};
                    border-radius: 3px;
                    transition: width 0.3s ease;
                "></div>
            </div>
        </div>
        
    </div>
    """, unsafe_allow_html=True)


def render_kpi_row(metrics, columns=4):
    """
    Renderiza una fila de KPIs con diseño consistente.
    
    Args:
        metrics: list - Lista de dicts con datos de métricas
        columns: int - Número de columnas
    """
    cols = st.columns(columns)
    
    for idx, metric in enumerate(metrics):
        if idx >= columns:
            break
            
        with cols[idx % columns]:
            render_metric_card(
                title=metric.get('title', 'Métrica'),
                value=metric.get('value', '-'),
                subtitle=metric.get('subtitle'),
                trend=metric.get('trend'),
                trend_value=metric.get('trend_value'),
                icon=metric.get('icon', '📊'),
                color=metric.get('color', COLORS["primary"]),
                sparkline_data=metric.get('sparkline_data'),
                size=metric.get('size', 'normal')
            )


def render_expandable_card(title, content_html, icon="📋", default_expanded=False):
    """
    Tarjeta expandible para mostrar información adicional.
    
    Args:
        title: str - Título de la sección
        content_html: str - Contenido HTML a mostrar
        icon: str - Icono de la sección
        default_expanded: bool - Estado inicial
    """
    expanded_class = "expanded" if default_expanded else ""
    display_style = "block" if default_expanded else "none"
    
    st.markdown(f"""
    <div style="
        background: white;
        border-radius: 12px;
        box-shadow: {SHADOWS['sm']};
        margin-bottom: 1rem;
        overflow: hidden;
    ">
        <div style="
            padding: 1rem 1.25rem;
            background: {COLORS['gray_50']};
            border-bottom: 1px solid {COLORS['gray_200']};
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        "
        onclick="toggleExpand(this)"
        >
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <span style="font-size: 1.25rem;">{icon}</span>
                <span style="font-weight: 600; color: {COLORS['text_primary']};">{title}</span>
            </div>
            <span style="color: {COLORS['text_secondary']}; font-size: 1.25rem; transition: transform 0.2s;">▼</span>
        </div>
        
        <div style="padding: 1.25rem; display: {display_style};">
            {content_html}
        </div>
        
    </div>
    
    <script>
    function toggleExpand(header) {{
        const content = header.nextElementSibling;
        const arrow = header.querySelector('span:last-child');
        
        if (content.style.display === 'none') {{
            content.style.display = 'block';
            arrow.style.transform = 'rotate(180deg)';
        }} else {{
            content.style.display = 'none';
            arrow.style.transform = 'rotate(0deg)';
        }}
    }}
    </script>
    """, unsafe_allow_html=True)


# Exportar funciones
__all__ = [
    "render_metric_card",
    "render_indicator_status_card",
    "render_action_card",
    "render_kpi_row",
    "render_expandable_card",
]
