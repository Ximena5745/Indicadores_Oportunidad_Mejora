from pathlib import Path
import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from ..services.data_service import DataService
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.data_service import DataService


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


def _cumplimiento_pct(df: pd.DataFrame) -> pd.Series:
    if "Cumplimiento_norm" in df.columns:
        vals = pd.to_numeric(df["Cumplimiento_norm"], errors="coerce")
        return vals * 100

    if "Cumplimiento" in df.columns:
        vals = pd.to_numeric(df["Cumplimiento"].apply(_to_float), errors="coerce")
        max_abs = vals.abs().max(skipna=True) if not vals.dropna().empty else 0
        return vals * 100 if max_abs <= 2 else vals

    return pd.Series(index=df.index, dtype="float64")


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


def _prepare_tracking(df: pd.DataFrame, map_df: pd.DataFrame) -> pd.DataFrame:
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

    try:
        from pypdf import PdfReader
    except Exception:
        return pd.DataFrame(), "No está instalado pypdf. Instala la dependencia para extraer texto de auditoría."

    if not processes:
        return pd.DataFrame(), "No hay procesos disponibles para buscar en los PDFs."

    rows = []
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

            text_norm = _norm_text(text)
            if not text_norm:
                continue

            for proc in processes:
                proc_norm = _norm_text(proc)
                if proc_norm and proc_norm in text_norm:
                    idx = text_norm.find(proc_norm)
                    start = max(0, idx - 120)
                    end = min(len(text_norm), idx + len(proc_norm) + 180)
                    snippet = re.sub(r"\s+", " ", text_norm[start:end]).strip()
                    rows.append(
                        {
                            "Proceso": proc,
                            "Fuente": pdf_path.name,
                            "Página": page_num,
                            "Evidencia IA": snippet[:240],
                        }
                    )

    if not rows:
        return pd.DataFrame(), "No se encontraron menciones directas de procesos en los PDFs de auditoría."

    mentions = pd.DataFrame(rows)
    resumen = (
        mentions.groupby(["Proceso", "Fuente"], dropna=False)
        .agg(
            Coincidencias=("Página", "count"),
            Primera_pagina=("Página", "min"),
            Evidencia_IA=("Evidencia IA", "first"),
        )
        .reset_index()
        .rename(columns={"Evidencia_IA": "Evidencia IA", "Primera_pagina": "Página inicial"})
    )
    return resumen, None


def _build_info_table(df_latest: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["Indicador"] = df_latest.get("Indicador", "")
    out["Meta"] = df_latest.get("Meta", pd.NA)
    out["Ejecución"] = df_latest.get("Ejecucion", pd.NA)
    out["Cumplimiento"] = df_latest.get("Cumplimiento_pct", pd.NA).apply(_cumpl_label)
    return out


def _build_indicadores_table(df_latest: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["Subproceso - Indicador"] = (
        df_latest.get("Subproceso_final", "Sin subproceso").astype(str)
        + " - "
        + df_latest.get("Indicador", "").astype(str)
    )
    out["Meta"] = df_latest.get("Meta", pd.NA)
    out["Ejecución"] = df_latest.get("Ejecucion", pd.NA)
    out["Cumplimiento"] = df_latest.get("Cumplimiento_pct", pd.NA).apply(_cumpl_label)
    return out


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

    work_df = _prepare_tracking(tracking_df, map_df)

    years = sorted([int(y) for y in pd.to_numeric(work_df.get("Año"), errors="coerce").dropna().unique().tolist()])
    default_month = "Diciembre"
    procesos = sorted(work_df["Proceso_padre"].dropna().astype(str).unique().tolist())

    st.markdown("#### Filtros")
    c1, c2, c3 = st.columns(3)
    with c1:
        anio = st.selectbox("Año", options=years, index=len(years) - 1 if years else None)
    with c2:
        mes = st.selectbox("Mes", options=MESES_OPCIONES, index=MESES_OPCIONES.index(default_month))
    with c3:
        proceso_sel = st.selectbox("Proceso (Filtro Padre)", options=["Todos"] + procesos)

    filtered = work_df.copy()

    if anio is not None and "Año" in filtered.columns:
        filtered = filtered[pd.to_numeric(filtered["Año"], errors="coerce") == int(anio)]

    if mes and "Mes" in filtered.columns:
        mes_num = MESES_OPCIONES.index(mes) + 1
        filtered = filtered[pd.to_numeric(filtered["Mes"], errors="coerce") == mes_num]

    if proceso_sel != "Todos":
        filtered = filtered[filtered["Proceso_padre"].astype(str) == proceso_sel]

    if filtered.empty:
        st.info("No hay datos para la combinación de filtros seleccionada. Se muestran las pestañas en modo informativo.")

    latest = _latest_per_indicator(filtered) if not filtered.empty else filtered.copy()
    selected_process_label = proceso_sel if proceso_sel != "Todos" else "Todos los procesos"

    st.caption(f"Filtro Padre activo: {selected_process_label} | Corte: {mes} {anio}")

    tabs = st.tabs([
        "📋 Resumen general",
        "ℹ️ Información por proceso",
        "📊 Indicadores",
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
        st.markdown("### Calidad")
        calidad_df, calidad_msg = _load_calidad_data()
        if calidad_msg:
            st.warning(calidad_msg)
        else:
            if proceso_sel != "Todos":
                calidad_df = calidad_df[calidad_df["Proceso"].astype(str) == proceso_sel]
            st.dataframe(calidad_df, use_container_width=True, hide_index=True)

    with tabs[4]:
        st.markdown("### Auditoría")
        auditoria_df, auditoria_msg = _load_auditoria_mentions(procesos)
        if auditoria_msg:
            st.warning(auditoria_msg)
        else:
            if proceso_sel != "Todos":
                auditoria_df = auditoria_df[auditoria_df["Proceso"].astype(str) == proceso_sel]
            st.dataframe(auditoria_df, use_container_width=True, hide_index=True)

    with tabs[5]:
        st.markdown("### Propuestos")
        st.dataframe(_build_propuestos(latest, selected_process_label), use_container_width=True, hide_index=True)

    with tabs[6]:
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
