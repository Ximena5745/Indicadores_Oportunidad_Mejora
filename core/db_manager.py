"""
core/db_manager.py — Persistencia dual SQLite (local) / PostgreSQL (Supabase).

Prioridad de detección de DATABASE_URL:
  1. st.secrets["DATABASE_URL"]  → Streamlit Cloud
  2. Variable de entorno DATABASE_URL → .env local / Render
  3. Sin URL → SQLite local en data/db/registros_om.db
"""
import os
import re
import sqlite3
import datetime
import socket
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "registros_om.db"


def _safe_st_secrets_get(key: str, default: str = "") -> str:
    """Lee un secret de Streamlit si está disponible, sin romper en ejecución no-Streamlit."""
    try:
        import streamlit as st
        return str(st.secrets.get(key, default)).strip()
    except Exception:
        return default


def _get_database_url() -> str:
    """Lee DATABASE_URL desde st.secrets o variable de entorno."""
    db_url = _safe_st_secrets_get("DATABASE_URL")
    if db_url:
        return _sanitize_postgres_dsn(db_url)
    return _sanitize_postgres_dsn(os.getenv("DATABASE_URL", "").strip())


def _sanitize_postgres_dsn(dsn: str) -> str:
    """Elimina parámetros de query no soportados por psycopg2 en URIs PostgreSQL."""
    raw = str(dsn or "").strip()
    if not raw or not raw.startswith("postgresql://"):
        return raw

    parsed = urlparse(raw)
    unsupported = {"pgbouncer"}
    cleaned_qs = [(k, v) for (k, v) in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in unsupported]
    new_query = urlencode(cleaned_qs, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def _extract_supabase_project_ref(supabase_url: str) -> str:
    """Extrae el project_ref desde https://<project_ref>.supabase.co."""
    if not supabase_url:
        return ""
    raw = str(supabase_url).strip().replace("https://", "").replace("http://", "")
    return raw.split(".")[0] if raw else ""


def _get_postgres_connect_kwargs() -> Optional[Dict[str, Any]]:
    """Construye kwargs de conexión a Postgres para Supabase.

    Prioridad:
      1) DATABASE_URL
      2) SUPABASE_POOLER_URL
      3) SUPABASE_URL + SUPABASE_DB_PASSWORD (+ overrides de host/puerto/usuario/db)
    """
    db_url = _get_database_url()
    if db_url:
        return {"dsn": db_url}

    pooler_url = _safe_st_secrets_get("SUPABASE_POOLER_URL") or os.getenv("SUPABASE_POOLER_URL", "").strip()
    if pooler_url:
        return {"dsn": _sanitize_postgres_dsn(pooler_url)}

    supabase_url = _safe_st_secrets_get("SUPABASE_URL") or os.getenv("SUPABASE_URL", "").strip()
    supabase_db_password = _safe_st_secrets_get("SUPABASE_DB_PASSWORD") or os.getenv("SUPABASE_DB_PASSWORD", "").strip()
    supabase_db_host = _safe_st_secrets_get("SUPABASE_DB_HOST") or os.getenv("SUPABASE_DB_HOST", "").strip()
    supabase_db_port = _safe_st_secrets_get("SUPABASE_DB_PORT") or os.getenv("SUPABASE_DB_PORT", "").strip()
    supabase_db_user = _safe_st_secrets_get("SUPABASE_DB_USER") or os.getenv("SUPABASE_DB_USER", "").strip()
    supabase_db_name = _safe_st_secrets_get("SUPABASE_DB_NAME") or os.getenv("SUPABASE_DB_NAME", "").strip()

    project_ref = _extract_supabase_project_ref(supabase_url)
    if project_ref and supabase_db_password:
        host = supabase_db_host or f"db.{project_ref}.supabase.co"
        port = int(supabase_db_port) if supabase_db_port.isdigit() else 5432
        user = supabase_db_user or "postgres"
        dbname = supabase_db_name or "postgres"
        return {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "password": supabase_db_password,
            "sslmode": "require",
        }

    return None


def _connect_postgres():
    import psycopg2

    kwargs = _get_postgres_connect_kwargs()
    if not kwargs:
        raise ValueError(
            "No hay credenciales de PostgreSQL configuradas. Usa DATABASE_URL o SUPABASE_URL + SUPABASE_DB_PASSWORD."
        )
    try:
        return psycopg2.connect(**kwargs)
    except Exception as exc:
        msg = str(exc)
        # Entornos sin salida IPv6 pueden fallar con hostnames que resuelven primero AAAA.
        if "Cannot assign requested address" in msg or "Network is unreachable" in msg:
            # Si hay pooler configurado, priorizarlo como fallback incluso cuando DATABASE_URL sea directa.
            pooler_url = _safe_st_secrets_get("SUPABASE_POOLER_URL") or os.getenv("SUPABASE_POOLER_URL", "").strip()
            if pooler_url:
                try:
                    return psycopg2.connect(dsn=pooler_url)
                except Exception:
                    pass
            retry_kwargs = _build_ipv4_retry_connect_kwargs(kwargs)
            if retry_kwargs:
                return psycopg2.connect(**retry_kwargs)
        raise


def _mes_numero_a_nombre(numero: int) -> str:
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    return meses[numero - 1] if 1 <= numero <= 12 else str(numero)


def _normalize_mes_nombre(mes: Any) -> str:
    texto = str(mes or "").strip()
    if not texto:
        return ""
    texto_lower = texto.lower()
    meses_map = {
        "ene": "Enero", "ene.": "Enero", "enero": "Enero",
        "feb": "Febrero", "feb.": "Febrero", "febrero": "Febrero",
        "mar": "Marzo", "mar.": "Marzo", "marzo": "Marzo",
        "abr": "Abril", "abr.": "Abril", "abril": "Abril",
        "may": "Mayo", "mayo": "Mayo",
        "jun": "Junio", "jun.": "Junio", "junio": "Junio",
        "jul": "Julio", "jul.": "Julio", "julio": "Julio",
        "ago": "Agosto", "ago.": "Agosto", "agosto": "Agosto",
        "sep": "Septiembre", "sep.": "Septiembre", "sept": "Septiembre",
        "sept.": "Septiembre", "septiembre": "Septiembre",
        "oct": "Octubre", "oct.": "Octubre", "octubre": "Octubre",
        "nov": "Noviembre", "nov.": "Noviembre", "noviembre": "Noviembre",
        "dic": "Diciembre", "dic.": "Diciembre", "diciembre": "Diciembre",
    }
    return meses_map.get(texto_lower, texto.capitalize())


def _normalize_om_periodo_anio(periodo: Any, anio: Any) -> tuple[str, int]:
    periodo_str = str(periodo or "").strip()
    anio_int = 0
    if isinstance(anio, int):
        anio_int = anio
    else:
        anio_text = str(anio or "").strip()
        if anio_text.isdigit():
            anio_int = int(anio_text)

    if not periodo_str:
        return "", anio_int

    match = re.match(r"^(\d{4})[-/](\d{1,2})$", periodo_str)
    if match:
        anio_int = int(match.group(1))
        return _mes_numero_a_nombre(int(match.group(2))), anio_int

    if periodo_str.isdigit():
        numero = int(periodo_str)
        if 1 <= numero <= 12:
            return _mes_numero_a_nombre(numero), anio_int

    return _normalize_mes_nombre(periodo_str), anio_int


def _ensure_sqlite_unique_index(conn: sqlite3.Connection) -> None:
    """Crea un índice único local para que ON CONFLICT funcione con la clave esperada."""
    cur = conn.cursor()
    cur.execute("PRAGMA index_list('registros_om')")
    indexes = {row[1] for row in cur.fetchall() if row[2] == 1}
    if "idx_registros_om_id_indicador_periodo_anio_unique" not in indexes:
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_registros_om_id_indicador_periodo_anio_unique "
            "ON registros_om (id_indicador, periodo, anio)"
        )
        conn.commit()


