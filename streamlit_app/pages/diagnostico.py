"""
Página de diagnóstico para Streamlit Cloud
Accede a: https://[tu-app].streamlit.app/diagnostico

Esta página verifica que todos los módulos se importen correctamente.
"""
import streamlit as st
import sys
from pathlib import Path

st.set_page_config(page_title="Diagnóstico", page_icon="🔍", layout="wide")

st.title("🔍 Diagnóstico del Sistema")

# Info del sistema
st.header("1. Información del Sistema")
col1, col2 = st.columns(2)
with col1:
    st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    st.metric("Streamlit Version", st.__version__)
with col2:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    st.metric("PROJECT_ROOT", str(PROJECT_ROOT))

# Test imports
st.header("2. Test de Imports")

import_results = []

# Test 1: core.proceso_types
st.subheader("Test 1: core.proceso_types")
try:
    from core.proceso_types import TIPOS_PROCESO, TIPO_PROCESO_COLORS, get_tipo_color
    st.success("✅ Import exitoso")
    st.code(f"TIPOS_PROCESO = {TIPOS_PROCESO}")
    st.code(f"get_tipo_color('APOYO') = {get_tipo_color('APOYO')}")
    import_results.append(("core.proceso_types", True, None))
except Exception as e:
    st.error(f"❌ Error al importar: {e}")
    import_results.append(("core.proceso_types", False, str(e)))
    with st.expander("Ver traceback completo"):
        import traceback
        st.code(traceback.format_exc())

# Test 2: resumen_por_proceso
st.subheader("Test 2: streamlit_app.pages.resumen_por_proceso")
try:
    import streamlit_app.pages.resumen_por_proceso as rpp
    st.success("✅ Import exitoso")
    st.info(f"Tiene función render(): {hasattr(rpp, 'render')}")
    import_results.append(("resumen_por_proceso", True, None))
except Exception as e:
    st.error(f"❌ Error al importar: {e}")
    import_results.append(("resumen_por_proceso", False, str(e)))
    with st.expander("Ver traceback completo"):
        import traceback
        st.code(traceback.format_exc())

# Test 3: Verificar archivos
st.header("3. Verificación de Archivos")
files_to_check = [
    "core/proceso_types.py",
    "core/__init__.py",
    "streamlit_app/pages/resumen_por_proceso.py",
    "app.py",
]
for file_path in files_to_check:
    full_path = PROJECT_ROOT / file_path
    exists = full_path.exists()
    if exists:
        st.success(f"✅ {file_path}")
    else:
        st.error(f"❌ {file_path} - NO EXISTE")

# Resumen
st.header("4. Resumen")
all_ok = all(result[1] for result in import_results)
if all_ok:
    st.success("🎉 Todos los imports funcionan correctamente")
else:
    st.error("⚠️ Hay problemas con algunos imports")
    failed = [r[0] for r in import_results if not r[1]]
    st.error(f"Módulos con error: {', '.join(failed)}")

# Info adicional
with st.expander("📋 sys.path completo"):
    for i, path in enumerate(sys.path):
        st.text(f"{i}: {path}")

with st.expander("📦 Módulos cargados (filtrados)"):
    relevant_modules = [m for m in sys.modules.keys() if 'core' in m or 'streamlit_app' in m or 'proceso' in m]
    st.json(sorted(relevant_modules))
