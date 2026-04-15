"""
test_imports.py - Diagnóstico de imports para debugging en Streamlit Cloud

Ejecuta este script para verificar que todos los módulos se importan correctamente.
"""
import sys
from pathlib import Path

print("=" * 80)
print("DIAGNÓSTICO DE IMPORTS")
print("=" * 80)

# Agregar paths
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print(f"\nPython version: {sys.version}")
print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"sys.path: {sys.path[:3]}")

# Test 1: Import core.proceso_types
print("\n" + "-" * 80)
print("Test 1: Importar core.proceso_types")
try:
    from core.proceso_types import TIPOS_PROCESO, TIPO_PROCESO_COLORS, get_tipo_color
    print("✅ Import exitoso")
    print(f"   TIPOS_PROCESO: {TIPOS_PROCESO}")
    print(f"   Colores: {list(TIPO_PROCESO_COLORS.keys())}")
    print(f"   get_tipo_color('APOYO'): {get_tipo_color('APOYO')}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Import streamlit_app.pages.resumen_por_proceso
print("\n" + "-" * 80)
print("Test 2: Importar resumen_por_proceso")
try:
    import streamlit_app.pages.resumen_por_proceso as rpp
    print("✅ Import exitoso")
    print(f"   Tiene función render(): {hasattr(rpp, 'render')}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Verificar archivo existe
print("\n" + "-" * 80)
print("Test 3: Verificar archivos existen")
files_to_check = [
    "core/proceso_types.py",
    "streamlit_app/pages/resumen_por_proceso.py",
    "app.py",
]
for file_path in files_to_check:
    full_path = PROJECT_ROOT / file_path
    exists = full_path.exists()
    status = "✅" if exists else "❌"
    print(f"   {status} {file_path}: {exists}")

print("\n" + "=" * 80)
print("FIN DEL DIAGNÓSTICO")
print("=" * 80)
