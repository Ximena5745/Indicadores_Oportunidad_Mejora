"""
scripts/etl/purga.py
Limpieza y deduplicación de hojas Excel existentes antes de escribir nuevos datos.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, Optional, Set, Tuple

import numpy as np
import pandas as pd

from .config import AÑO_CIERRE_ACTUAL
from .escritura import _ejec_score, get_last_data_row
from .extraccion import _ejec_corrected_from_row, _meta_corrected_from_row
from .formulas_excel import _build_col_map
from .normalizacion import _id_str, make_llave
from .periodos import ultimo_dia_mes

logger = logging.getLogger(__name__)


# ── Purga de filas inválidas ──────────────────────────────────────

def purgar_filas_invalidas(
    ws,
    nombre: str = "hoja",
    kawak_validos: Optional[Set[Tuple[str, int]]] = None,
) -> int:
    """
    Elimina filas donde:
      - La fecha es futura (año > AÑO_CIERRE_ACTUAL)
      - El campo Año contiene texto inválido
      - El par (Id, año) no existe en el catálogo Kawak (si kawak_validos != None)
    """
    cm = _build_col_map(ws)
    idx_id    = cm.get("Id",    1) - 1
    idx_fecha = cm.get("Fecha", 6) - 1
    idx_anio  = cm.get("Anio",  7) - 1

    filas_a_borrar = []
    n_kawak = 0
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        fecha_raw = row[idx_fecha].value if len(row) > idx_fecha else None
        año_fila  = None
        try:
            fecha = pd.to_datetime(fecha_raw)
            año_fila = fecha.year
            if fecha.year > AÑO_CIERRE_ACTUAL:
                filas_a_borrar.append(row[0].row)
                continue
        except Exception:
            pass
        anio_val = row[idx_anio].value if len(row) > idx_anio else None
        if anio_val is not None:
            if isinstance(anio_val, str) and anio_val.startswith("="):
                pass
            else:
                try:
                    año_fila = int(float(anio_val))
                except (TypeError, ValueError):
                    filas_a_borrar.append(row[0].row)
                    continue
        if kawak_validos is not None and año_fila is not None:
            id_val = row[idx_id].value if len(row) > idx_id else None
            id_s   = _id_str(id_val) if id_val is not None else None
            if id_s and (id_s, año_fila) not in kawak_validos:
                filas_a_borrar.append(row[0].row)
                n_kawak += 1

    for r_idx in sorted(set(filas_a_borrar), reverse=True):
        ws.delete_rows(r_idx)
    total = len(set(filas_a_borrar))
    if total:
        logger.info(
            f"  [{nombre}] {total} filas eliminadas "
            f"({n_kawak} por no estar en Indicadores Kawak)."
        )
    return total


# ── Limpiar Consolidado Cierres ───────────────────────────────────

def limpiar_cierres_existentes(ws) -> int:
    """
    Para años <= AÑO_CIERRE_ACTUAL: conserva solo el registro de diciembre.
    Para años > AÑO_CIERRE_ACTUAL: conserva todos.
    """
    filas = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        fecha_raw = row[5].value
        try:    fecha = pd.to_datetime(fecha_raw)
        except: fecha = None
        filas.append({
            "row_idx": row[0].row,
            "Id":      row[0].value,
            "fecha":   fecha,
            "mes":     fecha.month if fecha else None,
            "año":     fecha.year  if fecha else None,
        })

    if not filas:
        return 0

    grupos: Dict = defaultdict(list)
    for f in filas:
        if f["año"] is None:
            continue
        grupos[(str(f["Id"]), f["año"])].append(f)

    filas_a_conservar: Set[int] = set()
    for (id_val, año), grupo in grupos.items():
        if año > AÑO_CIERRE_ACTUAL:
            for f in grupo:
                filas_a_conservar.add(f["row_idx"])
        else:
            dic = [f for f in grupo if f["mes"] == 12]
            keep = sorted(dic if dic else grupo, key=lambda f: f["fecha"])[-1]
            filas_a_conservar.add(keep["row_idx"])

    for f in filas:
        if f["año"] is None:
            filas_a_conservar.add(f["row_idx"])

    filas_a_borrar = sorted(
        [f["row_idx"] for f in filas if f["row_idx"] not in filas_a_conservar],
        reverse=True,
    )
    for r_idx in filas_a_borrar:
        ws.delete_rows(r_idx)

    logger.info(f"  limpiar_cierres: {len(filas_a_borrar)} filas eliminadas.")
    return len(filas_a_borrar)


def _dedup_cierres_por_año(ws) -> int:
    """Garantiza UN registro por Id+Año en Consolidado Cierres (el más reciente)."""
    cm = _build_col_map(ws)
    idx_fecha = cm.get("Fecha", 6) - 1
    idx_ejec  = cm.get("Ejecucion", 11) - 1

    filas = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        fecha_raw = row[idx_fecha].value
        try:    fecha = pd.to_datetime(fecha_raw)
        except: fecha = None
        ejec_val = row[idx_ejec].value if len(row) > idx_ejec else None
        filas.append({
            "row_idx": row[0].row,
            "Id":      _id_str(row[0].value),
            "fecha":   fecha,
            "año":     fecha.year if fecha else None,
            "ejec":    ejec_val,
        })

    if not filas:
        return 0

    grupos: Dict = defaultdict(list)
    for f in filas:
        if f["año"] is None:
            continue
        grupos[(f["Id"], f["año"])].append(f)

    filas_a_borrar = []
    for (_id, _año), grupo in grupos.items():
        if len(grupo) <= 1:
            continue
        mejor = max(grupo, key=lambda f: (
            f["fecha"] or pd.Timestamp.min,
            _ejec_score(f["ejec"]),
        ))
        filas_a_borrar.extend(
            f["row_idx"] for f in grupo if f["row_idx"] != mejor["row_idx"]
        )

    for r_idx in sorted(filas_a_borrar, reverse=True):
        ws.delete_rows(r_idx)

    logger.info(
        f"  _dedup_cierres_por_año: {len(filas_a_borrar)} duplicados eliminados."
    )
    return len(filas_a_borrar)


# ── Reparar Meta / Ejecucion vacías ───────────────────────────────

def reparar_meta_vacia(ws, api_kawak_lookup: Dict, nombre: str = "") -> int:
    """Rellena Meta (y Ejecucion) vacías usando el lookup API_Kawak."""
    if not api_kawak_lookup:
        return 0
    cm = _build_col_map(ws)
    idx_id    = cm.get("Id")
    idx_fecha = cm.get("Fecha")
    idx_meta  = cm.get("Meta")
    idx_ejec  = cm.get("Ejecucion")
    if not all([idx_id, idx_fecha, idx_meta, idx_ejec]):
        return 0

    n_meta = n_ejec = 0
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        meta_cell = row[idx_meta - 1]
        ejec_cell = row[idx_ejec - 1]
        meta_val  = meta_cell.value
        ejec_val  = ejec_cell.value

        if meta_val is not None and not (isinstance(meta_val, float) and np.isnan(meta_val)):
            continue

        try:
            fecha_key = pd.to_datetime(row[idx_fecha - 1].value).normalize()
        except Exception:
            continue

        id_s = _id_str(row[idx_id - 1].value)
        vals = api_kawak_lookup.get((id_s, fecha_key))
        if vals is None:
            continue

        meta_lookup, ejec_lookup = vals
        if meta_lookup is not None:
            meta_cell.value = meta_lookup
            meta_cell.number_format = "General"
            n_meta += 1
        if (ejec_val is None or (isinstance(ejec_val, float) and np.isnan(ejec_val))) \
                and ejec_lookup is not None:
            ejec_cell.value = ejec_lookup
            n_ejec += 1

    if n_meta or n_ejec:
        logger.info(f"  [{nombre}] Meta reparada: {n_meta} | Ejecucion reparada: {n_ejec}")
    else:
        logger.info(f"  [{nombre}] Sin Meta vacía reparable.")
    return n_meta


def reparar_multiserie(
    ws,
    api_kawak_lookup: Dict,
    tipo_calculo_map: Dict,
    nombre: str = "",
) -> int:
    """
    Para indicadores multiserie (TipoCalculo definido), sobreescribe Meta
    y Ejecucion con valores del lookup, incluso si ya tienen valor.
    """
    if not api_kawak_lookup or not tipo_calculo_map:
        return 0
    cm = _build_col_map(ws)
    idx_id    = cm.get("Id")
    idx_fecha = cm.get("Fecha")
    idx_meta  = cm.get("Meta")
    idx_ejec  = cm.get("Ejecucion")
    if not all([idx_id, idx_fecha, idx_meta, idx_ejec]):
        return 0

    n_meta = n_ejec = 0
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        id_s = _id_str(row[idx_id - 1].value)
        if id_s not in tipo_calculo_map:
            continue
        try:
            fecha_key = pd.to_datetime(row[idx_fecha - 1].value).normalize()
        except Exception:
            continue
        vals = api_kawak_lookup.get((id_s, fecha_key))
        if vals is None:
            continue

        meta_cell = row[idx_meta - 1]
        ejec_cell = row[idx_ejec - 1]
        meta_lookup, ejec_lookup = vals

        if meta_lookup is not None and meta_cell.value != meta_lookup:
            meta_cell.value = meta_lookup
            meta_cell.number_format = "General"
            n_meta += 1
        if ejec_lookup is not None and ejec_cell.value != ejec_lookup:
            ejec_cell.value = ejec_lookup
            n_ejec += 1

    if n_meta or n_ejec:
        logger.info(f"  [{nombre}] Multiserie corregida: Meta={n_meta} Ejec={n_ejec}")
    else:
        logger.info(f"  [{nombre}] Multiserie: sin correcciones.")
    return n_meta


def reparar_semestral_agregados(
    ws,
    df_fuente_api: pd.DataFrame,
    extraccion_map: Dict,
    tipo_calculo_map: Dict,
    nombre: str = "",
) -> int:
    """
    Para indicadores Promedio/Acumulado, recalcula Meta y Ejecucion
    desde los datos mensuales (corrige el efecto de reparar_multiserie
    que escribe el valor mensual en lugar del agregado semestral/anual).
    """
    ids_avg = {ids for ids, tc in tipo_calculo_map.items() if tc.lower() == "promedio"}
    ids_sum = {ids for ids, tc in tipo_calculo_map.items() if tc.lower() == "acumulado"}
    ids_agg = ids_avg | ids_sum
    if not ids_agg:
        logger.info(f"  [{nombre}] Sin indicadores Promedio/Acumulado.")
        return 0

    # Lookup mensual: {(id_s, year, month): (ejec, meta)}
    monthly: Dict = {}
    for _, r in df_fuente_api.iterrows():
        id_s = _id_str(r.get("Id") or r.get("ID", ""))
        if id_s not in ids_agg:
            continue
        try:
            fecha = pd.to_datetime(r["fecha"])
        except Exception:
            continue
        ejec_v = _ejec_corrected_from_row(r, extraccion_map, None)
        meta_v = _meta_corrected_from_row(r, extraccion_map, None)
        monthly[(id_s, fecha.year, fecha.month)] = (ejec_v, meta_v)

    cm = _build_col_map(ws)
    idx_id    = cm.get("Id")
    idx_fecha = cm.get("Fecha")
    idx_meta  = cm.get("Meta")
    idx_ejec  = cm.get("Ejecucion")
    if not all([idx_id, idx_fecha, idx_meta, idx_ejec]):
        return 0

    is_cierre = "Cierre" in ws.title or "Cierres" in ws.title
    n_fix = 0

    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        id_s = _id_str(row[idx_id - 1].value)
        if id_s not in ids_agg:
            continue
        try:
            fecha = pd.to_datetime(row[idx_fecha - 1].value)
        except Exception:
            continue

        patron = "AVG" if id_s in ids_avg else "SUM"
        months = list(range(1, 13)) if is_cierre else (
            list(range(1, 7)) if fecha.month <= 6 else list(range(7, 13))
        )

        ejecs = [monthly.get((id_s, fecha.year, m), (None, None))[0] for m in months]
        metas = [monthly.get((id_s, fecha.year, m), (None, None))[1] for m in months]
        ejecs = [e for e in ejecs if e is not None]
        metas = [m for m in metas if m is not None]

        if not ejecs:
            continue

        ejec_agg = sum(ejecs) / len(ejecs) if patron == "AVG" else sum(ejecs)
        meta_agg = (
            (sum(metas) / len(metas) if patron == "AVG" else sum(metas))
            if metas else None
        )

        ejec_cell = row[idx_ejec - 1]
        meta_cell = row[idx_meta - 1]
        if ejec_cell.value != ejec_agg:
            ejec_cell.value = ejec_agg
            n_fix += 1
        if meta_agg is not None and meta_cell.value != meta_agg:
            meta_cell.value = meta_agg
            meta_cell.number_format = "General"

    logger.info(f"  [{nombre}] Promedio/Acumulado recalculados: {n_fix} filas")
    return n_fix
