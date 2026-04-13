import json
import streamlit as st
from pathlib import Path
from streamlit.components.v1 import html

from streamlit_app.components import ui_components

st.set_page_config(page_title="Dashboard Cumplimiento", layout="wide")

# Render filtros y construir payload dinámico
filters = ui_components.render_filters()
payload = ui_components.build_dashboard_payload(filters)

BASE = Path(__file__).parent
tpl_dir = BASE / "components" / "ui" / "templates"

# Render modular: KPIs, Charts y Tabla como componentes separados
kp_tpl = (tpl_dir / "kpis.html").read_text(encoding='utf-8')
charts_tpl = (tpl_dir / "charts.html").read_text(encoding='utf-8')
table_tpl = (tpl_dir / "table.html").read_text(encoding='utf-8')
insights_tpl = (tpl_dir / "insights.html").read_text(encoding='utf-8')

# Inyectar payload en cada plantilla
kp_html = kp_tpl.replace('__DATA__', json.dumps(payload, ensure_ascii=False)).replace('{{ kpis }}', '')
charts_html = charts_tpl.replace('__DATA__', json.dumps(payload, ensure_ascii=False))
table_html = table_tpl.replace('__DATA__', json.dumps(payload, ensure_ascii=False))
insights_html = insights_tpl.replace('__DATA__', json.dumps(payload, ensure_ascii=False))

st.markdown("<div style='display:flex;gap:16px'>", unsafe_allow_html=True)
html(kp_html, height=180, scrolling=False)
html(insights_html, height=140, scrolling=False)
html(charts_html, height=360, scrolling=True)
st.markdown("</div>", unsafe_allow_html=True)

html(table_html, height=320, scrolling=True)
