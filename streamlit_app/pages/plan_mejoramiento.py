from datetime import date as _date

import pandas as pd
import plotly.express as px
import streamlit as st

from streamlit_app.services.strategic_indicators import (
    NIVEL_COLOR_EXT,
    load_cna_catalog,
    preparar_cna_con_cierre,
    load_cierres,
)

CORTE_SEMESTRAL = {
    "Junio": 6,
    "Diciembre": 12,
}


def _default_corte(anios: list[int]) -> tuple[int, str]:
    if 2025 in anios:
        return 2025, "Diciembre"
    if anios:
        return anios[-1], "Diciembre"
    return _date.today().year, "Diciembre"


def render():
    st.title("Plan de Mejoramiento")
    st.caption("Indicadores CNA con filtros dependientes por Factor y Característica + cumplimiento de cierre.")

    cierres = load_cierres()
    if cierres.empty:
        st.error("No se encontró información de cierres en Resultados Consolidados.xlsx.")
        return

    anios = sorted(pd.to_numeric(cierres["Anio"], errors="coerce").dropna().astype(int).unique().tolist())
    if not anios:
        st.error("No hay años disponibles en consolidado de cierres.")
        return

    with st.expander("🔎 Filtros", expanded=False):
        if st.button("Limpiar filtros", key="pm_cna_clear"):
            for k in [
                "pm_cna_anio", "pm_cna_mes", "pm_cna_factor", "pm_cna_caracteristica", "pm_cna_nombre",
                "_pm_cna_last_anio",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

        _anio_default, _corte_default = _default_corte(anios)
        anio = st.selectbox("Año de corte", anios, index=anios.index(_anio_default), key="pm_cna_anio")
        corte = st.selectbox(
            "Corte",
            list(CORTE_SEMESTRAL.keys()),
            index=list(CORTE_SEMESTRAL.keys()).index(_corte_default),
            key="pm_cna_corte",
        )
        mes = CORTE_SEMESTRAL[corte]

    df = preparar_cna_con_cierre(int(anio), int(mes))
    if df.empty:
        st.warning("No hay indicadores CNA (flag=1) para el corte seleccionado.")
        return

    cna_catalog = load_cna_catalog()
    factores = sorted(
        cna_catalog["Factor"].dropna().astype(str).unique().tolist()
        if not cna_catalog.empty else df["Factor"].dropna().astype(str).unique().tolist()
    )
    factor_sel = st.selectbox("Factor CNA", ["Todos"] + factores, key="pm_cna_factor")

    if not cna_catalog.empty:
        car_pool = cna_catalog if factor_sel == "Todos" else cna_catalog[cna_catalog["Factor"] == factor_sel]
        caracts = sorted(car_pool["Caracteristica"].dropna().astype(str).unique().tolist())
    else:
        df_car = df if factor_sel == "Todos" else df[df["Factor"] == factor_sel]
        caracts = sorted(df_car["Caracteristica"].dropna().astype(str).unique().tolist())

    car_sel = st.selectbox("Característica", ["Todas"] + caracts, key="pm_cna_caracteristica")
    nombre_q = st.text_input("Buscar indicador", key="pm_cna_nombre", placeholder="Texto en nombre del indicador")

    if factor_sel != "Todos":
        df = df[df["Factor"] == factor_sel]
    if car_sel != "Todas":
        df = df[df["Caracteristica"] == car_sel]
    if nombre_q.strip():
        df = df[df["Indicador"].astype(str).str.contains(nombre_q.strip(), case=False, na=False)]

    if df.empty:
        st.info("No hay registros para los filtros seleccionados.")
        return

    activos = []
    if factor_sel != "Todos":
        activos.append(f"Factor: {factor_sel}")
    if car_sel != "Todas":
        activos.append(f"Característica: {car_sel}")
    if nombre_q.strip():
        activos.append(f"Indicador contiene: {nombre_q.strip()}")
    if activos:
        st.caption("Filtros activos: " + " · ".join(activos))
    st.caption(f"Corte seleccionado: {corte} {anio}")

    total = len(df)
    con_dato = int(df["cumplimiento_pct"].notna().sum())
    prom = float(df["cumplimiento_pct"].mean()) if con_dato else 0.0
    n_fact = int(df["Factor"].nunique())
    n_car = int(df["Caracteristica"].nunique())
    total_fact_catalogo = int(cna_catalog["Factor"].nunique()) if not cna_catalog.empty else n_fact
    total_car_catalogo = int(cna_catalog["Caracteristica"].nunique()) if not cna_catalog.empty else n_car

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Indicadores CNA", total)
    k2.metric("Factores visibles", n_fact)
    k3.metric("Características visibles", n_car)
    k4.metric("Con cumplimiento", con_dato)
    k5.metric("Promedio cumplimiento", f"{prom:.1f}%")

    st.caption(
        f"Catálogo CNA: {total_fact_catalogo} factores y {total_car_catalogo} características. "
        f"Con indicadores CNA=1 en corte: {n_fact} factores y {n_car} características."
    )

    factor_palette = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel + px.colors.qualitative.Bold
    factor_list = sorted(df["Factor"].dropna().astype(str).unique().tolist())
    factor_color_map = {f: factor_palette[i % len(factor_palette)] for i, f in enumerate(factor_list)}

    r1c1, r1c2 = st.columns([1, 1])
    with r1c1:
        by_factor = (
            df.groupby("Factor", dropna=False)["cumplimiento_pct"]
            .mean().fillna(0).reset_index().sort_values("cumplimiento_pct", ascending=True)
        )
        fig_factor = px.bar(
            by_factor,
            x="cumplimiento_pct",
            y="Factor",
            orientation="h",
            title="Cumplimiento promedio por factor",
            labels={"cumplimiento_pct": "Cumplimiento (%)", "Factor": "Factor"},
            color="Factor",
            color_discrete_map=factor_color_map,
        )
        fig_factor.update_layout(margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
        st.plotly_chart(fig_factor, use_container_width=True, key="pm_factor_avg")

    with r1c2:
        niveles = df["Nivel de cumplimiento"].fillna("Pendiente de reporte").value_counts().reset_index()
        niveles.columns = ["Nivel", "Cantidad"]
        fig_niv = px.pie(
            niveles,
            names="Nivel",
            values="Cantidad",
            title="Distribución de niveles",
            color="Nivel",
            color_discrete_map=NIVEL_COLOR_EXT,
            hole=0.45,
        )
        fig_niv.update_layout(margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_niv, use_container_width=True, key="pm_niveles_pie")

    st.markdown("### Gráficas adicionales")
    r2c1, r2c2 = st.columns([1, 1])
    with r2c1:
        df_stack = (
            df.groupby(["Factor", "Nivel de cumplimiento"], dropna=False)
            .size().reset_index(name="Cantidad")
        )
        fig_stack = px.bar(
            df_stack,
            x="Factor",
            y="Cantidad",
            color="Nivel de cumplimiento",
            title="Indicadores por factor y nivel",
            barmode="stack",
            color_discrete_map=NIVEL_COLOR_EXT,
        )
        fig_stack.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_title="Factor")
        st.plotly_chart(fig_stack, use_container_width=True, key="pm_factor_nivel_stack")

    with r2c2:
        df_tree = df[["Factor", "Caracteristica"]].copy()
        df_tree["Factor"] = df_tree["Factor"].astype(str).str.strip()
        df_tree["Caracteristica"] = df_tree["Caracteristica"].astype(str).str.strip()
        df_tree = df_tree[
            df_tree["Factor"].ne("")
            & df_tree["Caracteristica"].ne("")
            & ~df_tree["Factor"].isna()
            & ~df_tree["Caracteristica"].isna()
        ]
        df_tree = df_tree.groupby(["Factor", "Caracteristica"], as_index=False).size().rename(columns={"size": "Cantidad"})

        if df_tree.empty:
            st.info("No hay datos válidos para el treemap de factor/característica.")
        else:
            fig_tree = px.treemap(
                df_tree,
                path=["Factor", "Caracteristica"],
                values="Cantidad",
                title="Mapa de indicadores por factor y característica",
                color="Factor",
                color_discrete_map=factor_color_map,
            )
            fig_tree.update_layout(margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_tree, use_container_width=True, key="pm_factor_car_tree")

    st.markdown("### Indicadores CNA")
    tabla = df[[
        "Id", "Indicador", "Factor", "Caracteristica", "cumplimiento_pct", "Nivel de cumplimiento", "Anio", "Mes", "Fecha",
    ]].copy()
    tabla = tabla.rename(columns={
        "cumplimiento_pct": "Cumplimiento (%)",
        "Nivel de cumplimiento": "Nivel",
        "Anio": "Año cierre",
        "Mes": "Mes cierre",
        "Caracteristica": "Característica",
    })
    tabla["Cumplimiento (%)"] = pd.to_numeric(tabla["Cumplimiento (%)"], errors="coerce").round(1)
    st.dataframe(tabla.sort_values(["Factor", "Característica", "Id"], na_position="last"), use_container_width=True, hide_index=True)
