#!/usr/bin/env python3
"""
scripts/run_consolidation.py
Wrapper para ejecutar consolidación modular
"""

import sys
import warnings

# Filtrado selectivo de warnings (no suprimir todos)
warnings.filterwarnings('default', category=UserWarning)
warnings.filterwarnings('ignore', message='.*deprecated.*')

if __name__ == '__main__':
    from consolidation.main import main
    sys.exit(main())
