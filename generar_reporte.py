#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
"""
generar_reporte.py
==================
Procesa 'lmi_reporte.xls' (descargado de plataforma externa) y genera
'Seguimiento_Reporte.xlsx' con:

  1. Hoja "Seguimiento"  -> copia completa + columna "Revisar"
  2. Hojas por periodicidad (Mensual, Bimestral, Trimestral, Semestral, Anual)
     - Columnas Periodo X renombradas a fechas reales (dd/mm/aaaa)
     - Columna "Reportado"          (período más reciente con/sin dato)
     - Columna "Estado del indicador" (últimos 2 períodos)

CONFIGURACIÓN
─────────────
  RUTA_ORIGEN      : ruta al archivo fuente .xls
  RUTA_SALIDA      : ruta de salida .xlsx
  COLUMNA_REVISAR  : columna usada para detectar inicio de nuevo indicador
  FECHA_REFERENCIA : fecha de corte; el Periodo 1 se asigna al período más
                     reciente ≤ esta fecha según cada periodicidad.
"""

import os
from datetime import date, timedelta

import xlrd
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RUTA_ORIGEN = os.path.join(BASE_DIR, "data", "raw", "lmi_reporte.xls")
RUTA_SALIDA = os.path.join(BASE_DIR, "data", "raw", "Seguimiento_Reporte.xlsx")

# Columna cuyo cambio entre filas consecutivas marca un nuevo indicador único.
# Cambiar si la columna clave de la fuente tuviera otro nombre.
COLUMNA_REVISAR = "Id"

# Fecha de corte del reporte: el Periodo 1 corresponde al período cerrado
# más reciente ≤ esta fecha según la periodicidad del indicador.
# Ajustar antes de ejecutar si el reporte es de un período diferente.
FECHA_REFERENCIA = date(2025, 12, 31)

# ── Paleta de colores ──────────────────────────────────────────────────────────
C_HEADER    = "1F4E79"   # Azul institucional oscuro
C_SI        = "C6EFCE"   # Verde claro -> Sí / Reportado
C_NO        = "FFCCCC"   # Rojo claro  -> No
C_PENDIENTE = "FFEB9C"   # Amarillo    -> Pendiente de reporte
C_REVISAR1  = "DDEEFF"   # Azul suave  -> Revisar = 1 (nuevo indicador)

# ── Fechas de fin de período ───────────────────────────────────────────────────

def _ultimo_dia(year: int, month: int) -> date:
    """Retorna el último día calendario del mes indicado."""
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def _retroceder(year: int, mes_actual: int, meses_ciclo: list) -> tuple:
    """
    Dado un mes dentro de meses_ciclo, retorna el mes anterior del ciclo
    (y el año ajustado si se pasa al año anterior).
    """
    idx = meses_ciclo.index(mes_actual)
    if idx == 0:
        return year - 1, meses_ciclo[-1]
    return year, meses_ciclo[idx - 1]


def get_period_dates(periodicidad: str, n: int = 13) -> list:
    """
    Genera `n` fechas de fin de período hacia atrás desde FECHA_REFERENCIA.

    Reglas por periodicidad:
      Mensual    -> fin de cada mes calendario
      Bimestral  -> fin de: Feb, Abr, Jun, Ago, Oct, Dic
      Trimestral -> fin de: Mar, Jun, Sep, Dic
      Semestral  -> fin de: Jun, Dic
      Anual      -> 31 de diciembre de cada año

    Returns: list[date]  [0] = más reciente … [n-1] = más antigua
    """
    ref = FECHA_REFERENCIA
    dates = []

    if periodicidad == "Mensual":
        y, m = ref.year, ref.month
        for _ in range(n):
            dates.append(_ultimo_dia(y, m))
            m -= 1
            if m == 0:
                m, y = 12, y - 1

    elif periodicidad == "Bimestral":
        ciclo = [2, 4, 6, 8, 10, 12]
        y, m = ref.year, ref.month
        previos = [x for x in ciclo if x <= m]
        cur = max(previos) if previos else 12
        if not previos:
            y -= 1
        for _ in range(n):
            dates.append(_ultimo_dia(y, cur))
            y, cur = _retroceder(y, cur, ciclo)

    elif periodicidad == "Trimestral":
        ciclo = [3, 6, 9, 12]
        y, m = ref.year, ref.month
        previos = [x for x in ciclo if x <= m]
        cur = max(previos) if previos else 12
        if not previos:
            y -= 1
        for _ in range(n):
            dates.append(_ultimo_dia(y, cur))
            y, cur = _retroceder(y, cur, ciclo)

    elif periodicidad == "Semestral":
        ciclo = [6, 12]
        y, m = ref.year, ref.month
        previos = [x for x in ciclo if x <= m]
        cur = max(previos) if previos else 12
        if not previos:
            y -= 1
        for _ in range(n):
            dates.append(_ultimo_dia(y, cur))
            y, cur = _retroceder(y, cur, ciclo)

    elif periodicidad == "Anual":
        y = ref.year
        for i in range(n):
            dates.append(date(y - i, 12, 31))

    else:
        # Periodicidad desconocida: retorna etiquetas genéricas como None
        dates = [None] * n

    return dates


