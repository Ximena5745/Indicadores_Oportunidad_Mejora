"""
scripts/etl/desglose.py
Expansión de series, variables y análisis a filas planas.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from .normalizacion import _id_str, limpiar_html, make_llave, nan2none, parse_json_safe

logger = logging.getLogger(__name__)


def expandir_series(df_api: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df_api.iterrows():
        parsed = parse_json_safe(r.get("series"))
        if not parsed:
            continue
        for s in parsed:
            row_base = {
                "Id":          r["Id"],
                "Indicador":   limpiar_html(str(r.get("Indicador", ""))),
                "Proceso":     r.get("Proceso", ""),
                "Periodicidad":r.get("Periodicidad", ""),
                "Sentido":     r.get("Sentido", ""),
                "fecha":       r["fecha"],
                "LLAVE":       r["LLAVE"],
                "serie_nombre":    limpiar_html(str(s.get("nombre", ""))),
                "serie_meta":      s.get("meta"),
                "serie_resultado": s.get("resultado"),
            }
            for v in s.get("variables", []):
                row_base[f"var_{v.get('simbolo', 'X')}"] = v.get("valor")
            rows.append(row_base)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def expandir_variables(
    df_api: pd.DataFrame,
    df_kawak25: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    rows = []

    for _, r in df_api.iterrows():
        parsed = parse_json_safe(r.get("variables"))
        if not parsed:
            continue
        for v in parsed:
            rows.append({
                "Id":          r["Id"],
                "Indicador":   limpiar_html(str(r.get("Indicador", ""))),
                "Proceso":     r.get("Proceso", ""),
                "Periodicidad":r.get("Periodicidad", ""),
                "Sentido":     r.get("Sentido", ""),
                "fecha":       r["fecha"],
                "LLAVE":       r["LLAVE"],
                "var_simbolo": v.get("simbolo", ""),
                "var_nombre":  limpiar_html(str(v.get("nombre", ""))),
                "var_valor":   v.get("valor"),
            })

    if df_kawak25 is not None and len(df_kawak25) > 0:
        llaves_api = {r["LLAVE"] for r in rows}
        for _, r in df_kawak25.iterrows():
            llave = r.get("LLAVE")
            if llave in llaves_api:
                continue
            resultado = nan2none(r.get("resultado"))
            if resultado is None:
                continue
            rows.append({
                "Id":          r["Id"],
                "Indicador":   limpiar_html(str(r.get("Indicador", ""))),
                "Proceso":     r.get("Proceso", ""),
                "Periodicidad":r.get("Periodicidad", ""),
                "Sentido":     r.get("Sentido", ""),
                "fecha":       r["fecha"],
                "LLAVE":       llave,
                "var_simbolo": "",
                "var_nombre":  limpiar_html(str(r.get("Indicador", ""))),
                "var_valor":   resultado,
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def expandir_analisis(df_api: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df_api.iterrows():
        analisis = r.get("analisis", "")
        if pd.isna(analisis) or not str(analisis).strip():
            continue
        partes = str(analisis).split(" | ", 2)
        rows.append({
            "Id":       r["Id"],
            "Indicador":limpiar_html(str(r.get("Indicador", ""))),
            "Proceso":  r.get("Proceso", ""),
            "fecha":    r["fecha"],
            "LLAVE":    r["LLAVE"],
            "analisis_fecha": partes[0].strip() if len(partes) > 0 else "",
            "analisis_autor": partes[1].strip() if len(partes) > 1 else "",
            "analisis_texto": limpiar_html(
                partes[2].strip() if len(partes) > 2 else str(analisis).strip()
            ),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()
