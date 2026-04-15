"""
Resumen General - Diseño Visual Completo
Dashboard ejecutivo con tarjetas visuales, sparklines, perspectivas IA y gráficos interactivos
"""
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

try:
    from services.strategic_indicators import preparar_pdi_con_cierre, load_pdi_catalog
    import services.strategic_indicators as si
    from core.config import DATA_OUTPUT
    from core.proceso_types import TIPOS_PROCESO, get_tipo_color
    from streamlit_app.services.data_service import DataService
    from services.cmi_filters import filter_df_for_cmi_estrategico, filter_df_for_cmi_procesos
    from streamlit_app.components.interactive_cards import render_metric_card
except (ImportError, ModuleNotFoundError):
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from services.strategic_indicators import preparar_pdi_con_cierre, load_pdi_catalog
    import services.strategic_indicators as si
    from core.config import DATA_OUTPUT
    from core.proceso_types import TIPOS_PROCESO, get_tipo_color
    from streamlit_app.services.data_service import DataService
    from services.cmi_filters import filter_df_for_cmi_estrategico, filter_df_for_cmi_procesos
    from streamlit_app.components.interactive_cards import render_metric_card

# Limpiar caché si es necesario
if "page_cache_cleared" not in st.session_state:
    try:
        si.load_worksheet_flags.clear()
        si.load_cierres.clear()
    except Exception:
        pass
    st.session_state.page_cache_cleared = True

PATH_CONSOLIDADO = DATA_OUTPUT / "Resultados Consolidados.xlsx"

LINE_COLORS = {
    "Expansión": "#FBAF17",
    "Transformación organizacional": "#42F2F2",
    "Calidad": "#EC0677",
    "Experiencia": "#1FB2DE",
    "Sostenibilidad": "#A6CE38",
    "Educación para toda la vida": "#0F385A",
}

LINEA_ICONS = {
    "Expansión": "🚀",
    "Transformación organizacional": "⚙️",
    "Calidad": "✨",
    "Experiencia": "👥",
    "Sostenibilidad": "🌱",
    "Educación para toda la vida": "📚",
}

MESES_NOMBRES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def _load_consolidado_cierres() -> pd.DataFrame:
    """Carga y normaliza la hoja Consolidado Cierres"""
    if not PATH_CONSOLIDADO.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(PATH_CONSOLIDADO, sheet_name="Consolidado Cierres", engine="openpyxl")
    except Exception:
        return pd.DataFrame()
    
    # Normalizar columnas
    df.columns = [str(c).strip() for c in df.columns]
    
    # Normalizar año
    if "Ao" in df.columns:
        df["Año"] = pd.to_numeric(df["Ao"], errors="coerce")
    elif "Anio" in df.columns:
        df["Año"] = pd.to_numeric(df["Anio"], errors="coerce")
    
    # Normalizar mes
    if "Mes" in df.columns:
        df["Mes_num"] = df["Mes"].apply(_parse_month)
    
    # Normalizar cumplimiento
    if "Cumplimiento" in df.columns and "cumplimiento_pct" not in df.columns:
        df["cumplimiento_pct"] = pd.to_numeric(df["Cumplimiento"], errors="coerce")
    
    return df


def _parse_month(value):
    """Convierte mes a número"""
    MES_MAP = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    }
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return MES_MAP.get(text.lower())


def _available_years(df: pd.DataFrame) -> list[int]:
    """Retorna años disponibles en los datos"""
    if df.empty or "Año" not in df.columns:
        return []
    years = pd.to_numeric(df["Año"], errors="coerce").dropna().astype(int).unique().tolist()
    return sorted([y for y in years if y in {2022, 2023, 2024, 2025}])


def _available_months_for_year(df: pd.DataFrame, year: int) -> list[int]:
    """Retorna meses disponibles para un año"""
    subset = df[df["Año"] == year].copy()
    if subset.empty or "Mes_num" not in subset.columns:
        return []
    months = pd.to_numeric(subset["Mes_num"], errors="coerce").dropna().astype(int).unique()
    return sorted(months.tolist())


def _latest_month_for_year(df: pd.DataFrame, year: int) -> int | None:
    """Retorna el último mes disponible para un año"""
    subset = df[df["Año"] == year].copy()
    if subset.empty or "Mes_num" not in subset.columns:
        return None
    months = pd.to_numeric(subset["Mes_num"], errors="coerce").dropna().astype(int)
    return int(months.max()) if not months.empty else None


