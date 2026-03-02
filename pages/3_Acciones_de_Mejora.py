"""
pages/3_Acciones_de_Mejora.py — Oportunidades de Mejora.

Fuente principal : data/raw/OM.xls          (encabezados en fila 8)
Plan de Acción   : data/raw/Plan de accion/*.xls  (consolidado)

Interacción:
  · Seleccionar una fila en la tabla de OM despliega las acciones
    del Plan de Acción asociadas (vínculo: Id ↔ Id Oportunidad de mejora).
"""
import pandas as pd
import streamlit as st

from utils.data_loader import cargar_om, cargar_plan_accion
from utils.charts import exportar_excel

# ── Carga de datos ─────────────────────────────────────────────────────────────
st.markdown("# 📋 Oportunidades de Mejora")
st.caption("Fuente: **OM.xls** · Plan de Acción consolidado")
st.markdown("---")

df_om = cargar_om()
df_pa = cargar_plan_accion()

if df_om.empty:
    st.error(
        "No se encontró **OM.xls** en `data/raw/`. "
        "Verifica que el archivo exista y que los encabezados estén en la fila 8."
    )
    st.stop()

# ── Columnas a mostrar ────────────────────────────────────────────────────────
_COLS_OM = [
    "Id", "Fecha de identificación", "Avance (%)", "Estado",
    "Tipo de acción", "Tipo de oportunidad", "Procesos", "Sede",
    "Descripción", "Fuente", "Fecha de creación",
    "Fecha estimada de cierre", "Fecha real de cierre", "Comentario",
]
_COLS_PA = [
    "Id Acción", "Fecha creación", "Clasificación", "Avance (%)",
    "Estado (Plan de Acción)", "Estado (Oportunidad de mejora)", "Aprobado", "Comentario",
    "Id Oportunidad de mejora", "Descripción", "Acción",
    "Proceso responsable", "Responsable de ejecución", "Fecha límite de ejecución",
    "Responsable de seguimiento", "Fecha límite de seguimiento",
    "Responsable de evaluación", "Fuente de Identificación", "Fecha límite de evaluación",
    "Última ejecución", "Último seguimiento",
]

# Columna de vínculo OM ↔ Plan de Acción
_COL_PA_ID = next(
    (c for c in df_pa.columns if "id oportunidad" in c.lower()),
    None,
) if not df_pa.empty else None

# Columnas clave en OM
_COL_AV     = next((c for c in df_om.columns if "avance" in c.lower()), None)
_COL_ESTADO = next((c for c in df_om.columns if c.lower() == "estado"), None)


# ── KPIs ──────────────────────────────────────────────────────────────────────
total        = len(df_om)
cnt_cerradas = int((df_om[_COL_ESTADO] == "Cerrada").sum()) if _COL_ESTADO else 0
cnt_abiertas = total - cnt_cerradas
avance_prom  = float(df_om[_COL_AV].mean()) if _COL_AV else 0.0
cnt_pa       = len(df_pa)

kc = st.columns(5)
kc[0].metric("Total OM",         total)
kc[1].metric("Abiertas",         cnt_abiertas)
kc[2].metric("Cerradas",         cnt_cerradas)
kc[3].metric("Avance promedio",  f"{round(avance_prom, 1)}%")
kc[4].metric("Acciones de plan", cnt_pa)

st.markdown("---")


# ── Filtros ───────────────────────────────────────────────────────────────────
def _opts(col):
    if col not in df_om.columns:
        return [""]
    return [""] + sorted(df_om[col].dropna().astype(str).unique().tolist())


with st.expander("🔍 Filtros", expanded=True):
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    f_estado = fc1.selectbox("Estado",           _opts("Estado"),
                             key="om_estado", format_func=lambda x: "— Todos —" if x == "" else x)
    f_tipo_a = fc2.selectbox("Tipo de acción",   _opts("Tipo de acción"),
                             key="om_tipo_a", format_func=lambda x: "— Todos —" if x == "" else x)
    f_tipo_o = fc3.selectbox("Tipo oportunidad", _opts("Tipo de oportunidad"),
                             key="om_tipo_o", format_func=lambda x: "— Todos —" if x == "" else x)
    f_proc   = fc4.selectbox("Proceso",          _opts("Procesos"),
                             key="om_proc",   format_func=lambda x: "— Todos —" if x == "" else x)
    f_sede   = fc5.selectbox("Sede",             _opts("Sede"),
                             key="om_sede",   format_func=lambda x: "— Todos —" if x == "" else x)

df_filt = df_om.copy()
if f_estado and "Estado"              in df_filt.columns: df_filt = df_filt[df_filt["Estado"]              == f_estado]
if f_tipo_a and "Tipo de acción"      in df_filt.columns: df_filt = df_filt[df_filt["Tipo de acción"]      == f_tipo_a]
if f_tipo_o and "Tipo de oportunidad" in df_filt.columns: df_filt = df_filt[df_filt["Tipo de oportunidad"] == f_tipo_o]
if f_proc   and "Procesos"            in df_filt.columns: df_filt = df_filt[df_filt["Procesos"]            == f_proc]
if f_sede   and "Sede"                in df_filt.columns: df_filt = df_filt[df_filt["Sede"]                == f_sede]


