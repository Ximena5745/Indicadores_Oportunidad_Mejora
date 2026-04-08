import streamlit as st


def kpi_card(title: str, value: str, delta: str = None, color: str = "#0b5cff"):
    """Presenta un KPI card simple. Usa HTML/CSS inyectado para flexibilidad."""
    card_html = f"""
    <div style='border-radius:8px;padding:12px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,0.08);'>
      <div style='font-size:12px;color:#666'>{title}</div>
      <div style='font-size:22px;font-weight:700;color:{color};'>{value}</div>
      <div style='font-size:12px;color:#999'>{delta or ''}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
