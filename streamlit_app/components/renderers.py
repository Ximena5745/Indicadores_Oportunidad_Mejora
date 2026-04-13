import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from core import config as core_config
import datetime
import io
import pandas as pd

TEMPLATE_DIR = Path(__file__).parent / "ui" / "templates"


def render_exec_summary(data: dict, height: int = 360):
    """Carga la plantilla exec_summary.html, inyecta el JSON y la renderiza con st.components.v1.html

    data: dict con keys: kpis (list), donut (list de {value,name}), insight (str)
    """
    tpl_path = TEMPLATE_DIR / "exec_summary.html"
    html = tpl_path.read_text(encoding="utf-8")
    # Inyectar JSON en el script placeholder
    data_json = json.dumps(data, ensure_ascii=False)
    # Replace the DATA_HOLDER content
    html = html.replace('<script type="application/json" id="DATA_HOLDER">null</script>', f'<script type="application/json" id="DATA_HOLDER">{data_json}</script>')
    components.html(html, height=height, scrolling=True)


def render_alert_strip(message: str, level: str = "info"):
    """Muestra una tira de alerta estilizada.

    level: 'info'|'warning'|'danger'|'success'
    """
    colors = {
        'info':    ('#E6F2FF', '#1A3A5C'),
        'warning': ('#FFF8E1', '#F59E0B'),
        'danger':  ('#FFECEC', '#DC2626'),
        'success': ('#E8F5E9', '#16A34A'),
    }
    bg, border = colors.get(level, colors['info'])
    html = f"""
    <div style='background:{bg}; border-left:4px solid {border}; padding:10px; border-radius:6px; margin-bottom:12px;'>
      {message}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_narrative_panel(title: str, text: str, collapsed: bool = False):
    """Muestra un panel narrativo compacto con título y contenido.

    - `collapsed`: si True lo muestra en un `st.expander`.
    """
    if collapsed:
        with st.expander(title, expanded=False):
            st.write(text)
    else:
        html = f"""
        <div style='background:#ffffff;border-radius:8px;padding:12px;border:1px solid #e6eef8;margin-bottom:12px;'>
          <h4 style='margin:0 0 6px 0;color:#0f385a'>{title}</h4>
          <div style='color:#243447;font-size:0.95rem'>{text}</div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)


def kpi_card(
    title: str,
    value,
    delta: str | None = None,
    sparkline: list[float] | None = None,
    key: str | None = None,
    category: str | None = None,
    target: float | None = None,
    show_progress: bool = True,
):
    """Renderiza una tarjeta KPI mejorada.

    - `category`: opcional, una de las categorías (Peligro/Alerta/Cumplimiento/Sobrecumplimiento) para colorear la tarjeta.
    - `target`: valor objetivo para calcular progreso (porcentaje relativo si `value` y `target` son numéricos).
    - `show_progress`: si True muestra una barra de progreso cuando `target` está presente.
    """
    cols = st.columns([3, 1])
    # color según categoría
    color = None
    if category:
        color = core_config.COLOR_CATEGORIA.get(category, None)

    with cols[0]:
        title_md = f"**{title}**"
        if color:
            title_md = f"<span style='color:{color}; font-weight:600'>{title}</span>"
            st.markdown(title_md, unsafe_allow_html=True)
        else:
            st.markdown(title_md)

        if delta is not None:
            st.metric(label="", value=value, delta=delta)
        else:
            st.metric(label="", value=value)

        # Progress bar si target y value son numéricos
        if show_progress and target is not None:
            try:
                val = float(value)
                tgt = float(target)
                pct = 0.0 if tgt == 0 else max(0.0, min(1.0, val / tgt))
                st.progress(pct)
                st.caption(f"Progreso: {pct*100:.1f}% (valor {val} de objetivo {tgt})")
            except Exception:
                pass

    with cols[1]:
        if sparkline:
            fig = go.Figure(go.Scatter(y=sparkline, mode='lines', line=dict(width=2, color=core_config.COLORES.get('primario', '#0B5FFF'))))
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=60, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