# ── Tabla principal de OM (seleccionable) ─────────────────────────────────────
cols_show = [c for c in _COLS_OM if c in df_filt.columns]
df_tabla  = df_filt[cols_show].copy()

# Formatear avance
if _COL_AV and _COL_AV in df_tabla.columns:
    df_tabla[_COL_AV] = df_tabla[_COL_AV].apply(
        lambda v: f"{v:.1f}%" if pd.notna(v) else "—"
    )

# Formatear fechas
for _fc in ["Fecha de identificación", "Fecha de creación",
            "Fecha estimada de cierre", "Fecha real de cierre"]:
    if _fc in df_tabla.columns:
        df_tabla[_fc] = (pd.to_datetime(df_tabla[_fc], errors="coerce")
                          .dt.strftime("%d/%m/%Y").fillna("—"))

st.caption(
    f"Mostrando **{len(df_tabla)}** oportunidades — "
    "selecciona una fila para ver el **Plan de Acción**"
)

ev = st.dataframe(
    df_tabla,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Descripción":         st.column_config.TextColumn("Descripción",      width="large"),
        "Comentario":          st.column_config.TextColumn("Comentario",       width="medium"),
        "Procesos":            st.column_config.TextColumn("Procesos",         width="medium"),
        "Tipo de oportunidad": st.column_config.TextColumn("Tipo oportunidad", width="medium"),
    },
)

st.download_button(
    "📥 Exportar Oportunidades (Excel)",
    data=exportar_excel(df_tabla, "Oportunidades de Mejora"),
    file_name="oportunidades_mejora.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="exp_om",
)


# ── Plan de Acción — detalle al seleccionar fila ──────────────────────────────
if ev.selection and ev.selection.rows:
    row_idx = ev.selection.rows[0]
    row_om  = df_filt.iloc[row_idx]
    om_id   = str(row_om.get("Id", "")).strip()

    st.markdown("---")
    st.markdown(f"### 📌 Plan de Acción — Oportunidad **{om_id}**")

    # Tarjeta resumen de la OM seleccionada
    with st.expander("📄 Detalle de la Oportunidad", expanded=True):
        d1, d2, d3 = st.columns(3)
        d1.write(f"**Tipo de acción:** {row_om.get('Tipo de acción', '—')}")
        d1.write(f"**Tipo de oportunidad:** {row_om.get('Tipo de oportunidad', '—')}")
        d2.write(f"**Proceso:** {row_om.get('Procesos', '—')}")
        d2.write(f"**Sede:** {row_om.get('Sede', '—')}")
        d3.write(f"**Estado:** {row_om.get('Estado', '—')}")
        avance_val = row_om.get(_COL_AV, "—") if _COL_AV else "—"
        d3.write(f"**Avance:** {avance_val}")
        st.write(f"**Descripción:** {row_om.get('Descripción', '—')}")
        st.write(f"**Fuente:** {row_om.get('Fuente', '—')}")
        st.write(f"**Comentario:** {row_om.get('Comentario', '—')}")

    # Acciones del Plan de Acción
    if df_pa.empty or _COL_PA_ID is None:
        st.info(
            "No se encontraron archivos en `data/raw/Plan de accion/`. "
            "Coloca los archivos PA_*.xls en esa carpeta."
        )
    else:
        df_plan = df_pa[df_pa[_COL_PA_ID].astype(str) == om_id].copy()

        if df_plan.empty:
            st.info(f"No hay acciones registradas en el Plan de Acción para la OM **{om_id}**.")
        else:
            cols_pa_show = [c for c in _COLS_PA if c in df_plan.columns]
            df_plan_show = df_plan[cols_pa_show].copy()

            # Formatear fechas datetime
            for col in df_plan_show.select_dtypes(include="datetime").columns:
                df_plan_show[col] = df_plan_show[col].dt.strftime("%d/%m/%Y").fillna("—")

            # Formatear avance
            col_av_pa = next((c for c in df_plan_show.columns if "avance" in c.lower()), None)
            if col_av_pa:
                df_plan_show[col_av_pa] = df_plan_show[col_av_pa].apply(
                    lambda v: f"{v:.1f}%" if pd.notna(v) else "—"
                )

            st.caption(f"**{len(df_plan_show)}** acción(es) asociada(s)")
            st.dataframe(
                df_plan_show,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Descripción":                st.column_config.TextColumn("Descripción",       width="large"),
                    "Acción":                     st.column_config.TextColumn("Acción",            width="large"),
                    "Comentario":                 st.column_config.TextColumn("Comentario",        width="medium"),
                    "Proceso responsable":        st.column_config.TextColumn("Proc. resp.",       width="medium"),
                    "Responsable de ejecución":   st.column_config.TextColumn("Resp. ejecución",   width="medium"),
                    "Responsable de seguimiento": st.column_config.TextColumn("Resp. seguimiento", width="medium"),
                    "Responsable de evaluación":  st.column_config.TextColumn("Resp. evaluación",  width="medium"),
                },
            )

            st.download_button(
                "📥 Exportar Plan de Acción (Excel)",
                data=exportar_excel(df_plan_show, f"Plan_OM_{om_id}"),
                file_name=f"plan_accion_om_{om_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="exp_pa",
            )
