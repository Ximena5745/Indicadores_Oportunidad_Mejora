"""
tests/consolidation/test_utils.py
Tests unitarios para utilidades del sistema de consolidación
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Añadir scripts al path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from consolidation.core.utils import (
    calcular_cumplimiento,
    es_registro_na,
    es_vacio,
    extraer_meta_ejec_variables,
    extraer_por_simbolo,
    id_str,
    limpiar_html,
    make_llave,
    nan2none,
    parse_json_safe,
)


class TestMakeLlave:
    """Tests para make_llave()."""
    
    def test_make_llave_basico(self):
        """Generación de llave básica."""
        result = make_llave(123, "2024-03-15")
        assert result == "123-2024-03-15"
    
    def test_make_llave_decimal(self):
        """Manejo de ID con .0."""
        result = make_llave(123.0, "2024-03-15")
        assert result == "123-2024-03-15"
    
    def test_make_llave_string(self):
        """ID como string."""
        result = make_llave("456", "2024-12-01")
        assert result == "456-2024-12-01"
    
    def test_make_llave_timestamp(self):
        """Fecha como Timestamp."""
        fecha = pd.Timestamp("2024-06-30")
        result = make_llave(789, fecha)
        assert result == "789-2024-06-30"
    
    def test_make_llave_error(self):
        """Error en conversión retorna None."""
        result = make_llave(None, "fecha-invalida")
        assert result is None


class TestCalcularCumplimiento:
    """Tests para calcular_cumplimiento()."""
    
    def test_cumplimiento_positivo(self):
        """Sentido positivo."""
        capped, real = calcular_cumplimiento(100, 95, "Positivo")
        assert real == 0.95
        assert capped == 0.95
    
    def test_cumplimiento_negativo(self):
        """Sentido negativo."""
        capped, real = calcular_cumplimiento(100, 105, "Negativo")
        assert real == 100 / 105
        assert capped == 100 / 105
    
    def test_cumplimiento_sobre_meta(self):
        """Sobrecumplimiento con tope."""
        capped, real = calcular_cumplimiento(100, 200, "Positivo", tope=1.3)
        assert real == 2.0
        assert capped == 1.3
    
    def test_cumplimiento_meta_cero(self):
        """Meta cero retorna None."""
        result = calcular_cumplimiento(0, 100, "Positivo")
        assert result == (None, None)
    
    def test_cumplimiento_valores_none(self):
        """Valores None retornan None."""
        result = calcular_cumplimiento(None, 100, "Positivo")
        assert result == (None, None)
    
    def test_cumplimiento_ejecucion_cero_negativo(self):
        """Ejecución cero en sentido negativo."""
        result = calcular_cumplimiento(100, 0, "Negativo")
        assert result == (None, None)


class TestEsVacio:
    """Tests para es_vacio()."""
    
    def test_none_es_vacio(self):
        assert es_vacio(None) is True
    
    def test_nan_es_vacio(self):
        assert es_vacio(float('nan')) is True
        assert es_vacio(np.nan) is True
    
    def test_string_vacio_es_vacio(self):
        assert es_vacio("") is True
        assert es_vacio("  ") is True
    
    def test_string_nan_es_vacio(self):
        assert es_vacio("nan") is True
        assert es_vacio("None") is True
    
    def test_valor_valido_no_es_vacio(self):
        assert es_vacio(0) is False
        assert es_vacio("0") is False
        assert es_vacio("texto") is False


class TestIdStr:
    """Tests para id_str()."""
    
    def test_id_entero(self):
        assert id_str(123) == "123"
    
    def test_id_decimal_con_cero(self):
        assert id_str(123.0) == "123"
    
    def test_id_decimal_sin_cero(self):
        assert id_str(123.5) == "123.5"
    
    def test_id_string(self):
        assert id_str("456") == "456"


class TestParseJsonSafe:
    """Tests para parse_json_safe()."""
    
    def test_parse_lista(self):
        result = parse_json_safe("[1, 2, 3]")
        assert result == [1, 2, 3]
    
    def test_parse_dict(self):
        result = parse_json_safe("{'a': 1, 'b': 2}")
        assert result == {'a': 1, 'b': 2}
    
    def test_parse_none(self):
        assert parse_json_safe(None) is None
    
    def test_parse_nan(self):
        assert parse_json_safe(np.nan) is None
    
    def test_parse_vacio(self):
        assert parse_json_safe("") is None
    
    def test_parse_invalido(self):
        """String inválido retorna None."""
        result = parse_json_safe("no es json")
        assert result is None


class TestLimpiarHtml:
    """Tests para limpiar_html()."""
    
    def test_limpia_acentos(self):
        assert limpiar_html("caf&eacute;") == "café"
    
    def test_limpia_tildes(self):
        assert limpiar_html("ni&ntilde;o") == "niño"
    
    def test_limpia_multiple(self):
        assert limpiar_html("&aacute;&eacute;&iacute;&oacute;&uacute;") == "áéíóú"
    
    def test_no_string(self):
        assert limpiar_html(123) == 123
        assert limpiar_html(None) is None


class TestExtraerMetaEjecVariables:
    """Tests para extraer_meta_ejec_variables()."""
    
    def test_extrae_por_keyword(self):
        vars_list = [
            {'nombre': 'Real ejecutado', 'valor': 95},
            {'nombre': 'Meta planeada', 'valor': 100}
        ]
        meta, ejec = extraer_meta_ejec_variables(vars_list)
        assert ejec == 95
        assert meta == 100
    
    def test_extrae_por_posicion(self):
        """Cuando no hay keywords, usa posición."""
        vars_list = [
            {'nombre': 'Var1', 'valor': 50},
            {'nombre': 'Var2', 'valor': 60}
        ]
        meta, ejec = extraer_meta_ejec_variables(vars_list)
        assert ejec == 50  # Primera posición
        assert meta == 60  # Segunda posición
    
    def test_lista_vacia(self):
        assert extraer_meta_ejec_variables([]) == (None, None)
    
    def test_valores_nan(self):
        vars_list = [
            {'nombre': 'Real', 'valor': float('nan')},
            {'nombre': 'Meta', 'valor': 100}
        ]
        meta, ejec = extraer_meta_ejec_variables(vars_list)
        assert ejec is None
        assert meta == 100


class TestExtraerPorSimbolo:
    """Tests para extraer_por_simbolo()."""
    
    def test_extrae_por_simbolo(self):
        vars_list = [
            {'simbolo': 'R', 'valor': 95},
            {'simbolo': 'M', 'valor': 100}
        ]
        assert extraer_por_simbolo(vars_list, 'R') == 95.0
        assert extraer_por_simbolo(vars_list, 'M') == 100.0
    
    def test_simbolo_no_existe(self):
        vars_list = [{'simbolo': 'X', 'valor': 50}]
        assert extraer_por_simbolo(vars_list, 'Y') is None
    
    def test_simbolo_case_insensitive(self):
        vars_list = [{'simbolo': 'ABC', 'valor': 75}]
        assert extraer_por_simbolo(vars_list, 'abc') == 75.0
    
    def test_valor_nan(self):
        vars_list = [{'simbolo': 'X', 'valor': float('nan')}]
        assert extraer_por_simbolo(vars_list, 'X') is None


class TestEsRegistroNA:
    """Tests para es_registro_na()."""
    
    def test_na_por_analisis(self):
        """Texto 'no aplica' en análisis."""
        row = {
            'resultado': None,
            'analisis': 'Este periodo no aplica medición'
        }
        assert es_registro_na(row) is True
    
    def test_na_por_resultado_nan(self):
        """Resultado NaN sin datos útiles."""
        row = {
            'resultado': float('nan'),
            'analisis': '',
            'variables': None,
            'series': None
        }
        assert es_registro_na(row) is True
    
    def test_no_na_con_resultado(self):
        """Tiene resultado numérico."""
        row = {
            'resultado': 95.5,
            'analisis': ''
        }
        assert es_registro_na(row) is False
    
    def test_no_na_con_variables(self):
        """Resultado NaN pero tiene variables."""
        row = {
            'resultado': float('nan'),
            'variables': "[{'valor': 50}]",
            'analisis': ''
        }
        assert es_registro_na(row) is False


class TestNan2None:
    """Tests para nan2none()."""
    
    def test_nan_to_none(self):
        assert nan2none(float('nan')) is None
        assert nan2none(np.nan) is None
    
    def test_none_stays_none(self):
        assert nan2none(None) is None
    
    def test_valid_values(self):
        assert nan2none(0) == 0
        assert nan2none(5.5) == 5.5
        assert nan2none("texto") == "texto"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