def _compute_sparkline_data(df: pd.DataFrame, id_col: str, value_col: str, periods: int = 6) -> dict:
    """
    Genera datos de sparkline para los últimos N períodos.
    Retorna dict con {id: [valores históricos]}
    """
    # Implementación simplificada - retorna lista vacía por ahora
    # TODO: Implementar con datos históricos reales
    return {}


def _compute_trends(current: pd.DataFrame, previous: pd.DataFrame):
    """Calcula mejoras y desmejoras comparando dos períodos"""
    if current.empty or previous.empty:
        return [], []
    
    cur = current[["Id", "Indicador", "cumplimiento_pct"]].dropna(subset=["cumplimiento_pct"]).copy()
    prev = previous[["Id", "cumplimiento_pct"]].dropna(subset=["cumplimiento_pct"]).copy()
    merged = cur.merge(prev, on="Id", suffixes=("", "_prev"))
    
    if merged.empty:
        return [], []
    
    merged["variation"] = merged["cumplimiento_pct"] - merged["cumplimiento_pct_prev"]
    best = merged.sort_values("variation", ascending=False).head(5)
    worst = merged.sort_values("variation").head(5)
    
    return (
        [{"name": str(row["Indicador"]), "change": float(row["variation"])} for _, row in best.iterrows()],
        [{"name": str(row["Indicador"]), "change": float(row["variation"])} for _, row in worst.iterrows()],
    )


def _build_sunburst(pdi_df: pd.DataFrame) -> go.Figure:
    """Construye gráfico sunburst jerárquico"""
    df = pdi_df.copy()
    df["Linea"] = df["Linea"].fillna("Sin línea")
    df["Objetivo"] = df["Objetivo"].fillna("Sin objetivo")
    df = df[df["cumplimiento_pct"].notna()]
    
    if df.empty:
        return go.Figure()
    
    # Nivel 1: Líneas
    lines = df.groupby("Linea", dropna=False).agg(
        cumplimiento_pct=("cumplimiento_pct", "mean")
    ).reset_index()
    
    # Nivel 2: Objetivos
    grouped = df.groupby(["Linea", "Objetivo"], dropna=False).agg(
        cumplimiento_pct=("cumplimiento_pct", "mean")
    ).reset_index()
    
    labels = []
    parents = []
    values = []
    colors = []
    
    for _, line in lines.iterrows():
        labels.append(line["Linea"])
        parents.append("")
        values.append(1)
        colors.append(LINE_COLORS.get(line["Linea"], "#6B728E"))
    
    for _, row in grouped.iterrows():
        labels.append(row["Objetivo"])
        parents.append(row["Linea"])
        values.append(1)
        colors.append(LINE_COLORS.get(row["Linea"], "#6B728E"))
    
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
        insidetextorientation="radial",
    ))
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=600)
    
    return fig


def render_linea_cards(pdi_df: pd.DataFrame, prev_pdi_df: pd.DataFrame = None):
    """
    Renderiza tarjetas visuales por línea estratégica con diseño elaborado
    Incluye: icono, nombre, % cumplimiento, # indicadores, variación, sparkline
    """
    if pdi_df.empty:
        st.warning("No hay datos para mostrar")
        return
    
    # Agrupar por línea
    lineas_resumen = pdi_df.groupby("Linea").agg({
        "Indicador": "count",
        "cumplimiento_pct": "mean"
    }).reset_index()
    lineas_resumen.columns = ["Linea", "N_Indicadores", "Cumpl_Promedio"]
    
    # Calcular variación si hay datos previos
    variacion_map = {}
    if prev_pdi_df is not None and not prev_pdi_df.empty:
        prev_resumen = prev_pdi_df.groupby("Linea").agg({
            "cumplimiento_pct": "mean"
        }).reset_index()
        for _, row in lineas_resumen.iterrows():
            linea = row["Linea"]
            prev_row = prev_resumen[prev_resumen["Linea"] == linea]
            if not prev_row.empty:
                variacion = row["Cumpl_Promedio"] - prev_row.iloc[0]["cumplimiento_pct"]
                variacion_map[linea] = variacion
    
    # Mostrar en grid de 2 columnas
    for i in range(0, len(lineas_resumen), 2):
        cols = st.columns(2)
        
        for idx, (_, row) in enumerate(lineas_resumen.iloc[i:i+2].iterrows()):
            linea = row["Linea"]
            n_ind = int(row["N_Indicadores"])
            cumpl = row["Cumpl_Promedio"]
            
            icon = LINEA_ICONS.get(linea, "📊")
            color = LINE_COLORS.get(linea, "#6B728E")
            
            # Determinar tendencia
            trend = None
            trend_value = None
            if linea in variacion_map:
                var = variacion_map[linea]
                trend = "up" if var > 0 else "down" if var < 0 else "flat"
                trend_value = f"{var:+.1f}%"
            
            with cols[idx]:
                render_metric_card(
                    title=linea,
                    value=f"{cumpl:.1f}%",
                    subtitle=f"{n_ind} indicadores",
                    icon=icon,
                    color=color,
                    trend=trend,
                    trend_value=trend_value,
                    size="normal"
                )


