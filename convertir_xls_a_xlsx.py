"""
convertir_xls_a_xlsx.py
=======================
Convierte los archivos .xls de datos a .xlsx para evitar depender de xlrd
en la aplicación Streamlit.

Ejecutar UNA VEZ desde la raíz del proyecto:
    python convertir_xls_a_xlsx.py

Archivos que convierte:
  · data/raw/OM.xls        → data/raw/OM.xlsx
      (salta las 7 primeras filas de metadatos; encabezados en fila 8)
  · data/raw/Plan de accion/*.xls → misma carpeta, extensión .xlsx
"""
import sys
from pathlib import Path

import pandas as pd

DATA_RAW    = Path(__file__).parent / "data" / "raw"
PLAN_FOLDER = DATA_RAW / "Plan de accion"


def convertir(ruta_xls: Path, destino_xlsx: Path, header: int = 0) -> bool:
    """Intenta leer con openpyxl primero (xlsx disfrazado de xls), luego xlrd."""
    df = None
    for engine in ("openpyxl", "xlrd"):
        try:
            df = pd.read_excel(str(ruta_xls), header=header, engine=engine)
            break
        except Exception:
            pass

    if df is None:
        print(f"  ✗  {ruta_xls.name}: no se pudo leer con openpyxl ni xlrd", file=sys.stderr)
        return False

    try:
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how="all").reset_index(drop=True)
        df.to_excel(str(destino_xlsx), index=False, engine="openpyxl")
        print(f"  ✓  {ruta_xls.name}  →  {destino_xlsx.name}")
        return True
    except Exception as e:
        print(f"  ✗  {ruta_xls.name}: {e}", file=sys.stderr)
        return False


def main():
    ok = 0

    # ── OM.xls (encabezados en fila 8 → header=7) ────────────────────────────
    om_xls  = DATA_RAW / "OM.xls"
    om_xlsx = DATA_RAW / "OM.xlsx"
    if om_xls.exists():
        if convertir(om_xls, om_xlsx, header=7):
            ok += 1
    else:
        print(f"  -  OM.xls no encontrado en {DATA_RAW}")

    # ── Plan de accion/*.xls ──────────────────────────────────────────────────
    if PLAN_FOLDER.exists():
        for xls in sorted(PLAN_FOLDER.glob("*.xls")):
            xlsx = xls.with_suffix(".xlsx")
            if convertir(xls, xlsx, header=0):
                ok += 1
    else:
        print(f"  -  Carpeta no encontrada: {PLAN_FOLDER}")

    print(f"\nConvertidos: {ok} archivo(s).")


if __name__ == "__main__":
    main()
