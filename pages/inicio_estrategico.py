"""
Wrapper page para integrar la nueva interfaz `streamlit_app/pages/inicio_estrategico.py`
en la navegación original (carpeta `pages/`).
"""

try:
    from streamlit_app.pages import inicio_estrategico
except Exception as e:
    inicio_estrategico = None
    _import_error = e

import streamlit as st

if inicio_estrategico is None:
    st.error("No fue posible cargar la nueva página Inicio Estratégico.")
    st.exception(_import_error)
else:
    inicio_estrategico.run()
