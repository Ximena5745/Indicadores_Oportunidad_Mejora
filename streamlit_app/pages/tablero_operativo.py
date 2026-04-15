"""
pages/tablero_operativo.py — Tablero Operativo Nivel 3.

Fuentes:
  · cargar_dataset()        → indicadores con Categoria, Cumplimiento, Periodicidad, Proceso, Fecha
  · cargar_acciones_mejora() → acciones de mejora / OM
  · data/output/artifacts/ingesta_*.json → artefactos QC de ingesta

Pestañas:
  1. Resumen       — KPIs globales + donut + barras por proceso + alertas de frecuencia
  2. Kanban        — columnas por estado, click filtra tabla detallada
  3. QC Datos      — panel de calidad desde artefactos de ingesta
  4. Trazabilidad  — por indicador: artefactos, fechas, histórico de reportes
"""
from datetime import date
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from core.config import CACHE_TTL, NIVEL_COLOR, NIVEL_BG, NIVEL_ICON
    from services.data_loader import cargar_dataset, cargar_acciones_mejora
except (ImportError, ModuleNotFoundError):
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.config import CACHE_TTL, NIVEL_COLOR, NIVEL_BG, NIVEL_ICON
    from services.data_loader import cargar_dataset, cargar_acciones_mejora

# Importes desde streamlit_app
try:
    from ..utils.formatting import id_limpio as _id_limpio, to_num as _to_num
except (ImportError, ModuleNotFoundError):
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.formatting import id_limpio as _id_limpio, to_num as _to_num

# ── Rutas ─────────────────────────────────────────────────────────────────────
_ROOT      = Path(__file__).resolve().parents[2]
_ARTIFACTS = _ROOT / "data" / "output" / "artifacts"

# ── Constantes visuales (alineadas con resumen_general) ───────────────────────
_NO_APLICA = "No aplica"
_PEND      = "Pendiente de reporte"

_NIVEL_COLOR_EXT = {
    **NIVEL_COLOR,
    "Sobrecumplimiento": "#4472C4",
    _NO_APLICA: "#78909C",
    _PEND:      "#BDBDBD",
}
_NIVEL_BG_EXT = {
    **NIVEL_BG,
    _NO_APLICA: "#ECEFF1",
    _PEND:      "#F5F5F5",
}
_NIVEL_ICON_EXT = {
    **NIVEL_ICON,
    _NO_APLICA: "⚫",
    _PEND:      "⚪",
}

_KANBAN_COLS = [
    ("Peligro",           "#FFCDD2", "#C62828", "🔴"),
    ("Alerta",            "#FEF9E7", "#F57F17", "🟡"),
    ("Cumplimiento",      "#E8F5E9", "#2E7D32", "🟢"),
    ("Sobrecumplimiento", "#E3F2FD", "#1565C0", "🔵"),
    (_PEND,               "#F5F5F5", "#616161", "⚪"),
]

_ORDEN_SEV = {"Peligro": 0, "Alerta": 1, "Cumplimiento": 2, "Sobrecumplimiento": 3,
              _NO_APLICA: -1, _PEND: -1}

_MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
_MES_NUM = {m: i + 1 for i, m in enumerate(_MESES)}

# ── Ventana de periodicidad en meses ─────────────────────────────────────────
_VENTANA: dict[str, int] = {
    "mensual": 1, "bimestral": 2, "trimestral": 3, "semestral": 6, "anual": 12,
}


def _nm(s: str) -> str:
    s = str(s or "").strip().lower()
    for a, b in (("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u")):
        s = s.replace(a, b)
    return s


