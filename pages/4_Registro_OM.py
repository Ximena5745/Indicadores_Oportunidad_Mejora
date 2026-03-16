"""
pages/4_Registro_OM.py — Registro de Oportunidades de Mejora.

Flujo:
  1. Tabla superior: indicadores en incumplimiento (Peligro/Alerta) con estado OM.
     Clic en fila → precarga el formulario.
  2. Formulario izquierdo: indicador + año + periodo + ¿OM? + número/comentario.
     Validación cruzada con OM.xlsx: al ingresar N° OM muestra estado actual.
  3. Tabla derecha: registros guardados en BD, seleccionable para editar.
"""
import calendar
import datetime

import pandas as pd
import streamlit as st

from core.calculos import obtener_ultimo_registro
from services.data_loader import cargar_dataset, construir_opciones_indicadores, cargar_om
from core.db_manager import guardar_registro_om, leer_registros_om, registros_om_como_dict
from components.charts import exportar_excel
from core.config import COLORES, COLOR_CATEGORIA, COLOR_CATEGORIA_CLARO

# ── Carga de datos ─────────────────────────────────────────────────────────────
df_raw   = cargar_dataset()
df_om_xl = cargar_om()          # OM.xlsx para validación cruzada

if df_raw.empty:
    st.error("No se pudo cargar Dataset_Unificado.xlsx.")
    st.stop()

# ── Session state ──────────────────────────────────────────────────────────────
_SS_DEFAULTS = {
    "om_recarga":      0,
    "om_limpiar":      False,
    "om_ind_presel":   None,   # Id del indicador preseleccionado desde tabla superior
    "om_edit_data":    None,   # dict con datos del registro a editar
}
for k, v in _SS_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Título ─────────────────────────────────────────────────────────────────────
st.markdown("# 📝 Registro de Oportunidades de Mejora (OM)")
st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _periodo_esperado_actual(periodicidad: str) -> str:
    """Retorna el período esperado según la periodicidad y la fecha actual."""
    hoy  = datetime.date.today()
    p    = str(periodicidad).strip().lower()
    y, m = hoy.year, hoy.month
    nombres_mes = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    if any(x in p for x in ("anual", "año")):
        return str(y - 1)

    if any(x in p for x in ("semestral",)):
        sem = 1 if m <= 6 else 2
        return f"S{sem}-{y}" if m > 6 else f"S2-{y-1}"

    if any(x in p for x in ("trimestral", "trim")):
        q = (m - 1) // 3
        if q == 0:
            return f"Q4-{y-1}"
        return f"Q{q}-{y}"

    if any(x in p for x in ("bimestral",)):
        b = (m - 1) // 2
        if b == 0:
            return f"Nov-Dic {y-1}"
        m_ini = b * 2 - 1
        return f"{nombres_mes[m_ini-1]}-{nombres_mes[m_ini]} {y}"

    if any(x in p for x in ("mensual",)):
        if m == 1:
            return f"{nombres_mes[11]} {y-1}"
        return f"{nombres_mes[m-2]} {y}"

    return f"{nombres_mes[m-2]} {y}"


