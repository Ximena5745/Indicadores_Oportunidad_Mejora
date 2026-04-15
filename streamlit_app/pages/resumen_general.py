def calcular_cascada(df):
    # Nivel 4: Indicador (hoja)
    nivel4 = df.copy()
    nivel4["Nivel"] = 4
    nivel4["Total_Indicadores"] = 1
    nivel4 = nivel4[["Nivel", "Linea", "Objetivo", "Meta_PDI", "Indicador", "cumplimiento_pct", "Total_Indicadores"]]
    nivel4 = nivel4.rename(columns={"cumplimiento_pct": "Cumplimiento"})

    # Nivel 3: Meta_PDI
    nivel3 = (
        df.groupby(["Linea", "Objetivo", "Meta_PDI"], dropna=False)
        .agg(Cumplimiento=("cumplimiento_pct", "mean"), Total_Indicadores=("Indicador", "count"))
        .reset_index()
    )
    nivel3["Nivel"] = 3
    nivel3["Indicador"] = None
    nivel3 = nivel3[["Nivel", "Linea", "Objetivo", "Meta_PDI", "Indicador", "Cumplimiento", "Total_Indicadores"]]

    # Nivel 2: Objetivo
    nivel2 = (
        df.groupby(["Linea", "Objetivo"], dropna=False)
        .agg(Cumplimiento=("cumplimiento_pct", "mean"), Total_Indicadores=("Indicador", "count"))
        .reset_index()
    )
    nivel2["Nivel"] = 2
    nivel2["Meta_PDI"] = None
    nivel2["Indicador"] = None
    nivel2 = nivel2[["Nivel", "Linea", "Objetivo", "Meta_PDI", "Indicador", "Cumplimiento", "Total_Indicadores"]]

    # Nivel 1: Linea
    nivel1 = (
        df.groupby(["Linea"], dropna=False)
        .agg(Cumplimiento=("cumplimiento_pct", "mean"), Total_Indicadores=("Indicador", "count"))
        .reset_index()
    )
    nivel1["Nivel"] = 1
    nivel1["Objetivo"] = None
    nivel1["Meta_PDI"] = None
    nivel1["Indicador"] = None
    nivel1 = nivel1[["Nivel", "Linea", "Objetivo", "Meta_PDI", "Indicador", "Cumplimiento", "Total_Indicadores"]]

    # Unir todos los niveles
    cascada = pd.concat([nivel1, nivel2, nivel3, nivel4], ignore_index=True)
    return cascada
"""
pages/resumen_general_real.py — Resumen General con datos reales de Consolidado Cierres.

Fuente real: data/output/Resultados Consolidados.xlsx · hoja Consolidado Cierres
"""
from pathlib import Path  # noqa: F401 — retenido por compatibilidad con código heredado
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

try:
    from services.strategic_indicators import preparar_pdi_con_cierre, load_pdi_catalog
    import services.strategic_indicators as si
    from core.config import DATA_OUTPUT
    from core.proceso_types import TIPOS_PROCESO, get_tipo_color
    from core.calculos import simple_categoria_desde_porcentaje
    from streamlit_app.services.data_service import DataService
    from services.cmi_filters import filter_df_for_cmi_estrategico, filter_df_for_cmi_procesos
except (ImportError, ModuleNotFoundError):
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from services.strategic_indicators import preparar_pdi_con_cierre, load_pdi_catalog
    import services.strategic_indicators as si
    from core.config import DATA_OUTPUT
    from core.proceso_types import TIPOS_PROCESO, get_tipo_color
    from core.calculos import simple_categoria_desde_porcentaje
    from streamlit_app.services.data_service import DataService
    from services.cmi_filters import filter_df_for_cmi_estrategico, filter_df_for_cmi_procesos

# Limpiar caché corrupto si es necesario
if "page_cache_cleared" not in st.session_state:
    try:
        si.load_worksheet_flags.clear()
        si.load_cierres.clear()
    except Exception:
        pass
    st.session_state.page_cache_cleared = True

PATH_CONSOLIDADO = DATA_OUTPUT / "Resultados Consolidados.xlsx"

LINEA_COLORS = {
    "Expansión": "#FBAF17",
    "Transformación organizacional": "#42F2F2",
    "Calidad": "#EC0677",
    "Experiencia": "#1FB2DE",
    "Sostenibilidad": "#A6CE38",
    "Educación para toda la vida": "#0F385A",
}

MES_MAP = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    # Normaliza la columna de cumplimiento
    if "Cumplimiento" in df.columns and "cumplimiento_pct" not in df.columns:
        df = df.rename(columns={"Cumplimiento": "cumplimiento_pct"})
    return df


