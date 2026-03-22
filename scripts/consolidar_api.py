"""
scripts/consolidar_api.py
--------------------------
Consolida en un solo paso:

  1. data/raw/Kawak/*.xlsx  ->  data/raw/Fuentes Consolidadas/Indicadores Kawak.xlsx
     Todas las filas de todos los años con columnas clave (sin eliminar duplicados):
     Año | Id | Indicador | Clasificacion | Proceso | Tipo | Periodicidad | Sentido

  2. data/raw/API/*.xlsx    ->  data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx
     Todos los registros con fecha de los archivos anuales de la API.
     Usado por generar_reporte.py y pages/2_Indicadores_en_Riesgo.py.

Uso:
    python scripts/consolidar_api.py
"""

import pandas as pd

from pathlib import Path

# -- Rutas ---------------------------------------------------------------------
_ROOT      = Path(__file__).parent.parent
_KW_PATH   = _ROOT / "data" / "raw" / "Kawak"
_API_PATH  = _ROOT / "data" / "raw" / "API"
_OUT_DIR   = _ROOT / "data" / "raw" / "Fuentes Consolidadas"
_OUT_DIR.mkdir(parents=True, exist_ok=True)

_OUT_KAWAK_CAT = _OUT_DIR / "Indicadores Kawak.xlsx"
_OUT_API       = _OUT_DIR / "Consolidado_API_Kawak.xlsx"

YEARS = [2022, 2023, 2024, 2025]

# Columnas del catálogo Kawak
COLS_KAWAK = ["Año", "Id", "Indicador", "Clasificacion", "Proceso",
              "Tipo", "Periodicidad", "Sentido"]


# -----------------------------------------------------------------------------
# UTILIDADES
# -----------------------------------------------------------------------------

def _encontrar_col(df: pd.DataFrame, candidatos: list, idx_fallback: int = None):
    """Primera columna que coincida con algún candidato (case-insensitive)."""
    col_lower = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidatos:
        if cand.lower() in col_lower:
            return col_lower[cand.lower()]
    if idx_fallback is not None and idx_fallback < len(df.columns):
        return df.columns[idx_fallback]
    return None


def _limpiar_html(val):
    if not isinstance(val, str):
        return val
    return (val.replace('&oacute;', 'ó').replace('&eacute;', 'é')
               .replace('&aacute;', 'á').replace('&iacute;', 'í')
               .replace('&uacute;', 'ú').replace('&ntilde;', 'ñ')
               .replace('&Eacute;', 'É').replace('&amp;', '&'))


