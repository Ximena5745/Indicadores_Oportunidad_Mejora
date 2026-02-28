"""
pages/4_Registro_OM.py — Formulario de Registro de Oportunidades de Mejora.
"""
import datetime
import pandas as pd
import streamlit as st

from utils.data_loader import cargar_dataset, construir_opciones_indicadores
from utils.db_manager import guardar_registro_om, leer_registros_om
from utils.charts import exportar_excel
from config import COLORES, COLOR_CATEGORIA

# ── Carga de datos ────────────────────────────────────────────────────────────
df_raw = cargar_dataset()

if df_raw.empty:
    st.error("No se pudo cargar Dataset_Unificado.xlsx.")
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
if "om_recarga" not in st.session_state:
    st.session_state.om_recarga = 0
if "om_limpiar" not in st.session_state:
    st.session_state.om_limpiar = False

# ── Título ────────────────────────────────────────────────────────────────────
st.markdown("# 📝 Registro de Oportunidades de Mejora (OM)")
st.markdown("---")

# ── Layout dos columnas ───────────────────────────────────────────────────────
col_form, col_tabla = st.columns([2, 3], gap="large")

# ══════════════════════════════════════════════════════════════════════════════
# COLUMNA IZQUIERDA — Formulario
# ══════════════════════════════════════════════════════════════════════════════
with col_form:
    st.markdown("### Nuevo Registro")

    # 1. Indicador
    opciones_ind = construir_opciones_indicadores(df_raw)
    labels_list  = list(opciones_ind.keys())

    if st.session_state.om_limpiar:
        idx_default = 0
        st.session_state.om_limpiar = False
    else:
        idx_default = 0

    label_ind = st.selectbox(
        "Indicador *",
        options=["— Selecciona un indicador —"] + labels_list,
        index=idx_default,
        key=f"om_indicador_{st.session_state.om_recarga}",
    )

    id_indicador    = None
    nombre_ind      = ""
    proceso_ind     = ""
    cum_pct_actual  = None
    categoria_actual = ""

    if label_ind != "— Selecciona un indicador —":
        id_indicador = opciones_ind[label_ind]
        df_ind = df_raw[df_raw["Id"] == id_indicador]

        if not df_ind.empty:
            ultimo = df_ind.sort_values("Fecha").iloc[-1]
            nombre_ind      = str(ultimo.get("Indicador", ""))
            proceso_ind     = str(ultimo.get("Proceso", ""))
            cum_norm        = ultimo.get("Cumplimiento_norm", None)
            categoria_actual = str(ultimo.get("Categoria", "Sin dato"))
            cum_pct_actual  = round(float(cum_norm) * 100, 1) if pd.notna(cum_norm) else None

        # Info automática
        badge_col = COLOR_CATEGORIA.get(categoria_actual, "#9E9E9E")
        with st.container():
            st.markdown(
                f"""<div style="background:#F4F6F9;border-radius:8px;padding:12px;
                    border-left:4px solid {COLORES['primario']};">
                    <b>Proceso:</b> {proceso_ind}<br>
                    <b>Cumplimiento actual:</b> {f'{cum_pct_actual}%' if cum_pct_actual is not None else '—'}
                    &nbsp;&nbsp;
                    <span style="background:{badge_col};color:white;padding:2px 10px;
                    border-radius:12px;font-size:0.82rem">{categoria_actual}</span>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("")

    # 2. Año
    anios_disp = sorted(
        [int(a) for a in df_raw["Anio"].dropna().unique().tolist()]
    ) if "Anio" in df_raw.columns else [datetime.date.today().year]
    anio_actual = datetime.date.today().year
    anio_idx = anios_disp.index(anio_actual) if anio_actual in anios_disp else len(anios_disp) - 1

    anio_sel = st.selectbox(
        "Año *",
        options=anios_disp,
        index=anio_idx,
        key=f"om_anio_{st.session_state.om_recarga}",
    )

    # 3. Periodo (filtrar por año seleccionado si hay datos)
    df_periodos = df_raw[df_raw["Anio"] == anio_sel] if "Anio" in df_raw.columns else df_raw
    periodos_disp = sorted(df_periodos["Periodo"].dropna().unique().tolist()) if "Periodo" in df_periodos.columns else []

    if not periodos_disp:
        periodos_disp = sorted(df_raw["Periodo"].dropna().unique().tolist()) if "Periodo" in df_raw.columns else []

    periodo_sel = st.selectbox(
        "Periodo *",
        options=["— Selecciona —"] + periodos_disp,
        key=f"om_periodo_{st.session_state.om_recarga}",
    )
    periodo_val = periodo_sel if periodo_sel != "— Selecciona —" else None

    # 4. ¿Se abrió OM?
    tiene_om_radio = st.radio(
        "¿Se abrió Oportunidad de Mejora? *",
        options=["SI", "NO"],
        horizontal=True,
        key=f"om_radio_{st.session_state.om_recarga}",
    )

    numero_om  = None
    comentario = ""

    if tiene_om_radio == "SI":
        numero_om = st.number_input(
            "Número de OM *",
            min_value=1,
            step=1,
            key=f"om_numero_{st.session_state.om_recarga}",
        )
    else:
        comentario = st.text_area(
            "Comentario / Justificación *",
            placeholder="Describe por qué no se abrió OM (mínimo 20 caracteres)...",
            key=f"om_comentario_{st.session_state.om_recarga}",
        )
        char_count = len(comentario)
        color_counter = "green" if char_count >= 20 else "red"
        st.markdown(
            f"<small style='color:{color_counter}'>{char_count}/20 caracteres mínimos</small>",
            unsafe_allow_html=True,
        )

    # ── Validación ────────────────────────────────────────────────────────────
    errores = []
    if id_indicador is None:
        errores.append("Selecciona un indicador.")
    if periodo_val is None:
        errores.append("Selecciona un periodo.")
    if tiene_om_radio == "SI" and (numero_om is None or numero_om < 1):
        errores.append("Ingresa un número de OM válido.")
    if tiene_om_radio == "NO" and len(comentario) < 20:
        errores.append(f"El comentario debe tener al menos 20 caracteres (actual: {len(comentario)}).")

    formulario_valido = len(errores) == 0

    st.markdown("")

    # ── Botones ───────────────────────────────────────────────────────────────
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button(
            "💾 Guardar",
            disabled=not formulario_valido,
            use_container_width=True,
            type="primary",
        ):
            datos = {
                "id_indicador":    id_indicador,
                "nombre_indicador": nombre_ind,
                "proceso":          proceso_ind,
                "periodo":          periodo_val,
                "anio":             int(anio_sel),
                "tiene_om":         1 if tiene_om_radio == "SI" else 0,
                "numero_om":        str(int(numero_om)) if numero_om else "",
                "comentario":       comentario,
            }
            ok = guardar_registro_om(datos)
            if ok:
                st.success("✅ Registro guardado correctamente.")
                st.session_state.om_recarga += 1
                st.session_state.om_limpiar = True
                st.rerun()
            else:
                st.error("❌ No se pudo guardar el registro.")

    with col_btn2:
        if st.button("🗑️ Limpiar", use_container_width=True):
            st.session_state.om_recarga += 1
            st.session_state.om_limpiar = True
            st.rerun()

    # Mostrar errores si intenta guardar sin completar
    if not formulario_valido:
        for err in errores:
            st.caption(f"⚠️ {err}")

# ══════════════════════════════════════════════════════════════════════════════
# COLUMNA DERECHA — Tabla de registros
# ══════════════════════════════════════════════════════════════════════════════
with col_tabla:
    st.markdown("### Registros Guardados")

    # Filtro por año
    anio_filtro = st.selectbox(
        "Filtrar por año",
        options=["Todos"] + [str(a) for a in sorted(anios_disp, reverse=True)],
        key="om_filtro_anio",
    )

    anio_filtro_val = int(anio_filtro) if anio_filtro != "Todos" else None
    registros = leer_registros_om(anio=anio_filtro_val)

    if registros:
        df_registros = pd.DataFrame(registros)

        # Formato tiene_om
        if "tiene_om" in df_registros.columns:
            df_registros["tiene_om"] = df_registros["tiene_om"].apply(
                lambda x: "SI" if x == 1 else "NO"
            )

        cols_show = [
            "id_indicador", "nombre_indicador", "proceso",
            "periodo", "anio", "tiene_om", "numero_om", "comentario", "fecha_registro",
        ]
        cols_disp = [c for c in cols_show if c in df_registros.columns]
        df_show = df_registros[cols_disp].copy()

        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id_indicador":    st.column_config.TextColumn("ID Indicador"),
                "nombre_indicador": st.column_config.TextColumn("Indicador", width="medium"),
                "proceso":         st.column_config.TextColumn("Proceso"),
                "periodo":         st.column_config.TextColumn("Periodo"),
                "anio":            st.column_config.NumberColumn("Año", format="%d"),
                "tiene_om":        st.column_config.TextColumn("¿OM?"),
                "numero_om":       st.column_config.TextColumn("N° OM"),
                "comentario":      st.column_config.TextColumn("Comentario", width="large"),
                "fecha_registro":  st.column_config.TextColumn("Fecha Registro"),
            },
        )

        st.markdown(f"*{len(df_registros)} registros encontrados.*")

        st.download_button(
            label="📥 Exportar Excel",
            data=exportar_excel(df_show, "Registros OM"),
            file_name="registros_om.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("No hay registros guardados aún.")
        st.markdown(
            """
            > **Cómo usar este formulario:**
            > 1. Selecciona el indicador y periodo
            > 2. Indica si se abrió OM (SI/NO)
            > 3. Completa el número de OM o el comentario
            > 4. Haz clic en **Guardar**
            """
        )
