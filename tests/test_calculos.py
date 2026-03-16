"""
tests/test_calculos.py — Pruebas unitarias para core/calculos.py.

Ejecutar:
    pytest tests/ -v

No requiere Streamlit ni archivos de datos.
"""
import math
import pandas as pd
import pytest

from core.calculos import (
    normalizar_cumplimiento,
    categorizar_cumplimiento,
    calcular_tendencia,
    calcular_meses_en_peligro,
    obtener_ultimo_registro,
    calcular_kpis,
    estado_tiempo_acciones,
)


# ── normalizar_cumplimiento ────────────────────────────────────────────────────

class TestNormalizarCumplimiento:
    def test_decimal_sin_cambio(self):
        assert normalizar_cumplimiento(0.95) == pytest.approx(0.95)

    def test_decimal_mayor_a_1(self):
        assert normalizar_cumplimiento(1.30) == pytest.approx(1.30)

    def test_porcentaje_divide_100(self):
        assert normalizar_cumplimiento(95.0) == pytest.approx(0.95)

    def test_porcentaje_mayor_100(self):
        assert normalizar_cumplimiento(130.0) == pytest.approx(1.30)

    def test_string_con_simbolo(self):
        assert normalizar_cumplimiento("95%") == pytest.approx(0.95)

    def test_string_coma_decimal(self):
        assert normalizar_cumplimiento("0,95") == pytest.approx(0.95)

    def test_nan_retorna_nan(self):
        assert math.isnan(normalizar_cumplimiento(float("nan")))

    def test_none_retorna_nan(self):
        import numpy as np
        assert math.isnan(normalizar_cumplimiento(np.nan))

    def test_string_invalido(self):
        assert math.isnan(normalizar_cumplimiento("no_es_numero"))

    def test_cero(self):
        assert normalizar_cumplimiento(0) == pytest.approx(0.0)

    def test_exactamente_2_no_divide(self):
        # valor == 2 NO divide (condición es > 2)
        assert normalizar_cumplimiento(2.0) == pytest.approx(2.0)

    def test_mayor_de_2_divide(self):
        assert normalizar_cumplimiento(2.01) == pytest.approx(0.0201)


# ── categorizar_cumplimiento ───────────────────────────────────────────────────

class TestCategorizarCumplimiento:
    def test_peligro(self):
        assert categorizar_cumplimiento(0.50) == "Peligro"

    def test_limite_peligro(self):
        assert categorizar_cumplimiento(0.799) == "Peligro"

    def test_alerta_limite_inferior(self):
        assert categorizar_cumplimiento(0.80) == "Alerta"

    def test_alerta(self):
        assert categorizar_cumplimiento(0.90) == "Alerta"

    def test_cumplimiento_exacto(self):
        assert categorizar_cumplimiento(1.00) == "Cumplimiento"

    def test_cumplimiento(self):
        assert categorizar_cumplimiento(1.03) == "Cumplimiento"

    def test_limite_sobrecumplimiento(self):
        assert categorizar_cumplimiento(1.05) == "Cumplimiento"

    def test_sobrecumplimiento(self):
        assert categorizar_cumplimiento(1.10) == "Sobrecumplimiento"

    def test_nan_sin_dato(self):
        assert categorizar_cumplimiento(float("nan")) == "Sin dato"

    def test_sentido_negativo_no_cambia_umbral(self):
        # El Sentido Negativo se aplica al calcular el cumplimiento, no aquí
        assert categorizar_cumplimiento(1.10, sentido="Negativo") == "Sobrecumplimiento"


# ── calcular_tendencia ─────────────────────────────────────────────────────────

class TestCalcularTendencia:
    def _df(self, vals):
        return pd.DataFrame({
            "Fecha": pd.date_range("2024-01-01", periods=len(vals), freq="MS"),
            "Cumplimiento_norm": vals,
        })

    def test_sin_datos_suficientes(self):
        assert calcular_tendencia(self._df([0.9])) == "→"

    def test_mejora(self):
        assert calcular_tendencia(self._df([0.80, 0.95])) == "↑"

    def test_empeora(self):
        assert calcular_tendencia(self._df([0.95, 0.80])) == "↓"

    def test_estable(self):
        assert calcular_tendencia(self._df([0.95, 0.954])) == "→"


