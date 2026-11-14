"""Authenticate masking preparation and retain immutable selected facts.

Only bounded workers open full numerical payloads. Frozen-return validation
checks retained byte custody and original receipts without parsing, calculation,
native-path access, new acquisition or publication writes.
"""
from __future__ import annotations
import re
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_acquisition import _validate_retained_rows, original_source_payload, validate_native_blast_masking_capture
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_contracts import finite_json_copy, native_blast_digest, validate_original_bundle
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_result_worker import expected_outputs, qualified_masking_context, validate_worker_manifest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_hmmer_preparation_acquisition import _decode, _retained
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_sequence_masking_contracts import validate_sequence_masking_record as core
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_sequence_masking_result_views import PROJECTION_FIELDS, SAVED_SCHEMAS, unique_failures, validate_masking_projection, validate_masking_result_selector
PREFIX = 'native_blast_masking_'
PREPARED_VERSION = PREFIX + 'prepared_v1'
PUBLICATION_VERSION = PREFIX + 'publication_v1'
RETAINED_VERSION = PREFIX + 'retained_v1'
PROJECTION_VERSION = PREFIX + 'projection_artifact_v1'
RECEIPT_VERSION = PREFIX + 'worker_receipt_v1'
NUMERICAL_REFS = {'sheet': 'sheet_artifact_ref', 'calculations': 'calculations_artifact_ref', 'statistics': 'statistics_artifact_ref'}
_PREPARED_FIELDS = {'version', 'bundle_artifact_ref', 'source_grading_artifact_ref', *NUMERICAL_REFS.values(), 'operation', 'native_outcome', 'occurrences', 'failures', 'worker_completed'}
_STABLE_FIELDS = {'version', 'bundle', 'capture', 'original_plan', 'bundle_sha256', 'numerical_artifacts', 'worker_receipt_artifact_ref', *_PREPARED_FIELDS - {'version', 'source_grading_artifact_ref'}}
_PUBLICATION_FIELDS = {'version', 'source_ref', 'prepared_sha256', 'selector', 'projection_artifact_ref', *PROJECTION_FIELDS}

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

def validate_masking_prepared(prepared):
    """Validate only closed fields; Store-aware custody is a separate port."""
    prepared = finite_json_copy(prepared)
    _shape(prepared, _PREPARED_FIELDS, 'prepared_fields_invalid')
    if prepared['version'] != PREPARED_VERSION or type(prepared['worker_completed']) is not bool:
        _error('prepared_version_or_completion_invalid')
    _artifact_ref(prepared['bundle_artifact_ref'])
    for key in ('source_grading_artifact_ref', *NUMERICAL_REFS.values()):
        _artifact_ref(prepared[key], nullable=True)
    core('Operation', prepared['operation'])
    core('NativeOutcome', prepared['native_outcome'])
    if type(prepared['occurrences']) is not list:
        _error('prepared_occurrences_invalid')
    slots, ids = (set(), set())
    for row in prepared['occurrences']:
        core('Occurrence', row)
        slot = tuple((row[k] for k in ('direction', 'role', 'ordinal')))
        if slot in slots or row['occurrence_id'] in ids:
            _error('prepared_occurrence_duplicate')
        slots.add(slot)
        ids.add(row['occurrence_id'])
    unique_failures(prepared['failures'])
    if prepared['operation']['mode'] == 'create_counts' and any((prepared[k] is not None for k in ('sheet_artifact_ref', 'calculations_artifact_ref'))):
        _error('counts_have_no_mask_sheet')
    if prepared['operation']['program'] != 'windowmasker' and prepared['statistics_artifact_ref'] is not None:
        _error('prepared_unexpected_statistics')
    if prepared['calculations_artifact_ref'] is not None and prepared['sheet_artifact_ref'] is None:
        _error('prepared_calculations_without_sheet')
    return prepared

def _stable(store, prepared):
    if prepared['source_grading_artifact_ref'] is None:
        _error('prepared_source_grading_required')
    envelope = _json(store, prepared['source_grading_artifact_ref'])
    _shape(envelope, {'schema', 'provider', 'native_artifact_ref', 'grading'}, 'retained_envelope_invalid')
    if envelope['schema'] != 'tool_grading_artifact_v1' or envelope['provider'] != 'episode.execution_result' or envelope['native_artifact_ref'] != prepared['bundle_artifact_ref']:
        _error('retained_envelope_identity_conflict')
    stable = envelope['grading']
    _shape(stable, _STABLE_FIELDS, 'retained_grading_fields_invalid')
    if stable['version'] != RETAINED_VERSION:
        _error('retained_grading_version_invalid')
    for key in _PREPARED_FIELDS - {'version', 'source_grading_artifact_ref'}:
        if stable[key] != prepared[key]:
            _error('prepared_retained_identity_conflict')
    return stable

