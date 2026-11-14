"""Original native job-status schema consumed by root progress admission."""

OUTPUTS = {'native_text': 'native.stdout', 'native_stderr': 'native.stderr',
           'hit_table': 'hits.tbl', 'domain_table': 'domains.tbl'}

def _object(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}

def _reference(namespace):
    return {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}

STATUS_SCHEMA = _object({'job_ref': _reference('homology_job'), 'registry_ref': _reference('execution_registry'),
    'state': {'type': 'string', 'enum': ['not_submitted', 'prepared', 'submission_unconfirmed', 'starting', 'running', 'returned', 'execution_unknown']},
    'outcome': {'type': 'string', 'enum': ['pending', 'succeeded', 'failed', 'unknown']},
    'elapsed_seconds': {'type': ['number', 'null'], 'minimum': 0},
    'duration_measure': {'type': 'string', 'enum': ['systemd_service_wall_seconds']},
    'native_returncode': {'type': ['integer', 'null']},
    'failure_code': {'type': ['string', 'null'], 'enum': [None, 'native_nonzero_exit', 'local_job_resource_limit', 'local_job_execution_error']},
    'resource': {'type': ['string', 'null'], 'enum': [None, 'memory_bytes', 'scratch_bytes', 'file_bytes']},
    'progress_kind': {'type': 'string', 'enum': ['native_execution_state_and_output_bytes_not_search_fraction']},
    'outputs': {'type': 'array', 'items': _object({
        'role': {'type': 'string', 'enum': list(OUTPUTS)}, 'available': {'type': 'boolean'},
        'bytes': {'type': ['integer', 'null'], 'minimum': 0}, 'writer_closed': {'type': 'boolean'}})}})
