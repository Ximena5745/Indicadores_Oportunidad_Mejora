"""
scripts/actualizar_consolidado.py
Versión 8 — Orquestador principal del ETL.
Toda la lógica de negocio vive en scripts/etl/.
Este archivo contiene SOLO el flujo main() y las importaciones.

REQUISITO: ejecutar primero  python scripts/consolidar_api.py
  → genera data/raw/Fuentes Consolidadas/Indicadores Kawak.xlsx
  → genera data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx

═══════════════════════════════════════════════════════════════════════
QUÉ ES "No Aplica":
  Un indicador marca "No Aplica" cuando NO corresponde medirlo en ese
  período específico (por diseño, estacionalidad, fase del proyecto, etc.)
  No es un dato faltante ni un error: es una decisión explícita.

CÓMO SE DETECTA en la fuente API:
  1. El campo 'analisis' contiene el texto "no aplica" → es_na = True
  2. resultado=NaN  Y  sin datos en variables/series → es_na = True

CÓMO SE ESCRIBE en el consolidado:
  - Col K  (Ejecucion)        → None  (celda vacía)
  - Col O  (Ejecucion_Signo)  → "No Aplica"
  - Col L  (Cumplimiento)     → ""  via fórmula
  - Col J  (Meta)             → se conserva si existe, None si no
═══════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import shutil
import sys
import warnings
from pathlib import Path

import openpyxl
import pandas as pd

warnings.filterwarnings("ignore")

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── ETL modules ───────────────────────────────────────────────────
from etl.config import AÑO_CIERRE_ACTUAL, OUTPUT_FILE  # noqa: E402
from etl.normalizacion import _id_str, make_llave  # noqa: E402
from etl.fuentes import (                          # noqa: E402
    cargar_fuente_consolidada,
    cargar_kawak_validos,
    cargar_metadatos_kawak,
    cargar_metadatos_cmi,
    cargar_mapa_procesos,
    cargar_lmi_reporte,
    cargar_consolidado_api_kawak_lookup,
)
from etl.catalogo import (                         # noqa: E402
    cargar_catalogo_completo,
    cargar_config_patrones,     # noqa: F401  re-export usado por orchestrator
    construir_catalogo,
)
from etl.signos import obtener_signos                          # noqa: E402
from etl.formulas_excel import (                               # noqa: E402
    _reescribir_formulas,
    _materializar_formula_año,
    _materializar_cumplimiento,
    _ensure_tipo_registro_header,
)
from etl.escritura import (                        # noqa: E402
    llaves_de_df, deduplicar_sheet, escribir_filas, escribir_hoja_nueva,
)
from etl.purga import (                            # noqa: E402
    purgar_filas_invalidas,
    limpiar_cierres_existentes,
    _dedup_cierres_por_año,
    reparar_meta_vacia,
    reparar_multiserie,
    reparar_semestral_agregados,
)
from etl.builders import (                         # noqa: E402
    construir_registros_historico,
    construir_registros_semestral,
    construir_registros_cierres,
)

# ── Logging ───────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%H:%M:%S",
        )

    logger.info("=" * 65)
    logger.info("  ACTUALIZAR CONSOLIDADO  —  Año cierre: %s", AÑO_CIERRE_ACTUAL)
    logger.info("=" * 65)

    # ── 1. Cargar fuente principal ────────────────────────────────
    logger.info("1. Cargando fuente consolidada API/Kawak…")
    df_api = cargar_fuente_consolidada()
    logger.info("   %d registros fuente", len(df_api))

    # ── 2. Catálogo (un solo I/O) ─────────────────────────────────
    logger.info("2. Cargando catálogo…")
    cat_data = cargar_catalogo_completo()
    extraccion_map       = cat_data["extraccion_map"]
    tipo_calculo_map     = cat_data["tipo_calculo_map"]
    tipo_indicador_map   = cat_data["tipo_indicador_map"]
    variables_campo_map  = cat_data["variables_campo_map"]

    # ── 3. Metadatos y catálogos auxiliares ───────────────────────
    logger.info("3. Cargando metadatos y catálogos auxiliares…")
    kawak_validos   = cargar_kawak_validos()
    metadatos_kawak = cargar_metadatos_kawak()
    metadatos_cmi   = cargar_metadatos_cmi()
    mapa_procesos   = cargar_mapa_procesos()
    ids_metrica     = cargar_lmi_reporte()

    api_kawak_lookup = cargar_consolidado_api_kawak_lookup(extraccion_map)
    logger.info("   api_kawak_lookup: %d entradas", len(api_kawak_lookup))

    # ── 4. Config patrones ────────────────────────────────────────
    logger.info("4. Cargando config_patrones…")
    config_patrones = cargar_config_patrones()
    logger.info("   %d patrones configurados", len(config_patrones))

    # ── 5. Abrir workbook ─────────────────────────────────────────
    logger.info("5. Abriendo workbook %s…", OUTPUT_FILE.name)
    wb = openpyxl.load_workbook(OUTPUT_FILE)

    ws_hist     = wb["Consolidado Historico"]
    ws_sem      = wb["Consolidado Semestral"]
    ws_cierres  = wb["Consolidado Cierres"]

    # ── 6. Leer históricos existentes para signos ─────────────────
    logger.info("6. Leyendo hojas existentes…")
    df_hist_ex    = pd.read_excel(OUTPUT_FILE, sheet_name="Consolidado Historico")
    df_sem_ex     = pd.read_excel(OUTPUT_FILE, sheet_name="Consolidado Semestral")
    df_cierres_ex = pd.read_excel(OUTPUT_FILE, sheet_name="Consolidado Cierres")
    signos = obtener_signos(df_hist_ex, df_sem_ex, df_cierres_ex)
    logger.info("   %d indicadores con signo", len(signos))

    # ── 7. Purgar filas inválidas ──────────────────────────────────
    logger.info("7. Purgando filas inválidas…")
    for ws, nom in [(ws_hist, "Historico"), (ws_sem, "Semestral"), (ws_cierres, "Cierres")]:
        _ensure_tipo_registro_header(ws)
        purgar_filas_invalidas(ws, nom, kawak_validos)

    limpiar_cierres_existentes(ws_cierres)

    # ── 8. Construir escalas históricas ───────────────────────────
    logger.info("8. Construyendo escalas históricas…")
    hist_escalas: dict = {}
    for _, row in df_hist_ex.iterrows():
        id_s = _id_str(row.get("Id", ""))
        if id_s and id_s not in hist_escalas:
            hist_escalas[id_s] = {
                "Meta":      row.get("Meta"),
                "Ejecucion": row.get("Ejecucion"),
            }

    # ── 9. Preparar fuentes para builders ─────────────────────────
    logger.info("9. Preparando fuentes para builders…")
    # Llaves existentes (calculadas desde Id+Fecha reales)
    llaves_hist = llaves_de_df(df_hist_ex)
    llaves_sem  = llaves_de_df(df_sem_ex)

    # Normalizar fecha en df_api
    df_api["fecha"] = pd.to_datetime(df_api["fecha"], errors="coerce")
    df_api = df_api.dropna(subset=["fecha"])
    df_api["LLAVE"] = df_api.apply(
        lambda r: make_llave(r["Id"], r["fecha"]), axis=1
    )

    # ── 10. Construir nuevos registros ────────────────────────────
    logger.info("10. Construyendo nuevos registros…")

    regs_hist, skip_h, na_h = construir_registros_historico(
        df_api, llaves_hist, hist_escalas,
        config_patrones=config_patrones,
        mapa_procesos=mapa_procesos,
        kawak_validos=kawak_validos,
        extraccion_map=extraccion_map,
        api_kawak_lookup=api_kawak_lookup,
        variables_campo_map=variables_campo_map,
        tipo_indicador_map=tipo_indicador_map,
    )
    logger.info("   Histórico: %d nuevos, %d omitidos, %d NA", len(regs_hist), skip_h, na_h)

    regs_sem, skip_s, na_s = construir_registros_semestral(
        df_api, llaves_sem, hist_escalas,
        config_patrones=config_patrones,
        mapa_procesos=mapa_procesos,
        kawak_validos=kawak_validos,
        extraccion_map=extraccion_map,
        api_kawak_lookup=api_kawak_lookup,
        tipo_calculo_map=tipo_calculo_map,
        variables_campo_map=variables_campo_map,
        tipo_indicador_map=tipo_indicador_map,
    )
    logger.info("   Semestral: %d nuevos, %d omitidos, %d NA", len(regs_sem), skip_s, na_s)

    regs_cierres, skip_c, na_c = construir_registros_cierres(
        df_api, hist_escalas,
        config_patrones=config_patrones,
        mapa_procesos=mapa_procesos,
        kawak_validos=kawak_validos,
        extraccion_map=extraccion_map,
        api_kawak_lookup=api_kawak_lookup,
        tipo_calculo_map=tipo_calculo_map,
        variables_campo_map=variables_campo_map,
        tipo_indicador_map=tipo_indicador_map,
    )
    logger.info("   Cierres:   %d nuevos, %d omitidos, %d NA", len(regs_cierres), skip_c, na_c)

    # ── 11. Escribir nuevas filas ─────────────────────────────────
    logger.info("11. Escribiendo nuevas filas…")
    if regs_hist:
        escribir_filas(ws_hist, regs_hist, signos, ids_metrica=ids_metrica)
    if regs_sem:
        escribir_filas(ws_sem, regs_sem, signos, ids_metrica=ids_metrica)
    if regs_cierres:
        escribir_filas(ws_cierres, regs_cierres, signos, ids_metrica=ids_metrica)

    # ── 12. Reparar valores vacíos y recalcular ───────────────────
    logger.info("12. Reparando valores y recalculando…")
    for ws, nom in [(ws_hist, "Historico"), (ws_sem, "Semestral"), (ws_cierres, "Cierres")]:
        reparar_meta_vacia(ws, api_kawak_lookup, nom)
        reparar_multiserie(ws, api_kawak_lookup, tipo_calculo_map, nom)

    if tipo_calculo_map:
        reparar_semestral_agregados(
            ws_sem, df_api, extraccion_map, tipo_calculo_map, "Semestral"
        )
        reparar_semestral_agregados(
            ws_cierres, df_api, extraccion_map, tipo_calculo_map, "Cierres"
        )

    # ── 13. Deduplicar y reescribir fórmulas ─────────────────────
    logger.info("13. Deduplicando y reescribiendo fórmulas…")
    for ws, nom in [(ws_hist, "Historico"), (ws_sem, "Semestral")]:
        deduplicar_sheet(ws, nom)
        _reescribir_formulas(ws)
        _materializar_formula_año(ws)
        _materializar_cumplimiento(ws)

    # Cierres: dedup especial
    _dedup_cierres_por_año(ws_cierres)
    _reescribir_formulas(ws_cierres)
    _materializar_formula_año(ws_cierres)
    _materializar_cumplimiento(ws_cierres)

    # ── 14. Actualizar Catálogo Indicadores ───────────────────────
    logger.info("14. Actualizando Catálogo Indicadores…")
    df_catalogo = construir_catalogo(df_api, df_hist_ex, metadatos_kawak, metadatos_cmi)
    if not df_catalogo.empty:
        escribir_hoja_nueva(wb, "Catalogo Indicadores", df_catalogo)
        logger.info("   %d indicadores en catálogo", len(df_catalogo))

    # ── 15. Guardar ───────────────────────────────────────────────
    logger.info("15. Guardando %s…", OUTPUT_FILE.name)
    # Backup antes de sobreescribir
    backup = OUTPUT_FILE.with_suffix(".bak.xlsx")
    try:
        shutil.copy2(OUTPUT_FILE, backup)
    except Exception as exc:
        logger.warning("   No se pudo crear backup: %s", exc)

    wb.save(OUTPUT_FILE)
    logger.info("   Guardado correctamente.")

    # ── Resumen final ─────────────────────────────────────────────
    total_nuevos = len(regs_hist) + len(regs_sem) + len(regs_cierres)
    logger.info("=" * 65)
    logger.info("  COMPLETADO — %d registros nuevos totales", total_nuevos)
    logger.info("=" * 65)


if __name__ == "__main__":
    main()