def _lookup_om_xlsx(numero: str) -> dict | None:
    """Busca un número de OM en OM.xlsx y retorna sus datos clave o None."""
    if df_om_xl.empty or not numero:
        return None
    col_id = next((c for c in df_om_xl.columns if c.strip().lower() == "id"), None)
    if col_id is None:
        return None
    match = df_om_xl[df_om_xl[col_id].astype(str).str.strip() == str(numero).strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    col_est  = next((c for c in df_om_xl.columns if c.lower() == "estado"), None)
    col_av   = next((c for c in df_om_xl.columns if "avance" in c.lower()), None)
    col_fec  = next((c for c in df_om_xl.columns if "estimada" in c.lower() and "cierre" in c.lower()), None)
    return {
        "Estado":  str(row[col_est])  if col_est else "—",
        "Avance":  f"{row[col_av]:.1f}%" if col_av and pd.notna(row[col_av]) else "—",
        "F_cierre": pd.to_datetime(row[col_fec]).strftime("%d/%m/%Y")
                    if col_fec and pd.notna(row[col_fec]) else "—",
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — Tabla de indicadores en incumplimiento
# ══════════════════════════════════════════════════════════════════════════════

df_ultimo       = obtener_ultimo_registro(df_raw)
df_incumplimiento = df_ultimo[
    df_ultimo["Categoria"].isin(["Peligro", "Alerta"])
].copy() if not df_ultimo.empty else pd.DataFrame()

# Cruzar con registros de BD
om_dict = registros_om_como_dict()   # {id: {"tiene_om": bool, "numero_om": str, ...}}

if not df_incumplimiento.empty:
    df_incumplimiento["Cumplimiento%"] = (
        df_incumplimiento["Cumplimiento_norm"] * 100
    ).round(1).astype(str) + "%"

    df_incumplimiento["Estado OM"] = df_incumplimiento["Id"].apply(
        lambda i: "✅ Con OM" if om_dict.get(i, {}).get("tiene_om") else "❌ Sin OM"
    )
    df_incumplimiento["N° OM"] = df_incumplimiento["Id"].apply(
        lambda i: om_dict.get(i, {}).get("numero_om", "")
    )

    # Lookup estado actual en OM.xlsx
    def _estado_xlsx(numero_om):
        if not numero_om:
            return "—"
        info = _lookup_om_xlsx(str(numero_om))
        return info["Estado"] if info else "No encontrada"

    df_incumplimiento["Estado en OM.xlsx"] = df_incumplimiento["N° OM"].apply(_estado_xlsx)

    cols_tabla_sup = ["Id", "Indicador", "Proceso", "Periodicidad",
                      "Categoria", "Cumplimiento%", "Estado OM", "N° OM", "Estado en OM.xlsx"]
    cols_sup = [c for c in cols_tabla_sup if c in df_incumplimiento.columns]
    df_sup   = df_incumplimiento[cols_sup].copy()

    def _estilo_cat_sup(row):
        bg = COLOR_CATEGORIA_CLARO.get(str(row.get("Categoria", "")), "")
        return [f"background-color:{bg}" if c == "Categoria" else "" for c in row.index]

    n_sin_om = int((df_sup["Estado OM"] == "❌ Sin OM").sum()) if "Estado OM" in df_sup.columns else 0
    n_peligro = int((df_incumplimiento["Categoria"] == "Peligro").sum())
    n_alerta  = int((df_incumplimiento["Categoria"] == "Alerta").sum())

    with st.expander(
        f"📋 Indicadores en incumplimiento: 🔴 {n_peligro} Peligro · 🟡 {n_alerta} Alerta "
        f"· ❌ {n_sin_om} sin OM registrada — **clic en una fila para registrar**",
        expanded=True,
    ):
        ev_sup = st.dataframe(
            df_sup.style.apply(_estilo_cat_sup, axis=1),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="tabla_incumplimiento",
            column_config={
                "Indicador":        st.column_config.TextColumn("Indicador",    width="large"),
                "Estado OM":        st.column_config.TextColumn("Estado OM",    width="medium"),
                "Estado en OM.xlsx":st.column_config.TextColumn("OM.xlsx",      width="small"),
            },
        )
        if ev_sup.selection and ev_sup.selection.get("rows"):
            idx_sel = ev_sup.selection["rows"][0]
            id_sel  = df_sup["Id"].iloc[idx_sel]
            if st.session_state.om_ind_presel != id_sel:
                st.session_state.om_ind_presel = id_sel
                # Cargar datos existentes en BD para ese indicador
                reg_existente = om_dict.get(id_sel)
                if reg_existente:
                    st.session_state.om_edit_data = reg_existente
                else:
                    st.session_state.om_edit_data = None
                st.session_state.om_recarga += 1
                st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — Formulario + Tabla de registros
# ══════════════════════════════════════════════════════════════════════════════

col_form, col_tabla = st.columns([2, 3], gap="large")

# ─────────────────────────────────────────────────────────────────────────────
# COLUMNA IZQUIERDA — Formulario
# ─────────────────────────────────────────────────────────────────────────────
with col_form:
    st.markdown("### Nuevo Registro")

    # Indicador
    opciones_ind = construir_opciones_indicadores(df_raw)
    labels_list  = list(opciones_ind.keys())

    # Calcular índice default desde preselección
    id_presel = st.session_state.om_ind_presel
    if st.session_state.om_limpiar:
        idx_default = 0
        st.session_state.om_limpiar  = False
        st.session_state.om_ind_presel = None
        st.session_state.om_edit_data  = None
    elif id_presel:
        # Buscar el label que corresponde al id_presel
        matching = [i+1 for i, (lbl, iid) in enumerate(opciones_ind.items()) if iid == id_presel]
        idx_default = matching[0] if matching else 0
    else:
        idx_default = 0

    label_ind = st.selectbox(
        "Indicador *",
        options=["— Selecciona un indicador —"] + labels_list,
        index=idx_default,
        key=f"om_indicador_{st.session_state.om_recarga}",
    )

    id_indicador     = None
    nombre_ind       = ""
    proceso_ind      = ""
    periodicidad_ind = ""
    cum_pct_actual   = None
    categoria_actual = ""

    if label_ind != "— Selecciona un indicador —":
        id_indicador = opciones_ind[label_ind]
        df_ind       = df_raw[df_raw["Id"] == id_indicador]

        if not df_ind.empty:
            ultimo           = df_ind.sort_values("Fecha").iloc[-1]
            nombre_ind       = str(ultimo.get("Indicador", ""))
            proceso_ind      = str(ultimo.get("Proceso", ""))
            periodicidad_ind = str(ultimo.get("Periodicidad", ""))
            cum_norm         = ultimo.get("Cumplimiento_norm", None)
            categoria_actual = str(ultimo.get("Categoria", "Sin dato"))
            cum_pct_actual   = round(float(cum_norm) * 100, 1) if pd.notna(cum_norm) else None

        # Info badge del indicador
        badge_col  = COLOR_CATEGORIA.get(categoria_actual, "#9E9E9E")
        periodo_esp = _periodo_esperado_actual(periodicidad_ind)
        reg_existente = om_dict.get(id_indicador)

        st.markdown(
            f"""<div style="background:#F4F6F9;border-radius:8px;padding:12px;
                border-left:4px solid {COLORES['primario']};">
                <b>Proceso:</b> {proceso_ind}<br>
                <b>Periodicidad:</b> {periodicidad_ind} &nbsp;|&nbsp;
                <b>Período esperado:</b> {periodo_esp}<br>
                <b>Cumplimiento actual:</b> {f'{cum_pct_actual}%' if cum_pct_actual is not None else '—'}
                &nbsp;&nbsp;
                <span style="background:{badge_col};color:white;padding:2px 10px;
                border-radius:12px;font-size:0.82rem">{categoria_actual}</span>
            </div>""",
            unsafe_allow_html=True,
        )

        # Alerta de período sin / con registro
        if reg_existente:
            st.success(
                f"✅ Registro existente para este indicador "
                f"(Período: {reg_existente['periodo']} · "
                f"{'Con OM N° ' + reg_existente['numero_om'] if reg_existente['tiene_om'] else 'Sin OM'}). "
                "Guardar actualizará el registro."
            )
        else:
            st.warning(
                f"⚠️ No hay registro para este indicador en la BD. "
                f"Período esperado según periodicidad: **{periodo_esp}**."
            )

    st.markdown("")

    # Año
    anios_disp  = sorted([int(a) for a in df_raw["Anio"].dropna().unique().tolist()]) \
                  if "Anio" in df_raw.columns else [datetime.date.today().year]
    anio_actual = datetime.date.today().year
    anio_idx    = anios_disp.index(anio_actual) if anio_actual in anios_disp else len(anios_disp) - 1

    anio_sel = st.selectbox(
        "Año *",
        options=anios_disp,
        index=anio_idx,
        key=f"om_anio_{st.session_state.om_recarga}",
    )

    # Periodo
    df_periodos  = df_raw[df_raw["Anio"] == anio_sel] if "Anio" in df_raw.columns else df_raw
    periodos_disp = sorted(df_periodos["Periodo"].dropna().unique().tolist()) \
                    if "Periodo" in df_periodos.columns else []
    if not periodos_disp:
        periodos_disp = sorted(df_raw["Periodo"].dropna().unique().tolist()) \
                        if "Periodo" in df_raw.columns else []

    # Pre-seleccionar el periodo si hay edición
    edit_data    = st.session_state.om_edit_data
    periodo_presel = edit_data.get("periodo", "") if edit_data else ""
    per_options  = ["— Selecciona —"] + periodos_disp
    per_idx      = per_options.index(periodo_presel) if periodo_presel in per_options else 0

    periodo_sel = st.selectbox(
        "Periodo *",
        options=per_options,
        index=per_idx,
        key=f"om_periodo_{st.session_state.om_recarga}",
    )
    periodo_val = periodo_sel if periodo_sel != "— Selecciona —" else None

    # ¿Se abrió OM?
    tiene_om_default = "SI" if (edit_data and edit_data.get("tiene_om")) else "NO"
    tiene_om_radio   = st.radio(
        "¿Se abrió Oportunidad de Mejora? *",
        options=["SI", "NO"],
        index=0 if tiene_om_default == "SI" else 1,
        horizontal=True,
        key=f"om_radio_{st.session_state.om_recarga}",
    )

    numero_om  = None
    comentario = ""

    if tiene_om_radio == "SI":
        num_default = int(edit_data["numero_om"]) if edit_data and edit_data.get("numero_om") else 1
        numero_om   = st.number_input(
            "Número de OM *",
            min_value=1,
            step=1,
            value=num_default,
            key=f"om_numero_{st.session_state.om_recarga}",
        )
        # Validación cruzada con OM.xlsx
        info_om = _lookup_om_xlsx(str(int(numero_om)))
        if info_om:
            st.markdown(
                f"""<div style="background:#E8F5E9;border-radius:6px;padding:10px;
                    border-left:3px solid #43A047;font-size:0.9rem;">
                    <b>OM {int(numero_om)} encontrada en OM.xlsx</b><br>
                    Estado: <b>{info_om['Estado']}</b> &nbsp;|&nbsp;
                    Avance: <b>{info_om['Avance']}</b> &nbsp;|&nbsp;
                    Cierre estimado: <b>{info_om['F_cierre']}</b>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.warning(f"⚠️ El N° {int(numero_om)} no se encontró en OM.xlsx.")
    else:
        com_default = edit_data.get("comentario", "") if edit_data else ""
        comentario  = st.text_area(
            "Comentario / Justificación *",
            value=com_default,
            placeholder="Describe por qué no se abrió OM (mínimo 20 caracteres)...",
            key=f"om_comentario_{st.session_state.om_recarga}",
        )
        char_count  = len(comentario)
        color_cnt   = "green" if char_count >= 20 else "red"
        st.markdown(
            f"<small style='color:{color_cnt}'>{char_count}/20 caracteres mínimos</small>",
            unsafe_allow_html=True,
        )

    # Validación
    errores = []
    if id_indicador is None:
        errores.append("Selecciona un indicador.")
    if periodo_val is None:
        errores.append("Selecciona un periodo.")
    if tiene_om_radio == "SI" and (numero_om is None or numero_om < 1):
        errores.append("Ingresa un número de OM válido.")
    if tiene_om_radio == "NO" and len(comentario) < 20:
        errores.append(f"El comentario debe tener al menos 20 caracteres ({len(comentario)} actuales).")

    formulario_valido = len(errores) == 0
    es_edicion        = bool(edit_data)
    st.markdown("")

    # Botones
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        lbl_btn = "💾 Actualizar" if es_edicion else "💾 Guardar"
        if st.button(lbl_btn, disabled=not formulario_valido,
                     use_container_width=True, type="primary"):
            datos = {
                "id_indicador":     id_indicador,
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
                accion = "actualizado" if es_edicion else "guardado"
                st.success(f"✅ Registro {accion} correctamente.")
                st.session_state.om_recarga   += 1
                st.session_state.om_limpiar    = True
                st.session_state.om_ind_presel = None
                st.session_state.om_edit_data  = None
                st.rerun()
            else:
                st.error("❌ No se pudo guardar el registro.")

    with col_btn2:
        if st.button("🗑️ Limpiar", use_container_width=True):
            st.session_state.om_recarga   += 1
            st.session_state.om_limpiar    = True
            st.session_state.om_ind_presel = None
            st.session_state.om_edit_data  = None
            st.rerun()

    if not formulario_valido:
        for err in errores:
            st.caption(f"⚠️ {err}")


# ─────────────────────────────────────────────────────────────────────────────
# COLUMNA DERECHA — Tabla de registros guardados
# ─────────────────────────────────────────────────────────────────────────────
with col_tabla:
    st.markdown("### Registros Guardados")

    # Filtros
    fc1, fc2 = st.columns(2)
    anio_filtro = fc1.selectbox(
        "Filtrar por año",
        options=["Todos"] + [str(a) for a in sorted(anios_disp, reverse=True)],
        key="om_filtro_anio",
    )
    om_filtro   = fc2.selectbox(
        "¿Tiene OM?",
        options=["Todos", "Con OM", "Sin OM"],
        key="om_filtro_om",
    )

    anio_filtro_val = int(anio_filtro) if anio_filtro != "Todos" else None
    registros       = leer_registros_om(anio=anio_filtro_val)

    if registros:
        df_reg = pd.DataFrame(registros)
        if om_filtro == "Con OM":
            df_reg = df_reg[df_reg["tiene_om"] == 1]
        elif om_filtro == "Sin OM":
            df_reg = df_reg[df_reg["tiene_om"] == 0]

        if "tiene_om" in df_reg.columns:
            df_reg["tiene_om"] = df_reg["tiene_om"].apply(lambda x: "SI" if x == 1 else "NO")

        cols_show = ["id_indicador", "nombre_indicador", "proceso",
                     "periodo", "anio", "tiene_om", "numero_om", "comentario", "fecha_registro"]
        cols_disp = [c for c in cols_show if c in df_reg.columns]
        df_show   = df_reg[cols_disp].copy()

        # Mini-stats
        n_total = len(df_show)
        n_con   = int((df_show["tiene_om"] == "SI").sum()) if "tiene_om" in df_show.columns else 0
        n_sin   = n_total - n_con
        st.caption(f"**{n_total}** registros · ✅ {n_con} con OM · ❌ {n_sin} sin OM")

        ev_reg = st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="tabla_registros_om",
            column_config={
                "id_indicador":     st.column_config.TextColumn("ID"),
                "nombre_indicador": st.column_config.TextColumn("Indicador",  width="medium"),
                "proceso":          st.column_config.TextColumn("Proceso"),
                "periodo":          st.column_config.TextColumn("Periodo"),
                "anio":             st.column_config.NumberColumn("Año",      format="%d"),
                "tiene_om":         st.column_config.TextColumn("¿OM?"),
                "numero_om":        st.column_config.TextColumn("N° OM"),
                "comentario":       st.column_config.TextColumn("Comentario", width="large"),
                "fecha_registro":   st.column_config.TextColumn("Fecha Reg."),
            },
        )

        # Clic en tabla → cargar en formulario para editar
        if ev_reg.selection and ev_reg.selection.get("rows"):
            idx_r    = ev_reg.selection["rows"][0]
            row_edit = df_reg.iloc[idx_r]
            edit_id  = row_edit.get("id_indicador", "")
            if edit_id and st.session_state.om_ind_presel != edit_id:
                st.session_state.om_ind_presel = edit_id
                st.session_state.om_edit_data  = {
                    "tiene_om":   row_edit.get("tiene_om") in ("SI", 1, "1"),
                    "numero_om":  str(row_edit.get("numero_om", "")),
                    "periodo":    str(row_edit.get("periodo", "")),
                    "comentario": str(row_edit.get("comentario", "")),
                }
                st.session_state.om_recarga += 1
                st.rerun()

        st.download_button(
            "📥 Exportar Excel",
            data=exportar_excel(df_show, "Registros_OM"),
            file_name="registros_om.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("No hay registros guardados aún.")
        st.markdown(
            """
            > **Cómo usar este formulario:**
            > 1. Selecciona un indicador de la tabla superior (en incumplimiento)
            > 2. Confirma el año y periodo
            > 3. Indica si se abrió OM (SI/NO)
            > 4. Completa el número de OM o el comentario
            > 5. Haz clic en **Guardar**
            """
        )
