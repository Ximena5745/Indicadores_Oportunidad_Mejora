"""
utils/calculos.py — Lógica de negocio: categorías, umbrales, salud institucional.
"""
import pandas as pd
import numpy as np

UMBRAL_PELIGRO = 0.80
UMBRAL_ALERTA  = 1.00


def normalizar_cumplimiento(valor):
    """Garantiza escala decimal [0..n]. Divide /100 solo si valor > 2."""
    if pd.isna(valor):
        return np.nan
    if isinstance(valor, str):
        valor = valor.replace("%", "").replace(",", ".").strip()
        try:
            valor = float(valor)
        except ValueError:
            return np.nan
    valor = float(valor)
    return valor / 100 if valor > 2 else valor


def categorizar_cumplimiento(cumplimiento, sentido="Positivo"):
    """Retorna: 'Peligro' | 'Alerta' | 'Cumplimiento' | 'Sobrecumplimiento' | 'Sin dato'"""
    if pd.isna(cumplimiento):
        return "Sin dato"
    if cumplimiento < UMBRAL_PELIGRO:
        return "Peligro"
    elif cumplimiento < UMBRAL_ALERTA:
        return "Alerta"
    elif cumplimiento <= 1.0:
        return "Cumplimiento"
    else:
        return "Sobrecumplimiento"


def calcular_salud_institucional(df):
    """% promedio de cumplimiento agrupado por Fecha (para gráfico de tendencia)."""
    if "Fecha" not in df.columns or df.empty:
        return pd.DataFrame(columns=["Fecha", "Salud_pct"])
    result = (
        df.groupby("Fecha")["Cumplimiento_norm"]
        .mean()
        .reset_index()
        .assign(Salud_pct=lambda x: x["Cumplimiento_norm"] * 100)
    )
    return result


def calcular_tendencia(df_indicador):
    """Compara último vs penúltimo periodo. Retorna '↑' | '↓' | '→'"""
    if len(df_indicador) < 2:
        return "→"
    df_s = df_indicador.sort_values("Fecha")
    diff = df_s.iloc[-1]["Cumplimiento_norm"] - df_s.iloc[-2]["Cumplimiento_norm"]
    if pd.isna(diff):
        return "→"
    return "↑" if diff > 0.01 else "↓" if diff < -0.01 else "→"


def calcular_meses_en_peligro(df_indicador):
    """Periodos consecutivos en Peligro (desde el más reciente)."""
    df_s = df_indicador.sort_values("Fecha", ascending=False)
    conteo = 0
    for _, row in df_s.iterrows():
        if row.get("Categoria") == "Peligro":
            conteo += 1
        else:
            break
    return conteo


def generar_recomendaciones(categoria, cum_series):
    """
    Genera lista de recomendaciones según categoría y tendencia.
    Returns: (tendencia_str, [recomendaciones])
    """
    cum_series = cum_series.dropna()

    if len(cum_series) >= 3:
        ultima   = float(cum_series.iloc[-1])
        anterior = float(cum_series.iloc[-3:-1].mean())
        if ultima > anterior + 2:
            tendencia = "Mejorando"
        elif ultima < anterior - 2:
            tendencia = "Empeorando"
        else:
            tendencia = "Estable"
    elif len(cum_series) == 2:
        delta = float(cum_series.iloc[-1]) - float(cum_series.iloc[-2])
        tendencia = "Mejorando" if delta > 2 else "Empeorando" if delta < -2 else "Estable"
    else:
        tendencia = "Sin datos suficientes"

    recs_base = {
        "Peligro": [
            "Convocar mesa de trabajo urgente con el responsable del proceso para identificar causas raíz.",
            "Revisar disponibilidad de recursos humanos, técnicos y financieros asignados al proceso.",
            "Establecer plan de acción con actividades concretas, responsables y fechas.",
            "Considerar apertura de una Oportunidad de Mejora (OM) si aún no existe.",
            "Incrementar frecuencia de seguimiento a monitoreo semanal o quincenal.",
        ],
        "Alerta": [
            "Analizar las causas que impiden alcanzar la meta del 100%.",
            "Verificar si existen acciones de mejora abiertas y revisar su avance.",
            "Implementar medidas preventivas antes de caer en zona de peligro.",
            "Revisar con el responsable los factores que pueden afectar el resultado.",
        ],
        "Cumplimiento": [
            "Documentar buenas prácticas que permiten el cumplimiento de la meta.",
            "Asegurar la continuidad de los factores que contribuyen al cumplimiento.",
            "Mantener el monitoreo periódico para detectar desviaciones a tiempo.",
        ],
        "Sobrecumplimiento": [
            "Evaluar si la meta actual es suficientemente retadora; considerar ajustarla.",
            "Documentar y socializar las buenas prácticas para replicarlas en otros procesos.",
            "Verificar que el sobrecumplimiento sea sostenible y no represente ineficiencia.",
            "Reportar el logro como caso de éxito en espacios de gestión institucional.",
        ],
    }

    recs = list(recs_base.get(categoria, ["Revisar con el responsable del proceso."]))

    if tendencia == "Empeorando" and categoria in ("Cumplimiento", "Sobrecumplimiento"):
        recs.append(
            "Aunque cumple la meta, la tendencia es negativa — identificar causas antes de que impacte el resultado."
        )
    elif tendencia == "Mejorando" and categoria == "Peligro":
        recs.append("El indicador muestra mejoría — continuar con las acciones implementadas.")
    elif tendencia == "Empeorando" and categoria == "Alerta":
        recs.append("La tendencia es negativa — priorizar medidas preventivas para evitar zona de peligro.")

    return tendencia, recs


def obtener_ultimo_registro(df):
    """Retorna el último registro por indicador (dedup por Id, keep=last)."""
    if df.empty or "Id" not in df.columns:
        return df
    return (
        df.sort_values("Fecha")
        .drop_duplicates(subset="Id", keep="last")
    )


def calcular_kpis(df_ultimo):
    """Calcula los 5 KPIs principales desde df_ultimo."""
    df_con_datos = df_ultimo[df_ultimo["Cumplimiento_norm"].notna()]
    total = len(df_con_datos)
    conteos = {}
    for cat in ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento"]:
        n = (df_con_datos["Categoria"] == cat).sum()
        pct = (n / total * 100) if total > 0 else 0
        conteos[cat] = {"n": n, "pct": round(pct, 1)}
    return total, conteos


def estado_tiempo_acciones(df):
    """Aplica reglas Estado_Tiempo sobre df de acciones (in-place)."""
    df = df.copy()
    df["Estado_Tiempo"] = "A tiempo"
    if "DIAS_VENCIDA" in df.columns and "ESTADO" in df.columns:
        df.loc[df["DIAS_VENCIDA"] > 0, "Estado_Tiempo"] = "Vencida"
        df.loc[
            (df["DIAS_VENCIDA"] >= -30) & (df["DIAS_VENCIDA"] <= 0)
            & (df["ESTADO"] != "Cerrada"),
            "Estado_Tiempo",
        ] = "Por vencer"
        df.loc[df["ESTADO"] == "Cerrada", "Estado_Tiempo"] = "Cerrada"
    return df
