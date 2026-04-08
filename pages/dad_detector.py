"""
Wrapper for DAD Detector
"""
try:
    from streamlit_app.pages import dad_detector
except Exception as e:
    dad_detector = None
    _import_error = e

import streamlit as st

if dad_detector is None:
    st.error("No fue posible cargar DAD - Detector de anomalías.")
    st.exception(_import_error)
else:
    dad_detector.run()
