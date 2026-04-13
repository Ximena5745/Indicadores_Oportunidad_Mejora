"""
Modals and Notifications Component
Ventanas emergentes, modales y notificaciones tipo toast
"""

import streamlit as st
import streamlit.components.v1 as components
from streamlit_app.styles.design_system import COLORS, SHADOWS, ICONS, get_line_color


def render_indicator_detail_modal(indicator_data, modal_id="indicator_modal"):
    """
    Renderiza un modal con detalle completo de un indicador.
    
    Args:
        indicator_data: dict - Datos completos del indicador
        modal_id: str - ID único para el modal
    """
    # Preparar datos
    nombre = indicator_data.get('nombre', 'Indicador')
    codigo = indicator_data.get('codigo', 'IND-001')
    descripcion = indicator_data.get('descripcion', '')
    meta = indicator_data.get('meta', 0)
    ejecucion = indicator_data.get('ejecucion', 0)
    cumplimiento = indicator_data.get('cumplimiento', 0)
    estado = indicator_data.get('estado', 'Sin dato')
    tendencia = indicator_data.get('tendencia', [])
    responsable = indicator_data.get('responsable', 'Sin asignar')
    frecuencia = indicator_data.get('frecuencia', 'Mensual')
    unidad = indicator_data.get('unidad', '')
    proceso = indicator_data.get('proceso', '')
    linea = indicator_data.get('linea', '')
    acciones = indicator_data.get('acciones', [])
    
    # Color según línea si existe, sino por cumplimiento
    if linea:
        color = get_line_color(linea)
    else:
        if cumplimiento >= 100:
            color = COLORS["primary"]
        elif cumplimiento >= 80:
            color = COLORS["success"]
        elif cumplimiento >= 60:
            color = COLORS["warning"]
        else:
            color = COLORS["danger"]
    
    # Generar sparkline SVG
    sparkline_svg = ""
    if tendencia and len(tendencia) > 1:
        min_val = min(tendencia)
        max_val = max(tendencia)
        range_val = max_val - min_val if max_val != min_val else 1
        
        points = []
        width = 300
        height = 80
        for i, val in enumerate(tendencia):
            x = (i / (len(tendencia) - 1)) * width
            y = height - ((val - min_val) / range_val) * height * 0.8 - height * 0.1
            points.append(f"{x:.1f},{y:.1f}")
        
        path = " ".join(points)
        
        # Área bajo la curva
        area_path = f"0,{height} " + path + f" {width},{height}"
        
        sparkline_svg = f"""
        <svg width="100%" height="{height}" viewBox="0 0 {width} {height}" style="margin-top: 1rem;">
            <defs>
                <linearGradient id="areaGradient_{modal_id}" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style="stop-color:{color};stop-opacity:0.3" />
                    <stop offset="100%" style="stop-color:{color};stop-opacity:0.05" />
                </linearGradient>
            </defs>
            
            <polygon points="{area_path}" fill="url(#areaGradient_{modal_id})" />
            
            <polyline
                fill="none"
                stroke="{color}"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
                points="{path}"
            />
            
            <circle cx="{points[0].split(',')[0]}" cy="{points[0].split(',')[1]}" r="5" fill="{color}" />
            <circle cx="{points[-1].split(',')[0]}" cy="{points[-1].split(',')[1]}" r="6" fill="{color}" stroke="white" stroke-width="2"/>
        </svg>
        """
    
    # HTML del modal
    modal_html = f"""
    <div id="{modal_id}" class="modal-overlay" style="display: none;">
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <div class="modal-subtitle">{codigo}</div>
                    <div class="modal-title">{nombre}</div>
                </div>
                <button class="modal-close" onclick="closeModal('{modal_id}')">&times;</button>
            </div>
            
            <div class="modal-body">
                <!-- Métricas principales -->
                <div class="metric-grid">
                    <div class="metric-box" style="border-left-color: {color};">
                        <div class="metric-label">Cumplimiento</div>
                        <div class="metric-value" style="color: {color};">{cumplimiento:.1f}%</div>
                        <div class="metric-status" style="background: {color}20; color: {color};">{estado}</div>
                    </div>
                    
                    <div class="metric-box">
                        <div class="metric-label">Meta</div>
                        <div class="metric-value">{meta:,.0f}</div>
                        <div class="metric-unit">{unidad}</div>
                    </div>
                    
                    <div class="metric-box">
                        <div class="metric-label">Ejecución</div>
                        <div class="metric-value">{ejecucion:,.0f}</div>
                        <div class="metric-unit">{unidad}</div>
                    </div>
                    
                    <div class="metric-box">
                        <div class="metric-label">Brecha</div>
                        <div class="metric-value" style="color: {'#D32F2F' if ejecucion < meta else '#43A047'};">
                            {ejecucion - meta:+,.0f}
                        </div>
                        <div class="metric-unit">{unidad}</div>
                    </div>
                </div>
                
                <!-- Información adicional -->
                <div class="info-section">
                    <div class="info-grid">
                        <div class="info-item">
                            <span class="info-icon">👤</span>
                            <div>
                                <div class="info-label">Responsable</div>
                                <div class="info-value">{responsable}</div>
                            </div>
                        </div>
                        
                        <div class="info-item">
                            <span class="info-icon">📅</span>
                            <div>
                                <div class="info-label">Frecuencia</div>
                                <div class="info-value">{frecuencia}</div>
                            </div>
                        </div>
                        
                        <div class="info-item">
                            <span class="info-icon">🏢</span>
                            <div>
                                <div class="info-label">Proceso</div>
                                <div class="info-value">{proceso}</div>
                            </div>
                        </div>
                        
                        <div class="info-item">
                            <span class="info-icon">🎯</span>
                            <div>
                                <div class="info-label">Línea Estratégica</div>
                                <div class="info-value">{linea}</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Gráfico de tendencia -->
                {'<div class="chart-section"><h4>📈 Evolución Histórica</h4>' + sparkline_svg + '</div>' if sparkline_svg else ''}
                
                <!-- Descripción -->
                {f'<div class="description-section"><h4>📝 Descripción</h4><p>{descripcion}</p></div>' if descripcion else ''}
                
                <!-- Acciones de mejora -->
                {f'''
                <div class="actions-section">
                    <h4>✅ Acciones de Mejora Vinculadas</h4>
                    <ul class="actions-list">
                        {''.join([f'<li><span class="action-icon">▶️</span><span>{accion}</span></li>' for accion in acciones[:5]])}
                    </ul>
                </div>
                ''' if acciones else ''}
                
            </div>
            
            <div class="modal-footer">
                <button class="btn-secondary" onclick="closeModal('{modal_id}')">Cerrar</button>
                <button class="btn-primary" onclick="exportIndicator('{codigo}')">📥 Exportar</button>
            </div>
        </div>
    </div>
    
    <style>
    .modal-overlay {{
        position: fixed;
        z-index: 1000;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        backdrop-filter: blur(4px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
    }}
    
    .modal-content {{
        background: white;
        border-radius: 20px;
        width: 100%;
        max-width: 700px;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 25px 50px rgba(0,0,0,0.25);
        animation: modalSlideIn 0.3s ease;
    }}
    
    @keyframes modalSlideIn {{
        from {{ transform: translateY(-30px); opacity: 0; }}
        to {{ transform: translateY(0); opacity: 1; }}
    }}
    
    .modal-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 1.5rem 2rem;
        border-bottom: 1px solid {COLORS['gray_200']};
        background: {COLORS['gray_50']};
        border-radius: 20px 20px 0 0;
    }}
    
    .modal-title {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {COLORS['text_primary']};
        margin-top: 0.25rem;
    }}
    
    .modal-subtitle {{
        font-size: 0.85rem;
        color: {COLORS['primary']};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .modal-close {{
        background: none;
        border: none;
        font-size: 1.75rem;
        cursor: pointer;
        color: {COLORS['gray_500']};
        padding: 0;
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        transition: all 0.2s;
    }}
    
    .modal-close:hover {{
        background: {COLORS['gray_200']};
        color: {COLORS['text_primary']};
    }}
    
    .modal-body {{
        padding: 2rem;
    }}
    
    .metric-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 2rem;
    }}
    
    .metric-box {{
        background: {COLORS['gray_50']};
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        border-left: 4px solid {color};
    }}
    
    .metric-label {{
        font-size: 0.75rem;
        color: {COLORS['text_secondary']};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }}
    
    .metric-value {{
        font-size: 1.75rem;
        font-weight: 700;
        color: {COLORS['text_primary']};
        margin-bottom: 0.25rem;
    }}
    
    .metric-status {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }}
    
    .metric-unit {{
        font-size: 0.8rem;
        color: {COLORS['text_secondary']};
    }}
    
    .info-section {{
        background: {COLORS['gray_50']};
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
    }}
    
    .info-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
    }}
    
    .info-item {{
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }}
    
    .info-icon {{
        font-size: 1.25rem;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: white;
        border-radius: 8px;
    }}
    
    .info-label {{
        font-size: 0.75rem;
        color: {COLORS['text_secondary']};
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .info-value {{
        font-size: 0.95rem;
        font-weight: 600;
        color: {COLORS['text_primary']};
    }}
    
    .chart-section,
    .description-section,
    .actions-section {{
        margin-bottom: 1.5rem;
    }}
    
    .chart-section h4,
    .description-section h4,
    .actions-section h4 {{
        font-size: 1rem;
        font-weight: 600;
        color: {COLORS['text_primary']};
        margin-bottom: 1rem;
    }}
    
    .description-section p {{
        color: {COLORS['text_secondary']};
        line-height: 1.6;
    }}
    
    .actions-list {{
        list-style: none;
        padding: 0;
        margin: 0;
    }}
    
    .actions-list li {{
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem;
        background: {COLORS['gray_50']};
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }}
    
    .action-icon {{
        font-size: 0.9rem;
    }}
    
    .modal-footer {{
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1.25rem 2rem;
        border-top: 1px solid {COLORS['gray_200']};
        background: {COLORS['gray_50']};
        border-radius: 0 0 20px 20px;
    }}
    
    .btn-primary,
    .btn-secondary {{
        padding: 0.6rem 1.25rem;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        border: none;
    }}
    
    .btn-primary {{
        background: {COLORS['primary']};
        color: white;
    }}
    
    .btn-primary:hover {{
        background: {COLORS['primary_dark']};
    }}
    
    .btn-secondary {{
        background: {COLORS['gray_200']};
        color: {COLORS['text_primary']};
    }}
    
    .btn-secondary:hover {{
        background: {COLORS['gray_300']};
    }}
    
    @media (max-width: 640px) {{
        .metric-grid {{
            grid-template-columns: repeat(2, 1fr);
        }}
        
        .info-grid {{
            grid-template-columns: 1fr;
        }}
    }}
    </style>
    
    <script>
    function openModal(modalId) {{
        document.getElementById(modalId).style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }}
    
    function closeModal(modalId) {{
        document.getElementById(modalId).style.display = 'none';
        document.body.style.overflow = 'auto';
    }}
    
    function exportIndicator(codigo) {{
        // Llamar a Streamlit para exportar
        console.log('Exportando indicador:', codigo);
        // Aquí se puede agregar lógica para exportar
    }}
    
    // Cerrar al hacer click fuera
    window.onclick = function(event) {{
        if (event.target.classList.contains('modal-overlay')) {{
            event.target.style.display = 'none';
            document.body.style.overflow = 'auto';
        }}
    }}
    </script>
    """
    
    components.html(modal_html, height=0)
    
    return modal_id