def _parse_month(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except Exception:
            return None
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return MES_MAP.get(text.lower())


def _load_consolidado_cierres() -> pd.DataFrame:
    if not PATH_CONSOLIDADO.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(PATH_CONSOLIDADO, sheet_name="Consolidado Cierres", engine="openpyxl")
    except Exception:
        return pd.DataFrame()
    df = _normalize_columns(df)
    if "Ao" in df.columns:
        df["Ao"] = pd.to_numeric(df["Ao"], errors="coerce")
    elif "Anio" in df.columns:
        df["Ao"] = pd.to_numeric(df["Anio"], errors="coerce")
    else:
        df["Ao"] = pd.NA

    if "Mes" in df.columns:
        df["Mes_num"] = df["Mes"].apply(_parse_month)
    else:
        df["Mes_num"] = None

    # Si existe "Cumplimiento" y no "cumplimiento_pct", normaliza
    if "Cumplimiento" in df.columns and "cumplimiento_pct" not in df.columns:
        df = df.rename(columns={"Cumplimiento": "cumplimiento_pct"})
    # Asegurar que `cumplimiento_pct` esté en escala porcentual (0-100)
    if "cumplimiento_pct" in df.columns:
        df["cumplimiento_pct"] = pd.to_numeric(df.get("cumplimiento_pct"), errors="coerce")
        # Si los valores parecen estar en escala decimal [0..2], convertir a porcentaje
        try:
            mx = float(df["cumplimiento_pct"].abs().max(skipna=True)) if not df["cumplimiento_pct"].isna().all() else 0
        except Exception:
            mx = 0
        if mx <= 2:
            df["cumplimiento_pct"] = df["cumplimiento_pct"].multiply(100)

    df = _ensure_nivel_cumplimiento(df)
    return df


def _ensure_nivel_cumplimiento(df: pd.DataFrame) -> pd.DataFrame:
    # Prefer recalcular 'Nivel de cumplimiento' desde 'cumplimiento_pct' cuando esté disponible
    # 1) Normalize 'Cumplimiento' -> 'cumplimiento_pct' if necesario
    if "Cumplimiento" in df.columns and "cumplimiento_pct" not in df.columns:
        df = df.rename(columns={"Cumplimiento": "cumplimiento_pct"})

    if "cumplimiento_pct" in df.columns:
        def _map_level(value):
            import math
            if pd.isna(value):
                return "Pendiente de reporte"
            try:
                pct = float(value)
            except Exception:
                return "Pendiente de reporte"
            if math.isnan(pct):
                return "Pendiente de reporte"
            if pct >= 105:
                return "Sobrecumplimiento"
            if pct >= 100:
                return "Cumplimiento"
            if pct >= 80:
                return "Alerta"
            return "Peligro"

        df = df.copy()
        df["Nivel de cumplimiento"] = df["cumplimiento_pct"].apply(_map_level)
        return df

    # 2) Si no hay 'cumplimiento_pct' pero existe 'Categoria', usarla
    if "Categoria" in df.columns:
        df = df.copy()
        df["Nivel de cumplimiento"] = df["Categoria"]
        return df

    # 3) Si nada de lo anterior, marcar como pendiente
    df = df.copy()
    df["Nivel de cumplimiento"] = "Pendiente de reporte"
    return df


def _available_years(df: pd.DataFrame) -> list[int]:
    if df.empty or "Año" not in df.columns:
        return []
    years = pd.to_numeric(df["Año"], errors="coerce").dropna().astype(int).unique().tolist()
    allowed = [y for y in sorted(years) if y in {2022, 2023, 2024, 2025}]
    return allowed or sorted(years)


def _filter_consolidado_by_year_month(df: pd.DataFrame, year: int | None, month: int | None) -> pd.DataFrame:
    df = df.copy()
    
    # Simple debug to file
    import os
    debug_file = "debug_filter.log"
    with open(debug_file, "w") as f:
        f.write(f"Input rows: {len(df)}\n")
    
    # detect year column
    year_col = None
    for c in df.columns:
        if isinstance(c, str) and 'A' in c and 'o' in c and ('ñ' in c.lower() or c == 'Anio'):
            year_col = c
            break
    if year_col is None and 'Anio' in df.columns:
        year_col = 'Anio'
    if year_col is None and 'Año' in df.columns:
        year_col = 'Año'
        
    with open(debug_file, "a") as f:
        f.write(f"year_col: {year_col}\n")
        
    if year_col is not None and year_col in df.columns:
        df['_year'] = pd.to_numeric(df[year_col], errors='coerce')
    elif 'Periodo' in df.columns:
        df['_year'] = df['Periodo'].astype(str).str.split('-').str[0].apply(lambda x: pd.to_numeric(x, errors='coerce'))
    else:
        df['_year'] = pd.NA

    # detect month column
    if 'Mes_num' in df.columns:
        df['_month'] = pd.to_numeric(df['Mes_num'], errors='coerce')
    elif 'Mes' in df.columns:
        df['_month'] = pd.to_numeric(df['Mes'], errors='coerce')
    else:
        df['_month'] = pd.NA
    
    with open(debug_file, "a") as f:
        f.write(f"year filter: {year}, month filter: {month}\n")
        f.write(f"_year values: {sorted(df['_year'].dropna().unique())}\n")
        f.write(f"_month values: {sorted(df['_month'].dropna().unique())}\n")

    if year is not None:
        df = df[df['_year'] == int(year)]
    if month:
        df = df[df['_month'] == int(month)]
    
    with open(debug_file, "a") as f:
        f.write(f"Output rows: {len(df)}\n")

    # drop helper cols
    df = df.drop(columns=[c for c in ['_year', '_month'] if c in df.columns])
    return df


def _latest_month_for_year(df: pd.DataFrame, year: int) -> int | None:
    subset = df[df["Año"] == year].copy()
    if subset.empty or "Mes_num" not in subset.columns:
        return None
    months = pd.to_numeric(subset["Mes_num"], errors="coerce").dropna().astype(int)
    return int(months.max()) if not months.empty else None


def _available_months_for_year(df: pd.DataFrame, year: int) -> list[int]:
    subset = df[df["Año"] == year].copy()
    if subset.empty or "Mes_num" not in subset.columns:
        return []
    months = pd.to_numeric(subset["Mes_num"], errors="coerce").dropna().astype(int).unique()
    return sorted(months.tolist())


def _build_sunburst(pdi_df: pd.DataFrame) -> go.Figure:
    df = pdi_df.copy()
    df["Linea"] = df["Linea"].fillna("Sin línea")
    df["Objetivo"] = df["Objetivo"].fillna("Sin objetivo")
    df = df[df["cumplimiento_pct"].notna()]

    # Si no hay datos válidos, crear un nodo dummy con 0%
    if df.empty:
        labels = ["Sin datos"]
        parents = [""]
        values = [1]
        customdata = [[0]]
        colors = ["#6B728E"]
        text = ["Sin datos\n0.0%"]
    else:
        # Nivel 1: Linea (promedio)
        lines = df.groupby("Linea", dropna=False).agg(cumplimiento_pct=("cumplimiento_pct", "mean")).reset_index()
        # Nivel 2: Objetivo (promedio)
        grouped = df.groupby(["Linea", "Objetivo"], dropna=False).agg(cumplimiento_pct=("cumplimiento_pct", "mean")).reset_index()

        labels = []
        parents = []
        values = []
        customdata = []
        colors = []

        # Use counts for sizing but show cumplimiento_pct as text inside sectors
        line_counts = df.groupby('Linea').size().to_dict()
        obj_counts = df.groupby(['Linea', 'Objetivo']).size().to_dict()

        # helper to match color keys ignoring accents/case
        def _norm_key(s: str) -> str:
            import unicodedata, re
            if s is None:
                return ""
            t = str(s).strip().lower()
            t = unicodedata.normalize("NFD", t)
            t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
            # replace any non-alphanumeric with a single space and collapse spaces
            t = re.sub(r"[^0-9a-z]+", " ", t)
            t = re.sub(r"\s+", " ", t).strip()
            return t

        normalized_color_map = { _norm_key(k): v for k, v in LINEA_COLORS.items() }

        for _, line in lines.iterrows():
            linea_name = line["Linea"]
            labels.append(linea_name)
            parents.append("")
            values.append(int(line_counts.get(linea_name, 0)) or 1)
            customdata.append([line["cumplimiento_pct"] if pd.notna(line["cumplimiento_pct"]) else 0])
            colors.append(normalized_color_map.get(_norm_key(linea_name), "#6B728E"))

        for _, row in grouped.iterrows():
            obj_name = row["Objetivo"]
            parent_name = row["Linea"]
            labels.append(obj_name)
            parents.append(parent_name)
            values.append(int(obj_counts.get((parent_name, obj_name), 0)) or 1)
            customdata.append([row["cumplimiento_pct"] if pd.notna(row["cumplimiento_pct"]) else 0])
            colors.append(normalized_color_map.get(_norm_key(parent_name), "#6B728E"))

        # Wrap long labels to multiple lines so they fit inside sectors
        def wrap_label(s: str, width: int = 18) -> str:
            import re
            text = str(s or "").strip()
            if not text:
                return ""
            # First try logical separators to produce natural splits
            separators = [",", " / ", " - ", " y ", ";"]
            segments = [text]
            for sep in separators:
                if any(sep in seg for seg in segments):
                    new_segs = []
                    for seg in segments:
                        if sep in seg:
                            parts = [p.strip() for p in seg.split(sep) if p.strip()]
                            new_segs.extend(parts)
                        else:
                            new_segs.append(seg)
                    segments = new_segs
            # Now for each segment, apply word-wrap to the given width
            wrapped_lines = []
            for seg in segments:
                words = seg.split()
                cur = []
                for w in words:
                    if sum(len(x) for x in cur) + len(cur) + len(w) <= width:
                        cur.append(w)
                    else:
                        if cur:
                            wrapped_lines.append(" ".join(cur))
                        cur = [w]
                if cur:
                    wrapped_lines.append(" ".join(cur))
            # clean and return joined lines
            cleaned = [re.sub(r"\s+", " ", ln).strip() for ln in wrapped_lines]
            return "\n".join(cleaned)

        # Build wrapped text lines; include percentage
        text = []
        edu_key = _norm_key('Educación para toda la vida')
        for lab, cd, parent in zip(labels, customdata, parents):
            pct = (cd[0] if cd and cd[0] is not None else 0)
            is_edu = _norm_key(lab) == edu_key
            # Educación para toda la vida: wrap más pequeño para 3 líneas
            if parent == "":
                if is_edu:
                    wrapped = wrap_label(lab, width=8)
                else:
                    wrapped = wrap_label(lab, width=12)
            else:
                wrapped = wrap_label(lab, width=26)
            html_label = str(wrapped).replace('\n', '<br>')
            # Educación: mayor fonte
            if is_edu:
                html_label = f"<b><span style='font-size:22px'>{html_label}</span></b>"
            else:
                html_label = f"<b>{html_label}</b>"
            # percentage en azul
            pct_html = f"<br><span style='color:#0B5FFF;font-size:18px'>{pct:.0f}%</span>"
            text.append(f"{html_label}{pct_html}")

    # Split inner (Linea) and outer (Objetivo) for independent styling
    inner_idxs = [i for i, p in enumerate(parents) if p == ""]
    outer_idxs = [i for i, p in enumerate(parents) if p != ""]

    inner_labels = [labels[i] for i in inner_idxs]
    inner_values = [values[i] for i in inner_idxs]
    inner_colors = [colors[i] for i in inner_idxs]
    inner_custom = [customdata[i] for i in inner_idxs]
    inner_text = [text[i] for i in inner_idxs]

    outer_labels = [labels[i] for i in outer_idxs]
    outer_parents = [parents[i] for i in outer_idxs]
    outer_values = [values[i] for i in outer_idxs]
    outer_colors = [colors[i] for i in outer_idxs]
    outer_custom = [customdata[i] for i in outer_idxs]
    outer_text = [text[i] for i in outer_idxs]

    # Build a single Sunburst trace (more robust across runtimes)
    fig = go.Figure()
    all_labels = labels
    all_parents = parents
    all_values = values
    all_colors = colors
    all_custom = customdata
    all_text = text

    # Adjust sizes: amplify 'Educación para toda la vida' and reduce 'Sostenibilidad'
    try:
        edu_key = _norm_key('Educación para toda la vida')
        sus_key = _norm_key('Sostenibilidad')
        for i, lab in enumerate(all_labels):
            try:
                nk = _norm_key(lab)
                parent_label = all_parents[i] if i < len(all_parents) else ""
                parent_nk = _norm_key(parent_label) if parent_label else ""
                # Amplify Educación more and reduce Sostenibilidad further
                if nk == edu_key and (not parent_label):
                    all_values[i] = max(1, int(all_values[i] * 5))
                # If a node is a child of Educación, enlarge it as well
                elif parent_nk == edu_key:
                    all_values[i] = max(1, int(all_values[i] * 3))
                # reduce Sostenibilidad further
                if nk == sus_key:
                    all_values[i] = max(1, int(all_values[i] * 0.25))
            except Exception:
                continue
    except Exception:
        pass

    # Ensure parent nodes have values >= sum(children) to satisfy branchvalues='total'
    try:
        # build index map
        label_to_index = {lbl: idx for idx, lbl in enumerate(all_labels)}
        # compute children sums
        children_sum = {lbl: 0 for lbl in all_labels}
        for idx, parent in enumerate(all_parents):
            if parent and parent in label_to_index:
                children_sum[parent] += int(all_values[idx]) if idx < len(all_values) else 0
        # adjust parent values if needed
        for parent, s in children_sum.items():
            if s <= 0:
                continue
            pidx = label_to_index.get(parent)
            if pidx is None or pidx >= len(all_values):
                continue
            try:
                if int(all_values[pidx]) < s:
                    all_values[pidx] = int(s)
            except Exception:
                all_values[pidx] = int(s)
    except Exception:
        pass

    # Expand objective nodes more to make outer text more visible (multiply nodes with a parent)
    try:
        sus_key = _norm_key('Sostenibilidad')
        for i, p in enumerate(all_parents):
            if p and i < len(all_values):
                # avoid expanding children of Sostenibilidad to keep it smaller
                try:
                    parent_nk = _norm_key(p)
                    if parent_nk == sus_key:
                        continue
                except Exception:
                    pass
                # Increase outer ring (objetivos) so labels fit better
                all_values[i] = max(1, int(all_values[i] * 2.5))
    except Exception:
        pass

    # Prepare per-label text using newlines

    # Final enforcement: ensure parent nodes have values >= sum(children)
    try:
        label_to_index = {lbl: idx for idx, lbl in enumerate(all_labels)}
        children_sum = {lbl: 0 for lbl in all_labels}
        for idx, parent in enumerate(all_parents):
            if parent and parent in label_to_index and idx < len(all_values):
                children_sum[parent] += int(all_values[idx])
        for parent, s in children_sum.items():
            if s <= 0:
                continue
            pidx = label_to_index.get(parent)
            if pidx is None or pidx >= len(all_values):
                continue
            try:
                if int(all_values[pidx]) < s:
                    all_values[pidx] = int(s)
            except Exception:
                all_values[pidx] = int(s)
    except Exception:
        pass

    # Customize Sostenibilidad text to be slightly larger and bold
    # Keep Sostenibilidad styling consistent with other labels; centering applied above

    # Equalize objective sizes under 'Transformación organizacional' so children share same value
    try:
        transform_key = _norm_key('Transformación organizacional')
        # find parent label matching transform
        parent_label = None
        for lbl in all_labels:
            if _norm_key(lbl) == transform_key:
                parent_label = lbl
                break
        if parent_label:
            child_idxs = [i for i, p in enumerate(all_parents) if p == parent_label]
            if child_idxs:
                parent_idx = all_labels.index(parent_label)
                parent_val = int(all_values[parent_idx]) if parent_idx < len(all_values) else None
                if parent_val and len(child_idxs) > 0:
                    equal_val = max(1, int(parent_val / len(child_idxs)))
                    for i in child_idxs:
                        all_values[i] = equal_val
    except Exception:
        pass

    # Do not uppercase labels; instead make label text bold using HTML when building `all_text`.

    fig.add_trace(go.Sunburst(
        labels=all_labels,
        parents=all_parents,
        values=all_values,
        branchvalues="total",
        marker=dict(colors=all_colors, line=dict(color="#ffffff", width=1)),
        customdata=all_custom,
        text=all_text,
        textinfo='text',
        texttemplate='%{text}',
        insidetextorientation="horizontal",
        hovertemplate="<b>%{label}</b><br>Promedio cumplimiento: %{customdata[0]:.0f}%<extra></extra>",
        domain=dict(x=[0,1], y=[0,1]),
        maxdepth=2,
        sort=False
    ))

    # Improve readability: set explicit templates for the sunburst trace
    try:
        if len(fig.data) >= 1 and getattr(fig.data[0], 'type', None) == 'sunburst':
            fig.data[0].update(
                uniformtext=dict(minsize=8, mode='hide'),
                textfont=dict(family='Inter, sans-serif', size=14, color='#062A4F'),
                insidetextfont=dict(family='Inter, sans-serif', size=20, color='#0B5FFF'),
                marker=dict(line=dict(color='#FFFFFF', width=1)),
                branchvalues='total',
                separation=0,
                texttemplate='%{text}',
                hovertemplate="<b>%{label}</b><br>Promedio cumplimiento: %{customdata[0]:.1f}%<extra></extra>",
                insidetextorientation='radial',
                constraintext='hide'
            )
    except Exception:
        pass

    # As a final safety, ensure any remaining sunburst traces get a minimal uniformtext update
    for trace in fig.data:
        try:
            if getattr(trace, 'type', None) == 'sunburst' and not getattr(trace, 'uniformtext', None):
                trace.update(uniformtext=dict(minsize=9, mode='hide'))
        except Exception:
            pass
    # Ensure Sunburst is present: if not, try to create via plotly.express.sunburst
    has_sunburst = any(getattr(t, 'type', None) == 'sunburst' for t in fig.data)
    if not has_sunburst:
        try:
            import plotly.express as px
            # use the prepared df to create a sunburst via express (fallback creation)
            px_df = df.copy()
            px_df = px_df.dropna(subset=["Linea", "Objetivo", "cumplimiento_pct"])
            if not px_df.empty:
                px_fig = px.sunburst(px_df, path=["Linea", "Objetivo"], values=None, color="cumplimiento_pct")
                # convert to go.Figure and try to harmonize
                fig = go.Figure(px_fig)
        except Exception:
            # if express also fails, keep original fig and add diagnostic meta
            fig.layout.meta = {"sunburst_forced": False, "reason": "could not build sunburst via px"}

    # Final layout for sunburst
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=780, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
    # mark success
    fig.layout.meta = dict(fig.layout.meta or {}, sunburst_forced=True)
    return fig

def _compute_trends(current: pd.DataFrame, previous: pd.DataFrame):
    if current.empty or previous.empty:
        return [], []
    cur = current[["Id", "Indicador", "cumplimiento_pct"]].dropna(subset=["cumplimiento_pct"]).copy()
    prev = previous[["Id", "cumplimiento_pct"]].dropna(subset=["cumplimiento_pct"]).copy()
    merged = cur.merge(prev, on="Id", suffixes=("", "_prev"))
    if merged.empty:
        return [], []
    merged["variation"] = merged["cumplimiento_pct"] - merged["cumplimiento_pct_prev"]
    best = merged.sort_values("variation", ascending=False).head(3)
    worst = merged.sort_values("variation").head(3)
    return (
        [{"name": str(row["Indicador"]), "change": float(row["variation"])} for _, row in best.iterrows()],
        [{"name": str(row["Indicador"]), "change": float(row["variation"])} for _, row in worst.iterrows()],
    )


def _find_process_column(df: pd.DataFrame) -> str | None:
    for col in ["Proceso", "Subproceso", "ProcesoPadre", "Proceso Padre"]:
        if col in df.columns:
            return col
    return None


def _process_counts(df: pd.DataFrame, process_col: str) -> pd.DataFrame:
    levels = ["Sobrecumplimiento", "Cumplimiento", "Alerta", "Peligro"]
    df = df.copy()
    if "Nivel de cumplimiento" not in df.columns:
        df = _ensure_nivel_cumplimiento(df)
    df["Nivel de cumplimiento"] = df["Nivel de cumplimiento"].fillna("Pendiente de reporte")
    group_col = "Id" if "Id" in df.columns else process_col
    pivot = (
        df[df["Nivel de cumplimiento"].isin(levels)]
          .groupby([process_col, "Nivel de cumplimiento"])[group_col]
          .nunique()
          .reset_index(name="count")
          .pivot(index=process_col, columns="Nivel de cumplimiento", values="count")
          .fillna(0)
    )
    for lvl in levels:
        if lvl not in pivot.columns:
            pivot[lvl] = 0
    return pivot.reset_index()


def _process_improvements(current: pd.DataFrame, previous: pd.DataFrame, process_col: str):
    if current.empty or previous.empty or process_col not in current.columns or process_col not in previous.columns:
        return [], []
    current = current[current["cumplimiento_pct"].notna()]
    previous = previous[previous["cumplimiento_pct"].notna()]
    curr_avg = current.groupby(process_col)["cumplimiento_pct"].mean().reset_index(name="current_avg")
    prev_avg = previous.groupby(process_col)["cumplimiento_pct"].mean().reset_index(name="previous_avg")
    merged = curr_avg.merge(prev_avg, on=process_col, how="inner")
    if merged.empty:
        return [], []
    merged["delta"] = merged["current_avg"] - merged["previous_avg"]
    top = merged.sort_values("delta", ascending=False).head(3)
    alerts = merged[(merged["current_avg"] >= 50) & (merged["current_avg"] < 80) & (merged["delta"] < 0)]
    alerts = alerts.sort_values("delta").head(3)
    return (
        [{"name": str(row[process_col]), "change": float(row["delta"])} for _, row in top.iterrows()],
        [{"name": str(row[process_col]), "change": float(row["delta"])} for _, row in alerts.iterrows()],
    )


def _format_insights(items: list[dict], positive: bool = True):
    if not items:
        return []
    if positive:
        return [f"- **{item['name']}** mejora +{item['change']:.1f}% respecto al año anterior." for item in items]
    return [f"- **{item['name']}** empeora {item['change']:.1f}% respecto al año anterior." for item in items]


def render():
    st.title("Resumen General")
    st.markdown("#### Fuente real: Consolidado Cierres — Resultados Consolidados.xlsx")
    
    consolidado = _load_consolidado_cierres()
    if consolidado.empty:
        st.error("No se pudo cargar la hoja 'Consolidado Cierres' desde data/output/Resultados Consolidados.xlsx.")
        return

    years = _available_years(consolidado)
    if not years:
        st.error("No se encontraron años válidos en los datos.")
        return

    # Meses en español para despliegue
    MESES_NOMBRES = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 1: CMI ESTRATÉG ICO - Visión General
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("📊 CMI ESTRATÉGICO - Visión General")
    st.caption("Fuente real: Consolidado Cierres — Resultados Consolidados.xlsx")
    
    # Filtros independientes para CMI Estratégico
    st.markdown("##### Filtros")
    col_year_e, col_month_e, col_linea = st.columns(3)
    
    with col_year_e:
        year_estrategico = st.selectbox(
            "Año de análisis",
            options=years,
            index=len(years)-1,
            key="cmi_estrategico_year"
        )
    
    with col_month_e:
        available_months_e = _available_months_for_year(consolidado, year_estrategico)
        if available_months_e:
            last_avail_e = max([m for m in available_months_e if 1 <= m <= 12], default=12)
            default_idx_e = last_avail_e - 1
        else:
            default_idx_e = 11
        month_name_estrategico = st.selectbox(
            "Mes de análisis",
            options=MESES_NOMBRES,
            index=default_idx_e,
            key="cmi_estrategico_month"
        )
        month_estrategico = MESES_NOMBRES.index(month_name_estrategico) + 1
    
    # Cargar datos y aplicar filtro CMI Estratégico
    pdi_estrategico = preparar_pdi_con_cierre(int(year_estrategico), int(month_estrategico))
    pdi_estrategico = filter_df_for_cmi_estrategico(pdi_estrategico, id_column="Id")
    
    # Filtro adicional por línea estratégica
    pdi_catalog = load_pdi_catalog()
    lineas_disponibles = sorted(
        pdi_catalog["Linea"].dropna().astype(str).unique().tolist()
        if not pdi_catalog.empty else pdi_estrategico["Linea"].dropna().astype(str).unique().tolist()
    ) if not pdi_estrategico.empty else []
    
    with col_linea:
        linea_seleccionada = st.selectbox(
            "Línea Estratégica",
            options=["Todas"] + lineas_disponibles,
            key="cmi_estrategico_linea"
        )
    
    # Aplicar filtro de línea si seleccionaron una específica
    if linea_seleccionada != "Todas" and not pdi_estrategico.empty:
        pdi_estrategico = pdi_estrategico[pdi_estrategico["Linea"] == linea_seleccionada]
    
    # Mostrar tarjetas KPI para CMI Estratégico
    if not pdi_estrategico.empty:
        st.markdown("##### Métricas Clave de Negocio")
        
        # Agrupar por línea y calcular métricas
        if "Linea" in pdi_estrategico.columns:
            lineas_resumen = pdi_estrategico.groupby("Linea").agg({
                "Indicador": "count",
                "cumplimiento_pct": "mean"
            }).reset_index()
            lineas_resumen.columns = ["Linea", "N_Indicadores", "Cumpl_Promedio"]
            
            # Mostrar tarjetas por línea (máximo 3 por fila)
            for i in range(0, len(lineas_resumen), 3):
                cols = st.columns(3)
                for idx, (_, row) in enumerate(lineas_resumen.iloc[i:i+3].iterrows()):
                    linea = row["Linea"]
                    n_ind = int(row["N_Indicadores"])
                    cumpl = row["Cumpl_Promedio"]
                    
                    # Obtener color de la línea
                    import unicodedata, re
                    def _norm_key(s):
                        t = str(s).strip().lower()
                        t = unicodedata.normalize("NFD", t)
                        t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
                        t = re.sub(r"[^0-9a-z]+", " ", t)
                        return re.sub(r"\s+", " ", t).strip()
                    normalized_color_map = { _norm_key(k): v for k, v in LINEA_COLORS.items() }
                    linea_color = normalized_color_map.get(_norm_key(linea), "#6B728E")
                    
                    with cols[idx]:
                        st.markdown(
                            f"""<div style='background: white; padding: 1.5rem; border-radius: 12px; 
                            border-left: 4px solid {linea_color}; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                            <div style='background: {linea_color}20; padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem;'>
                                <h5 style='margin: 0; color: {linea_color}; font-weight: 600;'>{linea}</h5>
                            </div>
                            <div style='margin-bottom: 0.75rem;'>
                                <div style='font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;'>Indicadores</div>
                                <div style='font-size: 1.5rem; font-weight: 700; color: #1A1A1A;'>{n_ind}</div>
                            </div>
                            <div>
                                <div style='font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;'>% Cumplimiento</div>
                                <div style='font-size: 2rem; font-weight: 700; color: {linea_color};'>{cumpl:.1f}%</div>
                            </div>
                            </div>""",
                            unsafe_allow_html=True
                        )
        
        # Sunburst de alineación de objetivos estratégicos
        st.markdown("##### Alineación de Objetivos Estratégicos")
        sunburst = _build_sunburst(pdi_estrategico)
        st.plotly_chart(sunburst, use_container_width=True)
        
        # Métricas globales KPI
        st.markdown("##### Métricas Clave de Negocio")
        count_total_e = len(pdi_estrategico)
        counts_e = {
            "Sobrecumplimiento": int((pdi_estrategico["Nivel de cumplimiento"] == "Sobrecumplimiento").sum()),
            "Cumplimiento": int((pdi_estrategico["Nivel de cumplimiento"] == "Cumplimiento").sum()),
            "Alerta": int((pdi_estrategico["Nivel de cumplimiento"] == "Alerta").sum()),
            "Peligro": int((pdi_estrategico["Nivel de cumplimiento"] == "Peligro").sum()),
        }
        
        kpi_cols = st.columns(5)
        colors = ["#0B5FFF", "#1A3A5C", "#43A047", "#FBAF17", "#D32F2F"]
        values = [count_total_e, counts_e["Sobrecumplimiento"], counts_e["Cumplimiento"], counts_e["Alerta"], counts_e["Peligro"]]
        labels = ["Total indicadores PDI", "Sobrecumplimiento", "Cumplimiento", "Alerta", "Peligro"]
        for col, label, value, color in zip(kpi_cols, labels, values, colors):
            col.metric(label, value)
        
        # === Análisis de mejora vs histórico ===
        st.markdown("##### Indicadores con Mayor Mejora vs Histórico")
        prev_year_e = year_estrategico - 1
        prev_month_e = _latest_month_for_year(consolidado, prev_year_e)
        if prev_month_e:
            prev_pdi_e = preparar_pdi_con_cierre(prev_year_e, prev_month_e)
            prev_pdi_e = filter_df_for_cmi_estrategico(prev_pdi_e, id_column="Id")
            best_improvements_e, worst_declines_e = _compute_trends(pdi_estrategico, prev_pdi_e)
            
            if best_improvements_e:
                for item in best_improvements_e:
                    st.markdown(f"- **{item['name']}** — +{item['change']:.1f}%")
            else:
                st.markdown("- No hay comparativas disponibles contra el año anterior.")
        else:
            st.markdown("- No hay datos del año anterior para comparar.")
        
        st.markdown("##### Indicadores con Mayor Desmejora vs Histórico")
        if prev_month_e and worst_declines_e:
            for item in worst_declines_e:
                st.markdown(f"- **{item['name']}** — {item['change']:.1f}%")
        else:
            st.markdown("- No hay comparativas disponibles contra el año anterior.")
        
        # === Insights Estratégicos (IA) ===
        st.markdown("##### Insights Estratégicos (IA)")
        best_line = pdi_estrategico.groupby("Linea").agg(cumplimiento_pct=("cumplimiento_pct", "mean")).reset_index()
        best_line = best_line.sort_values("cumplimiento_pct", ascending=False).head(1)
        line_name = str(best_line.iloc[0]["Linea"]) if not best_line.empty else ""
        line_avg = float(best_line.iloc[0]["cumplimiento_pct"]) if not best_line.empty else 0
        health_rate_e = round(((counts_e["Sobrecumplimiento"] + counts_e["Cumplimiento"]) / max(count_total_e, 1)) * 100, 1)
        
        insights_e = []
        if health_rate_e >= 70:
            insights_e.append(f"✅ El {health_rate_e}% de los indicadores PDI están en niveles saludables.")
        elif health_rate_e >= 50:
            insights_e.append(f"⚠️ El {health_rate_e}% de los indicadores PDI están en cumplimiento, con riesgo en algunos objetivos.")
        else:
            insights_e.append(f"🚨 Solo el {health_rate_e}% de los indicadores PDI cumplen expectativas; se requiere acción prioritaria.")
        
        if line_name:
            insights_e.append(f"🌟 La línea \"{line_name}\" lidera con {line_avg:.1f}% de cumplimiento promedio.")
        
        if prev_month_e and best_improvements_e:
            insights_e.append(f"📈 Mejora destacada: \"{best_improvements_e[0]['name']}\" (+{best_improvements_e[0]['change']:.1f}%).")
        
        if prev_month_e and worst_declines_e:
            insights_e.append(f"📉 Atención a \"{worst_declines_e[0]['name']}\" ({worst_declines_e[0]['change']:.1f}%).")
        
        for insight in insights_e:
            st.markdown(f"- {insight}")
    else:
        st.warning("No hay indicadores de CMI Estratégico para el corte seleccionado.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 2: CMI POR PROCESOS - Desempeño Operativo
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("🔧 CMI POR PROCESOS - Desempeño Operativo")
    st.caption("Fuente real: Consolidado Cierres — Resultados Consolidados.xlsx")
    
    # Filtros independientes para CMI por Procesos
    st.markdown("##### Filtros")
    col_year_p, col_month_p, col_tipo = st.columns(3)
    
    with col_year_p:
        year_procesos = st.selectbox(
            "Año de análisis",
            options=years,
            index=len(years)-1,
            key="cmi_procesos_year"
        )
    
    with col_month_p:
        available_months_p = _available_months_for_year(consolidado, year_procesos)
        if available_months_p:
            last_avail_p = max([m for m in available_months_p if 1 <= m <= 12], default=12)
            default_idx_p = last_avail_p - 1
        else:
            default_idx_p = 11
        month_name_procesos = st.selectbox(
            "Mes de análisis",
            options=MESES_NOMBRES,
            index=default_idx_p,
            key="cmi_procesos_month"
        )
        month_procesos = MESES_NOMBRES.index(month_name_procesos) + 1
    
    with col_tipo:
        tipo_proceso_seleccionado = st.selectbox(
            "Tipo de proceso",
            options=["Todos"] + TIPOS_PROCESO,
            key="cmi_procesos_tipo",
            help="Filtrar indicadores por tipo de proceso"
        )
    
    # Cargar datos y aplicar filtro CMI por Procesos
    pdi_procesos = preparar_pdi_con_cierre(int(year_procesos), int(month_procesos))
    pdi_procesos = filter_df_for_cmi_procesos(pdi_procesos, id_column="Id")
    
    # Merge con tipos de proceso
    data_service = DataService()
    map_df = data_service.get_process_map()
    
    if not pdi_procesos.empty and not map_df.empty and "Subproceso" in pdi_procesos.columns and "Tipo de proceso" in map_df.columns:
        pdi_procesos = pdi_procesos.merge(
            map_df[["Subproceso", "Tipo de proceso"]].drop_duplicates(),
            on="Subproceso",
            how="left"
        )
        
        # Aplicar filtro de tipo si seleccionaron uno específico
        if tipo_proceso_seleccionado != "Todos":
            pdi_procesos = pdi_procesos[pdi_procesos["Tipo de proceso"] == tipo_proceso_seleccionado]
        
        # Mostrar tarjetas KPI para CMI por Procesos
        if not pdi_procesos.empty and "Tipo de proceso" in pdi_procesos.columns:
            st.markdown("##### Monitoreo de Procesos Clave")
            
            # Si "Todos" está seleccionado: mostrar tarjetas por tipo de proceso
            if tipo_proceso_seleccionado == "Todos":
                tipos_unicos = sorted([t for t in pdi_procesos["Tipo de proceso"].dropna().unique() if t in TIPOS_PROCESO])
                
                if tipos_unicos:
                    cols = st.columns(min(4, len(tipos_unicos)))
                    
                    for idx, tipo in enumerate(tipos_unicos):
                        df_tipo = pdi_procesos[pdi_procesos["Tipo de proceso"] == tipo]
                        
                        total_indicadores = len(df_tipo)
                        n_subprocesos = df_tipo["Subproceso"].nunique() if "Subproceso" in df_tipo.columns else 0
                        cumpl_promedio = (df_tipo["cumplimiento_pct"].mean()) if "cumplimiento_pct" in df_tipo.columns and not df_tipo["cumplimiento_pct"].isna().all() else 0
                        
                        with cols[idx % len(cols)]:
                            tipo_color = get_tipo_color(tipo, light=False)
                            tipo_color_light = get_tipo_color(tipo, light=True)
                            
                            st.markdown(
                                f"""<div style='background: white; padding: 1.5rem; border-radius: 12px; 
                                border-left: 4px solid {tipo_color}; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                                <div style='background: {tipo_color}20; padding: 0.75rem; border-radius: 8px; margin-bottom: 1rem;'>
                                    <h5 style='margin: 0; color: {tipo_color}; font-weight: 600;'>{tipo}</h5>
                                </div>
                                <div style='margin-bottom: 0.75rem;'>
                                    <div style='font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;'>Subprocesos</div>
                                    <div style='font-size: 1.5rem; font-weight: 700; color: #1A1A1A;'>{n_subprocesos}</div>
                                </div>
                                <div style='margin-bottom: 0.75rem;'>
                                    <div style='font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;'>Indicadores</div>
                                    <div style='font-size: 1.5rem; font-weight: 700; color: #1A1A1A;'>{total_indicadores}</div>
                                </div>
                                <div>
                                    <div style='font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;'>% Cumplimiento</div>
                                    <div style='font-size: 2rem; font-weight: 700; color: {tipo_color};'>{cumpl_promedio:.1f}%</div>
                                </div>
                                </div>""",
                                unsafe_allow_html=True
                            )
            
            # Si se seleccionó un tipo específico: mostrar tarjetas por subproceso
            else:
                subprocesos_del_tipo = sorted(pdi_procesos["Subproceso"].dropna().unique())
                
                if subprocesos_del_tipo:
                    for i in range(0, len(subprocesos_del_tipo), 3):
                        cols = st.columns(3)
                        for idx, subproceso in enumerate(subprocesos_del_tipo[i:i+3]):
                            df_subproceso = pdi_procesos[pdi_procesos["Subproceso"] == subproceso]
                            
                            total_ind = len(df_subproceso)
                            cumpl_prom = (df_subproceso["cumplimiento_pct"].mean()) if "cumplimiento_pct" in df_subproceso.columns and not df_subproceso["cumplimiento_pct"].isna().all() else 0
                            
                            # Color según cumplimiento
                            if cumpl_prom >= 100:
                                color = "#22C55E"
                            elif cumpl_prom >= 80:
                                color = "#FBBF24"
                            else:
                                color = "#EF4444"
                            
                            with cols[idx]:
                                st.markdown(
                                    f"""<div style='background: white; padding: 1.5rem; border-radius: 12px; 
                                    border-left: 4px solid {color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1rem;'>
                                    <div style='background: {color}20; padding: 0.5rem; border-radius: 6px; margin-bottom: 1rem;'>
                                        <h5 style='margin: 0; color: {color}; font-size: 0.9rem; font-weight: 600;'>{subproceso}</h5>
                                    </div>
                                    <div style='margin-bottom: 0.75rem;'>
                                        <div style='font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;'>Indicadores</div>
                                        <div style='font-size: 1.5rem; font-weight: 700; color: #1A1A1A;'>{total_ind}</div>
                                    </div>
                                    <div>
                                        <div style='font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;'>% Cumplimiento</div>
                                        <div style='font-size: 2rem; font-weight: 700; color: {color};'>{cumpl_prom:.1f}%</div>
                                    </div>
                                    </div>""",
                                    unsafe_allow_html=True
                                )
                else:
                    st.info(f"No hay subprocesos del tipo {tipo_proceso_seleccionado} con indicadores en este período.")
            
            # Indicadores con mayor mejora/desmejora vs histórico
            st.markdown("##### Indicadores de Proceso con Mayor Mejora vs Histórico")
            prev_year_p = year_procesos - 1
            prev_month_p = _latest_month_for_year(consolidado, prev_year_p)
            if prev_month_p:
                prev_pdi_procesos = preparar_pdi_con_cierre(prev_year_p, prev_month_p)
                prev_pdi_procesos = filter_df_for_cmi_procesos(prev_pdi_procesos, id_column="Id")
                
                best_improvements, worst_declines = _compute_trends(pdi_procesos, prev_pdi_procesos)
                
                if best_improvements:
                    for item in best_improvements[:3]:
                        st.markdown(f"- **{item['name']}** mejora +{item['change']:.1f}% respecto al año anterior")
                else:
                    st.info("No hay comparación con el año anterior.")
            else:
                st.info("No hay datos del año anterior para comparar.")
            
            # === Gráfico de barras apiladas por tipo de proceso ===
            st.markdown("##### Distribución de Niveles de Cumplimiento por Tipo de Proceso")
            # Cargar consolidado filtrado para análisis por tipo
            process_data = consolidado.copy()
            process_data["Año"] = pd.to_numeric(process_data.get("Año", process_data.get("Ao", pd.NA)), errors="coerce")
            process_data = process_data[process_data["Año"] == year_procesos]
            
            # Filtrar por mes si está disponible
            if "Mes_num" in process_data.columns:
                process_data = process_data[process_data["Mes_num"] == month_procesos]
            
            # Merge con tipos de proceso
            if not process_data.empty and "Subproceso" in process_data.columns:
                process_data = process_data.merge(
                    map_df[["Subproceso", "Tipo de proceso"]].drop_duplicates(),
                    on="Subproceso",
                    how="left"
                )
                
                # Calcular counts por tipo y nivel
                proc_counts = _process_counts(process_data, "Tipo de proceso")
                
                if not proc_counts.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        name='Sobrecumplimiento',
                        x=proc_counts['Tipo de proceso'],
                        y=proc_counts['Sobrecumplimiento'],
                        marker_color='#1A3A5C'
                    ))
                    fig.add_trace(go.Bar(
                        name='Cumplimiento',
                        x=proc_counts['Tipo de proceso'],
                        y=proc_counts['Cumplimiento'],
                        marker_color='#43A047'
                    ))
                    fig.add_trace(go.Bar(
                        name='Alerta',
                        x=proc_counts['Tipo de proceso'],
                        y=proc_counts['Alerta'],
                        marker_color='#FBAF17'
                    ))
                    fig.add_trace(go.Bar(
                        name='Peligro',
                        x=proc_counts['Tipo de proceso'],
                        y=proc_counts['Peligro'],
                        marker_color='#D32F2F'
                    ))
                    fig.update_layout(
                        barmode='stack',
                        xaxis_tickangle=-45,
                        height=480,
                        margin=dict(t=40, b=150),
                        showlegend=True
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay información de niveles de cumplimiento por tipo de proceso.")
            
            # === Análisis comparativo con año anterior ===
            if prev_month_p:
                st.markdown("##### Procesos con Mayor Mejora vs Año Anterior")
                previous_process_data = consolidado.copy()
                previous_process_data["Año"] = pd.to_numeric(
                    previous_process_data.get("Año", previous_process_data.get("Ao", pd.NA)),
                    errors="coerce"
                )
                previous_process_data = previous_process_data[previous_process_data["Año"] == prev_year_p]
                
                if "Mes_num" in previous_process_data.columns:
                    previous_process_data = previous_process_data[previous_process_data["Mes_num"] == prev_month_p]
                
                # Merge con tipos
                if not previous_process_data.empty and "Subproceso" in previous_process_data.columns:
                    previous_process_data = previous_process_data.merge(
                        map_df[["Subproceso", "Tipo de proceso"]].drop_duplicates(),
                        on="Subproceso",
                        how="left"
                    )
                    
                    process_top, process_alert = _process_improvements(
                        process_data, previous_process_data, "Tipo de proceso"
                    )
                    
                    if process_top:
                        for item in process_top:
                            st.markdown(f"- **{item['name']}** — +{item['change']:.1f}%")
                    else:
                        st.markdown("- No hay comparación de procesos con el año anterior.")
                    
                    st.markdown("##### Procesos en Alerta con Empeoramiento")
                    if process_alert:
                        for item in process_alert:
                            st.markdown(f"- **{item['name']}** — {item['change']:.1f}%")
                    else:
                        st.markdown("- No se detectaron procesos en alerta con empeoramiento.")
                    
                    # === Insights Operativos (IA) ===
                    st.markdown("##### Insights Operativos (IA)")
                    total_process = len(process_data) if not process_data.empty else 0
                    health_process = 0
                    if not proc_counts.empty:
                        health_process = proc_counts[['Sobrecumplimiento', 'Cumplimiento']].sum(axis=1).sum()
                    health_pct_p = round(health_process / max(total_process, 1) * 100, 1)
                    
                    insights_p = []
                    if process_top:
                        insights_p.append(f"🚀 {process_top[0]['name']} registra la mayor mejora respecto al año anterior.")
                    if process_alert:
                        insights_p.append(f"⚠️ {process_alert[0]['name']} está en alerta y empeoró respecto al año anterior.")
                    insights_p.append(f"✅ El {health_pct_p}% de los indicadores por proceso están en niveles saludables.")
                    
                    for insight in insights_p:
                        st.markdown(f"- {insight}")
        else:
            st.warning("No se pudo cargar información de tipos de proceso.")
    else:
        st.warning("No hay indicadores de CMI por Procesos para el corte seleccionado.")


if __name__ == "__main__":
    render()
