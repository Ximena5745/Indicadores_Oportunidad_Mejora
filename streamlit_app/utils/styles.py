import streamlit as st


CSS = '''
body { background-color: #f6f8fb; }
.stApp { font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto; }
.kpi-row { display:flex; gap:12px; }
'''


def load_css():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
