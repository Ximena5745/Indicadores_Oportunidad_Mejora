#!/usr/bin/env python3
"""
consolidation/cli.py
Interfaz de línea de comandos con argparse
"""

import argparse
import logging
import sys
from pathlib import Path

from .core.logging_config import setup_logging
from .pipeline.orchestrator import ConsolidationOrchestrator


def create_parser():
    """Crea parser de argumentos."""
    parser = argparse.ArgumentParser(
        prog='consolidation',
        description='Sistema de consolidación de indicadores - Versión Modular v8',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s                          # Ejecutar con configuración por defecto
  %(prog)s --dry-run                # Simular sin generar output
  %(prog)s --workers 4              # Usar 4 workers en paralelo
  %(prog)s --config config.yaml     # Usar configuración externa
  %(prog)s --validate-only          # Solo validar inputs
        """
    )
    
    # Argumentos principales
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 8.0.0'
    )
    
    # Modos de ejecución
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular ejecución sin generar archivos'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Solo validar archivos de entrada y salir'
    )
    
    # Configuración
    parser.add_argument(
        '-c', '--config',
        type=str,
        help='Ruta a archivo de configuración YAML/JSON'
    )
    
    parser.add_argument(
        '--input',
        type=str,
        help='Ruta al archivo de entrada (sobreescribe config)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Ruta al archivo de salida (sobreescribe config)'
    )
    
    # Procesamiento
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=None,
        help='Número de workers para procesamiento paralelo (default: auto)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Tamaño de batch para procesamiento (default: 1000)'
    )
    
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Deshabilitar procesamiento paralelo'
    )
    
    # Logging
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Aumentar verbosidad (-v, -vv, -vvv)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Modo silencioso, solo errores'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Ruta al archivo de log'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Deshabilitar colores en consola'
    )
    
    # Filtros
    parser.add_argument(
        '--filter-year',
        type=int,
        help='Filtrar por año específico'
    )
    
    parser.add_argument(
        '--filter-ids',
        type=str,
        help='IDs específicos a procesar (separados por coma)'
    )
    
    # Reporting
    parser.add_argument(
        '--report-format',
        choices=['json', 'yaml', 'html', 'xlsx'],
        default='json',
        help='Formato de reporte de métricas'
    )
    
    parser.add_argument(
        '--report-output',
        type=str,
        help='Ruta para guardar reporte de métricas'
    )
    
    return parser


def setup_logging_from_args(args):
    """Configura logging basado en argumentos CLI."""
    
    # Determinar nivel de logging
    if args.quiet:
        level = logging.ERROR
    elif args.verbose >= 3:
        level = logging.DEBUG
    elif args.verbose >= 2:
        level = logging.INFO
    elif args.verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    
    # Configurar
    log_file = Path(args.log_file) if args.log_file else None
    
    setup_logging(
        level=level,
        log_file=log_file,
        console=True
    )
    
    return level


def run_cli():
    """Punto de entrada CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configurar logging
    log_level = setup_logging_from_args(args)
    logger = logging.getLogger(__name__)
    
    logger.info(f"CLI iniciado con nivel de log: {logging.getLevelName(log_level)}")
    
    # Validar argumentos
    if args.dry_run:
        logger.info("MODO DRY-RUN: No se generarán archivos")
    
    # Validar-only mode
    if args.validate_only:
        logger.info("Modo validación: verificando archivos...")
        # Implementar validación
        return 0
    
    # Cargar configuración si existe
    config = {}
    if args.config:
        logger.info(f"Cargando configuración: {args.config}")
        # Cargar YAML/JSON
        pass
    
    # Crear orquestador con config
    orchestrator = ConsolidationOrchestrator(
        config=config,
        workers=args.workers if not args.no_parallel else 1,
        batch_size=args.batch_size
    )
    
    # Ejecutar
    try:
        result = orchestrator.run(
            dry_run=args.dry_run,
            filter_year=args.filter_year,
            filter_ids=args.filter_ids.split(',') if args.filter_ids else None
        )
        
        if result['success']:
            logger.info("✅ Consolidación completada exitosamente")
            
            # Generar reporte si se solicita
            if args.report_output:
                generate_report(result, args.report_format, args.report_output)
            
            return 0
        else:
            logger.error(f"❌ Error: {result.get('error', 'Unknown')}")
            return 1
            
    except Exception as e:
        logger.exception("Error fatal en consolidación")
        return 1


def generate_report(result, format, output_path):
    """Genera reporte de métricas."""
    import json
    from datetime import datetime
    
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'success': result['success'],
        'metrics': result.get('metrics', {})
    }
    
    if format == 'json':
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
    
    elif format == 'yaml':
        import yaml
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(metrics, f, allow_unicode=True)
    
    logging.getLogger(__name__).info(f"Reporte guardado: {output_path}")


if __name__ == '__main__':
    sys.exit(run_cli())
