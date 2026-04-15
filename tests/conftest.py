# tests/conftest.py — configuración global de pytest
# Excluye scripts diagnóstico (test_consol, test_sunburst) que no son tests pytest reales
collect_ignore_glob = [
    "test_consol.py",
    "test_filter.py",
    "test_sunburst.py",
]
