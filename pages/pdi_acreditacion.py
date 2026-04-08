"""
Wrapper for PDI / Acreditación
"""
try:
    from streamlit_app.pages import pdi_acreditacion
except Exception as e:
    pdi_acreditacion = None
    _import_error = e

import streamlit as st

if pdi_acreditacion is None:
    st.error("No fue posible cargar PDI / Acreditación.")
    st.exception(_import_error)
else:
    pdi_acreditacion.run()
