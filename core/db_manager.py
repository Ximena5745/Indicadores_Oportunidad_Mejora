"""
core/db_manager.py — Persistencia dual SQLite (local) / PostgreSQL (Supabase).

Prioridad de detección de DATABASE_URL:
  1. st.secrets["DATABASE_URL"]  → Streamlit Cloud
  2. Variable de entorno DATABASE_URL → .env local / Render
  3. Sin URL → SQLite local en data/db/registros_om.db
"""
import os
import sqlite3
import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "registros_om.db"


def _get_database_url() -> str:
    """Lee DATABASE_URL desde st.secrets (Streamlit Cloud) o env var.
    También puede usar SUPABASE_URL y SUPABASE_KEY de st.secrets."""
    try:
        import streamlit as st
        # Opción 1: DATABASE_URL completa
        if "DATABASE_URL" in st.secrets:
            return st.secrets.get("DATABASE_URL", "")
        
        # Opción 2: Construir desde SUPABASE_URL y SUPABASE_KEY
        supabase_url = st.secrets.get("SUPABASE_URL", "")
        supabase_key = st.secrets.get("SUPABASE_KEY", "")
        
        if supabase_url and supabase_key:
            # Extraer project_ref
            if "://" in supabase_url:
                project_ref = supabase_url.split("://")[1].split(".")[0]
            else:
                project_ref = supabase_url.split(".")[0]
            
            # Formato: postgresql://postgres:[password]@db.projectref.supabase.co:5432/postgres
            return f"postgresql://postgres:[{supabase_key}]@db.{project_ref}.supabase.co:5432/postgres"
    except Exception as e:
        pass
    
    # Opción 3: Variable de entorno
    return os.getenv("DATABASE_URL", "")


def _use_pg() -> bool:
    return bool(_get_database_url())


# ── Inicialización ────────────────────────────────────────────────────────────

def _init_sqlite():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS registros_om (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            id_indicador      TEXT NOT NULL,
            nombre_indicador  TEXT,
            proceso           TEXT,
            periodo           TEXT,
            anio              INTEGER,
            sede              TEXT DEFAULT '',
            tiene_om          INTEGER DEFAULT 0,
            tipo_accion       TEXT DEFAULT 'OM Kawak',
            numero_om         TEXT,
            comentario        TEXT,
            registrado_por    TEXT DEFAULT '',
            fecha_registro    TEXT,
            UNIQUE(id_indicador, periodo, anio, sede)
        )
    """)
    conn.commit()
    conn.close()


def _init_postgres():
    import psycopg2
    conn = psycopg2.connect(_get_database_url())
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS registros_om (
            id                SERIAL PRIMARY KEY,
            id_indicador      TEXT NOT NULL,
            nombre_indicador  TEXT,
            proceso           TEXT,
            periodo           TEXT,
            anio              INTEGER,
            sede              TEXT DEFAULT '',
            tiene_om          INTEGER DEFAULT 0,
            tipo_accion       TEXT DEFAULT 'OM Kawak',
            numero_om         TEXT,
            comentario        TEXT,
            registrado_por    TEXT DEFAULT '',
            fecha_registro    TEXT,
            UNIQUE(id_indicador, periodo, anio, sede)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def inicializar_db():
    try:
        if _use_pg():
            _init_postgres()
        else:
            _init_sqlite()
    except Exception as e:
        import streamlit as st
        st.warning(f"No se pudo inicializar la base de datos: {e}")


# ── Upsert ────────────────────────────────────────────────────────────────────

def guardar_registro_om(datos: dict) -> bool:
    """
    Upsert en registros_om.
    datos: dict con claves:
        id_indicador, nombre_indicador, proceso, periodo, anio,
        tiene_om (0/1), tipo_accion, numero_om, comentario
    Returns True si éxito.
    """
    inicializar_db()
    
    datos = {
        "id_indicador":     str(datos.get("id_indicador", "")),
        "nombre_indicador": str(datos.get("nombre_indicador", "")),
        "proceso":          str(datos.get("proceso", "")),
        "periodo":          str(datos.get("periodo", "")),
        "anio":             int(datos.get("anio", 0)),
        "sede":             "",
        "tiene_om":         int(datos.get("tiene_om", 0)),
        "tipo_accion":      str(datos.get("tipo_accion", "OM Kawak")),
        "numero_om":        str(datos.get("numero_om", "")),
        "comentario":       str(datos.get("comentario", "")),
        "registrado_por":   "",
        "fecha_registro":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        if _use_pg():
            return _upsert_postgres(datos)
        else:
            return _upsert_sqlite(datos)
    except Exception as e:
        import streamlit as st
        st.error(f"Error al guardar: {e}")
        return False


def _upsert_sqlite(d: dict) -> bool:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO registros_om
            (id_indicador, nombre_indicador, proceso, periodo, anio, sede,
             tiene_om, tipo_accion, numero_om, comentario, registrado_por, fecha_registro)
        VALUES
            (:id_indicador, :nombre_indicador, :proceso, :periodo, :anio, :sede,
             :tiene_om, :tipo_accion, :numero_om, :comentario, :registrado_por, :fecha_registro)
        ON CONFLICT(id_indicador, periodo, anio, sede) DO UPDATE SET
            nombre_indicador = excluded.nombre_indicador,
            proceso          = excluded.proceso,
            tiene_om         = excluded.tiene_om,
            tipo_accion      = excluded.tipo_accion,
            numero_om        = excluded.numero_om,
            comentario       = excluded.comentario,
            fecha_registro   = excluded.fecha_registro
    """, d)
    conn.commit()
    conn.close()
    return True


