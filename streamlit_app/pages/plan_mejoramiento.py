from datetime import date as _date

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from ..services.data_loader import cargar_acciones_mejora
    from ..services.strategic_indicators import (
        NIVEL_COLOR_EXT,
        load_cna_catalog,
        preparar_cna_con_cierre,
        load_cierres,
    )
except (ImportError, ValueError):
    from services.data_loader import cargar_acciones_mejora
    from services.strategic_indicators import (
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
        _pfc1, _pfc2 = st.columns(2)
        with _pfc1:
            anio = st.selectbox("Año de corte", anios, index=anios.index(_anio_default), key="pm_cna_anio")
        with _pfc2:
            corte = st.selectbox(
                "Corte semestral",
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
    _pff1, _pff2, _pff3 = st.columns([1, 2, 2])
    with _pff1:
        factor_sel = st.selectbox("Factor CNA", ["Todos"] + factores, key="pm_cna_factor")

    if not cna_catalog.empty:
        car_pool = cna_catalog if factor_sel == "Todos" else cna_catalog[cna_catalog["Factor"] == factor_sel]
        caracts = sorted(car_pool["Caracteristica"].dropna().astype(str).unique().tolist())
    else:
        df_car = df if factor_sel == "Todos" else df[df["Factor"] == factor_sel]
        caracts = sorted(df_car["Caracteristica"].dropna().astype(str).unique().tolist())

    with _pff2:
        car_sel = st.selectbox("Característica", ["Todas"] + caracts, key="pm_cna_caracteristica")
    with _pff3:
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
        try:
            from streamlit_app.components.renderers import render_echarts
            def _option_factor_bar(df_by_factor, color_map):
                labels = df_by_factor['Factor'].astype(str).tolist()
                vals = [float(v) for v in df_by_factor['cumplimiento_pct'].tolist()]
                data = [{"value": v, "name": n, "itemStyle": {"color": color_map.get(n, '#888')}} for n, v in zip(labels, vals)]
                option = {
                    "tooltip": {"trigger": "item"},
                    "xAxis": {"type": "value"},
                    "yAxis": {"type": "category", "data": labels[::-1]},
                    "series": [{"type": "bar", "data": [d['value'] for d in data[::-1]], "itemStyle": {}}],
                }
                # attach colors per bar via visualMap workaround (simpler: itemStyle per data in series not supported here),
                # we instead return data and let render_echarts render basic bars with default colors
                return {"option": option, "height": 300}

            opt = _option_factor_bar(by_factor, factor_color_map)
            if opt and opt.get('option'):
                render_echarts(opt['option'], height=opt.get('height', 300))
            else:
                st.plotly_chart(fig_factor, use_container_width=True, key="pm_factor_avg")
        except Exception:
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
        try:
            from streamlit_app.components.renderers import render_echarts
            def _option_pie_from_counts(df_counts):
                labels = df_counts['Nivel'].astype(str).tolist()
                vals = [int(v) for v in df_counts['Cantidad'].tolist()]
                option = {"tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
                          "legend": {"bottom": 0},
                          "series": [{"type": "pie", "radius": ["40%","65%"], "data": [{"name": l, "value": v} for l, v in zip(labels, vals)]}]}
                return {"option": option, "height": 300}

            opt = _option_pie_from_counts(niveles)
            if opt and opt.get('option'):
                render_echarts(opt['option'], height=opt.get('height', 300))
            else:
                st.plotly_chart(fig_niv, use_container_width=True, key="pm_niveles_pie")
        except Exception:
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
        try:
            from streamlit_app.components.renderers import render_echarts
            def _option_stack(df_stack):
                factors = sorted(df_stack['Factor'].astype(str).unique().tolist())
                niveles = sorted(df_stack['Nivel de cumplimiento'].astype(str).unique().tolist())
                series = []
                for niv in niveles:
                    vals = []
                    for f in factors:
                        row = df_stack[(df_stack['Factor'] == f) & (df_stack['Nivel de cumplimiento'] == niv)]
                        vals.append(int(row['Cantidad'].sum()) if not row.empty else 0)
                    series.append({"name": niv, "type": "bar", "stack": "total", "data": vals})
                option = {"tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                          "legend": {"bottom": 0},
                          "xAxis": {"type": "category", "data": factors},
                          "yAxis": {"type": "value"},
                          "series": series}
                return {"option": option, "height": 360}

            opt = _option_stack(df_stack)
            if opt and opt.get('option'):
                render_echarts(opt['option'], height=opt.get('height', 360))
            else:
                st.plotly_chart(fig_stack, use_container_width=True, key="pm_factor_nivel_stack")
        except Exception:
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
            try:
                from streamlit_app.components.renderers import render_echarts
                # construir estructura anidada para ECharts treemap
                tree_data = []
                for f, grp in df_tree.groupby('Factor'):
                    children = []
                    for _, r in grp.iterrows():
                        children.append({"name": r['Caracteristica'], "value": int(r['Cantidad']), "itemStyle": {"color": factor_color_map.get(f)}})
                    tree_data.append({"name": f, "children": children})
                option = {"series": [{"type": "treemap", "data": tree_data}]}
                render_echarts(option, height=360)
            except Exception:
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
    _cols_cna = ["Id", "Indicador", "Factor", "Caracteristica", "cumplimiento_pct", "Nivel de cumplimiento"]
    if "Meta" in df.columns:
        _cols_cna.append("Meta")
    if "Ejecucion" in df.columns:
        _cols_cna.append("Ejecucion")
    if "Sentido" in df.columns:
        _cols_cna.append("Sentido")
    _cols_cna += ["Anio", "Mes", "Fecha"]
    tabla = df[[c for c in _cols_cna if c in df.columns]].copy()
    tabla = tabla.rename(columns={
        "cumplimiento_pct": "Cumplimiento (%)",
        "Nivel de cumplimiento": "Nivel",
        "Anio": "Año cierre",
        "Mes": "Mes cierre",
        "Caracteristica": "Característica",
        "Meta": "Meta",
        "Ejecucion": "Ejecución",
    })
    tabla["Cumplimiento (%)"] = pd.to_numeric(tabla["Cumplimiento (%)"], errors="coerce").round(1)
    if "Meta" in tabla.columns:
        tabla["Meta"] = pd.to_numeric(tabla["Meta"], errors="coerce").round(2)
    if "Ejecución" in tabla.columns:
        tabla["Ejecución"] = pd.to_numeric(tabla["Ejecución"], errors="coerce").round(2)
    _NIVEL_ICONS_CNA = {
        "Peligro": "🔴", "Alerta": "🟡", "Cumplimiento": "🟢",
        "Sobrecumplimiento": "🔵", "No aplica": "⚫", "Pendiente de reporte": "⚪",
    }
    if "Nivel" in tabla.columns:
        tabla["Nivel"] = tabla["Nivel"].apply(
            lambda n: f'{_NIVEL_ICONS_CNA.get(str(n), "")} {n}' if pd.notna(n) else n
        )
    _sort_cols = [c for c in ["Factor", "Característica", "Id"] if c in tabla.columns]
    tabla = tabla.sort_values(_sort_cols, na_position="last")
    _cfg_cna = {
        "Id":              st.column_config.TextColumn("ID",          width="small"),
        "Indicador":       st.column_config.TextColumn("Indicador",   width="large"),
        "Factor":          st.column_config.TextColumn("Factor",      width="medium"),
        "Característica":  st.column_config.TextColumn("Característica", width="medium"),
        "Nivel":           st.column_config.TextColumn("Nivel",       width="medium"),
        "Cumplimiento (%)": st.column_config.NumberColumn("Cumplimiento %", format="%.1f", width="small"),
        "Meta":            st.column_config.NumberColumn("Meta",      format="%.2f", width="small"),
        "Ejecución":       st.column_config.NumberColumn("Ejecución", format="%.2f", width="small"),
        "Sentido":         st.column_config.TextColumn("Sentido",     width="small"),
        "Año cierre":      st.column_config.NumberColumn("Año",       format="%d",   width="small"),
        "Mes cierre":      st.column_config.NumberColumn("Mes",       format="%d",   width="small"),
        "Fecha":           st.column_config.DatetimeColumn("Fecha",   width="small"),
    }
    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True,
        column_config={k: v for k, v in _cfg_cna.items() if k in tabla.columns},
    )

    # ── Acciones de mejora vinculadas a indicadores CNA ───────────────────
    st.markdown("---")
    st.markdown("### 📋 Acciones de Mejora asociadas")
    st.caption("Acciones registradas en acciones_mejora.xlsx cuyo ID coincide con indicadores CNA visibles.")

    df_acc = cargar_acciones_mejora()
    if df_acc.empty:
        st.info("No hay datos de acciones de mejora disponibles.")
    else:
        # Intentar encontrar columna de ID de indicador en acciones
        id_col_acc = None
        for cand in ("ID_INDICADOR", "Id", "ID", "INDICADOR_ID", "id_indicador"):
            if cand in df_acc.columns:
                id_col_acc = cand
                break

        if id_col_acc is None:
            st.info("No se encontró columna de ID de indicador en acciones_mejora.xlsx.")
        else:
            # Normalizar IDs para cruce
            ids_cna = set(df["Id"].astype(str).str.strip().unique())
            df_acc_v = df_acc.copy()
            df_acc_v["_id_norm"] = (
                df_acc_v[id_col_acc]
                .apply(lambda x: str(int(float(x))) if str(x).replace(".", "").isdigit() else str(x).strip())
            )
            df_acc_cna = df_acc_v[df_acc_v["_id_norm"].isin(ids_cna)].copy()

            if df_acc_cna.empty:
                st.info("No se encontraron acciones vinculadas a los indicadores CNA del corte actual.")
            else:
                # KPIs
                total_acc = len(df_acc_cna)
                estado_col = "ESTADO" if "ESTADO" in df_acc_cna.columns else None
                cerradas = int((df_acc_cna[estado_col] == "Cerrada").sum()) if estado_col else 0
                abiertas = total_acc - cerradas
                avance_ser = pd.to_numeric(df_acc_cna.get("AVANCE", pd.Series(dtype=float)), errors="coerce").dropna()
                avance_prom = float(avance_ser.mean()) if not avance_ser.empty else None
                vencidas = int((df_acc_cna.get("Estado_Tiempo", "") == "Vencida").sum()) if "Estado_Tiempo" in df_acc_cna.columns else None

                ak1, ak2, ak3, ak4 = st.columns(4)
                ak1.metric("Total acciones", total_acc)
                ak2.metric("Cerradas", cerradas)
                ak3.metric("Abiertas", abiertas)
                ak4.metric("Avance promedio", f"{avance_prom:.1f}%" if avance_prom is not None else "—")

                if vencidas is not None:
                    st.caption(f"Acciones vencidas: **{vencidas}**")

                # Gráfica avance por estado
                if estado_col and "AVANCE" in df_acc_cna.columns:
                    _acc_g = df_acc_cna.groupby(estado_col)["AVANCE"].mean().reset_index()
                    _acc_g.columns = ["Estado", "Avance promedio (%)"]
                    _acc_g["Avance promedio (%)"] = _acc_g["Avance promedio (%)"].round(1)
                    fig_acc = px.bar(
                        _acc_g,
                        x="Estado",
                        y="Avance promedio (%)",
                        title="Avance promedio por estado de acción",
                        color="Estado",
                        text_auto=True,
                    )
                    try:
                        from streamlit_app.components.renderers import render_echarts
                        labels = _acc_g['Estado'].astype(str).tolist()
                        vals = [float(v) for v in _acc_g['Avance promedio (%)'].tolist()]
                        option = {"tooltip": {"trigger": "axis"},
                                  "xAxis": {"type": "category", "data": labels},
                                  "yAxis": {"type": "value"},
                                  "series": [{"type": "bar", "data": vals, "label": {"show": True}}]}
                        render_echarts(option, height=300)
                    except Exception:
                        fig_acc.update_layout(margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
                        st.plotly_chart(fig_acc, use_container_width=True, key="pm_acc_avance")

                # Tabla de acciones
                _show_cols = [c for c in [
                    "_id_norm", "ACCION", "ESTADO", "Estado_Tiempo",
                    "AVANCE", "FECHA_ESTIMADA_CIERRE", "RESPONSABLE",
                ] if c in df_acc_cna.columns]
                _rename = {"_id_norm": "Id indicador", "ACCION": "Acción", "ESTADO": "Estado",
                           "Estado_Tiempo": "Estado tiempo", "AVANCE": "Avance (%)",
                           "FECHA_ESTIMADA_CIERRE": "Fecha compromiso", "RESPONSABLE": "Responsable"}
                if _show_cols:
                    tbl_acc = df_acc_cna[_show_cols].rename(columns=_rename).copy()
                    if "Avance (%)" in tbl_acc.columns:
                        tbl_acc["Avance (%)"] = pd.to_numeric(tbl_acc["Avance (%)"], errors="coerce").round(1)
                    st.dataframe(tbl_acc, use_container_width=True, hide_index=True, height=320)
