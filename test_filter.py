import sys
sys.path.insert(0, '.')
from streamlit_app.services.data_service import DataService
from streamlit_app.pages.resumen_general_real import _filter_consolidado_by_year_month

ds = DataService()
df = ds.get_tracking_data()

print("Testing filter for Dic 2025 (month=12)")
result = _filter_consolidado_by_year_month(df, 2025, 12)
print(f"Result: {len(result)} rows")

print("\n=== DEBUG OUTPUT ===")
try:
    with open("debug_filter.log", "r") as f:
        print(f.read())
except:
    print("No debug file")