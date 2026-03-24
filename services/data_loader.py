"""
services/data_loader.py — Carga de datos desde xlsx con caché st.cache_data.

Fuente principal: data/output/Resultados Consolidados.xlsx (hoja Consolidado Semestral).
El Dataset_Unificado.xlsx NO es fuente oficial y NO debe usarse como origen de datos.

Regla de capas:
  - Lógica pura          → core/calculos.py
  - Configuración        → core/config.py
  - Carga con caché Streamlit → aquí (services/)
"""
import unicodedata
import streamlit as st
import pandas as pd
from pathlib import Path

from core.calculos import normalizar_cumplimiento, categorizar_cumplimiento, estado_tiempo_acciones
from core.config import DATA_RAW, DATA_OUTPUT

_RENAME = {
    "Año":           "Anio",
    "Ejecución":     "Ejecucion",
    "Clasificación": "Clasificacion",
    "Ejecución s":   "Ejecucion_s",
    "Meta s":        "Meta_Signo",
}


def _ascii_lower(s: str) -> str:
    return unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()


def _renombrar(df: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    mapping = {}
    for col in df.columns:
        for orig, dest in mapa.items():
            if _ascii_lower(col) == _ascii_lower(orig):
                mapping[col] = dest
                break
    return df.rename(columns=mapping)


def _id_a_str(x) -> str:
    if pd.isna(x):
        return ""
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x)


