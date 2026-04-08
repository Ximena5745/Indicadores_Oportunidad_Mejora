"""
pages/2_Gestion_OM.py — Gestión de Oportunidades de Mejora.

Flujo:
  Tab 1: Identificar indicadores en incumplimiento
         → clic en fila → modal emergente de registro OM
  Tab 2: Seguimiento de OM y acciones (análisis + retrasadas)
"""
from pathlib import Path
import calendar
import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import cargar_dataset, construir_opciones_indicadores, cargar_om, cargar_plan_accion
from core.calculos import obtener_ultimo_registro, calcular_meses_en_peligro
from components.charts import (grafico_historico_indicador, tabla_historica_indicador,
                               exportar_excel, panel_detalle_indicador)
from core.niveles import NIVEL_COLOR, NIVEL_BG, NIVEL_ORDEN
from core.db_manager import guardar_registro_om, leer_registros_om, registros_om_como_dict
from core.config import COLORES, COLOR_CATEGORIA, COLOR_CATEGORIA_CLARO

# ── Rutas ─────────────────────────────────────────────────────────────────────
_DATA_RAW   = Path(__file__).parent.parent / "data" / "raw"
_RUTA_KAWAK = _DATA_RAW / "Fuentes Consolidadas" / "Consolidado_API_Kawak.xlsx"

# ── Carga de datos (una sola vez, todo cacheado) ──────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def _kawak_ids() -> set:
    if not _RUTA_KAWAK.exists():
        return set()
    df = pd.read_excel(str(_RUTA_KAWAK), engine="openpyxl",
                       keep_default_na=False, na_values=[""])
    df.columns = [str(c).strip() for c in df.columns]
    col_id = next((c for c in df.columns if c.upper() == "ID"), None)
    if not col_id:
        return set()
    def _clean(x):
        try:
            f = float(x)
            return str(int(f)) if f == int(f) else str(f)
        except (TypeError, ValueError):
            return str(x).strip()
    return set(df[col_id].apply(_clean).dropna().unique())


df_raw_all = cargar_dataset()
if df_raw_all.empty:
    st.error("No se pudo cargar Resultados Consolidados.xlsx.")
    st.stop()

kawak_set = _kawak_ids()
df_raw = df_raw_all[df_raw_all["Id"].isin(kawak_set)].copy() if kawak_set and "Id" in df_raw_all.columns else df_raw_all.copy()

df_om_xl = cargar_om()
df_pa    = cargar_plan_accion()

# ── Session state ──────────────────────────────────────────────────────────────
_SS = {
    # Tab 1
    "gom_cat_activa":  "Peligro",
    "gom_sel_proceso": None,
    "gom_modal_id":    None,   # Id del indicador cuyo modal está abierto
    # Tab 2
    "gom_filtro_proc_tab2": None,
    # Registro OM
    "gom_om_recarga":       0,
}
for k, v in _SS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Datos para filtros (se renderizan después del título) ─────────────────────
anios_disp  = sorted(df_raw["Anio"].dropna().unique().tolist()) if "Anio" in df_raw.columns else []
default_año = [2025] if 2025 in anios_disp else (anios_disp[-1:] if anios_disp else [])
meses_disp  = sorted(df_raw["Mes"].dropna().unique().tolist()) if "Mes" in df_raw.columns else []
# Filtros se renderizan en la sección principal — ver abajo después del título
anios_sel   = default_año  # valor por defecto, se actualiza con widget
meses_sel   = []

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _lookup_om_xlsx(numero: str) -> dict | None:
    if df_om_xl.empty or not numero:
        return None
    col_id = next((c for c in df_om_xl.columns if c.strip().lower() == "id"), None)
    if col_id is None:
        return None
    match = df_om_xl[df_om_xl[col_id].astype(str).str.strip() == str(numero).strip()]
    if match.empty:
        return None
    row = match.iloc[0]
    col_est = next((c for c in df_om_xl.columns if c.lower() == "estado"), None)
    col_av  = next((c for c in df_om_xl.columns if "avance" in c.lower()), None)
    col_fec = next((c for c in df_om_xl.columns if "estimada" in c.lower() and "cierre" in c.lower()), None)
    return {
        "Estado":  str(row[col_est]) if col_est else "—",
        "Avance":  f"{row[col_av]:.1f}%" if col_av and pd.notna(row[col_av]) else "—",
        "F_cierre": pd.to_datetime(row[col_fec]).strftime("%d/%m/%Y")
                    if col_fec and pd.notna(row[col_fec]) else "—",
    }


def _periodo_esperado(periodicidad: str) -> str:
    hoy = datetime.date.today()
    p   = str(periodicidad).strip().lower()
    y, m = hoy.year, hoy.month
    meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    if any(x in p for x in ("anual", "año")):
        return str(y - 1)
    if "semestral" in p:
        return f"S{'1' if m <= 6 else '2'}-{y}" if m > 6 else f"S2-{y-1}"
    if any(x in p for x in ("trimestral", "trim")):
        q = (m - 1) // 3
        return f"Q4-{y-1}" if q == 0 else f"Q{q}-{y}"
    if "mensual" in p:
        return f"{meses[11]} {y-1}" if m == 1 else f"{meses[m-2]} {y}"
    return f"{meses[m-2]} {y}"


# ══════════════════════════════════════════════════════════════════════════════
# MODAL DE REGISTRO OM
# ══════════════════════════════════════════════════════════════════════════════

