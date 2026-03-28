"""
consolidation/extractors/base.py
Clase base para estrategias de extracción
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

import pandas as pd


class ExtractionResult:
    """Resultado estandarizado de extracción."""
    
    def __init__(
        self,
        meta: Optional[float] = None,
        ejec: Optional[float] = None,
        fuente: str = 'unknown',
        es_na: bool = False,
        metadata: Optional[Dict] = None
    ):
        self.meta = meta
        self.ejec = ejec
        self.fuente = fuente
        self.es_na = es_na
        self.metadata = metadata or {}
    
    def to_tuple(self) -> Tuple:
        """Convierte a tupla para compatibilidad."""
        return (self.meta, self.ejec, self.fuente, self.es_na)
    
    def __repr__(self):
        return f"ExtractionResult(meta={self.meta}, ejec={self.ejec}, fuente={self.fuente}, es_na={self.es_na})"


class BaseExtractor(ABC):
    """
    Clase base para extractores de meta/ejecución.
    
    Cada estrategia concreta debe implementar el método extract().
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def extract(self, row: Dict, hist_meta_escala: Optional[float] = None) -> ExtractionResult:
        """
        Extrae meta y ejecución de un registro.
        
        Args:
            row: Diccionario con datos del registro
            hist_meta_escala: Escala histórica de meta (opcional)
        
        Returns:
            ExtractionResult con valores extraídos
        """
        pass
    
    def can_extract(self, row: Dict) -> bool:
        """
        Verifica si este extractor puede procesar el registro.
        
        Args:
            row: Diccionario con datos del registro
        
        Returns:
            True si puede procesar, False en caso contrario
        """
        return True
    
    def _safe_numeric(self, val: Any) -> Optional[float]:
        """Convierte valor a numérico de forma segura."""
        if val is None:
            return None
        
        try:
            num = pd.to_numeric(val, errors='coerce')
            return None if pd.isna(num) else float(num)
        except:
            return None
    
    def _get_nan_safe(self, row: Dict, key: str) -> Optional[float]:
        """Obtiene valor de row manejando NaN."""
        from ..core.utils import nan2none
        val = row.get(key)
        return nan2none(self._safe_numeric(val))
