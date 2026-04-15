"""
Heatmap and Advanced Charts Component
Visualizaciones interactivas: heatmaps, sunburst, radar, timelines
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from streamlit_app.styles.design_system import COLORS, SHADOWS, get_palette_for_chart


def render_performance_heatmap(
    df, 
    x_col='Periodo', 
    y_col='Linea', 
    value_col='cumplimiento_pct',
    title="Matriz de Cumplimiento",
    height=500,
    show_values=True
    , linea=None, kind="default"
):
    """
    Renderiza un heatmap de cumplimiento con drill-down capability.
    
    Args:
        df: DataFrame - Datos a visualizar
        x_col: str - Columna para eje X (períodos)
        y_col: str - Columna para eje Y (líneas/objetivos)
        value_col: str - Columna con valores de cumplimiento
        title: str - Título del gráfico
        height: int - Altura del gráfico
        show_values: bool - Mostrar valores en celdas
    
    Returns:
        plotly.Figure
    """
    # Crear matriz pivot
    pivot_df = df.pivot_table(
        values=value_col,
        index=y_col,
        columns=x_col,
        aggfunc='mean'
    ).fillna(0)
    
    # Seleccionar paleta según línea/uso
    palette = get_palette_for_chart(kind=kind, linea=linea)

    # Construir colorscale continuo a partir de la paleta retornada
    if palette and isinstance(palette, (list, tuple)) and len(palette) > 0:
        n = len(palette)
        colorscale = [[i / (n - 1) if n > 1 else 1.0, palette[i]] for i in range(n)]
    else:
        colorscale = [
            [0.0, COLORS["danger"]],
            [0.3, COLORS["danger_light"]],
            [0.5, COLORS["warning"]],
            [0.7, "#AED581"],  # Verde claro
            [0.85, COLORS["success"]],
            [1.0, COLORS["primary"]]
        ]
    
    fig = px.imshow(
        pivot_df,
        labels=dict(x="Período", y=y_col, color="Cumplimiento %"),
        x=pivot_df.columns,
        y=pivot_df.index,
        color_continuous_scale=colorscale,
        aspect="auto",
        text_auto='.0f' if show_values else False,
        title=title
    )
    
    # Personalizar hover
    fig.update_traces(
        hovertemplate=(
            f'<b>{y_col}: %{{y}}</b><br>'
            f'Período: %{{x}}<br>'
            f'Cumplimiento: %{{z:.1f}}%<br>'
            f'<extra></extra>'
        ),
        hoverongaps=False
    )
    
    # Layout
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': COLORS['text_primary'], 'family': 'Inter, sans-serif'}
        },
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        xaxis_tickangle=-45,
        xaxis=dict(
            tickfont={'size': 11, 'color': COLORS['text_secondary']},
            title_font={'size': 13, 'color': COLORS['text_primary']}
        ),
        yaxis=dict(
            tickfont={'size': 11, 'color': COLORS['text_secondary']},
            title_font={'size': 13, 'color': COLORS['text_primary']}
        ),
        coloraxis_colorbar=dict(
            title="Cumplimiento %",
            titleside="right",
            tickfont={'size': 11},
            title_font={'size': 12}
        ),
        margin=dict(l=80, r=80, t=80, b=80)
    )
    
    return fig


def render_sunburst_hierarchy(
    df, 
    path=['Linea', 'Objetivo', 'Indicador'], 
    value='cumplimiento_pct',
    title="Jerarquía de Indicadores",
    height=600
):
    """
    Renderiza un sunburst chart para navegación jerárquica.
    
    Args:
        df: DataFrame - Datos a visualizar
        path: list - Jerarquía de columnas
        value: str - Columna con valores
        title: str - Título del gráfico
        height: int - Altura del gráfico
    
    Returns:
        plotly.Figure
    """
    # Preparar datos
    df_clean = df.dropna(subset=path + [value])
    
    fig = px.sunburst(
        df_clean,
        path=path,
        values=value,
        color=value,
        color_continuous_scale=[
            COLORS["danger"], 
            COLORS["warning"], 
            COLORS["success"],
            COLORS["primary"]
        ],
        color_continuous_midpoint=80,
        title=title
    )
    
    # Personalizar hover
    fig.update_traces(
        hovertemplate=(
            '<b>%{label}</b><br>'
            'Cumplimiento: %{value:.1f}%'
            '<extra></extra>'
        ),
        insidetextorientation='radial'
    )
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': COLORS['text_primary']}
        },
        paper_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        coloraxis_colorbar=dict(
            title="Cumplimiento %",
            titleside="right"
        )
    )
    
    return fig


def render_radar_comparison(
    df,
    categories_col='dimension',
    values_col='cumplimiento',
    group_col='grupo',
    title="Comparativa Multidimensional",
    height=500
):
    """
    Renderiza un radar chart para comparar múltiples dimensiones.
    
    Args:
        df: DataFrame - Datos a visualizar
        categories_col: str - Columna con categorías
        values_col: str - Columna con valores
        group_col: str - Columna para agrupar (líneas en radar)
        title: str - Título del gráfico
        height: int - Altura del gráfico
    
    Returns:
        plotly.Figure
    """
    fig = go.Figure()
    
    colors = [COLORS["primary"], COLORS["warning"], COLORS["success"], COLORS["danger"], COLORS["info"]]
    
    groups = df[group_col].unique()
    
    for i, group in enumerate(groups):
        group_data = df[df[group_col] == group]
        
        fig.add_trace(go.Scatterpolar(
            r=group_data[values_col].tolist() + [group_data[values_col].iloc[0]],
            theta=group_data[categories_col].tolist() + [group_data[categories_col].iloc[0]],
            fill='toself',
            name=str(group),
            line_color=colors[i % len(colors)],
            fillcolor=colors[i % len(colors)].replace(')', ', 0.2)').replace('rgb', 'rgba') if colors[i % len(colors)].startswith('rgb') else colors[i % len(colors)] + "33"
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont={'size': 10},
                tickcolor=COLORS['gray_300'],
                gridcolor=COLORS['gray_200']
            ),
            angularaxis=dict(
                tickfont={'size': 11, 'color': COLORS['text_primary']},
                gridcolor=COLORS['gray_200']
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font={'size': 11}
        ),
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': COLORS['text_primary']}
        },
        paper_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=80, r=80, t=80, b=80)
    )
    
    return fig


def render_timeline_with_events(
    df,
    x_col='fecha',
    y_col='cumplimiento',
    color_col='categoria',
    events=None,
    title="Evolución Temporal",
    height=400
):
    """
    Renderiza una línea de tiempo con eventos anotados.
    
    Args:
        df: DataFrame - Datos a visualizar
        x_col: str - Columna de fechas
        y_col: str - Columna de valores
        color_col: str - Columna para colorear líneas
        events: list - Lista de eventos (dict con 'fecha', 'titulo', 'descripcion')
        title: str - Título del gráfico
        height: int - Altura del gráfico
    
    Returns:
        plotly.Figure
    """
    fig = px.line(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        markers=True,
        line_shape='spline',
        title=title
    )
    
    # Personalizar líneas
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8, line=dict(width=2, color='white')),
        hovertemplate=(
            '<b>%{fullData.name}</b><br>'
            'Fecha: %{x}<br>'
            'Valor: %{y:.1f}%'
            '<extra></extra>'
        )
    )
    
    # Agregar eventos como anotaciones
    if events:
        colors_events = [COLORS["warning"], COLORS["info"], COLORS["success"]]
        
        for i, event in enumerate(events):
            fig.add_annotation(
                x=event['fecha'],
                y=event.get('y', 85),
                text=f"📋 {event['titulo']}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=colors_events[i % len(colors_events)],
                font=dict(
                    size=11,
                    color=COLORS['text_primary']
                ),
                bgcolor="rgba(255,255,255,0.95)",
                bordercolor=colors_events[i % len(colors_events)],
                borderwidth=1,
                borderpad=4,
                hovertext=event.get('descripcion', ''),
                hoverlabel=dict(bgcolor=COLORS['gray_800'], font_color='white')
            )
    
    # Layout
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': COLORS['text_primary']}
        },
        xaxis_title="Fecha",
        yaxis_title="Cumplimiento (%)",
        hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        xaxis=dict(
            tickfont={'size': 11, 'color': COLORS['text_secondary']},
            gridcolor=COLORS['gray_200'],
            showgrid=True
        ),
        yaxis=dict(
            tickfont={'size': 11, 'color': COLORS['text_secondary']},
            gridcolor=COLORS['gray_200'],
            showgrid=True,
            range=[0, 110]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            font={'size': 11}
        ),
        margin=dict(l=60, r=40, t=80, b=100)
    )
    
    return fig


def render_treemap_drilldown(
    df,
    path=['Macrolinea', 'Objetivo', 'Indicador'],
    value='cumplimiento_pct',
    color='cumplimiento_pct',
    title="Árbol de Objetivos",
    height=500
):
    """
    Renderiza un treemap con capacidad de drill-down.
    
    Args:
        df: DataFrame - Datos a visualizar
        path: list - Jerarquía de columnas
        value: str - Columna con valores
        color: str - Columna para colorear
        title: str - Título del gráfico
        height: int - Altura del gráfico
    
    Returns:
        plotly.Figure
    """
    fig = px.treemap(
        df,
        path=path,
        values=value,
        color=color,
        color_continuous_scale=[
            COLORS["danger"],
            COLORS["warning"],
            COLORS["success"],
            COLORS["primary"]
        ],
        range_color=[0, 130],
        title=title
    )
    
    # Personalizar
    fig.update_traces(
        textinfo='label+value',
        texttemplate='%{label}<br>%{value:.0f}%',
        hovertemplate=(
            '<b>%{label}</b><br>'
            'Cumplimiento: %{value:.1f}%'
            '<extra></extra>'
        ),
        textfont=dict(size=12, color='white'),
        insidetextfont=dict(size=11)
    )
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': COLORS['text_primary']}
        },
        paper_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        coloraxis_colorbar=dict(
            title="Cumplimiento %",
            titleside="right"
        )
    )
    
    return fig


def render_gauge_chart(
    value,
    title="Indicador",
    min_val=0,
    max_val=100,
    threshold=80,
    height=300
):
    """
    Renderiza un gauge semicircular.
    
    Args:
        value: float - Valor actual
        title: str - Título
        min_val: float - Valor mínimo
        max_val: float - Valor máximo
        threshold: float - Umbral para color
        height: int - Altura del gráfico
    
    Returns:
        plotly.Figure
    """
    # Determinar color según valor
    if value >= 100:
        color = COLORS["primary"]
    elif value >= threshold:
        color = COLORS["success"]
    elif value >= 60:
        color = COLORS["warning"]
    else:
        color = COLORS["danger"]
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        number={
            'suffix': "%",
            'font': {'size': 40, 'color': COLORS['text_primary'], 'family': 'Inter, sans-serif'},
            'valueformat': '.1f'
        },
        delta={
            'reference': threshold,
            'valueformat': '.1f',
            'increasing': {'color': COLORS["success"]},
            'decreasing': {'color': COLORS["danger"]},
            'font': {'size': 18}
        },
        title={
            'text': title,
            'font': {'size': 16, 'color': COLORS['text_secondary']}
        },
        gauge={
            'axis': {
                'range': [min_val, max_val],
                'tickwidth': 1,
                'tickcolor': COLORS['gray_400'],
                'tickfont': {'size': 10}
            },
            'bar': {
                'color': color,
                'thickness': 0.75
            },
            'bgcolor': COLORS['gray_100'],
            'borderwidth': 2,
            'bordercolor': COLORS['gray_300'],
            'steps': [
                {'range': [min_val, 60], 'color': COLORS['danger'] + '33'},  # 20% opacity
                {'range': [60, threshold], 'color': COLORS['warning'] + '33'},
                {'range': [threshold, max_val], 'color': COLORS['success'] + '33'}
            ],
            'threshold': {
                'line': {'color': COLORS['text_primary'], 'width': 3},
                'thickness': 0.8,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=30, r=30, t=50, b=30)
    )
    
    return fig


def render_bullet_chart(
    actual,
    target,
    ranges=[60, 80, 100],
    title="Cumplimiento",
    height=150
):
    """
    Renderiza un bullet chart para comparar actual vs meta.
    
    Args:
        actual: float - Valor actual
        target: float - Valor objetivo
        ranges: list - Rangos de referencia [malo, medio, bueno]
        title: str - Título
        height: int - Altura del gráfico
    
    Returns:
        plotly.Figure
    """
    fig = go.Figure()
    
    # Rangos de fondo
    colors_ranges = [COLORS['danger'] + '44', COLORS['warning'] + '44', COLORS['success'] + '44']
    
    for i, (range_val, color) in enumerate(zip(ranges, colors_ranges)):
        prev_val = ranges[i-1] if i > 0 else 0
        fig.add_trace(go.Bar(
            x=[range_val - prev_val],
            y=[title],
            orientation='h',
            marker_color=color,
            showlegend=False,
            hoverinfo='skip',
            width=0.5
        ))
    
    # Barra de valor actual
    fig.add_trace(go.Bar(
        x=[actual],
        y=[title],
        orientation='h',
        marker_color=COLORS['primary'],
        showlegend=False,
        width=0.3,
        name='Actual'
    ))
    
    # Línea de meta
    fig.add_trace(go.Scatter(
        x=[target],
        y=[title],
        mode='markers',
        marker=dict(
            symbol='line-ns',
            size=30,
            color=COLORS['text_primary'],
            line=dict(width=3)
        ),
        showlegend=False,
        name='Meta'
    ))
    
    fig.update_layout(
        barmode='overlay',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=100, r=30, t=20, b=20),
        xaxis=dict(
            range=[0, max(ranges) * 1.1],
            tickfont={'size': 10},
            showgrid=False
        ),
        yaxis=dict(
            tickfont={'size': 12, 'color': COLORS['text_primary']},
            showgrid=False
        ),
        annotations=[
            dict(
                x=actual,
                y=title,
                text=f'{actual:.1f}%',
                showarrow=False,
                xanchor='left',
                yanchor='middle',
                xshift=10,
                font=dict(size=11, color=COLORS['primary'], weight=600)
            )
        ]
    )
    
    return fig


# Exportar funciones
__all__ = [
    "render_performance_heatmap",
    "render_sunburst_hierarchy",
    "render_radar_comparison",
    "render_timeline_with_events",
    "render_treemap_drilldown",
    "render_gauge_chart",
    "render_bullet_chart",
]
