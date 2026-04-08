"""Wrapper for Coherencia de metas (ICM)"""
try:
    from streamlit_app.pages import coherencia_metas
except Exception as e:
    coherencia_metas = None
    _import_error = e

import streamlit as st

if coherencia_metas is None:
    st.error("No fue posible cargar Coherencia de metas.")
    st.exception(_import_error)
else:
    coherencia_metas.run()