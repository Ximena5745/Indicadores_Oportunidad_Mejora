from streamlit_app.pages.resumen_general_real import _load_consolidado_cierres, _filter_consolidado_by_year_month

consolidado = _load_consolidado_cierres()
filtered = _filter_consolidado_by_year_month(consolidado, 2025, 12)

print("Filtered rows:", len(filtered))
print("\nColumn 'cumplimiento_pct':")
print(filtered["cumplimiento_pct"].head(10))
print("\nIs null:", filtered["cumplimiento_pct"].isna().sum())
print("Not null:", filtered["cumplimiento_pct"].notna().sum())

# Check other columns that might have compliance
print("\n--- Similar columns ---")
for c in filtered.columns:
    if "cump" in c.lower() or "ejecut" in c.lower():
        print(f"{c}: {filtered[c].notna().sum()} non-null")