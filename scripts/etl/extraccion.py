"""
scripts/etl/extraccion.py
Estrategias de extracción de Meta y Ejecución desde la fuente API.

Contiene:
  - Constantes de tipos de extracción (_EXT_*)
  - Funciones de extracción básica (variables, series)
  - determinar_meta_ejec()   — lógica heurística/configurada por indicador
  - _extraer_registro()      — punto de entrada unificado
  - _ejec_corrected_from_row / _meta_corrected_from_row — helpers para builders
"""
from __future__ import annotations

import logging
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

import numpy as np
import pandas as pd

from .normalizacion import (
    _es_vacio, _id_str, limpiar_html, nan2none, parse_json_safe,
)
from .no_aplica import SIGNO_NA, is_na_record

logger = logging.getLogger(__name__)

# ── Keywords para extracción por nombre de variable ───────────────
KW_EJEC: List[str] = [
    "real", "ejecutado", "recaudado", "ahorrado", "consumo", "generado",
    "actual", "logrado", "obtenido", "reportado", "hoy",
]
KW_META: List[str] = [
    "planeado", "presupuestado", "propuesto", "programado", "objetivo",
    "esperado", "previsto", "estimado", "acumulado plan",
]

# ── Tipos de extracción ───────────────────────────────────────────
_EXT_SER_SUM_VAR = "Sumar las variables de las series y luego a aplicar la fórmula"
_EXT_SER_AVG_RES = "Aplicar la fórmula a cada serie y luego promediar los resultados"
_EXT_SER_AVG_VAR = "Promediar las variables de las series y luego a aplicar la fórmula"
_EXT_SER_SUM_RES = "Aplicar la fórmula a cada serie y luego sumar los resultados"
_EXT_SERIES_TIPOS: FrozenSet[str] = frozenset([
    _EXT_SER_SUM_VAR, _EXT_SER_AVG_RES, _EXT_SER_AVG_VAR, _EXT_SER_SUM_RES,
])
_EXT_DESGLOSE_SERIES = "Desglose Series"
_IDS_DESGLOSE_VAR_DIRECTO: FrozenSet[str] = frozenset({"122"})


# ── Extracción básica ─────────────────────────────────────────────

def extraer_meta_ejec_variables(
    vars_list: List[Dict],
) -> Tuple[Optional[float], Optional[float]]:
    """Extrae (meta, ejec) de lista de variables por keywords."""
    if not vars_list:
        return None, None
    meta_val = ejec_val = None
    for v in vars_list:
        nombre = str(v.get("nombre", "")).lower()
        valor  = v.get("valor")
        if valor is None or (isinstance(valor, float) and np.isnan(valor)):
            continue
        if any(kw in nombre for kw in KW_META) and meta_val is None:
            meta_val = valor
        elif any(kw in nombre for kw in KW_EJEC) and ejec_val is None:
            ejec_val = valor
    if meta_val is None and len(vars_list) >= 2:
        meta_val = vars_list[1].get("valor")
    if ejec_val is None and len(vars_list) >= 1:
        ejec_val = vars_list[0].get("valor")
    return meta_val, ejec_val


def extraer_meta_ejec_series(
    series_list: List[Dict],
) -> Tuple[Optional[float], Optional[float]]:
    """Suma meta y resultado de todas las series."""
    if not series_list:
        return None, None
    sum_meta = sum_res = 0.0
    has_meta = has_res = False
    for s in series_list:
        m, r = s.get("meta"), s.get("resultado")
        if m is not None and not (isinstance(m, float) and np.isnan(m)):
            sum_meta += float(m); has_meta = True
        if r is not None and not (isinstance(r, float) and np.isnan(r)):
            sum_res  += float(r); has_res  = True
    return (sum_meta if has_meta else None), (sum_res if has_res else None)


def extraer_por_simbolo(vars_list: List[Dict], simbolo: str) -> Optional[float]:
    """Extrae el valor de una variable por su símbolo (case-insensitive)."""
    if not vars_list or not simbolo:
        return None
    simbolo = str(simbolo).strip().upper()
    for v in vars_list:
        if str(v.get("simbolo", "")).strip().upper() == simbolo:
            val = v.get("valor")
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                return float(val)
    return None


def _extraer_por_simbolos(
    vars_list: List[Dict], simbolos: List[str]
) -> Optional[float]:
    """Busca el primer símbolo de la lista en vars_list."""
    for simb in simbolos:
        val = extraer_por_simbolo(vars_list, simb)
        if val is not None:
            return val
    return None


