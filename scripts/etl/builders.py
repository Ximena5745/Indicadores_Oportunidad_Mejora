"""
scripts/etl/builders.py
Constructores de registros para las hojas Histórico, Semestral y Cierres.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from .config import AÑO_CIERRE_ACTUAL
from .extraccion import (
    _ejec_corrected_from_row, _meta_corrected_from_row, _extraer_registro,
)
from .normalizacion import _id_str, limpiar_html, make_llave, nan2none
from .periodos import _fecha_es_periodo_valido, ultimo_dia_mes

logger = logging.getLogger(__name__)


# ── Histórico ─────────────────────────────────────────────────────

def construir_registros_historico(
    df_fuente: pd.DataFrame,
    llaves_existentes: Set[str],
    hist_escalas: Dict,
    config_patrones: Optional[Dict] = None,
    mapa_procesos: Optional[Dict] = None,
    kawak_validos: Optional[Set[Tuple[str, int]]] = None,
    extraccion_map: Optional[Dict] = None,
    api_kawak_lookup: Optional[Dict] = None,
    variables_campo_map: Optional[Dict] = None,
    tipo_indicador_map: Optional[Dict] = None,
) -> Tuple[List[Dict], int, int]:
    """
    Genera registros nuevos para Consolidado Histórico.
    Retorna (registros, skipped, conteo_na).
    """
    registros = []
    skipped   = 0
    conteo_na = 0
    df = df_fuente[~df_fuente["LLAVE"].isin(llaves_existentes)].dropna(subset=["LLAVE"])

    for row in df.itertuples(index=False):
        if kawak_validos is not None:
            id_s = _id_str(getattr(row, "Id", None) or getattr(row, "ID", ""))
            fecha_raw = getattr(row, "fecha", None)
            try:
                año = pd.to_datetime(fecha_raw).year
            except Exception:
                año = None
            if año is not None and (id_s, año) not in kawak_validos:
                skipped += 1
                continue

        meta, ejec, fuente, es_na = _extraer_registro(
            row, hist_escalas,
            config_patrones=config_patrones,
            extraccion_map=extraccion_map,
            api_kawak_lookup=api_kawak_lookup,
            variables_campo_map=variables_campo_map,
            tipo_indicador_map=tipo_indicador_map,
        )

        if fuente in ("skip", "sin_resultado"):
            skipped += 1
            continue

        if es_na:
            try:
                fecha_ts = pd.to_datetime(getattr(row, "fecha", None))
            except Exception:
                fecha_ts = None
            periodicidad = str(getattr(row, "Periodicidad", ""))
            if periodicidad and fecha_ts is not None:
                if not _fecha_es_periodo_valido(fecha_ts, periodicidad):
                    skipped += 1
                    continue
            conteo_na += 1

        registros.append({
            "Id":          getattr(row, "Id", None),
            "Indicador":   limpiar_html(str(getattr(row, "Indicador", ""))),
            "Proceso":     getattr(row, "Proceso", ""),
            "Periodicidad":getattr(row, "Periodicidad", ""),
            "Sentido":     getattr(row, "Sentido", ""),
            "fecha":       getattr(row, "fecha", None),
            "Meta":        meta,
            "Ejecucion":   ejec,
            "LLAVE":       getattr(row, "LLAVE", None),
            "es_na":       es_na,
        })

    return registros, skipped, conteo_na


# ── Semestral ─────────────────────────────────────────────────────

def construir_registros_semestral(
    df_fuente: pd.DataFrame,
    llaves_existentes: Set[str],
    hist_escalas: Dict,
    config_patrones: Optional[Dict] = None,
    mapa_procesos: Optional[Dict] = None,
    kawak_validos: Optional[Set[Tuple[str, int]]] = None,
    extraccion_map: Optional[Dict] = None,
    api_kawak_lookup: Optional[Dict] = None,
    tipo_calculo_map: Optional[Dict] = None,
    variables_campo_map: Optional[Dict] = None,
    tipo_indicador_map: Optional[Dict] = None,
) -> Tuple[List[Dict], int, int]:
    """
    Genera registros para Consolidado Semestral.

    TipoCalculo:
      Promedio  → promedio de meses del semestre
      Acumulado → suma de meses del semestre
      Cierre    → último período de cierre (jun/dic)
    """
    ids_avg: Set[str] = set()
    ids_sum: Set[str] = set()

    if config_patrones:
        for ids, cfg in config_patrones.items():
            if cfg["patron"] == "AVG":    ids_avg.add(ids)
            elif cfg["patron"] == "SUM":  ids_sum.add(ids)

    if tipo_calculo_map:
        for ids, tc in tipo_calculo_map.items():
            tc_n = tc.lower().strip()
            if tc_n == "promedio":   ids_avg.add(ids)
            elif tc_n == "acumulado": ids_sum.add(ids)

    df_base = df_fuente.copy()
    df_base["_ids"] = df_base["Id"].map(_id_str)
    df_base["_sem"] = (
        df_base["fecha"].dt.year.astype(int).astype(str)
        + "-"
        + (df_base["fecha"].dt.month <= 6).map({True: "1", False: "2"})
    )

    partes = []
    ids_agg = ids_avg | ids_sum

    # ── Indicadores Cierre/estándar ──────────────────────────────
    df_std = df_base[~df_base["_ids"].isin(ids_agg)].copy()
    df_std = df_std[df_std["fecha"].dt.month.isin([6, 12])]
    df_std = df_std[df_std["fecha"].dt.day == df_std["fecha"].dt.daysinmonth]
    partes.append(df_std)

    # ── Indicadores Promedio/Acumulado ───────────────────────────
    registros_agg: List[Dict] = []
    if ids_agg:
        df_agg_src = df_base[df_base["_ids"].isin(ids_agg)].copy()
        agg_records = df_agg_src.to_dict(orient="records")
        df_agg_src["_ejec_corr"] = [
            _ejec_corrected_from_row(rec, extraccion_map, api_kawak_lookup)
            for rec in agg_records
        ]
        df_agg_src["_meta_corr"] = [
            _meta_corrected_from_row(rec, extraccion_map, api_kawak_lookup)
            for rec in agg_records
        ]

        for (id_val, sem_label), grupo in df_agg_src.groupby(["Id", "_sem"]):
            ids = _id_str(id_val)
            patron = "AVG" if ids in ids_avg else "SUM"

            ejecs = pd.to_numeric(grupo["_ejec_corr"], errors="coerce").dropna()
            metas = pd.to_numeric(grupo["_meta_corr"], errors="coerce").dropna()
            if len(ejecs) == 0:
                continue

            ejec_agg = ejecs.mean() if patron == "AVG" else ejecs.sum()
            meta_agg = ((metas.mean() if patron == "AVG" else metas.sum())
                        if len(metas) > 0 else None)

            year, sem = int(sem_label.split("-")[0]), int(sem_label.split("-")[1])
            end_month = 6 if sem == 1 else 12
            end_fecha = pd.Timestamp(year, end_month, ultimo_dia_mes(year, end_month))
            llave = make_llave(id_val, end_fecha)

            if llave in llaves_existentes:
                continue
            if kawak_validos is not None and (ids, year) not in kawak_validos:
                continue

            last = grupo.sort_values("fecha").iloc[-1]
            registros_agg.append({
                "Id":          id_val,
                "Indicador":   limpiar_html(str(last.get("Indicador", ""))),
                "Proceso":     last.get("Proceso", ""),
                "Periodicidad":last.get("Periodicidad", ""),
                "Sentido":     last.get("Sentido", ""),
                "fecha":       end_fecha,
                "Meta":        nan2none(pd.to_numeric(meta_agg, errors="coerce")) if meta_agg is not None else None,
                "Ejecucion":   nan2none(pd.to_numeric(ejec_agg, errors="coerce")),
                "LLAVE":       llave,
                "es_na":       False,
            })

    df_sem = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    df_sem = df_sem.drop(
        columns=["_ids", "_sem", "_ejec_corr", "_meta_corr"], errors="ignore"
    )

    regs_std, skip_std, na_std = construir_registros_historico(
        df_sem, llaves_existentes, hist_escalas,
        config_patrones=config_patrones, mapa_procesos=mapa_procesos,
        kawak_validos=kawak_validos, extraccion_map=extraccion_map,
        api_kawak_lookup=api_kawak_lookup, variables_campo_map=variables_campo_map,
        tipo_indicador_map=tipo_indicador_map,
    )
    return regs_std + registros_agg, skip_std, na_std


# ── Cierres ───────────────────────────────────────────────────────

def construir_registros_cierres(
    df_fuente: pd.DataFrame,
    hist_escalas: Dict,
    config_patrones: Optional[Dict] = None,
    mapa_procesos: Optional[Dict] = None,
    kawak_validos: Optional[Set[Tuple[str, int]]] = None,
    extraccion_map: Optional[Dict] = None,
    api_kawak_lookup: Optional[Dict] = None,
    tipo_calculo_map: Optional[Dict] = None,
    variables_campo_map: Optional[Dict] = None,
    tipo_indicador_map: Optional[Dict] = None,
) -> Tuple[List[Dict], int, int]:
    """
    Genera registros para Consolidado Cierres.

    TipoCalculo:
      Cierre    → último dic (o último mes si no hay dic)
      Promedio  → promedio de todos los meses del año
      Acumulado → suma de todos los meses del año
    """
    df = df_fuente.copy()
    df["año"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    registros: List[Dict] = []
    skipped   = 0
    conteo_na = 0

    ids_avg = {ids for ids, tc in (tipo_calculo_map or {}).items() if tc.lower() == "promedio"}
    ids_sum = {ids for ids, tc in (tipo_calculo_map or {}).items() if tc.lower() == "acumulado"}

    for (id_val, año), grupo in df.groupby(["Id", "año"]):
        id_s = _id_str(id_val)
        if kawak_validos is not None and (id_s, int(año)) not in kawak_validos:
            skipped += len(grupo)
            continue

        patron = ("AVG" if id_s in ids_avg else
                  "SUM" if id_s in ids_sum else
                  "LAST")

        if patron in ("AVG", "SUM"):
            grupo = grupo.sort_values("fecha")
            ejecs = []
            for _, r in grupo.iterrows():
                ev = _ejec_corrected_from_row(r, extraccion_map, api_kawak_lookup)
                if ev is not None:
                    try:   ejecs.append(float(ev))
                    except: pass
            if not ejecs:
                skipped += 1
                continue
            ejec_agg = sum(ejecs) / len(ejecs) if patron == "AVG" else sum(ejecs)

            metas_corr = []
            for _, r in grupo.iterrows():
                mv = _meta_corrected_from_row(r, extraccion_map, api_kawak_lookup)
                if mv is not None:
                    try:   metas_corr.append(float(mv))
                    except: pass
            meta_agg = (
                (sum(metas_corr) / len(metas_corr) if patron == "AVG"
                 else sum(metas_corr))
                if metas_corr else None
            )

            dic_rows = grupo[grupo["mes"] == 12]
            fecha_cierre = (dic_rows.iloc[-1]["fecha"] if len(dic_rows) > 0
                            else grupo.iloc[-1]["fecha"])
            last = grupo.iloc[-1]
            registros.append({
                "Id":          id_val,
                "Indicador":   limpiar_html(str(last.get("Indicador", ""))),
                "Proceso":     last.get("Proceso", ""),
                "Periodicidad":last.get("Periodicidad", ""),
                "Sentido":     last.get("Sentido", ""),
                "fecha":       fecha_cierre,
                "Meta":        meta_agg,
                "Ejecucion":   ejec_agg,
                "LLAVE":       make_llave(id_val, fecha_cierre),
                "es_na":       False,
            })
            continue

        # LAST (Cierre)
        if año > AÑO_CIERRE_ACTUAL:
            candidatos = grupo.sort_values("fecha").tail(1)
        else:
            dic = grupo[grupo["mes"] == 12]
            candidatos = (dic.sort_values("fecha").tail(1)
                          if len(dic) > 0
                          else grupo.sort_values("fecha").tail(1))

        for _, row in candidatos.iterrows():
            meta, ejec, fuente, es_na = _extraer_registro(
                row, hist_escalas,
                config_patrones=config_patrones,
                extraccion_map=extraccion_map,
                api_kawak_lookup=api_kawak_lookup,
                variables_campo_map=variables_campo_map,
                tipo_indicador_map=tipo_indicador_map,
            )
            if fuente in ("skip", "sin_resultado"):
                skipped += 1
                continue
            if es_na:
                conteo_na += 1
            registros.append({
                "Id":          id_val,
                "Indicador":   limpiar_html(str(row.get("Indicador", ""))),
                "Proceso":     row.get("Proceso", ""),
                "Periodicidad":row.get("Periodicidad", ""),
                "Sentido":     row.get("Sentido", ""),
                "fecha":       row["fecha"],
                "Meta":        meta,
                "Ejecucion":   ejec,
                "LLAVE":       row["LLAVE"],
                "es_na":       es_na,
            })

    return registros, skipped, conteo_na
