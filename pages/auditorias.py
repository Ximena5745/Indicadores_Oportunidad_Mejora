"""
Wrapper for Auditorías
"""
try:
    from streamlit_app.pages import auditorias
except Exception as e:
    auditorias = None
    _import_error = e

import streamlit as st

if auditorias is None:
    st.error("No fue posible cargar Auditorías.")
    st.exception(_import_error)
else:
    auditorias.run()