def _ventana(periodicidad: str) -> int:
    return _VENTANA.get(_nm(periodicidad), 1)


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cargar_base() -> pd.DataFrame:
    return cargar_dataset()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cargar_artefactos_qc() -> list[dict]:
    """Carga todos los JSONs de ingesta en artifacts/."""
    resultados = []
    for path in sorted(_ARTIFACTS.glob("ingesta_*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_archivo"] = path.name
            resultados.append(data)
        except Exception:
            pass
    # Incluir también pipeline_run artifacts si existen
    for path in sorted(_ARTIFACTS.glob("pipeline_run_*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_archivo"] = path.name
            data["_tipo"] = "pipeline_run"
            resultados.append(data)
        except Exception:
            pass
    return resultados


# ══════════════════════════════════════════════════════════════════════════════
# TRANSFORMACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _preparar_df(
    df_all: pd.DataFrame,
    anio: int | None,
    mes_num: int | None,
    proceso: str,
    periodicidad: str,
) -> pd.DataFrame:
    if df_all.empty:
        return df_all.copy()

    df = df_all.copy()

    # Normalizar columna de categoría
    if "Categoria" not in df.columns and "Nivel de cumplimiento" in df.columns:
        df["Categoria"] = df["Nivel de cumplimiento"]

    # Columna de año
    if "Anio" not in df.columns and "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        df["Anio"] = df["Fecha"].dt.year

    if anio:
        if "Anio" in df.columns:
            df = df[pd.to_numeric(df["Anio"], errors="coerce") == anio]
        elif "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
            df = df[df["Fecha"].dt.year == anio]

    # Tomar último registro por indicador
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        df = df.sort_values("Fecha").drop_duplicates(subset="Id", keep="last")

    if proceso and proceso != "Todos" and "Proceso" in df.columns:
        df = df[df["Proceso"].astype(str) == proceso]

    if periodicidad and periodicidad != "Todas" and "Periodicidad" in df.columns:
        df = df[df["Periodicidad"].astype(str) == periodicidad]

    # Limpiar Categoria
    if "Categoria" in df.columns:
        df["Categoria"] = df["Categoria"].fillna(_PEND)
        df.loc[df["Categoria"].isin(["", "Sin dato", "nan"]), "Categoria"] = _PEND

    return df.reset_index(drop=True)


def _detectar_vencidos(df: pd.DataFrame) -> pd.DataFrame:
    """Indicadores cuyo último reporte supera la ventana de periodicidad."""
    hoy = date.today()
    ym_hoy = hoy.year * 12 + hoy.month
    needed = {"Id", "Fecha", "Periodicidad"}
    if not needed.issubset(df.columns):
        return pd.DataFrame()

    d = df.copy()
    d["Fecha"] = pd.to_datetime(d["Fecha"], errors="coerce")
    d["ym"] = (
        d["Fecha"].dt.year.fillna(0).astype(int) * 12
        + d["Fecha"].dt.month.fillna(0).astype(int)
    )
    d["ventana"] = d["Periodicidad"].apply(_ventana)
    d["diff"] = ym_hoy - d["ym"]
    venc = d[d["diff"] > d["ventana"]].copy()
    cols = [c for c in ["Id", "Indicador", "Proceso", "Periodicidad", "Categoria", "diff"] if c in venc.columns]
    return venc[cols].rename(columns={"diff": "Meses sin reporte"})


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICOS
# ══════════════════════════════════════════════════════════════════════════════

def _fig_donut(df: pd.DataFrame) -> go.Figure:
    if "Categoria" not in df.columns or df.empty:
        return go.Figure()
    cats = [c for c, *_ in _KANBAN_COLS]
    counts = df["Categoria"].value_counts()
    labels = [c for c in cats if c in counts.index]
    values = [int(counts[c]) for c in labels]
    colors = [_NIVEL_COLOR_EXT.get(c, "#BDBDBD") for c in labels]
    total  = sum(values)
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+value", textfont=dict(size=11),
        hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        height=380, showlegend=True,
        legend=dict(orientation="h", y=-0.15, x=0),
        margin=dict(t=10, b=60, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(text=f"<b>{total}</b><br>total", x=0.5, y=0.5, font_size=15, showarrow=False)],
    )
    return fig


