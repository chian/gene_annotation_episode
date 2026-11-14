"""Execution envelope for one selected, source-derived Cobra/GLPK FBA call.

Analytical records are owned by ``flux_balance_contracts``. This module only
validates execution paths, the selected software closure and the run envelope.
It neither discovers a resource nor starts work.
"""
from pathlib import PurePosixPath

def require(condition, code):
    if not condition:
        raise ValueError(code)

def path_value(value, *, absolute):
    require(type(value) is str and value and (not any((c in value for c in '\x00\r\n\\'))), 'fba_invalid_path')
    path = PurePosixPath(value)
    require(path.is_absolute() == absolute and str(path) == value and ('..' not in path.parts) and (value not in ('.', '/')) and (not value.startswith('//')), 'fba_invalid_path')
    return path
