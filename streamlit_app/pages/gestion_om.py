from datetime import date, datetime
import json
from pathlib import Path

import pandas as pd
import streamlit as st

_RUTA_KPI_DIAG = (
    Path(__file__).resolve().parents[2] / "data" / "output" / "artifacts" / "kpi_diagnostico.json"
)


def _guardar_kpi_diag(con_ia: bool, elapsed: float) -> None:
    """Persiste una medición de tiempo diagnóstico en el JSON histórico."""
    registro = {
        "ts": datetime.now().isoformat(),
        "con_ia": con_ia,
        "segundos": round(elapsed, 2),
    }
    try:
        if _RUTA_KPI_DIAG.exists():
            with open(_RUTA_KPI_DIAG, "r", encoding="utf-8") as f:
                historico = json.load(f)
        else:
            historico = []
        historico.append(registro)
        _RUTA_KPI_DIAG.parent.mkdir(parents=True, exist_ok=True)
        with open(_RUTA_KPI_DIAG, "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # No bloquear la UI si falla la escritura

try:
    from services.ai_analysis import analizar_texto_indicador as _analizar_texto_puro
    from services.data_loader import cargar_acciones_mejora, cargar_dataset
    from core.config import CACHE_TTL
    from core.db_manager import registros_om_como_dict, guardar_registro_om
    from streamlit_app.utils.formatting import ejecucion_his_signo, meta_his_signo
except (ImportError, ModuleNotFoundError):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parents[2]))
    sys.path.insert(0, str(Path(__file__).parents[2] / "services"))
    from ai_analysis import analizar_texto_indicador as _analizar_texto_puro
    from data_loader import cargar_acciones_mejora, cargar_dataset
    from core.config import CACHE_TTL
    from core.db_manager import registros_om_como_dict, guardar_registro_om
    from streamlit_app.utils.formatting import ejecucion_his_signo, meta_his_signo


def _cargar_registros_om() -> dict:
    """Carga OM sin cache para reflejar cambios inmediatamente."""
    return registros_om_como_dict(anio=None)


def _cargar_avance_om() -> dict:
    """
    Carga los archivos de Plan de accion y calcula el avance promedio por Id Oportunidad de mejora.
    Retorna: {id_oportunidad: avance_promedio}
    """
    import os
    base_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "Plan de accion"
    if not base_path.exists():
        return {}
    
    dfs = []
    for f in base_path.glob("*.xlsx"):
        try:
            df = pd.read_excel(f, dtype=str, na_filter=False)
            cols = df.columns.tolist()
            
            avance_col = next((c for c in cols if "Avance" in c and "%" in c), None)
            
            # Buscar columna "Id Oportunidad de mejora" (no "Estado...")
            id_om_col = next((c for c in cols if "Id Oportunidad de mejora" in c), None)
            if not id_om_col:
                id_om_col = next((c for c in cols if c.startswith("Id ") and "Oportunidad" in c), None)
            
            if id_om_col and avance_col:
                df_subset = df[[id_om_col, avance_col]].copy()
                df_subset.columns = ["Id_OM", "Avance"]
                dfs.append(df_subset)
        except Exception as e:
            continue
    
    if not dfs:
        return {}
    
    df_all = pd.concat(dfs, ignore_index=True)
    df_all["Avance"] = pd.to_numeric(df_all["Avance"], errors="coerce")
    df_all["Id_OM"] = df_all["Id_OM"].astype(str).str.strip()
    
    df_all = df_all.dropna(subset=["Id_OM", "Avance"])
    df_all = df_all[df_all["Id_OM"] != ""]
    df_all = df_all[df_all["Id_OM"].str.lower() != "nan"]
    
    if df_all.empty:
        return {}
    
    max_avance = df_all["Avance"].max()
    if max_avance < 2:
        df_all["Avance"] = df_all["Avance"] * 100

    # Debug: expose internal avances for quick sanity when DEBUG_OM is enabled
    try:
        import os
        if os.getenv("DEBUG_OM", "0") == "1":
            import json
            print("DEBUG_OM avances:", json.dumps(
                df_all.groupby("Id_OM")["Avance"].mean().round(1).to_dict(),
                indent=2,
            ))
    except Exception:
        pass
    
    resultado = df_all.groupby("Id_OM")["Avance"].mean().to_dict()
    
    return {str(k).strip(): round(float(v), 1) for k, v in resultado.items()}


