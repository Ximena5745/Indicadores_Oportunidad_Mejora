#!/usr/bin/env python3
"""
consolidation/main.py
Punto de entrada moderno para consolidación
"""

import logging
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from consolidation.core.logging_config import setup_logging
from consolidation.pipeline.orchestrator import ConsolidationOrchestrator


def main():
    """
    Punto de entrada principal.
    """
    # Configurar logging
    setup_logging(
        level=logging.INFO,
        log_file=ROOT / "logs" / "consolidation.log"
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 70)
    logger.info("INICIANDO CONSOLIDACIÓN V8 - VERSIÓN MODULAR")
    logger.info("=" * 70)
    
    # Ejecutar orquestador
    orchestrator = ConsolidationOrchestrator()
    result = orchestrator.run()
    
    if result['success']:
        logger.info("✅ Consolidación completada exitosamente")
        return 0
    else:
        logger.error(f"❌ Error: {result.get('error', 'Unknown')}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