def actions_table(df_actions):
    """Muestra una tabla de acciones priorizada. Si Streamlit soporta data_editor, lo usa para edición ligera."""
    if df_actions is None or df_actions.empty:
        st.info("No hay acciones para mostrar.")
        return
    # Mostrar tabla sin cálculo automático de prioridad.
    # Si existe una columna `prioridad` en el dataset la respetamos, pero no la calculamos.
    df_show = df_actions.copy().reset_index(drop=True)
    edited = None
    try:
        edited = st.experimental_data_editor(df_show, num_rows='dynamic', use_container_width=True)
    except Exception:
        st.dataframe(df_show, use_container_width=True)

    # Bulk actions: seleccionar filas por índice
    ids = df_show.index.astype(str).tolist()
    selected = st.multiselect("Seleccionar acciones (para bulk)", ids, key='bulk_actions_select')
    if selected:
        sel_idx = [int(i) for i in selected]
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Marcar seleccionadas como Cerradas"):
                df_show.loc[sel_idx, 'ESTADO'] = 'Cerrada'
                st.success(f"{len(sel_idx)} acciones marcadas como Cerradas (local).")
        with col2:
            nuevo_responsable = st.text_input("Reasignar responsable a:", key='bulk_reassign_input')
            if st.button("Reasignar seleccionadas") and nuevo_responsable.strip():
                # intentar columnas posibles
                for col in ('RESPONSABLE','responsable','Responsable'):
                    if col in df_show.columns:
                        df_show.loc[sel_idx, col] = nuevo_responsable
                st.success(f"{len(sel_idx)} acciones reasignadas a {nuevo_responsable} (local).")

    # Descarga CSV del dataset (editable si se editó)
    try:
        to_export = edited if edited is not None else df_show
        # Descargar Excel preferente para usuarios
        try:
            import pandas as _pd
            bio = io.BytesIO()
            _pd.DataFrame(to_export).to_excel(bio, index=False, engine='openpyxl')
            bio.seek(0)
            st.download_button(
                "Descargar Excel",
                bio.getvalue(),
                file_name="acciones_priorizadas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            # Fallback CSV
            csv = to_export.to_csv(index=False).encode('utf-8')
            st.download_button("Descargar CSV", csv, file_name="acciones_priorizadas.csv", mime="text/csv")
    except Exception:
        pass

    # Persistencia local: guardar CSV en data/raw/ con timestamp
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("Guardar cambios (Excel)"):
            try:
                saved_path = _save_actions_to_excel(to_export)
                st.success(f"Guardado local: {saved_path}")
            except Exception as e:
                st.error(f"Error guardando Excel: {e}")
    with col_b:
        if st.button("Guardar en DB (experimental)"):
            # Intentar usar un hook en core.db_manager si está disponible
            try:
                import core.db_manager as dbm
                if hasattr(dbm, 'guardar_acciones_bulk'):
                    ok = dbm.guardar_acciones_bulk(to_export)
                    if ok:
                        st.success("Guardado en DB (hook) exitoso.")
                    else:
                        st.error("El hook de DB devolvió fallo.")
                else:
                    st.warning("No se encontró un hook 'guardar_acciones_bulk' en core.db_manager. Implementa la función para habilitar guardado en DB.")
            except Exception as e:
                st.error(f"Error al intentar guardar en DB: {e}")


def pd_notna(v):
    return v is not None and (not (isinstance(v, float) and (v != v)))


def set_global_palette(palette: dict | None = None):
    """Inyecta variables CSS globales para la paleta del dashboard.

    palette: dict con keys: primary, success, alert, danger, bg, panel, text
    """
    if palette is None:
        palette = {
            'primary': '#0B5FFF', 'success': '#16A34A', 'alert': '#F59E0B',
            'danger': '#DC2626', 'bg': '#F5F7FA', 'panel': '#FFFFFF', 'text': '#0F1724'
        }
        css = f"""
        <style>
        :root {{
            --color-primary: {palette['primary']};
            --success: {palette['success']};
            --alert: {palette['alert']};
            --danger: {palette['danger']};
            --bg: {palette['bg']};
            --panel: {palette['panel']};
            --text: {palette['text']};
        }}
        /* Layout compacting: reduce default container padding and card spacing */
        [data-testid="stAppViewContainer"] .main .block-container {{
            padding: 8px 12px !important;
            max-width: 1200px;
            margin-left: auto;
            margin-right: auto;
        }}
        /* Sidebar padding */
        [data-testid="stSidebar"] {{ padding: 8px !important; }}
        /* Reduce expander and caption spacing */
        .streamlit-expanderHeader, .st-expander {{ padding: 6px 8px !important; margin-bottom:6px !important; }}
        .stCaption {{ margin-top:4px !important; margin-bottom:6px !important; }}
        /* Global background */
        :root, body {{ background: {palette['bg']} !important; color: {palette['text']} !important; }}
        </style>
        """
        components.html(css, height=0)


def render_kawak_caption(total_indicadores: int, total_reportados: int | None = None):
    """Muestra un caption consistente con el total de indicadores (fuente Kawak).

    - `total_indicadores`: número total informado por Kawak (puede ser 0 si no disponible).
    - `total_reportados`: número reportado en el período (opcional).
    """
    if total_reportados is None:
        st.caption(f"Indicadores totales (Kawak): {total_indicadores}")
    else:
        st.caption(f"Indicadores totales (Kawak): {total_indicadores} · Reportados en período: {total_reportados}")


def generate_sparkline_counts(df: pd.DataFrame, date_col: str = "Fecha", group_col: str | None = None, filter_val: str | None = None, periods: int = 6) -> list:
    """Genera una serie simple de conteos por mes para los últimos `periods` meses.

    - `df`: DataFrame con columna de fecha.
    - `group_col` y `filter_val`: si se proveen, se cuentan solo filas con group_col == filter_val.
    """
    try:
        if df is None or df.empty:
            return []
        d = df.copy()
        if date_col not in d.columns:
            return []
        d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
        if group_col and filter_val is not None and group_col in d.columns:
            d = d[d[group_col].astype(str) == str(filter_val)]
        # Última fecha presente
        last = d[date_col].max()
        if pd.isna(last):
            return []
        last = pd.Timestamp(last)
        # Generar meses hacia atrás
        series = []
        for i in range(periods - 1, -1, -1):
            m = (last.month - i - 1) % 12 + 1
            y = last.year + ((last.month - i - 1) // 12)
            mask = (d[date_col].dt.month == m) & (d[date_col].dt.year == y)
            series.append(int(mask.sum()))
        return series
    except Exception:
        return []


def generate_sparkline_agg(df: pd.DataFrame, date_col: str = "Fecha", value_col: str = "Cumplimiento", agg: str = "mean", periods: int = 6) -> list:
    """Genera una serie agregada (mean/sum/median) por mes para `value_col` sobre los últimos `periods` meses."""
    try:
        if df is None or df.empty:
            return []
        d = df.copy()
        if date_col not in d.columns or value_col not in d.columns:
            return []
        d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
        last = d[date_col].max()
        if pd.isna(last):
            return []
        last = pd.Timestamp(last)
        vals = []
        for i in range(periods - 1, -1, -1):
            m = (last.month - i - 1) % 12 + 1
            y = last.year + ((last.month - i - 1) // 12)
            mask = (d[date_col].dt.month == m) & (d[date_col].dt.year == y)
            seg = d.loc[mask, value_col].dropna().astype(float)
            if seg.empty:
                vals.append(None)
            else:
                if agg == "mean":
                    vals.append(float(seg.mean()))
                elif agg == "sum":
                    vals.append(float(seg.sum()))
                elif agg == "median":
                    vals.append(float(seg.median()))
                else:
                    vals.append(float(seg.mean()))
        return vals
    except Exception:
        return []


def render_table_paginated(df, page_size: int = 20, key: str | None = None):
    """Renderiza una tabla con paginación simple (server-side slicing).

    - df: pandas DataFrame
    - page_size: filas por página
    - key: session state key prefix
    """
    if df is None or df.empty:
        st.info("No hay datos para mostrar en la tabla paginada.")
        return
    k = key or "_pag_table"
    total = len(df)
    pages = max(1, (total + page_size - 1) // page_size)
    if f"{k}_page" not in st.session_state:
        st.session_state[f"{k}_page"] = 1

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("◀ Anterior", key=f"{k}_prev"):
            st.session_state[f"{k}_page"] = max(1, st.session_state[f"{k}_page"] - 1)
    with col2:
        if st.button("Siguiente ▶", key=f"{k}_next"):
            st.session_state[f"{k}_page"] = min(pages, st.session_state[f"{k}_page"] + 1)
    with col3:
        st.write(f"Página {st.session_state[f'{k}_page']} de {pages} — {total} filas")

    # slice
    p = st.session_state[f"{k}_page"]
    start = (p - 1) * page_size
    end = min(start + page_size, total)
    st.dataframe(df.iloc[start:end].reset_index(drop=True), use_container_width=True)


def render_echarts(option: dict, height: int = 420):
        """Renderiza una opción de ECharts en Streamlit mediante HTML embebido.

        option: dict que corresponde al objeto de configuración de ECharts.
        """
        tpl = f"""
        <div id='echart_{id(option)}' style='width:100%;height:{height}px;'></div>
        <script src='https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js'></script>
        <script>
            (function(){{
                try{{
                    const opt = {json.dumps(option, ensure_ascii=False)};
                    const el = document.getElementById('echart_{id(option)}');
                    const chart = echarts.init(el);
                    chart.setOption(opt);
                }}catch(e){{console.error(e)}}
            }})();
        </script>
        """
        components.html(tpl, height=height+20, scrolling=True)


def _save_actions_to_csv(df, basename: str = "acciones_priorizadas") -> str:
    """Guarda el DataFrame `df` como CSV en `data/raw/` con timestamp y retorna la ruta relativa."""
    from pathlib import Path
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(__file__).parent.parent.parent / "data" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{basename}_{ts}.csv"
    out_path = out_dir / filename
    # Asegurar que df sea exportable
    df.to_csv(out_path, index=False, encoding='utf-8')
    # Retornar ruta relativa al repo (Windows-friendly)
    return str(out_path)


def _save_actions_to_excel(df, basename: str = "acciones_priorizadas") -> str:
    """Guarda el DataFrame `df` como Excel (.xlsx) en `data/raw/` con timestamp y retorna la ruta relativa."""
    from pathlib import Path
    try:
        import pandas as _pd
    except Exception:
        _pd = None
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(__file__).parent.parent.parent / "data" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{basename}_{ts}.xlsx"
    out_path = out_dir / filename
    # Convertir a DataFrame si es necesario
    if _pd is not None:
        _pd.DataFrame(df).to_excel(out_path, index=False, engine='openpyxl')
    else:
        # Fallback: guardar CSV con extensión xlsx (no ideal)
        df.to_csv(out_path.with_suffix('.csv'), index=False, encoding='utf-8')
        out_path = out_path.with_suffix('.csv')
    return str(out_path)