def _sum_series_resultado(series_raw: Any) -> Optional[float]:
    """Suma los 'resultado' de cada serie en el JSON."""
    lst = parse_json_safe(series_raw)
    if not lst:
        return None
    vals = [
        x.get("resultado") for x in lst
        if x.get("resultado") is not None
        and not (isinstance(x.get("resultado"), float) and np.isnan(x.get("resultado")))
    ]
    return sum(vals) if vals else None


def _calc_ejec_series(series_raw: Any, extraccion: str) -> Optional[float]:
    """Calcula Ejecución desde JSON de series según tipo de Extraccion."""
    lst = parse_json_safe(series_raw)
    if not lst:
        return None

    def _ok(v: Any) -> bool:
        return v is not None and not (isinstance(v, float) and np.isnan(v))

    if extraccion == _EXT_SER_SUM_VAR:
        total = sum(v.get("valor", 0) for s in lst
                    for v in s.get("variables", []) if _ok(v.get("valor")))
        return total if any(_ok(v.get("valor")) for s in lst
                            for v in s.get("variables", [])) else None

    if extraccion == _EXT_SER_AVG_VAR:
        sumas = []
        for s in lst:
            vals = [v.get("valor") for v in s.get("variables", []) if _ok(v.get("valor"))]
            if vals:
                sumas.append(sum(vals))
        return sum(sumas) / len(sumas) if sumas else None

    if extraccion == _EXT_SER_AVG_RES:
        vals = [x.get("resultado") for x in lst if _ok(x.get("resultado"))]
        return sum(vals) / len(vals) if vals else None

    if extraccion == _EXT_SER_SUM_RES:
        vals = [x.get("resultado") for x in lst if _ok(x.get("resultado"))]
        return sum(vals) if vals else None

    return None


def _calc_meta_series(series_raw: Any, extraccion: str) -> Optional[float]:
    """Calcula Meta desde JSON de series según tipo de Extraccion."""
    lst = parse_json_safe(series_raw)
    if not lst:
        return None

    def _ok(v: Any) -> bool:
        return v is not None and not (isinstance(v, float) and np.isnan(v))

    metas = [float(x.get("meta")) for x in lst if _ok(x.get("meta"))]
    if not metas:
        return None
    if all(m in (0.0, 1.0) for m in metas):  # flags binarios, no metas reales
        return None
    if extraccion in (_EXT_SER_SUM_VAR, _EXT_SER_SUM_RES):
        return sum(metas)
    if extraccion in (_EXT_SER_AVG_VAR, _EXT_SER_AVG_RES):
        return sum(metas) / len(metas)
    return None


def _agregar_series_por_tipo_calculo(
    series_raw: Any, tipo_calculo: str
) -> Tuple[Optional[float], Optional[float]]:
    """Agrega serie['resultado'] y serie['meta'] según TipoCalculo."""
    tc = str(tipo_calculo or "").strip().lower()
    if tc == "cierre":
        return None, None

    lst = parse_json_safe(series_raw)
    if not lst:
        return None, None

    def _ok(v: Any) -> bool:
        return v is not None and not (isinstance(v, float) and np.isnan(v))

    ejec_vals = [float(x.get("resultado")) for x in lst if _ok(x.get("resultado"))]
    meta_vals  = [float(x.get("meta"))     for x in lst if _ok(x.get("meta"))]
    if not ejec_vals:
        return None, None

    if tc == "acumulado":
        ejec = sum(ejec_vals)
        meta = sum(meta_vals) if meta_vals else None
    elif tc == "promedio":
        ejec = sum(ejec_vals) / len(ejec_vals)
        meta = (sum(meta_vals) / len(meta_vals)) if meta_vals else None
    else:
        ejec = sum(ejec_vals)
        meta = sum(meta_vals) if meta_vals else None

    if meta is not None and all(m in (0.0, 1.0) for m in meta_vals):
        meta = None
    return ejec, meta


# ── determinar_meta_ejec ──────────────────────────────────────────

