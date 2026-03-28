"""
scripts/etl/catalogo.py
Carga unificada del Catálogo de Indicadores y configuraciones derivadas.

MEJORA CLAVE: cargar_catalogo_completo() lee 'Catalogo Indicadores' una
sola vez y extrae extraccion_map, tipo_calculo_map, tipo_indicador_map
y variables_campo_map en una pasada — antes eran 4 lecturas separadas.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from .config import INPUT_FILE, OUTPUT_FILE
from .normalizacion import (
    _fmt_val_raw, _id_str, limpiar_clasificacion, limpiar_html,
)

logger = logging.getLogger(__name__)


# ── Lectura unificada del Catálogo (1 sola I/O) ───────────────────

def cargar_catalogo_completo(src: Optional[Path] = None) -> Dict:
    """
    Lee 'Catalogo Indicadores' del archivo fuente UNA sola vez y retorna:
      {
        'extraccion_map':     {id_str: extraccion_str | None},
        'tipo_calculo_map':   {id_str: tipo_calculo_str},
        'tipo_indicador_map': {id_str: 'Tipo 1'|'Tipo 2'|...},
        'variables_campo_map':{id_str: {'ejec': [simbolos], 'meta': [simbolos]}},
        'user_data':          {id_str: {'TipoCalculo', 'Asociacion', 'Formato_Valores'}},
      }
    """
    source = src or INPUT_FILE
    result: Dict = {
        "extraccion_map":      {},
        "tipo_calculo_map":    {},
        "tipo_indicador_map":  {},
        "variables_campo_map": {},
        "user_data":           {},
    }
    if not source.exists():
        return result
    try:
        xl = pd.ExcelFile(source)
        # ── Hoja Catalogo Indicadores ──────────────────────────
        if "Catalogo Indicadores" in xl.sheet_names:
            df = xl.parse("Catalogo Indicadores")
            df.columns = [str(c).strip() for c in df.columns]
            col_tipo_ind = next(
                (c for c in df.columns if c.strip() == "Tipo de indicador"), None
            )
            for _, row in df.iterrows():
                id_s = _id_str(row.get("Id", ""))
                if not id_s:
                    continue
                # extraccion_map
                val = row.get("Extraccion")
                result["extraccion_map"][id_s] = (
                    None if pd.isna(val) else str(val).strip()
                )
                # tipo_calculo_map
                tc = row.get("TipoCalculo")
                if not pd.isna(tc) and str(tc).strip():
                    result["tipo_calculo_map"][id_s] = str(tc).strip()
                # tipo_indicador_map
                if col_tipo_ind:
                    ti = row.get(col_tipo_ind)
                    if not pd.isna(ti) and str(ti).strip():
                        result["tipo_indicador_map"][id_s] = str(ti).strip()
                # user_data
                result["user_data"][id_s] = {
                    "TipoCalculo":     str(row.get("TipoCalculo", "") or "").strip(),
                    "Asociacion":      str(row.get("Asociacion", "") or "").strip(),
                    "Formato_Valores": _fmt_val_raw(row.get("Formato_Valores")),
                }

        # ── Hoja Variables ─────────────────────────────────────
        if "Variables" in xl.sheet_names:
            dfv = xl.parse("Variables")
            dfv.columns = [str(c).strip() for c in dfv.columns]
            col_id   = next((c for c in dfv.columns if c.lower() == "id"), None)
            col_simb = next(
                (c for c in dfv.columns
                 if "simb" in c.lower() or c.lower() == "var_simbolo"),
                None,
            )
            col_camp = next((c for c in dfv.columns if "campo" in c.lower()), None)
            if all([col_id, col_simb, col_camp]):
                for _, row in dfv.iterrows():
                    id_s = _id_str(row.get(col_id, ""))
                    simb = str(row.get(col_simb, "") or "").strip()
                    camp = str(row.get(col_camp, "") or "").strip()
                    if not id_s or not simb or simb == "None":
                        continue
                    if id_s not in result["variables_campo_map"]:
                        result["variables_campo_map"][id_s] = {"ejec": [], "meta": []}
                    camp_low = camp.lower()
                    if "jecuci" in camp_low:
                        result["variables_campo_map"][id_s]["ejec"].append(simb)
                    elif camp_low == "meta":
                        result["variables_campo_map"][id_s]["meta"].append(simb)
    except Exception as e:
        logger.warning(f"  Error leyendo Catálogo de {source.name}: {e}")

    n1 = sum(1 for v in result["tipo_indicador_map"].values() if v == "Tipo 1")
    n2 = sum(1 for v in result["tipo_indicador_map"].values() if v == "Tipo 2")
    n_tc = len(result["tipo_calculo_map"])
    n_vc = len(result["variables_campo_map"])
    logger.info(
        f"  Catálogo unificado: "
        f"Tipo1={n1} Tipo2={n2} | TipoCalculo={n_tc} | Variables/Campo={n_vc}"
    )
    return result


# ── Funciones individuales (backward compat) ──────────────────────
# Usan cargar_catalogo_completo internamente o leen directamente si
# ya se tiene la info cargada.

def cargar_extraccion_map(src: Optional[Path] = None) -> Dict:
    return cargar_catalogo_completo(src)["extraccion_map"]


def cargar_tipo_calculo_map(src: Optional[Path] = None) -> Dict:
    return cargar_catalogo_completo(src)["tipo_calculo_map"]


def cargar_tipo_indicador_map(src: Optional[Path] = None) -> Dict:
    return cargar_catalogo_completo(src)["tipo_indicador_map"]


def cargar_variables_campo_map(src: Optional[Path] = None) -> Dict:
    return cargar_catalogo_completo(src)["variables_campo_map"]


# ── Construcción del Catálogo completo ────────────────────────────

def construir_catalogo(
    df_api: pd.DataFrame,
    df_hist: Optional[pd.DataFrame] = None,
    metadatos_kawak: Optional[Dict] = None,
    metadatos_cmi: Optional[Dict] = None,
) -> pd.DataFrame:
    if metadatos_kawak is None: metadatos_kawak = {}
    if metadatos_cmi   is None: metadatos_cmi   = {}

    # Leer user_data desde INPUT_FILE y OUTPUT_FILE
    user_data: Dict = {}
    for _src in (INPUT_FILE, OUTPUT_FILE):
        if not _src.exists():
            continue
        try:
            partial = cargar_catalogo_completo(_src)["user_data"]
            for ids, vals in partial.items():
                if ids not in user_data:
                    user_data[ids] = vals
        except Exception:
            pass

    all_ids: Dict = {}
    df_last = df_api.sort_values("fecha").groupby("Id").last().reset_index()
    for c in ["Indicador", "clasificacion", "Proceso", "Periodicidad", "Sentido", "Tipo", "estado"]:
        if c not in df_last.columns:
            df_last[c] = ""
    for _, row in df_last.iterrows():
        ids = _id_str(row["Id"])
        all_ids[ids] = {
            "Id": row["Id"],
            "Indicador":    limpiar_html(str(row["Indicador"])),
            "Clasificacion":limpiar_clasificacion(str(row["clasificacion"])),
            "Proceso":      limpiar_html(str(row["Proceso"])),
            "Periodicidad": str(row["Periodicidad"]),
            "Sentido":      str(row["Sentido"]),
            "Tipo_API":     str(row["Tipo"]),
            "Estado":       str(row["estado"]),
            "Fuente":       "API",
        }

    if df_hist is not None and len(df_hist) > 0:
        df_hc = df_hist.copy()
        df_hc["Fecha"] = pd.to_datetime(df_hc["Fecha"])
        df_hc_last = df_hc.sort_values("Fecha").groupby("Id").last().reset_index()
        col_ind  = next((c for c in ["Indicador", "nombre"] if c in df_hc_last.columns), None)
        col_proc = "Proceso"      if "Proceso"      in df_hc_last.columns else None
        col_per  = "Periodicidad" if "Periodicidad" in df_hc_last.columns else None
        col_sent = "Sentido"      if "Sentido"      in df_hc_last.columns else None
        col_clas = next((c for c in ["Clasificacion", "clasificacion"]
                         if c in df_hc_last.columns), None)
        for _, row in df_hc_last.iterrows():
            ids = _id_str(row["Id"])
            if ids not in all_ids:
                all_ids[ids] = {
                    "Id":           row["Id"],
                    "Indicador":    limpiar_html(str(row[col_ind])) if col_ind else "",
                    "Clasificacion":limpiar_clasificacion(str(row[col_clas])) if col_clas else "",
                    "Proceso":      limpiar_html(str(row[col_proc])) if col_proc else "",
                    "Periodicidad": str(row[col_per])  if col_per  else "",
                    "Sentido":      str(row[col_sent]) if col_sent else "",
                    "Tipo_API": "", "Estado": "Historico", "Fuente": "Historico",
                }

    def _clean(v: object) -> str:
        return "" if (v is None or str(v).strip() in ("", "nan", "None")) else str(v).strip()

    rows = []
    for ids, base in all_ids.items():
        kw  = metadatos_kawak.get(ids, {})
        cmi = metadatos_cmi.get(ids, {})
        nombre        = _clean(kw.get("nombre"))        or _clean(cmi.get("nombre"))        or base["Indicador"]
        clasificacion = _clean(kw.get("clasificacion")) or _clean(cmi.get("clasificacion")) or base["Clasificacion"]
        proceso       = _clean(kw.get("proceso"))       or _clean(cmi.get("proceso"))       or base["Proceso"]
        periodicidad  = _clean(kw.get("periodicidad"))  or _clean(cmi.get("periodicidad"))  or base["Periodicidad"]
        sentido       = _clean(kw.get("sentido"))       or _clean(cmi.get("sentido"))       or base["Sentido"]
        ud = user_data.get(ids, {})
        tipo_calculo    = _clean(ud.get("TipoCalculo"))     or _clean(kw.get("tipo_calculo", ""))
        asociacion      = _clean(ud.get("Asociacion",    ""))
        formato_valores = _clean(ud.get("Formato_Valores", "")) or "%"
        rows.append({
            "Id": base["Id"], "Indicador": nombre, "Clasificacion": clasificacion,
            "Proceso": proceso, "Periodicidad": periodicidad, "Sentido": sentido,
            "Tipo_API": base["Tipo_API"], "Estado": base["Estado"], "Fuente": base["Fuente"],
            "TipoCalculo": tipo_calculo, "Asociacion": asociacion,
            "Formato_Valores": formato_valores,
        })

    df_cat = pd.DataFrame(rows)

    def sort_key(id_val):
        try:    return (0, float(str(id_val)))
        except: return (1, str(id_val))

    return df_cat.sort_values("Id", key=lambda col: col.map(sort_key)).reset_index(drop=True)


# ── Config_Patrones ───────────────────────────────────────────────

def cargar_config_patrones() -> Dict:
    """Lee la hoja 'Config_Patrones' del OUTPUT_FILE si existe."""
    if not OUTPUT_FILE.exists():
        return {}
    try:
        xl = pd.ExcelFile(OUTPUT_FILE)
        if "Config_Patrones" not in xl.sheet_names:
            return {}
        df = xl.parse("Config_Patrones")
        config: Dict = {}
        for _, row in df.iterrows():
            ids = _id_str(row["Id"])
            config[ids] = {
                "patron":       str(row.get("Patron_Ejecucion", "LAST")).strip().upper(),
                "simbolo_ejec": str(row.get("Simbolo_Ejec", "") or "").strip(),
                "simbolo_meta": str(row.get("Simbolo_Meta", "") or "").strip(),
            }
        return config
    except Exception as e:
        logger.warning(f"  Error leyendo Config_Patrones: {e}")
        return {}


def crear_config_patrones_inicial() -> pd.DataFrame:
    """Genera el DataFrame inicial de Config_Patrones desde el diagnóstico."""
    diag_path = OUTPUT_FILE.parent / "diagnostico_fuente_ejecucion.xlsx"
    if not diag_path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(diag_path, sheet_name="Diagnostico")
    except Exception:
        return pd.DataFrame()

    rows = []
    for _, r in df.iterrows():
        ids    = _id_str(r["ID"])
        patron = str(r.get("Patron_Ejecucion", "LAST")).strip().upper()
        simbs  = str(r.get("Simbolos_Variables", "") or "").strip()
        lista  = [s.strip() for s in simbs.split(",") if s.strip()] if simbs else []
        simbolo_ejec = ""
        simbolo_meta = ""
        if patron == "VARIABLES":
            if len(lista) == 1:
                simbolo_ejec = lista[0]
            elif len(lista) == 2:
                simbolo_ejec = lista[0]
                simbolo_meta = lista[1]
        rows.append({
            "Id":               r["ID"],
            "Indicador":        r.get("Indicador", ""),
            "Patron_Ejecucion": patron,
            "Simbolo_Ejec":     simbolo_ejec,
            "Simbolo_Meta":     simbolo_meta,
            "Simbolos_Disponibles": simbs,
            "Nota": ("Revisar simbolos" if patron == "VARIABLES" and len(lista) >= 3 else ""),
        })
    return pd.DataFrame(rows)
