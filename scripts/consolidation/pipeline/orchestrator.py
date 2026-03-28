"""
consolidation/pipeline/orchestrator.py
Orquestador del pipeline de consolidación
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from ..core.constants import AÑO_CIERRE_ACTUAL, get_project_paths
from ..core.utils import ValidationError
from ..extractors.factory import ExtractorFactory
from ..loaders.data_loader import DataLoader

logger = logging.getLogger(__name__)


class ConsolidationOrchestrator:
    """
    Orquestador principal del proceso de consolidación.
    
    Coordina la carga, procesamiento y generación de outputs.
    """
    
    def __init__(self):
        self.paths = get_project_paths()
        self.loader = DataLoader()
        self.metrics = {
            'start_time': None,
            'end_time': None,
            'records_processed': 0,
            'records_na': 0,
            'records_skipped': 0,
            'errors': []
        }
    
    def run(self) -> Dict:
        """
        Ejecuta pipeline completo de consolidación.
        
        Returns:
            Dict con métricas y resultados
        """
        self.metrics['start_time'] = time.time()
        
        try:
            # 1. Validación pre-ejecución
            self._validate_prerequisites()
            
            # 2. Carga de fuentes
            sources = self._load_sources()
            
            # 3. Procesamiento
            processed = self._process_data(sources)
            
            # 4. Generación de output
            self._generate_output(processed)
            
            self.metrics['end_time'] = time.time()
            self._log_summary()
            
            return {
                'success': True,
                'metrics': self.metrics,
                'output_file': self.paths['OUTPUT_FILE']
            }
            
        except Exception as e:
            logger.exception("Error en consolidación")
            self.metrics['errors'].append(str(e))
            return {
                'success': False,
                'error': str(e),
                'metrics': self.metrics
            }
    
    def _validate_prerequisites(self):
        """Valida que existan archivos requeridos."""
        required = [
            self.paths['CONSOLIDADO_API_KW'],
            self.paths['INPUT_FILE']
        ]
        
        missing = [p for p in required if not p.exists()]
        if missing:
            raise ValidationError(
                f"Archivos requeridos no encontrados: {missing}"
            )
        
        logger.info("Validación de prerequisitos: OK")
    
    def _load_sources(self) -> Dict:
        """Carga todas las fuentes de datos."""
        logger.info("=" * 60)
        logger.info("CARGA DE FUENTES")
        logger.info("=" * 60)
        
        sources = {
            'api_consolidated': self.loader.load_api_consolidated(),
            'kawak_2025': self.loader.load_kawak_2025(),
            'historical': self.loader.load_historical_consolidated(),
            'kawak_valid_ids': self.loader.load_kawak_valid_ids(),
            'lmi_metric_ids': self.loader.load_lmi_metric_ids(),
        }
        
        return sources
    
    def _process_data(self, sources: Dict) -> Dict:
        """
        Procesa datos aplicando estrategias de extracción.
        
        Args:
            sources: Dict con DataFrames cargados
        
        Returns:
            Dict con datos procesados por tipo
        """
        logger.info("=" * 60)
        logger.info("PROCESAMIENTO DE DATOS")
        logger.info("=" * 60)
        
        df_api = sources['api_consolidated']
        
        # Preparar configuraciones
        extraction_configs = self._load_extraction_configs()
        
        # Procesar registros
        processed = {
            'historico': [],
            'semestral': [],
            'cierres': [],
            'na_count': 0,
            'skip_count': 0
        }
        
        for idx, row in df_api.iterrows():
            # Verificar si es N/A primero
            from ..core.utils import es_registro_na
            if es_registro_na(row.to_dict()):
                processed['na_count'] += 1
                continue
            
            # Determinar extractor
            row_id = str(row['Id'])
            config = extraction_configs.get(row_id, {'patron': 'LAST'})
            
            extractor = ExtractorFactory.create_from_config(config)
            
            result = extractor.extract(row.to_dict())
            
            if result.fuente == 'skip':
                processed['skip_count'] += 1
                continue
            
            # Clasificar según periodicidad
            periodicidad = row.get('Periodicidad', 'Mensual')
            
            # Aquí iría la lógica de enrutamiento a histórico/semestral/cierres
            # (simplificado para el ejemplo)
            processed['historico'].append({
                'Id': row['Id'],
                'Fecha': row['fecha'],
                'Meta': result.meta,
                'Ejecucion': result.ejec,
                'Cumplimiento': None,  # Calcular
                'LLAVE': row['LLAVE'],
                'fuente': result.fuente,
                'es_na': result.es_na
            })
        
        self.metrics['records_processed'] = len(processed['historico'])
        self.metrics['records_na'] = processed['na_count']
        self.metrics['records_skipped'] = processed['skip_count']
        
        logger.info(f"  Procesados: {self.metrics['records_processed']:,}")
        logger.info(f"  N/A: {self.metrics['records_na']:,}")
        logger.info(f"  Skip: {self.metrics['records_skipped']:,}")
        
        return processed
    
    def _load_extraction_configs(self) -> Dict:
        """
        Carga configuraciones de extracción desde archivo.
        
        Returns:
            Dict de {id: config}
        """
        # Importar función del script original para compatibilidad
        import sys
        from pathlib import Path
        scripts_dir = Path(__file__).parent.parent.parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        
        try:
            from actualizar_consolidado import cargar_config_patrones
            return cargar_config_patrones()
        except ImportError:
            logger.warning("No se pudo cargar configuración de patrones")
            return {}
    
    def _generate_output(self, processed: Dict):
        """
        Genera archivo Excel de salida.
        
        Args:
            processed: Dict con datos procesados
        """
        logger.info("=" * 60)
        logger.info("GENERACIÓN DE OUTPUT")
        logger.info("=" * 60)
        
        import shutil
        shutil.copy(self.paths['INPUT_FILE'], self.paths['OUTPUT_FILE'])
        
        # Aquí iría la escritura de datos procesados
        # usando openpyxl o xlsxwriter
        
        logger.info(f"Output generado: {self.paths['OUTPUT_FILE']}")
    
    def _log_summary(self):
        """Muestra resumen de ejecución."""
        duration = self.metrics['end_time'] - self.metrics['start_time']
        
        logger.info("=" * 60)
        logger.info("RESUMEN FINAL")
        logger.info("=" * 60)
        logger.info(f"Duración: {duration:.2f}s")
        logger.info(f"Registros procesados: {self.metrics['records_processed']:,}")
        logger.info(f"Registros N/A: {self.metrics['records_na']:,}")
        logger.info(f"Registros skip: {self.metrics['records_skipped']:,}")
        
        if self.metrics['errors']:
            logger.warning(f"Errores: {len(self.metrics['errors'])}")