def determinar_meta_ejec(
    row_api: Dict[str, Any],
    hist_meta_escala: Optional[float],
    patron_cfg: Optional[Dict] = None,
) -> Tuple[Optional[float], Optional[float], str, bool]:
    """
    Determina (meta, ejec, fuente, es_na) para un registro.

    patron_cfg: {'patron': LAST|VARIABLES|SUM_SER|AVG|SUM,
                 'simbolo_ejec': str, 'simbolo_meta': str}

    fuente: 'api_directo'|'variables'|'variables_simbolo'|'series_sum'|
            'series_sum_fallback'|'na_record'|'skip'|'sin_resultado'
    """
    # ── N/A ─────────────────────────────────────────────────────
    if is_na_record(row_api):
        meta_api = row_api.get("meta")
        meta_val = nan2none(
            pd.to_numeric(meta_api, errors="coerce")
            if not _es_vacio(meta_api) else None
        )
        return meta_val, None, "na_record", True

    resultado   = row_api.get("resultado")
    meta_api    = row_api.get("meta")
    vars_list   = parse_json_safe(row_api.get("variables"))
    series_list = parse_json_safe(row_api.get("series"))

    # ── Patrón configurado ───────────────────────────────────────
    if patron_cfg:
        patron = patron_cfg.get("patron", "LAST")

        if patron == "VARIABLES":
            sim_e = patron_cfg.get("simbolo_ejec", "")
            sim_m = patron_cfg.get("simbolo_meta", "")
            _meta_num = nan2none(
                pd.to_numeric(meta_api, errors="coerce")
                if not _es_vacio(meta_api) else None
            )
            if sim_e and vars_list:
                ejec_v = extraer_por_simbolo(vars_list, sim_e)
                if ejec_v is not None:
                    meta_v = (
                        extraer_por_simbolo(vars_list, sim_m) if sim_m else _meta_num
                    )
                    return meta_v, ejec_v, "variables_simbolo", False
            if vars_list:
                meta_v, ejec_v = extraer_meta_ejec_variables(vars_list)
                if ejec_v is not None:
                    return meta_v or _meta_num, ejec_v, "variables", False
            if series_list:
                sum_m, sum_r = extraer_meta_ejec_series(series_list)
                if sum_r is not None:
                    return sum_m or _meta_num, sum_r, "series_sum", False
            return None, None, "skip", False

        if patron == "SUM_SER":
            if series_list:
                sum_m, sum_r = extraer_meta_ejec_series(series_list)
                if sum_r is not None:
                    return sum_m, sum_r, "series_sum", False
            return None, None, "skip", False

        # LAST / AVG / SUM — usa resultado directo
        resultado_num = pd.to_numeric(resultado, errors="coerce")
        if resultado_num is not None and not (
            isinstance(resultado_num, float) and np.isnan(resultado_num)
        ):
            meta_val = nan2none(
                pd.to_numeric(meta_api, errors="coerce")
                if not _es_vacio(meta_api) else None
            )
            return meta_val, resultado_num, "api_directo", False
        return None, None, "sin_resultado", False

    # ── Lógica heurística ────────────────────────────────────────
    es_grande         = (hist_meta_escala is not None and hist_meta_escala > 1000)
    api_es_porcentaje = (
        not _es_vacio(meta_api) and abs(float(meta_api)) <= 200
    )

    if es_grande and api_es_porcentaje:
        if vars_list:
            meta_v, ejec_v = extraer_meta_ejec_variables(vars_list)
            if ejec_v is not None:
                return meta_v, ejec_v, "variables", False
        if series_list:
            sum_m, sum_r = extraer_meta_ejec_series(series_list)
            if sum_r is not None:
                return sum_m, sum_r, "series_sum", False
        return None, None, "skip", False

    resultado_num = pd.to_numeric(resultado, errors="coerce")
    if resultado_num is None or (
        isinstance(resultado_num, float) and np.isnan(resultado_num)
    ):
        if series_list:
            sum_m, sum_r = extraer_meta_ejec_series(series_list)
            if sum_r is not None:
                return sum_m, sum_r, "series_sum_fallback", False
        return None, None, "sin_resultado", False

    meta_val = nan2none(
        pd.to_numeric(meta_api, errors="coerce")
        if not _es_vacio(meta_api) else None
    )
    return meta_val, resultado_num, "api_directo", False


# ── _extraer_registro — punto de entrada unificado ────────────────

