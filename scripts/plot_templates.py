"""Plantillas Plotly minimal para prototipos de Fase 3.
Incluye paleta y estilos consistentes para el dashboard."""
from typing import List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Paleta institucional/sencilla
DEFAULT_PALETTE = ["#28a745", "#ffc107", "#dc3545", "#17a2b8", "#6c757d"]
DEFAULT_TEMPLATE = "plotly_white"


def scorecard_kpis(df: pd.DataFrame, kpis: List[str]) -> go.Figure:
    # Devuelve un gráfico tipo 'cards' horizontal con valores de KPIs simples
    values = []
    for k in kpis:
        if k in df.columns:
            try:
                values.append(df[k].dropna().astype(float).mean())
            except Exception:
                values.append(None)
        else:
            values.append(None)

    fig = go.Figure()
    for i, (k, v) in enumerate(zip(kpis, values)):
        fig.add_trace(go.Indicator(mode="number+delta", value=v or 0, title={'text': k}, domain={'x': [i/len(kpis), (i+1)/len(kpis)], 'y': [0,1]}))
    fig.update_layout(height=120, template=DEFAULT_TEMPLATE)
    return fig


def treemap_hierarchical(df: pd.DataFrame, path: List[str], values_col: str = None) -> go.Figure:
    # path: lista de columnas que definen la jerarquía (ej. ['Linea','Subproceso','Indicador'])
    fig = px.treemap(df, path=path, values=values_col, color_discrete_sequence=DEFAULT_PALETTE)
    fig.update_layout(margin=dict(t=25, l=0, r=0, b=0), template=DEFAULT_TEMPLATE)
    return fig


def sparkline_series(series: pd.Series) -> go.Figure:
    fig = go.Figure(go.Scatter(y=series.values, mode='lines', line=dict(width=1)))
    fig.update_layout(height=50, margin=dict(t=0,b=0,l=0,r=0), template=DEFAULT_TEMPLATE)
    return fig


def kanban_counts(df: pd.DataFrame, status_col: str = 'Status') -> go.Figure:
    counts = df[status_col].value_counts().reindex(['Actualizado','Pendiente','Alerta']).fillna(0)
    fig = px.bar(x=counts.index, y=counts.values, labels={'x':'Estado','y':'Conteo'}, text=counts.values, color_discrete_sequence=DEFAULT_PALETTE)
    fig.update_layout(height=240, template=DEFAULT_TEMPLATE)
    return fig


def heatmap_matrix(df: pd.DataFrame, index: str, columns: str, values: str) -> go.Figure:
    pivot = df.pivot_table(index=index, columns=columns, values=values, aggfunc='mean')
    fig = go.Figure(data=go.Heatmap(z=pivot.values, x=list(pivot.columns), y=list(pivot.index), colorscale='RdYlGn'))
    fig.update_layout(height=400, xaxis_nticks=20, template=DEFAULT_TEMPLATE)
    return fig


def stacked_bars(df: pd.DataFrame, x: str, y: str, color: str) -> go.Figure:
    fig = px.bar(df, x=x, y=y, color=color, color_discrete_sequence=DEFAULT_PALETTE)
    fig.update_layout(barmode='stack', height=400, template=DEFAULT_TEMPLATE)
    return fig


def bubble_chart(df: pd.DataFrame, x: str, y: str, size: str, color: str = None) -> go.Figure:
    fig = px.scatter(df, x=x, y=y, size=size, color=color, hover_name=df.columns[0], color_discrete_sequence=DEFAULT_PALETTE)
    fig.update_layout(height=400, template=DEFAULT_TEMPLATE)
    return fig


def sankey_chart(df: pd.DataFrame, source_col: str, target_col: str, value_col: str) -> go.Figure:
    # build categorical mapping
    sources = list(df[source_col].astype(str))
    targets = list(df[target_col].astype(str))
    labels = list(pd.unique(sources + targets))
    source_idx = [labels.index(s) for s in sources]
    target_idx = [labels.index(t) for t in targets]
    values = list(df[value_col].astype(float).fillna(1))
    link = dict(source=source_idx, target=target_idx, value=values)
    fig = go.Figure(data=[go.Sankey(node=dict(label=labels, pad=15), link=link)])
    fig.update_layout(height=400, template=DEFAULT_TEMPLATE)
    return fig


def waterfall_chart(df: pd.DataFrame, x: str, y: str, color_map: dict | None = None, title: str = '') -> go.Figure:
    # Normalize x and y and validate lengths
    x_vals = df[x].astype(str).tolist() if x in df.columns else []
    # Ensure y is numeric; coerce and drop rows with missing x or y
    y_series = pd.to_numeric(df.get(y, pd.Series(dtype=float)), errors='coerce')
    # Align lengths: build pairs where y is not NaN and x is present
    pairs = [(str(a), float(b)) for a, b in zip(x_vals, y_series.tolist()) if a is not None and str(a).strip() != '' and (b is not None and not pd.isna(b))]
    if not pairs:
        # No valid data; return empty figure with message
        fig = go.Figure()
        fig.update_layout(title=title or 'Waterfall (sin datos)', template=DEFAULT_TEMPLATE)
        return fig

    x_clean, y_clean = zip(*pairs)

    # Build colors list mapping each x value to a color in color_map (fallback palette)
    if color_map:
        colors = [color_map.get(v, DEFAULT_PALETTE[0]) for v in x_clean]
    else:
        colors = [DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)] for i in range(len(x_clean))]

    try:
        fig = go.Figure(go.Waterfall(x=list(x_clean), y=list(y_clean), marker=dict(color=colors, line=dict(color="#ffffff", width=1))))
        fig.update_layout(title=title, height=420, template=DEFAULT_TEMPLATE)
        fig.update_traces(hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>")
        # mark as waterfall
        fig.layout.meta = {"waterfall_used": True}
        return fig
    except Exception:
        # Fallback: bar chart if Waterfall fails, but include diagnostic info
        import traceback
        err = traceback.format_exc()
        fig = go.Figure(go.Bar(x=list(x_clean), y=list(y_clean), marker_color=colors))
        msg = f"Waterfall rendering failed; fallback to Bar. Error: {str(err).splitlines()[-1]}"
        fig.update_layout(title=(title or 'Waterfall fallback: Bar'), height=420, template=DEFAULT_TEMPLATE)
        # add a visible annotation with brief message and store full traceback in meta
        try:
            fig.add_annotation(text=msg, xref='paper', yref='paper', x=0.5, y=1.05, showarrow=False, font=dict(size=11, color='darkred'))
        except Exception:
            pass
        fig.layout.meta = {"waterfall_used": False, "fallback_error": err}
        return fig


def radar_chart(df: pd.DataFrame, categories: List[str], values: List[float], title: str = '') -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name=title))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=False, height=400, template=DEFAULT_TEMPLATE)
    return fig


def funnel_chart(df: pd.DataFrame, x: str, y: str) -> go.Figure:
    fig = px.funnel(df, x=x, y=y, color_discrete_sequence=DEFAULT_PALETTE)
    fig.update_layout(height=400, template=DEFAULT_TEMPLATE)
    return fig
