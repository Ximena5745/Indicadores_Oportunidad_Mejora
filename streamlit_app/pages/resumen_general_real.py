def calcular_cascada(df):
    # Nivel 4: Indicador (hoja)
    nivel4 = df.copy()
    nivel4["Nivel"] = 4
    nivel4["Total_Indicadores"] = 1
    nivel4 = nivel4[["Nivel", "Linea", "Objetivo", "Meta_PDI", "Indicador", "cumplimiento_pct", "Total_Indicadores"]]
    nivel4 = nivel4.rename(columns={"cumplimiento_pct": "Cumplimiento"})

    # Nivel 3: Meta_PDI
    nivel3 = (
        df.groupby(["Linea", "Objetivo", "Meta_PDI"], dropna=False)
        .agg(Cumplimiento=("cumplimiento_pct", "mean"), Total_Indicadores=("Indicador", "count"))
        .reset_index()
    )
    nivel3["Nivel"] = 3
    nivel3["Indicador"] = None
    nivel3 = nivel3[["Nivel", "Linea", "Objetivo", "Meta_PDI", "Indicador", "Cumplimiento", "Total_Indicadores"]]

    # Nivel 2: Objetivo
    nivel2 = (
        df.groupby(["Linea", "Objetivo"], dropna=False)
        .agg(Cumplimiento=("cumplimiento_pct", "mean"), Total_Indicadores=("Indicador", "count"))
        .reset_index()
    )
    nivel2["Nivel"] = 2
    nivel2["Meta_PDI"] = None
    nivel2["Indicador"] = None
    nivel2 = nivel2[["Nivel", "Linea", "Objetivo", "Meta_PDI", "Indicador", "Cumplimiento", "Total_Indicadores"]]

    # Nivel 1: Linea
    nivel1 = (
        df.groupby(["Linea"], dropna=False)
        .agg(Cumplimiento=("cumplimiento_pct", "mean"), Total_Indicadores=("Indicador", "count"))
        .reset_index()
    )
    nivel1["Nivel"] = 1
    nivel1["Objetivo"] = None
    nivel1["Meta_PDI"] = None
    nivel1["Indicador"] = None
    nivel1 = nivel1[["Nivel", "Linea", "Objetivo", "Meta_PDI", "Indicador", "Cumplimiento", "Total_Indicadores"]]

    # Unir todos los niveles
    cascada = pd.concat([nivel1, nivel2, nivel3, nivel4], ignore_index=True)
    return cascada
"""
pages/resumen_general_real.py — Resumen General con datos reales de Consolidado Cierres.

Fuente real: data/output/Resultados Consolidados.xlsx · hoja Consolidado Cierres
"""
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from streamlit_app.services.strategic_indicators import preparar_pdi_con_cierre
from scripts.plot_templates import waterfall_chart

DATA_ROOT = Path(__file__).resolve().parents[2]
PATH_CONSOLIDADO = DATA_ROOT / "data" / "output" / "Resultados Consolidados.xlsx"

LINEA_COLORS = {
    "Expansión": "#FBAF17",
    "Transformación organizacional": "#42F2F2",
    "Calidad": "#EC0677",
    "Experiencia": "#1FB2DE",
    "Sostenibilidad": "#A6CE38",
    "Educación para toda la vida": "#0F385A",
}

MES_MAP = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    # Normaliza la columna de cumplimiento
    if "Cumplimiento" in df.columns and "cumplimiento_pct" not in df.columns:
        df = df.rename(columns={"Cumplimiento": "cumplimiento_pct"})
    return df


