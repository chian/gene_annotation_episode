"""Retain original utility readings and authenticate frozen selected returns.

The original source record is never updated. Preparation and selection each have
one immutable worker receipt; an unfinished intent is not permission to rerun.
Saved validation authenticates hashes and those receipts without reopening native
paths, parsing native data, recalculating a payload, or starting a worker.
"""
from __future__ import annotations
import re
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_blast_utility_contracts import blast_utility_result_version_for_operation, validate_blast_utility_result, validate_blast_utility_record as core
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_blast_utility_result_views import PROJECTION_FIELDS, PROJECTION_V2_FIELDS, blast_utility_projection_fields, validate_blast_utility_projection, validate_blast_utility_result_selector
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_acquisition import _validate_saved
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_contracts import finite_json_copy, native_blast_digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_result_worker import qualified_utility_context, unique_failures, validate_context, validate_worker_manifest, validate_worker_plan
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_hmmer_preparation_acquisition import _decode, _retained
PREFIX = 'native_blast_utility_'
PREPARED_VERSION = PREFIX + 'prepared_v1'
PUBLICATION_VERSION = PREFIX + 'publication_v1'
PUBLICATION_V2_VERSION = PREFIX + 'publication_v2'
RETAINED_VERSION = PREFIX + 'retained_v1'
PROJECTION_VERSION = PREFIX + 'projection_artifact_v1'
PROJECTION_V2_VERSION = PREFIX + 'projection_artifact_v2'
RECEIPT_VERSION = PREFIX + 'worker_receipt_v1'
PAYLOAD_REFS = {'result': 'result_artifact_ref', 'prepared_database': 'prepared_database_projection_artifact_ref', 'prepared_manifest': 'prepared_database_manifest_artifact_ref'}
_PREPARED_FIELDS = {'version', 'source_ref', 'bundle_artifact_ref', 'source_grading_artifact_ref', 'operation', 'native_outcome', 'occurrences', 'failures', 'worker_completed', *PAYLOAD_REFS.values()}
_STABLE_FIELDS = {'version', 'capture', 'payload_artifacts', 'worker_receipt_artifact_ref', *_PREPARED_FIELDS - {'version', 'source_grading_artifact_ref'}}
_PUBLICATION_FIELDS = {'version', 'source_ref', 'prepared_sha256', 'selector', 'projection_artifact_ref', *PROJECTION_FIELDS}
_PUBLICATION_V2_FIELDS = {'version', 'source_ref', 'prepared_sha256', 'selector', 'projection_artifact_ref', *PROJECTION_V2_FIELDS}

def _vdb(operation):
    return operation['version'] == 'blast_utility_operation_v3'

def _error(code):
    raise ContractError(PREFIX + code)

def _shape(value, fields, code):
    if type(value) is not dict or set(value) != fields:
        _error(code)

