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
    from services.strategic_indicators import preparar_pdi_con_cierre
    import services.strategic_indicators as si
    from core.config import DATA_OUTPUT
    from core.proceso_types import TIPOS_PROCESO, get_tipo_color
    from core.calculos import simple_categoria_desde_porcentaje
    from streamlit_app.services.data_service import DataService
except (ImportError, ModuleNotFoundError):
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from services.strategic_indicators import preparar_pdi_con_cierre
    import services.strategic_indicators as si
    from core.config import DATA_OUTPUT
    from core.proceso_types import TIPOS_PROCESO, get_tipo_color
    from core.calculos import simple_categoria_desde_porcentaje
    from streamlit_app.services.data_service import DataService

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
    st.title("Resumen general")
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

    col_year, col_month, col_tipo = st.columns(3)
    with col_year:
        selected_year = st.segmented_control("Año de análisis", options=years, default=years[-1])
    with col_month:
        # Mostrar siempre los nombres completos de los meses; por defecto seleccionar
        # el último mes disponible para el año si existe, si no seleccionar Diciembre.
        available_months = _available_months_for_year(consolidado, selected_year)
        # default index: último disponible dentro de MESES_NOMBRES
        if available_months:
            last_avail = max([m for m in available_months if 1 <= m <= 12], default=12)
            default_idx = last_avail - 1
        else:
            default_idx = 11
        selected_month_name = st.selectbox("Mes de análisis", options=MESES_NOMBRES, index=default_idx)
        selected_month = MESES_NOMBRES.index(selected_month_name) + 1
    with col_tipo:
        selected_tipo_proceso = st.selectbox(
            "Tipo de proceso",
            ["Todos"] + TIPOS_PROCESO,
            help="Filtrar indicadores por tipo de proceso"
        )

    month_label = MESES_NOMBRES[selected_month - 1] if selected_month and 1 <= selected_month <= 12 else "último disponible"
    filtros_activos = [f"{selected_year}", f"Mes {month_label}"]
    if selected_tipo_proceso != "Todos":
        filtros_activos.append(f"Tipo: {selected_tipo_proceso}")
    st.caption(f"Filtros activos: {' · '.join(filtros_activos)}")

    # Asegurar que el mes predeterminado sea diciembre si no se selecciona otro
    if selected_month is None:
        selected_month = 12

    pdi_df = preparar_pdi_con_cierre(selected_year, selected_month if selected_month else 12)
    # Aplicar filtros explícitos de año/mes a las visualizaciones
    if not pdi_df.empty:
        if 'Anio' in pdi_df.columns:
            pdi_df['Anio'] = pd.to_numeric(pdi_df['Anio'], errors='coerce')
            pdi_df = pdi_df[pdi_df['Anio'] == int(selected_year)]
        if selected_month and 'Mes' in pdi_df.columns:
            pdi_df['Mes'] = pd.to_numeric(pdi_df['Mes'], errors='coerce')
            pdi_df = pdi_df[pdi_df['Mes'] == int(selected_month)]
    st.caption(f"Filtros aplicados: Año={selected_year}, Mes={selected_month if selected_month else 'último disponible'}")
    if pdi_df.empty:
        st.warning("No hay indicadores PDI disponibles para el año seleccionado.")
        return

    pdi_df["Nivel de cumplimiento"] = pdi_df["Nivel de cumplimiento"].fillna("Pendiente de reporte")
    count_total = len(pdi_df)
    counts = {
        "Sobrecumplimiento": int((pdi_df["Nivel de cumplimiento"] == "Sobrecumplimiento").sum()),
        "Cumplimiento": int((pdi_df["Nivel de cumplimiento"] == "Cumplimiento").sum()),
        "Alerta": int((pdi_df["Nivel de cumplimiento"] == "Alerta").sum()),
        "Peligro": int((pdi_df["Nivel de cumplimiento"] == "Peligro").sum()),
    }

    # ═══ TARJETAS KPI POR TIPO DE PROCESO ═══
    # Cargar mapa de procesos para obtener "Tipo de proceso"
    data_service = DataService()
    map_df = data_service.get_process_map()
    
    if not map_df.empty and "Tipo de proceso" in map_df.columns and "Proceso" in pdi_df.columns:
        # Hacer merge para agregar Tipo de proceso a pdi_df
        pdi_with_tipo = pdi_df.merge(
            map_df[["Proceso", "Tipo de proceso"]].drop_duplicates(),
            on="Proceso",
            how="left"
        )
        
        # Aplicar filtro de tipo de proceso si se seleccionó uno específico
        if selected_tipo_proceso != "Todos":
            pdi_with_tipo = pdi_with_tipo[pdi_with_tipo["Tipo de proceso"] == selected_tipo_proceso]
        
        if not pdi_with_tipo.empty and "Tipo de proceso" in pdi_with_tipo.columns:
            st.markdown("---")
            
            # CASO 1: Mostrar tarjetas por TIPO de proceso (cuando "Todos" está seleccionado)
            if selected_tipo_proceso == "Todos":
                st.markdown("### 📊 Indicadores por Tipo de Proceso")
                
                tipos_unicos = sorted([t for t in pdi_with_tipo["Tipo de proceso"].dropna().unique() if t in TIPOS_PROCESO])
                
                if tipos_unicos:
                    cols = st.columns(min(4, len(tipos_unicos)))
                    
                    for idx, tipo in enumerate(tipos_unicos):
                        df_tipo = pdi_with_tipo[pdi_with_tipo["Tipo de proceso"] == tipo]
                        
                        total_indicadores = len(df_tipo)
                        n_procesos = df_tipo["Proceso"].nunique() if "Proceso" in df_tipo.columns else 0
                        
                        # Calcular % cumplimiento promedio
                        if "cumplimiento_pct" in df_tipo.columns:
                            cumpl_promedio = (df_tipo["cumplimiento_pct"].mean() * 100) if not df_tipo["cumplimiento_pct"].isna().all() else 0
                        else:
                            cumpl_promedio = 0
                        
                        # Contar reportados
                        if "Nivel de cumplimiento" in df_tipo.columns:
                            n_reportados = (df_tipo["Nivel de cumplimiento"] != "Pendiente de reporte").sum()
                            pct_reportados = (n_reportados / total_indicadores * 100) if total_indicadores else 0
                        else:
                            pct_reportados = 0
                        
                        with cols[idx % len(cols)]:
                            tipo_color = get_tipo_color(tipo, light=False)
                            tipo_color_light = get_tipo_color(tipo, light=True)
                            
                            st.markdown(
                                f"""<div style='background: {tipo_color_light}; padding: 1rem; border-radius: 8px; 
                                border-left: 4px solid {tipo_color}; margin-bottom: 0.5rem;'>
                                <h4 style='margin: 0; color: {tipo_color};'>{tipo}</h4>
                                </div>""",
                                unsafe_allow_html=True
                            )
                            
                            st.metric("Procesos", n_procesos)
                            st.metric("Indicadores", total_indicadores)
                            st.metric("% Cumplimiento", f"{cumpl_promedio:.1f}%")
                            st.metric("% Reportados", f"{pct_reportados:.1f}%")
            
            # CASO 2: Mostrar tarjetas por PROCESOS individuales (cuando se seleccionó un tipo específico)
            else:
                st.markdown(f"### 📊 Procesos de tipo: {selected_tipo_proceso}")
                
                procesos_del_tipo = sorted(pdi_with_tipo["Proceso"].dropna().unique())
                
                if procesos_del_tipo:
                    # Mostrar en grid de 3 columnas
                    for i in range(0, len(procesos_del_tipo), 3):
                        cols = st.columns(3)
                        for idx, proceso in enumerate(procesos_del_tipo[i:i+3]):
                            df_proceso = pdi_with_tipo[pdi_with_tipo["Proceso"] == proceso]
                            
                            total_ind = len(df_proceso)
                            
                            if "cumplimiento_pct" in df_proceso.columns:
                                cumpl_prom = (df_proceso["cumplimiento_pct"].mean() * 100) if not df_proceso["cumplimiento_pct"].isna().all() else 0
                            else:
                                cumpl_prom = 0
                            
                            # Determinar color según cumplimiento
                            if cumpl_prom >= 100:
                                color = "#22C55E"  # Verde
                            elif cumpl_prom >= 80:
                                color = "#FBBF24"  # Amarillo
                            else:
                                color = "#EF4444"  # Rojo
                            
                            with cols[idx]:
                                st.markdown(
                                    f"""<div style='background: white; padding: 1rem; border-radius: 8px; 
                                    border-left: 4px solid {color}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                                    <h5 style='margin: 0; color: #1A1A1A; font-size: 14px;'>{proceso}</h5>
                                    </div>""",
                                    unsafe_allow_html=True
                                )
                                st.metric("Indicadores", total_ind)
                                st.metric("% Cumplimiento", f"{cumpl_prom:.1f}%", delta=None)
                else:
                    st.info(f"No hay procesos del tipo {selected_tipo_proceso} con indicadores en este período.")
            
            st.markdown("---")
    
    # Mantener el sunburst como referencia visual
    sunburst = _build_sunburst(pdi_df)
    st.plotly_chart(sunburst, use_container_width=True)
    # Debug: mostrar metadatos del sunburst y commit para verificar versión desplegada
    try:
        meta = getattr(sunburst.layout, 'meta', None)
        import subprocess
        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()
    except Exception:
        meta = getattr(sunburst.layout, 'meta', None)
        commit = None
    st.markdown(f"**DEBUG:** commit={commit} — meta={meta}")

    kpi_cols = st.columns(5)
    colors = ["#0B5FFF", "#1A3A5C", "#43A047", "#FBAF17", "#D32F2F"]
    values = [count_total, counts["Sobrecumplimiento"], counts["Cumplimiento"], counts["Alerta"], counts["Peligro"]]
    labels = ["Total indicadores PDI", "Sobrecumplimiento", "Cumplimiento", "Alerta", "Peligro"]
    for col, label, value, color in zip(kpi_cols, labels, values, colors):
        with col:
            st.markdown(
                f"<div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:18px;text-align:center;'>"
                f"<div style='font-size:30px;font-weight:800;color:{color};'>{value}</div>"
                f"<div style='font-size:12px;color:#64748B;letter-spacing:0.08em;margin-top:8px;'>{label}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("### Indicadores con Mayor Mejora vs Histórico")
    if best_improvements:
        for item in best_improvements:
            st.markdown(f"- {item['name']} — +{item['change']:.1f}%")
    else:
        st.markdown("- No hay comparativas disponibles contra el año anterior.")

    st.markdown("### Indicadores con Mayor Desmejora vs Histórico")
    if worst_declines:
        for item in worst_declines:
            st.markdown(f"- {item['name']} — {item['change']:.1f}%")
    else:
        st.markdown("- No hay comparativas disponibles contra el año anterior.")

    st.markdown("### Insights Estratégicos (IA)")
    best_line = pdi_df.groupby("Linea").agg(cumplimiento_pct=("cumplimiento_pct", "mean")).reset_index()
    best_line = best_line.sort_values("cumplimiento_pct", ascending=False).head(1)
    line_name = str(best_line.iloc[0]["Linea"]) if not best_line.empty else ""
    line_avg = float(best_line.iloc[0]["cumplimiento_pct"]) if not best_line.empty else 0
    health_rate = round(((counts["Sobrecumplimiento"] + counts["Cumplimiento"]) / max(count_total, 1)) * 100, 1)
    insights = []
    if health_rate >= 70:
        insights.append(f"✅ El {health_rate}% de los indicadores PDI están en niveles saludables.")
    elif health_rate >= 50:
        insights.append(f"⚠️ El {health_rate}% de los indicadores PDI están en cumplimiento, con riesgo en algunos objetivos.")
    else:
        insights.append(f"🚨 Solo el {health_rate}% de los indicadores PDI cumplen expectativas; se requiere acción prioritaria.")
    if line_name:
        insights.append(f"🌟 La línea \"{line_name}\" lidera con {line_avg:.1f}% de cumplimiento promedio.")
    if best_improvements:
        insights.append(f"📈 Mejora destacada: \"{best_improvements[0]['name']}\" (+{best_improvements[0]['change']:.1f}%).")
    if worst_declines:
        insights.append(f"📉 Atención a \"{worst_declines[0]['name']}\" ({worst_declines[0]['change']:.1f}%).")
    for insight in insights:
        st.markdown(f"- {insight}")

    st.markdown("---")
    st.subheader("Indicadores por Proceso")
    # Para la visualización por procesos usamos el `consolidado` (hoja Consolidado Cierres)
    # porque contiene la columna `Proceso` y mapeo necesario para todos los indicadores.
    process_col = _find_process_column(consolidado)
    if not process_col:
        st.warning("No se encontró columna de proceso en los datos reales.")
        return
    # Construir `process_data` a partir del `consolidado` (contiene Proceso)
    # Filtrar consolidado con la misma lógica de Año y Mes seleccionados en la página
    process_data = _filter_consolidado_by_year_month(consolidado, selected_year, selected_month)

    # Si por alguna razón `Proceso` no existe, detectar la columna en `process_data`
    detected_col = _find_process_column(process_data)
    if detected_col:
        process_col = detected_col
    if process_data.empty:
        st.warning("No hay datos por proceso para el año seleccionado.")
        return

    total_process = int(process_data["Id"].nunique()) if "Id" in process_data.columns else len(process_data)
    st.markdown(f"**Total indicadores por proceso:** {total_process}")
    # Bloque de diagnóstico para validar niveles de cumplimiento
    with st.expander("Diagnóstico: Niveles de cumplimiento (procesos)", expanded=False):
        st.markdown("Se muestran estadísticas y una muestra de filas para identificar por qué todos aparecen en 'Peligro'.")
        # asegurar columnas
        for c in [process_col, "cumplimiento_pct", "Nivel de cumplimiento", "Id"]:
            if c not in process_data.columns:
                process_data[c] = pd.NA
        # Estadísticas numéricas de cumplimiento
        stats = process_data["cumplimiento_pct"].describe(percentiles=[0.25, 0.5, 0.75]).to_dict()
        st.markdown("**Resumen numérico de `cumplimiento_pct`**")
        st.write({k: (None if pd.isna(v) else float(v)) for k, v in stats.items()})
        # Bins por umbrales esperados
        bins = {
            "<80 (Peligro)": int((process_data["cumplimiento_pct"] < 80).sum()),
            "80-99.9 (Alerta)": int(((process_data["cumplimiento_pct"] >= 80) & (process_data["cumplimiento_pct"] < 100)).sum()),
            "100-104.9 (Cumplimiento)": int(((process_data["cumplimiento_pct"] >= 100) & (process_data["cumplimiento_pct"] < 105)).sum()),
            ">=105 (Sobrecumplimiento)": int((process_data["cumplimiento_pct"] >= 105).sum()),
            "NaN": int(process_data["cumplimiento_pct"].isna().sum()),
        }
        st.markdown("**Conteo por rango (bins)**")
        st.write(bins)
        # Mostrar valor único de Nivel de cumplimiento y limpiar espacios
        st.markdown("**Valores únicos de `Nivel de cumplimiento`**")
        st.write(process_data["Nivel de cumplimiento"].astype(str).str.strip().value_counts())
        # mostrar primeras 20 filas con columnas relevantes
        preview_cols = ["Id", process_col, "cumplimiento_pct", "Nivel de cumplimiento"]
        st.markdown("**Muestra de filas (primeras 20)**")
        st.dataframe(process_data[preview_cols].head(20))
    proc_counts = _process_counts(process_data, process_col)
    if not proc_counts.empty:
        # Mejorar gráfica: usar colores oficiales por categoría y orden definido
        try:
            from core.config import COLOR_CATEGORIA, ORDEN_CATEGORIAS
        except Exception:
            COLOR_CATEGORIA = {
                'Peligro': '#D32F2F', 'Alerta': '#FBAF17', 'Cumplimiento': '#43A047', 'Sobrecumplimiento': '#1A3A5C'
            }
            ORDEN_CATEGORIAS = ['Peligro', 'Alerta', 'Cumplimiento', 'Sobrecumplimiento']

        # Asegurar columnas de orden
        levels = [lvl for lvl in ORDEN_CATEGORIAS if lvl in proc_counts.columns]
        # ordenar procesos por total (desc) para mejor lectura
        proc_counts['_total'] = proc_counts[[c for c in levels]].sum(axis=1)
        proc_counts = proc_counts.sort_values('_total', ascending=False).reset_index(drop=True)

        fig = go.Figure()
        # agregar trazas siguiendo el orden de niveles (stacked)
        for lvl in levels:
            color = COLOR_CATEGORIA.get(lvl, '#6B728E')
            yvals = proc_counts.get(lvl, [0] * len(proc_counts))
            fig.add_trace(go.Bar(name=lvl, x=proc_counts[process_col], y=yvals, marker_color=color,
                                 hovertemplate=f"%{{x}}<br>{lvl}: %{{y}}<extra></extra>"))

        fig.update_layout(barmode='stack', xaxis_tickangle=-45, height=520,
                          margin=dict(t=40, b=180), template='plotly_white',
                          legend=dict(title_text='Nivel de cumplimiento', orientation='v', x=1.02, xanchor='left'))
        fig.update_xaxes(tickfont=dict(size=10), tickangle=-45)
        fig.update_yaxes(title_text='N° indicadores')
        st.plotly_chart(fig, use_container_width=True)
        # Detalle: mostrar indicadores con nivel 'Peligro' (detalle filtrable)
        try:
            peligro_mask = process_data.get('Nivel de cumplimiento').astype(str).str.strip().str.lower().str.contains('peligro', na=False)
            peligro_df = process_data[peligro_mask].copy()
        except Exception:
            peligro_df = pd.DataFrame()

        with st.expander("Indicadores en Peligro (detalle)", expanded=False):
            if peligro_df.empty:
                st.info("No se encontraron indicadores en nivel 'Peligro' para el período seleccionado.")
            else:
                st.markdown(f"**Total indicadores en Peligro:** {len(peligro_df)}")
                proc_col_list = []
                if 'Proceso' in peligro_df.columns:
                    proc_col_list = sorted(peligro_df['Proceso'].dropna().unique())
                if proc_col_list:
                    sel_proc = st.selectbox("Filtrar por proceso", ["Todos"] + proc_col_list)
                    if sel_proc != "Todos":
                        disp_df = peligro_df[peligro_df['Proceso'] == sel_proc]
                    else:
                        disp_df = peligro_df
                else:
                    disp_df = peligro_df
                cols_show = [c for c in ['Id','Indicador','Proceso','Subproceso','cumplimiento_pct','Meta','Ejecucion','Fecha'] if c in disp_df.columns]
                st.dataframe(disp_df[cols_show].reset_index(drop=True), use_container_width=True)
    else:
        st.info("No hay información de niveles de cumplimiento por proceso en el período seleccionado.")

    previous_process_data = _filter_consolidado_by_year_month(consolidado, prev_year, prev_month)
    process_top, process_alert = _process_improvements(process_data, previous_process_data, process_col)

    st.markdown("### Procesos con Mayor Mejora vs Año Anterior")
    if process_top:
        for item in process_top:
            st.markdown(f"- **{item['name']}** — +{item['change']:.1f}%")
    else:
        st.markdown("- No hay comparación de procesos con el año anterior.")

    st.markdown("### Procesos en Alerta con Empeoramiento")
    if process_alert:
        for item in process_alert:
            st.markdown(f"- **{item['name']}** — {item['change']:.1f}%")
    else:
        st.markdown("- No se detectaron procesos en alerta con empeoramiento.")

    health_process = proc_counts[['Sobrecumplimiento', 'Cumplimiento']].sum(axis=1).sum()
    health_pct = round(health_process / max(total_process, 1) * 100, 1)
    st.markdown("### Insights Operativos (IA)")
    if process_top:
        st.markdown(f"- 🚀 {process_top[0]['name']} registra la mayor mejora respecto al año anterior.")
    if process_alert:
        st.markdown(f"- ⚠️ {process_alert[0]['name']} está en alerta y empeoró respecto al año anterior.")
    st.markdown(f"- ✅ El {health_pct}% de los indicadores por proceso están en niveles saludables.")