def _cargar_plan_accion_para_om(om_id: str) -> pd.DataFrame:
    """Carga las actividades del plan de acción para un Id Oportunidad de mejora (om_id).

    Devuelve un DataFrame con columnas:
      - Acción
      - Responsable de ejecución
      - Avance (%)
      - Estado (Plan de Acción)
      - Estado (Oportunidad de mejora)
    Si no hay datos, devuelve un DataFrame vacío.
    """
    if not om_id:
        return pd.DataFrame()
    base_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "Plan de accion"
    if not base_path.exists():
        return pd.DataFrame()

    rows = []
    for f in base_path.glob("*.xlsx"):
        try:
            df = pd.read_excel(f, dtype=str, na_filter=False)
        except Exception:
            continue
        cols = df.columns.tolist()
        id_col = next((c for c in cols if "Id Oportunidad de mejora" in c), None)
        if not id_col:
            id_col = next((c for c in cols if c.startswith("Id ") and "Oportunidad" in c), None)
        if not id_col or id_col not in df.columns:
            continue
        subset = df.loc[df[id_col].astype(str).str.strip() == om_id, :]
        if subset.empty:
            continue
        # Build plan action rows
        for _, row in subset.iterrows():
            accion = str(row.get("Id Acción", "")) or str(row.get("Descripci\u00f3n", "")) or str(row.get("Descripcion", ""))
            if not accion:
                accion = str(row.get("Acción", ""))
            resp = str(row.get("Responsable de ejecuci\u00f3n", "")) or str(row.get("Responsable", "")) or str(row.get("Fuente de Identificaci\u00f3n", ""))
            avance = row.get("Avance (%)", row.get("Avance", ""))
            if avance is None or (isinstance(avance, float) and pd.isna(avance)):
                avance = ""
            estado_plan = str(row.get("Estado (Plan de Acci\u00f3n)", "")) or str(row.get("Estado (Plan Acción)", ""))
            estado_om = str(row.get("Estado (Oportunidad de mejora)", "")) or str(row.get("Estado de Oportunidad", ""))
            rows.append({
                "Acción": accion,
                "Responsable de ejecución": resp,
                "Avance (%)": avance,
                "Estado (Plan de Acción)": estado_plan,
                "Estado (Oportunidad de mejora)": estado_om,
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _extraer_tipo_y_identificador(numero_om: str) -> tuple:
    """Extrae el tipo de acción y el identificador del campo numero_om."""
    if not numero_om:
        return ("Sin acción", "")
    for tipo in ["OM Kawak", "Reto Plan Anual", "Proyecto Institucional", "Otro"]:
        if numero_om.startswith(tipo + ":"):
            identificador = numero_om[len(tipo) + 1:].strip()
            return (tipo, identificador)
    return ("Otro", numero_om)


def _color_tipo_accion(tipo: str) -> str:
    """Retorna el color para cada tipo de acción."""
    colores = {
        "OM Kawak": "#3B82F6",
        "Reto Plan Anual": "#F59E0B",
        "Proyecto Institucional": "#8B5CF6",
        "Otro": "#6B7280",
        "Sin acción": "#9CA3AF",
    }
    return colores.get(tipo, "#6B7280")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _cargar_indicadores_riesgo() -> pd.DataFrame:
    df = cargar_dataset()
    if df.empty:
        return df

    # No hacer drop_duplicates - mantener todos los registros por indicador y período
    if "Categoria" in df.columns:
        df = df[df["Categoria"].isin(["Peligro", "Alerta"])].copy()

    cols = [
        c
        for c in [
            "Id", "Indicador", "Proceso", "Subproceso", "Categoria", "Cumplimiento", "Cumplimiento_pct", "Periodicidad", "Anio", "Mes",
            "Meta", "Ejecucion", "Meta_Signo", "Meta s", "MetaS", "Ejecucion_Signo", "Ejecución s", "Ejecucion s", "EjecS",
            "Decimales", "Decimales_Meta", "Decimales_Ejecucion", "DecimalesEje", "DecMeta", "DecEjec",
        ]
        if c in df.columns
    ]
    return df[cols].reset_index(drop=True)


def _meses_disponibles() -> list[str]:
    return [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]


def _mes_a_nombre(mes) -> str:
    if pd.isna(mes):
        return ""
    if isinstance(mes, (int, float)) and not isinstance(mes, bool):
        try:
            idx = int(mes)
            return _meses_disponibles()[idx - 1] if 1 <= idx <= 12 else str(mes)
        except Exception:
            return str(mes)

    texto = str(mes).strip()
    if not texto:
        return ""

    texto_lower = texto.lower()
    meses_map = {
        "ene": "Enero",
        "ene.": "Enero",
        "enero": "Enero",
        "feb": "Febrero",
        "feb.": "Febrero",
        "febrero": "Febrero",
        "mar": "Marzo",
        "mar.": "Marzo",
        "marzo": "Marzo",
        "abr": "Abril",
        "abr.": "Abril",
        "abril": "Abril",
        "may": "Mayo",
        "mayo": "Mayo",
        "jun": "Junio",
        "jun.": "Junio",
        "junio": "Junio",
        "jul": "Julio",
        "jul.": "Julio",
        "julio": "Julio",
        "ago": "Agosto",
        "ago.": "Agosto",
        "agosto": "Agosto",
        "sep": "Septiembre",
        "sep.": "Septiembre",
        "sept": "Septiembre",
        "sept.": "Septiembre",
        "septiembre": "Septiembre",
        "oct": "Octubre",
        "oct.": "Octubre",
        "octubre": "Octubre",
        "nov": "Noviembre",
        "nov.": "Noviembre",
        "noviembre": "Noviembre",
        "dic": "Diciembre",
        "dic.": "Diciembre",
        "diciembre": "Diciembre",
    }
    return meses_map.get(texto_lower, texto.capitalize())


def _normalizar_periodicidad(periodicidad: str) -> str:
    p = str(periodicidad or "").strip().lower()
    p = p.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return p


def _periodos_disponibles(periodicidad: str) -> list[str]:
    p = _normalizar_periodicidad(periodicidad)
    if p == "bimestral":
        return ["Ene-Feb", "Mar-Abr", "May-Jun", "Jul-Ago", "Sep-Oct", "Nov-Dic"]
    if p == "trimestral":
        return ["Ene-Mar", "Abr-Jun", "Jul-Sep", "Oct-Dic"]
    if p == "semestral":
        return ["Ene-Jun", "Jul-Dic"]
    if p == "anual":
        return ["Anual"]
    return _meses_disponibles()


def _indice_periodo_actual(periodicidad: str, periodos: list[str]) -> int:
    if not periodos:
        return 0

    mes = date.today().month
    p = _normalizar_periodicidad(periodicidad)

    if p == "mensual":
        return max(0, min(len(periodos) - 1, mes - 1))
    if p == "bimestral":
        return max(0, min(len(periodos) - 1, (mes - 1) // 2))
    if p == "trimestral":
        return max(0, min(len(periodos) - 1, (mes - 1) // 3))
    if p == "semestral":
        return 0 if mes <= 6 else 1
    return 0


def _id_str(v) -> str:
    if pd.isna(v):
        return ""
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none"}:
        return ""
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except Exception:
        pass
    return s


def _buscar_col(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    if df.empty:
        return None
    normalizadas = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidatos:
        key = cand.strip().lower()
        if key in normalizadas:
            return normalizadas[key]
    return None


def _bool_si(v) -> bool:
    if pd.isna(v):
        return False
    s = str(v).strip().lower()
    return s in {"1", "si", "sí", "true", "x", "yes", "y"}


def _init_diag_metrics() -> None:
    if "om_diag_metrics" not in st.session_state:
        st.session_state["om_diag_metrics"] = {
            "with_ai_sec": [],
            "without_ai_sec": [],
        }


def _registrar_tiempo_diagnostico(con_ia: bool) -> None:
    inicio = st.session_state.get("om_diag_start")
    if inicio is None:
        return

    elapsed = (datetime.now() - inicio).total_seconds()
    if elapsed <= 0:
        return

    metrics = st.session_state["om_diag_metrics"]
    if con_ia:
        metrics["with_ai_sec"].append(elapsed)
    else:
        metrics["without_ai_sec"].append(elapsed)

    _guardar_kpi_diag(con_ia, elapsed)


def _render_diag_kpi() -> None:
    metrics = st.session_state["om_diag_metrics"]
    with_ai = metrics["with_ai_sec"]
    without_ai = metrics["without_ai_sec"]

    avg_with = (sum(with_ai) / len(with_ai)) if with_ai else None
    avg_without = (sum(without_ai) / len(without_ai)) if without_ai else None

    st.markdown("### KPI de diagnostico (Sesion actual)")
    k1, k2, k3 = st.columns(3)

    with k1:
        val = f"{avg_without / 60:.1f} min" if avg_without is not None else "N/D"
        st.metric("Antes (sin IA)", val)

    with k2:
        val = f"{avg_with / 60:.1f} min" if avg_with is not None else "N/D"
        st.metric("Despues (con IA)", val)

    with k3:
        if avg_with is not None and avg_without is not None and avg_without > 0:
            ahorro_sec = avg_without - avg_with
            ahorro_pct = (ahorro_sec / avg_without) * 100
            st.metric("Reduccion estimada", f"{ahorro_sec / 60:.1f} min", delta=f"{ahorro_pct:+.1f}%")
        else:
            st.metric("Reduccion estimada", "N/D")

    st.caption(
        f"Muestras: sin IA={len(without_ai)} | con IA={len(with_ai)}. "
        "Metricas de sesion para baseline operativo rapido."
    )
    # ── Histórico de sesiones anteriores ──────────────────────────────────
    if _RUTA_KPI_DIAG.exists():
        try:
            with open(_RUTA_KPI_DIAG, "r", encoding="utf-8") as f:
                hist = json.load(f)
            if hist:
                df_hist = pd.DataFrame(hist)
                df_hist["segundos"] = pd.to_numeric(df_hist["segundos"], errors="coerce")
                h_sin = df_hist[~df_hist["con_ia"]]["segundos"].dropna()
                h_con = df_hist[df_hist["con_ia"]]["segundos"].dropna()
                h_avg_sin = float(h_sin.mean()) if not h_sin.empty else None
                h_avg_con = float(h_con.mean()) if not h_con.empty else None
                with st.expander(f"Baseline histórico ({len(df_hist)} mediciones acumuladas)", expanded=False):
                    hk1, hk2, hk3 = st.columns(3)
                    hk1.metric("Promedio sin IA (histórico)", f"{h_avg_sin / 60:.1f} min" if h_avg_sin else "N/D")
                    hk2.metric("Promedio con IA (histórico)", f"{h_avg_con / 60:.1f} min" if h_avg_con else "N/D")
                    if h_avg_sin and h_avg_con and h_avg_sin > 0:
                        reduccion = (h_avg_sin - h_avg_con) / h_avg_sin * 100
                        hk3.metric("Reduccion historica", f"{reduccion:.1f}%")
                    else:
                        hk3.metric("Reduccion historica", "N/D")
        except Exception:
            pass

def _build_consolidado_om(df_reg: pd.DataFrame) -> pd.DataFrame:
    total = len(df_reg)
    con_om = int((df_reg.get("tiene_om", pd.Series(dtype=int)) == 1).sum())
    sin_om = total - con_om
    cobertura = (con_om / total * 100) if total > 0 else 0.0

    return pd.DataFrame([
        {
            "Registros totales": total,
            "Con OM": con_om,
            "Sin OM": sin_om,
            "Cobertura OM (%)": round(cobertura, 1),
        }
    ])


def _build_consolidado_por_periodo(df_reg: pd.DataFrame) -> pd.DataFrame:
    if df_reg.empty:
        return df_reg

    df = df_reg.copy()
    if "tiene_om" in df.columns:
        df["tiene_om"] = pd.to_numeric(df["tiene_om"], errors="coerce").fillna(0).astype(int)
    else:
        df["tiene_om"] = 0

    agrupado = (
        df.groupby(["anio", "periodo"], dropna=False)
        .agg(registros=("id", "count"), con_om=("tiene_om", "sum"))
        .reset_index()
    )
    agrupado["sin_om"] = agrupado["registros"] - agrupado["con_om"]
    agrupado["cobertura_om_pct"] = ((agrupado["con_om"] / agrupado["registros"]).fillna(0) * 100).round(1)
    return agrupado.sort_values(["anio", "periodo"], ascending=[False, True]).reset_index(drop=True)


def _resumen_om_por_id(df_reg: pd.DataFrame, avances_om: dict = None) -> pd.DataFrame:
    if df_reg.empty:
        return pd.DataFrame(columns=["Id", "tiene_om", "numero_om", "periodo_om", "anio_om", "avance_om", "tipo_accion", "identificador"])

    df = df_reg.copy()
    df["Id"] = df.get("id_indicador", "").apply(_id_str)
    df = df[df["Id"] != ""].copy()
    if df.empty:
        return pd.DataFrame(columns=["Id", "tiene_om", "numero_om", "periodo_om", "anio_om", "avance_om", "tipo_accion", "identificador"])

    if "fecha_registro" in df.columns:
        df = df.sort_values("fecha_registro", ascending=False)

    out = (
        df.groupby("Id", as_index=False)
        .agg(
            tiene_om=("tiene_om", "max"),
            tipo_accion=("tipo_accion", "first"),
            numero_om=("numero_om", "first"),
            periodo_om=("periodo", "first"),
            anio_om=("anio", "first"),
        )
    )
    out["tiene_om"] = pd.to_numeric(out["tiene_om"], errors="coerce").fillna(0).astype(int)
    out["tipo_accion"] = out["tipo_accion"].fillna("OM Kawak")
    out["identificador"] = out["numero_om"].fillna("")
    
    if avances_om and isinstance(avances_om, dict) and len(avances_om) > 0:
        def buscar_avance(x):
            import re
            x_clean = str(x).strip()
            if not x_clean:
                return 0
            # Prefijo exacto
            if x_clean in avances_om:
                return avances_om[x_clean]
            # Digitos puros (ej. 'OM 440' -> '440')
            m = re.findall(r"\d+", x_clean)
            if m:
                key = m[0]
                if key in avances_om:
                    return avances_om[key]
            # Upper / lower variants
            if x_clean.upper() in avances_om:
                return avances_om[x_clean.upper()]
            if x_clean.lower() in avances_om:
                return avances_om[x_clean.lower()]
            return 0
        out["avance_om"] = out["identificador"].apply(buscar_avance)
    else:
        out["avance_om"] = 0
    
    out["avance_om"] = pd.to_numeric(out["avance_om"], errors="coerce").fillna(0)
    
    return out


def _resumen_acciones_por_id(df_acc: pd.DataFrame) -> pd.DataFrame:
    base_cols = ["Id", "tiene_accion", "avance_accion", "mitiga_reto", "mitiga_proyecto"]
    if df_acc.empty:
        return pd.DataFrame(columns=base_cols)

    id_col = _buscar_col(df_acc, ["Id", "ID", "Id Indicador", "ID Indicador", "id_indicador", "id indicador"]) or ""
    if not id_col:
        return pd.DataFrame(columns=base_cols)

    av_col = _buscar_col(df_acc, ["AVANCE", "Avance", "% Avance", "Porcentaje Avance"]) or ""
    tipo_col = _buscar_col(df_acc, ["Tipo", "TIPO", "Tipo de accion", "Tipo Accion", "TIPO_ACCION"]) or ""
    reto_col = _buscar_col(df_acc, ["Reto", "RETO", "Mitiga con reto", "mitiga_reto"]) or ""
    proyecto_col = _buscar_col(df_acc, ["Proyecto", "PROYECTO", "Mitiga con proyecto", "mitiga_proyecto"]) or ""

    df = df_acc.copy()
    df["Id"] = df[id_col].apply(_id_str)
    df = df[df["Id"] != ""].copy()
    if df.empty:
        return pd.DataFrame(columns=base_cols)

    df["_avance"] = pd.to_numeric(df[av_col], errors="coerce") if av_col else pd.NA

    if tipo_col:
        tipo = df[tipo_col].astype(str).str.lower()
        df["_is_reto"] = tipo.str.contains("reto", na=False)
        df["_is_proyecto"] = tipo.str.contains("proyecto", na=False)
    else:
        df["_is_reto"] = False
        df["_is_proyecto"] = False

    if reto_col:
        df["_is_reto"] = df["_is_reto"] | df[reto_col].apply(_bool_si)
    if proyecto_col:
        df["_is_proyecto"] = df["_is_proyecto"] | df[proyecto_col].apply(_bool_si)

    out = (
        df.groupby("Id", as_index=False)
        .agg(
            tiene_accion=("Id", "count"),
            avance_accion=("_avance", "mean"),
            mitiga_reto=("_is_reto", "max"),
            mitiga_proyecto=("_is_proyecto", "max"),
        )
    )
    out["tiene_accion"] = (out["tiene_accion"] > 0).astype(int)
    out["avance_accion"] = pd.to_numeric(out["avance_accion"], errors="coerce").round(1)
    out["mitiga_reto"] = out["mitiga_reto"].astype(bool)
    out["mitiga_proyecto"] = out["mitiga_proyecto"].astype(bool)
    return out


def _matriz_mitigacion_peligro(df_riesgo: pd.DataFrame, df_reg: pd.DataFrame, df_acc: pd.DataFrame, avances_om: dict = None) -> pd.DataFrame:
    if df_riesgo.empty:
        return pd.DataFrame()

    df_peligro = df_riesgo[df_riesgo.get("Categoria", "").astype(str).str.lower() == "peligro"].copy()
    if df_peligro.empty:
        return pd.DataFrame()

    df_peligro["Id"] = df_peligro["Id"].apply(_id_str)

    om = _resumen_om_por_id(df_reg, avances_om)
    acc = _resumen_acciones_por_id(df_acc)

    m = df_peligro.merge(om, on="Id", how="left").merge(acc, on="Id", how="left")
    for c in ["tiene_om", "tiene_accion"]:
        m[c] = pd.to_numeric(m.get(c), errors="coerce").fillna(0).astype(int)
    for c in ["mitiga_reto", "mitiga_proyecto"]:
        m[c] = m.get(c).fillna(False).astype(bool)

    m["tipo_mitigacion"] = "Sin accion"
    m.loc[m["tiene_om"] == 1, "tipo_mitigacion"] = "OM"
    m.loc[m["tiene_accion"] == 1, "tipo_mitigacion"] = "Accion de mejora"
    m.loc[m["mitiga_reto"], "tipo_mitigacion"] = "Reto"
    m.loc[m["mitiga_proyecto"], "tipo_mitigacion"] = "Proyecto"

    m["accion_creada"] = (m["tiene_om"] == 1) | (m["tiene_accion"] == 1)
    m["avance_mitigacion_pct"] = pd.to_numeric(m.get("avance_accion"), errors="coerce").round(1)

    # Incluir porcentaje de cumplimiento actual (si está disponible) y asegurar número OM
    # Cumplimiento puede estar en columnas 'Cumplimiento' (0-100 o 0-1) o 'Cumplimiento_norm' (0-1)
    if "Cumplimiento" in m.columns:
        m["Cumplimiento_pct"] = pd.to_numeric(m.get("Cumplimiento"), errors="coerce")
        # si está en rango 0..1, convertir a 0..100
        if m["Cumplimiento_pct"].max(skipna=True) <= 1.5:
            m["Cumplimiento_pct"] = (m["Cumplimiento_pct"] * 100).round(1)
        else:
            m["Cumplimiento_pct"] = m["Cumplimiento_pct"].round(1)
    elif "Cumplimiento_norm" in m.columns:
        m["Cumplimiento_pct"] = (pd.to_numeric(m.get("Cumplimiento_norm"), errors="coerce") * 100).round(1)
    else:
        m["Cumplimiento_pct"] = pd.NA

    # Asegurar que numero_om exista (viene de la tabla registros_om)
    if "numero_om" not in m.columns:
        m["numero_om"] = ""
    if "tipo_accion" not in m.columns:
        m["tipo_accion"] = "Sin acción"
    if "identificador" not in m.columns:
        m["identificador"] = ""

    # Añadir columna Ver más solo si hay OM registrada (tiene_om=1 y existe identificador)
    if "Id" in m.columns:
        def _link_ver_mas(row):
            if int(row.get("tiene_om", 0) or 0) == 1:
                om_num = str(row.get("identificador", "")).strip()
                if om_num:
                    return f"<a href='?ver_mas={om_num}'>Ver más</a>"
            return ""
        m["Ver_mas"] = m.apply(_link_ver_mas, axis=1)

    cols = [
        "Id", "Indicador", "Proceso", "Subproceso", "Periodicidad", "Categoria",
        "tiene_om", "Ver_mas", "numero_om", "tipo_accion", "identificador", "avance_om", "tipo_mitigacion", "Cumplimiento_pct",
        "Meta", "Ejecucion",
        "Meta_Signo", "Meta s", "MetaS", "Ejecucion_Signo", "Ejecución s", "Ejecucion s", "EjecS",
        "Decimales", "Decimales_Meta", "Decimales_Ejecucion", "DecimalesEje", "DecMeta", "DecEjec",
    ]
    cols = [c for c in cols if c in m.columns]
    m = m[cols]
    return m.sort_values(["tipo_mitigacion", "Id"], ascending=[True, True]).reset_index(drop=True)


def _construir_tabla_peligro(df_riesgo: pd.DataFrame, registros_om: dict, mes_sel: str, anio_sel: str, proc_sel: str, sub_sel: str, avances_om: dict = None) -> pd.DataFrame:
    """Construye la tabla de indicadores en peligro aplicando filtros."""
    if df_riesgo.empty:
        return pd.DataFrame()

    # Aplicar filtros
    df_filtrado = df_riesgo.copy()

    if mes_sel:
        df_filtrado = df_filtrado[df_filtrado.get("Mes", "").astype(str) == mes_sel]

    if anio_sel:
        df_filtrado = df_filtrado[df_filtrado.get("Anio", "").astype(str) == str(anio_sel)]

    if proc_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado.get("Proceso", "").astype(str) == proc_sel]

    if sub_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado.get("Subproceso", "").astype(str) == sub_sel]

    if df_filtrado.empty:
        return pd.DataFrame()

    # Convertir registros_om dict a DataFrame esperado por _resumen_om_por_id
    if registros_om:
        df_reg = pd.DataFrame([
            {
                "id_indicador": k,
                "tiene_om": v.get("tiene_om", False),
                "tipo_accion": v.get("tipo_accion", "OM Kawak"),
                "numero_om": v.get("numero_om", ""),
                "periodo": v.get("periodo", ""),
                "anio": v.get("anio", ""),
            }
            for k, v in registros_om.items()
        ])
    else:
        df_reg = pd.DataFrame()

    df_acc = pd.DataFrame()  # Por ahora vacío, se puede implementar si hay acciones

    # Usar la función existente para construir la matriz
    return _matriz_mitigacion_peligro(df_filtrado, df_reg, df_acc)


def _build_option_label(row) -> str:
    """Construye la etiqueta para las opciones del selectbox de indicadores."""
    indicador_id = row.get("Id", "")
    indicador_nombre = row.get("Indicador", "")
    return f"{indicador_id} - {indicador_nombre}"


def _generar_tabla_html(df: pd.DataFrame) -> str:
    """Genera una tabla HTML con estilos y colores según nivel de cumplimiento."""
    if df.empty:
        return ""

    def _icono_cumplimiento(val):
        if pd.isna(val):
            return "⚪"
        if val >= 105:
            return "🔵"
        elif val >= 100:
            return "🟢"
        elif val >= 80:
            return "🟡"
        else:
            return "🔴"

    def _color_tipo_accion_html(tipo: str) -> str:
        colores = {
            "OM Kawak": "#3B82F6",
            "Reto Plan Anual": "#F59E0B",
            "Proyecto Institucional": "#8B5CF6",
            "Otro": "#6B7280",
            "Sin acción": "#9CA3AF",
        }
        return colores.get(tipo, "#6B7280")

    cols = list(df.columns)
    cols_excluir = {
        "accion_creada", "mitiga_reto", "mitiga_proyecto", "avance_mitigacion_pct",
        "Meta_Signo", "Meta s", "MetaS", "Ejecucion_Signo", "Ejecución s", "Ejecucion s", "EjecS",
        "Decimales", "Decimales_Meta", "Decimales_Ejecucion", "DecimalesEje", "DecMeta", "DecEjec",
        "numero_om", "tipo_mitigacion", "Proceso",
    }
    cols = [c for c in cols if c not in cols_excluir]
    cols_orden = ["Id", "Indicador", "Subproceso", "Periodicidad", "Meta", "Ejecucion", "Cumplimiento_pct", "Categoria", "tipo_accion", "identificador", "avance_om", "tiene_om"]
    cols = [c for c in cols_orden if c in cols]
    
    rename_map = {
        "Cumplimiento_pct": "Cumplimiento",
        "avance_om": "Avance OM",
        "tiene_om": "Ver más",
        "tipo_accion": "Tipo de Acción",
        "identificador": "OM"
    }
    df_display = df[cols].copy()
    df_display.columns = [rename_map.get(c, c) for c in df_display.columns]
    
    def _icono_cumpl(val):
        if pd.isna(val):
            return "⚪"
        if val >= 105:
            return "🔵"
        elif val >= 100:
            return "🟢"
        elif val >= 80:
            return "🟡"
        return "🔴"
    
    df_display["Cumplimiento"] = df_display["Cumplimiento"].apply(lambda x: f"{_icono_cumpl(x)} {x}%" if pd.notna(x) else "-")
    
    def _color_tipo(t):
        colores = {"OM Kawak": "blue", "Reto Plan Anual": "orange", "Proyecto Institucional": "purple", "Otro": "gray"}
        return colores.get(t, "gray")
    
    return df_display


def render():
    st.title("Gestión OM")
    st.caption("Filtrado por mes, año, proceso y subproceso. Registra OM abiertas o pendientes sobre indicadores en Peligro.")

    df_riesgo = _cargar_indicadores_riesgo()
    if df_riesgo.empty:
        st.warning("No hay indicadores en riesgo para mostrar.")
        return

    if "Mes" in df_riesgo.columns:
        df_riesgo["Mes"] = df_riesgo["Mes"].apply(_mes_a_nombre)
    else:
        df_riesgo["Mes"] = ""

    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    anios = ["2025", "2026"]

    procesos = ["Todos"]
    if "Proceso" in df_riesgo.columns:
        procesos += sorted(df_riesgo["Proceso"].dropna().astype(str).unique().tolist())

    subprocesos = ["Todos"]
    if "Subproceso" in df_riesgo.columns:
        subprocesos += sorted(df_riesgo["Subproceso"].dropna().astype(str).unique().tolist())

    with st.expander("Filtros", expanded=True):
        fa, fm, fp, fs = st.columns(4)
        with fa:
            anio_sel = st.segmented_control("Año", options=anios, default="2025")
        with fm:
            default_mes = meses.index("Diciembre")
            mes_sel = st.selectbox("Mes", meses, index=default_mes)
        with fp:
            proc_sel = st.selectbox("Proceso", procesos, index=0)
        with fs:
            sub_sel = st.selectbox("Subproceso", subprocesos, index=0)

    registros_om = _cargar_registros_om()
    avances_om = _cargar_avance_om()
    
    df_tabla = _construir_tabla_peligro(df_riesgo, registros_om, mes_sel, anio_sel, proc_sel, sub_sel, avances_om)
    # Soporte: abrir popup desde enlace Ver más usando query params
    try:
        params = st.experimental_get_query_params()
        if "ver_mas" in params and params["ver_mas"]:
            om_id_q = str(params["ver_mas"][0])
            if om_id_q:
                st.session_state["om_popup_open"] = True
                st.session_state["om_popup_id"] = om_id_q
    except Exception:
        pass
    # Debug: expose avances_om mapping for troubleshooting UI
    try:
        import os
        if os.getenv("DEBUG_OM_UI", "0") == "1":
            st.write("DEBUG avances_om:")
            st.json(avances_om)
    except Exception:
        pass

    if df_tabla.empty:
        st.info("No hay indicadores en Peligro con los filtros seleccionados.")
        return

    total_peligro = len(df_tabla)
    st.markdown(f"### 📊 Indicadores en Peligro: {total_peligro} ({mes_sel} {anio_sel})")

    # --- Visualización mejorada de la tabla con expansión por fila ---
    from streamlit_app.utils.formatting import formatear_meta_ejecucion_df
    df_tabla_fmt = formatear_meta_ejecucion_df(df_tabla.copy(), meta_col="Meta", ejec_col="Ejecucion")
    # Definir columnas a mostrar
    cols = ["Id", "Indicador", "Subproceso", "Periodicidad", "Meta", "Ejecucion", "Cumplimiento_pct", "Categoria", "Tipo de Acción", "OM", "Avance OM", "Ver más"]
    cols = [c for c in cols if c in df_tabla_fmt.columns]
    st.markdown("""
    <style>
    .om-bar-bg { height: 18px; border-radius: 8px; background: #F3F4F6; position: relative; }
    .om-bar-fill { height: 18px; border-radius: 8px; position: absolute; left: 0; top: 0; }
    .om-badge { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 12px; font-weight: 600; color: #fff; margin-right: 2px; }
    .om-kawak { background: #3B82F6; }
    .om-reto { background: #F59E0B; }
    .om-proy { background: #8B5CF6; }
    .om-otro { background: #6B7280; }
    .om-sin { background: #9CA3AF; color: #222; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div style='background:#1E293B;color:#fff;padding:8px 4px;font-weight:bold;border-radius:6px 6px 0 0;'>"
                + " | ".join(cols) + "</div>", unsafe_allow_html=True)
    for idx, row in df_tabla_fmt.iterrows():
        c1, c2 = st.columns([0.97, 0.03])
        with c1:
            st.markdown("<div style='border-bottom:1px solid #E5E7EB;padding:4px 0;'>" +
                " | ".join([
                    str(row[c]) if c not in ["Avance OM", "Tipo de Acción"]
                    else (barra_avance_om(row["Avance OM"]) if c=="Avance OM" else badge_tipo_accion(row["Tipo de Acción"]))
                for c in cols]) + "</div>", unsafe_allow_html=True)
        with c2:
            om_id = row["OM"] if "OM" in row else ""
            tiene_om = row["Ver más"] if "Ver más" in row else 0
            if tiene_om == 1 and om_id and str(om_id).lower() != "nan":
                expand_key = f"expand_om_{om_id}"
                expanded = st.toggle("", key=expand_key, label_visibility="collapsed")
                if expanded:
                    plan_df = _cargar_plan_accion_para_om(om_id)
                    campos = ["Id Acción", "Acción", "Responsable de ejecución", "Avance (%)", "Estado (Plan de Acción)", "Estado (Oportunidad de mejora)"]
                    if plan_df is not None and not plan_df.empty:
                        df_show = plan_df.copy()
                        renames = {}
                        for c in df_show.columns:
                            if c.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u") == "id accion":
                                renames[c] = "Id Acción"
                            if c.lower().startswith("accion"):
                                renames[c] = "Acción"
                            if "responsable" in c.lower():
                                renames[c] = "Responsable de ejecución"
                            if "avance" in c.lower():
                                renames[c] = "Avance (%)"
                            if "plan de accion" in c.lower():
                                renames[c] = "Estado (Plan de Acción)"
                            if "oportunidad" in c.lower():
                                renames[c] = "Estado (Oportunidad de mejora)"
                        df_show = df_show.rename(columns=renames)
                        df_show = df_show[[c for c in campos if c in df_show.columns]].copy()
                        st.markdown("<div style='background:#F8FAFC;padding:8px 0 8px 0;border-radius:0 0 8px 8px;'>", unsafe_allow_html=True)
                        st.write(df_show.style.set_properties(**{"text-align": "center"}), unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.info("Sin actividades.")

    def barra_avance_om(pct):
        if pd.isna(pct) or pct == 0:
            color = "#F3F4F6"
            icon = "⚪"
            bar = f'''<div class=\"om-bar-bg\"><div class=\"om-bar-fill\" style=\"width:0;background:{color}\"></div><span style=\"position:absolute;left:8px;top:0;font-size:13px;font-weight:600;color:#888;\">{icon} -</span></div>'''
            return bar
        color = "#F87171"  # rojo
        icon = "🔴"
        if pct >= 105:
            color = "#2563EB"; icon = "🔵"
        elif pct >= 100:
            color = "#22C55E"; icon = "🟢"
        elif pct >= 80:
            color = "#FACC15"; icon = "🟡"
        bar = f'''<div class=\"om-bar-bg\"><div class=\"om-bar-fill\" style=\"width:{min(100,pct)}%;background:{color}\"></div><span style=\"position:absolute;left:8px;top:0;font-size:13px;font-weight:600;color:#222;\">{icon} {pct:.1f}%</span></div>'''
        return bar

    def badge_tipo_accion(tipo):
        clases = {
            "OM Kawak": "om-badge om-kawak",
            "Reto Plan Anual": "om-badge om-reto",
            "Proyecto Institucional": "om-badge om-proy",
            "Otro": "om-badge om-otro",
            "Sin acción": "om-badge om-sin",
        }
        return f'<span class="{clases.get(tipo,"om-badge om-otro")}">{tipo}</span>'

    # Construir tabla HTML con barra y badges
    table_html = "<table style='width:100%;border-collapse:collapse;font-size:15px;'>"
    # Encabezados
    table_html += "<tr>"
    for col in df_display.columns:
        table_html += f"<th style='padding:6px 4px;background:#F1F5F9;border-bottom:2px solid #E5E7EB;text-align:left;'>{col}</th>"
    table_html += "</tr>"
    # Filas
    for idx, row in df_display.iterrows():
        bg = "#fff" if idx%2==0 else "#F9FAFB"
        table_html += f"<tr style='background:{bg};'>"
        for col in df_display.columns:
            val = row[col]
            if col == "Avance OM":
                bar = barra_avance_om(row["Avance OM"] if "Avance OM" in row else 0)
                table_html += f"<td style='padding:4px 2px;vertical-align:middle;min-width:120px;'>{bar}</td>"
            elif col == "Tipo de Acción":
                badge = badge_tipo_accion(row["Tipo de Acción"] if "Tipo de Acción" in row else "")
                table_html += f"<td style='padding:4px 2px;vertical-align:middle;'>{badge}</td>"
            elif col == "Ver más":
                # Si tiene OM asociada, mostrar botón para expandir acciones
                tiene_om = row["Ver más"] if "Ver más" in row else 0
                om_id = row["OM"] if "OM" in row else ""
                if tiene_om == 1 and om_id:
                    btn = f"<button class='om-icon-btn' onclick=\"window.location.search='?ver_mas={om_id}'\">📋</button>"
                    table_html += f"<td style='text-align:center;'>{btn}</td>"
                else:
                    table_html += "<td></td>"
            else:
                table_html += f"<td style='padding:4px 2px;vertical-align:middle;'>{val}</td>"
        table_html += "</tr>"
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

    oms_con_om = df_tabla[df_tabla["tiene_om"] == 1][["Id", "identificador"]].dropna()
    if not oms_con_om.empty:
        st.markdown("### Ver detalle de OM")
        cols = st.columns(3)
        col_idx = 0
        for idx, row in oms_con_om.iterrows():
            id_om = str(row.get("identificador", ""))
            with cols[col_idx % 3]:
                if st.checkbox(f"OM {id_om}", key=f"chk_{id_om}"):
                    plan_df = _cargar_plan_accion_para_om(id_om)
                    with st.expander(f"Detalle OM {id_om}", expanded=True):
                        if plan_df is not None and not plan_df.empty:
                            st.table(plan_df)
                        else:
                            st.write("Sin actividades.")
            col_idx += 1

    st.markdown("---")

    opciones = df_tabla.apply(_build_option_label, axis=1).tolist()
    indicador_seleccionado = st.selectbox("Seleccionar indicador", opciones, index=0)
    selected_id = indicador_seleccionado.split(" - ")[0] if indicador_seleccionado else ""

    if st.button("➕ Asociar nueva OM", use_container_width=True):
        st.session_state["om_modal_open"] = True
        st.session_state["om_modal_indicator"] = selected_id

    if st.session_state.get("om_modal_open"):
        indicador = st.session_state.get("om_modal_indicator", selected_id)
        row = df_tabla[df_tabla["Id"] == indicador]
        nombre_ind = row.iloc[0]["Indicador"] if not row.empty else ""
        ind_anio = str(row.iloc[0].get("Anio", "")) if not row.empty else ""
        ind_mes = row.iloc[0].get("Mes", "") if not row.empty else ""
        
        # Usar SIEMPRE el formato global pasando el dict completo de la fila
        meta_val = meta_his_signo(row.iloc[0].to_dict()) if not row.empty else ""
        ejec_val = ejecucion_his_signo(row.iloc[0].to_dict()) if not row.empty else ""
        cumpl_val = row.iloc[0].get("Cumplimiento_pct", "") if not row.empty else ""

        with st.expander("Asociar Oportunidad de mejora", expanded=True):
            st.markdown(f"**Indicador:** `{indicador}` - {nombre_ind}")
            st.markdown(f"**Período:** {ind_mes} {ind_anio}")
            
            if meta_val or ejec_val or cumpl_val:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Meta", meta_val if meta_val else "-")
                with c2:
                    st.metric("Ejecución", ejec_val if ejec_val else "-")
                with c3:
                    st.metric("Cumplimiento", f"{cumpl_val}%" if cumpl_val else "-")
            
            st.markdown("---")
            with st.form("om_modal_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    tipo_accion = st.selectbox("Tipo de Acción", ["OM Kawak", "Reto Plan Anual", "Proyecto Institucional", "Otro"], index=0)
                with col2:
                    placeholders = {
                        "OM Kawak": "N° OM Kawak",
                        "Reto Plan Anual": "Nombre del reto",
                        "Proyecto Institucional": "Nombre del proyecto",
                        "Otro": "Descripción de la acción",
                    }
                    numero_om = st.text_input("Identificador", placeholder=placeholders.get(tipo_accion, ""))
                
                observacion = st.text_area("Observación", placeholder="Describe la situación o justificación para la acción.")
                
                submitted = st.form_submit_button("💾 Guardar Oportunidad de Mejora", use_container_width=True)

        if submitted:
                    payload = {
                        "id_indicador": str(indicador),
                        "nombre_indicador": str(nombre_ind),
                        "proceso": str(row.iloc[0].get("Proceso", "")) if not row.empty else "",
                        "periodo": str(ind_mes),
                        "anio": int(ind_anio) if ind_anio.isdigit() else int(date.today().year),
                        "tiene_om": 1,
                        "tipo_accion": tipo_accion,
                        "numero_om": str(numero_om).strip(),
                        "comentario": str(observacion).strip(),
}
                    if guardar_registro_om(payload):
                        st.success(f"✅ Oportunidad de mejora guardada para indicador {indicador}")

if st.session_state.get("om_popup_open"):
        om_id = str(st.session_state.get("om_popup_id", ""))
        plan_df = _cargar_plan_accion_para_om(om_id)
        # Usar expander para ventana emergente
        with st.expander(f"Plan de Acción - OM {om_id}", expanded=True):
            st.subheader(f"Plan de Acción para OM {om_id}")
            if plan_df is not None and not plan_df.empty:
                st.table(plan_df)
            else:
                st.write("No hay actividades para mostrar.")
            if st.button("Cerrar", key=f'cerrar_popup_{om_id}'):
                st.session_state["om_popup_open"] = False
                st.rerun()
