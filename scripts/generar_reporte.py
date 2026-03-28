"""
scripts/generar_reporte.py
Paso 3 del pipeline: genera un resumen ejecutivo en JSON y CSV
sobre los archivos de salida del ETL.

Salida (en artifacts/):
  - reporte_YYYYMMDD.json  — métricas por hoja
  - reporte_YYYYMMDD.csv   — tabla plana para revisión rápida
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Archivos a inspeccionar
_TARGETS = [
    {
        "key":    "resultados_consolidados",
        "path":   _ROOT / "data/output/Resultados Consolidados.xlsx",
        "sheets": [
            "Consolidado Historico",
            "Consolidado Semestral",
            "Consolidado Cierres",
            "Catalogo Indicadores",
        ],
    },
    {
        "key":   "seguimiento_reporte",
        "path":  _ROOT / "data/output/Seguimiento_Reporte.xlsx",
        "sheets": None,   # todas
    },
]

_COL_ID    = "Id"
_COL_CUMPL = "Cumplimiento"
_COL_FECHA = "Fecha"


def _resumen_hoja(df: pd.DataFrame) -> dict:
    """Calcula métricas básicas de una hoja."""
    n_rows = len(df)
    cols   = list(df.columns)

    resultado: dict = {"rows": n_rows, "columns": len(cols)}

    # Indicadores únicos
    if _COL_ID in df.columns:
        resultado["ids_unicos"] = int(df[_COL_ID].dropna().nunique())

    # Rango de fechas
    if _COL_FECHA in df.columns:
        fechas = pd.to_datetime(df[_COL_FECHA], errors="coerce").dropna()
        if not fechas.empty:
            resultado["fecha_min"] = str(fechas.min().date())
            resultado["fecha_max"] = str(fechas.max().date())

    # Cumplimiento promedio
    if _COL_CUMPL in df.columns:
        cumpl = pd.to_numeric(df[_COL_CUMPL], errors="coerce").dropna()
        if not cumpl.empty:
            resultado["cumplimiento_promedio"] = round(float(cumpl.mean()), 4)
            resultado["cumplimiento_mediana"]  = round(float(cumpl.median()), 4)

    # Columnas con nulos
    nulos = {
        c: int(df[c].isna().sum())
        for c in [_COL_ID, "Meta", "Ejecucion", _COL_CUMPL]
        if c in df.columns and df[c].isna().any()
    }
    if nulos:
        resultado["nulos"] = nulos

    return resultado


def main() -> int:
    stamp      = datetime.now().strftime("%Y%m%d")
    art_dir    = _ROOT / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)

    reporte: dict = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "archivos": {},
    }
    filas_csv: list = []

    for target in _TARGETS:
        key   = target["key"]
        path  = target["path"]
        sheets_filter = target["sheets"]

        if not path.exists():
            logger.warning("  [%s] Archivo no encontrado: %s", key, path)
            reporte["archivos"][key] = {"error": "archivo no encontrado", "path": str(path)}
            continue

        logger.info("  Leyendo %s…", path.name)
        try:
            xl = pd.ExcelFile(str(path), engine="openpyxl")
        except Exception as exc:
            reporte["archivos"][key] = {"error": str(exc)}
            continue

        sheets_to_read = sheets_filter if sheets_filter else xl.sheet_names
        reporte["archivos"][key] = {"path": str(path.relative_to(_ROOT)), "hojas": {}}

        for sheet in sheets_to_read:
            if sheet not in xl.sheet_names:
                logger.warning("    Hoja '%s' no encontrada en %s", sheet, path.name)
                reporte["archivos"][key]["hojas"][sheet] = {"error": "hoja no encontrada"}
                continue
            try:
                df = xl.parse(sheet, keep_default_na=False, na_values=[""])
                resumen = _resumen_hoja(df)
                reporte["archivos"][key]["hojas"][sheet] = resumen
                logger.info("    %-35s  %d filas", sheet, resumen["rows"])

                filas_csv.append({
                    "archivo": key,
                    "hoja":    sheet,
                    **{k: v for k, v in resumen.items() if not isinstance(v, dict)},
                })
            except Exception as exc:
                reporte["archivos"][key]["hojas"][sheet] = {"error": str(exc)}

    # Guardar JSON
    json_path = art_dir / f"reporte_{stamp}.json"
    json_path.write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Reporte JSON: %s", json_path.relative_to(_ROOT))

    # Guardar CSV
    if filas_csv:
        csv_path = art_dir / f"reporte_{stamp}.csv"
        pd.DataFrame(filas_csv).to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info("Reporte CSV:  %s", csv_path.relative_to(_ROOT))

    logger.info("Generación completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