def _ensure_postgres_unique_constraint(cur) -> None:
    """Crea la constraint única en Postgres para que ON CONFLICT ON CONSTRAINT funcione."""
    cur.execute("""
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'registros_om_unique_key'
          AND conrelid = 'public.registros_om'::regclass
    """)
    if cur.fetchone() is not None:
        return

    # Si existe un índice con ese nombre pero no es constraint, elimínalo antes de crearla.
    cur.execute("""
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'registros_om_unique_key'
          AND c.relkind = 'i'
          AND n.nspname = 'public'
    """)
    if cur.fetchone() is not None:
        cur.execute("DROP INDEX IF EXISTS public.registros_om_unique_key")

    cur.execute(
        "ALTER TABLE public.registros_om ADD CONSTRAINT registros_om_unique_key UNIQUE (id_indicador, periodo, anio)"
    )


def _build_ipv4_retry_connect_kwargs(kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Crea kwargs de reintento forzando hostaddr IPv4 cuando sea posible."""
    if "hostaddr" in kwargs:
        return None

    host = kwargs.get("host")
    port = kwargs.get("port", 5432)

    if not host and "dsn" in kwargs:
        parsed = urlparse(str(kwargs.get("dsn", "")))
        host = parsed.hostname
        port = parsed.port or 5432

    if not host:
        return None

    try:
        ipv4_infos = socket.getaddrinfo(str(host), int(port), socket.AF_INET, socket.SOCK_STREAM)
        if not ipv4_infos:
            return None
        ipv4_addr = ipv4_infos[0][4][0]
    except Exception:
        return None

    retry_kwargs = dict(kwargs)
    retry_kwargs["hostaddr"] = ipv4_addr
    return retry_kwargs


def _use_pg() -> bool:
    return _get_postgres_connect_kwargs() is not None


def _notify_streamlit(level: str, message: str) -> None:
    """Publica mensajes en Streamlit si existe contexto UI."""
    try:
        import streamlit as st
        fn = getattr(st, level, None)
        if callable(fn):
            fn(message)
    except Exception:
        pass


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
            tiene_om          INTEGER DEFAULT 0,
            tipo_accion       TEXT DEFAULT 'OM Kawak',
            numero_om         TEXT,
            comentario        TEXT,
            registrado_por    TEXT DEFAULT '',
            fecha_registro    TEXT,
            UNIQUE(id_indicador, periodo, anio)
        )
    """)
    conn.commit()
    _ensure_sqlite_unique_index(conn)
    conn.close()