def _artifact_ref(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or re.fullmatch('artifact_[0-9a-f]{64}', value) is None:
        _error('result_artifact_reference_invalid')

def _descriptor(store, reference):
    meta = _retained(store, reference)
    return {'artifact_ref': reference, 'sha256': meta['sha256'], 'size_bytes': meta['size']}

def _json(store, reference):
    _descriptor(store, reference)
    return _decode(store.get_artifact(reference))

def _file(store, reference):
    row = _descriptor(store, reference)
    return {'path': str(store.path / 'artifacts' / row['sha256'][:2] / row['sha256']), **{k: row[k] for k in ('sha256', 'size_bytes')}}

def validate_utility_prepared(prepared):
    """Closed structural validation; original custody uses the Store-aware port."""
    prepared = finite_json_copy(prepared)
    _shape(prepared, _PREPARED_FIELDS, 'prepared_fields_invalid')
    if prepared['version'] != PREPARED_VERSION or type(prepared['worker_completed']) is not bool or type(prepared['source_ref']) is not str or (not prepared['source_ref']):
        _error('prepared_version_or_source_invalid')
    _artifact_ref(prepared['bundle_artifact_ref'])
    _artifact_ref(prepared['source_grading_artifact_ref'])
    for key in PAYLOAD_REFS.values():
        _artifact_ref(prepared[key], nullable=True)
    core('Operation', prepared['operation'])
    core('NativeOutcome', prepared['native_outcome'])
    if type(prepared['occurrences']) is not list:
        _error('prepared_occurrences_invalid')
    rows = [core('ArtifactOccurrence', row) for row in prepared['occurrences']]
    ids = {r['occurrence_id'] for r in rows}
    if len(ids) != len(rows) or len({(r['direction'], r['role'], r['ordinal']) for r in rows}) != len(rows):
        _error('prepared_occurrences_duplicate')
    if unique_failures(prepared['failures']) != prepared['failures']:
        _error('prepared_duplicate_failures')
    if any((row['occurrence_id'] is not None and row['occurrence_id'] not in ids or (row['native_returncode'] is not None and row['native_returncode'] != prepared['native_outcome']['returncode']) for row in prepared['failures'])):
        _error('prepared_failure_context_conflict')
    projection, manifest = (prepared['prepared_database_projection_artifact_ref'], prepared['prepared_database_manifest_artifact_ref'])
    builder = blast_utility_result_version_for_operation(prepared['operation']) in {'blast_database_artifact_set_v1', 'blast_database_artifact_set_v2'}
    if projection is not None and (prepared['result_artifact_ref'] is None or not builder) or (manifest is not None and projection is None):
        _error('prepared_database_payload_conflict')
    return prepared

def _stable(store, prepared):
    envelope = _json(store, prepared['source_grading_artifact_ref'])
    _shape(envelope, {'schema', 'provider', 'native_artifact_ref', 'grading'}, 'retained_envelope_invalid')
    if envelope['schema'] != 'tool_grading_artifact_v1' or envelope['provider'] != 'episode.execution_result' or envelope['native_artifact_ref'] != prepared['bundle_artifact_ref']:
        _error('retained_envelope_identity_conflict')
    stable = envelope['grading']
    _shape(stable, _STABLE_FIELDS, 'retained_grading_fields_invalid')
    if stable['version'] != RETAINED_VERSION or any((stable[key] != prepared[key] for key in _PREPARED_FIELDS - {'version', 'source_grading_artifact_ref'})):
        _error('prepared_retained_identity_conflict')
    return stable

def _validate_receipt(store, reference, *, task):
    receipt = _json(store, reference)
    _shape(receipt, {'version', 'plan', 'returncode', 'manifest', 'outputs', 'failures', 'diagnostic_artifact_refs', 'exception'}, 'worker_receipt_fields_invalid')
    plan = validate_worker_plan(receipt['plan'])
    if receipt['version'] != RECEIPT_VERSION or plan['task'] != task:
        _error('worker_receipt_identity_conflict')
    if receipt['returncode'] is not None and type(receipt['returncode']) is not int:
        _error('worker_receipt_returncode_invalid')
    if unique_failures(receipt['failures']) != receipt['failures']:
        _error('worker_receipt_failures_invalid')
    if receipt['exception'] is not None and (type(receipt['exception']) is not dict or set(receipt['exception']) != {'exception_type', 'detail'} or any((type(v) is not str for v in receipt['exception'].values()))):
        _error('worker_receipt_exception_invalid')
    manifest = None if receipt['manifest'] is None else validate_worker_manifest(receipt['manifest'], plan)
    if type(receipt['outputs']) is not dict or (manifest is None and receipt['outputs']):
        _error('worker_receipt_outputs_invalid')
    for role, descriptor in receipt['outputs'].items():
        if manifest is None or role not in manifest['outputs'] or type(descriptor) is not dict or (set(descriptor) != {'artifact_ref', 'sha256', 'size_bytes'}) or (descriptor != _descriptor(store, descriptor['artifact_ref'])):
            _error('worker_receipt_output_identity_conflict')
        if any((descriptor[k] != manifest['outputs'][role][k] for k in ('sha256', 'size_bytes'))):
            _error('worker_receipt_output_bytes_conflict')
    if type(receipt['diagnostic_artifact_refs']) is not list or any((type(v) is not str for v in receipt['diagnostic_artifact_refs'])):
        _error('worker_receipt_diagnostics_invalid')
    for ref in receipt['diagnostic_artifact_refs']:
        _descriptor(store, ref)
    original = plan['context']['failures'] + ([] if manifest is None else manifest['failures'])
    if any((row not in receipt['failures'] for row in original)):
        _error('worker_receipt_original_failures_missing')
    return receipt

def _completed(receipt):
    return bool(receipt['returncode'] == 0 and receipt['manifest'] is not None and receipt['manifest']['completed'] and (set(receipt['outputs']) == set(receipt['manifest']['outputs'])) and (receipt['exception'] is None))

def _same_file_identity(left, right):
    return left is None and right is None or (left is not None and right is not None and all((left[k] == right[k] for k in ('sha256', 'size_bytes'))))

def validate_prepared_utility_result(store, prepared):
    """Validate retained custody and original receipts, never native data readers."""
    prepared = validate_utility_prepared(prepared)
    stable = _stable(store, prepared)
    capture = _validate_saved(store, stable['capture'])
    if capture['source_ref'] != prepared['source_ref'] or capture['bundle_artifact_ref'] != prepared['bundle_artifact_ref']:
        _error('prepared_original_capture_conflict')
    original = qualified_utility_context(capture)
    if any((prepared[k] != original[k] for k in ('operation', 'native_outcome', 'occurrences'))):
        _error('prepared_original_context_conflict')
    receipt = _validate_receipt(store, stable['worker_receipt_artifact_ref'], task='parse_original')
    plan = receipt['plan']
    if plan['capture'] != capture or plan['context'] != original:
        _error('prepared_worker_context_conflict')
    if not _same_file_identity(plan['bundle_file'], _file(store, prepared['bundle_artifact_ref'])):
        _error('prepared_worker_bundle_identity_conflict')
    expected = [{'occurrence_id': row['occurrence_id'], **_file(store, row['artifact_ref'])} for row in original['occurrences']]
    if [{k: v for k, v in row.items() if k != 'path'} for row in plan['files']] != [{k: v for k, v in row.items() if k != 'path'} for row in expected]:
        _error('prepared_worker_file_identity_conflict')
    if stable['payload_artifacts'] != receipt['outputs'] or prepared['failures'] != receipt['failures']:
        _error('prepared_worker_result_conflict')
    for role, key in PAYLOAD_REFS.items():
        if prepared[key] != receipt['outputs'].get(role, {}).get('artifact_ref'):
            _error('prepared_payload_artifact_conflict')
    if prepared['worker_completed'] != _completed(receipt):
        _error('prepared_worker_completion_conflict')
    if _vdb(prepared['operation']):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_vdb_utility_context import validate_vdb_context_authentication
        proof = None if receipt['manifest'] is None else receipt['manifest']['context_authentication']
        if proof is not None:
            validate_vdb_context_authentication(proof, capture=capture, context=original)
        if prepared['result_artifact_ref'] is not None:
            if proof is None:
                _error('prepared_vdb_context_authentication_required')
            result = validate_blast_utility_result(_json(store, prepared['result_artifact_ref']))
            if result['version'] != blast_utility_result_version_for_operation(original['operation']) or result['operation'] != original['operation'] or result['original_outcome'] != original['native_outcome'] or any((result[key] != original[key] for key in ('database_binding', 'operation_input_occurrences', 'vdb_context'))):
                _error('prepared_vdb_result_context_conflict')
            known = {row['occurrence_id']: row for row in original['occurrences']}
            if any((row is not None and known.get(row['occurrence_id']) != row for row in (result['output_occurrence'], result['stderr_occurrence']))):
                _error('prepared_vdb_result_occurrence_conflict')
    return prepared

def _projection_context(prepared, stable):
    original = qualified_utility_context(stable['capture'])
    if _vdb(prepared['operation']) and prepared['result_artifact_ref'] is not None:
        return original
    return validate_context({**original, 'failures': prepared['failures']})

def _projection_authentication(store, prepared, stable):
    """Copy the original proof after prepared-result custody validation."""
    if prepared['result_artifact_ref'] is None:
        return None
    receipt = _validate_receipt(store, stable['worker_receipt_artifact_ref'], task='parse_original')
    proof = receipt['manifest']['context_authentication']
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_vdb_utility_context import validate_vdb_context_authentication
    return validate_vdb_context_authentication(proof, capture=stable['capture'], context=qualified_utility_context(stable['capture']))

def _saved_descriptors(store, prepared):
    result = []
    for kind, key in (('result', 'result_artifact_ref'), ('prepared_database', 'prepared_database_manifest_artifact_ref')):
        if prepared[key] is not None:
            payload = _json(store, prepared[key])
            schema = payload.get('version') if type(payload) is dict else None
            expected = {blast_utility_result_version_for_operation(prepared['operation'])} if kind == 'result' else {'native_blast_standard_prepared_database_manifest_v1', 'native_blast_prepared_database_manifest_v1'}
            if schema not in expected:
                _error('saved_payload_version_conflict')
            result.append({'source_ref': prepared['source_ref'], 'kind': kind, **_descriptor(store, prepared[key]), 'schema': schema})
    return result

def _source(source_ref, prepared):
    if source_ref != prepared['source_ref']:
        _error('publication_original_source_conflict')

def validate_utility_publication(store, *, source_ref, prepared, selector, publication):
    """Validate frozen values and grants; do not invoke a worker or result reader."""
    prepared = validate_prepared_utility_result(store, prepared)
    _source(source_ref, prepared)
    stable = _stable(store, prepared)
    selector = validate_blast_utility_result_selector(selector, operation=prepared['operation'])
    vdb = _vdb(prepared['operation'])
    projection_fields = blast_utility_projection_fields(selector)
    context = _projection_context(prepared, stable)
    publication = finite_json_copy(publication)
    _shape(publication, _PUBLICATION_V2_FIELDS if vdb else _PUBLICATION_FIELDS, 'publication_fields_invalid')
    if publication['version'] != (PUBLICATION_V2_VERSION if vdb else PUBLICATION_VERSION) or publication['source_ref'] != source_ref or publication['selector'] != selector or (publication['prepared_sha256'] != native_blast_digest(prepared)):
        _error('publication_original_selection_conflict')
    envelope = _json(store, publication['projection_artifact_ref'])
    _shape(envelope, {'version', 'source_ref', 'prepared_sha256', 'selector', 'projection', 'worker_receipt_artifact_ref', 'selected_projection_artifact_ref'}, 'projection_envelope_invalid')
    if envelope['version'] != (PROJECTION_V2_VERSION if vdb else PROJECTION_VERSION) or any((envelope[k] != publication[k] for k in ('source_ref', 'prepared_sha256', 'selector'))):
        _error('projection_envelope_identity_conflict')
    selected = validate_blast_utility_projection(envelope['projection'], source_ref=source_ref, operation=prepared['operation'], native_outcome=prepared['native_outcome'], selector=selector, occurrences=prepared['occurrences'], **{'context': context} if vdb else {})
    if any((publication[k] != selected[k] for k in projection_fields)) or _json(store, envelope['selected_projection_artifact_ref']) != selected:
        _error('publication_frozen_values_conflict')
    available = _saved_descriptors(store, prepared)
    by_kind = {row['kind']: row for row in available}
    if selected['saved_data'] != [by_kind[k] for k in selector['saved_data'] if k in by_kind]:
        _error('publication_saved_data_grant_conflict')
    receipt = _validate_receipt(store, envelope['worker_receipt_artifact_ref'], task='project_saved')
    plan = receipt['plan']
    if plan['source_ref'] != source_ref or plan['selector'] != selector or plan['saved_data'] != available or (plan['context'] != context):
        _error('publication_worker_context_conflict')
    if vdb:
        proof = _projection_authentication(store, prepared, stable)
        if receipt['manifest'] is None or plan['context_authentication'] != proof or receipt['manifest']['context_authentication'] != proof:
            _error('publication_vdb_context_authentication_conflict')
    for role, key in PAYLOAD_REFS.items():
        expected = None if prepared[key] is None else _file(store, prepared[key])
        if not _same_file_identity(plan['files'][role], expected):
            _error('publication_saved_input_conflict')
    if not _completed(receipt) or receipt['outputs']['projection']['artifact_ref'] != envelope['selected_projection_artifact_ref']:
        _error('publication_worker_result_conflict')
    return publication