def _parse_month(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except Exception:
            return None
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return MES_MAP.get(text.lower())


def _load_consolidado_cierres() -> pd.DataFrame:
    if not PATH_CONSOLIDADO.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(PATH_CONSOLIDADO, sheet_name="Consolidado Cierres", engine="openpyxl")
    except Exception:
        return pd.DataFrame()
    df = _normalize_columns(df)
    if "Ao" in df.columns:
        df["Ao"] = pd.to_numeric(df["Ao"], errors="coerce")
    elif "Anio" in df.columns:
        df["Ao"] = pd.to_numeric(df["Anio"], errors="coerce")
    else:
        df["Ao"] = pd.NA

    if "Mes" in df.columns:
        df["Mes_num"] = df["Mes"].apply(_parse_month)
    else:
        df["Mes_num"] = None

    # Si existe "Cumplimiento" y no "cumplimiento_pct", normaliza
    if "Cumplimiento" in df.columns and "cumplimiento_pct" not in df.columns:
        df = df.rename(columns={"Cumplimiento": "cumplimiento_pct"})

    df = _ensure_nivel_cumplimiento(df)
    return df


def _ensure_nivel_cumplimiento(df: pd.DataFrame) -> pd.DataFrame:
    if "Nivel de cumplimiento" in df.columns:
        return df
    if "Categoria" in df.columns:
        df["Nivel de cumplimiento"] = df["Categoria"]
        return df
    # Si existe "Cumplimiento" y no "cumplimiento_pct", normaliza
    if "Cumplimiento" in df.columns and "cumplimiento_pct" not in df.columns:
        df = df.rename(columns={"Cumplimiento": "cumplimiento_pct"})
    if "cumplimiento_pct" in df.columns:
        def _map_level(value):
            try:
                pct = float(value)
            except Exception:
                return "Pendiente de reporte"
            if pct >= 105:
                return "Sobrecumplimiento"
            if pct >= 100:
                return "Cumplimiento"
            if pct >= 80:
                return "Alerta"
            return "Peligro"
        df["Nivel de cumplimiento"] = df["cumplimiento_pct"].apply(_map_level)
        return df
    df["Nivel de cumplimiento"] = "Pendiente de reporte"
    return df


def _available_years(df: pd.DataFrame) -> list[int]:
    if df.empty or "Año" not in df.columns:
        return []
    years = pd.to_numeric(df["Año"], errors="coerce").dropna().astype(int).unique().tolist()
    allowed = [y for y in sorted(years) if y in {2022, 2023, 2024, 2025}]
    return allowed or sorted(years)


def _latest_month_for_year(df: pd.DataFrame, year: int) -> int | None:
    subset = df[df["Año"] == year].copy()
    if subset.empty or "Mes_num" not in subset.columns:
        return None
    months = pd.to_numeric(subset["Mes_num"], errors="coerce").dropna().astype(int)
    return int(months.max()) if not months.empty else None


def _build_sunburst(pdi_df: pd.DataFrame) -> go.Figure:
    df = pdi_df.copy()
    df["Linea"] = df["Linea"].fillna("Sin línea")
    df["Objetivo"] = df["Objetivo"].fillna("Sin objetivo")
    df = df[df["cumplimiento_pct"].notna()]

    # Si no hay datos válidos, crear un nodo dummy con 0%
    if df.empty:
        labels = ["Sin datos"]
        parents = [""]
        values = [1]
        customdata = [[0]]
        colors = ["#6B728E"]
        text = ["Sin datos\n0.0%"]
    else:
        # Nivel 1: Linea (promedio)
        lines = df.groupby("Linea", dropna=False).agg(cumplimiento_pct=("cumplimiento_pct", "mean")).reset_index()
        # Nivel 2: Objetivo (promedio)
        grouped = df.groupby(["Linea", "Objetivo"], dropna=False).agg(cumplimiento_pct=("cumplimiento_pct", "mean")).reset_index()

        labels = []
        parents = []
        values = []
        customdata = []
        colors = []

        # Use counts for sizing but show cumplimiento_pct as text inside sectors
        line_counts = df.groupby('Linea').size().to_dict()
        obj_counts = df.groupby(['Linea', 'Objetivo']).size().to_dict()

        for _, line in lines.iterrows():
            linea_name = line["Linea"]
            labels.append(linea_name)
            parents.append("")
            values.append(int(line_counts.get(linea_name, 0)) or 1)
            customdata.append([line["cumplimiento_pct"] if pd.notna(line["cumplimiento_pct"]) else 0])
            colors.append(LINEA_COLORS.get(linea_name, "#6B728E"))

        for _, row in grouped.iterrows():
            obj_name = row["Objetivo"]
            parent_name = row["Linea"]
            labels.append(obj_name)
            parents.append(parent_name)
            values.append(int(obj_counts.get((parent_name, obj_name), 0)) or 1)
            customdata.append([row["cumplimiento_pct"] if pd.notna(row["cumplimiento_pct"]) else 0])
            colors.append(LINEA_COLORS.get(parent_name, "#6B728E"))

        # Wrap long labels to multiple lines so they fit inside sectors
        def wrap_label(s: str, width: int = 18) -> str:
            parts = []
            cur = []
            for word in str(s).split():
                if sum(len(w) for w in cur) + len(cur) + len(word) <= width:
                    cur.append(word)
                else:
                    parts.append(" ".join(cur))
                    cur = [word]
            if cur:
                parts.append(" ".join(cur))
            # center each line and join with newline
            return "\n".join(part.strip() for part in parts)

        # Build wrapped text lines; put percentage on its own centered line
        text = []
        for lab, cd, parent in zip(labels, customdata, parents):
            pct = (cd[0] if cd and cd[0] is not None else 0)
            wrapped = wrap_label(lab, width=18)
            # Show label + percentage only for inner ring (parents == ""); outer ring shows wrapped label only
            if parent == "":
                text.append(f"{wrapped}\n{pct:.1f}%")
            else:
                text.append(wrapped)

    # Split inner (Linea) and outer (Objetivo) for independent styling
    inner_idxs = [i for i, p in enumerate(parents) if p == ""]
    outer_idxs = [i for i, p in enumerate(parents) if p != ""]

    inner_labels = [labels[i] for i in inner_idxs]
    inner_values = [values[i] for i in inner_idxs]
    inner_colors = [colors[i] for i in inner_idxs]
    inner_custom = [customdata[i] for i in inner_idxs]
    inner_text = [text[i] for i in inner_idxs]

    outer_labels = [labels[i] for i in outer_idxs]
    outer_parents = [parents[i] for i in outer_idxs]
    outer_values = [values[i] for i in outer_idxs]
    outer_colors = [colors[i] for i in outer_idxs]
    outer_custom = [customdata[i] for i in outer_idxs]
    outer_text = [text[i] for i in outer_idxs]

    fig = go.Figure()
    # Outer ring: smaller white text
    fig.add_trace(go.Sunburst(
        labels=outer_labels,
        parents=outer_parents,
        values=outer_values,
        branchvalues="total",
        marker=dict(colors=outer_colors, line=dict(color="#ffffff", width=1)),
        customdata=outer_custom,
        text=outer_text,
        textinfo='text',
        insidetextorientation="radial",
        hovertemplate="<b>%{label}</b><br>Promedio cumplimiento: %{customdata[0]:.1f}%<extra></extra>",
        domain=dict(x=[0,1], y=[0,1]),
        maxdepth=2,
    ))

    # Inner ring: larger, colored percentage text
    fig.add_trace(go.Sunburst(
        labels=inner_labels,
        parents=["" for _ in inner_labels],
        values=inner_values,
        branchvalues="total",
        marker=dict(colors=inner_colors, line=dict(color="#ffffff", width=2)),
        customdata=inner_custom,
        text=inner_text,
        textinfo='text',
        insidetextorientation="radial",
        hovertemplate="<b>%{label}</b><br>Promedio cumplimiento: %{customdata[0]:.1f}%<extra></extra>",
        domain=dict(x=[0,1], y=[0,1]),
        maxdepth=1,
        insidetextfont=dict(size=16, color="#08306B", family='Arial')
    ))

    # Improve readability: set explicit templates for outer and inner sunburst traces
    try:
        # Outer trace (labels)
        if len(fig.data) >= 1 and getattr(fig.data[0], 'type', None) == 'sunburst':
            fig.data[0].update(
                uniformtext=dict(minsize=9, mode='hide'),
                textfont=dict(family='Arial', size=11, color='#0b1946'),
                insidetextfont=dict(family='Arial', size=11, color='white'),
                texttemplate='%{text}',
                hovertemplate="<b>%{label}</b><br>Promedio cumplimiento: %{customdata[0]:.1f}%<extra></extra>"
            )

        # Inner trace (percentages) — más grande y con otro tono
        if len(fig.data) >= 2 and getattr(fig.data[1], 'type', None) == 'sunburst':
            fig.data[1].update(
                uniformtext=dict(minsize=12, mode='hide'),
                textfont=dict(family='Arial', size=14, color='#08306B'),
                insidetextfont=dict(family='Arial', size=18, color='#08306B'),
                texttemplate='%{customdata[0]:.1f}%',
                hovertemplate="<b>%{label}</b><br>Promedio cumplimiento: %{customdata[0]:.1f}%<extra></extra>"
            )
    except Exception:
        # no queremos romper la renderización por problemas de versionado de plotly
        pass

    # As a final safety, ensure any remaining sunburst traces get a minimal uniformtext update
    for trace in fig.data:
        try:
            if getattr(trace, 'type', None) == 'sunburst' and not getattr(trace, 'uniformtext', None):
                trace.update(uniformtext=dict(minsize=9, mode='hide'))
        except Exception:
            pass

    fig.update_layout(margin=dict(t=20, l=0, r=0, b=0), height=720)
    return fig


def _compute_trends(current: pd.DataFrame, previous: pd.DataFrame):
    if current.empty or previous.empty:
        return [], []
    cur = current[["Id", "Indicador", "cumplimiento_pct"]].dropna(subset=["cumplimiento_pct"]).copy()
    prev = previous[["Id", "cumplimiento_pct"]].dropna(subset=["cumplimiento_pct"]).copy()
    merged = cur.merge(prev, on="Id", suffixes=("", "_prev"))
    if merged.empty:
        return [], []
    merged["variation"] = merged["cumplimiento_pct"] - merged["cumplimiento_pct_prev"]
    best = merged.sort_values("variation", ascending=False).head(3)
    worst = merged.sort_values("variation").head(3)
    return (
        [{"name": str(row["Indicador"]), "change": float(row["variation"])} for _, row in best.iterrows()],
        [{"name": str(row["Indicador"]), "change": float(row["variation"])} for _, row in worst.iterrows()],
    )


def _find_process_column(df: pd.DataFrame) -> str | None:
    for col in ["Proceso", "Subproceso", "ProcesoPadre", "Proceso Padre"]:
        if col in df.columns:
            return col
    return None


def _process_counts(df: pd.DataFrame, process_col: str) -> pd.DataFrame:
    levels = ["Sobrecumplimiento", "Cumplimiento", "Alerta", "Peligro"]
    df = df.copy()
    if "Nivel de cumplimiento" not in df.columns:
        df = _ensure_nivel_cumplimiento(df)
    df["Nivel de cumplimiento"] = df["Nivel de cumplimiento"].fillna("Pendiente de reporte")
    group_col = "Id" if "Id" in df.columns else process_col
    pivot = (
        df[df["Nivel de cumplimiento"].isin(levels)]
          .groupby([process_col, "Nivel de cumplimiento"])[group_col]
          .nunique()
          .reset_index(name="count")
          .pivot(index=process_col, columns="Nivel de cumplimiento", values="count")
          .fillna(0)
    )
    for lvl in levels:
        if lvl not in pivot.columns:
            pivot[lvl] = 0
    return pivot.reset_index()


def _process_improvements(current: pd.DataFrame, previous: pd.DataFrame, process_col: str):
    if current.empty or previous.empty or process_col not in current.columns or process_col not in previous.columns:
        return [], []
    current = current[current["cumplimiento_pct"].notna()]
    previous = previous[previous["cumplimiento_pct"].notna()]
    curr_avg = current.groupby(process_col)["cumplimiento_pct"].mean().reset_index(name="current_avg")
    prev_avg = previous.groupby(process_col)["cumplimiento_pct"].mean().reset_index(name="previous_avg")
    merged = curr_avg.merge(prev_avg, on=process_col, how="inner")
    if merged.empty:
        return [], []
    merged["delta"] = merged["current_avg"] - merged["previous_avg"]
    top = merged.sort_values("delta", ascending=False).head(3)
    alerts = merged[(merged["current_avg"] >= 50) & (merged["current_avg"] < 80) & (merged["delta"] < 0)]
    alerts = alerts.sort_values("delta").head(3)
    return (
        [{"name": str(row[process_col]), "change": float(row["delta"])} for _, row in top.iterrows()],
        [{"name": str(row[process_col]), "change": float(row["delta"])} for _, row in alerts.iterrows()],
    )


def _format_insights(items: list[dict], positive: bool = True):
    if not items:
        return []
    if positive:
        return [f"- **{item['name']}** mejora +{item['change']:.1f}% respecto al año anterior." for item in items]
    return [f"- **{item['name']}** empeora {item['change']:.1f}% respecto al año anterior." for item in items]


def render():
    st.title("Resumen general")
    st.markdown("#### Fuente real: Consolidado Cierres — Resultados Consolidados.xlsx")
    consolidado = _load_consolidado_cierres()
    if consolidado.empty:
        st.error("No se pudo cargar la hoja 'Consolidado Cierres' desde data/output/Resultados Consolidados.xlsx.")
        return

    years = _available_years(consolidado)
    if not years:
        st.error("No se encontraron años válidos en los datos.")
        return

    selected_year = st.selectbox("Año de análisis", years, index=len(years)-1)
    selected_month = _latest_month_for_year(consolidado, selected_year)
    month_label = selected_month if selected_month else "último disponible"
    st.caption(f"Corte seleccionado: {selected_year} — Mes {month_label}")

    pdi_df = preparar_pdi_con_cierre(selected_year, selected_month if selected_month else 12)
    # Aplicar filtros explícitos de año/mes a las visualizaciones
    if not pdi_df.empty:
        if 'Anio' in pdi_df.columns:
            pdi_df['Anio'] = pd.to_numeric(pdi_df['Anio'], errors='coerce')
            pdi_df = pdi_df[pdi_df['Anio'] == int(selected_year)]
        if selected_month and 'Mes' in pdi_df.columns:
            pdi_df['Mes'] = pd.to_numeric(pdi_df['Mes'], errors='coerce')
            pdi_df = pdi_df[pdi_df['Mes'] == int(selected_month)]
    st.caption(f"Filtros aplicados: Año={selected_year}, Mes={selected_month if selected_month else 'último disponible'}")
    if pdi_df.empty:
        st.warning("No hay indicadores PDI disponibles para el año seleccionado.")
        return

    pdi_df["Nivel de cumplimiento"] = pdi_df["Nivel de cumplimiento"].fillna("Pendiente de reporte")
    count_total = len(pdi_df)
    counts = {
        "Sobrecumplimiento": int((pdi_df["Nivel de cumplimiento"] == "Sobrecumplimiento").sum()),
        "Cumplimiento": int((pdi_df["Nivel de cumplimiento"] == "Cumplimiento").sum()),
        "Alerta": int((pdi_df["Nivel de cumplimiento"] == "Alerta").sum()),
        "Peligro": int((pdi_df["Nivel de cumplimiento"] == "Peligro").sum()),
    }

    prev_year = selected_year - 1
    prev_month = _latest_month_for_year(consolidado, prev_year)
    prev_pdi_df = preparar_pdi_con_cierre(prev_year, prev_month if prev_month else 12) if prev_month else pd.DataFrame()

    best_improvements, worst_declines = _compute_trends(pdi_df, prev_pdi_df)
    # --- Nueva lógica de cascada ---
    # Asegura que existan las columnas requeridas
    for col in ["Linea", "Objetivo", "Meta_PDI", "Indicador"]:
        if col not in pdi_df.columns:
            pdi_df[col] = None
    cascada_df = calcular_cascada(pdi_df)
    # Puedes mostrar la tabla para depuración:
    # st.dataframe(cascada_df)
    # Construir cascada: usar Nivel 1 (Linea) promedio de Cumplimiento cuando exista
    # Asegurar columna numérica
    cascada_df['Cumplimiento'] = pd.to_numeric(cascada_df.get('Cumplimiento'), errors='coerce')
    nivel1 = cascada_df[cascada_df['Nivel'] == 1].copy()
    nivel1 = nivel1[nivel1['Cumplimiento'].notna()]
    if not nivel1.empty:
        # ordenar para estabilizar visualización
        nivel1 = nivel1.sort_values('Cumplimiento', ascending=False)
        fig_cascada = waterfall_chart(nivel1, x='Linea', y='Cumplimiento', color_map=LINEA_COLORS, title='Cascada: Promedio cumplimiento por Línea')
        st.plotly_chart(fig_cascada, use_container_width=True)
    else:
        # intentar con indicadores (Nivel 4) si no hay promedios por Línea
        nivel4 = cascada_df[cascada_df['Nivel'] == 4].copy()
        nivel4['Cumplimiento'] = pd.to_numeric(nivel4.get('Cumplimiento'), errors='coerce')
        nivel4 = nivel4[nivel4['Cumplimiento'].notna()]
        if not nivel4.empty:
            top4 = nivel4.sort_values('Cumplimiento', ascending=False).head(20)
            fig_cascada = waterfall_chart(top4, x='Indicador', y='Cumplimiento', title='Cascada: Top 20 Indicadores por Cumplimiento')
            st.plotly_chart(fig_cascada, use_container_width=True)
        else:
            st.info("No hay datos numéricos de cumplimiento disponibles para construir la cascada.")

    # Mantener el sunburst como referencia visual
    sunburst = _build_sunburst(pdi_df)
    st.plotly_chart(sunburst, use_container_width=True)

    kpi_cols = st.columns(5)
    colors = ["#0B5FFF", "#1A3A5C", "#43A047", "#FBAF17", "#D32F2F"]
    values = [count_total, counts["Sobrecumplimiento"], counts["Cumplimiento"], counts["Alerta"], counts["Peligro"]]
    labels = ["Total indicadores PDI", "Sobrecumplimiento", "Cumplimiento", "Alerta", "Peligro"]
    for col, label, value, color in zip(kpi_cols, labels, values, colors):
        with col:
            st.markdown(
                f"<div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:18px;text-align:center;'>"
                f"<div style='font-size:30px;font-weight:800;color:{color};'>{value}</div>"
                f"<div style='font-size:12px;color:#64748B;letter-spacing:0.08em;margin-top:8px;'>{label}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("### Indicadores con Mayor Mejora vs Histórico")
    if best_improvements:
        for item in best_improvements:
            st.markdown(f"- {item['name']} — +{item['change']:.1f}%")
    else:
        st.markdown("- No hay comparativas disponibles contra el año anterior.")

    st.markdown("### Indicadores con Mayor Desmejora vs Histórico")
    if worst_declines:
        for item in worst_declines:
            st.markdown(f"- {item['name']} — {item['change']:.1f}%")
    else:
        st.markdown("- No hay comparativas disponibles contra el año anterior.")

    st.markdown("### Insights Estratégicos (IA)")
    best_line = pdi_df.groupby("Linea").agg(cumplimiento_pct=("cumplimiento_pct", "mean")).reset_index()
    best_line = best_line.sort_values("cumplimiento_pct", ascending=False).head(1)
    line_name = str(best_line.iloc[0]["Linea"]) if not best_line.empty else ""
    line_avg = float(best_line.iloc[0]["cumplimiento_pct"]) if not best_line.empty else 0
    health_rate = round(((counts["Sobrecumplimiento"] + counts["Cumplimiento"]) / max(count_total, 1)) * 100, 1)
    insights = []
    if health_rate >= 70:
        insights.append(f"✅ El {health_rate}% de los indicadores PDI están en niveles saludables.")
    elif health_rate >= 50:
        insights.append(f"⚠️ El {health_rate}% de los indicadores PDI están en cumplimiento, con riesgo en algunos objetivos.")
    else:
        insights.append(f"🚨 Solo el {health_rate}% de los indicadores PDI cumplen expectativas; se requiere acción prioritaria.")
    if line_name:
        insights.append(f"🌟 La línea \"{line_name}\" lidera con {line_avg:.1f}% de cumplimiento promedio.")
    if best_improvements:
        insights.append(f"📈 Mejora destacada: \"{best_improvements[0]['name']}\" (+{best_improvements[0]['change']:.1f}%).")
    if worst_declines:
        insights.append(f"📉 Atención a \"{worst_declines[0]['name']}\" ({worst_declines[0]['change']:.1f}%).")
    for insight in insights:
        st.markdown(f"- {insight}")

    st.markdown("---")
    st.subheader("Indicadores por Proceso")
    process_col = _find_process_column(consolidado)
    if not process_col:
        st.warning("No se encontró columna de proceso en los datos reales.")
        return
    process_data = consolidado[consolidado["Año"] == selected_year].copy()
    if selected_month:
        process_data = process_data[process_data["Mes_num"] == selected_month]
    if process_data.empty:
        st.warning("No hay datos por proceso para el año seleccionado.")
        return

    total_process = int(process_data["Id"].nunique()) if "Id" in process_data.columns else len(process_data)
    st.markdown(f"**Total indicadores por proceso:** {total_process}")
    proc_counts = _process_counts(process_data, process_col)
    if not proc_counts.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Sobrecumplimiento', x=proc_counts[process_col], y=proc_counts['Sobrecumplimiento'], marker_color='#1A3A5C'))
        fig.add_trace(go.Bar(name='Cumplimiento', x=proc_counts[process_col], y=proc_counts['Cumplimiento'], marker_color='#43A047'))
        fig.add_trace(go.Bar(name='Alerta', x=proc_counts[process_col], y=proc_counts['Alerta'], marker_color='#FBAF17'))
        fig.add_trace(go.Bar(name='Peligro', x=proc_counts[process_col], y=proc_counts['Peligro'], marker_color='#D32F2F'))
        fig.update_layout(barmode='stack', xaxis_tickangle=-45, height=480, margin=dict(t=40, b=150))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay información de niveles de cumplimiento por proceso en el período seleccionado.")

    previous_process_data = consolidado[consolidado["Año"] == prev_year].copy()
    if selected_month:
        previous_process_data = previous_process_data[previous_process_data["Mes_num"] == prev_month]
    process_top, process_alert = _process_improvements(process_data, previous_process_data, process_col)

    st.markdown("### Procesos con Mayor Mejora vs Año Anterior")
    if process_top:
        for item in process_top:
            st.markdown(f"- **{item['name']}** — +{item['change']:.1f}%")
    else:
        st.markdown("- No hay comparación de procesos con el año anterior.")

    st.markdown("### Procesos en Alerta con Empeoramiento")
    if process_alert:
        for item in process_alert:
            st.markdown(f"- **{item['name']}** — {item['change']:.1f}%")
    else:
        st.markdown("- No se detectaron procesos en alerta con empeoramiento.")

    health_process = proc_counts[['Sobrecumplimiento', 'Cumplimiento']].sum(axis=1).sum()
    health_pct = round(health_process / max(total_process, 1) * 100, 1)
    st.markdown("### Insights Operativos (IA)")
    if process_top:
        st.markdown(f"- 🚀 {process_top[0]['name']} registra la mayor mejora respecto al año anterior.")
    if process_alert:
        st.markdown(f"- ⚠️ {process_alert[0]['name']} está en alerta y empeoró respecto al año anterior.")
    st.markdown(f"- ✅ El {health_pct}% de los indicadores por proceso están en niveles saludables.")