# ── calcular_meses_en_peligro ──────────────────────────────────────────────────

class TestCalcularMesesEnPeligro:
    def _df(self, cats):
        return pd.DataFrame({
            "Fecha": pd.date_range("2024-01-01", periods=len(cats), freq="MS"),
            "Categoria": cats,
        })

    def test_sin_peligro(self):
        assert calcular_meses_en_peligro(self._df(["Cumplimiento", "Alerta"])) == 0

    def test_uno_en_peligro(self):
        assert calcular_meses_en_peligro(self._df(["Cumplimiento", "Peligro"])) == 1

    def test_consecutivos(self):
        assert calcular_meses_en_peligro(self._df(["Alerta", "Peligro", "Peligro"])) == 2

    def test_no_consecutivos(self):
        # Rompió la racha en el penúltimo
        assert calcular_meses_en_peligro(self._df(["Peligro", "Cumplimiento", "Peligro"])) == 1


# ── obtener_ultimo_registro ────────────────────────────────────────────────────

class TestObtenerUltimoRegistro:
    def test_vacio(self):
        df = pd.DataFrame()
        assert obtener_ultimo_registro(df).empty

    def test_deduplica_por_id(self):
        df = pd.DataFrame({
            "Id": ["1", "1", "2"],
            "Fecha": pd.to_datetime(["2024-01-01", "2024-06-01", "2024-01-01"]),
            "Cumplimiento_norm": [0.8, 0.9, 1.0],
        })
        result = obtener_ultimo_registro(df)
        assert len(result) == 2
        # Para Id=1 debe quedar el más reciente (0.9)
        assert result[result["Id"] == "1"]["Cumplimiento_norm"].iloc[0] == pytest.approx(0.9)

    def test_usa_revisar_si_existe(self):
        df = pd.DataFrame({
            "Id": ["1", "1"],
            "Fecha": pd.to_datetime(["2024-01-01", "2024-06-01"]),
            "Cumplimiento_norm": [0.8, 0.9],
            "Revisar": [1, 0],
        })
        result = obtener_ultimo_registro(df)
        assert len(result) == 1
        assert result["Cumplimiento_norm"].iloc[0] == pytest.approx(0.8)


# ── calcular_kpis ──────────────────────────────────────────────────────────────

class TestCalcularKpis:
    def test_proporciones(self):
        df = pd.DataFrame({
            "Cumplimiento_norm": [0.5, 0.85, 1.02, 1.10, float("nan")],
            "Categoria": ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento", "Sin dato"],
        })
        total, conteos = calcular_kpis(df)
        assert total == 4  # NaN excluido
        assert conteos["Peligro"]["n"] == 1
        assert conteos["Sobrecumplimiento"]["pct"] == pytest.approx(25.0)


# ── estado_tiempo_acciones ─────────────────────────────────────────────────────

class TestEstadoTiempoAcciones:
    def _df(self, dias, estado):
        return pd.DataFrame({"DIAS_VENCIDA": [dias], "ESTADO": [estado]})

    def test_cerrada(self):
        assert estado_tiempo_acciones(self._df(-10, "Cerrada"))["Estado_Tiempo"].iloc[0] == "Cerrada"

    def test_vencida(self):
        assert estado_tiempo_acciones(self._df(5, "Abierta"))["Estado_Tiempo"].iloc[0] == "Vencida"

    def test_por_vencer(self):
        assert estado_tiempo_acciones(self._df(-15, "Abierta"))["Estado_Tiempo"].iloc[0] == "Por vencer"

    def test_a_tiempo(self):
        assert estado_tiempo_acciones(self._df(-60, "Abierta"))["Estado_Tiempo"].iloc[0] == "A tiempo"
