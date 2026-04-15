import json
import streamlit as st
from pathlib import Path
from streamlit.components.v1 import html
from typing import Any

# Limpiar caché corrupto al inicio
if "cache_cleared" not in st.session_state:
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state.cache_cleared = True

from components import ui_components

st.set_page_config(page_title="Dashboard Cumplimiento", layout="wide")

# ─── Inyectar estilos CSS personalizados ───────────────────────────────────────
def _load_css(file_path):
    """Carga un archivo CSS y lo retorna como una cadena."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def _inject_styles():
    """Inyecta estilos locales con ruta robusta para local y cloud."""
    base = Path(__file__).resolve().parent / "styles"
    css_files = ["styles.css", "main.css"]
    for css_name in css_files:
        css_path = base / css_name
        if not css_path.exists():
            css_path = Path(f"streamlit_app/styles/{css_name}")
        if css_path.exists():
            styles = _load_css(str(css_path))
            st.markdown(f"<style>{styles}</style>", unsafe_allow_html=True)

_inject_styles()

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


def _json_default(o: Any):
	"""Serializador por defecto para json.dumps que convierte tipos de numpy/pandas."""
	try:
		import numpy as _np
		import pandas as _pd
	except Exception:
		_np = None
		_pd = None

	# pandas NA / numpy nan
	try:
		if _pd is not None and _pd.isna(o):
			return None
	except Exception:
		pass

	if _np is not None:
		if isinstance(o, _np.integer):
			return int(o)
		if isinstance(o, _np.floating):
			return float(o)
		if isinstance(o, _np.ndarray):
			return o.tolist()

	if _pd is not None:
		if isinstance(o, _pd.Series):
			return o.tolist()
		if isinstance(o, _pd.Timestamp):
			return o.isoformat()
		if isinstance(o, _pd.Timedelta):
			return str(o)

	# Fallback: intentar extraer valor con .item() si existe
	if hasattr(o, 'item'):
		try:
			return o.item()
		except Exception:
			pass

	# Finalmente, representar como string
	try:
		return str(o)
	except Exception:
		return None


# Inyectar payload en cada plantilla (usando serializador seguro)
payload_json = json.dumps(payload, ensure_ascii=False, default=_json_default)
kp_html = kp_tpl.replace('__DATA__', payload_json).replace('{{ kpis }}', '')
charts_html = charts_tpl.replace('__DATA__', payload_json)
table_html = table_tpl.replace('__DATA__', payload_json)
insights_html = insights_tpl.replace('__DATA__', payload_json)

st.markdown("<div style='display:flex;gap:16px'>", unsafe_allow_html=True)
html(kp_html, height=180, scrolling=False)
html(insights_html, height=140, scrolling=False)
html(charts_html, height=360, scrolling=True)
st.markdown("</div>", unsafe_allow_html=True)

html(table_html, height=320, scrolling=True)
