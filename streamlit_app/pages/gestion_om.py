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
    
    resultado = df_all.groupby("Id_OM")["Avance"].mean().to_dict()
    
    return {str(k).strip(): round(float(v), 1) for k, v in resultado.items()}


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

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        df = df.sort_values("Fecha").drop_duplicates(subset="Id", keep="last")
    else:
        df = df.drop_duplicates(subset="Id", keep="last")

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
            x_clean = str(x).strip()
            if not x_clean:
                return 0
            return avances_om.get(x_clean, avances_om.get(x_clean.upper(), avances_om.get(x_clean.lower(), 0)))
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

    cols = [
        "Id", "Indicador", "Proceso", "Subproceso", "Periodicidad", "Categoria",
        "tiene_om", "numero_om", "tipo_accion", "identificador", "avance_om", "tipo_mitigacion", "Cumplimiento_pct",
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
    cols_orden = ["Id", "Indicador", "Subproceso", "Periodicidad", "Meta", "Ejecucion", "Cumplimiento_pct", "Categoria", "tipo_accion", "identificador", "avance_om"]
    cols = [c for c in cols_orden if c in cols]
    renamed_cols = [
        c.replace("Cumplimiento_pct", "Cumplimiento")
         .replace("avance_om", "Avance OM")
         .replace("tiene_om", "Tiene OM")
         .replace("tipo_accion", "Tipo de Acción")
         .replace("identificador", "OM")
        for c in cols
    ]
    
    html = """
    <style>
    .om-table { border-collapse: collapse; width: 100%; font-size: 14px; }
    .om-table th { background: #1f2937; color: white; padding: 10px; text-align: left; }
    .om-table td { padding: 8px; border-bottom: 1px solid #e5e7eb; }
    .om-table tr:hover { background: #f3f4f6; }
    </style>
    <table class="om-table">
    <thead><tr>
    """
    for c in renamed_cols:
        html += f"<th>{c}</th>"
    html += "</tr></thead><tbody>"

    for _, row in df.iterrows():
        html += "<tr>"
        for col in cols:
            val = row.get(col)
            if col == "Cumplimiento_pct":
                icono = _icono_cumplimiento(val)
                html += f"<td>{icono} {val}%</td>"
            elif col == "tipo_accion":
                tipo_val = val if val and str(val).strip() and str(val).lower() != "nan" else "Sin acción"
                color = _color_tipo_accion_html(tipo_val)
                html += f"<td style='color: {color}; font-weight: bold;'>{tipo_val}</td>"
            elif col == "identificador":
                html += f"<td>{val}</td>"
            elif col == "avance_om":
                if val and val > 0:
                    color_bar = "#22C55E" if val >= 80 else "#F59E0B" if val >= 50 else "#EF4444"
                    html += f'''<td>
                        <div style="width: 100px; height: 8px; background: #E5E7EB; border-radius: 4px; overflow: hidden;">
                            <div style="width: {min(val, 100)}%; height: 100%; background: {color_bar};"></div>
                        </div>
                        <span style="font-size: 12px;">{val}%</span>
                    </td>'''
                elif val == 0:
                    html += f'''<td>
                        <div style="width: 100px; height: 8px; background: #E5E7EB; border-radius: 4px; overflow: hidden;">
                            <div style="width: 0%; height: 100%; background: #EF4444;"></div>
                        </div>
                        <span style="font-size: 12px;">0%</span>
                    </td>'''
                else:
                    html += f"<td>-</td>"
            elif col == "Meta":
                html += f"<td>{meta_his_signo(row)}</td>"
            elif col == "Ejecucion":
                html += f"<td>{ejecucion_his_signo(row)}</td>"
            elif col == "Categoria":
                html += f"<td>{val}</td>"
            elif col == "Id":
                html += f"<td><b>{val}</b></td>"
            else:
                html += f"<td>{val}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html


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

    if df_tabla.empty:
        st.info("No hay indicadores en Peligro con los filtros seleccionados.")
        return

    total_peligro = len(df_tabla)
    st.markdown(f"### 📊 Indicadores en Peligro: {total_peligro} ({mes_sel} {anio_sel})")
    st.markdown(_generar_tabla_html(df_tabla), unsafe_allow_html=True)

    opciones = df_tabla.apply(_build_option_label, axis=1).tolist()
    indicador_seleccionado = st.selectbox("Seleccionar indicador para nueva OM", opciones)
    selected_id = indicador_seleccionado.split(" - ")[0] if indicador_seleccionado else ""

    if st.button("Asociar nueva OM", use_container_width=True):
        if not selected_id:
            st.warning("Selecciona primero un indicador para asociar la OM.")
        else:
            st.session_state["om_modal_open"] = True
            st.session_state["om_modal_indicator"] = selected_id

    if st.session_state.get("om_modal_open"):
        indicador = st.session_state.get("om_modal_indicator", selected_id)
        row = df_tabla[df_tabla["Id"] == indicador]
        nombre_ind = row.iloc[0]["Indicador"] if not row.empty else ""
        ind_anio = str(row.iloc[0].get("Anio", "")) if not row.empty else ""
        ind_mes = row.iloc[0].get("Mes", "") if not row.empty else ""
        
        meta_val = meta_his_signo(row.iloc[0]) if not row.empty else ""
        ejec_val = ejecucion_his_signo(row.iloc[0]) if not row.empty else ""
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
                        st.session_state["om_modal_open"] = False
                        st.session_state["om_indicador_seleccionado"] = None
                        st.rerun()
                    else:
                        st.error("❌ No fue posible guardar la acción. Intenta nuevamente.")