def _validate_receipt(store, reference, *, task):
    receipt = _json(store, reference)
    _shape(receipt, {'version', 'plan', 'returncode', 'manifest', 'outputs', 'failures', 'diagnostic_artifact_refs', 'exception'}, 'worker_receipt_fields_invalid')
    if receipt['version'] != RECEIPT_VERSION or receipt['plan'].get('task') != task:
        _error('worker_receipt_identity_conflict')
    if receipt['returncode'] is not None and type(receipt['returncode']) is not int:
        _error('worker_receipt_returncode_invalid')
    unique_failures(receipt['failures'])
    manifest = receipt['manifest']
    if manifest is not None:
        manifest = validate_worker_manifest(manifest, receipt['plan'])
    if type(receipt['outputs']) is not dict or (manifest is None and receipt['outputs']):
        _error('worker_receipt_outputs_invalid')
    for role, descriptor in receipt['outputs'].items():
        if manifest is None or role not in manifest['outputs'] or descriptor != _descriptor(store, descriptor['artifact_ref']):
            _error('worker_receipt_output_identity_conflict')
        native = manifest['outputs'][role]
        if any((descriptor[k] != native[k] for k in ('sha256', 'size_bytes'))):
            _error('worker_receipt_output_bytes_conflict')
    for reference in receipt['diagnostic_artifact_refs']:
        _descriptor(store, reference)
    return receipt

def validate_prepared_masking_result(store, prepared, *, bundle=None):
    """Authenticate original custody and small immutable receipts, without grading."""
    prepared = validate_masking_prepared(prepared)
    stable = _stable(store, prepared)
    retained_bundle = _json(store, prepared['bundle_artifact_ref'])
    if retained_bundle != stable['bundle'] or (bundle is not None and retained_bundle != finite_json_copy(bundle)):
        _error('prepared_bundle_identity_conflict')
    bundle = validate_original_bundle(retained_bundle, stable['original_plan'])
    capture = validate_native_blast_masking_capture(stable['capture'])
    if capture['bundle_artifact_ref'] != prepared['bundle_artifact_ref'] or stable['bundle_sha256'] != native_blast_digest(bundle):
        _error('prepared_capture_bundle_conflict')
    _validate_retained_rows(store, capture, stable['original_plan'], bundle)
    occurrences, outcome, original_failures = qualified_masking_context(bundle, capture)
    if prepared['operation'] != bundle['operation'] or prepared['native_outcome'] != outcome or prepared['occurrences'] != occurrences or any((f not in prepared['failures'] for f in original_failures)):
        _error('prepared_original_context_conflict')
    receipt = _validate_receipt(store, stable['worker_receipt_artifact_ref'], task='parse_calculate')
    plan = receipt['plan']
    if any((plan[k] != stable[k] for k in ('bundle', 'capture', 'original_plan', 'bundle_artifact_ref', 'occurrences', 'native_outcome'))) or plan['failures'] != original_failures:
        _error('prepared_worker_context_conflict')
    expected_files = [{'occurrence_id': r['occurrence_id'], **_file(store, r['artifact_ref'])} for r in occurrences if r['role'] not in {'stdout', 'stderr'}]
    if [{k: v for k, v in r.items() if k != 'path'} for r in plan['files']] != [{k: v for k, v in r.items() if k != 'path'} for r in expected_files]:
        _error('prepared_worker_input_identity_conflict')
    numerical = stable['numerical_artifacts']
    if numerical != receipt['outputs'] or prepared['failures'] != receipt['failures']:
        _error('prepared_worker_result_conflict')
    for role, key in NUMERICAL_REFS.items():
        descriptor = numerical.get(role)
        if prepared[key] != (descriptor['artifact_ref'] if descriptor else None):
            _error('prepared_numerical_artifact_conflict')
    completed = bool(receipt['returncode'] == 0 and receipt['manifest'] is not None and receipt['manifest']['completed'] and (set(numerical) == expected_outputs(plan)))
    if prepared['worker_completed'] != completed:
        _error('prepared_worker_completion_conflict')
    return prepared

