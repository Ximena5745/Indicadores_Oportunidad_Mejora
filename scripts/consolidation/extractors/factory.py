"""
consolidation/extractors/factory.py
Factory para crear extractores según configuración
"""

import logging
from typing import Dict, Optional

from .base import BaseExtractor
from .strategies import (
    APIDirectExtractor, HeuristicExtractor, NARecordExtractor,
    SeriesSumExtractor, VariableSymbolExtractor
)

logger = logging.getLogger(__name__)


class ExtractorFactory:
    """
    Factory para crear extractores según patrón de configuración.
    """
    
    _extractors = {
        'LAST': APIDirectExtractor,
        'VARIABLES': VariableSymbolExtractor,
        'SUM_SER': SeriesSumExtractor,
        'AVG': APIDirectExtractor,
        'SUM': APIDirectExtractor,
    }
    
    @classmethod
    def create_extractor(
        cls,
        patron: str,
        config: Optional[Dict] = None
    ) -> BaseExtractor:
        """
        Crea extractor según patrón.
        
        Args:
            patron: Patrón de extracción (LAST, VARIABLES, etc.)
            config: Configuración adicional para el extractor
        
        Returns:
            Instancia de BaseExtractor
        """
        extractor_class = cls._extractors.get(patron)
        
        if extractor_class is None:
            logger.warning(f"Patrón desconocido: {patron}, usando heurística")
            return HeuristicExtractor(config)
        
        return extractor_class(config)
    
    @classmethod
    def create_from_config(cls, config_dict: Dict) -> BaseExtractor:
        """
        Crea extractor desde diccionario de configuración.
        
        Args:
            config_dict: Dict con 'patron', 'simbolo_ejec', 'simbolo_meta'
        
        Returns:
            Instancia de BaseExtractor configurada
        """
        patron = config_dict.get('patron', 'LAST')
        return cls.create_extractor(patron, config_dict)
    
    @classmethod
    def get_available_patterns(cls) -> list:
        """Retorna lista de patrones disponibles."""
        return list(cls._extractors.keys())
