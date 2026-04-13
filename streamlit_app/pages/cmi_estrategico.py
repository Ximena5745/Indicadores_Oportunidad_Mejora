from datetime import date as _date
import unicodedata

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from streamlit_app.services.strategic_indicators import (
    NIVEL_COLOR_EXT,
    load_pdi_catalog,
    preparar_pdi_con_cierre,
    load_cierres,
)
from streamlit_app.styles.design_system import get_line_color

CORTE_SEMESTRAL = {
    "Junio": 6,
    "Diciembre": 12,
}

LINEA_COLORS = {
    "Expansión": "#FBAF17",
    "Transformación organizacional": "#42F2F2",
    "Calidad": "#EC0677",
    "Experiencia": "#1FB2DE",
    "Sostenibilidad": "#A6CE38",
    "Educación para toda la vida": "#0F385A",
}


def _linea_color(linea: str) -> str:
    txt = str(linea or "").strip().lower()
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(ch for ch in txt if unicodedata.category(ch) != "Mn")
    if "expansi" in txt:
        return "#FBAF17"
    if "transform" in txt:
        return "#42F2F2"
    if "calidad" in txt:
        return "#EC0677"
    if "experien" in txt:
        return "#1FB2DE"
    if "sostenib" in txt:
        return "#A6CE38"
    if "educaci" in txt or "toda la vida" in txt:
        return "#0F385A"
    # Fallback al sistema de diseño (si existe mapeo global)
    return get_line_color(linea)


# ─── Pesos por línea estratégica para el ISI ─────────────────────────────────
# Ajustables según prioridad institucional; suman 1.0
_PESOS_LINEA: dict[str, float] = {
    "expansion":                      0.20,
    "transformacion organizacional":   0.18,
    "calidad":                         0.22,
    "experiencia":                     0.15,
    "sostenibilidad":                  0.15,
    "educacion para toda la vida":     0.10,
}
_PESO_DEFAULT = 1.0  # peso neutro si la línea no está en el mapa

# Bonus por sobrecumplimiento y penalización por peligro (puntos sobre 100)
_BONUS_SOBRE = 5.0
_PEN_PELIGRO = -8.0
_PEN_ALERTA  = -3.0


