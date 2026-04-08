import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np


def plot_trend(df: pd.DataFrame, index_col: str = 'fecha', value_col: str = 'value'):
    df2 = df.reset_index() if index_col in df.index.names else df.copy()
    if index_col in df2.columns:
        x = df2[index_col]
    else:
        x = df2.iloc[:, 0]
    y = df2[value_col] if value_col in df2.columns else df2.iloc[:, 1]
    fig = go.Figure(go.Scatter(x=x, y=y, mode='lines+markers'))
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    return fig


def plot_overview(irip: pd.DataFrame, dad: pd.DataFrame, cmi: pd.DataFrame):
    # ejemplo: barras comparativas agregadas
    df = pd.DataFrame({
        'conjunto': ['IRIP', 'DAD', 'CMI'],
        'valor': [irip['cumplimiento'].mean(), dad['avance'].mean(), cmi['score'].mean()]
    })
    fig = px.bar(df, x='conjunto', y='valor', text='valor', color='conjunto')
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def plot_map(units_df: pd.DataFrame, value_col: str = 'valor'):
    """Scatter geográfico simple usando lat/lon en unidades mock."""
    if 'lat' not in units_df.columns or 'lon' not in units_df.columns:
        # crear posiciones aleatorias si no existen
        rng = np.random.RandomState(1)
        units_df['lat'] = -12 + rng.rand(len(units_df))
        units_df['lon'] = -77 + rng.rand(len(units_df))
    fig = px.scatter_geo(units_df, lat='lat', lon='lon', color=value_col, hover_name='unidad',
                         size=value_col, projection='natural earth')
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
    return fig


def plot_heatmap(df: pd.DataFrame, x: str, y: str, z: str):
    """Crea un heatmap de densidad/valores agregados."""
    pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc='mean')
    fig = px.imshow(pivot, labels=dict(x=x, y=y, color=z), aspect='auto')
    fig.update_layout(margin=dict(l=30, r=10, t=30, b=30))
    return fig