def render_ai_insights_panel(insights: list[str], title: str = "💡 Perspectivas IA Estratégicas"):
    """
    Panel estilizado para mostrar insights generados por IA
    """
    if not insights:
        return
    
    insights_html = "\n".join([f"<li style='margin-bottom: 0.75rem;'>{insight}</li>" for insight in insights])
    
    panel_html = f"""
    <div style='
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8a 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        border-left: 4px solid #42F2F2;
    '>
        <div style='
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
        '>
            <div style='
                width: 48px;
                height: 48px;
                background: rgba(66, 242, 242, 0.2);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
            '>
                🤖
            </div>
            <h3 style='
                color: #FFFFFF;
                margin: 0;
                font-size: 1.1rem;
                font-weight: 600;
            '>{title}</h3>
        </div>
        
        <ul style='
            color: #E6F2FF;
            font-size: 0.95rem;
            line-height: 1.6;
            margin: 0;
            padding-left: 1.5rem;
        '>
            {insights_html}
        </ul>
    </div>
    """
    
    st.markdown(panel_html, unsafe_allow_html=True)


def render_trend_table(items: list[dict], title: str, positive: bool = True):
    """
    Tabla de indicadores con mayor mejora/desmejora incluyendo mini sparklines
    """
    if not items:
        st.info(f"No hay datos de {title.lower()}")
        return
    
    st.markdown(f"##### {title}")
    
    for item in items[:5]:  # Mostrar top 5
        name = item['name']
        change = item['change']
        
        # Color según si es positivo o negativo
        color = "#22C5 5E" if (positive and change > 0) or (not positive and change < 0) else "#EF4444"
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        
        # Mini sparkline (simulado con barras de progreso)
        sparkline_width = min(abs(change) * 2, 100)  # Escalar para visualización
        
        st.markdown(f"""
        <div style='
            background: white;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            border-left: 3px solid {color};
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        '>
            <div style='flex: 1;'>
                <div style='font-weight: 600; color: #1A1A1A; font-size: 0.9rem;'>{name}</div>
            </div>
            <div style='
                display: flex;
                align-items: center;
                gap: 0.5rem;
                min-width: 120px;
                justify-content: flex-end;
            '>
                <span style='color: {color}; font-size: 1.2rem;'>{arrow}</span>
                <span style='
                    font-weight: 700;
                    color: {color};
                    font-size: 1rem;
                '>{change:+.1f}%</span>
                <div style='
                    width: {sparkline_width}px;
                    height: 4px;
                    background: {color};
                    border-radius: 2px;
                    margin-left: 0.5rem;
                '></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render():
    """Función principal de renderizado"""
    st.title("📊 Resumen General")
    st.caption("Fuente: Consolidado Cierres — Resultados Consolidados.xlsx")
    
    # Cargar datos
    consolidado = _load_consolidado_cierres()
    if consolidado.empty:
        st.error("No se pudo cargar datos del consolidado.")
        return
    
    years = _available_years(consolidado)
    if not years:
        st.error("No hay años válidos en los datos.")
        return
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 1: CMI ESTRATÉGICO - Visión General
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("🎯 CMI ESTRATÉGICO - Visión General")
    
    # Filtros
    col_year_e, col_month_e,  col_linea = st.columns(3)
    
    with col_year_e:
        year_estrategico = st.selectbox(
            "Año de análisis",
            options=years,
            index=len(years)-1,
            key="cmi_estrategico_year"
        )
    
    with col_month_e:
        available_months_e = _available_months_for_year(consolidado, year_estrategico)
        if available_months_e:
            last_avail_e = max([m for m in available_months_e if 1 <= m <= 12], default=12)
            default_idx_e = last_avail_e - 1
        else:
            default_idx_e = 11
        month_name_estrategico = st.selectbox(
            "Mes de análisis",
            options=MESES_NOMBRES,
            index=default_idx_e,
            key="cmi_estrategico_month"
        )
        month_estrategico = MESES_NOMBRES.index(month_name_estrategico) + 1
    
    # Cargar datos PDI para CMI Estratégico
    pdi_estrategico = preparar_pdi_con_cierre(int(year_estrategico), int(month_estrategico))
    
    # Debug info
    st.info(f"✅ PDI cargado: {len(pdi_estrategico)} registros antes de filtrar por CMI Estratégico")
    
    pdi_estrategico = filter_df_for_cmi_estrategico(pdi_estrategico, id_column="Id")
    
    # Debug info después del filtro
    st.info(f"✅ CMI Estratégico filtrado: {len(pdi_estrategico)} indicadores")
    if not pdi_estrategico.empty:
        st.success(f"Columnas disponibles: {', '.join(pdi_estrategico.columns[:10])}")
    
    # Filtrar por línea si se selecciona
    pdi_catalog = load_pdi_catalog()
    lineas_disponibles = sorted(
        pdi_catalog["Linea"].dropna().astype(str).unique().tolist()
        if not pdi_catalog.empty else pdi_estrategico["Linea"].dropna().astype(str).unique().tolist()
    ) if not pdi_estrategico.empty else []
    
    with col_linea:
        linea_seleccionada = st.selectbox(
            "Línea Estratégica",
            options=["Todas"] + lineas_disponibles,
            key="cmi_estrategico_linea"
        )
    
    if linea_seleccionada != "Todas" and not pdi_estrategico.empty:
        before_count = len(pdi_estrategico)
        pdi_estrategico = pdi_estrategico[pdi_estrategico["Linea"] == linea_seleccionada]
        st.info(f"Filtrado por línea '{linea_seleccionada}': {before_count} → {len(pdi_estrategico)} indicadores")
    
    # Datos previos para comparación
    prev_year_e = year_estrategico - 1
    prev_month_e = _latest_month_for_year(consolidado, prev_year_e)
    prev_pdi_e = None
    if prev_month_e:
        prev_pdi_e = preparar_pdi_con_cierre(prev_year_e, prev_month_e)
        prev_pdi_e = filter_df_for_cmi_estrategico(prev_pdi_e, id_column="Id")
    
    if not pdi_estrategico.empty:
        # === Tarjetas por Línea Estratégica ===
        st.markdown("##### Métricas Clave por Línea Estratégica")
        try:
            render_linea_cards(pdi_estrategico, prev_pdi_e)
        except Exception as e:
            st.error(f"Error renderizando tarjetas: {e}")
            import traceback
            st.code(traceback.format_exc())
        
        # === Sunburst ===
        st.markdown("##### Alineación de Objetivos Estratégicos")
        try:
            # Verificar columnas necesarias
            required_cols = ["Linea", "Objetivo", "cumplimiento_pct"]
            missing_cols = [col for col in required_cols if col not in pdi_estrategico.columns]
            if missing_cols:
                st.error(f"❌ Columnas faltantes para sunburst: {missing_cols}")
                st.write("Columnas disponibles:", list(pdi_estrategico.columns))
            else:
                st.success(f"✅ Construyendo sunburst con {len(pdi_estrategico)} indicadores")
                sunburst = _build_sunburst(pdi_estrategico)
                if len(sunburst.data) > 0:
                    st.plotly_chart(sunburst, use_container_width=True)
                else:
                    st.warning("⚠️ El sunburst está vacío (sin datos válidos)")
        except Exception as e:
            st.error(f"❌ Error construyendo sunburst: {e}")
            import traceback
            st.code(traceback.format_exc())
        
        # === KPIs Globales ===
        st.markdown("##### KPIs Globales")
        count_total = len(pdi_estrategico)
        counts = {
            "Sobrecumplimiento": int((pdi_estrategico["Nivel de cumplimiento"] == "Sobrecumplimiento").sum()),
            "Cumplimiento": int((pdi_estrategico["Nivel de cumplimiento"] == "Cumplimiento").sum()),
            "Alerta": int((pdi_estrategico["Nivel de cumplimiento"] == "Alerta").sum()),
            "Peligro": int((pdi_estrategico["Nivel de cumplimiento"] == "Peligro").sum()),
        }
        
        kpi_cols = st.columns(5)
        colors = ["#0B5FFF", "#1A3A5C", "#43A047", "#FBAF17", "#D32F2F"]
        values = [count_total, counts["Sobrecumplimiento"], counts["Cumplimiento"], counts["Alerta"], counts["Peligro"]]
        labels = ["Total", "Sobrecumplimiento", "Cumplimiento", "Alerta", "Peligro"]
        icons = ["📊", "🏆", "✅", "⚠️", "🚨"]
        
        for col, label, value, color, icon in zip(kpi_cols, labels, values, colors, icons):
            with col:
                st.metric(label=label, value=value)
        
        # === Análisis de Tendencias ===
        if prev_pdi_e is not None:
            best_improvements, worst_declines = _compute_trends(pdi_estrategico, prev_pdi_e)
            
            col1, col2 = st.columns(2)
            with col1:
                render_trend_table(best_improvements, "📈 Mayor Mejora vs Histórico", positive=True)
            with col2:
                render_trend_table(worst_declines, "📉 Mayor Desmejora vs Histórico", positive=False)
        
        # === Insights IA ===
        health_rate = round(((counts["Sobrecumplimiento"] + counts["Cumplimiento"]) / max(count_total, 1)) * 100, 1)
        insights = []
        
        if health_rate >= 70:
            insights.append(f"✅ El {health_rate}% de los indicadores PDI están en niveles saludables.")
        elif health_rate >= 50:
            insights.append(f"⚠️ El {health_rate}% de los indicadores están en cumplimiento, con riesgo en algunos objetivos.")
        else:
            insights.append(f"🚨 Solo el {health_rate}% cumplen expectativas; se requiere acción prioritaria.")
        
        # Línea líder
        best_line = pdi_estrategico.groupby("Linea").agg(cumplimiento_pct=("cumplimiento_pct", "mean")).reset_index()
        best_line = best_line.sort_values("cumplimiento_pct", ascending=False).head(1)
        if not best_line.empty:
            line_name = str(best_line.iloc[0]["Linea"])
            line_avg = float(best_line.iloc[0]["cumplimiento_pct"])
            insights.append(f"🌟 La línea \"{line_name}\" lidera con {line_avg:.1f}% de cumplimiento promedio.")
        
        render_ai_insights_panel(insights)
    
    else:
        st.warning("No hay indicadores de CM I Estratégico para el corte seleccionado.")
    
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 2: CMI POR PROCESOS - Desempeño Operativo
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("🔧 CMI POR PROCESOS - Desempeño Operativo")
    
    # Filtros
    col_year_p, col_month_p, col_tipo = st.columns(3)
    
    with col_year_p:
        year_procesos = st.selectbox(
            "Año de análisis",
            options=years,
            index=len(years)-1,
            key="cmi_procesos_year"
        )
    
    with col_month_p:
        available_months_p = _available_months_for_year(consolidado, year_procesos)
        if available_months_p:
            last_avail_p = max([m for m in available_months_p if 1 <= m <= 12], default=12)
            default_idx_p = last_avail_p - 1
        else:
            default_idx_p = 11
        month_name_procesos = st.selectbox(
            "Mes de análisis",
            options=MESES_NOMBRES,
            index=default_idx_p,
            key="cmi_procesos_month"
        )
        month_procesos = MESES_NOMBRES.index(month_name_procesos) + 1
    
    with col_tipo:
        tipo_proceso_seleccionado = st.selectbox(
            "Tipo de proceso",
            options=["Todos"] + TIPOS_PROCESO,
            key="cmi_procesos_tipo"
        )
    
    # Cargar datos
    pdi_procesos = preparar_pdi_con_cierre(int(year_procesos), int(month_procesos))
    pdi_procesos = filter_df_for_cmi_procesos(pdi_procesos, id_column="Id")
    
    # Merge con tipos
    data_service = DataService()
    map_df = data_service.get_process_map()
    
    if not pdi_procesos.empty and not map_df.empty and "Subproceso" in pdi_procesos.columns:
        pdi_procesos = pdi_procesos.merge(
            map_df[["Subproceso", "Tipo de proceso"]].drop_duplicates(),
            on="Subproceso",
            how="left"
        )
        
        # Filtrar por tipo si se seleccionó uno específico
        if tipo_proceso_seleccionado != "Todos":
            pdi_procesos = pdi_procesos[pdi_procesos["Tipo de proceso"] == tipo_proceso_seleccionado]
        
        if not pdi_procesos.empty:
            st.markdown("##### Monitoreo de Procesos Clave")
            
            # Tarjetas por tipo o subproceso
            if tipo_proceso_seleccionado == "Todos":
                # Vista por tipos
                tipos_unicos = sorted([t for t in pdi_procesos["Tipo de proceso"].dropna().unique() if t in TIPOS_PROCESO])
                
                if tipos_unicos:
                    # Grid de 4 columnas
                    for i in range(0, len(tipos_unicos), 4):
                        cols = st.columns(4)
                        for idx, tipo in enumerate(tipos_unicos[i:i+4]):
                            df_tipo = pdi_procesos[pdi_procesos["Tipo de proceso"] == tipo]
                            
                            n_subprocesos = df_tipo["Subproceso"].nunique()
                            n_indicadores = len(df_tipo)
                            cumpl_promedio = df_tipo["cumplimiento_pct"].mean() if not df_tipo["cumplimiento_pct"].isna().all() else 0
                            
                            tipo_color = get_tipo_color(tipo, light=False)
                            
                            with cols[idx]:
                                render_metric_card(
                                    title=tipo,
                                    value=f"{cumpl_promedio:.1f}%",
                                    subtitle=f"{n_indicadores} indicadores · {n_subprocesos} subprocesos",
                                    icon="📋",
                                    color=tipo_color,
                                    size="normal"
                                )
            else:
                # Vista por subprocesos del tipo seleccionado
                subprocesos_del_tipo = sorted(pdi_procesos["Subproceso"].dropna().unique())
                
                st.markdown(f"###### Subprocesos de {tipo_proceso_seleccionado}")
                
                if subprocesos_del_tipo:
                    for i in range(0, len(subprocesos_del_tipo), 3):
                        cols = st.columns(3)
                        for idx, subproceso in enumerate(subprocesos_del_tipo[i:i+3]):
                            df_subproceso = pdi_procesos[pdi_procesos["Subproceso"] == subproceso]
                            
                            n_ind = len(df_subproceso)
                            cumpl_prom = df_subproceso["cumplimiento_pct"].mean() if not df_subproceso["cumplimiento_pct"].isna().all() else 0
                            
                            # Color según cumplimiento
                            if cumpl_prom >= 100:
                                color = "#22C55E"
                            elif cumpl_prom >= 80:
                                color = "#FBBF24"
                            else:
                                color = "#EF4444"
                            
                            with cols[idx]:
                                render_metric_card(
                                    title=subproceso,
                                    value=f"{cumpl_prom:.1f}%",
                                    subtitle=f"{n_ind} indicadores",
                                    icon="⚙️",
                                    color=color,
                                    size="small"
                                )
                else:
                    st.info(f"No hay subprocesos del tipo {tipo_proceso_seleccionado}")
            
            # Gráfico de barras apiladas
            st.markdown("##### Distribución de Niveles de Cumplimiento")
            
            # Procesar datos para gráfico
            levels = ["Sobrecumplimiento", "Cumplimiento", "Alerta", "Peligro"]
            tipos_para_grafico = sorted([t for t in pdi_procesos["Tipo de proceso"].dropna().unique() if t in TIPOS_PROCESO])
            
            fig = go.Figure()
            for level in levels:
                counts_por_tipo = []
                for tipo in tipos_para_grafico:
                    count = len(pdi_procesos[(pdi_procesos["Tipo de proceso"] == tipo) & (pdi_procesos["Nivel de cumplimiento"] == level)])
                    counts_por_tipo.append(count)
                
                level_colors = {
                    "Sobrecumplimiento": "#1A3A5C",
                    "Cumplimiento": "#43A047",
                    "Alerta": "#FBAF17",
                    "Peligro": "#D32F2F"
                }
                
                fig.add_trace(go.Bar(
                    name=level,
                    x=tipos_para_grafico,
                    y=counts_por_tipo,
                    marker_color=level_colors.get(level, "#6B728E")
                ))
            
            fig.update_layout(
                barmode='stack',
                xaxis_tickangle=-45,
                height=400,
                margin=dict(t=40, b=100),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Insights IA Operativos
            total_procesos = len(pdi_procesos)
            health_procesos = len(pdi_procesos[pdi_procesos["Nivel de cumplimiento"].isin(["Sobrecumplimiento", "Cumplimiento"])])
            health_pct = round(health_procesos / max(total_procesos, 1) * 100, 1)
            
            insights_op = [
                f"✅ El {health_pct}% de los indicadores por proceso están en niveles saludables."
            ]
            
            render_ai_insights_panel(insights_op, title="💡 Perspectivas Operativas IA")
    
    else:
        st.warning("No hay indicadores de CMI por Procesos para el corte seleccionado.")


if __name__ == "__main__":
    render()