# ── Mapa subproceso → proceso padre (basado en Subproceso-Proceso-Area.xlsx) ─
# Hardcodeado como constante para evitar dependencias de lectura de archivos
# dentro de funciones cacheadas anidadas.
# Clave: _ascii_lower(subproceso)  Valor: proceso canonical (MAYÚSCULAS)
_MAPA_PROCESO_PADRE: dict[str, str] = {
    # DIRECCIONAMIENTO ESTRATÉGICO
    _ascii_lower("Gestion de Proyectos"):             "DIRECCIONAMIENTO ESTRAT\u00c9GICO",
    _ascii_lower("Planeacion Estrategica"):            "DIRECCIONAMIENTO ESTRAT\u00c9GICO",
    _ascii_lower("Desempeno Institucional"):           "DIRECCIONAMIENTO ESTRAT\u00c9GICO",
    _ascii_lower("Gerencia de Estrategia"):            "DIRECCIONAMIENTO ESTRAT\u00c9GICO",
    # PLANIFICACIÓN Y MEJORA DEL SISTEMA INTEGRADO
    _ascii_lower("Gestion de calidad"):                "PLANIFICACI\u00d3N Y MEJORA DEL SISTEMA INTEGRADO",
    _ascii_lower("Gestion de Calidad"):                "PLANIFICACI\u00d3N Y MEJORA DEL SISTEMA INTEGRADO",
    _ascii_lower("Planificacion POLISIGS"):            "PLANIFICACI\u00d3N Y MEJORA DEL SISTEMA INTEGRADO",
    # COMUNICACIÓN Y POSICIONAMIENTO ESTRATÉGICO
    _ascii_lower("Comunicaciones Externas"):           "COMUNICACI\u00d3N Y POSICIONAMIENTO ESTRAT\u00c9GICO",
    _ascii_lower("Comunicaciones Internas"):           "COMUNICACI\u00d3N Y POSICIONAMIENTO ESTRAT\u00c9GICO",
    _ascii_lower("Gestion de campanas integradas de marketing"):
                                                       "COMUNICACI\u00d3N Y POSICIONAMIENTO ESTRAT\u00c9GICO",
    # AUTOEVALUACIÓN Y AUTOREGULACIÓN
    _ascii_lower("Autoevaluacion de programas academicos"):
                                                       "AUTOEVALUACI\u00d3N Y AUTOREGULACI\u00d3N",
    _ascii_lower("Autoevaluacion institucional"):      "AUTOEVALUACI\u00d3N Y AUTOREGULACI\u00d3N",
    # GESTIÓN DE PORTAFOLIO INSTITUCIONAL
    _ascii_lower("Gestion, Evaluacion e Innovacion Curricular"):
                                                       "GESTI\u00d3N DE PORTAFOLIO INSTITUCIONAL",
    _ascii_lower("Creacion, modificacion y cierre de programas academicos"):
                                                       "GESTI\u00d3N DE PORTAFOLIO INSTITUCIONAL",
    _ascii_lower("Diseno de Contenido Virtual"):       "GESTI\u00d3N DE PORTAFOLIO INSTITUCIONAL",
    # DOCENCIA
    _ascii_lower("Gestion Docente"):                   "DOCENCIA",
    _ascii_lower("Gestion de Unidades Academicas"):    "DOCENCIA",
    _ascii_lower("Operaciones Academicas"):            "DOCENCIA",
    _ascii_lower("Operacion de Educacion no Formal"):  "DOCENCIA",
    _ascii_lower("Operaciones Academica pregrado y posgrado presencial."):
                                                       "DOCENCIA",
    _ascii_lower("Operaciones Academica pregrado y posgrado virtual"):
                                                       "DOCENCIA",
    _ascii_lower("Operacion de nuevos negocios y CI"): "DOCENCIA",
    # EXTENSIÓN
    _ascii_lower("Gestion de Graduados"):              "EXTENSI\u00d3N",
    _ascii_lower("Practicas"):                         "EXTENSI\u00d3N",
    _ascii_lower("Emprendimiento"):                    "EXTENSI\u00d3N",
    _ascii_lower("Gestion de la Responsabilidad Social"):
                                                       "EXTENSI\u00d3N",
    # INVESTIGACIÓN, INNOVACIÓN Y CREACIÓN
    _ascii_lower("Investigacion, desarrollo tecnologico, innovacion y creacion"):
                                                       "INVESTIGACI\u00d3N, INNOVACI\u00d3N Y CREACI\u00d3N",
    _ascii_lower("Investigacion, desarrollo tecnologico e innovacion"):
                                                       "INVESTIGACI\u00d3N, INNOVACI\u00d3N Y CREACI\u00d3N",
    _ascii_lower("Formacion para la investigacion, creacion e innovacion"):
                                                       "INVESTIGACI\u00d3N, INNOVACI\u00d3N Y CREACI\u00d3N",
    # RECURSOS ACADÉMICOS Y DE INVESTIGACIÓN
    _ascii_lower("Biblioteca Institucional"):          "RECURSOS ACAD\u00c9MICOS Y DE INVESTIGACI\u00d3N",
    _ascii_lower("Editorial y Publicaciones"):         "RECURSOS ACAD\u00c9MICOS Y DE INVESTIGACI\u00d3N",
    _ascii_lower("Centro de Medios Audiovisuales"):    "RECURSOS ACAD\u00c9MICOS Y DE INVESTIGACI\u00d3N",
    _ascii_lower("LEI"):                               "RECURSOS ACAD\u00c9MICOS Y DE INVESTIGACI\u00d3N",
    # MERCADEO, ADMISIONES Y MATRÍCULA
    _ascii_lower("Inscripcion, admision y matricula de estudiantes nuevos"):
                                                       "MERCADEO, ADMISIONES Y MATR\u00cdCULA",
    _ascii_lower("Mercadeo de programas academicos"):  "MERCADEO, ADMISIONES Y MATR\u00cdCULA",
    _ascii_lower("Mercadeo y venta de educacion para la vida"):
                                                       "MERCADEO, ADMISIONES Y MATR\u00cdCULA",
    # BIENESTAR INSTITUCIONAL
    _ascii_lower("Cultura y Deporte"):                 "BIENESTAR INSTITUCIONAL",
    _ascii_lower("Servicio de Salud"):                 "BIENESTAR INSTITUCIONAL",
    # SERVICIO Y PERMANENCIA
    _ascii_lower("Servicio"):                          "SERVICIO Y PERMANENCIA",
    _ascii_lower("Permanencia"):                       "SERVICIO Y PERMANENCIA",
    _ascii_lower("Registro y Control"):                "SERVICIO Y PERMANENCIA",
    _ascii_lower("Rematricula"):                       "SERVICIO Y PERMANENCIA",
    # GESTIÓN FINANCIERA
    _ascii_lower("Planeacion Financiera"):             "GESTI\u00d3N FINANCIERA",
    _ascii_lower("Contabilidad"):                      "GESTI\u00d3N FINANCIERA",
    _ascii_lower("Tesoreria"):                         "GESTI\u00d3N FINANCIERA",
    # INFRAESTRUCTURA Y SERVICIOS ADMINISTRATIVOS
    _ascii_lower("Gestion Infraestructura Fisica"):    "INFRAESTRUCTURA Y SERVICIOS ADMINISTRATIVOS",
    _ascii_lower("Administracion de Servicios Generales"):
                                                       "INFRAESTRUCTURA Y SERVICIOS ADMINISTRATIVOS",
}