# ── Leer archivo fuente ────────────────────────────────────────────────────────

def leer_xls(ruta: str) -> pd.DataFrame:
    """
    Lee lmi_reporte.xls usando xlrd con ignore_workbook_corruption=True
    (la corrupción OLE2 menor es habitual en reportes exportados desde
    plataformas web; el contenido de datos está íntegro).
    """
    wb = xlrd.open_workbook(
        ruta,
        ignore_workbook_corruption=True,
        encoding_override="cp1252",
    )
    sh = wb.sheets()[0]
    headers = sh.row_values(0)
    filas = [sh.row_values(r) for r in range(1, sh.nrows)]
    return pd.DataFrame(filas, columns=headers)


# ── Lógica de columnas "Revisar", "Reportado", "Estado" ───────────────────────

def agregar_revisar(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Agrega columna 'Revisar' al final del DataFrame.

    Regla:
      - Fila 1 siempre -> 1
      - Fila i: 0 si df[col][i] == df[col][i-1], de lo contrario 1
    """
    df = df.copy()
    valores = df[col].tolist()
    revisar = [1] + [
        0 if valores[i] == valores[i - 1] else 1
        for i in range(1, len(valores))
    ]
    df["Revisar"] = revisar
    return df


def _tiene_dato(v) -> bool:
    """Retorna True si el valor representa un dato real (no vacío ni guión)."""
    if v is None:
        return False
    s = str(v).strip()
    return s not in ("", "-", "nan", "NaN", "None")


def agregar_columnas_seguimiento(df: pd.DataFrame, col_p1: str, col_p2: str) -> pd.DataFrame:
    """
    Agrega las columnas 'Reportado' y 'Estado del indicador'.

    Reportado:
      - "Sí"  si el período más reciente (col_p1) tiene dato
      - "No"  si está vacío o es '-'

    Estado del indicador (últimos 2 períodos):
      - "Reportado"           si ambos col_p1 y col_p2 tienen dato
      - "Pendiente de reporte" si alguno está vacío / sin dato
    """
    df = df.copy()

    df["Reportado"] = df[col_p1].apply(
        lambda v: "Sí" if _tiene_dato(v) else "No"
    )

    def _estado(row):
        p1_ok = _tiene_dato(row[col_p1])
        p2_ok = _tiene_dato(row[col_p2]) if col_p2 else True
        return "Reportado" if (p1_ok and p2_ok) else "Pendiente de reporte"

    df["Estado del indicador"] = df.apply(_estado, axis=1)
    return df


# ── Escritura con openpyxl ─────────────────────────────────────────────────────

def _estilo_header(cell):
    cell.font = Font(bold=True, color="FFFFFF", size=10)
    cell.fill = PatternFill("solid", fgColor=C_HEADER)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    borde = Side(style="thin", color="FFFFFF")
    cell.border = Border(left=borde, right=borde, bottom=borde)


def _ancho_columna(ws, col_idx: int, max_ancho: int = 40):
    letra = get_column_letter(col_idx)
    ws.column_dimensions[letra].width = min(max_ancho, max(
        ws.column_dimensions[letra].width, 8
    ))


def escribir_hoja(ws, df: pd.DataFrame, mapa_fechas: dict = None):
    """
    Escribe el DataFrame en la hoja de openpyxl.

    mapa_fechas: {nombre_columna_original: date} para renombrar encabezados
                 de período como 'dd/mm/aaaa'.
    """
    mapa_fechas = mapa_fechas or {}

    # ── Encabezados
    for ci, col in enumerate(df.columns, 1):
        val = col
        if col in mapa_fechas and mapa_fechas[col] is not None:
            val = mapa_fechas[col].strftime("%d/%m/%Y")
        cell = ws.cell(row=1, column=ci, value=val)
        _estilo_header(cell)
        # Ancho inicial basado en el nombre del encabezado
        ws.column_dimensions[get_column_letter(ci)].width = max(len(str(val)) + 2, 10)

    # ── Datos fila a fila
    for ri, row in enumerate(df.itertuples(index=False), 2):
        for ci, raw_val in enumerate(row, 1):
            col_name = df.columns[ci - 1]

            # Limpiar floats enteros en Id
            if col_name == "Id" and isinstance(raw_val, float):
                val = int(raw_val) if raw_val == int(raw_val) else raw_val
            # Guiones -> None para que la celda quede vacía
            elif str(raw_val).strip() == "-":
                val = None
            else:
                val = raw_val

            cell = ws.cell(row=ri, column=ci, value=val)
            cell.alignment = Alignment(horizontal="center", vertical="center")

            # Colores semáforo
            if col_name == "Reportado":
                if val == "Sí":
                    cell.fill = PatternFill("solid", fgColor=C_SI)
                elif val == "No":
                    cell.fill = PatternFill("solid", fgColor=C_NO)

            elif col_name == "Estado del indicador":
                if val == "Reportado":
                    cell.fill = PatternFill("solid", fgColor=C_SI)
                elif val == "Pendiente de reporte":
                    cell.fill = PatternFill("solid", fgColor=C_PENDIENTE)

            elif col_name == "Revisar" and val == 1:
                cell.fill = PatternFill("solid", fgColor=C_REVISAR1)

            # Ampliar columna si el contenido es mayor al ancho actual
            ancho_actual = ws.column_dimensions[get_column_letter(ci)].width
            contenido_ancho = len(str(val)) + 2 if val is not None else 0
            ws.column_dimensions[get_column_letter(ci)].width = min(
                40, max(ancho_actual, contenido_ancho)
            )

    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions


# ── Resumen por periodicidad ───────────────────────────────────────────────────

def crear_hoja_resumen(wb, resumen_data: list):
    """
    Crea una hoja 'Resumen' con estadísticas por periodicidad.
    resumen_data: lista de dict con claves: Periodicidad, Total, Reportados, Pendientes
    """
    ws = wb.create_sheet(title="Resumen", index=0)
    headers = ["Periodicidad", "Total indicadores", "Reportados (período actual)",
               "Pendientes de reporte", "% Reporte"]
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=ci, value=h)
        _estilo_header(cell)
        ws.column_dimensions[get_column_letter(ci)].width = max(len(h) + 4, 18)

    for ri, row in enumerate(resumen_data, 2):
        ws.cell(row=ri, column=1, value=row["Periodicidad"])
        ws.cell(row=ri, column=2, value=row["Total"])
        ws.cell(row=ri, column=3, value=row["Reportados"])
        ws.cell(row=ri, column=4, value=row["Pendientes"])
        pct = round(row["Reportados"] / row["Total"] * 100, 1) if row["Total"] else 0
        pct_cell = ws.cell(row=ri, column=5, value=f"{pct}%")
        # Color semáforo sobre %
        if pct >= 80:
            pct_cell.fill = PatternFill("solid", fgColor=C_SI)
        elif pct >= 50:
            pct_cell.fill = PatternFill("solid", fgColor=C_PENDIENTE)
        else:
            pct_cell.fill = PatternFill("solid", fgColor=C_NO)


# ── Flujo principal ────────────────────────────────────────────────────────────

def main():
    sep = "=" * 62
    print(sep)
    print("  generar_reporte.py -> Seguimiento_Reporte.xlsx")
    print(sep)

    # ── 1. Leer fuente ────────────────────────────────────────────────────────
    print(f"\n[1] Leyendo fuente: {RUTA_ORIGEN}")
    if not os.path.exists(RUTA_ORIGEN):
        sys.exit(f"    ERROR: No se encontró {RUTA_ORIGEN}")

    df = leer_xls(RUTA_ORIGEN)
    print(f"    OK -> {len(df)} filas  |  {len(df.columns)} columnas")

    # ── 2. Columna Revisar ───────────────────────────────────────────────────
    if COLUMNA_REVISAR not in df.columns:
        sys.exit(f"    ERROR: Columna '{COLUMNA_REVISAR}' no encontrada en la fuente.")

    print(f"\n[2] Columna 'Revisar' (basada en '{COLUMNA_REVISAR}')...")
    df = agregar_revisar(df, COLUMNA_REVISAR)
    indicadores_unicos = df["Revisar"].sum()
    print(f"    {indicadores_unicos} indicadores únicos detectados.")

    # ── 3. Identificar columnas de período ───────────────────────────────────
    periodo_cols = [c for c in df.columns if str(c).startswith("Periodo ")]
    n_periodos = len(periodo_cols)
    print(f"\n[3] Columnas de período: {n_periodos}  ({periodo_cols[0]} … {periodo_cols[-1]})")

    # ── 4. Crear workbook ────────────────────────────────────────────────────
    wb = openpyxl.Workbook()
    wb.remove(wb.active)   # quitar hoja vacía por defecto

    # ── 5. Hoja "Seguimiento" (copia completa) ───────────────────────────────
    print(f"\n[4] Hoja 'Seguimiento' -> {len(df)} filas...")
    ws_seg = wb.create_sheet(title="Seguimiento")
    escribir_hoja(ws_seg, df)
    print("    OK")

    # ── 6. Hojas por periodicidad ────────────────────────────────────────────
    periodicidades = [p for p in df["Periodicidad"].dropna().unique() if p]
    print(f"\n[5] Periodicidades: {periodicidades}")
    resumen_data = []

    for perio in periodicidades:
        df_p = df[df["Periodicidad"] == perio].copy().reset_index(drop=True)
        total = len(df_p)
        print(f"\n    ── {perio} ({total} filas)")

        # Fechas para cada columna de período
        fechas = get_period_dates(perio, n_periodos)
        mapa = {col: f for col, f in zip(periodo_cols, fechas)}
        if fechas[0]:
            print(f"       Periodo 1 -> {fechas[0].strftime('%d/%m/%Y')}  "
                  f"| Periodo {n_periodos} -> {fechas[-1].strftime('%d/%m/%Y')}")

        # Columnas de seguimiento
        col_p1 = periodo_cols[0]
        col_p2 = periodo_cols[1] if n_periodos >= 2 else None
        df_p = agregar_columnas_seguimiento(df_p, col_p1, col_p2)

        reportados = (df_p["Reportado"] == "Sí").sum()
        pendientes = (df_p["Estado del indicador"] == "Pendiente de reporte").sum()
        print(f"       Reportados (período más reciente) : {reportados}/{total}")
        print(f"       Pendientes de reporte (2 períodos): {pendientes}/{total}")

        # Escribir hoja
        ws = wb.create_sheet(title=perio[:31])
        escribir_hoja(ws, df_p, mapa)

        resumen_data.append({
            "Periodicidad": perio,
            "Total": total,
            "Reportados": int(reportados),
            "Pendientes": int(pendientes),
        })

    # ── 7. Hoja Resumen ──────────────────────────────────────────────────────
    print("\n[6] Hoja 'Resumen'...")
    crear_hoja_resumen(wb, resumen_data)
    print("    OK")

    # ── 8. Guardar ───────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(RUTA_SALIDA), exist_ok=True)
    print(f"\n[7] Guardando en {RUTA_SALIDA}...")
    wb.save(RUTA_SALIDA)
    print(f"    OK -> archivo guardado.")

    print(f"\n{sep}")
    print(f"  Proceso completado exitosamente.")
    print(f"  Archivo: {RUTA_SALIDA}")
    print(sep)


if __name__ == "__main__":
    main()
