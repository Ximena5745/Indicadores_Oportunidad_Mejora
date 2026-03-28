"""
consolidation/core/config_loader.py
Carga de configuración externa YAML/JSON
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from ..models.schemas import InputConfig, ProcessingConfig, ExtractionConfig

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Cargador de configuración desde archivos YAML/JSON.
    """
    
    SUPPORTED_FORMATS = ['.yaml', '.yml', '.json']
    
    @classmethod
    def load(cls, config_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Carga configuración desde archivo.
        
        Args:
            config_path: Ruta al archivo de configuración
        
        Returns:
            Dict con configuración cargada
        """
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {path}")
        
        suffix = path.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            return cls._load_yaml(path)
        elif suffix == '.json':
            return cls._load_json(path)
        else:
            raise ValueError(
                f"Formato no soportado: {suffix}. "
                f"Use: {', '.join(cls.SUPPORTED_FORMATS)}"
            )
    
    @classmethod
    def _load_yaml(cls, path: Path) -> Dict:
        """Carga archivo YAML."""
        if not HAS_YAML:
            raise ImportError("PyYAML no instalado. Ejecute: pip install pyyaml")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
        
        logger.info(f"Configuración YAML cargada: {path}")
        return content or {}
    
    @classmethod
    def _load_json(cls, path: Path) -> Dict:
        """Carga archivo JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        logger.info(f"Configuración JSON cargada: {path}")
        return content
    
    @classmethod
    def validate(cls, config: Dict) -> Dict[str, Any]:
        """
        Valida configuración contra esquemas Pydantic.
        
        Args:
            config: Dict con configuración
        
        Returns:
            Dict con configuración validada
        """
        validated = {}
        
        # Validar sección de archivos
        if 'input' in config:
            validated['input'] = InputConfig(**config['input'])
        
        # Validar sección de procesamiento
        if 'processing' in config:
            validated['processing'] = ProcessingConfig(**config['processing'])
        
        # Validar extracciones
        if 'extractions' in config:
            validated['extractions'] = {
                k: ExtractionConfig(id=k, **v) 
                for k, v in config['extractions'].items()
            }
        
        return validated


# Configuración por defecto
DEFAULT_CONFIG = {
    'input': {
        'input_file': 'data/raw/Resultados_Consolidados_Fuente.xlsx',
        'api_consolidated': 'data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx',
        'kawak_catalog': 'data/raw/Fuentes Consolidadas/Indicadores Kawak.xlsx',
        'lmi_report': 'data/raw/lmi_reporte.xlsx'
    },
    'processing': {
        'año_cierre': 2025,
        'batch_size': 1000,
        'use_cache': True,
        'validate_output': True
    },
    'logging': {
        'level': 'INFO',
        'format': '%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s',
        'file': 'logs/consolidation.log'
    }
}


def get_default_config() -> Dict:
    """Retorna configuración por defecto."""
    return DEFAULT_CONFIG.copy()


def merge_configs(base: Dict, override: Dict) -> Dict:
    """
    Combina dos configuraciones (override tiene prioridad).
    
    Args:
        base: Configuración base
        override: Configuración a sobreescribir
    
    Returns:
        Configuración combinada
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def save_config(config: Dict, path: Union[str, Path], format: str = 'yaml'):
    """
    Guarda configuración a archivo.
    
    Args:
        config: Configuración a guardar
        path: Ruta de destino
        format: Formato ('yaml' o 'json')
    """
    path = Path(path)
    
    if format == 'yaml':
        if not HAS_YAML:
            raise ImportError("PyYAML no instalado")
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    else:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Configuración guardada: {path}")
