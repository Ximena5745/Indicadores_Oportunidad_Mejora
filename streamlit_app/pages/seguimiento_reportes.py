from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Importes desde root
try:
    from components.charts import exportar_excel
    from core.config import CACHE_TTL
except (ImportError, ModuleNotFoundError):
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from components.charts import exportar_excel
    from core.config import CACHE_TTL

# Importes desde streamlit_app
try:
    from ..utils.formatting import id_limpio
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.formatting import id_limpio


RUTA_SEGUIMIENTO = Path(__file__).resolve().parents[2] / "data" / "output" / "Seguimiento_Reporte.xlsx"

# Ventana máxima en meses antes de marcar como vencido
_VENTANA_MESES: dict[str, int] = {
    "mensual": 1,
    "bimestral": 2,
    "trimestral": 3,
    "semestral": 6,
    "anual": 12,
}


def _nm(s: str) -> str:
    """Normaliza string a minúsculas sin tildes."""
    s = str(s or "").strip().lower()
    for a, b in (("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u")):
        s = s.replace(a, b)
    return s


def _ventana(periodicidad: str) -> int:
    return _VENTANA_MESES.get(_nm(periodicidad), 1)


def _detectar_vencidos(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (vencidos, por_vencer) basados en última fecha de reporte.

    Lógica:
    - Por cada indicador, busca el último registro con Estado=="Reportado".
    - Compara el año-mes de ese registro con el mes actual.
    - Si la diferencia supera la ventana de su periodicidad → Vencido.
    - Si la diferencia está entre 80-100 % de la ventana → Por vencer.
    """
    hoy = date.today()
    ym_actual = hoy.year * 12 + hoy.month

    needed = {"Id", "Año", "Mes", "Estado"}
    if not needed.issubset(df.columns):
        return pd.DataFrame(), pd.DataFrame()

    df_rep = df[df["Estado"].astype(str).str.strip() == "Reportado"].copy()
    df_rep["ym"] = (
        pd.to_numeric(df_rep["Año"], errors="coerce").fillna(0).astype(int) * 12
        + pd.to_numeric(df_rep["Mes"], errors="coerce").fillna(0).astype(int)
    )
    ultimo = df_rep.groupby("Id")["ym"].max().reset_index().rename(columns={"ym": "ultimo_ym"})

    # Metadatos base por indicador
    meta_cols = [c for c in ["Id", "Periodicidad", "Proceso", "Indicador"] if c in df.columns]
    meta = df[meta_cols].drop_duplicates(subset=["Id"])

    merged = meta.merge(ultimo, on="Id", how="left")
    merged["ultimo_ym"] = merged["ultimo_ym"].fillna(0).astype(int)
    merged["ventana"] = merged.get("Periodicidad", pd.Series("mensual", index=merged.index)).apply(_ventana)
    merged["diff_meses"] = ym_actual - merged["ultimo_ym"]

    vencidos = merged[merged["diff_meses"] > merged["ventana"]].copy()
    por_vencer = merged[
        (merged["diff_meses"] <= merged["ventana"])
        & (merged["diff_meses"] >= (merged["ventana"] * 0.8).astype(int))
        & (merged["diff_meses"] > 0)
    ].copy()

    return vencidos, por_vencer


@st.cache_data(ttl=CACHE_TTL, show_spinner="Cargando Tracking Mensual...")
def _cargar_tracking() -> pd.DataFrame:
    if not RUTA_SEGUIMIENTO.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(str(RUTA_SEGUIMIENTO), sheet_name="Tracking Mensual", engine="openpyxl")
    except Exception:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(id_limpio)
    if "Año" in df.columns:
        df["Año"] = pd.to_numeric(df["Año"], errors="coerce").astype("Int64")
    if "Mes" in df.columns:
        df["Mes"] = pd.to_numeric(df["Mes"], errors="coerce").astype("Int64")
    return df


def render():
    st.title("Seguimiento de Reportes")
    st.caption("Vista operativa de reportes mensuales por estado, proceso y periodicidad.")

    df = _cargar_tracking()
    if df.empty:
        st.error("No se encontró la hoja Tracking Mensual en data/output/Seguimiento_Reporte.xlsx.")
        return

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    # Meses en español
    MESES_OPCIONES = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]

    anios = sorted(pd.to_numeric(df.get("Año", pd.Series(dtype=float)), errors="coerce").dropna().astype(int).unique().tolist())
    # default: prefer 2025 if present, else the latest year
    with col_f1:
        year_options = ["Todos"] + anios
        if 2025 in anios:
            default_year = 2025
        else:
            default_year = anios[-1] if anios else "Todos"
        anio_sel = st.segmented_control("Año", options=year_options, default=default_year)

    meses_nums = sorted(pd.to_numeric(df.get("Mes", pd.Series(dtype=float)), errors="coerce").dropna().astype(int).unique().tolist())
    with col_f2:
        # map numeric months to names for display
        mes_names = [MESES_OPCIONES[m - 1] for m in meses_nums if 1 <= m <= 12]
        mes_options = ["Todos"] + mes_names
        # default to Diciembre if available
        default_mes_idx = mes_options.index("Diciembre") if "Diciembre" in mes_options else max(0, len(mes_options) - 1)
        mes_sel = st.selectbox("Mes", options=mes_options, index=default_mes_idx)

    procesos = sorted(df["Proceso"].dropna().astype(str).unique().tolist()) if "Proceso" in df.columns else []
    with col_f3:
        proceso_sel = st.selectbox("Proceso", options=["Todos"] + procesos)

    estados = sorted(df["Estado"].dropna().astype(str).unique().tolist()) if "Estado" in df.columns else []
    with col_f4:
        estado_sel = st.selectbox("Estado", options=["Todos"] + estados)

    df_view = df.copy()
    if anio_sel != "Todos" and "Año" in df_view.columns:
        df_view = df_view[df_view["Año"] == anio_sel]
    if mes_sel != "Todos" and "Mes" in df_view.columns:
        # mes_sel is a month name; map back to number
        try:
            mes_num = MESES_OPCIONES.index(mes_sel) + 1
            df_view = df_view[df_view["Mes"] == mes_num]
        except Exception:
            # fallback: if mes_sel was numeric-like, compare directly
            try:
                df_view = df_view[df_view["Mes"] == int(mes_sel)]
            except Exception:
                pass
    if proceso_sel != "Todos" and "Proceso" in df_view.columns:
        df_view = df_view[df_view["Proceso"] == proceso_sel]
    if estado_sel != "Todos" and "Estado" in df_view.columns:
        df_view = df_view[df_view["Estado"] == estado_sel]

    total = len(df_view)
    reportado = int((df_view.get("Estado", pd.Series(dtype=str)) == "Reportado").sum())
    pendiente = int((df_view.get("Estado", pd.Series(dtype=str)) == "Pendiente").sum())
    no_aplica = int((df_view.get("Estado", pd.Series(dtype=str)) == "No aplica").sum())

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Registros", total)
    k2.metric("Reportados", reportado)
    k3.metric("Pendientes", pendiente)
    k4.metric("No aplica", no_aplica)

    # ── Alertas de reporte vencido ─────────────────────────────────────────
    vencidos, por_vencer = _detectar_vencidos(df)
    if not vencidos.empty or not por_vencer.empty:
        st.markdown("### ⚠️ Alertas de frecuencia de reporte")
        ac1, ac2 = st.columns(2)
        with ac1:
            if not vencidos.empty:
                st.error(f"**{len(vencidos)} indicadores vencidos** (sin reporte en su ventana)")
                _v_cols = [c for c in ["Id", "Indicador", "Proceso", "Periodicidad", "diff_meses"] if c in vencidos.columns]
                st.dataframe(
                    vencidos[_v_cols].rename(columns={"diff_meses": "Meses sin reporte"}).head(20),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.success("Sin indicadores vencidos detectados.")
        with ac2:
            if not por_vencer.empty:
                st.warning(f"**{len(por_vencer)} próximos a vencer** (dentro del 80 % de ventana)")
                _pv_cols = [c for c in ["Id", "Indicador", "Proceso", "Periodicidad", "diff_meses"] if c in por_vencer.columns]
                st.dataframe(
                    por_vencer[_pv_cols].rename(columns={"diff_meses": "Meses sin reporte"}).head(20),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.success("Sin indicadores próximos a vencer.")

    # ── Gráfica de estado por proceso ──────────────────────────────────────
    if "Proceso" in df_view.columns and "Estado" in df_view.columns:
        st.markdown("### Estado de reportes por proceso")
        df_proc = (
            df_view.groupby(["Proceso", "Estado"], dropna=False)
            .size().reset_index(name="Cantidad")
        )
        _col_estado = {
            "Reportado": "#28a745",
            "Pendiente": "#ffc107",
            "No aplica": "#6c757d",
        }
        fig_proc = px.bar(
            df_proc,
            x="Proceso",
            y="Cantidad",
            color="Estado",
            barmode="stack",
            title="Indicadores por proceso y estado de reporte",
            color_discrete_map=_col_estado,
        )
        fig_proc.update_layout(
            xaxis_tickangle=-35,
            margin=dict(l=10, r=10, t=50, b=120),
            legend_title="Estado",
        )
        try:
            from components.renderers import render_echarts

            def _option_proc_estado(df_proc, color_map):
                procs = df_proc['Proceso'].astype(str).unique().tolist()
                estados = df_proc['Estado'].astype(str).unique().tolist()
                # ordenar procs
                procs = sorted(procs)
                series = []
                for est in estados:
                    vals = []
                    for p in procs:
                        s = df_proc[(df_proc['Proceso'] == p) & (df_proc['Estado'] == est)]
                        vals.append(int(s['Cantidad'].sum()) if not s.empty else 0)
                    series.append({
                        'name': est,
                        'type': 'bar',
                        'stack': 'total',
                        'data': vals,
                        'itemStyle': {'color': color_map.get(est, '#888')},
                    })
                option = {
                    'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
                    'legend': {'bottom': 0},
                    'xAxis': {'type': 'category', 'data': procs, 'axisLabel': {'rotate': -35}},
                    'yAxis': {'type': 'value'},
                    'series': series,
                    'grid': {'left': '10%', 'right': '5%', 'bottom': '20%'}
                }
                return {'option': option, 'height': max(320, len(procs) * 28 + 80)}

            opt = _option_proc_estado(df_proc, _col_estado)
            if opt and opt.get('option'):
                render_echarts(opt['option'], height=opt.get('height', 420))
            else:
                st.plotly_chart(fig_proc, use_container_width=True, key="sr_proc_estado")
        except Exception:
            st.plotly_chart(fig_proc, use_container_width=True, key="sr_proc_estado")

    st.markdown("### Detalle")
    st.dataframe(df_view, use_container_width=True, height=500)

    st.download_button(
        label="Descargar vista filtrada (Excel)",
        data=exportar_excel(df_view, nombre_hoja="Seguimiento"),
        file_name="seguimiento_reportes_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
