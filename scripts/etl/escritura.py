"""
scripts/etl/escritura.py
Escritura de filas al workbook Excel y utilidades de deduplicación.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

import numpy as np
import pandas as pd

from .config import IDS_PLAN_ANUAL, IDS_TOPE_100
from .cumplimiento import _calc_cumpl
from .formulas_excel import (
    _build_col_map, _validar_col_formulas,
    formula_G, formula_H, formula_I, formula_L, formula_M, formula_R,
)
from .normalizacion import _id_str, make_llave, nan2none
from .no_aplica import SIGNO_NA

logger = logging.getLogger(__name__)


# ── Utilidades de fila ────────────────────────────────────────────

def get_last_data_row(ws) -> int:
    """Última fila con valor en columna A. NO usar ws.max_row."""
    last = 1
    for row in ws.iter_rows(min_col=1, max_col=1, values_only=False):
        if row[0].value is not None:
            last = row[0].row
    return last


def llaves_de_df(df: pd.DataFrame, id_col: str = "Id", fecha_col: str = "Fecha") -> Set[str]:
    """Calcula LLAVEs desde Id+Fecha (valores reales, no la col LLAVE con fórmulas)."""
    llaves: Set[str] = set()
    for _, row in df.iterrows():
        if pd.isna(row.get(fecha_col)):
            continue
        llave = make_llave(row[id_col], row[fecha_col])
        if llave:
            llaves.add(llave)
    return llaves


def _ejec_score(val: Any) -> int:
    """Score de calidad de una ejecución para elegir la mejor fila en dedup."""
    if val is None:
        return 0
    try:
        return 2 if float(val) != 0.0 else 1
    except Exception:
        return 1 if str(val).strip() not in ("", "nan", "None") else 0


# ── Deduplicación ─────────────────────────────────────────────────

def deduplicar_sheet(ws, nombre: str = "") -> int:
    """
    Elimina filas con LLAVE duplicada (mismo Id+Fecha), conservando la que
    tenga ejecución más completa (no nula, no cero).
    """
    cm = _build_col_map(ws)
    idx_fecha = cm.get("Fecha", 6) - 1
    idx_ejec  = cm.get("Ejecucion", 11) - 1

    filas = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        try:
            llave = make_llave(row[0].value, row[idx_fecha].value)
        except Exception:
            llave = None
        ejec_val = row[idx_ejec].value if len(row) > idx_ejec else None
        filas.append({"row_idx": row[0].row, "llave": llave, "ejec": ejec_val})

    grupos: Dict = defaultdict(list)
    for f in filas:
        grupos[f["llave"]].append(f)

    filas_a_borrar = []
    for llave, grupo in grupos.items():
        if llave is None or len(grupo) <= 1:
            continue
        mejor = max(grupo, key=lambda f: _ejec_score(f["ejec"]))
        filas_a_borrar.extend(
            f["row_idx"] for f in grupo if f["row_idx"] != mejor["row_idx"]
        )

    for r_idx in sorted(filas_a_borrar, reverse=True):
        ws.delete_rows(r_idx)

    logger.info(f"  [{nombre}] {len(filas_a_borrar)} duplicados eliminados.")
    return len(filas_a_borrar)


# ── Escritura principal ───────────────────────────────────────────

def escribir_filas(
    ws,
    filas: List[Dict],
    signos: Dict,
    start_row: Optional[int] = None,
    ids_metrica: Optional[Set[str]] = None,
) -> int:
    """
    Escribe filas nuevas en la hoja usando el mapa de columnas real.
    Retorna el índice de la última fila escrita.
    """
    cm = _build_col_map(ws)
    _validar_col_formulas(cm, ws.title)

    def _set(r: int, campo: str, value: Any, fmt: Optional[str] = None) -> None:
        col = cm.get(campo)
        if col is None:
            return
        ws.cell(r, col).value = value
        if fmt and value is not None:
            ws.cell(r, col).number_format = fmt

    if start_row is None:
        start_row = get_last_data_row(ws) + 1

    r = start_row
    for fila in filas:
        id_str_val = str(fila.get("Id", ""))
        sg = signos.get(id_str_val, {
            "meta_signo": "%", "ejec_signo": "%",
            "dec_meta": 0, "dec_ejec": 0,
        })

        fecha_raw = fila.get("fecha")
        fecha_dt  = pd.to_datetime(fecha_raw) if fecha_raw is not None else None
        fecha_val = fecha_dt.to_pydatetime().date() if fecha_dt is not None else None

        meta    = nan2none(fila.get("Meta"))
        ejec    = nan2none(fila.get("Ejecucion"))
        es_na   = fila.get("es_na", False)
        sentido = str(fila.get("Sentido", "Positivo"))
        es_metrica = ids_metrica is not None and id_str_val in ids_metrica

        if es_na:
            ejec = None
        ejec_signo = SIGNO_NA if es_na else sg["ejec_signo"]

        if es_metrica:
            tipo_registro = "Metrica"
        elif es_na:
            tipo_registro = SIGNO_NA
        else:
            tipo_registro = ""

        _set(r, "Id",           fila.get("Id"))
        _set(r, "Indicador",    fila.get("Indicador", ""))
        _set(r, "Proceso",      fila.get("Proceso", ""))
        _set(r, "Periodicidad", fila.get("Periodicidad", ""))
        _set(r, "Sentido",      sentido)
        _set(r, "Fecha",        fecha_val, "YYYY-MM-DD")

        _set(r, "Anio",     formula_G(r))
        _set(r, "Mes",      formula_H(r))
        _set(r, "Semestre", formula_I(r))

        _set(r, "Meta",      meta)
        _set(r, "Ejecucion", ejec)

        if es_metrica:
            _set(r, "Cumplimiento", None)
            _set(r, "CumplReal",   None)
        else:
            _id_fila = _id_str(fila.get("Id"))
            _tope = 1.0 if _id_fila in IDS_PLAN_ANUAL or _id_fila in IDS_TOPE_100 else 1.3
            _set(r, "Cumplimiento", formula_L(r, tope=_tope), "0.00%")
            _set(r, "CumplReal",   formula_M(r), "0.00%")

        _set(r, "MetaS",        sg["meta_signo"])
        _set(r, "EjecS",        ejec_signo)
        _set(r, "DecMeta",      sg.get("dec_meta", 0))
        _set(r, "DecEjec",      sg.get("dec_ejec", 0))
        _set(r, "LLAVE",        formula_R(r))
        _set(r, "TipoRegistro", tipo_registro)

        r += 1

    return r - 1


# ── Escritura de hojas nuevas ─────────────────────────────────────

def escribir_hoja_nueva(wb, nombre: str, df: pd.DataFrame) -> None:
    """Sobreescribe o crea una hoja con el DataFrame dado."""
    if nombre in wb.sheetnames:
        del wb[nombre]
    ws = wb.create_sheet(nombre)
    for j, col in enumerate(df.columns, 1):
        ws.cell(1, j).value = col
    for i, (_, row) in enumerate(df.iterrows(), 2):
        for j, col in enumerate(df.columns, 1):
            val = row[col]
            if isinstance(val, pd.Timestamp):
                val = val.to_pydatetime().date()
            elif isinstance(val, float) and np.isnan(val):
                val = None
            ws.cell(i, j).value = val
