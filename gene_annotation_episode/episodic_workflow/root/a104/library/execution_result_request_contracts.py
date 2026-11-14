from __future__ import annotations
from ..execution_contracts import obj
RESULTS_VERSION = 'execution_results_assignment_v1'
TEXT = {'type': 'string', 'minLength': 1}
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT, 'selector': {'type': 'object'}})