def _source(store, source_ref, prepared, stable):
    source = store._require(source_ref, {'source'})
    expected = original_source_payload(bundle=stable['bundle'], capture=stable['capture'], prepared=prepared)
    if source.get('origin') != 'tool' or any((source.get(k) != v for k, v in expected.items())):
        _error('publication_source_custody_conflict')

def _saved_descriptors(store, source_ref, prepared):
    result = []
    for kind, key in (('sheet', 'sheet_artifact_ref'), ('calculations', 'calculations_artifact_ref'), ('parsed_statistics', 'statistics_artifact_ref')):
        if prepared[key] is not None:
            result.append({'source_ref': source_ref, 'kind': kind, **_descriptor(store, prepared[key]), 'schema': SAVED_SCHEMAS[kind]})
    return result

def _selector(prepared, selector):
    selector = validate_masking_result_selector(selector, operation=prepared['operation'])
    if selector['mode'] == 'saved_recalculation' and selector['saved_sheet_ref'] != prepared['sheet_artifact_ref']:
        _error('saved_sheet_original_reference_conflict')
    return selector

def validate_masking_publication(store, *, source_ref, prepared, selector, publication):
    """Validate immutable selected values only; never launch or recalculate."""
    prepared = validate_prepared_masking_result(store, prepared)
    stable, selector = (_stable(store, prepared), _selector(prepared, selector))
    _source(store, source_ref, prepared, stable)
    publication = finite_json_copy(publication)
    _shape(publication, _PUBLICATION_FIELDS, 'publication_fields_invalid')
    if publication['version'] != PUBLICATION_VERSION or publication['source_ref'] != source_ref or publication['selector'] != selector or (publication['prepared_sha256'] != native_blast_digest(prepared)):
        _error('publication_original_selection_conflict')
    envelope = _json(store, publication['projection_artifact_ref'])
    _shape(envelope, {'version', 'source_ref', 'prepared_sha256', 'selector', 'projection', 'worker_receipt_artifact_ref', 'selected_projection_artifact_ref', 'recalculations_artifact_ref'}, 'projection_envelope_invalid')
    if envelope['version'] != PROJECTION_VERSION or any((envelope[k] != publication[k] for k in ('source_ref', 'prepared_sha256', 'selector'))):
        _error('projection_envelope_identity_conflict')
    selected = validate_masking_projection(envelope['projection'], source_ref=source_ref, operation=prepared['operation'], selector=selector, occurrences=prepared['occurrences'])
    if any((publication[k] != selected[k] for k in PROJECTION_FIELDS)) or _json(store, envelope['selected_projection_artifact_ref']) != selected:
        _error('publication_frozen_values_conflict')
    if selected['status']['native_state'] != prepared['native_outcome']['state'] or selected['status']['output_complete'] != prepared['native_outcome']['output_complete']:
        _error('publication_native_outcome_conflict')
    available = {r['kind']: r for r in _saved_descriptors(store, source_ref, prepared)}
    if selected['saved_data'] != [available[k] for k in selector['saved_data'] if k in available]:
        _error('publication_saved_data_grant_conflict')
    receipt = _validate_receipt(store, envelope['worker_receipt_artifact_ref'], task='project_saved')
    plan = receipt['plan']
    if plan['source_ref'] != source_ref or plan['selector'] != selector or any((plan[k] != prepared[k] for k in ('operation', 'native_outcome', 'occurrences', 'failures'))) or (plan['saved_data'] != list(available.values())):
        _error('publication_worker_context_conflict')
    for role, key in NUMERICAL_REFS.items():
        descriptor = plan['files'][role]
        expected = _descriptor(store, prepared[key]) if prepared[key] is not None else None
        if (descriptor is None) != (expected is None) or (descriptor is not None and any((descriptor[k] != expected[k] for k in ('sha256', 'size_bytes')))):
            _error('publication_saved_input_conflict')
    if receipt['returncode'] != 0 or receipt['manifest'] is None or (not receipt['manifest']['completed']) or (set(receipt['outputs']) != expected_outputs(plan)) or (receipt['outputs']['projection']['artifact_ref'] != envelope['selected_projection_artifact_ref']) or (receipt['outputs'].get('recalculations', {}).get('artifact_ref') != envelope['recalculations_artifact_ref']):
        _error('publication_worker_result_conflict')
    return publication