def _nm_linea(s: str) -> str:
    s = str(s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s


def _calcular_isi(df: pd.DataFrame) -> tuple[float, pd.DataFrame, pd.DataFrame]:
    """Calcula el Índice de Salud Institucional (0-100).

    Retorna (isi, df_por_linea, df_por_objetivo).
    Fórmula:
      1. Cumplimiento promedio ponderado por línea (escala 0-100)
      2. Ajustes: bonus por sobrecumplimiento, penalización por peligro/alerta
      3. Clip [0, 100]
    """
    if df.empty or "cumplimiento_pct" not in df.columns:
        return 0.0, pd.DataFrame(), pd.DataFrame()

    df_v = df[df["cumplimiento_pct"].notna()].copy()
    if df_v.empty:
        return 0.0, pd.DataFrame(), pd.DataFrame()

    # Peso por fila según su línea
    df_v["_peso"] = df_v["Linea"].apply(
        lambda l: _PESOS_LINEA.get(_nm_linea(str(l)), _PESO_DEFAULT / len(_PESOS_LINEA))
    )

    # Promedio ponderado global
    denom = df_v["_peso"].sum()
    if denom == 0:
        return 0.0, pd.DataFrame(), pd.DataFrame()
    base_score = float((df_v["cumplimiento_pct"] * df_v["_peso"]).sum() / denom)

    # Ajustes por distribución de niveles
    n_total = len(df_v)
    n_sobre  = int((df_v["Nivel de cumplimiento"] == "Sobrecumplimiento").sum())
    n_peligro = int((df_v["Nivel de cumplimiento"] == "Peligro").sum())
    n_alerta  = int((df_v["Nivel de cumplimiento"] == "Alerta").sum())
    ajuste = (
        (n_sobre  / n_total) * _BONUS_SOBRE +
        (n_peligro / n_total) * _PEN_PELIGRO +
        (n_alerta  / n_total) * _PEN_ALERTA
    ) if n_total else 0.0

    isi = float(min(max(base_score + ajuste, 0.0), 100.0))

    # Por línea
    por_linea = (
        df_v.groupby("Linea", dropna=False)
        .agg(
            indicadores=("cumplimiento_pct", "count"),
            cumplimiento=("cumplimiento_pct", "mean"),
            peligro=("Nivel de cumplimiento", lambda x: (x == "Peligro").sum()),
            alerta=("Nivel de cumplimiento",  lambda x: (x == "Alerta").sum()),
        )
        .reset_index()
    )
    por_linea["cumplimiento"] = por_linea["cumplimiento"].round(1)

    # Por objetivo
    por_obj = (
        df_v.groupby(["Linea", "Objetivo"], dropna=False)
        .agg(
            indicadores=("cumplimiento_pct", "count"),
            cumplimiento=("cumplimiento_pct", "mean"),
            peligro=("Nivel de cumplimiento", lambda x: (x == "Peligro").sum()),
        )
        .reset_index()
    )
    por_obj["cumplimiento"] = por_obj["cumplimiento"].round(1)

    return isi, por_linea, por_obj


def _fig_gauge_isi(isi: float) -> go.Figure:
    """Gauge semicircular para el Índice de Salud Institucional."""
    if isi >= 95:
        color = "#28a745"
        label = "Excelente"
    elif isi >= 80:
        color = "#a8d08d"
        label = "Bueno"
    elif isi >= 65:
        color = "#ffc107"
        label = "En riesgo"
    else:
        color = "#dc3545"
        label = "Crítico"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=isi,
        number={"suffix": "/100", "font": {"size": 32, "color": "#0f385a"}},
        delta={"reference": 80, "increasing": {"color": "#28a745"}, "decreasing": {"color": "#dc3545"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#9ba8b7"},
            "bar": {"color": color, "thickness": 0.30},
            "bgcolor": "white",
            "borderwidth": 2,
            "bordercolor": "#dce6f2",
            "steps": [
                {"range": [0, 65],  "color": "#FFCDD2"},
                {"range": [65, 80], "color": "#FEF9E7"},
                {"range": [80, 95], "color": "#E8F5E9"},
                {"range": [95, 100], "color": "#DDEEFF"},
            ],
            "threshold": {"line": {"color": "#0f385a", "width": 4}, "thickness": 0.9, "value": 80},
        },
        title={"text": f"Índice de Salud Institucional<br><span style='font-size:0.85rem;color:{color}'>{label}</span>",
               "font": {"size": 15, "color": "#0f385a"}},
    ))
    fig.update_layout(
        height=300,
        margin=dict(t=60, b=10, l=30, r=30),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _fig_treemap_pdi(df: pd.DataFrame) -> go.Figure:
    """Treemap jerárquico: PDI → Línea → Objetivo → Indicador.

    Color por cumplimiento_pct; tamaño uniforme (1 por indicador).
    """
    req = {"Linea", "Objetivo", "Id", "cumplimiento_pct"}
    if not req.issubset(df.columns) or df.empty:
        return go.Figure()

    df_t = df.copy()
    df_t["Indicador_label"] = df_t.apply(
        lambda r: f"{r['Id']}: {str(r.get('Indicador',''))[:45]}", axis=1
    )
    df_t["cumplimiento_pct"] = pd.to_numeric(df_t["cumplimiento_pct"], errors="coerce").fillna(0)
    df_t["_size"] = 1

    # Etiqueta de texto con % para hover
    df_t["_label_hover"] = df_t["cumplimiento_pct"].apply(lambda v: f"{v:.1f}%")

    fig = px.treemap(
        df_t,
        path=[px.Constant("PDI"), "Linea", "Objetivo", "Indicador_label"],
        values="_size",
        color="cumplimiento_pct",
        color_continuous_scale=[
            [0.00, "#FFCDD2"],  # peligro
            [0.75, "#FEF9E7"],  # alerta
            [0.95, "#E8F5E9"],  # cumplimiento
            [1.00, "#D0E4FF"],  # sobrecumplimiento
        ],
        range_color=[0, 130],
        custom_data=["_label_hover", "Nivel de cumplimiento"],
        title="Árbol de Objetivos PDI — Línea → Objetivo → Indicador",
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Cumplimiento: %{customdata[0]}<br>Nivel: %{customdata[1]}<extra></extra>",
        textinfo="label",
    )
    fig.update_layout(
        height=520,
        margin=dict(t=50, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(
            title="Cumpl. %",
            tickvals=[0, 80, 100, 130],
            ticktext=["0%", "80%", "100%", "130%"],
        ),
    )
    return fig


def _default_corte(anios: list[int]) -> tuple[int, str]:
    if 2025 in anios:
        return 2025, "Diciembre"
    if anios:
        return anios[-1], "Diciembre"
    return _date.today().year, "Diciembre"


def render():
    st.title("CMI Estratégico")
    st.caption("Indicadores del Plan Estratégico (PDI) con cumplimiento de cierre y niveles institucionales.")

    cierres = load_cierres()
    if cierres.empty:
        st.error("No se encontró información de cierres en Resultados Consolidados.xlsx.")
        return

    anios = sorted(pd.to_numeric(cierres["Anio"], errors="coerce").dropna().astype(int).unique().tolist())
    if not anios:
        st.error("No hay años disponibles en consolidado de cierres.")
        return

    with st.expander("🔎 Filtros", expanded=False):
        if st.button("Limpiar filtros", key="cmi_pdi_clear"):
            for k in [
                "cmi_pdi_anio", "cmi_pdi_mes", "cmi_pdi_linea", "cmi_pdi_objetivo", "cmi_pdi_nombre",
                "_cmi_pdi_last_anio",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

        _anio_default, _corte_default = _default_corte(anios)
        _fc1, _fc2 = st.columns(2)
        with _fc1:
            anio = st.selectbox("Año de corte", anios, index=anios.index(_anio_default), key="cmi_pdi_anio")
        with _fc2:
            corte = st.selectbox(
                "Corte semestral",
                list(CORTE_SEMESTRAL.keys()),
                index=list(CORTE_SEMESTRAL.keys()).index(_corte_default),
                key="cmi_pdi_corte",
            )
        mes = CORTE_SEMESTRAL[corte]

    df = preparar_pdi_con_cierre(int(anio), int(mes))
    if df.empty:
        st.warning("No hay indicadores PDI (flag=1) para el corte seleccionado.")
        return

    pdi_catalog = load_pdi_catalog()
    lineas = sorted(
        pdi_catalog["Linea"].dropna().astype(str).unique().tolist()
        if not pdi_catalog.empty else df["Linea"].dropna().astype(str).unique().tolist()
    )
    _ff1, _ff2, _ff3 = st.columns([1, 2, 2])
    with _ff1:
        linea_sel = st.selectbox("Línea estratégica", ["Todas"] + lineas, key="cmi_pdi_linea")

    if not pdi_catalog.empty:
        obj_pool = pdi_catalog if linea_sel == "Todas" else pdi_catalog[pdi_catalog["Linea"] == linea_sel]
        objetivos = sorted(obj_pool["Objetivo"].dropna().astype(str).unique().tolist())
    else:
        df_obj = df if linea_sel == "Todas" else df[df["Linea"] == linea_sel]
        objetivos = sorted(df_obj["Objetivo"].dropna().astype(str).unique().tolist())

    with _ff2:
        objetivo_sel = st.selectbox("Objetivo estratégico", ["Todos"] + objetivos, key="cmi_pdi_objetivo")
    with _ff3:
        nombre_q = st.text_input("Buscar indicador", key="cmi_pdi_nombre", placeholder="Texto en nombre del indicador")

    if linea_sel != "Todas":
        df = df[df["Linea"] == linea_sel]
    if objetivo_sel != "Todos":
        df = df[df["Objetivo"] == objetivo_sel]
    if nombre_q.strip():
        df = df[df["Indicador"].astype(str).str.contains(nombre_q.strip(), case=False, na=False)]

    if df.empty:
        st.info("No hay registros para los filtros seleccionados.")
        return

    activos = []
    if linea_sel != "Todas":
        activos.append(f"Línea: {linea_sel}")
    if objetivo_sel != "Todos":
        activos.append(f"Objetivo: {objetivo_sel}")
    if nombre_q.strip():
        activos.append(f"Indicador contiene: {nombre_q.strip()}")
    if activos:
        st.caption("Filtros activos: " + " · ".join(activos))

    total = len(df)
    con_dato = int(df["cumplimiento_pct"].notna().sum())
    promedio = float(df["cumplimiento_pct"].mean()) if con_dato else 0.0
    top_nivel = df["Nivel de cumplimiento"].value_counts().idxmax() if total else "Sin dato"
    n_lineas_vis = int(df["Linea"].nunique())
    n_obj_vis = int(df["Objetivo"].nunique())
    n_lineas_cat = int(pdi_catalog["Linea"].nunique()) if not pdi_catalog.empty else n_lineas_vis
    n_obj_cat = int(pdi_catalog["Objetivo"].nunique()) if not pdi_catalog.empty else n_obj_vis

    # ── Índice de Salud Institucional ──────────────────────────────────────
    isi, por_linea, por_obj = _calcular_isi(df)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Indicadores PDI", total)
    k2.metric("Con cumplimiento", con_dato)
    k3.metric("Promedio cumplimiento", f"{promedio:.1f}%")
    k4.metric("Nivel predominante", top_nivel)
    k5.metric(
        "🏥 Salud institucional",
        f"{isi:.1f}/100",
        delta=f"{isi - 80:+.1f} vs umbral 80",
        delta_color="normal",
    )

    st.caption(f"Corte seleccionado: {corte} {anio}")
    st.caption(
        f"Catálogo PDI: {n_lineas_cat} líneas y {n_obj_cat} objetivos. "
        f"Con indicadores Plan Estratégico=1 en corte: {n_lineas_vis} líneas y {n_obj_vis} objetivos."
    )

    # ── Panel ISI + tabla por línea ────────────────────────────────────────
    isi_c1, isi_c2 = st.columns([1, 2])
    with isi_c1:
        st.plotly_chart(_fig_gauge_isi(isi), use_container_width=True, key="cmi_isi_gauge")
    with isi_c2:
        if not por_linea.empty:
            st.markdown("**Salud por línea estratégica**")
            _pl = por_linea.copy()
            _pl.columns = ["Línea", "Indicadores", "Cumpl. promedio (%)", "En Peligro", "En Alerta"]
            _pl["Cumpl. promedio (%)"] = _pl["Cumpl. promedio (%)"].round(1)
            st.dataframe(_pl, use_container_width=True, hide_index=True, height=240)

    if not por_obj.empty:
        with st.expander("Detalle por objetivo estratégico", expanded=False):
            _po = por_obj.copy()
            _po.columns = ["Línea", "Objetivo", "Indicadores", "Cumpl. promedio (%)", "En Peligro"]
            _po["Cumpl. promedio (%)"] = _po["Cumpl. promedio (%)"].round(1)
            _po = _po.sort_values(["Línea", "Cumpl. promedio (%)"])
            st.dataframe(_po, use_container_width=True, hide_index=True, height=320)

    st.markdown("---")

    c1, c2 = st.columns([1, 1])
    with c1:
        by_linea = (
            df.groupby("Linea", dropna=False)["cumplimiento_pct"]
            .mean().fillna(0).reset_index().sort_values("cumplimiento_pct", ascending=True)
        )
        by_linea["Linea"] = by_linea["Linea"].astype(str)
        _linea_map = {lin: _linea_color(lin) for lin in by_linea["Linea"].tolist()}
        fig_linea = px.bar(
            by_linea,
            x="cumplimiento_pct",
            y="Linea",
            orientation="h",
            title="Cumplimiento promedio por línea estratégica",
            labels={"cumplimiento_pct": "Cumplimiento (%)", "Linea": "Línea"},
            color="Linea",
            color_discrete_map=_linea_map,
        )
        fig_linea.update_layout(margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
        st.plotly_chart(fig_linea, use_container_width=True, key="cmi_pdi_linea_bar")

    with c2:
        niveles = df["Nivel de cumplimiento"].fillna("Pendiente de reporte").value_counts().reset_index()
        niveles.columns = ["Nivel", "Cantidad"]
        fig_niv = px.pie(
            niveles,
            names="Nivel",
            values="Cantidad",
            title="Distribución por nivel",
            color="Nivel",
            color_discrete_map=NIVEL_COLOR_EXT,
            hole=0.45,
        )
        fig_niv.update_layout(margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_niv, use_container_width=True, key="cmi_pdi_nivel_pie")

    st.markdown("### Indicadores PDI")
    st.markdown("### Indicadores PDI")
    _cols_pdi = ["Id", "Indicador", "Linea", "Objetivo", "cumplimiento_pct", "Nivel de cumplimiento"]
    if "Meta" in df.columns:
        _cols_pdi.append("Meta")
    if "Ejecucion" in df.columns:
        _cols_pdi.append("Ejecucion")
    if "Sentido" in df.columns:
        _cols_pdi.append("Sentido")
    _cols_pdi += ["Anio", "Mes", "Fecha"]
    tabla = df[[c for c in _cols_pdi if c in df.columns]].copy()
    tabla = tabla.rename(columns={
        "cumplimiento_pct": "Cumplimiento (%)",
        "Nivel de cumplimiento": "Nivel",
        "Anio": "Año cierre",
        "Mes": "Mes cierre",
        "Meta": "Meta",
        "Ejecucion": "Ejecución",
    })
    tabla["Cumplimiento (%)"] = pd.to_numeric(tabla["Cumplimiento (%)"], errors="coerce").round(1)
    if "Meta" in tabla.columns:
        tabla["Meta"] = pd.to_numeric(tabla["Meta"], errors="coerce").round(2)
    if "Ejecución" in tabla.columns:
        tabla["Ejecución"] = pd.to_numeric(tabla["Ejecución"], errors="coerce").round(2)
    tabla = tabla.sort_values(["Linea", "Objetivo", "Id"] if all(c in tabla.columns for c in ["Linea", "Objetivo"]) else ["Id"], na_position="last")

    # Color de fondo por Nivel en columna Nivel
    _NIVEL_BG_CMI = {
        "Peligro": "#FFCDD2", "Alerta": "#FEF3D0", "Cumplimiento": "#E8F5E9",
        "Sobrecumplimiento": "#D0E4FF", "No aplica": "#ECEFF1", "Pendiente de reporte": "#F5F5F5",
    }
    _NIVEL_ICONS_CMI = {
        "Peligro": "🔴", "Alerta": "🟡", "Cumplimiento": "🟢",
        "Sobrecumplimiento": "🔵", "No aplica": "⚫", "Pendiente de reporte": "⚪",
    }
    if "Nivel" in tabla.columns:
        tabla["Nivel"] = tabla["Nivel"].apply(
            lambda n: f'{_NIVEL_ICONS_CMI.get(str(n), "")} {n}' if pd.notna(n) else n
        )
    if "Linea" in tabla.columns:
        tabla["Color Línea"] = tabla["Linea"].apply(lambda l: _linea_color(str(l or "")))

    _cfg_pdi = {
        "Id":        st.column_config.TextColumn("ID",          width="small"),
        "Indicador": st.column_config.TextColumn("Indicador",   width="large"),
        "Linea":     st.column_config.TextColumn("Línea",       width="medium"),
        "Objetivo":  st.column_config.TextColumn("Objetivo",    width="large"),
        "Nivel":     st.column_config.TextColumn("Nivel",       width="medium"),
        "Cumplimiento (%)": st.column_config.NumberColumn("Cumplimiento %", format="%.1f", width="small"),
        "Meta":      st.column_config.NumberColumn("Meta",      format="%.2f", width="small"),
        "Ejecución": st.column_config.NumberColumn("Ejecución", format="%.2f", width="small"),
        "Sentido":   st.column_config.TextColumn("Sentido",     width="small"),
        "Año cierre": st.column_config.NumberColumn("Año",      format="%d",   width="small"),
        "Mes cierre": st.column_config.NumberColumn("Mes",      format="%d",   width="small"),
        "Fecha":     st.column_config.DatetimeColumn("Fecha",   width="small"),
    }
    # Renderizar indicadores PDI por Línea: título con color y tarjetas por Objetivo
    def _render_indicator_table(df_obj: pd.DataFrame) -> str:
        """Retorna HTML de una tabla compacta con columnas Indicador, Meta, Ejecución, Cumplimiento."""
        cols = [c for c in ["Indicador", "Meta", "Ejecución", "Cumplimiento (%)"] if c in df_obj.columns]
        if df_obj.empty:
            return "<div style='padding:8px'>No hay indicadores para este objetivo.</div>"
        html = ["<table style='width:100%;border-collapse:collapse;font-size:0.9rem'>"]
        # header
        html.append("<tr style='background:#e9f7fb;color:#033;'><th style='padding:8px;border:1px solid #d0e9ef;text-align:left'>Indicador</th>")
        for c in cols[1:]:
            html.append(f"<th style='padding:8px;border:1px solid #d0e9ef;text-align:center'>{c}</th>")
        html.append("</tr>")
        # rows
        for _, r in df_obj.iterrows():
            html.append("<tr>")
            html.append(f"<td style='padding:8px;border:1px solid #eef7fb'>{_escape(str(r.get('Indicador','')))}</td>")
            for c in cols[1:]:
                val = r.get(c, "")
                display = f"{val}" if pd.notna(val) else ""
                align = "center"
                html.append(f"<td style='padding:8px;border:1px solid #eef7fb;text-align:{align}'>{display}</td>")
            html.append("</tr>")
        html.append("</table>")
        return "".join(html)

    # Ordenar líneas según catálogo (asegurar las seis líneas ordenadas)
    ordered_lineas = [l for l in LINEA_COLORS.keys() if l in tabla['Linea'].unique()] + [l for l in tabla['Linea'].unique() if l not in LINEA_COLORS.keys()]
    from html import escape as _escape

    for linea in ordered_lineas:
        color = LINEA_COLORS.get(linea, _linea_color(linea))
        st.markdown(f"<div style='background:{color};padding:14px;border-radius:6px;margin-top:12px;margin-bottom:8px'><h3 style='color:#ffffff;margin:0;padding:0'>{_escape(linea)}</h3></div>", unsafe_allow_html=True)
        df_line = tabla[tabla['Linea'] == linea].copy()
        if df_line.empty:
            st.info(f"No hay indicadores PDI para la línea {linea} en el corte seleccionado.")
            continue
        # Agrupar por Objetivo y renderizar tarjetas en dos columnas
        objetivos = df_line['Objetivo'].fillna('Sin objetivo').unique().tolist()
        cols_iter = iter(objetivos)
        while True:
            try:
                o1 = next(cols_iter)
            except StopIteration:
                break
            o2 = None
            try:
                o2 = next(cols_iter)
            except StopIteration:
                o2 = None
            c1, c2 = st.columns([1,1])
            with c1:
                df_o1 = df_line[df_line['Objetivo'] == o1]
                st.markdown(f"<div style='background:#f2fbfb;border-radius:6px;padding:8px'><strong>{_escape(str(o1))}</strong></div>", unsafe_allow_html=True)
                st.markdown(_render_indicator_table(df_o1), unsafe_allow_html=True)
            with c2:
                if o2:
                    df_o2 = df_line[df_line['Objetivo'] == o2]
                    st.markdown(f"<div style='background:#f2fbfb;border-radius:6px;padding:8px'><strong>{_escape(str(o2))}</strong></div>", unsafe_allow_html=True)
                    st.markdown(_render_indicator_table(df_o2), unsafe_allow_html=True)
        # separación entre líneas
        st.markdown("<br>", unsafe_allow_html=True)
    # Renderizar indicadores PDI por Línea: título con color y tarjetas por Objetivo
    def _render_indicator_table(df_obj: pd.DataFrame) -> str:
        """Retorna HTML de una tabla compacta con columnas Indicador, Meta, Ejecución, Cumplimiento."""
        cols = [c for c in ["Indicador", "Meta", "Ejecución", "Cumplimiento (%)"] if c in df_obj.columns]
        if df_obj.empty:
            return "<div style='padding:8px'>No hay indicadores para este objetivo.</div>"
        html = ["<table style='width:100%;border-collapse:collapse;font-size:0.9rem'>"]
        # header
        html.append("<tr style='background:#e9f7fb;color:#033;'><th style='padding:8px;border:1px solid #d0e9ef;text-align:left'>Indicador</th>")
        for c in cols[1:]:
            html.append(f"<th style='padding:8px;border:1px solid #d0e9ef;text-align:center'>{c}</th>")
        html.append("</tr>")
        # rows
        for _, r in df_obj.iterrows():
            html.append("<tr>")
            html.append(f"<td style='padding:8px;border:1px solid #eef7fb'>{_escape(str(r.get('Indicador','')))}</td>")
            for c in cols[1:]:
                val = r.get(c, "")
                display = f"{val}" if pd.notna(val) else ""
                align = "center"
                html.append(f"<td style='padding:8px;border:1px solid #eef7fb;text-align:{align}'>{display}</td>")
            html.append("</tr>")
        html.append("</table>")
        return "".join(html)

    # Ordenar líneas según catálogo (asegurar las seis líneas ordenadas)
    ordered_lineas = [l for l in LINEA_COLORS.keys() if l in tabla['Linea'].unique()] + [l for l in tabla['Linea'].unique() if l not in LINEA_COLORS.keys()]
    from html import escape as _escape

    for linea in ordered_lineas:
        color = LINEA_COLORS.get(linea, _linea_color(linea))
        st.markdown(f"<div style='background:{color};padding:14px;border-radius:6px;margin-top:12px;margin-bottom:8px'><h3 style='color:#ffffff;margin:0;padding:0'>{_escape(linea)}</h3></div>", unsafe_allow_html=True)
        df_line = tabla[tabla['Linea'] == linea].copy()
        if df_line.empty:
            st.info(f"No hay indicadores PDI para la línea {linea} en el corte seleccionado.")
            continue
        # Agrupar por Objetivo y renderizar tarjetas en dos columnas
        objetivos = df_line['Objetivo'].fillna('Sin objetivo').unique().tolist()
        cols_iter = iter(objetivos)
        while True:
            try:
                o1 = next(cols_iter)
            except StopIteration:
                break
            o2 = None
            try:
                o2 = next(cols_iter)
            except StopIteration:
                o2 = None
            c1, c2 = st.columns([1,1])
            with c1:
                df_o1 = df_line[df_line['Objetivo'] == o1]
                st.markdown(f"<div style='background:#f2fbfb;border-radius:6px;padding:8px'><strong>{_escape(str(o1))}</strong></div>", unsafe_allow_html=True)
                st.markdown(_render_indicator_table(df_o1), unsafe_allow_html=True)
            with c2:
                if o2:
                    df_o2 = df_line[df_line['Objetivo'] == o2]
                    st.markdown(f"<div style='background:#f2fbfb;border-radius:6px;padding:8px'><strong>{_escape(str(o2))}</strong></div>", unsafe_allow_html=True)
                    st.markdown(_render_indicator_table(df_o2), unsafe_allow_html=True)
        # separación entre líneas
        st.markdown("<br>", unsafe_allow_html=True)

