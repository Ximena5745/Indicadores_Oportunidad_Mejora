"""
Wrapper for Resumen por proceso
"""
try:
    from streamlit_app.pages import resumen_por_proceso
except Exception as e:
    resumen_por_proceso = None
    _import_error = e

import streamlit as st

if resumen_por_proceso is None:
    st.error("No fue posible cargar Resumen por proceso.")
    st.exception(_import_error)
else:
    resumen_por_proceso.run()
