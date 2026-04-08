"""
app.py — Entrada principal del Dashboard de Desempeño Institucional.
"""
import os

import streamlit as st
import subprocess


def _get_git_commit_short():
    try:
        p = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        return p.stdout.strip()
    except Exception:
        return os.getenv("GIT_COMMIT", "unknown")


EMBEDDED_MODE = os.getenv("POWER_APPS_EMBEDDED", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Delegar siempre a la nueva UI (streamlit_app/main.py) — este `app.py` es el
# único entrypoint. La función _new_main() ejecuta st.navigation() que bloquea act.
from streamlit_app.main import main as _new_main

# El entrypoint delega a la nueva UI sin elementos de diagnóstico en el sidebar.
_new_main()
