"""
Entrypoint Streamlit para el scaffold del módulo "Inicio estratégico".
"""
import streamlit as st
from pages import inicio_estrategico


def main():
    st.set_page_config(page_title="Inicio Estratégico", layout="wide")
    inicio_estrategico.run()


if __name__ == "__main__":
    main()
