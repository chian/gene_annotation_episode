"""Original HMMER operation contracts, native status and receipt constants."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import identity
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.library.provider_jobs import validate_remote_identity

PROVIDER = 'episode.api_hmmer_handoff'
VERSION = 'api_hmmer_execution_v1'
HANDOFF_VERSION = 'api_hmmer_handoff_v1'
RESULT_DESCRIPTION = ('Acquire exactly the assigned HMMER result page from the original API handoff; '
    'retain native scores, domain alignments and separately defined numerical correspondence measurements.')


def _now():
    return datetime.now(timezone.utc).isoformat()


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


def hmmer_operation_catalog(role):
    """Declared contracts without an invented query, target or service call."""
    if role not in {'launch_api', 'results'}:
        raise ValueError('api_execution_role_required')
    descriptions = ({'api.hmmer.result': RESULT_DESCRIPTION}
        if role == 'results' else {
            'api.hmmer.databases': 'Read one current served database inventory; no job is selected or submitted.',
            'api.hmmer.prepare': 'Freeze the assigned query sequence, submitted FASTA and exact request identities.',
            'api.hmmer.submit': 'Commit intent and submit the original assigned search once; uncertain submissions never repeat.',
            'api.hmmer.status': 'Read the original submitted search with one status request.',
            'api.hmmer.check_handoff': 'Read one status response and validate a usable original monitoring/results handoff.'})
    return [{'name': name, 'description': description, 'input_schema': _object({})}
            for name, description in descriptions.items()]


def _envelope(key, *, status='completed', result=None, refs=(), feedback=None):
    return {'status': status, 'operation_ref': identity('api_operation', {'key': key}),
            'record_refs': list(refs), 'changed_record_refs': list(refs),
            'result': result, 'feedback': feedback}


def _native_status(snapshot, request, remote_id):
    try:
        native = json.loads(snapshot.content)
        canonical(native)  # Native projections must remain finite recorded JSON.
        task = native.get('task') if isinstance(native, dict) else None
        if (not isinstance(native, dict) or task is not None and
                (not isinstance(task, dict) or not isinstance(task.get('status', 'UNKNOWN'), str))):
            raise ValueError('status_object_required')
    except (ValueError, TypeError, UnicodeError) as error:
        raise AcquisitionError('provider_status_response_invalid', snapshot=snapshot,
                               phase='status_response') from error
    try:
        validate_remote_identity(native, request, remote_id)
    except AcquisitionError as error:
        error.snapshot = snapshot
        raise
    status = (task or {}).get('status', 'UNKNOWN')
    states = {'PENDING': 'submitted', 'RECEIVED': 'submitted', 'STARTED': 'running',
              'RETRY': 'running', 'SUCCESS': 'completed', 'FAILURE': 'failed', 'REVOKED': 'failed'}
    return native, status, states.get(status, 'unknown')