def _upsert_postgres(d: dict) -> bool:
    import psycopg2
    conn = psycopg2.connect(_get_database_url())
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO registros_om
            (id_indicador, nombre_indicador, proceso, periodo, anio, sede,
             tiene_om, tipo_accion, numero_om, comentario, registrado_por, fecha_registro)
        VALUES
            (%(id_indicador)s, %(nombre_indicador)s, %(proceso)s, %(periodo)s,
             %(anio)s, %(sede)s, %(tiene_om)s, %(tipo_accion)s, %(numero_om)s, %(comentario)s,
             %(registrado_por)s, %(fecha_registro)s)
        ON CONFLICT(id_indicador, periodo, anio, sede) DO UPDATE SET
            nombre_indicador = EXCLUDED.nombre_indicador,
            proceso          = EXCLUDED.proceso,
            tiene_om         = EXCLUDED.tiene_om,
            tipo_accion      = EXCLUDED.tipo_accion,
            numero_om        = EXCLUDED.numero_om,
            comentario       = EXCLUDED.comentario,
            fecha_registro   = EXCLUDED.fecha_registro
    """, d)
    conn.commit()
    cur.close()
    conn.close()
    return True


# ── Consulta ──────────────────────────────────────────────────────────────────

def leer_registros_om(anio: int = None):
    """Retorna lista de dicts con los registros guardados."""
    try:
        if _use_pg():
            return _leer_postgres(anio)
        else:
            return _leer_sqlite(anio)
    except Exception as e:
        import streamlit as st
        st.error(f"Error al leer registros: {e}")
        return []


def _leer_sqlite(anio):
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if anio:
        rows = conn.execute(
            "SELECT * FROM registros_om WHERE anio = ? ORDER BY fecha_registro DESC",
            (anio,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM registros_om ORDER BY fecha_registro DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _leer_postgres(anio):
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(_get_database_url())
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if anio:
        cur.execute(
            "SELECT * FROM registros_om WHERE anio = %(anio)s ORDER BY fecha_registro DESC",
            {"anio": anio},
        )
    else:
        cur.execute("SELECT * FROM registros_om ORDER BY fecha_registro DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def registros_om_como_dict(anio: int = None) -> dict:
    """
    Retorna {id_indicador: {"tiene_om": bool, "tipo_accion": str, "numero_om": str, "periodo": str, "comentario": str}}
    Útil para cruzar con tabla de indicadores en otros módulos.
    Si un indicador tiene múltiples registros (distintos períodos), conserva el más reciente.
    """
    registros = leer_registros_om(anio=anio)
    result = {}
    for r in registros:
        iid = r["id_indicador"]
        if iid not in result:  # leer_registros_om ordena DESC → primer registro = más reciente
            result[iid] = {
                "tiene_om":   bool(r.get("tiene_om", 0)),
                "tipo_accion": r.get("tipo_accion", "OM Kawak"),
                "numero_om":  r.get("numero_om", ""),
                "periodo":    r.get("periodo", ""),
                "comentario": r.get("comentario", ""),
                "anio":       r.get("anio", ""),
            }
    return result


# Inicializar al importar
inicializar_db()


def guardar_acciones_bulk(df) -> bool:
    """
    Guarda un DataFrame o lista de dicts de acciones en una tabla `acciones`.
    Esta función es deliberadamente tolerante: crea la tabla con columnas TEXT
    según los nombres de columnas del DataFrame y luego inserta filas.

    Retorna True si la operación parece exitosa.
    """
    if df is None:
        return False
    try:
        import pandas as pd
    except Exception:
        pd = None

    # Normalizar a DataFrame
    if pd is not None and not isinstance(df, pd.DataFrame):
        try:
            df = pd.DataFrame(df)
        except Exception:
            return False

    # Si no hay filas, salir
    if (hasattr(df, 'empty') and df.empty) or (not hasattr(df, 'shape') and len(df) == 0):
        return False

    cols = list(df.columns)
    try:
        if _use_pg():
            import psycopg2
            conn = psycopg2.connect(_get_database_url())
            cur = conn.cursor()
            # Crear tabla con columnas TEXT si no existe
            cols_defs = ", ".join([f'"{c}" TEXT' for c in cols])
            cur.execute(f'CREATE TABLE IF NOT EXISTS acciones (id SERIAL PRIMARY KEY, {cols_defs})')
            # Insertar filas
            for _, row in df.iterrows():
                vals = [None if (pd is not None and pd.isna(x)) else str(x) for x in row.tolist()]
                placeholders = ','.join(['%s'] * len(vals))
                cur.execute(f'INSERT INTO acciones ({", ".join([f"\"{c}\"" for c in cols])}) VALUES ({placeholders})', tuple(vals))
            conn.commit()
            cur.close()
            conn.close()
            return True
        else:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cols_defs = ", ".join([f'"{c}" TEXT' for c in cols])
            cur.execute(f'CREATE TABLE IF NOT EXISTS acciones (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols_defs})')
            insert_sql = f'INSERT INTO acciones ({", ".join([f"\"{c}\"" for c in cols])}) VALUES ({", ".join(["?" for _ in cols])})'
            for _, row in df.iterrows():
                vals = [None if (pd is not None and pd.isna(x)) else str(x) for x in row.tolist()]
                cur.execute(insert_sql, vals)
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        try:
            import streamlit as st
            st.error(f"Error guardar_acciones_bulk: {e}")
        except Exception:
            pass
        return False


def leer_acciones(limit: int = 1000) -> list:
    """Lee hasta `limit` filas de la tabla `acciones` y retorna lista de dicts."""
    try:
        if _use_pg():
            import psycopg2.extras
            conn = psycopg2.connect(_get_database_url())
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(f"SELECT * FROM acciones ORDER BY id DESC LIMIT {int(limit)}")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(r) for r in rows]
        else:
            if not DB_PATH.exists():
                return []
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM acciones ORDER BY id DESC LIMIT {int(limit)}")
            rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]
    except Exception as e:
        try:
            import streamlit as st
            st.error(f"Error leer_acciones: {e}")
        except Exception:
            pass
        return []


def borrar_acciones_por_marker(col: str, value: str) -> bool:
    """Borra filas de la tabla `acciones` donde `col` == `value`.

    Retorna True si la operación se ejecutó sin excepciones.
    """
    try:
        if _use_pg():
            import psycopg2
            conn = psycopg2.connect(_get_database_url())
            cur = conn.cursor()
            cur.execute(f"DELETE FROM acciones WHERE \"{col}\" = %s", (str(value),))
            conn.commit()
            cur.close()
            conn.close()
            return True
        else:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(f"DELETE FROM acciones WHERE \"{col}\" = ?", (str(value),))
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        try:
            import streamlit as st
            st.error(f"Error borrar_acciones_por_marker: {e}")
        except Exception:
            pass
        return False
