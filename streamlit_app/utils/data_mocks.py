"""
Mocks reproducibles para IRIP, DAD y CMI.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _date_range(days=30):
    today = datetime.today()
    return [today - timedelta(days=i) for i in range(days)][::-1]


def get_irip_data(days=30):
    np.random.seed(42)
    fechas = _date_range(days)
    cumplimiento = np.clip(70 + np.random.randn(days).cumsum() * 0.1, 50, 100)
    unidad = np.random.choice(['Unidad A', 'Unidad B', 'Unidad C'], size=days)
    df = pd.DataFrame({'fecha': fechas, 'cumplimiento': cumplimiento, 'unidad': unidad})
    return df


def get_dad_data(days=30):
    np.random.seed(7)
    fechas = _date_range(days)
    avance = np.clip(60 + np.random.randn(days).cumsum() * 0.12, 30, 100)
    unidad = np.random.choice(['Unidad A', 'Unidad B', 'Unidad C'], size=days)
    df = pd.DataFrame({'fecha': fechas, 'avance': avance, 'unidad': unidad})
    return df


def get_cmi_data(days=30):
    np.random.seed(21)
    fechas = _date_range(days)
    score = np.clip(3 + np.random.randn(days).cumsum() * 0.02, 1, 5)
    unidad = np.random.choice(['Unidad A', 'Unidad B', 'Unidad C'], size=days)
    df = pd.DataFrame({'fecha': fechas, 'score': score, 'unidad': unidad})
    return df


def get_riesgos_table(irip, dad, cmi):
    # Devuelve una tabla mock con indicadores que caen
    datos = [
        {'indicador': 'IRIP_001', 'valor': irip['cumplimiento'].iloc[-1], 'tendencia': 'baja'},
        {'indicador': 'DAD_023', 'valor': dad['avance'].iloc[-1], 'tendencia': 'baja'},
        {'indicador': 'CMI_98', 'valor': cmi['score'].iloc[-1], 'tendencia': 'estable'},
    ]
    return pd.DataFrame(datos)


def get_indicator_detail(indicador_id: str = None, days: int = 30):
    """Genera un detalle mock por indicador. Devuelve DataFrame con columnas 'fecha' y 'valor'."""
    np.random.seed(123 if indicador_id is None else abs(hash(indicador_id)) % 2**32)
    fechas = _date_range(days)
    valores = np.clip(50 + np.random.randn(days).cumsum() * 0.2, 10, 100)
    df = pd.DataFrame({'fecha': fechas, 'valor': valores})
    nombre = indicador_id or 'Indicador X - Ejemplo'
    return {
        'nombre': nombre,
        'descripcion': f'Detalle sintético para {nombre}.',
        'valores': df
    }


def get_units_geo():
    # Mocks de unidades con lat/lon y un valor agregado
    unidades = ['Unidad A', 'Unidad B', 'Unidad C']
    lat = [-12.04, -12.10, -12.00]
    lon = [-77.03, -77.05, -76.95]
    valor = [75, 62, 88]
    df = pd.DataFrame({'unidad': unidades, 'lat': lat, 'lon': lon, 'valor': valor})
    return df
