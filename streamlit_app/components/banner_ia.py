import streamlit as st


def banner_ia(message: str):
    """Pequeño banner de recomendaciones generadas por IA."""
    html = f"""
    <div style='background:linear-gradient(90deg,#f0f7ff,#e8f3ff);padding:10px;border-radius:8px;'>
      <strong>IA:</strong> {message}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
