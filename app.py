"""
app.py — Entrada principal del Dashboard de Desempeño Institucional.
"""
import os

import streamlit as st


EMBEDDED_MODE = os.getenv("POWER_APPS_EMBEDDED", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Delegar siempre a la nueva UI (streamlit_app/main.py) — este `app.py` es el
# único entrypoint. La función _new_main() ejecuta st.navigation() que bloquea act.
from streamlit_app.main import main as _new_main

_new_main()