def _extraer_registro(
    row: Any,
    hist_escalas: Dict,
    config_patrones: Optional[Dict] = None,
    extraccion_map: Optional[Dict] = None,
    api_kawak_lookup: Optional[Dict] = None,
    variables_campo_map: Optional[Dict] = None,
    tipo_indicador_map: Optional[Dict] = None,
) -> Tuple[Optional[float], Optional[float], str, bool]:
    """
    Extrae (meta, ejec, fuente, es_na) para una fila de fuente.

    Prioridad según columna 'Extraccion' del Catálogo:
      _EXT_SERIES_TIPOS   → calcula desde JSON de series
      _EXT_DESGLOSE_SERIES → agrega serie['resultado']/serie['meta']
      'Desglose Variables' → usa Variables/Campo o heurística
      resto / vacío       → lookup api_kawak_directo o heurística
    """
    row_dict = row.to_dict() if hasattr(row, "to_dict") else row
    id_val = row_dict.get("Id") or row_dict.get("ID")
    id_s   = _id_str(id_val)
    id_num = pd.to_numeric(id_val, errors="coerce")
    hist_meta_escala = hist_escalas.get(id_num) or hist_escalas.get(str(id_val))

    # Kawak2025 directo
    if row_dict.get("fuente") == "Kawak2025":
        return (
            nan2none(row_dict.get("Meta")),
            nan2none(row_dict.get("resultado")),
            "Kawak2025",
            False,
        )

    extraccion = (extraccion_map or {}).get(id_s)

    # ── Series tipos calculados ──────────────────────────────────
    if extraccion in _EXT_SERIES_TIPOS:
        fecha_raw = row_dict.get("fecha")
        try:
            fecha_key = pd.to_datetime(fecha_raw).normalize()
        except Exception:
            fecha_key = None

        meta = _calc_meta_series(row_dict.get("series"), extraccion)
        if meta is None and api_kawak_lookup and fecha_key is not None:
            v = api_kawak_lookup.get((id_s, fecha_key))
            if v:
                meta = v[0]
        if meta is None:
            meta = nan2none(pd.to_numeric(row_dict.get("meta"), errors="coerce")
                            if not _es_vacio(row_dict.get("meta")) else None)

        ejec = _calc_ejec_series(row_dict.get("series"), extraccion)
        if ejec is None and api_kawak_lookup and fecha_key is not None:
            v = api_kawak_lookup.get((id_s, fecha_key))
            if v:
                ejec = v[1]
        if ejec is None:
            return meta, None, "sin_resultado", False
        if is_na_record(row_dict):
            return meta, None, "na_record", True
        return meta, ejec, "series_extraccion", False

    # ── Desglose Series ──────────────────────────────────────────
    if extraccion == _EXT_DESGLOSE_SERIES:
        fecha_raw = row_dict.get("fecha")
        try:
            fecha_key = pd.to_datetime(fecha_raw).normalize()
        except Exception:
            fecha_key = None
        ejec = meta = None
        if api_kawak_lookup and fecha_key is not None:
            v = api_kawak_lookup.get((id_s, fecha_key))
            if v:
                meta, ejec = v
        if ejec is None:
            ejec = nan2none(pd.to_numeric(row_dict.get("resultado"), errors="coerce")
                            if not _es_vacio(row_dict.get("resultado")) else None)
        if meta is None:
            meta = nan2none(pd.to_numeric(row_dict.get("meta"), errors="coerce")
                            if not _es_vacio(row_dict.get("meta")) else None)
        if ejec is None:
            return meta, None, "sin_resultado", False
        if is_na_record(row_dict):
            return meta, None, "na_record", True
        return meta, ejec, "desglose_series", False

    # ── Consolidado_API_Kawak (o vacío) ──────────────────────────
    if extraccion != "Desglose Variables":
        if api_kawak_lookup:
            fecha_raw = row_dict.get("fecha")
            try:
                fecha_key = pd.to_datetime(fecha_raw).normalize()
            except Exception:
                fecha_key = None
            if fecha_key is not None:
                v = api_kawak_lookup.get((id_s, fecha_key))
                if v is not None:
                    meta, res = v
                    if is_na_record(row_dict):
                        return meta, None, "na_record", True
                    return meta, res, "api_kawak_directo", res is None
        patron_cfg = (config_patrones or {}).get(id_s)
        return determinar_meta_ejec(row_dict, hist_meta_escala, patron_cfg)

    # ── Desglose Variables ───────────────────────────────────────
    _tipo_ind = (tipo_indicador_map or {}).get(id_s, "")
    _usar_api_directo = (
        _tipo_ind == "Tipo 1" or id_s in _IDS_DESGLOSE_VAR_DIRECTO
    )

    if _usar_api_directo:
        fecha_raw = row_dict.get("fecha")
        try:
            fecha_key = pd.to_datetime(fecha_raw).normalize()
        except Exception:
            fecha_key = None
        if api_kawak_lookup and fecha_key is not None:
            v = api_kawak_lookup.get((id_s, fecha_key))
            if v is not None:
                meta_v, res_v = v
                if is_na_record(row_dict):
                    return meta_v, None, "na_record", True
                return meta_v, res_v, "api_kawak_directo", res_v is None
        meta_v = nan2none(pd.to_numeric(row_dict.get("meta"), errors="coerce")
                          if not _es_vacio(row_dict.get("meta")) else None)
        res_v  = nan2none(pd.to_numeric(row_dict.get("resultado"), errors="coerce")
                          if not _es_vacio(row_dict.get("resultado")) else None)
        if res_v is None:
            return meta_v, None, "sin_resultado", False
        if is_na_record(row_dict):
            return meta_v, None, "na_record", True
        return meta_v, res_v, "api_kawak_directo", False

    # 1) Config_Patrones override
    patron_cfg = (config_patrones or {}).get(id_s)
    if patron_cfg and patron_cfg.get("simbolo_ejec"):
        return determinar_meta_ejec(row_dict, hist_meta_escala, patron_cfg)

    # 2) Variables/Campo canónico
    campo_info = (variables_campo_map or {}).get(id_s, {})
    simbs_ejec = campo_info.get("ejec", [])
    simbs_meta = campo_info.get("meta", [])
    if simbs_ejec:
        vars_list = parse_json_safe(row_dict.get("variables"))
        ejec_v = _extraer_por_simbolos(vars_list, simbs_ejec) if vars_list else None
        if ejec_v is not None:
            meta_v = _extraer_por_simbolos(vars_list, simbs_meta) if simbs_meta else None
            if meta_v is None:
                meta_v = nan2none(pd.to_numeric(row_dict.get("meta"), errors="coerce")
                                  if not _es_vacio(row_dict.get("meta")) else None)
            if is_na_record(row_dict):
                return meta_v, None, "na_record", True
            return meta_v, ejec_v, "variables_campo", False

    # 3) Fallback heurística
    patron_fb = patron_cfg or {"patron": "VARIABLES", "simbolo_ejec": "", "simbolo_meta": ""}
    return determinar_meta_ejec(row_dict, hist_meta_escala, patron_fb)


