import streamlit as st
from ..utils import data_mocks
from datetime import date, timedelta


def get_filters():
    """Muestra filtros y devuelve las selecciones (periodo, unidades y rango de fechas)."""
    with st.sidebar:
        st.title("Filtros")
        periodo = st.selectbox("Periodo", ["Último mes", "Último trimestre", "Último año"], index=0)
        unidades_disponibles = data_mocks.get_units_geo()['unidad'].tolist()
        unidades = st.multiselect("Unidades", unidades_disponibles, default=unidades_disponibles[:1])

        # Selector avanzado de rango de fechas
        default_end = date.today()
        default_start = default_end - timedelta(days=30)
        start_date, end_date = st.date_input("Rango de fechas", [default_start, default_end])

        st.markdown("---")
        st.write("Navegación")
        modulo = st.radio("Módulos", ["Inicio estratégico", "Gestión OM", "Seguimiento"])
    return {'periodo': periodo, 'unidades': unidades, 'modulo': modulo, 'start_date': start_date, 'end_date': end_date}
