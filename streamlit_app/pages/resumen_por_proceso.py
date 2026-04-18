from pathlib import Path
import importlib
import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

from components.charts import grafico_historico_indicador, tabla_historica_indicador
from streamlit_app.services.data_service import DataService
from streamlit_app.utils.formatting import formatear_meta_ejecucion_df


MESES_OPCIONES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

MES_MAP = {m.upper(): i + 1 for i, m in enumerate(MESES_OPCIONES)}

NIVELES_COLORS = {
    "sobrecumplimiento": "#1565C0",
    "cumplimiento": "#2E7D32",
    "alerta": "#F9A825",
    "peligro": "#C62828",
    "sin dato": "#6E7781",
}


def _norm_text(value: object) -> str:
    text = str(value or "").strip().upper()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _to_float(value: object) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip().replace("%", "").replace(",", ".")
    try:
        return float(value)
    except Exception:
        return None


def _mes_to_num(value: object) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        try:
            v = int(value)
            return float(v) if 1 <= v <= 12 else None
        except Exception:
            return None

    txt = str(value).strip()
    if not txt:
        return None

    if txt.isdigit():
        v = int(txt)
        return float(v) if 1 <= v <= 12 else None

    txt_norm = _norm_text(txt)
    return float(MES_MAP.get(txt_norm)) if txt_norm in MES_MAP else None


def _cumplimiento_pct(df: pd.DataFrame) -> pd.Series:
    if "Cumplimiento_norm" in df.columns:
        vals = pd.to_numeric(df["Cumplimiento_norm"], errors="coerce")
        return vals * 100

    if "Cumplimiento" in df.columns:
        vals = pd.to_numeric(df["Cumplimiento"].apply(_to_float), errors="coerce")
        max_abs = vals.abs().max(skipna=True) if not vals.dropna().empty else 0
        return vals * 100 if max_abs <= 2 else vals

    if {"Meta", "Ejecucion"}.issubset(df.columns):
        meta = pd.to_numeric(df["Meta"].apply(_to_float), errors="coerce")
        ejec = pd.to_numeric(df["Ejecucion"].apply(_to_float), errors="coerce")
        ratio = (ejec / meta.replace({0: pd.NA})) * 100
        return pd.to_numeric(ratio, errors="coerce")

    return pd.Series(index=df.index, dtype="float64")


def _first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_norm = {_norm_text(c): c for c in df.columns}
    for cand in candidates:
        key = _norm_text(cand)
        if key in cols_norm:
            return cols_norm[key]
    for cand in candidates:
        key = _norm_text(cand)
        for norm_col, real_col in cols_norm.items():
            if key in norm_col:
                return real_col
    return None


def _period_col_for_month(df: pd.DataFrame, month_num: int | None) -> str | None:
    if month_num is None:
        return None
    col = _first_col(df, [f"Periodo {int(month_num)}", f"Periodo{int(month_num)}"])
    if col is not None:
        return col

    period_cols = [c for c in df.columns if _norm_text(c).startswith("PERIODO")]
    for c in period_cols:
        digits = "".join(ch for ch in str(c) if ch.isdigit())
        if digits and int(digits) == int(month_num):
            return c
    return None


def _categoria_por_pct(pct: float | None) -> str:
    if pct is None or pd.isna(pct):
        return "Sin dato"
    if pct >= 105:
        return "Sobrecumplimiento"
    if pct >= 100:
        return "Cumplimiento"
    if pct >= 80:
        return "Alerta"
    return "Peligro"


def _available_months_with_data(df: pd.DataFrame) -> list[int]:
    if df.empty:
        return []
    months = sorted(
        set(
            int(m)
            for m in pd.to_numeric(df.get("Mes"), errors="coerce").dropna().unique()
            if 1 <= int(m) <= 12
        )
    )
    valid = []
    for month in months:
        period_col = _period_col_for_month(df, month)
        if period_col and df[period_col].notna().any():
            valid.append(month)
    return valid


