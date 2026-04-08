"""
Wrapper for Analítica IA
"""
try:
    from streamlit_app.pages import analitica_ia
except Exception as e:
    analitica_ia = None
    _import_error = e

import streamlit as st

if analitica_ia is None:
    st.error("No fue posible cargar Analítica IA.")
    st.exception(_import_error)
else:
    analitica_ia.run()
