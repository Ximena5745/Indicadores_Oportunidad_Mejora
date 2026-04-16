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
    
    def _parse_avance(v):
        if v is None:
            return pd.NA
        s = str(v).strip()
        if not s or s.lower() in {"nan", "none", "-"}:
            return pd.NA

        has_percent = "%" in s
        s = s.replace("%", "").replace(" ", "")
        s = s.replace(".", "") if ("," in s and "." in s and s.rfind(",") > s.rfind(".")) else s
        s = s.replace(",", ".")
        n = pd.to_numeric(s, errors="coerce")
        if pd.isna(n):
            return pd.NA

        # Si viene en escala 0..1 sin símbolo %, interpretarlo como fracción y convertir a 0..100
        if not has_percent and abs(n) <= 1.5:
            n = n * 100
        return float(n)

    dfs = []
    for f in base_path.glob("*.xlsx"):
        try:
            df = pd.read_excel(f, dtype=str, na_filter=False)
            cols = df.columns.tolist()
            
            avance_col = next((c for c in cols if "Avance" in c and "%" in c), None)
            if not avance_col:
                avance_col = next((c for c in cols if "Avance" in c), None)
            
            # Buscar columna "Id Oportunidad de mejora" (no "Estado...")
            id_om_col = next((c for c in cols if "Id Oportunidad de mejora" in c), None)
            if not id_om_col:
                id_om_col = next((c for c in cols if c.startswith("Id ") and "Oportunidad" in c), None)
            id_accion_col = next((c for c in cols if str(c).strip().lower() in {"id acción", "id accion"}), None)
            
            if id_om_col and avance_col:
                subset_cols = [id_om_col, avance_col]
                if id_accion_col:
                    subset_cols.append(id_accion_col)
                df_subset = df[subset_cols].copy()
                if id_accion_col:
                    df_subset.columns = ["Id_OM", "Avance", "Id_Accion"]
                else:
                    df_subset.columns = ["Id_OM", "Avance"]
                dfs.append(df_subset)
        except Exception as e:
            continue
    
    if not dfs:
        return {}
    
    df_all = pd.concat(dfs, ignore_index=True)
    df_all["Avance"] = df_all["Avance"].apply(_parse_avance)
    df_all["Id_OM"] = df_all["Id_OM"].astype(str).str.strip()
    
    df_all = df_all.dropna(subset=["Id_OM", "Avance"])
    df_all = df_all[df_all["Id_OM"] != ""]
    df_all = df_all[df_all["Id_OM"].str.lower() != "nan"]

    # Evitar sobre-representar avance por actividades repetidas.
    # Importante: no colapsar filas cuando Id_Accion está vacío, porque eso sesga el promedio.
    if "Id_Accion" in df_all.columns:
        df_all["Id_Accion"] = df_all["Id_Accion"].astype(str).str.strip()
        con_id = df_all[df_all["Id_Accion"] != ""].copy()
        sin_id = df_all[df_all["Id_Accion"] == ""].copy()
        if not con_id.empty:
            con_id = con_id.drop_duplicates(subset=["Id_OM", "Id_Accion"], keep="last")
        df_all = pd.concat([con_id, sin_id], ignore_index=True)
    
    if df_all.empty:
        return {}
    
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

    # Generar llaves robustas para matchear OM (ej: "440", "440.0", "OM 440").
    import re
    salida = {}
    for k, v in resultado.items():
        try:
            avance = round(float(v), 1)
        except Exception:
            continue

        key_raw = str(k).strip()
        if not key_raw:
            continue
        salida[key_raw] = avance

        key_norm = _id_str(key_raw)
        if key_norm:
            salida[key_norm] = avance

        nums = re.findall(r"\d+", key_raw)
        if nums:
            salida[nums[0]] = avance

    return salida


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
            id_accion = str(row.get("Id Acción", "")).strip()
            if not id_accion:
                id_accion = str(row.get("Id Accion", "")).strip()
            accion = str(row.get("Acción", "")).strip()
            if not accion:
                accion = str(row.get("Accion", "")).strip()
            if not accion:
                accion = str(row.get("Descripci\u00f3n", "")).strip() or str(row.get("Descripcion", "")).strip()
            resp = str(row.get("Responsable de ejecuci\u00f3n", "")) or str(row.get("Responsable", "")) or str(row.get("Fuente de Identificaci\u00f3n", ""))
            avance = row.get("Avance (%)", row.get("Avance", ""))
            if avance is None or (isinstance(avance, float) and pd.isna(avance)):
                avance = ""
            estado_plan = str(row.get("Estado (Plan de Acci\u00f3n)", "")) or str(row.get("Estado (Plan Acción)", ""))
            estado_om = str(row.get("Estado (Oportunidad de mejora)", "")) or str(row.get("Estado de Oportunidad", ""))
            rows.append({
                "Id Acción": id_accion,
                "Acción": accion,
                "Responsable de ejecución": resp,
                "Avance (%)": avance,
                "Estado (Plan de Acción)": estado_plan,
                "Estado (Oportunidad de mejora)": estado_om,
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _normalizar_campos_plan_accion(plan_df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza columnas del plan de acción y deja solo campos requeridos."""
    if plan_df is None or plan_df.empty:
        return pd.DataFrame()

    campos = [
        "Id Acción",
        "Acción",
        "Responsable de ejecución",
        "Avance (%)",
        "Estado (Plan de Acción)",
        "Estado (Oportunidad de mejora)",
    ]

    df_show = plan_df.copy()
    renames = {}
    for c in df_show.columns:
        c_norm = c.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        if c_norm == "id accion":
            renames[c] = "Id Acción"
        elif c_norm.startswith("accion"):
            renames[c] = "Acción"
        elif "responsable" in c_norm:
            renames[c] = "Responsable de ejecución"
        elif "avance" in c_norm:
            renames[c] = "Avance (%)"
        elif "plan de accion" in c_norm:
            renames[c] = "Estado (Plan de Acción)"
        elif "oportunidad" in c_norm:
            renames[c] = "Estado (Oportunidad de mejora)"

    df_show = df_show.rename(columns=renames)
    df_show = df_show[[c for c in campos if c in df_show.columns]].copy()

    # Deduplicar por Id Acción (si no existe, usar Acción como respaldo)
    if "Id Acción" in df_show.columns:
        df_show["Id Acción"] = df_show["Id Acción"].astype(str).str.strip()
        df_show = df_show[df_show["Id Acción"] != ""]
        df_show = df_show.drop_duplicates(subset=["Id Acción"], keep="first")
    elif "Acción" in df_show.columns:
        df_show["Acción"] = df_show["Acción"].astype(str).str.strip()
        df_show = df_show[df_show["Acción"] != ""]
        df_show = df_show.drop_duplicates(subset=["Acción"], keep="first")

    # Formatear avance como porcentaje; si viene en escala 0-1, convertir a 0-100
    if "Avance (%)" in df_show.columns:
        avance_num = pd.to_numeric(df_show["Avance (%)"], errors="coerce")
        avance_num = avance_num.apply(lambda v: v * 100 if pd.notna(v) and abs(v) <= 1.5 else v)
        df_show["Avance (%)"] = avance_num.apply(lambda v: "-" if pd.isna(v) else f"{v:.1f}%")

    return df_show.reset_index(drop=True)


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
    # Normalizar identificador OM para facilitar cruce con avances_om
    out["identificador"] = out["numero_om"].fillna("").apply(
        lambda x: _extraer_tipo_y_identificador(str(x))[1] if str(x).strip() else ""
    )
    out["identificador"] = out["identificador"].apply(_id_str)
    
    if avances_om and isinstance(avances_om, dict) and len(avances_om) > 0:
        def buscar_avance(x):
            import re
            x_clean = str(x).strip()
            if not x_clean:
                return 0
            # Prefijo exacto
            if x_clean in avances_om:
                return avances_om[x_clean]
            # Forma normalizada numérica (ej. '440.0' -> '440')
            x_norm = _id_str(x_clean)
            if x_norm in avances_om:
                return avances_om[x_norm]
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

    # Usar la función existente para construir la matriz, incluyendo avances OM
    return _matriz_mitigacion_peligro(df_filtrado, df_reg, df_acc, avances_om)


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


def barra_avance_om(pct):
    if pd.isna(pct) or pct == 0:
        color = "#F3F4F6"
        icon = "⚪"
        return f'''<div class="om-bar-bg"><div class="om-bar-fill" style="width:0;background:{color}"></div><span style="position:absolute;left:8px;top:0;font-size:13px;font-weight:600;color:#888;">{icon} -</span></div>'''

    color = "#F87171"
    icon = "🔴"
    if pct >= 105:
        color = "#2563EB"
        icon = "🔵"
    elif pct >= 100:
        color = "#22C55E"
        icon = "🟢"
    elif pct >= 80:
        color = "#FACC15"
        icon = "🟡"

    return f'''<div class="om-bar-bg"><div class="om-bar-fill" style="width:{min(100,pct)}%;background:{color}"></div><span style="position:absolute;left:8px;top:0;font-size:13px;font-weight:600;color:#222;">{icon} {pct:.1f}%</span></div>'''


def badge_tipo_accion(tipo):
    clases = {
        "OM Kawak": "om-badge om-kawak",
        "Reto Plan Anual": "om-badge om-reto",
        "Proyecto Institucional": "om-badge om-proy",
        "Otro": "om-badge om-otro",
        "Sin acción": "om-badge om-sin",
    }
    return f'<span class="{clases.get(tipo, "om-badge om-otro")}">{tipo}</span>'


def _icono_cumplimiento(cumpl_val) -> str:
    n = pd.to_numeric(cumpl_val, errors="coerce")
    if pd.isna(n):
        return "⚪"
    if n >= 105:
        return "🔵"
    if n >= 100:
        return "🟢"
    if n >= 80:
        return "🟡"
    return "🔴"


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

    # --- Tabla principal con encabezado visual e icono de expansión OM ---
    from streamlit_app.utils.formatting import formatear_meta_ejecucion_df

    df_tabla_fmt = formatear_meta_ejecucion_df(df_tabla.copy(), meta_col="Meta", ejec_col="Ejecucion")
    rename_map = {
        "Cumplimiento_pct": "Cumplimiento",
        "avance_om": "Avance OM",
        "tiene_om": "Ver más",
        "tipo_accion": "Tipo de Acción",
        "identificador": "OM",
    }
    df_tabla_fmt = df_tabla_fmt.rename(columns=rename_map)

    cols_orden = [
        "Id", "Indicador", "Subproceso", "Periodicidad", "Meta", "Ejecucion",
        "Cumplimiento", "Categoria", "Tipo de Acción", "OM", "Avance OM"
    ]
    cols_tabla = [c for c in cols_orden if c in df_tabla_fmt.columns]
    df_view = df_tabla_fmt[cols_tabla + (["Ver más"] if "Ver más" in df_tabla_fmt.columns else [])].copy()

    if "Cumplimiento" in df_view.columns:
        df_view["Cumplimiento"] = pd.to_numeric(df_view["Cumplimiento"], errors="coerce").round(1)

    if "Avance OM" in df_view.columns:
        df_view["Avance OM"] = pd.to_numeric(df_view["Avance OM"], errors="coerce")

    if "OM" in df_view.columns:
        df_view["OM"] = df_view["OM"].apply(lambda v: "" if pd.isna(v) else str(v))

    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"] { gap: 0 !important; }
        div[data-testid="stColumn"] { padding-left: 0 !important; padding-right: 0 !important; }
        div[data-testid="stButton"] {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 0 !important;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        div[data-testid="stButton"] > button {
            margin: 0 !important;
        }
        div[data-testid="stButton"] > button[kind="secondary"],
        div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] {
            min-height: 0 !important;
            height: 18px !important;
            width: 18px !important;
            padding: 0 !important;
            margin: 0 auto !important;
            border-radius: 4px !important;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        div[data-testid="stButton"] > button[kind="secondary"]:hover,
        div[data-testid="stButton"] > button[data-testid="baseButton-secondary"]:hover {
            background: #e2e8f0 !important;
        }
        div[data-testid="stButton"] > button[kind="secondary"] p,
        div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] p {
            font-size: 0.85rem;
            line-height: 1;
        }
        /* Mantener botones primarios con estilo normal */
        div[data-testid="stButton"] > button[kind="primary"],
        div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
            width: auto !important;
            height: auto !important;
            min-height: 2.25rem !important;
            padding: 0.25rem 0.9rem !important;
            border-radius: 0.5rem !important;
        }
        .om-head {
            background:#1e293b;
            color:#fff;
            font-weight:700;
            padding:6px 4px;
            border-right:1px solid #334155;
            border-radius:0;
            white-space:nowrap;
            line-height:1.1;
            font-size:14px;
        }
        .om-cell {
            padding:6px 4px;
            border-bottom:1px solid #e2e8f0;
            line-height:1.15;
        }
        .om-cell-alt {
            padding:6px 4px;
            border-bottom:1px solid #e2e8f0;
            background:#f8fafc;
            line-height:1.15;
        }
        .om-center { text-align:center; }
        .om-avance-wrap {
            min-width: 86px;
            max-width: 110px;
            margin: 0 auto;
        }
        .om-badge {
            display:inline-block;
            padding:2px 8px;
            border-radius:8px;
            font-size:12px;
            font-weight:700;
            color:#fff;
            white-space:nowrap;
        }
        .om-kawak { background:#2563EB; }
        .om-reto { background:#D97706; }
        .om-proy { background:#0EA5A4; }
        .om-otro { background:#6B7280; }
        .om-sin { background:#94A3B8; color:#0F172A; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Encabezado visual
    encabezados = cols_orden + ["Ver más"]
    anchos = [0.5, 4.2, 2.8, 1.15, 0.9, 0.95, 1.25, 1.0, 1.4, 0.75, 1.05, 0.45]
    head_cols = st.columns(anchos, gap="small")
    for i, h in enumerate(encabezados):
        with head_cols[i]:
            st.markdown(f"<div class='om-head'>{h}</div>", unsafe_allow_html=True)

    # Filas con estilo + expansión por icono
    for ridx, row in df_view.iterrows():
        row_cols = st.columns(anchos, gap="small")
        cell_class = "om-cell" if ridx % 2 == 0 else "om-cell-alt"

        cumple_num = pd.to_numeric(row.get("Cumplimiento"), errors="coerce")
        cumple_txt = barra_avance_om(float(cumple_num)) if pd.notna(cumple_num) else barra_avance_om(0)

        tipo_raw = row.get("Tipo de Acción", "Sin acción")
        if pd.isna(tipo_raw) or str(tipo_raw).strip().lower() in {"", "nan", "none"}:
            tipo_raw = "Sin acción"
        tipo_badge = badge_tipo_accion(str(tipo_raw))

        avance_num = pd.to_numeric(row.get("Avance OM"), errors="coerce")
        if pd.notna(avance_num) and abs(avance_num) <= 1.5:
            avance_num = avance_num * 100
        avance_txt = "<div class='om-avance-wrap'>" + (barra_avance_om(float(avance_num)) if pd.notna(avance_num) else barra_avance_om(0)) + "</div>"

        valores = [
            str(row.get("Id", "")),
            str(row.get("Indicador", "")),
            str(row.get("Subproceso", "")),
            str(row.get("Periodicidad", "")),
            str(row.get("Meta", "")),
            str(row.get("Ejecucion", "")),
            cumple_txt,
            str(row.get("Categoria", "")),
            tipo_badge,
            "" if pd.isna(row.get("OM")) or str(row.get("OM")).lower() == "nan" else str(row.get("OM")),
            avance_txt,
        ]

        for i, val in enumerate(valores):
            with row_cols[i]:
                extra = " om-center" if i in [4, 5, 9, 10] else ""
                st.markdown(f"<div class='{cell_class}{extra}'>{val}</div>", unsafe_allow_html=True)

        with row_cols[11]:
            om_id = "" if pd.isna(row.get("OM")) else str(row.get("OM")).strip()
            tiene_om = str(row.get("Ver más", "0")) in {"1", "True", "true"}
            if tiene_om and om_id and om_id.lower() != "nan":
                if st.button("📋", key=f"btn_om_{ridx}_{om_id}", help=f"Ver acciones OM {om_id}", type="secondary"):
                    active = st.session_state.get("om_expanded_row")
                    st.session_state["om_expanded_row"] = None if active == (ridx, om_id) else (ridx, om_id)
            else:
                st.markdown(f"<div class='{cell_class}'></div>", unsafe_allow_html=True)

        if st.session_state.get("om_expanded_row") == (ridx, om_id):
            plan_df = _cargar_plan_accion_para_om(om_id)
            df_show = _normalizar_campos_plan_accion(plan_df)
            if not df_show.empty:
                st.markdown(f"##### Acciones asociadas a OM {om_id}")
                st.dataframe(df_show, use_container_width=True, hide_index=True)
            else:
                st.info(f"OM {om_id} sin acciones asociadas.")

    st.markdown("---")

    opciones = df_tabla.apply(_build_option_label, axis=1).tolist()
    indicador_seleccionado = st.selectbox("Seleccionar indicador", opciones, index=0)
    selected_id = indicador_seleccionado.split(" - ")[0] if indicador_seleccionado else ""

    if st.button("➕ Asociar nueva OM", use_container_width=True, type="primary"):
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
        df_show = _normalizar_campos_plan_accion(plan_df)
        # Mantener compatibilidad con query param existente
        with st.expander(f"Plan de Acción - OM {om_id}", expanded=True):
            st.subheader(f"Plan de Acción para OM {om_id}")
            if not df_show.empty:
                st.dataframe(df_show, use_container_width=True, hide_index=True)
            else:
                st.write("No hay actividades para mostrar.")
            if st.button("Cerrar", key=f"cerrar_popup_{om_id}"):
                st.session_state["om_popup_open"] = False
                st.rerun()