def show_toast_notification(message, type_="info", duration=3000):
    """
    Muestra una notificación tipo toast no intrusiva.
    
    Args:
        message: str - Mensaje a mostrar
        type_: str - 'success', 'warning', 'danger', 'info'
        duration: int - Duración en milisegundos
    """
    colors = {
        "success": (COLORS["success"], "✅"),
        "warning": (COLORS["warning"], "⚠️"),
        "danger": (COLORS["danger"], "🚨"),
        "info": (COLORS["info"], "ℹ️")
    }
    
    color, icon = colors.get(type_, colors["info"])
    
    toast_html = f"""
    <div id="toast" style="
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: white;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        box-shadow: {SHADOWS['2xl']};
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        border-left: 4px solid {color};
        animation: slideIn 0.3s ease;
        max-width: 400px;
    ">
        <span style="font-size: 1.25rem;">{icon}</span>
        <span style="color: {COLORS['text_primary']}; font-weight: 500;">{message}</span>
        
        <button onclick="this.parentElement.remove()" style="
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1.25rem;
            color: {COLORS['gray_400']};
            padding: 0;
            margin-left: 0.5rem;
        ">&times;</button>
    </div>
    
    <style>
    @keyframes slideIn {{
        from {{ transform: translateX(100%); opacity: 0; }}
        to {{ transform: translateX(0); opacity: 1; }}
    }}
    
    @keyframes slideOut {{
        from {{ transform: translateX(0); opacity: 1; }}
        to {{ transform: translateX(100%); opacity: 0; }}
    }}
    </style>
    
    <script>
    setTimeout(function() {{
        var toast = document.getElementById('toast');
        if (toast) {{
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(function() {{
                toast.remove();
            }}, 300);
        }}
    }}, {duration});
    </script>
    """
    
    components.html(toast_html, height=0)