def _default_month_num(df: pd.DataFrame) -> int:
    valid_months = _available_months_with_data(df)
    if valid_months:
        return valid_months[-1]
    return MESES_OPCIONES.index("Diciembre") + 1


def _ensure_historic_tracking(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Cumplimiento_pct"] = _cumplimiento_pct(out)
    out["Cumplimiento_norm"] = pd.to_numeric(out["Cumplimiento_pct"], errors="coerce") / 100
    out["Categoria"] = out["Cumplimiento_pct"].apply(_categoria_por_pct)
    if "Año" in out.columns and "Mes" in out.columns:
        out["Fecha"] = pd.to_datetime(
            out["Año"].astype(str).str.replace("<NA>", "NaN", regex=False)
            + "-"
            + out["Mes"].astype(str).str.replace("<NA>", "NaN", regex=False).str.zfill(2)
            + "-01",
            errors="coerce",
        )
    elif "Periodo" in out.columns:
        out["Fecha"] = pd.to_datetime(out["Periodo"].astype(str), errors="coerce")
    else:
        out["Fecha"] = pd.NaT
    return out


def _build_indicator_history(df: pd.DataFrame, indicador: str) -> pd.DataFrame:
    if df.empty or indicador is None:
        return df.copy()
    history = df[df["Indicador"].astype(str) == str(indicador)].copy()
    if history.empty:
        return history
    history = _ensure_historic_tracking(history)
    return history.sort_values("Fecha").reset_index(drop=True)


def _cumpl_icon(pct: float | None) -> str:
    if pct is None or pd.isna(pct):
        return "⚪"
    if pct >= 105:
        return "🔵"
    if pct >= 100:
        return "🟢"
    if pct >= 80:
        return "🟡"
    return "🔴"


def _cumpl_label(pct: float | None) -> str:
    if pct is None or pd.isna(pct):
        return "⚪ Sin dato"
    return f"{_cumpl_icon(pct)} {pct:.1f}%"


def _latest_per_indicator(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    sort_cols = [c for c in ["Año", "Mes", "Fecha", "Periodo"] if c in df.columns]
    out = df.sort_values(sort_cols) if sort_cols else df.copy()

    if "Id" in out.columns:
        out = out.drop_duplicates(subset=["Id"], keep="last")
    elif "Indicador" in out.columns:
        out = out.drop_duplicates(subset=["Indicador"], keep="last")

    return out.reset_index(drop=True)


def _prepare_tracking(df: pd.DataFrame, map_df: pd.DataFrame, month_num: int | None = None) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    if "Proceso" not in out.columns:
        out["Proceso"] = "Sin proceso"

    if not map_df.empty and {"Subproceso", "Proceso"}.issubset(map_df.columns):
        sub_map = map_df[["Subproceso", "Proceso"]].dropna().drop_duplicates(subset=["Subproceso"]).copy()
        sub_map["sub_norm"] = sub_map["Subproceso"].astype(str).map(_norm_text)

        out["proc_input"] = out["Proceso"].astype(str)
        out["proc_norm"] = out["proc_input"].map(_norm_text)

        out = out.merge(
            sub_map[["sub_norm", "Proceso"]].rename(columns={"Proceso": "Proceso_padre_sub"}),
            left_on="proc_norm",
            right_on="sub_norm",
            how="left",
        )

        out["Proceso_padre"] = out["Proceso_padre_sub"].fillna(out["proc_input"])
        if "Subproceso" in out.columns:
            out["Subproceso_final"] = out["Subproceso"].fillna(out["proc_input"])
        else:
            out["Subproceso_final"] = out["proc_input"]

        out = out.drop(columns=[c for c in ["proc_input", "proc_norm", "sub_norm", "Proceso_padre_sub"] if c in out.columns])
    else:
        out["Proceso_padre"] = out["Proceso"].astype(str)
        out["Subproceso_final"] = out["Proceso"].astype(str)

    meta_col = _first_col(out, ["Meta", "Meta último periodo", "Meta ultimo periodo"])
    if meta_col is not None:
        out["Meta"] = out[meta_col].apply(_to_float)
    else:
        out["Meta"] = pd.NA

    ejec_col = _first_col(out, ["Ejecución", "Ejecucion"])
    period_col = _period_col_for_month(out, month_num) if month_num is not None else None

    if period_col is not None:
        out["Ejecucion"] = out[period_col].apply(_to_float)
    elif month_num is None and "Mes" in out.columns:
        def _row_ejec(row):
            month = _mes_to_num(row.get("Mes"))
            if month is None:
                return None
            col_name = _period_col_for_month(out, int(month))
            return _to_float(row.get(col_name)) if col_name is not None and col_name in row else None

        out["Ejecucion"] = out.apply(_row_ejec, axis=1)
    elif ejec_col is not None:
        out["Ejecucion"] = out[ejec_col].apply(_to_float)
    else:
        out["Ejecucion"] = pd.Series(index=out.index, dtype="float64")

    out["Cumplimiento_pct"] = _cumplimiento_pct(out)
    return out


@st.cache_data(show_spinner=False)
def _load_calidad_data() -> tuple[pd.DataFrame, str | None]:
    excel_path = Path("data") / "raw" / "Monitoreo" / "Monitoreo_Informacion_Procesos 2025.xlsx"
    if not excel_path.exists():
        return pd.DataFrame(), f"No existe el archivo: {excel_path}"

    try:
        df = pd.read_excel(excel_path, skiprows=4, engine="openpyxl")
    except Exception as exc:
        return pd.DataFrame(), f"No se pudo leer el Excel de calidad: {exc}"

    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]

    norm_cols = {_norm_text(c): c for c in df.columns}
    proc_col = next((v for k, v in norm_cols.items() if "PROCESO" in k), None)
    tem_col = next((v for k, v in norm_cols.items() if "TEMATICA" in k), None)

    if proc_col is None:
        return pd.DataFrame(), "No se encontró la columna Proceso en el archivo de calidad."
    if tem_col is None:
        return pd.DataFrame(), "No se encontró la columna Temática en el archivo de calidad."

    metric_cols = [
        c
        for c in df.columns
        if _norm_text(c) not in {_norm_text(proc_col), _norm_text(tem_col)}
    ]
    if len(metric_cols) < 5:
        return pd.DataFrame(), "No se identificaron 5 características evaluadas en el archivo de calidad."

    out = df[[proc_col, tem_col] + metric_cols[:5]].copy()
    out = out.rename(columns={proc_col: "Proceso", tem_col: "Temática"})
    out = out.dropna(subset=["Proceso"]).reset_index(drop=True)
    return out, None


@st.cache_data(show_spinner=False)
def _load_auditoria_mentions(processes: list[str]) -> tuple[pd.DataFrame, str | None]:
    raw_dir = Path("data") / "raw" / "auditoria"
    if not raw_dir.exists():
        return pd.DataFrame(), f"No existe la carpeta: {raw_dir}"

    pdf_files = sorted(raw_dir.glob("*.pdf"))
    if not pdf_files:
        return pd.DataFrame(), "No hay PDFs en data/raw/auditoria."

    PdfReader = None
    for package in ("pypdf", "PyPDF2"):
        try:
            module = importlib.import_module(package)
            PdfReader = getattr(module, "PdfReader", None)
            if PdfReader is not None:
                break
        except Exception:
            continue

    if PdfReader is None:
        return pd.DataFrame(), "No está instalado pypdf ni PyPDF2. Instala uno de esos paquetes para extraer texto de auditoría."

    if not processes:
        return pd.DataFrame(), "No hay procesos disponibles para buscar en los PDFs."

    indicator_keys = [
        "INDICADOR",
        "INDICADORES",
        "CUMPLIMIENTO",
        "DESEMPENO",
        "DESEMPEÑO",
        "MEDICION",
        "MEDICIÓN",
        "METRICA",
        "MÉTRICA",
        "KPI",
        "OBJETIVO",
        "OBJETIVOS",
        "LINEA BASE",
        "LÍNEA BASE",
        "VARIACION",
        "VARIACIÓN",
        "TENDENCIA",
        "BRECHA",
        "META",
        "EJECUCION",
        "EJECUCIÓN",
        "RESULTADO",
        "AVANCE",
        "HALLAZGO",
        "RIESGO",
        "CONTROL",
        "VERIFICACION",
        "VERIFICACIÓN",
        "EVIDENCIA",
        "SEGUIMIENTO",
        "PLAN DE MEJORAMIENTO",
    ]
    indicator_keys_norm = {_norm_text(k) for k in indicator_keys}

    def _split_sentences(text: str) -> list[str]:
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        if not text:
            return []
        parts = re.split(r"(?<=[\.!\?;])\s+", text)
        return [p.strip() for p in parts if p and len(p.strip()) > 20]

    def _contains_indicator_context(text_norm: str) -> bool:
        return any(k in text_norm for k in indicator_keys_norm)

    def _extract_detected_terms(text_norm: str) -> list[str]:
        found = [k for k in indicator_keys_norm if k in text_norm]
        return sorted(found)

    def _redact_summary(proc: str, fragments: list[str]) -> str:
        if not fragments:
            return f"No se identificó evidencia explícita de indicadores para {proc} en los documentos revisados."

        clean = []
        seen = set()
        for frag in fragments:
            f = re.sub(r"\s+", " ", str(frag or "")).strip()
            if not f:
                continue
            key = _norm_text(f)
            if key in seen:
                continue
            seen.add(key)
            clean.append(f)

        if not clean:
            return f"No se identificó evidencia explícita de indicadores para {proc} en los documentos revisados."

        top = clean[:3]
        if len(top) == 1:
            return f"Para el proceso {proc}, la auditoría reporta que {top[0]}"
        if len(top) == 2:
            return f"Para el proceso {proc}, la auditoría evidencia que {top[0]} Además, {top[1]}"
        return f"Para el proceso {proc}, la auditoría evidencia que {top[0]} Además, {top[1]} Finalmente, {top[2]}"

    proc_names = [str(p) for p in processes if str(p).strip()]
    proc_norm_map = {_norm_text(p): p for p in proc_names}
    collected: dict[tuple[str, str], dict] = {}

    for pdf_path in pdf_files:
        try:
            reader = PdfReader(str(pdf_path))
        except Exception:
            continue

        for page_num, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""

            text = re.sub(r"\s+", " ", str(text or "")).strip()
            text_norm = _norm_text(text)
            if not text_norm or len(text_norm) < 30:
                continue

            sentences = _split_sentences(text)
            if not sentences:
                continue

            for proc_norm, proc_name in proc_norm_map.items():
                if proc_norm not in text_norm:
                    continue

                matched_fragments = []
                for idx, sent in enumerate(sentences):
                    sent_norm = _norm_text(sent)
                    if proc_norm in sent_norm:
                        window = sentences[max(0, idx - 1): min(len(sentences), idx + 2)]
                        for frag in window:
                            frag_norm = _norm_text(frag)
                            if _contains_indicator_context(frag_norm) or proc_norm in frag_norm:
                                matched_fragments.append(frag)

                if not matched_fragments:
                    # fallback breve si aparece el proceso pero no contexto explícito de indicador
                    fallback = [s for s in sentences if proc_norm in _norm_text(s)][:2]
                    matched_fragments = fallback

                if not matched_fragments:
                    continue

                key = (proc_name, pdf_path.name)
                if key not in collected:
                    collected[key] = {
                        "Proceso": proc_name,
                        "Fuente": pdf_path.name,
                        "Paginas": set(),
                        "Fragmentos": [],
                        "Terminos": set(),
                    }

                collected[key]["Paginas"].add(page_num)
                collected[key]["Fragmentos"].extend(matched_fragments)
                for frag in matched_fragments:
                    collected[key]["Terminos"].update(_extract_detected_terms(_norm_text(frag)))

    if not collected:
        return pd.DataFrame(), "No se encontraron menciones directas de procesos en los PDFs de auditoría."

    rows = []
    for (proc_name, source_name), payload in collected.items():
        paginas = sorted(list(payload["Paginas"]))
        fragments = payload["Fragmentos"]
        summary = _redact_summary(proc_name, fragments)
        rows.append(
            {
                "Proceso": proc_name,
                "Fuente": source_name,
                "Coincidencias": len(fragments),
                "Paginas": ", ".join(str(p) for p in paginas),
                "Resumen IA": summary,
            }
        )

    resumen = pd.DataFrame(rows).sort_values(["Proceso", "Fuente"]).reset_index(drop=True)
    return resumen, None


def _build_info_table(df_latest: pd.DataFrame) -> pd.DataFrame:
    base_cols = [
        c
        for c in [
            "Indicador", "Meta", "Ejecucion", "Meta_Signo", "Meta s", "MetaS", "Ejecucion_Signo", "Ejecución s", "Ejecucion s", "EjecS",
            "Decimales", "Decimales_Meta", "Decimales_Ejecucion", "DecimalesEje", "DecMeta", "DecEjec",
        ]
        if c in df_latest.columns
    ]
    out = df_latest[base_cols].copy() if base_cols else pd.DataFrame(index=df_latest.index)
    if "Indicador" not in out.columns:
        out["Indicador"] = ""
    if "Meta" not in out.columns:
        out["Meta"] = pd.NA
    if "Ejecucion" not in out.columns:
        out["Ejecucion"] = pd.NA
    out = formatear_meta_ejecucion_df(out, meta_col="Meta", ejec_col="Ejecucion")
    out = out.rename(columns={"Ejecucion": "Ejecución"})
    out["Cumplimiento"] = df_latest.get("Cumplimiento_pct", pd.NA).apply(_cumpl_label)
    return out[[c for c in ["Indicador", "Meta", "Ejecución", "Cumplimiento"] if c in out.columns]]


def _build_indicadores_table(df_latest: pd.DataFrame) -> pd.DataFrame:
    base_cols = [
        c
        for c in [
            "Subproceso_final", "Indicador", "Meta", "Ejecucion", "Meta_Signo", "Meta s", "MetaS", "Ejecucion_Signo", "Ejecución s", "Ejecucion s", "EjecS",
            "Decimales", "Decimales_Meta", "Decimales_Ejecucion", "DecimalesEje", "DecMeta", "DecEjec",
        ]
        if c in df_latest.columns
    ]
    out = df_latest[base_cols].copy() if base_cols else pd.DataFrame(index=df_latest.index)
    out["Subproceso - Indicador"] = (
        out.get("Subproceso_final", pd.Series(["Sin subproceso"] * len(out), index=out.index)).astype(str)
        + " - "
        + out.get("Indicador", pd.Series([""] * len(out), index=out.index)).astype(str)
    )
    if "Meta" not in out.columns:
        out["Meta"] = pd.NA
    if "Ejecucion" not in out.columns:
        out["Ejecucion"] = pd.NA
    out = formatear_meta_ejecucion_df(out, meta_col="Meta", ejec_col="Ejecucion")
    out = out.rename(columns={"Ejecucion": "Ejecución"})
    out["Cumplimiento"] = df_latest.get("Cumplimiento_pct", pd.NA).apply(_cumpl_label)
    return out[[c for c in ["Subproceso - Indicador", "Meta", "Ejecución", "Cumplimiento"] if c in out.columns]]


def _build_propuestos(df_latest: pd.DataFrame, process_name: str) -> pd.DataFrame:
    if df_latest.empty:
        return pd.DataFrame(
            [
                {
                    "Proceso": process_name,
                    "Plan de mejoramiento": "Sin datos para priorizar acciones.",
                    "PDI 2026-2030": "Definir metas e hitos por indicador.",
                    "SGA": "Validar integración de evidencias y trazabilidad.",
                    "Retos": "Completar reporte de indicadores faltantes.",
                }
            ]
        )

    work = df_latest.copy()
    work["Cumplimiento_pct"] = pd.to_numeric(work["Cumplimiento_pct"], errors="coerce")
    riesgos = work[work["Cumplimiento_pct"].notna() & (work["Cumplimiento_pct"] < 80)]
    top_riesgos = riesgos.nsmallest(3, "Cumplimiento_pct") if not riesgos.empty else pd.DataFrame()

    riesgo_names = ", ".join(top_riesgos.get("Indicador", pd.Series(dtype=str)).astype(str).tolist())
    if not riesgo_names:
        riesgo_names = "Ninguno crítico en el corte"

    return pd.DataFrame(
        [
            {
                "Proceso": process_name,
                "Plan de mejoramiento": f"Priorizar cierre de brechas en: {riesgo_names}.",
                "PDI 2026-2030": "Alinear metas por resultados históricos y capacidad operativa.",
                "SGA": "Fortalecer controles de calidad de dato y consistencia de soportes.",
                "Retos": "Sostener cumplimiento mensual y reducir dispersión entre subprocesos.",
            }
        ]
    )


def render() -> None:
    st.title("Resumen por procesos")

    ds = DataService()
    tracking_df = ds.get_tracking_data()
    map_df = ds.get_process_map()

    if tracking_df.empty:
        st.warning("No se encontró data de seguimiento en data/output/Seguimiento_Reporte.xlsx.")
        return
    if map_df.empty:
        st.warning("No se encontró el mapeo de procesos en data/raw/Subproceso-Proceso-Area.xlsx.")
        return

    years = sorted([int(y) for y in pd.to_numeric(tracking_df.get("Año"), errors="coerce").dropna().unique().tolist()])
    default_month_num = _default_month_num(tracking_df)
    default_month = MESES_OPCIONES[default_month_num - 1]
    full_work_df = _prepare_tracking(tracking_df, map_df, month_num=None)
    snapshot_df = _prepare_tracking(tracking_df, map_df, month_num=default_month_num)
    procesos_all = sorted(full_work_df["Proceso_padre"].dropna().astype(str).unique().tolist())

    st.markdown("#### Filtros")
    c1, c2, c3 = st.columns(3)
    with c1:
        default_year = 2025 if 2025 in years else (years[-1] if years else None)
        default_year_idx = years.index(default_year) if default_year in years else 0
        anio = st.selectbox("Año", options=years, index=default_year_idx if years else None)
    with c2:
        mes = st.selectbox("Mes", options=MESES_OPCIONES, index=MESES_OPCIONES.index(default_month))
    with c3:
        proceso_placeholder = st.empty()

    # Recalcular datos del corte según mes seleccionado para que Meta/Ejecución/Cumplimiento respondan al filtro
    selected_month_num = MESES_OPCIONES.index(mes) + 1 if mes in MESES_OPCIONES else default_month_num
    snapshot_df = _prepare_tracking(tracking_df, map_df, month_num=selected_month_num)
    base_filtered = snapshot_df.copy()

    if anio is not None and "Año" in base_filtered.columns:
        base_filtered = base_filtered[pd.to_numeric(base_filtered["Año"], errors="coerce") == int(anio)]

    if mes and "Mes" in base_filtered.columns:
        mes_num = MESES_OPCIONES.index(mes) + 1
        base_filtered = base_filtered[base_filtered["Mes"].apply(_mes_to_num) == float(mes_num)]

    procesos_filtrados = sorted(base_filtered["Proceso_padre"].dropna().astype(str).unique().tolist())
    opciones_proceso = ["Todos"] + (procesos_filtrados if procesos_filtrados else procesos_all)
    default_index = 1 if len(opciones_proceso) > 1 else 0

    proceso_sel = proceso_placeholder.selectbox("Proceso (Filtro Padre)", options=opciones_proceso, index=default_index)

    filtered = base_filtered.copy()
    if proceso_sel != "Todos":
        filtered = filtered[filtered["Proceso_padre"].astype(str) == proceso_sel]

    subproceso_sel = "Todos"
    if proceso_sel != "Todos":
        subprocesos_filtrados = sorted(filtered["Subproceso_final"].dropna().astype(str).unique().tolist())
        if subprocesos_filtrados:
            sub_options = ["Todos"] + subprocesos_filtrados
            subproceso_sel = st.selectbox("Subproceso", options=sub_options, index=0)
            if subproceso_sel != "Todos":
                filtered = filtered[filtered["Subproceso_final"].astype(str) == subproceso_sel]

    if filtered.empty:
        st.info("No hay datos para la combinación de filtros seleccionada. Se muestran las pestañas en modo informativo.")

    latest = _latest_per_indicator(filtered) if not filtered.empty else filtered.copy()
    selected_process_label = proceso_sel if proceso_sel != "Todos" else "Todos los procesos"
    selected_subprocess_label = subproceso_sel if subproceso_sel != "Todos" else "Todos los subprocesos"

    historic_base = full_work_df.copy()
    if anio is not None and "Año" in historic_base.columns:
        historic_base = historic_base[pd.to_numeric(historic_base["Año"], errors="coerce") == int(anio)]
    if proceso_sel != "Todos":
        historic_base = historic_base[historic_base["Proceso_padre"].astype(str) == proceso_sel]
    if subproceso_sel != "Todos":
        historic_base = historic_base[historic_base["Subproceso_final"].astype(str) == subproceso_sel]

    st.caption(f"Filtro Padre activo: {selected_process_label} | Subproceso: {selected_subprocess_label} | Corte: {mes} {anio}")

    tabs = st.tabs([
        "📋 Resumen general",
        "ℹ️ Información por proceso",
        "📊 Indicadores",
        "📈 Evolución",
        "✅ Calidad",
        "🔍 Auditoría",
        "💡 Propuestos",
        "🤖 Análisis IA",
    ])

    with tabs[0]:
        st.markdown("### Resumen general - Gráficas importantes")

        if latest.empty:
            st.warning("No hay datos para construir gráficas con el filtro actual.")
        else:
            total = len(latest)
            cumplimiento = pd.to_numeric(latest.get("Cumplimiento_pct"), errors="coerce")
            avg = float(cumplimiento.mean()) if not cumplimiento.dropna().empty else None
            criticos = int((cumplimiento < 80).sum()) if not cumplimiento.dropna().empty else 0

            k1, k2, k3 = st.columns(3)
            k1.metric("Total indicadores", total)
            k2.metric("Cumplimiento promedio", f"{avg:.1f}%" if avg is not None else "Sin dato")
            k3.metric("Indicadores en alerta/peligro", criticos)

            col_a, col_b = st.columns(2)
            with col_a:
                bins_df = pd.DataFrame({"Nivel": "Sin dato"}, index=latest.index)
                bins_df.loc[cumplimiento >= 105, "Nivel"] = "Sobrecumplimiento"
                bins_df.loc[(cumplimiento >= 100) & (cumplimiento < 105), "Nivel"] = "Cumplimiento"
                bins_df.loc[(cumplimiento >= 80) & (cumplimiento < 100), "Nivel"] = "Alerta"
                bins_df.loc[cumplimiento < 80, "Nivel"] = "Peligro"

                pie_df = bins_df["Nivel"].value_counts().rename_axis("Nivel").reset_index(name="Total")
                fig_pie = px.pie(
                    pie_df,
                    names="Nivel",
                    values="Total",
                    color="Nivel",
                    color_discrete_map={
                        "Sobrecumplimiento": NIVELES_COLORS["sobrecumplimiento"],
                        "Cumplimiento": NIVELES_COLORS["cumplimiento"],
                        "Alerta": NIVELES_COLORS["alerta"],
                        "Peligro": NIVELES_COLORS["peligro"],
                        "Sin dato": NIVELES_COLORS["sin dato"],
                    },
                    title="Distribución de cumplimiento",
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_b:
                by_sub = (
                    latest.groupby("Subproceso_final", dropna=False)
                    .size()
                    .reset_index(name="Indicadores")
                    .sort_values("Indicadores", ascending=False)
                    .head(15)
                )
                fig_bar = px.bar(
                    by_sub,
                    x="Indicadores",
                    y="Subproceso_final",
                    orientation="h",
                    title="Top subprocesos por número de indicadores",
                )
                st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[1]:
        st.markdown("### Información por proceso")
        info_df = _build_info_table(latest)
        if info_df.empty:
            st.info("Sin información para el filtro actual.")
        else:
            st.dataframe(info_df, use_container_width=True, hide_index=True)

    with tabs[2]:
        st.markdown("### Indicadores")
        ind_df = _build_indicadores_table(latest)
        if ind_df.empty:
            st.info("Sin indicadores para el filtro actual.")
        else:
            st.dataframe(ind_df, use_container_width=True, hide_index=True)

    with tabs[3]:
        st.markdown("### Evolución de indicadores")
        if historic_base.empty:
            st.warning("No hay datos históricos para el filtro activo.")
        else:
            indicador_options = sorted(historic_base["Indicador"].dropna().astype(str).unique().tolist())
            if not indicador_options:
                st.info("No hay indicadores históricos disponibles para el filtro activo.")
            else:
                selected_indicator = st.selectbox("Indicador para evolución", options=indicador_options, index=0)
                if selected_indicator:
                    hist_df = _build_indicator_history(historic_base, selected_indicator)
                    if hist_df.empty:
                        st.info("No hay histórico disponible para el indicador seleccionado.")
                    else:
                        st.plotly_chart(
                            grafico_historico_indicador(hist_df, titulo=f"Evolución de {selected_indicator}"),
                            use_container_width=True,
                        )
                        hist_table = tabla_historica_indicador(hist_df)
                        if hist_table.empty:
                            st.info("No hay registros históricos con cumplimiento calculado.")
                        else:
                            st.markdown("#### Detalle histórico")
                            st.dataframe(hist_table, use_container_width=True, hide_index=True)

    with tabs[4]:
        st.markdown("### Calidad")
        calidad_df, calidad_msg = _load_calidad_data()
        if calidad_msg:
            st.warning(calidad_msg)
        else:
            if proceso_sel != "Todos":
                calidad_df = calidad_df[calidad_df["Proceso"].astype(str) == proceso_sel]
            st.dataframe(calidad_df, use_container_width=True, hide_index=True)

    with tabs[5]:
        st.markdown("### Auditoría")
        auditoria_df, auditoria_msg = _load_auditoria_mentions(procesos_all)
        if auditoria_msg:
            st.warning(auditoria_msg)
        else:
            if proceso_sel != "Todos":
                auditoria_df = auditoria_df[auditoria_df["Proceso"].astype(str) == proceso_sel]
            st.dataframe(auditoria_df, use_container_width=True, hide_index=True)

    with tabs[6]:
        st.markdown("### Propuestos")
        st.dataframe(_build_propuestos(latest, selected_process_label), use_container_width=True, hide_index=True)

    with tabs[7]:
        st.markdown("### Análisis IA")
        cumplimiento = pd.to_numeric(latest.get("Cumplimiento_pct"), errors="coerce")
        riesgos = latest[cumplimiento < 80]
        alertas = latest[(cumplimiento >= 80) & (cumplimiento < 100)]

        st.write(f"Se identifican {len(riesgos)} indicadores en peligro y {len(alertas)} en alerta para el filtro activo.")
        if not riesgos.empty:
            cols = [c for c in ["Indicador", "Subproceso_final", "Cumplimiento_pct"] if c in riesgos.columns]
            preview = riesgos[cols].copy().sort_values("Cumplimiento_pct", ascending=True).head(10)
            preview = preview.rename(columns={"Subproceso_final": "Subproceso", "Cumplimiento_pct": "Cumplimiento (%)"})
            st.dataframe(preview, use_container_width=True, hide_index=True)
        else:
            st.success("No hay indicadores en peligro para el corte seleccionado.")