def _option_donut(df: pd.DataFrame) -> dict:
    if "Categoria" not in df.columns or df.empty:
        return {}
    cats = [c for c, *_ in _KANBAN_COLS]
    counts = df["Categoria"].value_counts()
    labels = [c for c in cats if c in counts.index]
    values = [int(counts[c]) for c in labels]
    option = {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {"orient": "horizontal", "bottom": 0},
        "series": [
            {
                "name": "Categorias",
                "type": "pie",
                "radius": ["40%", "65%"],
                "avoidLabelOverlap": False,
                "label": {"show": False, "position": "center"},
                "emphasis": {"label": {"show": True, "fontSize": 14, "fontWeight": "bold"}},
                "labelLine": {"show": False},
                "data": [{"value": v, "name": l} for v, l in zip(values, labels)],
            }
        ],
    }
    return {"option": option, "height": 380}


def _fig_proceso(df: pd.DataFrame) -> go.Figure:
    col = (
        "ProcesoPadre" if "ProcesoPadre" in df.columns
        else ("Proceso" if "Proceso" in df.columns else None)
    )
    if not col or df.empty or "Categoria" not in df.columns:
        return go.Figure()

    cats = [c for c, *_ in _KANBAN_COLS]
    stats = (
        df.groupby([col, "Categoria"], dropna=False)
        .size().unstack(fill_value=0).reset_index()
    )
    for c in cats:
        if c not in stats.columns:
            stats[c] = 0

    stats["_crit"] = stats.get("Peligro", 0) + stats.get("Alerta", 0)
    stats = stats.sort_values("_crit", ascending=True).tail(16)
    procs = stats[col].astype(str).tolist()
    h = max(320, len(procs) * 32 + 70)

    fig = go.Figure()
    for cat in cats:
        if cat not in stats.columns:
            continue
        fig.add_trace(go.Bar(
            y=procs, x=stats[cat].tolist(), orientation="h", name=cat,
            marker_color=_NIVEL_COLOR_EXT.get(cat, "#BDBDBD"),
            text=[v if v else "" for v in stats[cat].tolist()],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=10, color="white"),
        ))
    fig.update_layout(
        barmode="stack", height=h,
        yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
        margin=dict(t=10, b=40, l=200, r=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.12),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# RENDER
# ══════════════════════════════════════════════════════════════════════════════

def render() -> None:
    st.title("Tablero Operativo")
    st.caption("Nivel 3 — Kanban de indicadores · Alertas de reporte · QC de datos · Trazabilidad")

    # ── Carga base ─────────────────────────────────────────────────────────
    df_all = _cargar_base()

    # Años disponibles
    anios: list[int] = []
    if not df_all.empty:
        if "Anio" in df_all.columns:
            anios = sorted(pd.to_numeric(df_all["Anio"], errors="coerce").dropna().astype(int).unique().tolist())
        elif "Fecha" in df_all.columns:
            df_all["Fecha"] = pd.to_datetime(df_all["Fecha"], errors="coerce")
            anios = sorted(df_all["Fecha"].dt.year.dropna().astype(int).unique().tolist())

    # ── Filtros globales ───────────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            default_idx = len(anios) if anios else 0
            anio_sel = st.selectbox(
                "Año", options=["Todos"] + anios, index=default_idx, key="to_anio",
            )
        with fc2:
            mes_sel = st.selectbox("Mes", options=["Todos"] + _MESES, key="to_mes")
        with fc3:
            procs_op = ["Todos"] + sorted(
                df_all["Proceso"].dropna().astype(str).unique().tolist()
            ) if not df_all.empty and "Proceso" in df_all.columns else ["Todos"]
            proceso_sel = st.selectbox("Proceso", procs_op, key="to_proc")
        with fc4:
            perios_op = ["Todas"] + sorted(
                df_all["Periodicidad"].dropna().astype(str).unique().tolist()
            ) if not df_all.empty and "Periodicidad" in df_all.columns else ["Todas"]
            period_sel = st.selectbox("Periodicidad", perios_op, key="to_perio")

    anio_v   = int(anio_sel) if anio_sel != "Todos" and anio_sel else None
    mes_v    = _MES_NUM.get(mes_sel) if mes_sel != "Todos" else None
    df = _preparar_df(df_all, anio_v, mes_v, proceso_sel, period_sel)

    if df.empty:
        st.warning("Sin datos para los filtros seleccionados.")
        return

    # ── Pestañas ───────────────────────────────────────────────────────────
    tab_res, tab_kan, tab_qc, tab_traz = st.tabs(
        ["📊 Resumen", "📋 Kanban", "🔬 QC Datos", "🔗 Trazabilidad"]
    )

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1 — RESUMEN
    # ═══════════════════════════════════════════════════════════════════════
    with tab_res:
        total   = len(df)
        peligro = int((df["Categoria"] == "Peligro").sum()) if "Categoria" in df.columns else 0
        alerta  = int((df["Categoria"] == "Alerta").sum())  if "Categoria" in df.columns else 0
        pend    = int((df["Categoria"] == _PEND).sum())     if "Categoria" in df.columns else 0
        cum_s   = pd.to_numeric(df.get("Cumplimiento", pd.Series(dtype=float)), errors="coerce").dropna()
        prom_c  = float(cum_s.mean() * 100) if not cum_s.empty else None

        try:
            from ..components.renderers import kpi_card, generate_sparkline_counts, generate_sparkline_agg
        except (ImportError, ModuleNotFoundError):
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from components.renderers import kpi_card, generate_sparkline_counts, generate_sparkline_agg
        # Generar sparklines (usamos `df_all` para series históricas)
        spark_total = generate_sparkline_counts(df_all, periods=6)
        spark_peligro = generate_sparkline_counts(df_all, group_col='Categoria', filter_val='Peligro', periods=6)
        spark_alerta = generate_sparkline_counts(df_all, group_col='Categoria', filter_val='Alerta', periods=6)
        spark_sinrep = generate_sparkline_counts(df_all, group_col='Categoria', filter_val=_PEND, periods=6)
        spark_prom = generate_sparkline_agg(df_all, value_col='Cumplimiento', agg='mean', periods=6)

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            try:
                kpi_card("Total indicadores", total, sparkline=spark_total)
            except Exception:
                st.metric("Total indicadores", total)
        with k2:
            try:
                kpi_card("🔴 Peligro", peligro, delta=(f"{peligro / total * 100:.1f}%" if total else ""), category="Peligro", sparkline=spark_peligro)
            except Exception:
                st.metric("🔴 Peligro", peligro, delta=(f"{peligro / total * 100:.1f}%" if total else ""), delta_color="inverse")
        with k3:
            try:
                kpi_card("🟡 Alerta", alerta, delta=(f"{alerta / total * 100:.1f}%" if total else ""), category="Alerta", sparkline=spark_alerta)
            except Exception:
                st.metric("🟡 Alerta", alerta, delta=(f"{alerta / total * 100:.1f}%" if total else ""), delta_color="inverse")
        with k4:
            try:
                kpi_card("⚪ Sin reporte", pend, sparkline=spark_sinrep)
            except Exception:
                st.metric("⚪ Sin reporte", pend)
        with k5:
            try:
                kpi_card("Cumplimiento promedio", f"{prom_c:.1f}%" if prom_c is not None else "N/D", sparkline=spark_prom)
            except Exception:
                st.metric("Cumplimiento promedio", f"{prom_c:.1f}%" if prom_c is not None else "N/D")

        try:
            try:
                from ..components.renderers import render_narrative_panel, render_alert_strip
            except (ImportError, ModuleNotFoundError):
                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from components.renderers import render_narrative_panel, render_alert_strip
            # Mostrar advertencia si promedio muy bajo
            if prom_c is not None and prom_c < 70:
                render_alert_strip(f"Promedio de cumplimiento bajo: {prom_c:.1f}% — revisar procesos críticos.", level='warning')
            render_narrative_panel("Resumen rápido", f"Total: {total} · Peligro: {peligro} · Alerta: {alerta} · Sin reporte: {pend}", collapsed=True)
        except Exception:
            pass

        # Alertas de frecuencia de reporte
        venc = _detectar_vencidos(df)
        if not venc.empty:
            st.warning(f"⚠️ **{len(venc)} indicadores** sin reporte dentro de su ventana de periodicidad.")
            with st.expander("Ver indicadores con reporte vencido", expanded=False):
                st.dataframe(venc, use_container_width=True, hide_index=True, height=260)

        r1c1, r1c2 = st.columns([1, 1])
        with r1c1:
            st.markdown("#### Distribución por nivel")
            try:
                try:
                    from ..components.renderers import render_echarts
                except (ImportError, ModuleNotFoundError):
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent))
                    from components.renderers import render_echarts
                opt = _option_donut(df)
                if opt and opt.get('option'):
                    render_echarts(opt['option'], height=opt.get('height', 380))
                else:
                    st.plotly_chart(_fig_donut(df), use_container_width=True, key="to_res_donut")
            except Exception:
                st.plotly_chart(_fig_donut(df), use_container_width=True, key="to_res_donut")
        with r1c2:
            st.markdown("#### Por proceso (top 16 críticos)")
            try:
                try:
                    from ..components.renderers import render_echarts
                except (ImportError, ModuleNotFoundError):
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent))
                    from components.renderers import render_echarts
                opt_h = _option_proceso(df)
                if opt_h and isinstance(opt_h, dict) and opt_h.get('option'):
                    render_echarts(opt_h['option'], height=opt_h.get('height', 420))
                else:
                    st.plotly_chart(_fig_proceso(df), use_container_width=True, key="to_res_proc")
            except Exception:
                st.plotly_chart(_fig_proceso(df), use_container_width=True, key="to_res_proc")

        # Panel de acciones de mejora vinculadas
        st.markdown("---")
        st.markdown("#### Acciones de Mejora abiertas")
        df_acc = cargar_acciones_mejora()
        if not df_acc.empty:
            estado_col = "ESTADO" if "ESTADO" in df_acc.columns else None
            abiertas = df_acc[df_acc[estado_col] != "Cerrada"] if estado_col else df_acc
            vencidas = (
                int((abiertas["Estado_Tiempo"] == "Vencida").sum())
                if "Estado_Tiempo" in abiertas.columns else None
            )
            avance_s = pd.to_numeric(abiertas.get("AVANCE", pd.Series(dtype=float)), errors="coerce").dropna()
            prom_av  = float(avance_s.mean()) if not avance_s.empty else None

            ac1, ac2, ac3 = st.columns(3)
            ac1.metric("Acciones abiertas", len(abiertas))
            if vencidas is not None:
                ac2.metric("Vencidas", vencidas, delta_color="inverse")
            ac3.metric("Avance promedio", f"{prom_av:.1f}%" if prom_av is not None else "—")
        else:
            st.info("No hay datos de acciones de mejora disponibles.")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2 — KANBAN
    # ═══════════════════════════════════════════════════════════════════════
    with tab_kan:
        if "to_kanban_filtro" not in st.session_state:
            st.session_state["to_kanban_filtro"] = None

        # ── Columnas Kanban ────────────────────────────────────────────────
        cols_kan = st.columns(len(_KANBAN_COLS))
        for idx, (cat, bg, fg, icon) in enumerate(_KANBAN_COLS):
            cnt = int((df["Categoria"] == cat).sum()) if "Categoria" in df.columns else 0
            active  = st.session_state["to_kanban_filtro"] == cat
            border  = f"3px solid {fg}" if active else f"1px solid {fg}55"
            opacity = "1.0" if active or cnt else "0.55"
            with cols_kan[idx]:
                st.markdown(
                    f"""<div style="background:{bg};border:{border};border-radius:12px;
                        padding:0.9rem 0.5rem;text-align:center;opacity:{opacity};
                        box-shadow:0 4px 12px {fg}22;">
                        <div style="font-size:1.5rem;">{icon}</div>
                        <div style="font-size:1.75rem;font-weight:800;color:{fg};
                             line-height:1.2;">{cnt}</div>
                        <div style="font-size:0.78rem;font-weight:600;color:{fg};
                             margin-top:0.25rem;">{cat}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                btn_label = "✓ Activo" if active else "Filtrar"
                if st.button(btn_label, key=f"to_kan_btn_{idx}", use_container_width=True):
                    st.session_state["to_kanban_filtro"] = None if active else cat
                    st.rerun()

        st.markdown("---")
        filtro_k = st.session_state.get("to_kanban_filtro")
        df_kan   = df[df["Categoria"] == filtro_k].copy() if filtro_k else df.copy()
        caption  = (
            f"**{filtro_k}** — {len(df_kan)} indicadores · Haz clic en el botón activo para limpiar."
            if filtro_k else f"Todos los indicadores ({len(df_kan)}) · Selecciona una columna para filtrar."
        )
        st.caption(caption)

        # Búsqueda adicional dentro de la vista kanban
        busq = st.text_input("Buscar por ID o nombre", key="to_kan_busq", placeholder="Texto libre...")
        if busq.strip():
            _m = (
                df_kan["Id"].astype(str).str.contains(busq.strip(), case=False, na=False)
                | df_kan.get("Indicador", pd.Series(dtype=str)).astype(str).str.contains(busq.strip(), case=False, na=False)
            )
            df_kan = df_kan[_m]

        disp_cols = [c for c in ["Id", "Indicador", "Proceso", "Periodicidad", "Categoria", "Cumplimiento", "Fecha"] if c in df_kan.columns]
        disp_df   = df_kan[disp_cols].copy()
        if "Cumplimiento" in disp_df.columns:
            disp_df["Cumplimiento"] = pd.to_numeric(disp_df["Cumplimiento"], errors="coerce").apply(
                lambda v: f"{v * 100:.1f}%" if pd.notna(v) else "—"
            )
        if "Fecha" in disp_df.columns:
            disp_df["Fecha"] = pd.to_datetime(disp_df["Fecha"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("—")

        st.dataframe(
            disp_df,
            use_container_width=True,
            hide_index=True,
            height=440,
            column_config={
                "Id":           st.column_config.TextColumn("ID", width="small"),
                "Indicador":    st.column_config.TextColumn("Indicador", width="large"),
                "Proceso":      st.column_config.TextColumn("Proceso", width="medium"),
                "Periodicidad": st.column_config.TextColumn("Periodicidad", width="small"),
                "Categoria":    st.column_config.TextColumn("Estado", width="medium"),
                "Cumplimiento": st.column_config.TextColumn("Cumplimiento", width="small"),
                "Fecha":        st.column_config.TextColumn("Última fecha", width="small"),
            },
        )

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 3 — QC DATOS
    # ═══════════════════════════════════════════════════════════════════════
    with tab_qc:
        artefactos = _cargar_artefactos_qc()
        # Filtrar solo los de ingesta (no pipeline_run que tienen estructura diferente)
        ingesta_arts = [a for a in artefactos if a.get("_tipo") != "pipeline_run" and "resumen" in a]

        if not ingesta_arts:
            st.info("No se encontraron artefactos de ingesta en data/output/artifacts/.")
        else:
            # KPIs globales
            t_arch  = sum(a["resumen"].get("total_archivos", 0) for a in ingesta_arts)
            t_exit  = sum(a["resumen"].get("exitosos", 0) for a in ingesta_arts)
            t_fall  = sum(a["resumen"].get("fallidos", 0) for a in ingesta_arts)
            t_reg   = sum(a["resumen"].get("total_registros", 0) for a in ingesta_arts)
            t_val   = sum(a["resumen"].get("total_validaciones", 0) for a in ingesta_arts)

            qa1, qa2, qa3, qa4, qa5 = st.columns(5)
            qa1.metric("Ejecuciones", len(ingesta_arts))
            qa2.metric("Archivos procesados", t_arch)
            qa3.metric("✅ Exitosos", t_exit)
            qa4.metric("❌ Fallidos", t_fall, delta_color="inverse")
            qa5.metric("Registros totales", f"{t_reg:,}")

            # Semáforo QC
            tasa_ok = t_exit / t_arch * 100 if t_arch else 0
            if tasa_ok >= 80:
                st.success(f"QC semáforo: ✅ Tasa de éxito {tasa_ok:.0f}%")
            elif tasa_ok >= 50:
                st.warning(f"QC semáforo: 🟡 Tasa de éxito {tasa_ok:.0f}%")
            else:
                st.error(f"QC semáforo: 🔴 Tasa de éxito {tasa_ok:.0f}%")

            # ── Tabla resumen por archivo ──────────────────────────────────
            rows = []
            for art in ingesta_arts:
                fecha_run = art["resumen"].get("fecha", art.get("_archivo", "—"))
                for det in art.get("detalle", []):
                    warns = [v for v in det.get("validaciones", []) if v.get("estado") == "WARNING"]
                    fails = [v for v in det.get("validaciones", []) if v.get("estado") == "FAIL"]
                    rows.append({
                        "Ejecución":         str(fecha_run)[:19],
                        "Plantilla":         det.get("plantilla", "—"),
                        "Archivo":           det.get("archivo", "—"),
                        "Leídos":            det.get("registros_leidos", 0),
                        "Válidos":           det.get("registros_validos", 0),
                        "Estado":            "✅" if det.get("exitosa") else "❌",
                        "Errores":           len(det.get("errores", [])),
                        "Adv.":              len(warns),
                        "Fallos validación": len(fails),
                    })

            if rows:
                st.markdown("#### Detalle por archivo")
                df_qc = pd.DataFrame(rows)
                st.dataframe(df_qc, use_container_width=True, hide_index=True, height=330)

            # ── Issues agrupados por tipo ──────────────────────────────────
            issues: list[dict] = []
            for art in ingesta_arts:
                fecha_run = art["resumen"].get("fecha", "—")
                for det in art.get("detalle", []):
                    for v in det.get("validaciones", []):
                        issues.append({
                            "Ejecución": str(fecha_run)[:10],
                            "Archivo":   det.get("archivo", "—"),
                            "Plantilla": det.get("plantilla", "—"),
                            "Tipo":      v.get("tipo", "—"),
                            "Campo":     v.get("campo", "—"),
                            "Estado":    v.get("estado", "—"),
                            "Mensaje":   v.get("mensaje", "—"),
                        })
                    for e in det.get("errores", []):
                        issues.append({
                            "Ejecución": str(fecha_run)[:10],
                            "Archivo":   det.get("archivo", "—"),
                            "Plantilla": det.get("plantilla", "—"),
                            "Tipo":      "ERROR",
                            "Campo":     "—",
                            "Estado":    "ERROR",
                            "Mensaje":   str(e),
                        })

            if issues:
                df_iss = pd.DataFrame(issues)
                fails_df = df_iss[df_iss["Estado"].isin(["FAIL", "ERROR"])]
                warns_df = df_iss[df_iss["Estado"] == "WARNING"]

                if not fails_df.empty:
                    with st.expander(f"🔴 Errores y fallos de validación ({len(fails_df)})", expanded=True):
                        st.dataframe(fails_df, use_container_width=True, hide_index=True, height=280)
                if not warns_df.empty:
                    with st.expander(f"🟡 Advertencias ({len(warns_df)})", expanded=False):
                        st.dataframe(warns_df, use_container_width=True, hide_index=True, height=280)
            else:
                st.success("Sin issues de validación registrados.")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 4 — TRAZABILIDAD
    # ═══════════════════════════════════════════════════════════════════════
    with tab_traz:
        st.markdown("#### Trazabilidad por indicador")
        st.caption(
            "Ingresa el ID de un indicador para ver su estado actual, "
            "artefactos de ingesta relacionados e histórico de reportes."
        )

        id_q = st.text_input("ID del indicador", key="to_traz_id", placeholder="Ej: 125, 3.15, PR-05")

        if id_q.strip():
            id_norm = _id_limpio(id_q.strip())

            # ── Estado en el dataset filtrado ──────────────────────────────
            df_ind = df[df["Id"].astype(str) == id_norm]
            if not df_ind.empty:
                row = df_ind.iloc[0]
                nombre = str(row.get("Indicador", "—"))
                cat    = str(row.get("Categoria",  "—"))
                bg_cat = _NIVEL_BG_EXT.get(cat, "#F5F5F5")
                fg_cat = _NIVEL_COLOR_EXT.get(cat, "#333333")
                st.markdown(
                    f"""<div style="background:{bg_cat};border:2px solid {fg_cat}44;
                        border-radius:12px;padding:0.8rem 1rem;margin-bottom:0.5rem;">
                        <b style="font-size:1.05rem;">{nombre}</b>
                        <span style="float:right;background:{fg_cat};color:white;
                              border-radius:8px;padding:0.2rem 0.7rem;font-size:0.85rem;">
                          {_NIVEL_ICON_EXT.get(cat,'')} {cat}
                        </span>
                    </div>""",
                    unsafe_allow_html=True,
                )
                ic1, ic2, ic3, ic4 = st.columns(4)
                ic1.metric("Proceso", str(row.get("Proceso", "—"))[:35])
                ic2.metric("Periodicidad", str(row.get("Periodicidad", "—")))
                _cum_raw = _to_num(row.get("Cumplimiento"))
                ic3.metric("Cumplimiento", f"{_cum_raw * 100:.1f}%" if _cum_raw is not None else "—")
                _fecha_raw = pd.to_datetime(row.get("Fecha"), errors="coerce")
                ic4.metric("Última fecha", _fecha_raw.strftime("%d/%m/%Y") if pd.notna(_fecha_raw) else "—")
            else:
                st.info(f"ID **{id_norm}** no encontrado en el dataset filtrado.")

            # ── Artefactos de ingesta relacionados ─────────────────────────
            artefactos_traz = _cargar_artefactos_qc()
            art_rel = []
            for art in artefactos_traz:
                if art.get("_tipo") == "pipeline_run":
                    continue
                fecha_run = art.get("resumen", {}).get("fecha", "—")
                for det in art.get("detalle", []):
                    plantilla = str(det.get("plantilla", "")).lower()
                    if any(kw in plantilla for kw in ["consolidado", "resultados", "indicadores", "kawak"]):
                        v_list = [
                            f"{v.get('estado','—')}: {str(v.get('mensaje',''))[:70]}"
                            for v in det.get("validaciones", [])
                        ]
                        art_rel.append({
                            "Ejecución":       str(fecha_run)[:19],
                            "Plantilla":       det.get("plantilla", "—"),
                            "Archivo":         det.get("archivo", "—"),
                            "Registros leídos": det.get("registros_leidos", 0),
                            "Válidos":          det.get("registros_validos", 0),
                            "Resultado":        "✅" if det.get("exitosa") else "❌",
                            "Validaciones":     "; ".join(v_list) if v_list else "Sin issues",
                        })

            if art_rel:
                st.markdown("#### Artefactos de ingesta (plantillas relacionadas)")
                st.dataframe(pd.DataFrame(art_rel), use_container_width=True, hide_index=True, height=240)
            else:
                st.info(
                    "No se encontraron artefactos con plantillas de consolidado. "
                    "La trazabilidad precisa requiere artefactos indexados por ID."
                )

            # ── Histórico en el dataset completo ───────────────────────────
            if not df_all.empty and "Id" in df_all.columns:
                df_hist = df_all[df_all["Id"].astype(str) == id_norm].copy()
                if not df_hist.empty:
                    st.markdown("#### Histórico de reportes del indicador")
                    if "Fecha" in df_hist.columns:
                        df_hist = df_hist.sort_values("Fecha")

                    hist_cols = [
                        c for c in ["Fecha", "Anio", "Mes", "Periodicidad", "Cumplimiento", "Categoria", "Proceso"]
                        if c in df_hist.columns
                    ]
                    dh = df_hist[hist_cols].copy()
                    if "Cumplimiento" in dh.columns:
                        dh["Cumplimiento"] = pd.to_numeric(dh["Cumplimiento"], errors="coerce").apply(
                            lambda v: f"{v * 100:.1f}%" if pd.notna(v) else "—"
                        )
                    if "Fecha" in dh.columns:
                        dh["Fecha"] = pd.to_datetime(dh["Fecha"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("—")

                    st.dataframe(dh, use_container_width=True, hide_index=True, height=300)
                else:
                    st.info(f"No hay registros históricos para el ID {id_norm}.")
        else:
            st.info("Ingresa el ID de un indicador para ver su trazabilidad.")