def _id_str(val):
    """Normaliza Id: 474.0 -> '474'."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s[:-2] if s.endswith('.0') else s


def _diagnosticar(df: pd.DataFrame, etiqueta: str) -> None:
    if "resultado" not in df.columns:
        print(f"  [{etiqueta}] Columna 'resultado' no encontrada")
        return
    nan_count    = df["resultado"].isna().sum()
    na_str_count = (df["resultado"].astype(str).str.strip().str.upper() == "N/A").sum()
    print(f"  [{etiqueta}] NaN reales: {nan_count} | String 'N/A': {na_str_count}")


# -----------------------------------------------------------------------------
# 1. CATÁLOGO KAWAK
# -----------------------------------------------------------------------------

def _procesar_kawak_año(path: Path, year: int) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]

    col_id   = _encontrar_col(df, ['Id', 'ID'],                       idx_fallback=0)
    col_ind  = _encontrar_col(df, ['Indicador', 'Nombre', 'nombre'],  idx_fallback=1)
    col_clas = _encontrar_col(df, ['Clasificación', 'Clasificacion',
                                    'Clasificaci?n', 'clasificacion',
                                    'clasificación'],                  idx_fallback=2)
    col_proc = _encontrar_col(df, ['Proceso', 'Subproceso', 'SS'],    idx_fallback=3)
    col_tipo = _encontrar_col(df, ['Tipo'],                           idx_fallback=4)
    col_per  = _encontrar_col(df, ['Periodicidad', 'frecuencia'])
    col_sent = _encontrar_col(df, ['Sentido'])

    def _get(col):
        return df[col] if col else pd.Series([None] * len(df))

    df_out = pd.DataFrame({
        "Año":          year,
        "Id":           _get(col_id).apply(_id_str),
        "Indicador":    _get(col_ind).apply(lambda v: _limpiar_html(str(v)) if pd.notna(v) else None),
        "Clasificacion":_get(col_clas).apply(lambda v: str(v).strip() if pd.notna(v) else None),
        "Proceso":      _get(col_proc).apply(lambda v: str(v).strip() if pd.notna(v) else None),
        "Tipo":         _get(col_tipo).apply(lambda v: str(v).strip() if pd.notna(v) else None),
        "Periodicidad": _get(col_per).apply(lambda v: str(v).strip() if pd.notna(v) else None),
        "Sentido":      _get(col_sent).apply(lambda v: str(v).strip() if pd.notna(v) else None),
    })

    df_out = df_out[df_out["Id"].notna() & (df_out["Id"] != "")]

    # Limpiar strings residuales
    for col in ["Clasificacion", "Proceso", "Tipo", "Periodicidad", "Sentido"]:
        df_out[col] = df_out[col].replace({'nan': None, 'None': None})

    return df_out[COLS_KAWAK]


def consolidar_kawak() -> None:
    print("\n" + "=" * 60)
    print("PARTE 1: Catálogo Kawak -> Indicadores Kawak.xlsx")
    print("=" * 60)

    if not _KW_PATH.exists():
        print(f"  [ERROR] Carpeta no encontrada: {_KW_PATH}")
        return

    frames = []
    for year in YEARS:
        path = _KW_PATH / f"{year}.xlsx"
        if not path.exists():
            print(f"  [OMITIDO] {path.name} no encontrado")
            continue
        try:
            df = _procesar_kawak_año(path, year)
            print(f"  {year}.xlsx: {len(df):,} indicadores únicos")
            frames.append(df)
        except Exception as e:
            print(f"  [ERROR] {year}.xlsx: {e}")

    if not frames:
        print("  [WARN] No se encontraron archivos en", _KW_PATH)
        return

    df_total = pd.concat(frames, ignore_index=True)
    df_total.to_excel(_OUT_KAWAK_CAT, index=False)

    print(f"  -----------------------------------------------------")
    print(f"  Total filas     : {len(df_total):,}")
    print(f"  IDs únicos      : {df_total['Id'].nunique():,}")
    print(f"  Años cubiertos  : {sorted(df_total['Año'].unique().tolist())}")
    print(f"  [OK] {_OUT_KAWAK_CAT.relative_to(_ROOT)}")


# -----------------------------------------------------------------------------
# 2. CONSOLIDADO API
# -----------------------------------------------------------------------------

def consolidar_api() -> None:
    print("\n" + "=" * 60)
    print("PARTE 2: Consolidado API -> Consolidado_API_Kawak.xlsx")
    print("=" * 60)

    if not _API_PATH.exists():
        print(f"  [ERROR] Carpeta no encontrada: {_API_PATH}")
        return

    frames = []
    for y in YEARS:
        path = _API_PATH / f"{y}.xlsx"
        if not path.exists():
            print(f"  [OMITIDO] {path.name} no encontrado")
            continue

        print(f"  Procesando {y}.xlsx ...")
        df = pd.read_excel(path, keep_default_na=False, na_values=[""])
        _diagnosticar(df, str(y))
        df["año_archivo"] = y

        antes = len(df)
        df    = df[df["fecha"].notna()].copy()
        print(f"  {y}.xlsx: {antes:,} filas -> {len(df):,} (eliminados {antes - len(df):,} sin fecha)")
        frames.append(df)

    if not frames:
        print("  [WARN] No se encontraron archivos en", _API_PATH)
        return

    df_total = pd.concat(frames, ignore_index=True)
    df_total["fecha"] = pd.to_datetime(df_total["fecha"])
    df_total = df_total.sort_values(["ID", "fecha"]).reset_index(drop=True)

    df_total.to_excel(_OUT_API, index=False)

    print(f"  -----------------------------------------------------")
    print(f"  Total registros : {len(df_total):,}")
    print(f"  IDs únicos      : {df_total['ID'].nunique():,}")
    print(f"  Rango fechas    : {df_total['fecha'].min().date()} -> {df_total['fecha'].max().date()}")
    print(f"  [OK] {_OUT_API.relative_to(_ROOT)}")


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    consolidar_kawak()
    consolidar_api()
    print("\n[COMPLETADO]")
