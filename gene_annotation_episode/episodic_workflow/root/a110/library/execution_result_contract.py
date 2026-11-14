"""The original own-axis Results assignment envelope."""
from ..execution_contracts import obj

TEXT = {'type': 'string', 'minLength': 1}
RESULTS_VERSION = 'execution_results_assignment_v1'
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT,
                      'selector': {'type': 'object'}})
