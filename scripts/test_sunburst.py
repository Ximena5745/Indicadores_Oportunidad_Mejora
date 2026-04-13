"""Prueba rápida para validar que `_build_sunburst` construye un Sunburst.
Carga el Excel de debug y verifica que la figura resultante contiene trazas de tipo 'sunburst'.
Exit code 0 = OK, 2 = falla.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
import pandas as pd
import types, sys
# Provide a minimal stub for streamlit so the module can be imported in tests without installing streamlit
sys.modules.setdefault('streamlit', types.ModuleType('streamlit'))
# minimal st API used at import-time
_st = sys.modules['streamlit']
def _dummy_cache_data(**kwargs):
    def _dec(f):
        return f
    return _dec
_st.cache_data = _dummy_cache_data
_st.cache_resource = _dummy_cache_data

from streamlit_app.pages.resumen_general_real import _build_sunburst

pdi_xlsx = 'artifacts/debug_cascada/pdi.xlsx'
if not os.path.exists(pdi_xlsx):
    print('ERROR: archivo de prueba no encontrado:', pdi_xlsx)
    sys.exit(2)

try:
    df = pd.read_excel(pdi_xlsx)
except Exception as e:
    print('ERROR: no se pudo leer el Excel:', e)
    sys.exit(2)

try:
    fig = _build_sunburst(df)
except Exception as e:
    print('ERROR: _build_sunburst lanzó excepción:', e)
    sys.exit(2)

# check for sunburst traces
has_sb = any(getattr(t, 'type', None) == 'sunburst' for t in fig.data)
if has_sb:
    print('OK: Sunburst presente en figura.')
    sys.exit(0)
else:
    print('ERROR: No se encontró traza sunburst en figura. fig.meta=', getattr(fig.layout, 'meta', None))
    sys.exit(2)
