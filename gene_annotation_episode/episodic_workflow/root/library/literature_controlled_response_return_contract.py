from __future__ import annotations

from copy import deepcopy as cp
from . import literature_controlled_response_v3_contracts as source

def controlled_response_cells_schema():
    return cp(source._schemas()['NATIVE_RETURN_SCHEMA_V3_007'])


