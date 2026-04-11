## (Eliminada línea duplicada 'from __future__ import annotations')
# ── Utilidad de limpieza y orden ───────────────────────────────
def limpiar_ordenar_hoja(ws, nombre: str = "", ordenar_por: list = None, validar: bool = True, log_inconsistencias: bool = True):
    """
    Deduplica, ordena (por año, mes, fecha, etc.), reescribe fórmulas y reporta inconsistencias.
    ordenar_por: lista de campos (ej: ["Anio", "Mes"]).
    """
    deduplicar_sheet(ws, nombre)
    # Ordenar por ID, Año, Mes si no se especifica otro orden
    cm = _build_col_map(ws)
    if not ordenar_por:
        ordenar_por = ["Id", "Anio", "Mes"]
    idxs = [cm.get(campo) for campo in ordenar_por if cm.get(campo)]
    # Columnas que deben ser fórmulas
    col_formula = set([cm.get("Anio"), cm.get("Mes"), cm.get("Semestre"), cm.get("LLAVE")])
    if idxs:
        datos = []
        for row in ws.iter_rows(min_row=2, values_only=False):
            if row[0].value is None:
                continue
            fila = []
            for idx, cell in enumerate(row, start=1):
                if idx in col_formula:
                    fila.append(None)  # Dejar en blanco para que la fórmula se reescriba
                else:
                    fila.append(cell.value)
            datos.append(fila)
        from datetime import datetime, date
        def normaliza_valor(val):
            if isinstance(val, datetime):
                return val.date()
            return val
        datos.sort(key=lambda x: tuple((normaliza_valor(x[i-1]) if x[i-1] is not None else 0) for i in idxs))
        for i, row_vals in enumerate(datos, start=2):
            for j, val in enumerate(row_vals, start=1):
                ws.cell(row=i, column=j).value = val
        # Reescribir fórmulas explícitamente en columnas de fórmula
        from etl.formulas_excel import formula_G, formula_H, formula_I, formula_R
        cm = _build_col_map(ws)
        idx_anio = cm.get("Anio")
        idx_mes = cm.get("Mes")
        idx_sem = cm.get("Semestre")
        idx_llave = cm.get("LLAVE")
        for i in range(2, 2 + len(datos)):
            if idx_anio:
                ws.cell(i, idx_anio).value = formula_G(i)
            if idx_mes:
                ws.cell(i, idx_mes).value = formula_H(i)
            if idx_sem:
                ws.cell(i, idx_sem).value = formula_I(i)
            if idx_llave:
                ws.cell(i, idx_llave).value = formula_R(i)
    # Reescribir SIEMPRE las fórmulas de Cumplimiento y CumplReal
    _reescribir_formulas(ws)
    _materializar_formula_año(ws)
    # Formato de fecha dd/mm/yyyy
    idx_fecha = cm.get("Fecha")
    if idx_fecha:
        for row in ws.iter_rows(min_row=2, values_only=False):
            c = row[idx_fecha-1]
            if c.value:
                c.number_format = "DD/MM/YYYY"
    if validar and log_inconsistencias:
        cm = _build_col_map(ws)
        idx_meta = cm.get("Meta")
        idx_ejec = cm.get("Ejecucion")
        idx_cumpl = cm.get("Cumplimiento")
        inconsistencias = []
        for row in ws.iter_rows(min_row=2, values_only=False):
            if row[0].value is None:
                continue
            meta = row[idx_meta-1].value if idx_meta else None
            ejec = row[idx_ejec-1].value if idx_ejec else None
            cumpl = row[idx_cumpl-1].value if idx_cumpl else None
            if meta is not None and ejec is not None and (cumpl is None or str(cumpl).strip() == ""):
                inconsistencias.append(row[0].row)
        if inconsistencias:
            logger.warning(f"[{ws.title}] Filas con Meta y Ejecución pero Cumplimiento vacío: {inconsistencias}")
## (Eliminada línea duplicada 'from __future__ import annotations')
def ordenar_por_anio(ws, campo_anio: str = "Anio"):
    """Ordena las filas de la hoja por la columna de año (Anio) de forma ascendente."""
    cm = _build_col_map(ws)
    idx_anio = cm.get(campo_anio)
    if not idx_anio:
        return
    datos = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        datos.append([cell.value for cell in row])
    # Ordenar por año (columna idx_anio-1)
    datos.sort(key=lambda x: (x[idx_anio-1] if x[idx_anio-1] is not None else 0))
    # Escribir de nuevo los datos ordenados
    for i, row_vals in enumerate(datos, start=2):
        for j, val in enumerate(row_vals, start=1):
            ws.cell(row=i, column=j).value = val
"""
scripts/etl/escritura.py
Escritura de filas al workbook Excel y utilidades de deduplicación.
"""

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
    _reescribir_formulas, _materializar_formula_año
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
    if df.empty or id_col not in df.columns or fecha_col not in df.columns:
        return set()

    fechas = pd.to_datetime(df[fecha_col], errors="coerce")
    valid = fechas.notna()
    if not valid.any():
        return set()

    ids = df.loc[valid, id_col].map(_id_str)
    fechas_v = fechas.loc[valid]
    llaves_series = (
        ids
        + "-"
        + fechas_v.dt.year.astype(int).astype(str)
        + "-"
        + fechas_v.dt.month.astype(int).astype(str).str.zfill(2)
        + "-"
        + fechas_v.dt.day.astype(int).astype(str).str.zfill(2)
    )
    return set(llaves_series.dropna().tolist())


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
