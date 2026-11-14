from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_search as blast
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.api_services import object_schema, validate_service_configuration, validate_value
TEXT = {'type': 'string', 'minLength': 1}
EMPTY = object_schema({})

def blast_wait_forecast(handle, observed_at, state):
    """BLAST-only scheduling estimate as of an explicit evaluation time.

    A saved WAITING reply establishes only that the RID was unfinished at its
    observation time. An owner may reevaluate the unresolved job's planning
    estimate later without another NCBI request. The provisional curve passes
    through one minute remaining after two minutes and ten minutes remaining
    after ten minutes. It is neither scientific credit nor a provider promise.
    """
    submitted = handle.get('submitted_at')
    if submitted is None:
        return {'method': 'unavailable_original_submission_time', 'elapsed_since_submission_seconds': None, 'estimated_remaining_seconds': None}
    start = datetime.fromisoformat(submitted.replace('Z', '+00:00'))
    observed = datetime.fromisoformat(observed_at.replace('Z', '+00:00'))
    if start.tzinfo is None or observed.tzinfo is None or start.utcoffset() != timezone.utc.utcoffset(start) or (observed.utcoffset() != timezone.utc.utcoffset(observed)):
        raise ValueError('blast_wait_utc_time_required')
    elapsed = max(0.0, (observed - start).total_seconds())
    if state == 'READY':
        remaining = 0.0
    elif state in {'WAITING', 'accepted'}:
        exponent = 1.430676558073393
        remaining = max(0.0, float(handle['rtoe_seconds']) - elapsed, 60.0 * (elapsed / 120.0) ** exponent)
    else:
        remaining = None
    return {'method': 'blast_unresolved_elapsed_provisional_v1', 'elapsed_since_submission_seconds': elapsed, 'estimated_remaining_seconds': remaining}

class NCBIBlastService:
    service = 'ncbi_blast'
    request_schema = object_schema({'subject_ref': TEXT, 'program': {'enum': list(blast.PROGRAM_UNITS)}, 'database': TEXT, 'hitlist_size': {'type': 'integer', 'minimum': 1}}, ['subject_ref', 'program', 'database'])
    selector_schema = EMPTY

    def __init__(self, tool_registry, configuration=None, *, client=None):
        self.configuration = validate_service_configuration(self.service, configuration or {})
        self.tools = tool_registry
        self.client = client if client is not None else tool_registry.clients

    def validate_request(self, request, scope):
        request = validate_value(request, self.request_schema, 'blast_request_invalid')
        if not request['database'].strip():
            raise ValueError('blast_database_required')
        if scope is not None:
            self._operand(request, scope)
        return request

    def _operand(self, request, scope):
        row = self.tools._check_sequence_operand(request['subject_ref'], scope)
        model = 'protein' if blast.PROGRAM_UNITS[request['program']][0] == 'aa' else 'dna'
        sequence = self.tools._sequence(row['id'], molecule_model=model)
        return (row['id'], sequence)

    @staticmethod
    def _handle(handle):
        if not isinstance(handle, dict) or not isinstance(handle.get('rid'), str) or re.fullmatch('[A-Za-z0-9_-]+', handle['rid']) is None:
            raise ValueError('blast_original_handle_required')
        return dict(handle)

    def result_catalog(self, request, selector):
        self.validate_request(request, None)
        validate_value(selector or {}, EMPTY, 'blast_result_selector_must_be_empty')
        return self.result_capabilities()

    @staticmethod
    def result_capabilities():
        """Native result contracts, independent of a submitted query."""
        return [{'name': 'api.blast.status', 'description': 'Observe the original RID once to decide whether result retrieval is useful. This response supplies protocol status, not scientific result rows.', 'input_schema': EMPTY}, {'name': 'api.blast.fetch', 'description': 'Fetch one native JSON2 result response for the original RID. Preserve all native HSP scores and subjects; this does not assign function or poll for readiness.', 'input_schema': EMPTY}]

    def prepare(self, name, request, arguments, *, scope, previous_events, handle=None, selector=None):
        request = self.validate_request(request, scope)
        validate_value(arguments, EMPTY, 'blast_operation_arguments_invalid')
        validate_value(selector or {}, EMPTY, 'blast_result_selector_must_be_empty')
        operation = name.removeprefix('api.blast.')
        if name != 'api.blast.' + operation or operation not in {'prepare', 'submit', 'status', 'fetch'}:
            raise ValueError('blast_operation_not_available')
        subject, sequence = self._operand(request, scope)
        native = {'program': request['program'], 'database': request['database'], 'hitlist_size': request.get('hitlist_size', 50)}
        if operation in {'prepare', 'submit'}:
            native['query_fasta'] = f'>{subject}\n{sequence}'
        if operation == 'submit' and any((row.get('name') == 'api.blast.submit' and (row.get('event', {}).get('native_handle') or {}).get('rid') for row in previous_events)):
            raise ValueError('blast_original_submission_already_recorded')
        if operation in {'status', 'fetch'}:
            handle = self._handle(handle)
            native['rid'] = handle['rid']
            for row in previous_events:
                previous = row.get('event', {}).get('native_handle') or {}
                if previous.get('rid') and previous['rid'] != handle['rid']:
                    raise ValueError('blast_original_handle_conflict')
        return {'operation': name, 'mutates_remote': operation == 'submit', 'request': request, 'native_operation': operation, 'native_arguments': native, 'query_length': len(sequence), 'sequence_sha256': hashlib.sha256(sequence.encode()).hexdigest(), 'native_handle': handle if operation in {'status', 'fetch'} else None}