def _cargar_mapa_proceso_padre() -> dict:
    """
    Retorna {ascii_lower(subproceso): proceso_canonical}.
    Usa el mapa hardcodeado como base y lo enriquece leyendo
    Subproceso-Proceso-Area.xlsx si está disponible.
    """
    mapa: dict[str, str] = dict(_MAPA_PROCESO_PADRE)
    path = DATA_RAW / "Subproceso-Proceso-Area.xlsx"
    if not path.exists():
        return mapa
    try:
        df = pd.read_excel(str(path), engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        col_sub = next((c for c in df.columns if "ubpro" in c), None)
        col_pro = next((c for c in df.columns
                        if "roceso" in c and "ubpro" not in c), None)
        if col_sub and col_pro:
            for _, r in df.iterrows():
                if pd.isna(r[col_sub]) or pd.isna(r[col_pro]):
                    continue
                pro = str(r[col_pro]).strip()
                sub = str(r[col_sub]).strip()
                if _ascii_lower(pro) in ("no aplica", ""):
                    continue
                key = _ascii_lower(sub)
                if key not in mapa:
                    mapa[key] = pro
    except Exception as exc:
        print(f"[data_loader] _cargar_mapa_proceso_padre: {exc}")
    return mapa


@st.cache_data(ttl=300, show_spinner="Cargando datos principales...")
def cargar_dataset() -> pd.DataFrame:
    """
    Carga el dataset principal desde Resultados Consolidados.xlsx (fuente oficial).
    Enriquece con Clasificacion (Catálogo) y Subproceso/Linea (CMI).
    El Sentido se toma SIEMPRE del Consolidado (calculado desde Kawak/API).
    """
    path = DATA_OUTPUT / "Resultados Consolidados.xlsx"
    if not path.exists():
        st.error(f"Archivo no encontrado: {path}")
        return pd.DataFrame()

    df = pd.read_excel(path, sheet_name="Consolidado Semestral", engine="openpyxl")
    df = _renombrar(df, _RENAME)

    # Id como string limpio (antes de los joins)
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_a_str)

    # ── Enriquecer con Clasificacion desde Catalogo Indicadores ──────────────
    if "Clasificacion" not in df.columns:
        try:
            df_cat = pd.read_excel(path, sheet_name="Catalogo Indicadores", engine="openpyxl")
            df_cat["Id"] = df_cat["Id"].apply(_id_a_str)
            cols_cat = ["Id"] + [c for c in ["Clasificacion"] if c in df_cat.columns]
            if len(cols_cat) > 1:
                df = df.merge(df_cat[cols_cat].drop_duplicates("Id"), on="Id", how="left")
        except Exception:
            pass

    # ── Enriquecer con Subproceso y Linea desde Indicadores por CMI ──────────
    # (NO se toma Sentido del CMI — puede estar desactualizado respecto a Kawak)
    try:
        df_cmi = pd.read_excel(
            DATA_RAW / "Indicadores por CMI.xlsx",
            sheet_name="Worksheet", engine="openpyxl",
        )
        df_cmi = _renombrar(df_cmi, _RENAME)
        df_cmi["Id"] = df_cmi["Id"].apply(_id_a_str)
        cols_cmi = ["Id"] + [c for c in ["Subproceso", "Linea", "Objetivo"]
                             if c in df_cmi.columns]
        if len(cols_cmi) > 1:
            df = df.merge(df_cmi[cols_cmi].drop_duplicates("Id"), on="Id", how="left")
    except Exception:
        pass

    # ── Enriquecer con Proceso padre desde Subproceso-Proceso-Area.xlsx ─────
    if "Proceso" in df.columns:
        _mapa_proc = _cargar_mapa_proceso_padre()
        df["ProcesoPadre"] = df["Proceso"].apply(
            lambda x: _mapa_proc.get(_ascii_lower(str(x)), str(x).strip())
        )

    # ── Reconstruir columnas derivadas de fórmulas Excel ─────────────────────
    # El xlsx tiene fórmulas (=YEAR(F), =IFERROR(...), etc.) que openpyxl guarda
    # sin evaluar → pandas las lee como NaN. Se recalculan aquí desde columnas base.

    # Año, Mes, Periodo desde Fecha
    if "Fecha" in df.columns:
        _fecha = pd.to_datetime(df["Fecha"], errors="coerce")
        _MESES_ES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
                     7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
        if "Año" in df.columns:
            df["Año"] = df["Año"].fillna(_fecha.dt.year)
        if "Mes" in df.columns:
            df["Mes"] = df["Mes"].where(df["Mes"].notna() & (df["Mes"] != ""),
                                        _fecha.dt.month.map(_MESES_ES))
        if "Periodo" in df.columns:
            _periodo_calc = _fecha.dt.year.astype("Int64").astype(str) + "-" + \
                            _fecha.dt.month.apply(lambda m: "1" if m <= 6 else "2")
            df["Periodo"] = df["Periodo"].where(
                df["Periodo"].notna() & (df["Periodo"] != ""), _periodo_calc)

    # Cumplimiento desde Meta / Ejecucion / Sentido
    if "Cumplimiento" in df.columns and "Meta" in df.columns and "Ejecucion" in df.columns:
        from core.config import IDS_PLAN_ANUAL
        mask_nan = df["Cumplimiento"].isna()
        if mask_nan.any():
            def _recalc_cumpl(row):
                try:
                    m = float(row["Meta"])
                    e = float(row["Ejecucion"])
                except (TypeError, ValueError):
                    return float("nan")
                if m == 0 or pd.isna(m) or pd.isna(e):
                    return float("nan")
                sentido = str(row.get("Sentido", "Positivo"))
                raw = (e / m) if sentido == "Positivo" else (m / e if e != 0 else float("nan"))
                if pd.isna(raw):
                    return float("nan")
                # Plan Anual: tope 1.0;  resto: tope 1.3
                tope = 1.0 if str(row.get("Id", "")).strip() in IDS_PLAN_ANUAL else 1.3
                return min(max(raw, 0.0), tope)
            df.loc[mask_nan, "Cumplimiento"] = df[mask_nan].apply(_recalc_cumpl, axis=1)

    # ── Normalizar cumplimiento ───────────────────────────────────────────────
    if "Cumplimiento" in df.columns:
        df["Cumplimiento_norm"] = df["Cumplimiento"].apply(normalizar_cumplimiento)
    else:
        df["Cumplimiento_norm"] = float("nan")

    # ── Categorizar ───────────────────────────────────────────────────────────
    df["Categoria"] = df.apply(
        lambda r: categorizar_cumplimiento(
            r["Cumplimiento_norm"],
            r.get("Sentido", "Positivo"),
            id_indicador=r.get("Id"),
        ),
        axis=1,
    )

    # ── Fechas ────────────────────────────────────────────────────────────────
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    # ── Año como Int64 ────────────────────────────────────────────────────────
    # La columna Año puede contener fórmulas Excel (ej. "=YEAR(F2)") que
    # to_numeric convierte a NaN. En ese caso se deriva desde Fecha.
    if "Anio" in df.columns:
        df["Anio"] = pd.to_numeric(df["Anio"], errors="coerce")
        if "Fecha" in df.columns and df["Anio"].isna().any():
            df["Anio"] = df["Anio"].fillna(df["Fecha"].dt.year)
        df["Anio"] = df["Anio"].astype("Int64")

    return df


