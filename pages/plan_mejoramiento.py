"""Wrapper for Plan de Mejoramiento"""
try:
    from streamlit_app.pages import plan_mejoramiento
except Exception as e:
    plan_mejoramiento = None
    _import_error = e

import streamlit as st

if plan_mejoramiento is None:
    st.error("No fue posible cargar Plan de Mejoramiento.")
    st.exception(_import_error)
else:
    plan_mejoramiento.run()