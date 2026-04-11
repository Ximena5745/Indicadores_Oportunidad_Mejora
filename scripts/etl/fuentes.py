"""
scripts/etl/fuentes.py
Carga de todas las fuentes de datos externas.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import numpy as np
import pandas as pd

from .config import BASE_PATH, CONSOLIDADO_API_KW, KAWAK_CAT_FILE
from .extraccion import (
    _EXT_SERIES_TIPOS, _EXT_DESGLOSE_SERIES,
    _calc_ejec_series, _calc_meta_series,
    _sum_series_resultado,
)
from .normalizacion import (
    _id_str, limpiar_clasificacion, limpiar_html, make_llave, nan2none,
)
from .periodos import fechas_por_periodicidad, ultimo_dia_mes

logger = logging.getLogger(__name__)

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


# ── Fuente principal (Consolidado_API_Kawak.xlsx) ─────────────────

def cargar_fuente_consolidada() -> pd.DataFrame:
    """Lee Consolidado_API_Kawak.xlsx generado por consolidar_api.py."""
    if not CONSOLIDADO_API_KW.exists():
        logger.error(
            f"No se encontró {CONSOLIDADO_API_KW}.\n"
            "  Ejecutar primero: python scripts/consolidar_api.py"
        )
        return pd.DataFrame()
    df = pd.read_excel(CONSOLIDADO_API_KW)
    df = df.dropna(subset=["fecha"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    if "clasificacion" in df.columns:
        df["clasificacion"] = df["clasificacion"].apply(limpiar_clasificacion)
    df = df.rename(columns={
        "ID": "Id", "nombre": "Indicador", "proceso": "Proceso",
        "frecuencia": "Periodicidad", "sentido": "Sentido",
    })
    id_series = df["Id"].map(_id_str)
    fecha_series = df["fecha"]
    df["LLAVE"] = (
        id_series
        + "-"
        + fecha_series.dt.year.astype(int).astype(str)
        + "-"
        + fecha_series.dt.month.astype(int).astype(str).str.zfill(2)
        + "-"
        + fecha_series.dt.day.astype(int).astype(str).str.zfill(2)
    )
    return df


# ── Kawak 2025 ────────────────────────────────────────────────────

def cargar_kawak_2025() -> pd.DataFrame:
    path = BASE_PATH / "Kawak" / "2025.xlsx"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_excel(path)
    rename_map: Dict[str, str] = {}
    for col in df.columns:
        if "Clasificaci" in col:                rename_map[col] = "clasificacion"
        elif "Meta" in col and "ltimo" in col:  rename_map[col] = "Meta"
        elif "Tipo de variable" in col:         rename_map[col] = "Tipo_variable"
        elif "Tipo de calculo" in col:          rename_map[col] = "TipoCalculo"
        elif "Nombre variable" in col:          rename_map[col] = "NombreVar"
    df = df.rename(columns=rename_map)
    if "clasificacion" not in df.columns:
        df["clasificacion"] = ""
    df["clasificacion"] = df["clasificacion"].apply(limpiar_clasificacion)

    periodo_cols = [c for c in df.columns if str(c).startswith("Periodo ")]
    df_global = (
        df[df["NombreVar"].str.contains("Consolidado Global", na=False)].copy()
        if "NombreVar" in df.columns
        else pd.DataFrame()
    )
    ids_sin_global = set(df["Id"]) - set(df_global["Id"])
    if ids_sin_global:
        extra = df[df["Id"].isin(ids_sin_global)].drop_duplicates("Id")
        df_global = pd.concat([df_global, extra], ignore_index=True)

    records = []
    for _, row in df_global.iterrows():
        periodicidad = row.get("Periodicidad", "Mensual")
        fechas = fechas_por_periodicidad(periodicidad, 2025)
        for i, col in enumerate(periodo_cols):
            if i >= len(fechas):
                break
            valor = row.get(col)
            if pd.isna(valor):
                continue
            records.append({
                "Id": row["Id"], "Indicador": limpiar_html(str(row.get("Indicador", ""))),
                "clasificacion": row["clasificacion"], "Proceso": row.get("Proceso", ""),
                "Periodicidad": periodicidad, "Sentido": row.get("Sentido", ""),
                "TipoCalculo": row.get("TipoCalculo", ""),
                "Meta": row.get("Meta", np.nan), "resultado": valor,
                "meta": row.get("Meta", np.nan), "fecha": fechas[i], "fuente": "Kawak2025",
            })
    if not records:
        return pd.DataFrame()
    df_k = pd.DataFrame(records)
    id_series = df_k["Id"].map(_id_str)
    fecha_series = pd.to_datetime(df_k["fecha"], errors="coerce")
    df_k = df_k.loc[fecha_series.notna()].copy()
    id_series = id_series.loc[df_k.index]
    fecha_series = fecha_series.loc[df_k.index]
    df_k["fecha"] = fecha_series
    df_k["LLAVE"] = (
        id_series
        + "-"
        + fecha_series.dt.year.astype(int).astype(str)
        + "-"
        + fecha_series.dt.month.astype(int).astype(str).str.zfill(2)
        + "-"
        + fecha_series.dt.day.astype(int).astype(str).str.zfill(2)
    )
    return df_k


def cargar_kawak_old(years: tuple = (2021,)) -> pd.DataFrame:
    frames = []
    for y in years:
        path = BASE_PATH / "Kawak" / f"{y}.xlsx"
        if not path.exists():
            continue
        df = pd.read_excel(path)
        df["año_archivo"] = y
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["fecha"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["clasificacion"] = df["clasificacion"].apply(limpiar_clasificacion)
    df = df.rename(columns={"ID": "Id", "nombre": "Indicador",
                             "proceso": "Proceso", "sentido": "Sentido"})
    if "frecuencia" in df.columns:
        df = df.rename(columns={"frecuencia": "Periodicidad"})
    elif "Periodicidad" not in df.columns:
        df["Periodicidad"] = "Mensual"
    id_series = df["Id"].map(_id_str)
    fecha_series = df["fecha"]
    df["LLAVE"] = (
        id_series
        + "-"
        + fecha_series.dt.year.astype(int).astype(str)
        + "-"
        + fecha_series.dt.month.astype(int).astype(str).str.zfill(2)
        + "-"
        + fecha_series.dt.day.astype(int).astype(str).str.zfill(2)
    )
    return df


# ── Catálogo Kawak ────────────────────────────────────────────────

def cargar_lmi_reporte() -> Set[str]:
    """Retorna set de IDs (str) cuyo Tipo == 'Metrica' o cuyo nombre contiene 'metrica'."""
    path = BASE_PATH / "lmi_reporte.xlsx"
    if not path.exists():
        logger.info(f"  No se encontró {path.name}; ids_metrica = vacío")
        return set()
    try:
        df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        col_tipo = next(
            (c for c in df.columns
             if c.lower().startswith("tipo")
             and "variable" not in c.lower()
             and "calculo" not in c.lower()),
            None,
        )
        col_ind = next(
            (c for c in df.columns if c.lower().startswith("indicador")), None
        )
        col_id = next((c for c in df.columns if c.lower() == "id"), "Id")
        mask = pd.Series(False, index=df.index)
        if col_tipo:
            mask |= df[col_tipo].astype(str).str.strip().str.lower() == "metrica"
        if col_ind:
            mask |= df[col_ind].astype(str).str.lower().str.contains("metrica", na=False)
        ids: Set[str] = set()
        for val in df.loc[mask, col_id].dropna():
            s = str(val).strip()
            ids.add(s[:-2] if s.endswith(".0") else s)
        return ids
    except Exception as e:
        logger.warning(f"  Error leyendo lmi_reporte.xlsx: {e}")
        return set()


def cargar_kawak_validos() -> Optional[Set[Tuple[str, int]]]:
    """Set de tuplas (id_str, año) válidos. None = sin filtro."""
    if not KAWAK_CAT_FILE.exists():
        logger.warning(
            f"  No se encontró {KAWAK_CAT_FILE.name}; filtro Kawak desactivado."
        )
        return None
    try:
        df = pd.read_excel(KAWAK_CAT_FILE)
        df.columns = [str(c).strip() for c in df.columns]
        col_id  = next((c for c in df.columns if c.lower() == "id"), None)
        col_año = next(
            (c for c in df.columns if c.lower() in ("año", "anio", "year")), None
        )
        if not col_id or not col_año:
            logger.warning(f"  Columnas Id/Año no encontradas en {KAWAK_CAT_FILE.name}.")
            return None
        validos: Set[Tuple[str, int]] = set()
        for _, row in df.iterrows():
            id_s = _id_str(row[col_id])
            try:
                año = int(float(row[col_año]))
            except (TypeError, ValueError):
                continue
            if id_s:
                validos.add((id_s, año))
        return validos
    except Exception as e:
        logger.warning(f"  Error leyendo {KAWAK_CAT_FILE.name}: {e}")
        return None


# ── Metadatos maestros ────────────────────────────────────────────

def cargar_metadatos_kawak() -> Dict:
    meta: Dict = {}
    if KAWAK_CAT_FILE.exists():
        try:
            df = pd.read_excel(KAWAK_CAT_FILE)
            df.columns = [str(c).strip() for c in df.columns]
            col_id   = next((c for c in df.columns if c.lower() == "id"), None)
            col_ind  = next((c for c in df.columns if c.lower() == "indicador"), None)
            col_clas = next((c for c in df.columns if "clasificaci" in c.lower()), None)
            col_proc = next((c for c in df.columns if c.lower() == "proceso"), None)
            col_per  = next((c for c in df.columns if c.lower() == "periodicidad"), None)
            col_sent = next((c for c in df.columns if c.lower() == "sentido"), None)
            for _, row in df.iterrows():
                id_val = row.get(col_id) if col_id else None
                if pd.isna(id_val):
                    continue
                ids = _id_str(id_val)
                meta[ids] = {
                    "nombre":        limpiar_html(str(row.get(col_ind, ""))) if col_ind else "",
                    "clasificacion": limpiar_clasificacion(str(row.get(col_clas, ""))) if col_clas else "",
                    "proceso":       limpiar_html(str(row.get(col_proc, ""))) if col_proc else "",
                    "periodicidad":  str(row.get(col_per, "")) if col_per else "",
                    "sentido":       str(row.get(col_sent, "")) if col_sent else "",
                    "tipo_calculo":  "",
                }
        except Exception as e:
            logger.warning(f"  Error leyendo {KAWAK_CAT_FILE.name}: {e}")

    path25 = BASE_PATH / "Kawak" / "2025.xlsx"
    if path25.exists():
        try:
            df25     = pd.read_excel(path25)
            clas_col = next((c for c in df25.columns if "Clasificaci" in c), None)
            tc_col   = next((c for c in df25.columns if "Tipo de calculo" in c), None)
            for _, row in df25.drop_duplicates("Id").iterrows():
                id_val = row.get("Id")
                if pd.isna(id_val):
                    continue
                ids = _id_str(id_val)
                meta[ids] = {
                    "nombre":        limpiar_html(str(row.get("Indicador", ""))),
                    "clasificacion": limpiar_clasificacion(str(row.get(clas_col, "")) if clas_col else ""),
                    "proceso":       limpiar_html(str(row.get("Proceso", ""))),
                    "periodicidad":  str(row.get("Periodicidad", "")),
                    "sentido":       str(row.get("Sentido", "")),
                    "tipo_calculo":  str(row.get(tc_col, "")) if tc_col else "",
                }
        except Exception as e:
            logger.warning(f"  Error leyendo Kawak/2025.xlsx: {e}")
    return meta


def cargar_metadatos_cmi() -> Dict:
    path = BASE_PATH / "Indicadores por CMI.xlsx"
    if not path.exists():
        return {}
    try:
        df = pd.read_excel(path, sheet_name="Worksheet")
    except Exception:
        return {}
    clas_col = next((c for c in df.columns if "Clasificaci" in c), None)
    meta: Dict = {}
    for _, row in df.iterrows():
        id_val = row.get("Id")
        if pd.isna(id_val):
            continue
        ids = _id_str(id_val)
        meta[ids] = {
            "nombre":        limpiar_html(str(row.get("Indicador", ""))),
            "clasificacion": limpiar_clasificacion(str(row.get(clas_col, "")) if clas_col else ""),
            "proceso":       limpiar_html(str(row.get("Subproceso", ""))),
            "periodicidad":  str(row.get("Periodicidad", "")),
            "sentido":       str(row.get("Sentido", "")),
            "tipo_calculo":  "",
        }
    return meta


# ── Mapa subproceso → proceso ─────────────────────────────────────

def cargar_mapa_procesos() -> Dict[str, str]:
    path = BASE_PATH / "Subproceso-Proceso-Area.xlsx"
    if not path.exists():
        return {}
    try:
        df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        col_sub  = next((c for c in df.columns if "Subproceso" in c and ".1" not in c), None)
        col_proc = next((c for c in df.columns if c.lower() == "proceso"), None)
        if not col_sub or not col_proc:
            return {}
        mapa: Dict[str, str] = {}
        for _, row in df.iterrows():
            sub  = str(row.get(col_sub, "") or "").strip()
            proc = str(row.get(col_proc, "") or "").strip()
            if sub and proc:
                mapa[sub.lower()] = proc
        return mapa
    except Exception as e:
        logger.warning(f"  Error leyendo Subproceso-Proceso-Area.xlsx: {e}")
        return {}


def homologar_proceso(subproceso: str, mapa_procesos: Dict) -> str:
    if not mapa_procesos or not subproceso:
        return subproceso
    return mapa_procesos.get(str(subproceso).strip().lower(), subproceso)


# ── Lookup Consolidado_API_Kawak ──────────────────────────────────

def cargar_consolidado_api_kawak_lookup(
    extraccion_map: Optional[Dict] = None,
) -> Dict[Tuple, Tuple]:
    """
    Construye dict {(id_str, fecha_normalizada): (meta, resultado)}
    para acceso O(1) por llave.
    """
    if not CONSOLIDADO_API_KW.exists():
        logger.warning(f"  No se encontró {CONSOLIDADO_API_KW.name}; lookup desactivado.")
        return {}
    try:
        df = pd.read_excel(CONSOLIDADO_API_KW)
        df.columns = [str(c).strip() for c in df.columns]
        col_id   = next((c for c in df.columns if c.upper() == "ID"), None)
        col_fec  = next((c for c in df.columns if c.lower() == "fecha"), None)
        col_meta = next((c for c in df.columns if c.lower() == "meta"), None)
        col_res  = next((c for c in df.columns if c.lower() == "resultado"), None)
        col_ser  = next((c for c in df.columns if c.lower() == "series"), None)
        if not all([col_id, col_fec, col_meta, col_res]):
            logger.warning(f"  Columnas faltantes en {CONSOLIDADO_API_KW.name}")
            return {}
        df[col_fec] = pd.to_datetime(df[col_fec], errors="coerce")
        lookup: Dict[Tuple, Tuple] = {}
        n_series_ext = n_series_fall = 0
        for _, row in df.iterrows():
            id_s  = _id_str(row[col_id])
            fecha = row[col_fec]
            if pd.isna(fecha) or not id_s:
                continue
            key  = (id_s, fecha.normalize())
            meta = nan2none(row[col_meta])
            res  = nan2none(row[col_res])

            if col_ser:
                ext = (extraccion_map or {}).get(id_s)
                if ext in _EXT_SERIES_TIPOS:
                    ser_val = _calc_ejec_series(row[col_ser], ext)
                    if ser_val is not None:
                        res = ser_val; n_series_ext += 1
                    ser_meta = _calc_meta_series(row[col_ser], ext)
                    if ser_meta is not None:
                        meta = ser_meta
                elif ext != _EXT_DESGLOSE_SERIES:
                    if res is None or res == 0.0:
                        ser_sum = _sum_series_resultado(row[col_ser])
                        if ser_sum is not None and ser_sum != 0.0:
                            res = ser_sum; n_series_fall += 1

            existing = lookup.get(key)
            if existing is None or (existing[1] in (None, 0.0) and res not in (None, 0.0)):
                lookup[key] = (meta, res)

        logger.info(
            f"  Lookup Consolidado_API_Kawak: {len(lookup):,} registros "
            f"({n_series_ext} series-ext, {n_series_fall} fallback-suma)"
        )
        return lookup
    except Exception as e:
        logger.warning(f"  Error leyendo {CONSOLIDADO_API_KW.name}: {e}")
        return {}
