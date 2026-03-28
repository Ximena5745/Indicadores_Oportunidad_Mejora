"""
scripts/etl/signos.py
Extracción del mapa de signos (Meta_Signo, Ejecucion_Signo, Decimales)
desde los DataFrames históricos existentes.
"""
from __future__ import annotations

import logging
from typing import Dict

import pandas as pd

from .no_aplica import SIGNO_NA

logger = logging.getLogger(__name__)


def obtener_signos(
    df_hist: pd.DataFrame,
    df_sem: pd.DataFrame,
    df_cierres: pd.DataFrame,
) -> Dict[str, Dict]:
    """
    Construye {id_str: {meta_signo, ejec_signo, dec_meta, dec_ejec}}
    leyendo los tres DataFrames históricos en orden cronológico.

    Regla: el último signo real encontrado prevalece;
           'No Aplica' solo sobreescribe si no hay signo real previo.
    """
    signos: Dict[str, Dict] = {}
    col_ejec_candidates = [
        "Ejecucion_Signo", "Ejecución Signo", "Ejecucion Signo",
        "Ejecución s", "Ejecucion s",
    ]
    col_ms_candidates = ["Meta_Signo", "Meta Signo", "Meta s"]

    for df in [df_hist, df_sem, df_cierres]:
        col_ms = next((c for c in col_ms_candidates if c in df.columns), None)
        col_es = next((c for c in col_ejec_candidates if c in df.columns), None)
        col_dm = "Decimales_Meta"      if "Decimales_Meta"      in df.columns else None
        col_de = "Decimales_Ejecucion" if "Decimales_Ejecucion" in df.columns else None

        for _, row in df.sort_values("Fecha").iterrows():
            id_s = str(row["Id"])
            ejec_signo_raw = row.get(col_es, "%") if col_es else "%"

            # Normalizar variantes de "No Aplica"
            if str(ejec_signo_raw).strip().lower() in ("no aplica", "n/a"):
                ejec_signo_raw = SIGNO_NA

            # No sobreescribir signo real con No Aplica
            if (
                ejec_signo_raw == SIGNO_NA
                and id_s in signos
                and signos[id_s]["ejec_signo"] != SIGNO_NA
            ):
                continue

            signos[id_s] = {
                "meta_signo": row.get(col_ms, "%") if col_ms else "%",
                "ejec_signo": ejec_signo_raw,
                "dec_meta":   row.get(col_dm, 0) if col_dm else 0,
                "dec_ejec":   row.get(col_de, 0) if col_de else 0,
            }

    return signos