@st.dialog("Registrar / Actualizar Oportunidad de Mejora", width="large")
def _modal_registro_om(id_indicador: str):
    """Modal emergente con formulario de registro OM + histórico del indicador."""
    # ── Datos del indicador ────────────────────────────────────────────────────
    df_ind = df_raw[df_raw["Id"] == id_indicador]
    if df_ind.empty:
        st.warning("No se encontraron datos para este indicador.")
        return

    ultimo = df_ind.sort_values("Fecha").iloc[-1]
    nombre_ind       = str(ultimo.get("Indicador", ""))
    proceso_ind      = str(ultimo.get("Proceso", ""))
    periodicidad_ind = str(ultimo.get("Periodicidad", ""))
    cum_norm         = ultimo.get("Cumplimiento_norm", None)
    categoria_actual = str(ultimo.get("Categoria", "Sin dato"))
    cum_pct_actual   = round(float(cum_norm) * 100, 1) if pd.notna(cum_norm) else None

    reg_existente = om_dict.get(id_indicador)

    # ── Badge del indicador ────────────────────────────────────────────────────
    badge_col   = COLOR_CATEGORIA.get(categoria_actual, "#9E9E9E")
    periodo_esp = _periodo_esperado(periodicidad_ind)

    st.markdown(
        f"""<div style="background:#F4F6F9;border-radius:8px;padding:12px;
            border-left:4px solid {COLORES['primario']};margin-bottom:12px;">
            <b style="font-size:1rem">{id_indicador} — {nombre_ind}</b><br>
            <b>Proceso:</b> {proceso_ind} &nbsp;|&nbsp;
            <b>Periodicidad:</b> {periodicidad_ind} &nbsp;|&nbsp;
            <b>Período esperado:</b> {periodo_esp}<br>
            <b>Cumplimiento actual:</b>
            {f'<b>{cum_pct_actual}%</b>' if cum_pct_actual is not None else '—'}
            &nbsp;
            <span style="background:{badge_col};color:white;padding:2px 10px;
            border-radius:12px;font-size:0.82rem">{categoria_actual}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Dos columnas: formulario | histórico ──────────────────────────────────
    col_frm, col_hist = st.columns([1, 1], gap="medium")

    with col_frm:
        st.markdown("#### Registro OM")
        if reg_existente:
            st.info(
                f"✅ Registro existente — "
                f"{'OM N° ' + str(reg_existente['numero_om']) if reg_existente['tiene_om'] else 'Sin OM'} "
                f"(Período: {reg_existente.get('periodo', '—')}). Guardar actualizará."
            )

        recarga = st.session_state.gom_om_recarga

        # Año
        anios_f = sorted([int(a) for a in df_raw["Anio"].dropna().unique()]) \
                  if "Anio" in df_raw.columns else [datetime.date.today().year]
        anio_actual = datetime.date.today().year
        anio_idx = anios_f.index(anio_actual) if anio_actual in anios_f else len(anios_f) - 1
        anio_sel = st.selectbox("Año *", options=anios_f, index=anio_idx,
                                key=f"gom_anio_{recarga}")

        # Mes del registro
        _MESES_ORDEN = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                        "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        df_per = df_raw[df_raw["Anio"] == anio_sel] if "Anio" in df_raw.columns else df_raw
        meses_disp_modal = [m for m in _MESES_ORDEN
                            if m in df_per["Mes"].dropna().unique().tolist()] \
                           if "Mes" in df_per.columns else _MESES_ORDEN
        edit_data      = reg_existente or {}
        periodo_presel = edit_data.get("periodo", "")
        per_opts       = ["— Selecciona —"] + meses_disp_modal
        per_idx        = per_opts.index(periodo_presel) if periodo_presel in per_opts else 0
        periodo_sel    = st.selectbox("Mes *", options=per_opts, index=per_idx,
                                      key=f"gom_periodo_{recarga}")
        periodo_val    = periodo_sel if periodo_sel != "— Selecciona —" else None

        # ¿Se abrió OM?
        tiene_om_default = "SI" if edit_data.get("tiene_om") else "NO"
        tiene_om_radio   = st.radio(
            "¿Se abrió Oportunidad de Mejora? *",
            options=["SI", "NO"],
            index=0 if tiene_om_default == "SI" else 1,
            horizontal=True,
            key=f"gom_radio_{recarga}",
        )

        numero_om  = None
        comentario = ""

        if tiene_om_radio == "SI":
            num_default = int(edit_data["numero_om"]) if edit_data.get("numero_om") else 1
            numero_om   = st.number_input("Número de OM *", min_value=1, step=1,
                                          value=num_default, key=f"gom_num_{recarga}")
            info_om = _lookup_om_xlsx(str(int(numero_om)))
            if info_om:
                st.markdown(
                    f"""<div style="background:#E8F5E9;border-radius:6px;padding:10px;
                        border-left:3px solid #43A047;font-size:0.9rem;margin-top:6px;">
                        <b>OM {int(numero_om)} en OM.xlsx</b><br>
                        Estado: <b>{info_om['Estado']}</b> &nbsp;|&nbsp;
                        Avance: <b>{info_om['Avance']}</b> &nbsp;|&nbsp;
                        Cierre estimado: <b>{info_om['F_cierre']}</b>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.warning(f"N° {int(numero_om)} no encontrado en OM.xlsx.")
        else:
            com_default = edit_data.get("comentario", "")
            comentario  = st.text_area(
                "Comentario / Justificación *",
                value=com_default,
                placeholder="Describe por qué no se abrió OM (mín. 20 caracteres)...",
                key=f"gom_comentario_{recarga}",
            )
            char_count = len(comentario)
            color_cnt  = "green" if char_count >= 20 else "red"
            st.markdown(f"<small style='color:{color_cnt}'>{char_count}/20 mínimos</small>",
                        unsafe_allow_html=True)

        # Validación
        errores = []
        if periodo_val is None:
            errores.append("Selecciona un mes.")
        if tiene_om_radio == "SI" and (numero_om is None or numero_om < 1):
            errores.append("Ingresa un número de OM válido.")
        if tiene_om_radio == "NO" and len(comentario) < 20:
            errores.append(f"Comentario mínimo 20 caracteres ({len(comentario)} actuales).")

        formulario_valido = len(errores) == 0
        lbl_btn = "💾 Actualizar" if reg_existente else "💾 Guardar"

        st.markdown("")
        btn_g, btn_c = st.columns(2)
        with btn_g:
            if st.button(lbl_btn, disabled=not formulario_valido,
                         use_container_width=True, type="primary",
                         key=f"gom_guardar_{recarga}"):
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
                    st.success("✅ Registro guardado.")
                    st.session_state.gom_om_recarga   += 1
                    st.session_state.gom_modal_id      = None
                    st.rerun()
                else:
                    st.error("❌ No se pudo guardar.")
        with btn_c:
            if st.button("✖ Cerrar", use_container_width=True,
                         key=f"gom_cerrar_{recarga}"):
                st.session_state.gom_modal_id = None
                st.rerun()

        if errores:
            for err in errores:
                st.caption(f"⚠️ {err}")

    with col_hist:
        st.markdown("#### Histórico del indicador")
        df_hist_ind = df_raw[df_raw["Id"] == id_indicador].sort_values("Fecha")
        if not df_hist_ind.empty:
            fig_h = grafico_historico_indicador(df_hist_ind, titulo=nombre_ind)
            st.plotly_chart(fig_h, use_container_width=True)
            df_th = tabla_historica_indicador(df_hist_ind)
            st.dataframe(df_th, use_container_width=True, hide_index=True)
        else:
            st.info("Sin histórico disponible.")


# ══════════════════════════════════════════════════════════════════════════════
# TÍTULO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# Gestión de Oportunidades de Mejora")
st.markdown("<div class='section-panel'>", unsafe_allow_html=True)

# ── Filtros globales (siempre visibles, dependientes en cascada) ──────────────
_col_proc_gom = "ProcesoPadre" if "ProcesoPadre" in df_raw.columns else "Proceso"

# Fila 1: Año, Mes, Proceso (padre), Subproceso
_fc1, _fc2, _fc3, _fc4 = st.columns(4)
with _fc1:
    anios_sel = st.multiselect("Año", options=anios_disp, default=default_año,
                                key="gom_filtro_anio")
with _fc2:
    meses_sel = st.multiselect("Mes", options=meses_disp, default=[],
                                key="gom_filtro_mes")
with _fc3:
    _procs_all = sorted(df_raw[_col_proc_gom].dropna().unique().tolist()) \
                 if _col_proc_gom in df_raw.columns else []
    _proc_opts_gom = [""] + _procs_all
    _f_proc_gom = st.selectbox("Proceso", _proc_opts_gom, key="gom_filtro_proc_top",
                               format_func=lambda x: "— Todos —" if x == "" else x)
with _fc4:
    # Subproceso depende del Proceso seleccionado
    _df_sub_pool = df_raw.copy()
    if _f_proc_gom and _col_proc_gom in _df_sub_pool.columns:
        _df_sub_pool = _df_sub_pool[_df_sub_pool[_col_proc_gom] == _f_proc_gom]
    _sub_all = sorted(_df_sub_pool["Proceso"].dropna().unique().tolist()) \
               if "Proceso" in _df_sub_pool.columns else []
    _sub_opts_gom = [""] + _sub_all
    _f_sub_gom = st.selectbox("Subproceso", _sub_opts_gom, key="gom_filtro_sub",
                              format_func=lambda x: "— Todos —" if x == "" else x)

# Fila 2: ID, Indicador, Categoría
_fc5, _fc6, _fc7 = st.columns(3)
with _fc5:
    _f_id_gom = st.text_input("ID", key="gom_filtro_id", placeholder="Buscar ID...")
with _fc6:
    _f_nom_gom = st.text_input("Indicador", key="gom_filtro_nom", placeholder="Buscar nombre...")
with _fc7:
    _cats_disp = [c for c in ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento"]
                  if c in df_raw["Categoria"].unique()] if "Categoria" in df_raw.columns else []
    _cat_sel = st.multiselect("Categoría", options=_cats_disp, default=[], key="gom_filtro_cat")

# ── Aplicar filtros ──────────────────────────────────────────────────────────
df = df_raw.copy()
if anios_sel:
    df = df[df["Anio"].isin(anios_sel)]
if meses_sel:
    df = df[df["Mes"].isin(meses_sel)]
if _f_proc_gom and _col_proc_gom in df.columns:
    df = df[df[_col_proc_gom] == _f_proc_gom]
if _f_sub_gom and "Proceso" in df.columns:
    df = df[df["Proceso"] == _f_sub_gom]
if _f_id_gom.strip():
    df = df[df["Id"].astype(str).str.contains(_f_id_gom.strip(), case=False, na=False)]
if _f_nom_gom.strip() and "Indicador" in df.columns:
    df = df[df["Indicador"].astype(str).str.contains(_f_nom_gom.strip(), case=False, na=False)]
if _cat_sel and "Categoria" in df.columns:
    df = df[df["Categoria"].isin(_cat_sel)]

df_ultimo    = obtener_ultimo_registro(df)
df_con_datos = df_ultimo[df_ultimo["Cumplimiento_norm"].notna()]
om_dict      = registros_om_como_dict()

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

# Calcular retrasadas para badge
hoy = pd.Timestamp(datetime.date.today())
_COL_FECHA_LIM_PA = next((c for c in df_pa.columns if "fecha límite de ejecución" in c.lower()
                          or "fecha limite de ejecucion" in c.lower()), None) if not df_pa.empty else None
_COL_ESTADO_PA    = next((c for c in df_pa.columns if "estado (plan" in c.lower()), None) if not df_pa.empty else None
n_retrasadas = 0
if not df_pa.empty and _COL_FECHA_LIM_PA and _COL_ESTADO_PA:
    mask_ret = (
        pd.to_datetime(df_pa[_COL_FECHA_LIM_PA], errors="coerce") < hoy
    ) & (df_pa[_COL_ESTADO_PA].astype(str).str.strip() != "Ejecutado")
    n_retrasadas = int(mask_ret.sum())

n_peligro = int((df_con_datos["Categoria"] == "Peligro").sum())
n_alerta  = int((df_con_datos["Categoria"] == "Alerta").sum())
label_tab2 = f"⚠️ Seguimiento OM ({n_retrasadas} retrasadas)" if n_retrasadas else "Seguimiento OM"

tab1, tab2 = st.tabs([
    f"🔴 Indicadores en Riesgo ({n_peligro} peligro · {n_alerta} alerta)",
    label_tab2,
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — IDENTIFICACIÓN + REGISTRO OM (modal)
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("<div class='section-panel'>", unsafe_allow_html=True)
    total = len(df_con_datos)

    # ── Semáforo ──────────────────────────────────────────────────────────────
    st.markdown("### Semáforo de Desempeño")
    st.caption("Haz clic en una categoría para filtrar la tabla.")

    semaforo_cfg = [
        ("Sobrecumplimiento", "🔵", NIVEL_COLOR["Sobrecumplimiento"]),
        ("Cumplimiento",      "🟢", NIVEL_COLOR["Cumplimiento"]),
        ("Alerta",            "🟡", NIVEL_COLOR["Alerta"]),
        ("Peligro",           "🔴", NIVEL_COLOR["Peligro"]),
    ]
    col_sems = st.columns(4)
    for i, (cat, icon, color) in enumerate(semaforo_cfg):
        n_cat  = int((df_con_datos["Categoria"] == cat).sum())
        pct    = round(n_cat / total * 100, 1) if total > 0 else 0
        activa = st.session_state.gom_cat_activa == cat
        borde  = f"3px solid {color}" if activa else f"2px solid {color}55"
        bg     = f"#0F2640" if activa else "#1A3A5C"
        with col_sems[i]:
            st.markdown(
                f"""<div style="border:{borde};border-radius:10px;padding:14px;
                    text-align:center;background:{bg};cursor:pointer;
                    box-shadow:0 3px 10px rgba(0,0,0,0.3);">
                    <span style="font-size:2rem">{icon}</span><br>
                    <strong style="font-size:1.4rem;color:{color}">{n_cat}</strong><br>
                    <span style="font-size:0.85rem;color:#B3D9FF">{cat}</span><br>
                    <span style="font-size:0.8rem;color:#7FB3D3">{pct}%</span>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button(f"Ver {cat}", key=f"gom_sem_{cat}", use_container_width=True):
                st.session_state.gom_cat_activa  = cat
                st.session_state.gom_sel_proceso = None
                st.rerun()

    st.markdown("---")

    # ── Indicadores que deterioraron ──────────────────────────────────────────
    _ORDEN_CAT = {"Peligro": 0, "Alerta": 1, "Cumplimiento": 2, "Sobrecumplimiento": 3, "Sin dato": -1}
    if "Id" in df_raw.columns and "Fecha" in df_raw.columns:
        df_s = df_raw[df_raw["Cumplimiento_norm"].notna()].sort_values("Fecha")
        rows_det = []
        for id_ind, grupo in df_s.groupby("Id"):
            if len(grupo) < 2:
                continue
            prev, curr = grupo.iloc[-2], grupo.iloc[-1]
            cat_prev, cat_curr = str(prev.get("Categoria", "Sin dato")), str(curr.get("Categoria", "Sin dato"))
            if (_ORDEN_CAT.get(cat_curr, -1) < _ORDEN_CAT.get(cat_prev, -1)
                    and cat_curr in ("Peligro", "Alerta")):
                delta = round((curr["Cumplimiento_norm"] - prev["Cumplimiento_norm"]) * 100, 1) \
                        if pd.notna(curr["Cumplimiento_norm"]) and pd.notna(prev["Cumplimiento_norm"]) else None
                rows_det.append({
                    "Id": id_ind,
                    "Indicador": str(curr.get("Indicador", "")),
                    "Proceso":   str(curr.get("Proceso", "")),
                    "Cat. anterior": cat_prev,
                    "Cat. actual":   cat_curr,
                    "Δ Cumplimiento%": f"{delta:+.1f}%" if delta is not None else "—",
                })
        df_det = pd.DataFrame(rows_det)
        if not df_det.empty:
            with st.expander(f"⬇️ Indicadores que deterioraron de categoría ({len(df_det)})", expanded=False):
                def _estilo_det(row):
                    bg = NIVEL_BG.get(str(row.get("Cat. actual", "")), "")
                    return [f"background-color:{bg}" if c == "Cat. actual" else "" for c in row.index]
                st.dataframe(df_det.style.apply(_estilo_det, axis=1),
                             use_container_width=True, hide_index=True,
                             column_config={"Indicador": st.column_config.TextColumn("Indicador", width="large")})

    # ── Categoría activa ──────────────────────────────────────────────────────
    cat_act   = st.session_state.gom_cat_activa
    df_cat    = df_con_datos[df_con_datos["Categoria"] == cat_act].copy()
    df_cat["Cumplimiento%"] = (df_cat["Cumplimiento_norm"] * 100).round(1)
    color_act = NIVEL_COLOR.get(cat_act, "#9E9E9E")

    # Persistencia en riesgo
    if not df_cat.empty:
        df_cat["Períodos en riesgo"] = df_cat["Id"].apply(
            lambda i: calcular_meses_en_peligro(
                df_raw[df_raw["Id"] == i].sort_values("Fecha", ascending=False)
                .assign(Categoria=df_raw[df_raw["Id"] == i]["Categoria"])
            )
        )
        df_cat["Estado OM"] = df_cat["Id"].apply(
            lambda i: "✅ Con OM" if om_dict.get(i, {}).get("tiene_om") else "❌ Sin OM"
        )
        df_cat["N° OM"] = df_cat["Id"].apply(
            lambda i: om_dict.get(i, {}).get("numero_om", "")
        )

    # ── Gráficos ──────────────────────────────────────────────────────────────
    st.markdown(f"### Visualizaciones — {cat_act}")
    col_g1, col_g2 = st.columns(2)

    sel_proceso = st.session_state.get("gom_sel_proceso")

    with col_g1:
        st.markdown("**Top 10 — Cumplimiento**")
        st.caption("Clic en una barra para ver detalle y registrar OM.")
        if cat_act in ("Peligro", "Alerta"):
            df_top = df_cat.nsmallest(10, "Cumplimiento_norm")
            titulo_top = "10 indicadores con menor cumplimiento"
        else:
            df_top = df_cat.nlargest(10, "Cumplimiento_norm")
            titulo_top = "10 indicadores con mayor cumplimiento"

        if not df_top.empty:
            etiquetas  = (df_top["Id"] + " — " + df_top["Indicador"].str[:35]).tolist()
            per_riesgo = df_top.get("Períodos en riesgo", pd.Series([0]*len(df_top))).fillna(0).astype(int).tolist()
            fig_top = go.Figure(go.Bar(
                x=df_top["Cumplimiento%"].tolist(),
                y=etiquetas,
                orientation="h",
                marker_color=color_act,
                text=df_top["Cumplimiento%"].round(1).astype(str) + "%",
                textposition="outside",
                customdata=list(zip(df_top["Id"].tolist(), per_riesgo)),
                hovertemplate="<b>%{y}</b><br>Cumplimiento: %{x:.1f}%<br>Períodos en riesgo: %{customdata[1]}<extra></extra>",
            ))
            fig_top.update_layout(
                height=400, title=titulo_top,
                xaxis=dict(title="Cumplimiento (%)", ticksuffix="%"),
                yaxis=dict(title="", autorange="reversed"),
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=60, t=30, b=30),
            )
            ev_top = st.plotly_chart(fig_top, use_container_width=True,
                                     on_select="rerun", selection_mode="points", key="gom_top10")
            if ev_top and ev_top.selection and ev_top.selection.get("points"):
                pt_idx = ev_top.selection["points"][0].get("point_index")
                if pt_idx is not None:
                    st.session_state.gom_modal_id = df_top["Id"].iloc[pt_idx]
                    st.rerun()
        else:
            st.info("Sin datos para esta categoría.")

    with col_g2:
        st.markdown("**Distribución por Proceso**")
        st.caption("Clic en un segmento para filtrar la tabla.")
        if not df_cat.empty and "Proceso" in df_cat.columns:
            proc_counts = df_cat.groupby("Proceso").size().reset_index(name="count")
            proc_colors = ["#1A3A5C","#1565C0","#0277BD","#0288D1","#0097A7",
                           "#00897B","#43A047","#7CB342","#C0CA33","#FDD835"]
            fig_dona = go.Figure(go.Pie(
                labels=proc_counts["Proceso"].tolist(),
                values=proc_counts["count"].tolist(),
                hole=0.4,
                marker=dict(colors=proc_colors[:len(proc_counts)]),
                hovertemplate="<b>%{label}</b><br>%{value} indicadores<br>%{percent}<extra></extra>",
            ))
            fig_dona.update_layout(height=400, legend=dict(orientation="v", x=1.02),
                                   plot_bgcolor="white", paper_bgcolor="white",
                                   margin=dict(t=20, b=20))
            ev_dona = st.plotly_chart(fig_dona, use_container_width=True,
                                      on_select="rerun", key="gom_dona_proc")
            if ev_dona and ev_dona.selection and ev_dona.selection.get("points"):
                clicked_proc = ev_dona.selection["points"][0].get("label")
                if clicked_proc and clicked_proc != sel_proceso:
                    st.session_state.gom_sel_proceso = clicked_proc
                    st.session_state.gom_sel_heatmap_proc = None
                    st.rerun()
        else:
            st.info("Sin datos.")

    st.markdown("---")

    # ── Filtro activo sobre tabla ──────────────────────────────────────────────
    if sel_proceso:
        fc1, fc2 = st.columns([7, 1])
        with fc1:
            st.info(f"Filtro gráfico: **{sel_proceso}**")
        with fc2:
            if st.button("✖ Limpiar", key="gom_clear_graf"):
                st.session_state.gom_sel_proceso = None
                st.rerun()

    # ── Tabla detallada ────────────────────────────────────────────────────────
    titulo_tabla = f"### Tabla — {cat_act}"
    if sel_proceso:
        titulo_tabla += f" · Proceso: *{sel_proceso}*"
    st.markdown(titulo_tabla)
    st.caption("Selecciona una fila para registrar o actualizar la OM asociada.")

    df_tabla = df_cat.copy()
    if sel_proceso and "Proceso" in df_tabla.columns:
        df_tabla = df_tabla[df_tabla["Proceso"] == sel_proceso]

    df_tabla["Cumplimiento%"] = df_tabla["Cumplimiento_norm"].apply(
        lambda x: f"{round(x*100,1)}%" if pd.notna(x) else "—"
    )

    def _estilo_cat(row):
        bg = NIVEL_BG.get(str(row.get("Categoria", "")), "")
        return [f"background-color:{bg}" if c == "Categoria" else "" for c in row.index]

    cols_show = ["Id", "Indicador", "Proceso", "Periodicidad", "Mes",
                 "Cumplimiento%", "Categoria", "Períodos en riesgo", "Estado OM", "N° OM"]
    cols_disp = [c for c in cols_show if c in df_tabla.columns]

    st.caption(f"Mostrando **{len(df_tabla)}** indicadores — clic en fila para registrar OM")
    ev_tabla = st.dataframe(
        df_tabla[cols_disp].style.apply(_estilo_cat, axis=1),
        use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row",
        key="gom_tabla_riesgo",
        column_config={
            "Indicador":          st.column_config.TextColumn("Indicador", width="large"),
            "Períodos en riesgo": st.column_config.NumberColumn("Períodos en riesgo", format="%d"),
            "Estado OM":          st.column_config.TextColumn("Estado OM", width="small"),
        },
    )

    col_exp, _ = st.columns([1, 5])
    with col_exp:
        st.download_button(
            "📥 Exportar Excel",
            data=exportar_excel(df_tabla[cols_disp], "Indicadores_en_Riesgo"),
            file_name=f"indicadores_{cat_act.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ── Detectar selección en tabla ────────────────────────────────────────────
    _tabla_tiene_sel = (ev_tabla and ev_tabla.selection and ev_tabla.selection.get("rows"))
    if _tabla_tiene_sel:
        idx = ev_tabla.selection["rows"][0]
        if "Id" in df_tabla.columns and idx < len(df_tabla):
            selected_id = df_tabla["Id"].iloc[idx]
            if st.session_state.gom_modal_id != selected_id:
                st.session_state.gom_modal_id = selected_id
                st.rerun()

    # ── Abrir modal SOLO si hay selección activa (tabla o gráfico) ─────────────
    _hay_sel_top10 = False
    try:
        _hay_sel_top10 = bool(ev_top and ev_top.selection and ev_top.selection.get("points"))
    except NameError:
        pass
    if st.session_state.gom_modal_id and (_tabla_tiene_sel or _hay_sel_top10):
        _modal_registro_om(st.session_state.gom_modal_id)
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SEGUIMIENTO DE OM
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-panel'>", unsafe_allow_html=True)
    if df_om_xl.empty:
        st.error("No se encontró **OM.xlsx** en `data/raw/`.")
        st.stop()

    # ── Paleta ────────────────────────────────────────────────────────────────
    _C = {
        "Cerrada":   COLORES["cumplimiento"],
        "Ejecución": "#1976D2",
        "Abierta":   COLORES["alerta"],
        "Retrasada": COLORES["peligro"],
        "primary":   COLORES["primario"],
    }

    # ── Detectar columnas clave ────────────────────────────────────────────────
    _COL_AV       = next((c for c in df_om_xl.columns if "avance"           in c.lower()), None)
    _COL_ESTADO   = next((c for c in df_om_xl.columns if c.lower() == "estado"),           None)
    _COL_DIAS     = next((c for c in df_om_xl.columns if "días vencida"    in c.lower()
                                                     or "dias vencida"    in c.lower()), None)
    _COL_PROC     = next((c for c in df_om_xl.columns if c.lower() == "procesos"),        None)
    _COL_FUENTE   = next((c for c in df_om_xl.columns if c.lower() == "fuente"),          None)
    _COL_TIPO_A   = next((c for c in df_om_xl.columns if "tipo de acción"  in c.lower()
                                                     or "tipo de accion"  in c.lower()), None)
    _COL_TIPO_O   = next((c for c in df_om_xl.columns if "tipo de oportunidad" in c.lower()), None)
    _COL_FECHA_ID = next((c for c in df_om_xl.columns if "identificación"  in c.lower()
                                                     or "identificacion"  in c.lower()), None)
    _COL_FECHA_EST= next((c for c in df_om_xl.columns if "estimada" in c.lower() and "cierre" in c.lower()), None)
    _COL_FECHA_REAL=next((c for c in df_om_xl.columns if "real"     in c.lower() and "cierre" in c.lower()), None)
    _COL_DESC     = next((c for c in df_om_xl.columns if "descrip"         in c.lower()), None)

    _COL_PA_ID    = next((c for c in df_pa.columns if "id oportunidad"         in c.lower()), None) if not df_pa.empty else None
    _COL_PROC_RESP= next((c for c in df_pa.columns if "proceso responsable"    in c.lower()), None) if not df_pa.empty else None
    _COL_ESTADO_PA= next((c for c in df_pa.columns if "estado (plan"           in c.lower()), None) if not df_pa.empty else None

    # ── Tasa de cierre en plazo ────────────────────────────────────────────────
    n_atiempo = n_tarde = pct_plazo = None
    if _COL_ESTADO and _COL_FECHA_EST and _COL_FECHA_REAL:
        df_cerr = df_om_xl[df_om_xl[_COL_ESTADO] == "Cerrada"].copy()
        if not df_cerr.empty:
            f_est  = pd.to_datetime(df_cerr[_COL_FECHA_EST],  errors="coerce")
            f_real = pd.to_datetime(df_cerr[_COL_FECHA_REAL], errors="coerce")
            validos = f_est.notna() & f_real.notna()
            if validos.any():
                n_atiempo  = int((f_real[validos] <= f_est[validos]).sum())
                n_tarde    = int(validos.sum()) - n_atiempo
                pct_plazo  = round(n_atiempo / validos.sum() * 100, 1)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_om     = len(df_om_xl)
    cnt_cerradas = int((df_om_xl[_COL_ESTADO] == "Cerrada").sum()) if _COL_ESTADO else 0
    cnt_abiertas = total_om - cnt_cerradas
    avance_prom  = float(df_om_xl[_COL_AV].mean()) if _COL_AV else 0.0
    cnt_vencidas = int((df_om_xl[_COL_DIAS] > 0).sum()) if _COL_DIAS else 0
    cnt_pa       = len(df_pa)

    k = st.columns(6)
    k[0].metric("Total OM",         total_om)
    k[1].metric("Abiertas",         cnt_abiertas)
    k[2].metric("Cerradas",         cnt_cerradas)
    k[3].metric("Avance promedio",  f"{avance_prom:.1f}%")
    k[4].metric("OM vencidas",      cnt_vencidas)
    k[5].metric("Acciones de plan", cnt_pa)

    if pct_plazo is not None:
        st.markdown(
            f"""<div style="background:#E8F5E9;border-radius:6px;padding:8px 16px;
                border-left:3px solid #43A047;margin-top:6px;font-size:0.9rem;">
                ✅ <b>Eficacia de cierre:</b> {pct_plazo}% de las OM cerraron dentro del plazo
                &nbsp;·&nbsp; {n_atiempo} a tiempo · {n_tarde} con retraso
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Filtros ────────────────────────────────────────────────────────────────
    def _opts(df, col):
        if col is None or col not in df.columns:
            return [""]
        return [""] + sorted(df[col].dropna().astype(str).unique().tolist())

    with st.expander("🔍 Filtros", expanded=True):
        fc = st.columns(4)
        f_estado = fc[0].selectbox("Estado",        _opts(df_om_xl, _COL_ESTADO),
                                   key="gom2_estado", format_func=lambda x: "— Todos —" if x == "" else x)
        f_tipo_a = fc[1].selectbox("Tipo de acción", _opts(df_om_xl, _COL_TIPO_A),
                                   key="gom2_tipo_a", format_func=lambda x: "— Todos —" if x == "" else x)
        f_proc   = fc[2].selectbox("Proceso",        _opts(df_om_xl, _COL_PROC),
                                   key="gom2_proc",   format_func=lambda x: "— Todos —" if x == "" else x)
        # Fuente: predeterminada "Indicadores"
        _opts_fuente = _opts(df_om_xl, _COL_FUENTE)
        _idx_fuente  = _opts_fuente.index("Indicadores") if "Indicadores" in _opts_fuente else 0
        f_fuente = fc[3].selectbox("Fuente",         _opts_fuente,
                                   index=_idx_fuente,
                                   key="gom2_fuente", format_func=lambda x: "— Todos —" if x == "" else x)

    df_f = df_om_xl.copy()
    if f_estado and _COL_ESTADO: df_f = df_f[df_f[_COL_ESTADO] == f_estado]
    if f_tipo_a and _COL_TIPO_A: df_f = df_f[df_f[_COL_TIPO_A] == f_tipo_a]
    if f_proc   and _COL_PROC:   df_f = df_f[df_f[_COL_PROC]   == f_proc]
    if f_fuente and _COL_FUENTE: df_f = df_f[df_f[_COL_FUENTE] == f_fuente]

    # ── Sub-tabs de seguimiento ────────────────────────────────────────────────
    ret_label = f"⚠️ Retrasadas ({n_retrasadas})" if n_retrasadas else "✅ Retrasadas (0)"
    st2_anal, st2_info, st2_ret = st.tabs(["📊 Análisis", "📋 Información", ret_label])

    # ─── Sub-tab Análisis ────────────────────────────────────────────────────
    with st2_anal:
        if df_f.empty:
            st.info("Sin datos con los filtros aplicados.")
        else:
            row1 = st.columns(2)
            with row1[0]:
                if _COL_ESTADO:
                    cnt_e = df_f[_COL_ESTADO].value_counts().reset_index()
                    cnt_e.columns = ["Estado", "N"]
                    fig = go.Figure(go.Pie(
                        labels=cnt_e["Estado"], values=cnt_e["N"], hole=0.55,
                        marker_colors=[_C.get(e, _C["primary"]) for e in cnt_e["Estado"]],
                        textinfo="label+percent",
                        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
                    ))
                    fig.update_layout(title="Distribución por Estado", height=300,
                                      margin=dict(l=10, r=10, t=50, b=10))
                    st.plotly_chart(fig, use_container_width=True)

            with row1[1]:
                if _COL_PROC and _COL_AV:
                    av_proc = (df_f.groupby(_COL_PROC)[_COL_AV].mean().reset_index()
                               .rename(columns={_COL_AV: "Avance"})
                               .sort_values("Avance"))
                    av_proc["color"] = av_proc["Avance"].apply(
                        lambda v: _C["Retrasada"] if v < 30 else _C["Abierta"] if v < 70 else _C["Cerrada"]
                    )
                    fig = go.Figure(go.Bar(
                        x=av_proc["Avance"], y=av_proc[_COL_PROC], orientation="h",
                        marker_color=av_proc["color"],
                        text=av_proc["Avance"].apply(lambda v: f"{v:.1f}%"),
                        textposition="outside",
                        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
                    ))
                    fig.update_layout(
                        title="Avance promedio por Proceso",
                        xaxis=dict(range=[0, 115], title="Avance (%)"), yaxis_title="",
                        height=max(280, len(av_proc) * 30 + 80),
                        margin=dict(l=10, r=50, t=50, b=10),
                    )
                    ev_avproc = st.plotly_chart(fig, use_container_width=True,
                                                on_select="rerun", key="gom2_av_proc")
                    if ev_avproc and ev_avproc.selection and ev_avproc.selection.get("points"):
                        proc_click = ev_avproc.selection["points"][0].get("y")
                        if proc_click:
                            st.session_state["gom_filtro_proc_tab2"] = proc_click
                            st.rerun()

            # Estado por proceso (apiladas) + Scatter
            row2 = st.columns(2)
            with row2[0]:
                if _COL_PROC and _COL_ESTADO:
                    pivot = df_f.groupby([_COL_PROC, _COL_ESTADO]).size().reset_index(name="N")
                    fig = go.Figure()
                    for est in pivot[_COL_ESTADO].unique():
                        sub = pivot[pivot[_COL_ESTADO] == est]
                        fig.add_trace(go.Bar(
                            name=est, x=sub[_COL_PROC], y=sub["N"],
                            marker_color=_C.get(est, _C["primary"]),
                            hovertemplate=f"{est}: %{{y}}<extra></extra>",
                        ))
                    fig.update_layout(
                        barmode="stack", title="Estado de OM por Proceso",
                        xaxis_title="", yaxis_title="N° OM",
                        xaxis_tickangle=-35, height=340,
                        margin=dict(l=10, r=10, t=50, b=100),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    )
                    st.plotly_chart(fig, use_container_width=True)

            with row2[1]:
                if _COL_AV and _COL_DIAS and _COL_ESTADO:
                    st.markdown("**Días vencida por Estado**")
                    df_dias = df_f[[_COL_ESTADO, _COL_DIAS]].dropna()
                    if not df_dias.empty:
                        fig_box = go.Figure()
                        for est in ["Ejecución", "Abierta", "Cerrada"]:
                            sub = df_dias[df_dias[_COL_ESTADO] == est]
                            if not sub.empty:
                                fig_box.add_trace(go.Box(
                                    y=sub[_COL_DIAS], name=est,
                                    marker_color=_C.get(est, _C["primary"]),
                                    boxmean=True,
                                ))
                        fig_box.update_layout(
                            yaxis_title="Días vencida", showlegend=False,
                            height=340, margin=dict(l=10, r=10, t=30, b=30),
                        )
                        st.plotly_chart(fig_box, use_container_width=True)

    # ─── Sub-tab Información ─────────────────────────────────────────────────
    with st2_info:
        _COLS_OM = ["Id", "Fecha de identificación", "Avance (%)", "Estado",
                    "Tipo de acción", "Tipo de oportunidad", "Procesos", "Fuente",
                    "Descripción", "Fecha estimada de cierre", "Fecha real de cierre",
                    "Días vencida", "Comentario"]

        filtro_proc_t2 = st.session_state.get("gom_filtro_proc_tab2")
        if filtro_proc_t2 and _COL_PROC:
            fpt1, fpt2 = st.columns([8, 1])
            with fpt1:
                st.info(f"Filtro desde Análisis: **{filtro_proc_t2}**")
            with fpt2:
                if st.button("✖", key="gom2_clear_proc"):
                    st.session_state["gom_filtro_proc_tab2"] = None
                    st.rerun()
            df_info = df_f[df_f[_COL_PROC] == filtro_proc_t2].copy() if _COL_PROC in df_f.columns else df_f.copy()
        else:
            df_info = df_f.copy()

        cols_show = [c for c in _COLS_OM if c in df_info.columns]
        df_tabla_om = df_info[cols_show].copy()
        if _COL_AV and _COL_AV in df_tabla_om.columns:
            df_tabla_om[_COL_AV] = df_tabla_om[_COL_AV].apply(
                lambda v: f"{v:.1f}%" if pd.notna(v) else "—"
            )
        for _fc in ["Fecha de identificación", "Fecha estimada de cierre", "Fecha real de cierre"]:
            if _fc in df_tabla_om.columns:
                df_tabla_om[_fc] = (pd.to_datetime(df_tabla_om[_fc], errors="coerce")
                                    .dt.strftime("%d/%m/%Y").fillna("—"))

        st.caption(f"Mostrando **{len(df_tabla_om)}** oportunidades — selecciona fila para ver Plan de Acción")
        ev_om = st.dataframe(
            df_tabla_om, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="single-row",
            column_config={
                "Descripción": st.column_config.TextColumn("Descripción", width="large"),
                "Comentario":  st.column_config.TextColumn("Comentario",  width="medium"),
                "Días vencida":st.column_config.NumberColumn("Días vencida", format="%d"),
            },
        )
        st.download_button(
            "📥 Exportar OM (Excel)",
            data=exportar_excel(df_tabla_om, "Oportunidades_de_Mejora"),
            file_name="oportunidades_mejora.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="gom2_exp_om",
        )

        if ev_om.selection and ev_om.selection.rows:
            row_om = df_info.iloc[ev_om.selection.rows[0]]
            om_id  = str(row_om.get("Id", "")).strip()
            st.markdown(f"### Plan de Acción — OM **{om_id}**")
            with st.expander("Detalle de la Oportunidad", expanded=True):
                d1, d2, d3 = st.columns(3)
                d1.write(f"**Tipo de acción:** {row_om.get('Tipo de acción', '—')}")
                d2.write(f"**Proceso:** {row_om.get('Procesos', '—')}")
                d3.write(f"**Estado:** {row_om.get('Estado', '—')}")
                d3.write(f"**Avance:** {row_om.get(_COL_AV, '—') if _COL_AV else '—'}")
                if _COL_DESC:
                    st.write(f"**Descripción:** {row_om.get(_COL_DESC, '—')}")

            if not df_pa.empty and _COL_PA_ID:
                df_plan = df_pa[df_pa[_COL_PA_ID].astype(str) == om_id].copy()
                if df_plan.empty:
                    st.info(f"Sin acciones en Plan de Acción para OM **{om_id}**.")
                else:
                    _COLS_PA = ["Id Acción", "Descripción", "Acción", "Estado (Plan de Acción)",
                                "Proceso responsable", "Responsable de ejecución",
                                "Fecha límite de ejecución", "Avance (%)"]
                    cols_pa = [c for c in _COLS_PA if c in df_plan.columns]
                    df_ps   = df_plan[cols_pa].copy()
                    for col in df_ps.select_dtypes(include="datetime").columns:
                        df_ps[col] = df_ps[col].dt.strftime("%d/%m/%Y").fillna("—")
                    st.caption(f"**{len(df_ps)}** acción(es) asociada(s)")
                    st.dataframe(df_ps, use_container_width=True, hide_index=True,
                                 column_config={
                                     "Descripción": st.column_config.TextColumn("Descripción", width="large"),
                                     "Acción":      st.column_config.TextColumn("Acción",      width="large"),
                                 })
                    st.download_button(
                        "📥 Exportar Plan de Acción",
                        data=exportar_excel(df_ps, f"Plan_OM_{om_id}"),
                        file_name=f"plan_accion_om_{om_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="gom2_exp_pa",
                    )

    # ─── Sub-tab Retrasadas ──────────────────────────────────────────────────
    with st2_ret:
        if df_pa.empty or not all([_COL_PA_ID, _COL_FECHA_LIM_PA, _COL_ESTADO_PA, _COL_PROC_RESP]):
            st.warning("Faltan columnas en el Plan de Acción.")
        else:
            mask_ret = (
                pd.to_datetime(df_pa[_COL_FECHA_LIM_PA], errors="coerce") < hoy
            ) & (df_pa[_COL_ESTADO_PA].astype(str).str.strip() != "Ejecutado")
            df_ret = df_pa[mask_ret].copy()

            r1, r2, r3 = st.columns(3)
            r1.metric("Acciones retrasadas", len(df_ret))
            r2.metric("Procesos afectados",
                      df_ret[_COL_PROC_RESP].nunique() if not df_ret.empty else 0)
            if not df_ret.empty and _COL_FECHA_LIM_PA:
                dias_max = int((hoy - pd.to_datetime(df_ret[_COL_FECHA_LIM_PA], errors="coerce").min()).days)
                r3.metric("Días máx. de retraso", dias_max)

            st.markdown("---")
            if df_ret.empty:
                st.success("✅ No hay acciones retrasadas.")
            else:
                resumen = (df_ret.groupby(_COL_PROC_RESP).size()
                           .reset_index(name="Acciones retrasadas")
                           .sort_values("Acciones retrasadas", ascending=False))
                col_g, col_t = st.columns([3, 2])
                with col_g:
                    fig = go.Figure(go.Bar(
                        x=resumen["Acciones retrasadas"], y=resumen[_COL_PROC_RESP],
                        orientation="h", marker_color=_C["Retrasada"],
                        text=resumen["Acciones retrasadas"], textposition="outside",
                        hovertemplate="%{y}: %{x} acciones<extra></extra>",
                    ))
                    fig.update_layout(
                        title=f"Acciones retrasadas por Proceso ({len(df_ret)} total)",
                        xaxis_title="N° acciones",
                        yaxis={"categoryorder": "total ascending"},
                        height=max(280, len(resumen) * 35 + 80),
                        margin=dict(l=10, r=50, t=50, b=30),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                with col_t:
                    st.dataframe(resumen, use_container_width=True, hide_index=True)

                with st.expander("Ver detalle completo"):
                    _cols_ret = [c for c in [_COL_PA_ID, _COL_PROC_RESP,
                                              "Descripción", "Acción", _COL_ESTADO_PA,
                                              _COL_FECHA_LIM_PA, "Responsable de ejecución"]
                                 if c and c in df_ret.columns]
                    df_ret_show = df_ret[_cols_ret].copy()
                    if _COL_FECHA_LIM_PA in df_ret_show.columns:
                        df_ret_show[_COL_FECHA_LIM_PA] = (
                            pd.to_datetime(df_ret_show[_COL_FECHA_LIM_PA], errors="coerce")
                            .dt.strftime("%d/%m/%Y").fillna("—")
                        )
                    st.dataframe(df_ret_show, use_container_width=True, hide_index=True,
                                 column_config={
                                     "Descripción": st.column_config.TextColumn("Descripción", width="large"),
                                     "Acción":      st.column_config.TextColumn("Acción",      width="large"),
                                 })
                    st.download_button(
                        "📥 Exportar retrasadas",
                        data=exportar_excel(df_ret_show, "Acciones_Retrasadas"),
                        file_name="acciones_retrasadas.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="gom2_exp_ret",
                    )
    st.markdown("</div>", unsafe_allow_html=True)