@st.cache_data(ttl=300, show_spinner="Cargando acciones de mejora...")
def cargar_acciones_mejora() -> pd.DataFrame:
    path = DATA_RAW / "acciones_mejora.xlsx"
    if not path.exists():
        st.error(f"Archivo no encontrado: {path}")
        return pd.DataFrame()

    df = pd.read_excel(path, sheet_name="Acciones", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    for col in ["FECHA_IDENTIFICACION", "FECHA_ESTIMADA_CIERRE", "FECHA_CIERRE", "FECHA_CREACION"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["DIAS_VENCIDA", "MESES_SIN_AVANCE", "AVANCE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = estado_tiempo_acciones(df)
    return df


@st.cache_data(ttl=300, show_spinner="Cargando ficha técnica...")
def cargar_ficha_tecnica() -> pd.DataFrame:
    path = DATA_RAW / "Ficha_Tecnica.xlsx"
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_excel(path, sheet_name="Hoja1", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    if "Id Ind" in df.columns:
        df["Id"] = df["Id Ind"].apply(_id_a_str)
    return df


def _leer_excel(path: Path, header: int = 0) -> pd.DataFrame:
    """Lee .xlsx (openpyxl) o .xls (xlrd) con preferencia por .xlsx."""
    xlsx = path.with_suffix(".xlsx")
    if path.suffix.lower() == ".xls" and xlsx.exists():
        path = xlsx
    ext = path.suffix.lower()
    if ext == ".xlsx":
        return pd.read_excel(str(path), header=header, engine="openpyxl")
    return pd.read_excel(str(path), header=header, engine="xlrd")


@st.cache_data(ttl=300, show_spinner="Cargando Oportunidades de Mejora...")
def cargar_om() -> pd.DataFrame:
    """Carga OM.xlsx (preferido) o OM.xls. Encabezados en fila 8 (header=7)."""
    xlsx = DATA_RAW / "OM.xlsx"
    xls  = DATA_RAW / "OM.xls"

    if xlsx.exists():
        path, header = xlsx, 7
    elif xls.exists():
        path, header = xls, 7
    else:
        return pd.DataFrame()

    try:
        engine = "openpyxl" if path.suffix.lower() == ".xlsx" else "xlrd"
        df = pd.read_excel(str(path), header=header, engine=engine)
    except Exception as e:
        st.error(f"Error leyendo {path.name}: {e}")
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").reset_index(drop=True)

    if "Id" in df.columns:
        df = df[df["Id"].notna() & (df["Id"].astype(str).str.strip() != "")].reset_index(drop=True)
        df["Id"] = df["Id"].apply(_id_a_str)

    for col in ["Fecha de identificación", "Fecha de creación",
                "Fecha estimada de cierre", "Fecha real de cierre"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    col_av = next((c for c in df.columns if "avance" in c.lower()), None)
    if col_av:
        df[col_av] = pd.to_numeric(df[col_av], errors="coerce")
        mask = df[col_av].notna()
        if mask.any() and df.loc[mask, col_av].max() <= 1.5:
            df[col_av] = df[col_av] * 100

    return df


@st.cache_data(ttl=300, show_spinner="Cargando Plan de Acción...")
def cargar_plan_accion() -> pd.DataFrame:
    """Consolida todos los archivos de data/raw/Plan de accion/. Prioriza .xlsx sobre .xls."""
    folder = DATA_RAW / "Plan de accion"
    if not folder.exists():
        return pd.DataFrame()

    xlsx_stems = {p.stem for p in folder.glob("*.xlsx")}
    archivos = []
    for p in sorted(folder.iterdir()):
        ext = p.suffix.lower()
        if ext == ".xlsx":
            archivos.append(p)
        elif ext == ".xls" and p.stem not in xlsx_stems:
            archivos.append(p)

    frames = []
    for p in archivos:
        try:
            engine = "openpyxl" if p.suffix.lower() == ".xlsx" else "xlrd"
            df = pd.read_excel(str(p), engine=engine)
            df.columns = [str(c).strip() for c in df.columns]
            df = df.dropna(how="all").reset_index(drop=True)
            frames.append(df)
        except Exception as e:
            print(f"[data_loader] No se pudo leer {p.name}: {e}")

    if not frames:
        return pd.DataFrame()

    df_all = pd.concat(frames, ignore_index=True)

    for col in df_all.columns:
        if any(kw in col.lower() for kw in ["fecha", "ejecuci", "seguimiento", "evaluaci"]):
            try:
                df_all[col] = pd.to_datetime(df_all[col], errors="coerce")
            except Exception:
                pass

    col_av = next((c for c in df_all.columns if "avance" in c.lower()), None)
    if col_av:
        df_all[col_av] = pd.to_numeric(df_all[col_av], errors="coerce")
        mask = df_all[col_av].notna()
        if mask.any() and df_all.loc[mask, col_av].max() <= 1.5:
            df_all[col_av] = df_all[col_av] * 100

    for col in df_all.columns:
        if "id oportunidad" in col.lower():
            df_all[col] = df_all[col].apply(_id_a_str)

    return df_all


@st.cache_data(ttl=300, show_spinner=False)
def cargar_analisis_usuarios() -> pd.DataFrame:
    """
    Carga la hoja 'Desglose Analisis' de Resultados Consolidados.xlsx.
    Retorna columnas: Id (str), fecha, analisis_fecha, analisis_autor, analisis_texto.
    """
    path = DATA_OUTPUT / "Resultados Consolidados.xlsx"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(path, sheet_name="Desglose Analisis", engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        if "Id" in df.columns:
            df["Id"] = df["Id"].apply(_id_a_str)
        for col in ("analisis_fecha", "fecha"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def df_indicadores_unicos(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna un registro único por Id (el más reciente por Fecha)."""
    if df.empty or "Id" not in df.columns:
        return df
    if "Revisar" in df.columns:
        revisar = pd.to_numeric(df["Revisar"], errors="coerce").fillna(0)
        return df[revisar == 1].drop_duplicates(subset="Id", keep="first").reset_index(drop=True)
    col_fecha = "Fecha" if "Fecha" in df.columns else None
    if col_fecha:
        return df.sort_values(col_fecha).drop_duplicates(subset="Id", keep="last").reset_index(drop=True)
    return df.drop_duplicates(subset="Id", keep="last").reset_index(drop=True)


def construir_opciones_indicadores(df: pd.DataFrame) -> dict:
    """Retorna dict {label: id_str} con etiquetas 'Id — Nombre' únicas."""
    if df.empty or "Id" not in df.columns:
        return {}
    unicos = df_indicadores_unicos(df)
    sub = unicos[["Id", "Indicador"]].dropna(subset=["Id"])
    sub = sub[sub["Id"] != ""]
    opciones = {}
    for _, row in sub.iterrows():
        label = f"{row['Id']} — {row.get('Indicador', '')}"
        opciones[label] = row["Id"]
    return dict(sorted(opciones.items()))
