"""Original private observation declaration for the A104 homology binding."""
from copy import deepcopy
from .homology_jobs import STATUS_SCHEMA

def _object(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}

EXECUTION_OBSERVATION_SCHEMA = _object({
    'observation_kind': {'type': 'string', 'enum': ['monitor_sample', 'handoff_check']},
    'sample_ref': {'type': ['string', 'null'], 'format': 'reference',
                   'x-reference-namespace': 'job_sample'},
    'sampled_at_unix_seconds': {'type': ['number', 'null'], 'minimum': 0},
    'checked_at_unix_seconds': {'type': ['number', 'null'], 'minimum': 0},
    **deepcopy(STATUS_SCHEMA['properties']),
})