# ── Helpers para builders/purga ───────────────────────────────────

def _ejec_corrected_from_row(
    row: Any,
    extraccion_map: Optional[Dict],
    api_kawak_lookup: Optional[Dict],
) -> Optional[float]:
    """Ejecución correcta para una fila del df_fuente (para agregados)."""
    row_d = row.to_dict() if hasattr(row, "to_dict") else row
    id_s  = _id_str(row_d.get("Id") or row_d.get("ID", ""))
    ext   = (extraccion_map or {}).get(id_s)

    if ext in _EXT_SERIES_TIPOS:
        ejec = _calc_ejec_series(row_d.get("series"), ext)
        if ejec is not None:
            return ejec

    if api_kawak_lookup:
        try:
            fecha_key = pd.to_datetime(row_d["fecha"]).normalize()
            v = api_kawak_lookup.get((id_s, fecha_key))
            if v is not None and v[1] is not None:
                return v[1]
        except Exception:
            pass

    return nan2none(pd.to_numeric(row_d.get("resultado"), errors="coerce"))


def _meta_corrected_from_row(
    row: Any,
    extraccion_map: Optional[Dict],
    api_kawak_lookup: Optional[Dict],
) -> Optional[float]:
    """Meta correcta para una fila del df_fuente (para agregados)."""
    row_d = row.to_dict() if hasattr(row, "to_dict") else row
    id_s  = _id_str(row_d.get("Id") or row_d.get("ID", ""))
    ext   = (extraccion_map or {}).get(id_s)

    if ext in _EXT_SERIES_TIPOS:
        meta = _calc_meta_series(row_d.get("series"), ext)
        if meta is not None:
            return meta

    if api_kawak_lookup:
        try:
            fecha_key = pd.to_datetime(row_d["fecha"]).normalize()
            v = api_kawak_lookup.get((id_s, fecha_key))
            if v is not None and v[0] is not None:
                return v[0]
        except Exception:
            pass

    return nan2none(pd.to_numeric(row_d.get("meta"), errors="coerce"))