def render_tooltip(content, tooltip_text, position="top"):
    """
    Renderiza un elemento con tooltip al hacer hover.
    
    Args:
        content: str - Contenido visible
        tooltip_text: str - Texto del tooltip
        position: str - 'top', 'bottom', 'left', 'right'
    """
    positions = {
        "top": ("bottom: 100%; left: 50%; transform: translateX(-50%); margin-bottom: 8px;"),
        "bottom": ("top: 100%; left: 50%; transform: translateX(-50%); margin-top: 8px;"),
        "left": ("right: 100%; top: 50%; transform: translateY(-50%); margin-right: 8px;"),
        "right": ("left: 100%; top: 50%; transform: translateY(-50%); margin-left: 8px;")
    }
    
    position_style = positions.get(position, positions["top"])
    
    tooltip_html = f"""
    <span style="
        position: relative;
        display: inline-block;
        cursor: help;
    ">
        {content}
        
        <span style="
            visibility: hidden;
            background: {COLORS['gray_800']};
            color: white;
            text-align: center;
            padding: 0.5rem 0.75rem;
            border-radius: 8px;
            font-size: 0.85rem;
            white-space: nowrap;
            position: absolute;
            z-index: 100;
            {position_style}
            opacity: 0;
            transition: opacity 0.2s;
        ">
            {tooltip_text}
            
            <span style="
                position: absolute;
                {'top: 100%; left: 50%; transform: translateX(-50%); border: 6px solid transparent; border-top-color: ' + COLORS['gray_800'] + ';' if position == 'top' else ''}
                {'bottom: 100%; left: 50%; transform: translateX(-50%); border: 6px solid transparent; border-bottom-color: ' + COLORS['gray_800'] + ';' if position == 'bottom' else ''}
            "></span>
        </span>
    </span>
    
    <style>
    span:hover > span {{
        visibility: visible !important;
        opacity: 1 !important;
    }}
    </style>
    """
    
    st.markdown(tooltip_html, unsafe_allow_html=True)


# Exportar funciones
__all__ = [
    "render_indicator_detail_modal",
    "show_toast_notification",
    "render_tooltip",
]
