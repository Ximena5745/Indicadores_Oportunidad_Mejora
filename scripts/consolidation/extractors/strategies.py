"""
consolidation/extractors/strategies.py
Estrategias concretas de extracción
"""

import logging
from typing import Any, Dict, Optional

import pandas as pd

from ..core.utils import (
    es_registro_na, es_vacio, extraer_meta_ejec_variables,
    extraer_por_simbolo, nan2none, parse_json_safe
)
from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class APIDirectExtractor(BaseExtractor):
    """
    Extractor para uso directo de resultado API.
    Patrón: LAST
    """
    
    def extract(self, row: Dict, hist_meta_escala: Optional[float] = None) -> ExtractionResult:
        """Extrae usando resultado API directamente."""
        resultado = self._get_nan_safe(row, 'resultado')
        meta_api = row.get('meta')
        
        if resultado is not None:
            meta_val = self._get_nan_safe(row, 'meta') if not es_vacio(meta_api) else None
            return ExtractionResult(
                meta=meta_val,
                ejec=resultado,
                fuente='api_directo',
                es_na=False
            )
        
        return ExtractionResult(fuente='sin_resultado', es_na=False)
    
    def can_extract(self, row: Dict) -> bool:
        resultado = self._get_nan_safe(row, 'resultado')
        return resultado is not None


class VariableSymbolExtractor(BaseExtractor):
    """
    Extractor por símbolo de variable.
    Patrón: VARIABLES
    """
    
    def extract(self, row: Dict, hist_meta_escala: Optional[float] = None) -> ExtractionResult:
        """Extrae usando símbolos configurados."""
        vars_list = parse_json_safe(row.get('variables'))
        
        if not vars_list:
            return ExtractionResult(fuente='skip', es_na=False)
        
        sim_e = self.config.get('simbolo_ejec', '')
        sim_m = self.config.get('simbolo_meta', '')
        
        # Intento por símbolo configurado
        if sim_e:
            ejec_v = extraer_por_simbolo(vars_list, sim_e)
            if ejec_v is not None:
                meta_v = (extraer_por_simbolo(vars_list, sim_m) if sim_m 
                         else self._get_nan_safe(row, 'meta'))
                return ExtractionResult(
                    meta=meta_v,
                    ejec=ejec_v,
                    fuente='variables_simbolo',
                    es_na=False
                )
        
        # Fallback: keyword matching
        meta_v, ejec_v = extraer_meta_ejec_variables(vars_list)
        if ejec_v is not None:
            if meta_v is None:
                meta_v = self._get_nan_safe(row, 'meta')
            return ExtractionResult(
                meta=meta_v,
                ejec=ejec_v,
                fuente='variables',
                es_na=False
            )
        
        return ExtractionResult(fuente='skip', es_na=False)
    
    def can_extract(self, row: Dict) -> bool:
        vars_list = parse_json_safe(row.get('variables'))
        return bool(vars_list)


class SeriesSumExtractor(BaseExtractor):
    """
    Extractor sumando series.
    Patrón: SUM_SER
    """
    
    def extract(self, row: Dict, hist_meta_escala: Optional[float] = None) -> ExtractionResult:
        """Extrae sumando meta y resultado de series."""
        series_list = parse_json_safe(row.get('series'))
        
        if not series_list:
            return ExtractionResult(fuente='skip', es_na=False)
        
        sum_meta = sum_res = 0.0
        has_meta = has_res = False
        
        for s in series_list:
            m = s.get('meta')
            r = s.get('resultado')
            
            if m is not None and not (isinstance(m, float) and pd.isna(m)):
                sum_meta += float(m)
                has_meta = True
            
            if r is not None and not (isinstance(r, float) and pd.isna(r)):
                sum_res += float(r)
                has_res = True
        
        if has_res:
            return ExtractionResult(
                meta=sum_meta if has_meta else self._get_nan_safe(row, 'meta'),
                ejec=sum_res,
                fuente='series_sum',
                es_na=False
            )
        
        return ExtractionResult(fuente='skip', es_na=False)
    
    def can_extract(self, row: Dict) -> bool:
        series_list = parse_json_safe(row.get('series'))
        return bool(series_list)


class NARecordExtractor(BaseExtractor):
    """
    Extractor para registros No Aplica.
    Detecta y marca registros N/A.
    """
    
    def extract(self, row: Dict, hist_meta_escala: Optional[float] = None) -> ExtractionResult:
        """Detecta si es registro N/A y retorna meta solamente."""
        if es_registro_na(row):
            meta_api = row.get('meta')
            meta_val = self._get_nan_safe(row, 'meta') if not es_vacio(meta_api) else None
            
            return ExtractionResult(
                meta=meta_val,
                ejec=None,
                fuente='na_record',
                es_na=True
            )
        
        return ExtractionResult(fuente='not_na', es_na=False)
    
    def can_extract(self, row: Dict) -> bool:
        return es_registro_na(row)


class HeuristicExtractor(BaseExtractor):
    """
    Extractor heurístico para casos sin configuración.
    Implementa la lógica heurística original.
    """
    
    def extract(self, row: Dict, hist_meta_escala: Optional[float] = None) -> ExtractionResult:
        """Aplica heurísticas para determinar extracción."""
        meta_api = row.get('meta')
        resultado = self._get_nan_safe(row, 'resultado')
        
        es_grande = (hist_meta_escala is not None and hist_meta_escala > 1000)
        api_es_porcentaje = (not es_vacio(meta_api) and abs(float(meta_api)) <= 200)
        
        # Caso: indicadores grandes con meta porcentaje → buscar en variables
        if es_grande and api_es_porcentaje:
            vars_list = parse_json_safe(row.get('variables'))
            if vars_list:
                meta_v, ejec_v = self._extraer_de_variables(vars_list)
                if ejec_v is not None:
                    return ExtractionResult(meta=meta_v, ejec=ejec_v, fuente='variables', es_na=False)
            
            series_list = parse_json_safe(row.get('series'))
            if series_list:
                sum_m, sum_r = self._sumar_series(series_list)
                if sum_r is not None:
                    return ExtractionResult(meta=sum_m, ejec=sum_r, fuente='series_sum', es_na=False)
            
            return ExtractionResult(fuente='skip', es_na=False)
        
        # Caso normal: usar resultado API
        if resultado is not None:
            meta_val = self._get_nan_safe(row, 'meta') if not es_vacio(meta_api) else None
            return ExtractionResult(meta=meta_val, ejec=resultado, fuente='api_directo', es_na=False)
        
        # Fallback: buscar en series
        series_list = parse_json_safe(row.get('series'))
        if series_list:
            sum_m, sum_r = self._sumar_series(series_list)
            if sum_r is not None:
                return ExtractionResult(meta=sum_m, ejec=sum_r, fuente='series_sum_fallback', es_na=False)
        
        return ExtractionResult(fuente='sin_resultado', es_na=False)
    
    def _extraer_de_variables(self, vars_list):
        """Helper para extraer de variables."""
        from ..core.utils import extraer_meta_ejec_variables
        return extraer_meta_ejec_variables(vars_list)
    
    def _sumar_series(self, series_list):
        """Helper para sumar series."""
        sum_meta = sum_res = 0.0
        has_meta = has_res = False
        
        for s in series_list:
            m = s.get('meta')
            r = s.get('resultado')
            
            if m is not None and not pd.isna(m):
                sum_meta += float(m)
                has_meta = True
            
            if r is not None and not pd.isna(r):
                sum_res += float(r)
                has_res = True
        
        return (sum_meta if has_meta else None), (sum_res if has_res else None)