def _init_postgres():
    conn = _connect_postgres()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS registros_om (
            id                SERIAL PRIMARY KEY,
            id_indicador      TEXT NOT NULL,
            nombre_indicador  TEXT,
            proceso           TEXT,
            periodo           TEXT,
            anio              INTEGER,
            tiene_om          INTEGER DEFAULT 0,
            tipo_accion       TEXT DEFAULT 'OM Kawak',
            numero_om         TEXT,
            comentario        TEXT,
            registrado_por    TEXT DEFAULT '',
            fecha_registro    TEXT,
            UNIQUE(id_indicador, periodo, anio)
        )
    """)
    conn.commit()
    _ensure_postgres_unique_constraint(cur)
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
        _notify_streamlit("warning", f"No se pudo inicializar la base de datos: {e}")


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
    
    periodo, anio = _normalize_om_periodo_anio(datos.get("periodo", ""), datos.get("anio", 0))
    datos = {
        "id_indicador":     str(datos.get("id_indicador", "")),
        "nombre_indicador": str(datos.get("nombre_indicador", "")),
        "proceso":          str(datos.get("proceso", "")),
        "periodo":          str(periodo),
        "anio":             int(anio),
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
        _notify_streamlit("error", f"Error al guardar: {e}")
        return False


def _upsert_sqlite(d: dict) -> bool:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO registros_om
            (id_indicador, nombre_indicador, proceso, periodo, anio,
             tiene_om, tipo_accion, numero_om, comentario, registrado_por, fecha_registro)
        VALUES
            (:id_indicador, :nombre_indicador, :proceso, :periodo, :anio,
             :tiene_om, :tipo_accion, :numero_om, :comentario, :registrado_por, :fecha_registro)
        ON CONFLICT(id_indicador, periodo, anio) DO UPDATE SET
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
    conn = _connect_postgres()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO registros_om
            (id_indicador, nombre_indicador, proceso, periodo, anio,
             tiene_om, tipo_accion, numero_om, comentario, registrado_por, fecha_registro)
        VALUES
            (%(id_indicador)s, %(nombre_indicador)s, %(proceso)s, %(periodo)s,
             %(anio)s, %(tiene_om)s, %(tipo_accion)s, %(numero_om)s, %(comentario)s,
             %(registrado_por)s, %(fecha_registro)s)
        ON CONFLICT ON CONSTRAINT registros_om_unique_key DO UPDATE SET
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

def leer_registros_om(anio: int = None, periodo: str = None):
    """Retorna lista de dicts con los registros guardados."""
    try:
        if _use_pg():
            return _leer_postgres(anio, periodo)
        else:
            return _leer_sqlite(anio, periodo)
    except Exception as e:
        _notify_streamlit("error", f"Error al leer registros: {e}")
        return []


def _leer_sqlite(anio, periodo):
    if not DB_PATH.exists():
        return []
    periodo_norm = ""
    if periodo:
        periodo_norm, _ = _normalize_om_periodo_anio(periodo, anio or 0)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if anio and periodo_norm:
        rows = conn.execute(
            "SELECT * FROM registros_om WHERE anio = ? AND periodo = ? ORDER BY fecha_registro DESC",
            (anio, periodo_norm),
        ).fetchall()
    elif anio:
        rows = conn.execute(
            "SELECT * FROM registros_om WHERE anio = ? ORDER BY fecha_registro DESC",
            (anio,),
        ).fetchall()
    elif periodo_norm:
        rows = conn.execute(
            "SELECT * FROM registros_om WHERE periodo = ? ORDER BY fecha_registro DESC",
            (periodo_norm,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM registros_om ORDER BY fecha_registro DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _leer_postgres(anio, periodo):
    import psycopg2.extras
    conn = _connect_postgres()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    periodo_norm = ""
    if periodo:
        periodo_norm, _ = _normalize_om_periodo_anio(periodo, anio or 0)

    if anio and periodo_norm:
        cur.execute(
            "SELECT * FROM registros_om WHERE anio = %(anio)s AND periodo = %(periodo)s ORDER BY fecha_registro DESC",
            {"anio": anio, "periodo": periodo_norm},
        )
    elif anio:
        cur.execute(
            "SELECT * FROM registros_om WHERE anio = %(anio)s ORDER BY fecha_registro DESC",
            {"anio": anio},
        )
    elif periodo_norm:
        cur.execute(
            "SELECT * FROM registros_om WHERE periodo = %(periodo)s ORDER BY fecha_registro DESC",
            {"periodo": periodo_norm},
        )
    else:
        cur.execute("SELECT * FROM registros_om ORDER BY fecha_registro DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def registros_om_como_dict(anio: int = None, periodo: str = None) -> dict:
    """
    Retorna {id_indicador: {"tiene_om": bool, "tipo_accion": str, "numero_om": str, "periodo": str, "comentario": str}}
    Útil para cruzar con tabla de indicadores en otros módulos.
    Si un indicador tiene múltiples registros (distintos períodos), conserva el más reciente.
    """
    registros = leer_registros_om(anio=anio, periodo=periodo)
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
            conn = _connect_postgres()
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
        _notify_streamlit("error", f"Error guardar_acciones_bulk: {e}")
        return False


def leer_acciones(limit: int = 1000) -> list:
    """Lee hasta `limit` filas de la tabla `acciones` y retorna lista de dicts."""
    try:
        if _use_pg():
            import psycopg2
            import psycopg2.extras
            conn = _connect_postgres()
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
        _notify_streamlit("error", f"Error leer_acciones: {e}")
        return []


def borrar_acciones_por_marker(col: str, value: str) -> bool:
    """Borra filas de la tabla `acciones` donde `col` == `value`.

    Retorna True si la operación se ejecutó sin excepciones.
    """
    try:
        if _use_pg():
            conn = _connect_postgres()
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
        _notify_streamlit("error", f"Error borrar_acciones_por_marker: {e}")
        return False
