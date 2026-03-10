"""
scripts/consolidar_api.py
--------------------------
Consolida los archivos anuales de data/raw/API/ y genera
data/raw/indicadores_kawak.xlsx con todos los registros con fecha.

Este archivo es usado por:
  - generar_reporte.py  → cruza Id × Fecha → Resultado
  - pages/2_Indicadores_en_Riesgo.py → extrae IDs únicos (columna ID)

Uso:
    python scripts/consolidar_api.py
"""

import pandas as pd
from pathlib import Path

# ── Rutas relativas a la raíz del proyecto ────────────────────────────────────
_ROOT      = Path(__file__).parent.parent
_API_PATH  = _ROOT / "data" / "raw" / "API"
_OUT_KAWAK = _ROOT / "data" / "raw" / "indicadores_kawak.xlsx"

YEARS = [2022, 2023, 2024, 2025]


def _diagnosticar(df: pd.DataFrame, etiqueta: str) -> None:
    if "resultado" not in df.columns:
        print(f"  [{etiqueta}] Columna 'resultado' no encontrada")
        return
    nan_count    = df["resultado"].isna().sum()
    na_str_count = (df["resultado"].astype(str).str.strip().str.upper() == "N/A").sum()
    print(f"  [{etiqueta}] NaN reales: {nan_count} | String 'N/A': {na_str_count}")


def consolidar_api() -> None:
    print("=" * 60)
    print("CONSOLIDANDO ARCHIVOS API → indicadores_kawak.xlsx")
    print("=" * 60)

    if not _API_PATH.exists():
        print(f"\n[ERROR] Carpeta no encontrada: {_API_PATH}")
        return

    frames = []
    for y in YEARS:
        path = _API_PATH / f"{y}.xlsx"
        if not path.exists():
            print(f"\n  [OMITIDO] {path.name} no encontrado")
            continue

        print(f"\n  Procesando {y}.xlsx ...")

        # Lectura con protección: N/A no convertido a NaN
        df = pd.read_excel(path, keep_default_na=False, na_values=[""])
        _diagnosticar(df, f"{y}")

        df["año_archivo"] = y

        # Filtrar registros sin fecha
        antes = len(df)
        df    = df[df["fecha"].notna()].copy()
        print(f"  {y}.xlsx: {antes:,} filas → {len(df):,} (eliminados {antes - len(df):,} sin fecha)")

        frames.append(df)

    if not frames:
        print("\n[WARN] No se encontraron archivos en", _API_PATH)
        return

    df_total = pd.concat(frames, ignore_index=True)
    df_total["fecha"] = pd.to_datetime(df_total["fecha"])
    df_total = df_total.sort_values(["ID", "fecha"]).reset_index(drop=True)

    print(f"\n{'─'*60}")
    print(f"  Total registros   : {len(df_total):,}")
    print(f"  IDs únicos        : {df_total['ID'].nunique():,}")
    print(f"  Rango de fechas   : {df_total['fecha'].min().date()} → {df_total['fecha'].max().date()}")

    # ── Guardar consolidación completa como indicadores_kawak.xlsx ────────────
    df_total.to_excel(_OUT_KAWAK, index=False)
    print(f"\n  [OK] Guardado: {_OUT_KAWAK.relative_to(_ROOT)}")
    print("=" * 60)


if __name__ == "__main__":
    consolidar_api()
