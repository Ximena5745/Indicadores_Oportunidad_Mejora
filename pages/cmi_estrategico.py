"""
Wrapper for CMI Estratégico
"""
try:
    from streamlit_app.pages import cmi_estrategico
except Exception as e:
    cmi_estrategico = None
    _import_error = e

import streamlit as st

if cmi_estrategico is None:
    st.error("No fue posible cargar CMI Estratégico.")
    st.exception(_import_error)
else:
    cmi_estrategico.run()
