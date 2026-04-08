"""
Wrapper for IRIP Predictivo
"""
try:
    from streamlit_app.pages import irip_predictivo
except Exception as e:
    irip_predictivo = None
    _import_error = e

import streamlit as st

if irip_predictivo is None:
    st.error("No fue posible cargar IRIP Predictivo.")
    st.exception(_import_error)
else:
    irip_predictivo.run()
