"""Original homology job handoff contract used by received-result validation."""

VERSION = 'single_query_phmmer_jobs_v2'


def _object(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def _reference(namespace):
    return {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}


HANDOFF_SCHEMA = _object({'job_ref': _reference('homology_job'), 'registry_ref': _reference('execution_registry'),
    'backend': {'type': 'string', 'enum': [VERSION]},
    'status_interface': {'type': 'string', 'enum': ['homology.status.v1']},
    'progress_interface': {'type': 'string', 'enum': ['homology.progress.v1']},
    'results_interface': {'type': 'string', 'enum': ['homology.results.v1']}})
