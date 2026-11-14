from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, identity, validate_schema
from gene_annotation_episode.episodic_workflow.root.a110.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_acquisition import _attempt, _decode, _retained, _source_payload, _validate_capture
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_contracts import validate_native_blast_database_bundle
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_result_views import native_blast_database_fact_sources, project_native_blast_database_rows, validate_native_blast_database_result_selector, FUNCTION_SELECTOR, saved_function_descriptor
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_result_worker import native_blast_database_calculation_identity, native_blast_database_input_identity, _FUNCTION_REQUEST, _FUNCTION_MANIFEST, _FUNCTION_SHEETS, _FUNCTION_CALCULATIONS
PREPARATION_VERSION = 'native_blast_database_preparation_v1'
PUBLICATION_VERSION = 'native_blast_database_publication_v1'
_ARTIFACT_FIELDS = {'collection': 'collection_artifact_ref', 'sheets': 'sheets_artifact_ref', 'calculations': 'calculations_artifact_ref', 'rows': 'full_rows_artifact_ref', 'row_index': 'row_index_artifact_ref', 'diagnostics': 'diagnostics_artifact_ref'}
_ROLES_V1 = {'inputs': ('inputs.json', 'native_blast_database_prepared_inputs_v1'), 'collection': ('collection.json', 'blast_report_collection_v1'), 'sheets': ('sheets.json', 'native_blast_database_sheet_set_v1'), 'calculations': ('calculations.json', 'native_blast_database_calculations_v1'), 'rows': ('rows.ndjson', 'native_blast_database_numeric_row_v1'), 'row_index': ('row-index.json', 'native_blast_database_row_index_v1'), 'metric_definitions': ('metric-definitions.json', 'native_blast_database_metric_definitions_v1'), 'diagnostics': ('diagnostics.json', 'native_blast_database_diagnostics_v1')}
_ROLES_V2 = {**_ROLES_V1, 'sheets': ('sheets.json', 'native_blast_database_sheet_set_v2'), 'native_convergence': ('native-convergence.json', 'blast_native_convergence_extraction_v1')}
_MANIFEST_ROLES = {'native_blast_database_result_worker_manifest_v1': _ROLES_V1, 'native_blast_database_result_worker_manifest_v2': _ROLES_V2, _FUNCTION_MANIFEST: {**_ROLES_V1, 'sheets': ('sheets.json', _FUNCTION_SHEETS), 'calculations': ('calculations.json', _FUNCTION_CALCULATIONS), 'rows': ('rows.ndjson', 'native_blast_vdb_function_numeric_row_v1')}}

def _failure(stage, code, detail_code, **fields):
    return dict(stage=stage, code=code, artifact_key=None, input_key=None, search_key=None, record_key=None, pointer='', detail_code=detail_code) | fields

def _json(store, reference):
    return _decode(_retained(store, reference).read_bytes())

def _known(store, context):
    """Use the existing frozen receipt prefix; Store presence grants no authority."""
    EpisodeReturnRecords(store, context.run_id, failure_prefix='native_blast_database_input_').authenticate(context, allow_unsaved=True)
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_receipt_inheritance'").fetchone():
        return set()
    if not store.db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)).fetchone():
        return set()
    receipts = EpisodeReceipts.__new__(EpisodeReceipts)
    receipts.store, receipts.db, receipts.run_id = (store, store.db, context.run_id)
    return set(receipts.known(context.episode_id))

def _selected_input_refs(selector):
    references = [r['artifact_ref'] for r in selector['metadata_inputs']]
    references += [ref for r in selector['retained_sources'] for ref in (r['source_ref'], r['artifact_ref'])]
    selected = selector.get('calculation_input', {})
    if selected.get('mode') == 'saved_function_sheet':
        references += [selected[k + '_artifact_ref'] for k in ('manifest', 'sheets', 'collection')]
        references.append(selected['original_result_receipt']['source_ref'])
    return list(dict.fromkeys(references))

def validate_selected_inputs(store, context, selector, *, handoff_ref=None):
    known = _known(store, context)
    if handoff_ref is not None and handoff_ref not in known:
        raise ContractError('native_blast_database_original_handoff_not_received')
    if not set(_selected_input_refs(selector)) <= known:
        raise ContractError('native_blast_database_selected_input_not_received')
    for row in [*selector['metadata_inputs'], *selector['retained_sources']]:
        _retained(store, row['artifact_ref'], sha256=row['sha256'], size_bytes=row['size_bytes'])
    for row in selector['retained_sources']:
        source = store.get(row['source_ref'])
        if source.get('record_type') != 'source' or source.get('artifact_ref') != row['artifact_ref']:
            raise ContractError('native_blast_database_selected_source_artifact_conflict')
    selected = selector.get('calculation_input', {})
    if selected.get('mode') == 'saved_function_sheet':
        for role in ('manifest', 'sheets', 'collection'):
            _retained(store, selected[role + '_artifact_ref'], sha256=selected[role + '_sha256'])
    return _selected_input_refs(selector)

def _original_commission(store, context):
    """Read the original parent selection through existing episode records."""
    from gene_annotation_episode.episodic_workflow.root.a110.method_loop.identities import EpisodeRef
    authority = EpisodeReturnRecords(store, context.run_id, failure_prefix='native_blast_database_preparation_')
    authority.authenticate(context)
    if context.role != 'results' or len(context.path) < 2:
        raise ContractError('native_blast_database_original_results_commission_required')
    parent = authority.context(EpisodeRef(context.run_id, context.path[:-1]).episode_id)
    label = context.path[-1][1]
    index = label.removeprefix('child_')
    if not label.startswith('child_') or not index.isdecimal() or str(int(index)) != index:
        raise ContractError('native_blast_database_original_results_commission_required')
    row = store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (context.run_id, parent.episode_id, int(index))).fetchone()
    selected = {} if row is None else json.loads(row['action'])
    contract = plain(context.request)['report_contract']
    if selected.get('kind') != 'episode_child' or selected.get('role') != 'results' or selected.get('assignment') != plain(context.assignment) or (selected.get('scope') != plain(context.scope)) or (selected.get('purpose') != contract['decision']) or (_decode(selected.get('schema_json', '{}')) != contract['measurements']['schema']):
        raise ContractError('native_blast_database_original_results_commission_conflict')
    store.validate_scope(plain(context.scope), parent_scope=plain(parent.scope))

def _original_handoff(store, context, target, attempt):
    from gene_annotation_episode.episodic_workflow.root.a110.practical_receipt_information import PracticalReceiptInformation
    if target['handle'] != plain(context.assignment)['handoff_ref'] or target['handle'] not in _known(store, context):
        raise ContractError('native_blast_database_original_handoff_not_received')
    body = PracticalReceiptInformation(store, context.run_id).read(target['handle'], context.scope)
    snapshot = _json(store, store.get(target['handle'])['request_ref'])
    assignment, receipt = (snapshot['assignment'], body['receipt'])
    detail = receipt['outcome']['native_outcome']
    if receipt['tool_name'] == 'exec_command':
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_database_terminal_custody import qualify_manifest
        manifest = assignment.get('scientific_manifest')
        if manifest is None or target['assignment'] != assignment or target['origin_episode_id'] != body['episode_id']:
            raise ContractError('native_blast_database_original_handoff_conflict')
        raw = store.get_artifact('artifact_' + manifest['sha256'])
        witness = qualify_manifest(target, receipt, raw)
        if witness['authenticated_attempt'] != attempt:
            raise ContractError('native_blast_database_original_handoff_conflict')
        return
    expected = dict(version='execution_target_v1', handle=target['handle'], run_id=context.run_id, resource_id=assignment['resource_id'], resource_kind='hpc', execution_id=detail['pbs_job_id'], request_sha256=digest(assignment['requested_job']), origin_episode_id=body['episode_id'], assignment=assignment, scope=body['scope'])
    if target != expected or detail['attempt_id'] != attempt['identity']['attempt_id'] or detail['attempt_operation_key'] != attempt['identity']['operation_key'] or (detail['native_blast_database_plan_sha256'] != attempt['plan_sha256']) or (detail['native_blast_database_plan_path'] != str(Path(attempt['attempt_directory']) / 'native-blast-database-plan.json')):
        raise ContractError('native_blast_database_original_handoff_conflict')

def _metadata_descriptors(bundle, capture, selector):
    job = bundle['requested_job']['native_blast_database']
    byinput = {r['input_key']: r for r in bundle['artifacts'] if r['input_key'] is not None}
    selected_inputs = {r['input_key']: r for r in job['inputs']}
    descriptors = []
    for descriptor in job['metadata_inputs']:
        item = byinput.get(descriptor['input_key'])
        original = selected_inputs[descriptor['input_key']]
        sha = original['sha256'] if item is None else item['sha256']
        size = original['size_bytes'] if item is None else item['size_bytes']
        ref = None if item is None else capture['artifact_refs'].get(item['artifact_key'])
        descriptors.append(dict(**descriptor, artifact_ref=ref or 'artifact_' + sha, sha256=sha, size_bytes=size, origin='original_job_input'))
    descriptors += [dict(**row, origin='selected_results_input') for row in selector['metadata_inputs']]
    return descriptors

def _retained_catalog(store, selector, artifacts, snapshots):
    retained = [dict(**row, path=str(_retained(store, row['artifact_ref']))) for row in selector['retained_sources']]
    present = {r['artifact_ref'] for r in artifacts + retained}
    for row in selector['metadata_inputs']:
        if row['artifact_ref'] not in present:
            retained.append(dict(source_ref=row['artifact_ref'], **{k: row[k] for k in ('artifact_ref', 'sha256', 'size_bytes')}, path=str(_retained(store, row['artifact_ref']))))
            present.add(row['artifact_ref'])
    for row in snapshots:
        if row['sequence_artifact_ref'] not in present:
            retained.append(dict(source_ref=row['sequence_artifact_ref'], artifact_ref=row['sequence_artifact_ref'], sha256=row['sequence_sha256'], size_bytes=row['length'], path=row['sequence_path']))
            present.add(row['sequence_artifact_ref'])
    return retained

def _manifest(store, reference, request, artifact_refs):
    value = _json(store, reference)
    expected = {'version', 'calculation_id', 'request_sha256', 'status', 'input_identity', 'input_interpretation_id', 'input_implementation_sha256', 'implementation_manifest_sha256', 'sequence_model', 'artifacts', 'counts', 'failures'}
    function_mode = request['version'] == _FUNCTION_REQUEST
    if function_mode:
        expected.add('vdb_function_model')
    if type(value) is not dict or set(value) != expected or value['version'] not in _MANIFEST_ROLES or (function_mode != (value['version'] == _FUNCTION_MANIFEST)) or (function_mode and (request['bundle']['program'] not in {'blastn_vdb', 'tblastn_vdb'} or value['vdb_function_model'] != request['vdb_function_model'])) or (value['version'] == 'native_blast_database_result_worker_manifest_v2' and request['bundle']['program'] not in {'psiblast', 'deltablast'}) or (value['status'] not in {'complete', 'partial', 'failed'}) or (value['calculation_id'] != request['calculation_id']) or (value['request_sha256'] != hashlib.sha256((canonical(request) + '\n').encode('utf-8')).hexdigest()) or (value['input_identity'] != native_blast_database_input_identity(request)) or (value['implementation_manifest_sha256'] != request['implementation']['manifest_sha256']) or (value['sequence_model'] != request['sequence_model']) or (type(value['counts']) is not dict) or (set(value['counts']) != {'searches', 'native_hsp_slots', 'numerical_rows'}) or any((type(n) is not int or n < 0 for n in value['counts'].values())) or (type(value['artifacts']) is not list):
        raise ContractError('native_blast_database_worker_manifest_invalid')
    ids = native_blast_database_calculation_identity(input_identity=value['input_identity'], input_implementation_sha256=value['input_implementation_sha256'], sequence_model=value['sequence_model'], implementation_manifest_sha256=value['implementation_manifest_sha256'], vdb_function_model=value.get('vdb_function_model'))
    if any((value[k] != v for k, v in ids.items())):
        raise ContractError('native_blast_database_worker_manifest_identity_conflict')
    roles, seen = (_MANIFEST_ROLES[value['version']], set())
    for row in value['artifacts']:
        role = row['role']
        if set(row) != {'role', 'relative_path', 'sha256', 'size_bytes', 'schema'} or role not in roles or role in seen or ((row['relative_path'], row['schema']) != roles[role]) or (role not in artifact_refs):
            raise ContractError('native_blast_database_worker_artifact_manifest_conflict')
        seen.add(role)
        _retained(store, artifact_refs[role], sha256=row['sha256'], size_bytes=row['size_bytes'])
    if seen != set(artifact_refs):
        raise ContractError('native_blast_database_worker_artifact_manifest_conflict')
    if value['status'] != 'failed' and (not set(_ROLES_V1) <= seen):
        raise ContractError('native_blast_database_worker_artifact_manifest_incomplete')
    if 'sheets' in artifact_refs:
        sheets = _json(store, artifact_refs['sheets'])
        if sheets.get('schema') != roles['sheets'][1]:
            raise ContractError('native_blast_database_frozen_sheet_schema_conflict')
        if value['version'] == 'native_blast_database_result_worker_manifest_v2':
            _frozen_convergence(store, request, sheets, artifact_refs)
        elif 'native_convergence' in sheets:
            raise ContractError('native_blast_database_frozen_sheet_schema_conflict')
    elif 'native_convergence' in artifact_refs:
        extraction = _json(store, artifact_refs['native_convergence'])
        if value['status'] != 'failed' or extraction.get('schema') != _ROLES_V2['native_convergence'][1] or extraction.get('source_context') != dict(original_job=request['bundle']['requested_job']['native_blast_database'], bundle=request['bundle'], attempt_identity=request['authenticated_attempt']):
            raise ContractError('native_blast_database_frozen_convergence_conflict')
    validate_schema(value['failures'], native_blast_database_fact_sources()['execution_blast_database_failures']['report_schema'])
    return value

def _frozen_convergence(store, request, sheets, artifact_refs):
    """Check saved binding and exact extraction bytes without interpreting them."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_convergence import validate_native_blast_database_convergence_binding
    if 'collection' not in artifact_refs:
        raise ContractError('native_blast_database_frozen_convergence_conflict')
    collection = _json(store, artifact_refs['collection'])
    if sheets['collection'] != collection:
        raise ContractError('native_blast_database_frozen_convergence_conflict')
    binding = validate_native_blast_database_convergence_binding(sheets['native_convergence'], collection=collection)
    if binding['source_context'] != dict(original_job=request['bundle']['requested_job']['native_blast_database'], bundle=request['bundle'], attempt_identity=request['authenticated_attempt']):
        raise ContractError('native_blast_database_frozen_convergence_conflict')
    reference = artifact_refs.get('native_convergence')
    if (binding['extraction'] is not None) != (reference is not None):
        raise ContractError('native_blast_database_frozen_convergence_artifact_missing')
    if reference is not None:
        expected = binding['extraction_artifact']
        if reference != expected['artifact_ref']:
            raise ContractError('native_blast_database_frozen_convergence_artifact_identity_conflict')
        path = _retained(store, reference, sha256=expected['sha256'], size_bytes=expected['size_bytes'])
        if path.read_bytes() != (canonical(binding['extraction']) + '\n').encode('utf-8'):
            raise ContractError('native_blast_database_frozen_convergence_artifact_conflict')

def _preparation_failures(manifest, caller_failure, capture):
    failures = [] if manifest is None else deepcopy(manifest['failures'])
    if caller_failure is not None:
        failures.append(deepcopy(caller_failure))
    for index, failure in enumerate(capture['failures']):
        failures.append(_failure('capture', 'native_blast_database_capture_incomplete', 'artifact_digest_conflict' if failure['code'] in {'file_digest_mismatch', 'file_changed'} else 'artifact_bytes_unavailable', artifact_key=failure['artifact_key'], pointer='/capture/failures/' + str(index)))
    status = 'failed' if manifest is None or manifest['status'] == 'failed' else 'partial' if failures else manifest['status']
    return (failures, status)

def saved_function_input_descriptor(store, body):
    """Describe one already validated sealed generation, never choose a receipt."""
    prepared, publication = (body['preparation'], body['publication'])
    if prepared is None or publication is None or prepared['worker_manifest_artifact_ref'] is None:
        raise ContractError('native_blast_database_saved_function_input_unavailable')
    manifest = _json(store, prepared['worker_manifest_artifact_ref'])
    if manifest.get('version') != _FUNCTION_MANIFEST or manifest['status'] == 'failed':
        raise ContractError('native_blast_database_sheet_invalid')
    value = dict(schema='native_blast_vdb_function_saved_input_v1', original_result_receipt=dict(source_ref=publication['source_ref'], run_id=body['run_id'], episode_id=body['episode_id'], operation_key=body['operation_key'], receipt_sha256=digest(body)), input_interpretation_id=manifest['input_interpretation_id'], original_calculation_id=manifest['calculation_id'])
    for role, field in (('manifest', 'worker_manifest_artifact_ref'), ('sheets', 'sheets_artifact_ref'), ('collection', 'collection_artifact_ref')):
        ref = prepared[field]
        record = store.get(ref)
        path = _retained(store, ref)
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ContractError('native_blast_database_frozen_artifact_changed')
        value[role + '_artifact_ref'], value[role + '_sha256'] = (ref, record['sha256'])
    return value

def _saved_original(store, context, target, selector, body, *, seen=()):
    """Check exact recorded action and selected generation; no source lookup."""
    descriptor = saved_function_descriptor(selector['calculation_input'])
    address = descriptor['original_result_receipt']
    key = (address['run_id'], address['episode_id'], address['operation_key'])
    if key in seen or body.get('version') != 'native_blast_database_result_receipt_vdb_function_v1':
        raise ContractError('native_blast_database_return_unauthorized')
    authority = EpisodeReturnRecords(store, context.run_id, failure_prefix='native_blast_database_return_')
    original = authority.context(address['episode_id'])
    prefix = f'{context.run_id}:{original.episode_id}:'
    index = address['operation_key'].removeprefix(prefix)
    if address['run_id'] != context.run_id or not address['operation_key'].startswith(prefix) or (not index.isdecimal()) or (str(int(index)) != index):
        raise ContractError('native_blast_database_return_unauthorized')
    action = store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (context.run_id, original.episode_id, int(index))).fetchone()
    outcome = None if action is None or action['result'] is None else json.loads(action['result'])
    if outcome is None or outcome.get('status') != 'completed' or outcome.get('result') != body or (outcome.get('record_refs') != body['record_refs']) or (body['target'] != target) or (body['run_id'] != address['run_id']) or (body['episode_id'] != address['episode_id']) or (body['operation_key'] != address['operation_key']) or (digest(body) != address['receipt_sha256']) or (json.loads(action['action']) != dict(kind='tool', tool=body['tool_name'], arguments=body['arguments'])) or (body['assignment'] != plain(original.assignment)) or (body['scope'] != plain(original.scope)) or (address['source_ref'] not in body['record_refs']):
        raise ContractError('native_blast_database_return_unauthorized')
    store.validate_scope(body['scope'], parent_scope=plain(context.scope))
    frozen = _validate_preparation(store, original, body['preparation'], _seen=(*seen, key))
    if saved_function_input_descriptor(store, body) != descriptor:
        raise ContractError('native_blast_database_return_unauthorized')
    return frozen

def _validate_preparation(store, context, preparation, *, _seen=()):
    expected = {'version', 'calculation_id', 'bundle_artifact_ref', 'capture_artifact_ref', 'worker_manifest_artifact_ref', 'source_grading_artifact_ref', 'status', 'failures', *_ARTIFACT_FIELDS.values()}
    selected = plain(context.assignment)['selector']
    function_mode = selected['version'] == FUNCTION_SELECTOR
    saved_mode = function_mode and selected['calculation_input']['mode'] == 'saved_function_sheet'
    if function_mode:
        expected.update(('calculation_input', 'reused_result_receipt'))
    if type(preparation) is not dict or set(preparation) != expected or preparation['version'] != PREPARATION_VERSION:
        raise ContractError('native_blast_database_preparation_invalid')
    _original_commission(store, context)
    envelope = _json(store, preparation['source_grading_artifact_ref'])
    if envelope.get('schema') != 'tool_grading_artifact_v1' or envelope.get('provider') != 'episode.execution_result' or envelope.get('native_artifact_ref') != preparation['bundle_artifact_ref']:
        raise ContractError('native_blast_database_grading_custody_conflict')
    grading = envelope['grading']
    intent = _json(store, grading['intent_artifact_ref'])
    if intent['run_id'] != context.run_id or intent['episode_id'] != context.episode_id or intent['scope'] != plain(context.scope) or (intent['assignment'] != plain(context.assignment)):
        raise ContractError('native_blast_database_preparation_owner_conflict')
    capture = _json(store, preparation['capture_artifact_ref'])
    if not saved_mode and capture != intent['capture'] or grading['capture_artifact_ref'] != preparation['capture_artifact_ref']:
        raise ContractError('native_blast_database_preparation_capture_conflict')
    original_frozen = None
    if function_mode:
        if any((preparation[k] != intent[k] for k in ('calculation_input', 'reused_result_receipt'))) or preparation['calculation_input'] != selected['calculation_input']:
            raise ContractError('native_blast_database_preparation_owner_conflict')
        if preparation['reused_result_receipt'] != selected['calculation_input'].get('original_result_receipt'):
            raise ContractError('native_blast_database_return_unauthorized')
    if saved_mode:
        original_frozen = _saved_original(store, context, intent['target'], selected, _json(store, grading['original_receipt_artifact_ref']), seen=_seen)
        if intent['capture'] is not None or grading['observation_artifact_ref'] is not None or capture != original_frozen['capture']:
            raise ContractError('native_blast_database_preparation_capture_conflict')
    _validate_capture(store, capture, target=intent['target'])
    witness = _json(store, grading['authenticated_attempt_artifact_ref'])
    attempt = _attempt(intent['target'], witness)
    _original_handoff(store, context, intent['target'], attempt)
    bundle = validate_native_blast_database_bundle(_json(store, preparation['bundle_artifact_ref']), original_job=intent['target']['assignment']['requested_job']['native_blast_database'], attempt_identity=attempt)
    plan = _json(store, capture['plan_artifact_ref'])
    if bundle['plan'] != plan or digest(plan) != attempt['plan_sha256']:
        raise ContractError('native_blast_database_frozen_plan_conflict')
    bykey = {r['artifact_key']: r for r in bundle['artifacts']}
    if capture['status'] == 'complete' and set(capture['artifact_refs']) != set(bykey):
        raise ContractError('native_blast_database_frozen_capture_completeness_conflict')
    for key, ref in capture['artifact_refs'].items():
        _retained(store, ref, sha256=bykey[key]['sha256'], size_bytes=bykey[key]['size_bytes'])
    request = _json(store, grading['request_artifact_ref'])
    selector = validate_native_blast_database_result_selector(intent['selector'], program=bundle['program'])
    validate_selected_inputs(store, context, selector)
    if request['calculation_id'] != preparation['calculation_id'] or request['bundle'] != bundle or request['authenticated_attempt'] != attempt or (request['bundle_artifact_ref'] != preparation['bundle_artifact_ref']) or (selector != plain(context.assignment)['selector']) or (request['metadata_descriptors'] != (original_frozen['request']['metadata_descriptors'] if saved_mode else _metadata_descriptors(bundle, capture, selector))) or (request['sequence_model'] != bundle['requested_job']['native_blast_database']['grading_parameters']['sequence_database_model']):
        raise ContractError('native_blast_database_frozen_request_conflict')
    expected_artifacts = [dict(artifact_key=row['artifact_key'], artifact_ref=capture['artifact_refs'][row['artifact_key']], sha256=row['sha256'], size_bytes=row['size_bytes']) for row in bundle['artifacts'] if row['artifact_key'] in capture['artifact_refs']]
    if [{k: v for k, v in row.items() if k != 'path'} for row in request['artifacts']] != expected_artifacts:
        raise ContractError('native_blast_database_frozen_artifact_association_conflict')
    expected_retained = original_frozen['request']['retained_sources'] if saved_mode else _retained_catalog(store, selector, request['artifacts'], request['subject_snapshots'])
    if [{k: v for k, v in row.items() if k != 'path'} for row in request['retained_sources']] != [{k: v for k, v in row.items() if k != 'path'} for row in expected_retained]:
        raise ContractError('native_blast_database_frozen_selected_source_conflict')
    known = _known(store, context)
    for row in [*request['artifacts'], *request['retained_sources']]:
        _retained(store, row['artifact_ref'], sha256=row['sha256'], size_bytes=row['size_bytes'])
    for row in request['subject_snapshots']:
        if not saved_mode and row['subject_ref'] not in known or not store.reference_subset([row['subject_ref']], plain(context.scope)):
            raise ContractError('native_blast_database_frozen_subject_authority_conflict')
        _retained(store, row['sequence_artifact_ref'], sha256=row['sequence_sha256'], size_bytes=row['length'])
    _json(store, grading['worker_receipt_artifact_ref'])
    for ref in grading['worker_log_artifact_refs']:
        _retained(store, ref)
    for ref in grading.get('unsealed_artifact_refs', {}).values():
        _retained(store, ref)
    if grading['caller_diagnostics_artifact_ref'] is not None:
        _json(store, grading['caller_diagnostics_artifact_ref'])
    manifest = None
    if preparation['worker_manifest_artifact_ref'] is not None:
        if preparation['worker_manifest_artifact_ref'] != grading['manifest_artifact_ref']:
            raise ContractError('native_blast_database_frozen_manifest_conflict')
        manifest = _manifest(store, preparation['worker_manifest_artifact_ref'], request, grading['artifact_refs'])
    if function_mode and request.get('vdb_function_model') != selector['vdb_function_model']:
        raise ContractError('native_blast_database_frozen_request_conflict')
    if saved_mode:
        if request['reuse'] is None or (manifest is not None and manifest['input_interpretation_id'] != selected['calculation_input']['input_interpretation_id']) or any((request[k] != original_frozen['request'][k] for k in ('bundle', 'bundle_artifact_ref', 'bundle_capture', 'authenticated_attempt', 'artifacts', 'metadata_descriptors', 'retained_sources', 'subject_snapshots', 'sequence_model'))):
            raise ContractError('native_blast_database_frozen_request_conflict')
    for role, field in _ARTIFACT_FIELDS.items():
        expected_ref = grading['artifact_refs'].get(role)
        if role == 'diagnostics' and expected_ref is None:
            expected_ref = grading['caller_diagnostics_artifact_ref']
        if preparation[field] != expected_ref:
            raise ContractError('native_blast_database_frozen_artifact_association_conflict')
        if expected_ref is not None:
            _retained(store, expected_ref)
    validate_schema(preparation['failures'], native_blast_database_fact_sources()['execution_blast_database_failures']['report_schema'])
    failures, status = _preparation_failures(manifest, grading['caller_failure'], capture)
    if preparation['failures'] != failures or preparation['status'] != status:
        raise ContractError('native_blast_database_frozen_preparation_outcome_conflict')
    return {'grading': grading, 'request': request, 'bundle': bundle, 'capture': capture, 'manifest': manifest, 'observation': original_frozen['observation'] if saved_mode else _json(store, grading['observation_artifact_ref'])}

def _full_rows(store, prepared, frozen):
    if prepared['full_rows_artifact_ref'] is None:
        return []
    raw = _retained(store, prepared['full_rows_artifact_ref']).read_bytes()
    rows, offsets, position = ([], [], 0)
    for line in raw.splitlines(keepends=True):
        row = _decode(line)
        rows.append(row)
        offsets.append(dict(family=row['family'], record_key=row['record_key'], ordinal=len(rows) - 1, byte_start=position, byte_end=position + len(line)))
        position += len(line)
    index = _json(store, prepared['row_index_artifact_ref'])
    if index != dict(schema='native_blast_database_row_index_v1', calculation_id=prepared['calculation_id'], rows=offsets):
        raise ContractError('native_blast_database_frozen_row_index_conflict')
    if frozen['manifest']['counts']['numerical_rows'] != len(rows):
        raise ContractError('native_blast_database_frozen_row_count_conflict')
    if frozen['manifest']['version'] == 'native_blast_database_result_worker_manifest_v2':
        _frozen_native_occurrences(store, prepared, frozen, rows)
    return rows

def _frozen_native_occurrences(store, prepared, frozen, rows):
    """Resolve saved occurrence addresses; never recreate numerical rows."""
    sheets = _json(store, prepared['sheets_artifact_ref'])
    calculations = _json(store, prepared['calculations_artifact_ref'])
    binding = sheets['native_convergence']
    extraction = binding['extraction']
    originals = [] if extraction is None else extraction['convergence_records']
    observed = (calculations['iteration'] or {}).get('convergence_observations', [])
    combined = (sheets['iteration'] or {}).get('convergence_records', [])
    native = [(i, value) for i, value in enumerate(observed) if value['evidence']['origin'] == 'native_extractor_output']
    if len(native) != len(originals):
        raise ContractError('native_blast_database_frozen_convergence_record_conflict')
    reference = frozen['grading']['artifact_refs'].get('native_convergence')
    qualified_rows = []
    for j, original in enumerate(originals):
        candidates = [(i, value) for i, value in native if value['record_key'] == original['record_key']]
        saved = [(i, value) for i, value in enumerate(combined) if value['record_key'] == original['record_key']]
        markers = [i for i, value in enumerate(extraction['markers']) if value['record_key'] == original['record_key']]
        if len(candidates) != 1 or len(saved) != 1 or len(markers) != 1 or (saved[0][1] != original):
            raise ContractError('native_blast_database_frozen_convergence_record_conflict')
        i, observation = candidates[0]
        if observation['record_index'] != saved[0][0] or any((observation[key] != original[key] for key in ('record_key', 'query_operand', 'search_key', 'evidence'))):
            raise ContractError('native_blast_database_frozen_convergence_record_conflict')
        calculation_ref = dict(artifact_role='calculations', pointer=f'/iteration/convergence_observations/{i}')
        matching_rows = [row for row in rows if row['family'] == 'iteration_convergence' and calculation_ref in row['component_refs']]
        refs = [calculation_ref, dict(artifact_role='sheets', pointer=f'/native_convergence/extraction/convergence_records/{j}'), dict(artifact_role='sheets', pointer=f'/native_convergence/extraction/markers/{markers[0]}')]
        if len(matching_rows) != 1 or matching_rows[0]['component_refs'] != refs or matching_rows[0]['identity']['record_source'] != dict(source_ref=reference, pointer=f'/convergence_records/{j}'):
            raise ContractError('native_blast_database_frozen_convergence_row_conflict')
        qualified_rows.append(matching_rows[0]['record_key'])
    if reference is not None and any((row['record_key'] not in qualified_rows for row in rows if row['family'] == 'iteration_convergence' and row['identity']['record_source']['source_ref'] == reference)):
        raise ContractError('native_blast_database_frozen_convergence_row_conflict')

def _projection(store, context, preparation, selector):
    frozen = _validate_preparation(store, context, preparation)
    selector = validate_native_blast_database_result_selector(selector, program=frozen['bundle']['program'])
    intent = _json(store, frozen['grading']['intent_artifact_ref'])
    if selector != intent['selector'] or selector != plain(context.assignment)['selector']:
        raise ContractError('native_blast_database_original_selector_conflict')
    rows = _full_rows(store, preparation, frozen)
    projected = project_native_blast_database_rows(rows, selector=selector, calculation_id=preparation['calculation_id'])
    return (frozen, projected)

class _QueryQualification(ValueError):
    """A usable numerical row lacks a proved biological query relation."""

def _one(values, reason):
    if len(values) != 1:
        raise _QueryQualification(reason)
    return values[0]

def _master_relation(store, inputs, calculations, query, axis):
    kind = {'msa_master': 'msa', 'pssm_master': 'pssm'}[axis]
    relation = _one([r for item in inputs['metadata'] if item['consumer'] == 'query_identity' and item['status'] == 'valid' and (item['normalized'] is not None) for r in item['normalized']['master_subjects'] if r['kind'] == kind and r['input_key'] == query['input_key'] and (r['record_ordinal'] == query['record_ordinal'])], 'master_subject_relation_unresolved')
    if relation['subject_ref'] != query['subject_ref'] or relation['sequence_sha256'] != query['sequence_sha256']:
        raise _QueryQualification('master_subject_relation_conflict')
    source = store.get(relation['source']['source_ref'])
    if source['record_type'] != 'source':
        raise _QueryQualification('master_relation_source_record_unavailable')
    if axis == 'msa_master':
        sheet = _one([s for s in inputs['msa_sheets'] if s['artifact_key'] == query['artifact_key']], 'master_positional_map_unavailable')
        if sheet['status'] != 'complete' or sheet['master_record_ordinal'] != query['record_ordinal'] or inputs['effective_master_record_ordinal'] != query['record_ordinal'] or (inputs['selected_master_record_ordinal'] not in (None, query['record_ordinal'])):
            raise _QueryQualification('master_positional_map_conflict')
        mapping = sheet['master_column_map']
        if [r['alignment_column'] for r in mapping] != list(range(sheet['alignment_columns'])):
            raise _QueryQualification('master_positional_map_incomplete')
        positions = [r for r in mapping if r['master_position'] is not None]
        if [r['master_position'] for r in positions] != list(range(query['length'])) or ''.join((r['symbol'] for r in positions)) != query['sequence']:
            raise _QueryQualification('master_positional_map_conflict')
    else:
        sheet = _one([s for s in inputs['pssm_sheets'] if s['artifact_key'] == query['artifact_key']], 'master_positional_map_unavailable')
        original = _one([r for r in sheet['pssms'] if r['record_ordinal'] == query['record_ordinal']], 'master_positional_map_unavailable')
        candidates = [*calculations['pssm'], *(calculations['iteration'] or {}).get('pssms', [])]
        matrix = _one([r for item in candidates if item['artifact_key'] == query['artifact_key'] for r in item['components']['matrices'] if r['pssm_key'] == original['pssm_key'] and r['record_ordinal'] == query['record_ordinal']], 'master_positional_map_unavailable')
        master = matrix['master']
        if master['status'] != 'complete' or master['sequence'] != query['sequence'] or master['decoded_length'] != query['length'] or (master['reported_length'] != query['length']) or (matrix['dimensions']['positions'] != query['length']) or (master['column_to_residue'] != [dict(column=i, master_position=i, symbol=s) for i, s in enumerate(query['sequence'])]):
            raise _QueryQualification('master_positional_map_conflict')
    return source['id']

def _hsp_payload(store, context, preparation, frozen, full_row, documents):
    """Qualify saved components and exact biological operands, without regrading."""
    inputs, collection, calculations = documents
    key = full_row['identity']['row_key']
    search = _one([r for r in collection['searches'] if r['search_key'] == key['search_key']], 'query_search_unresolved')
    operand = search['operand_binding']
    if operand is None:
        raise _QueryQualification('query_operand_unresolved')
    query = _one([r for r in inputs['query_records'] if r['artifact_key'] == operand['artifact_key'] and r['record_ordinal'] == operand['record_ordinal']], 'query_operand_unresolved')
    if query['binding_status'] != 'available' or query['subject_ref'] is None or operand['subject_ref'] != query['subject_ref']:
        raise _QueryQualification('query_subject_identity_unresolved')
    snapshot = _one([r for r in frozen['request']['subject_snapshots'] if r['subject_ref'] == query['subject_ref']], 'query_subject_snapshot_unavailable')
    subject = store.get(query['subject_ref'])
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.alignment_site_native import immutable_record
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_hmmer_result_publication import _subject_chunks
    immutable_record(subject)
    actual_digest, actual_length = (hashlib.sha256(), 0)
    for chunk in _subject_chunks(store, subject['id']):
        chunk = chunk.encode('ascii') if isinstance(chunk, str) else chunk
        actual_digest.update(chunk)
        actual_length += len(chunk)
    if subject['record_type'] != snapshot['record_type'] or actual_length != snapshot['length'] or actual_length != query['length'] or (store.subject_molecule(subject['id']) != query['molecule']) or (snapshot['molecule'] != query['molecule']) or (actual_digest.hexdigest() != snapshot['sequence_sha256']) or (snapshot['sequence_sha256'] != query['sequence_sha256']) or (hashlib.sha256(query['sequence'].encode('ascii')).hexdigest() != query['sequence_sha256']) or (_retained(store, snapshot['sequence_artifact_ref']).read_bytes() != query['sequence'].encode('ascii')):
        raise _QueryQualification('complete_query_sequence_identity_conflict')
    axis, reference_axis = (full_row['context'][k] for k in ('query_axis_kind', 'reference_axis_kind'))
    if axis not in {'sequence', 'msa_master', 'pssm_master'} or reference_axis not in {'sequence', 'profile_model', 'vdb_member'}:
        raise _QueryQualification('native_axis_identity_unresolved')
    relation_source = None if axis == 'sequence' else _master_relation(store, inputs, calculations, query, axis)
    component = _one([r for r in calculations['native_hsp_components'] if r['row_key'] == key], 'native_hsp_component_unresolved')
    measured = component['component']
    if component['status'] != 'available' or not measured['geometry_available'] or (not measured['traceback_available']) or (not measured['pairs']) or (search['program_context']['geometry_program'] is None):
        raise _QueryQualification('complete_query_geometry_unavailable')
    spans = []
    for pair in measured['pairs']:
        start, end = (pair['query_start'], pair['query_end'])
        if type(start) is not int or type(end) is not int or (not 0 <= start < end <= query['length']):
            raise _QueryQualification('query_geometry_outside_complete_subject')
        if query['selected_interval'] is not None and (not query['selected_interval'][0] <= start < end <= query['selected_interval'][1]):
            raise _QueryQualification('query_geometry_outside_selected_interval')
        spans.append((start, end))
    merged = []
    for start, end in sorted(set(spans)):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    if not store.reference_subset([subject['id']], plain(context.scope)) or not store.has_exact_mapping(subject['id']):
        raise _QueryQualification('query_original_mapping_unavailable')
    segments = [dict(start=a, end=b) for a, b in merged]
    if not store.scope_covers(store.map_segments(subject['id'], segments), plain(context.scope)):
        raise _QueryQualification('query_geometry_outside_assigned_scope')
    names = dict(native_score_bits='native_score_bits', native_raw_score='native_raw_score', native_evalue='native_evalue', alignment_columns='alignment_columns', paired_columns='paired_positions', query_gap_columns='query_gap_columns', reference_gap_columns='reference_gap_columns', paired_query_units='query_aligned_positions')
    if reference_axis != 'profile_model':
        names.update(identical_pairs='identical_positions', paired_identity='paired_identity', alignment_identity='alignment_identity', paired_reference_units='reference_aligned_positions')
    values = [dict(name=names[cell['name']], value=dict(type='number', value=cell['value'], unit_ref=None)) for cell in full_row['measurements'] if cell['name'] in names and cell['status'] == 'available' and (type(cell['value']) in (int, float)) and math.isfinite(cell['value'])]
    if not values:
        raise _QueryQualification('native_hsp_measurements_unavailable')
    payload = dict(subject_refs=[subject['id']], source_subject_refs=[], source_ref=identity('source', {'origin': 'tool', 'record': _source_payload(frozen['bundle'], frozen['capture'])}), kind='profile_match' if reference_axis == 'profile_model' else 'comparison', measurements=values, dependencies=[], anchor=None, operand_intervals=[dict(role='query', subject_ref=subject['id'], start=a, end=b, unit=store.subject_unit(subject['id']), model_unit=measured['coordinate_units']['alignment']) for a, b in merged], native_blast_database=dict(version='native_blast_database_observation_v1', program=full_row['program'], record_key=full_row['record_key'], search_key=key['search_key'], hit_ordinal=key['hit_ordinal'], hsp_ordinal=key['hsp_ordinal'], bundle_artifact_ref=preparation['bundle_artifact_ref'], query_axis_kind=axis, reference_axis_kind=reference_axis))
    payload['dependencies'] = list(dict.fromkeys([payload['source_ref'], subject['id'], *([relation_source] if relation_source else [])]))
    return payload

def _published_rows(store, context, preparation, frozen, projected, *, publish):
    """The same frozen projection proves writes and byte-exact read-only replay."""
    source = identity('source', {'origin': 'tool', 'record': _source_payload(frozen['bundle'], frozen['capture'])})
    all_rows = {(r['family'], r['record_key']): r for r in _full_rows(store, preparation, frozen)}
    saved_mode = preparation.get('calculation_input', {}).get('mode') == 'saved_function_sheet'
    documents = None
    if not saved_mode and projected['families'] and any((f['family'] == 'hsp' and f['rows'] for f in projected['families'])):
        refs = frozen['grading']['artifact_refs']
        documents = tuple((_json(store, refs[role]) for role in ('inputs', 'collection', 'calculations')))
    rows, references, failures, diagnostics = ({}, [source], [], [])
    for family in projected['families']:
        items = rows[family['family']] = []
        for selected in family['rows']:
            row = dict(**selected, source_ref=source, observation_ref=None, subject_ref=None, reference_refs=[], publication_status='source_only')
            if family['family'] == 'hsp' and (not saved_mode):
                try:
                    payload = _hsp_payload(store, context, preparation, frozen, all_rows['hsp', selected['record_key']], documents)
                except _QueryQualification as error:
                    diagnostics.append(dict(record_key=selected['record_key'], reason=str(error)))
                    failures.append(_failure('publication', 'native_blast_database_query_unbound', 'query_identity_unresolved', record_key=selected['record_key'], search_key=selected['identity']['row_key']['search_key'], pointer='/grading/publication_diagnostics/' + str(len(diagnostics) - 1)))
                else:
                    reference = identity('observation', {'origin': 'tool', 'record': payload})
                    if publish:
                        actual = store.put('observation', payload, origin='tool', scope=plain(context.scope))
                    else:
                        actual = store.get(reference)
                    expected = dict(**payload, id=reference, origin='tool', record_type='observation')
                    if canonical(actual) != canonical(expected):
                        raise ContractError('native_blast_database_frozen_observation_conflict')
                    store._validate_record('observation', payload, 'tool')
                    row.update(observation_ref=reference, subject_ref=payload['subject_refs'][0], publication_status='published')
                    if reference not in references:
                        references.append(reference)
            items.append(row)
    return (rows, references, failures, diagnostics)

def validate_native_blast_database_publication(store, *, context, publication):
    expected = {'version', 'calculation_id', 'source_ref', 'preparation_artifact_ref', 'selector', 'selected_rows_artifact_ref', 'rows_by_family', 'record_refs', 'acquisition_complete', 'projection_complete', 'native_execution_successful', 'complete', 'failures'}
    if type(publication) is not dict or set(publication) != expected or publication['version'] != PUBLICATION_VERSION:
        raise ContractError('native_blast_database_publication_invalid')
    prepared = _json(store, publication['preparation_artifact_ref'])
    frozen, projected = _projection(store, context, prepared, publication['selector'])
    payload = _source_payload(frozen['bundle'], frozen['capture'])
    expected_source = identity('source', {'origin': 'tool', 'record': payload})
    source = store.get(publication['source_ref'])
    if publication['source_ref'] != expected_source or {k: v for k, v in source.items() if k not in {'id', 'record_type', 'origin'}} != payload or source['origin'] != 'tool':
        raise ContractError('native_blast_database_original_source_conflict')
    rows, records, qualifications, diagnostics = _published_rows(store, context, prepared, frozen, projected, publish=False)
    selected = _json(store, publication['selected_rows_artifact_ref'])
    if selected != {'schema': 'tool_grading_artifact_v1', 'provider': 'episode.execution_result', 'native_artifact_ref': prepared['bundle_artifact_ref'], 'grading': {'schema': 'native_blast_database_selected_grading_v1', 'projection': projected, 'rows_by_family': rows, 'publication_diagnostics': diagnostics}}:
        raise ContractError('native_blast_database_frozen_projection_conflict')
    projection_failures = deepcopy(prepared['failures']) + deepcopy(projected['failures'])
    failures = projection_failures + qualifications
    acquisition = frozen['capture']['status'] == 'complete'
    projection = prepared['full_rows_artifact_ref'] is not None and (not projection_failures)
    observation, bundle = (frozen['observation'], frozen['bundle'])
    success = observation['state'] == 'completed' and observation['returncode'] == 0 and bundle['process']['started'] and (bundle['process']['returncode'] == 0) and (not bundle['failures'])
    comparison = dict(publication, calculation_id=prepared['calculation_id'], rows_by_family=rows, record_refs=records, acquisition_complete=acquisition, projection_complete=projection, native_execution_successful=success, complete=acquisition and projection and success, failures=failures)
    if canonical(publication) != canonical(comparison):
        raise ContractError('native_blast_database_frozen_publication_conflict')
    descriptors = native_blast_database_fact_sources()
    for family, items in rows.items():
        validate_schema(items, descriptors['execution_blast_database_' + family + '_rows']['report_schema'])
    return deepcopy(publication)

def validate_native_blast_database_observation(store, observation):
    """Resolve only actual completed actions and their exact frozen publications."""
    if type(observation) is not dict or observation.get('record_type') != 'observation' or observation.get('origin') != 'tool' or (not observation.get('native_blast_database')):
        raise ContractError('native_blast_database_observation_required')
    payload = {k: v for k, v in observation.items() if k not in {'id', 'origin', 'record_type'}}
    if observation['id'] != identity('observation', {'origin': 'tool', 'record': payload}):
        raise ContractError('native_blast_database_frozen_observation_conflict')
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_actions'").fetchone():
        raise ContractError('native_blast_database_original_publication_required')
    actions = store.db.execute("SELECT run_id,episode_id,decision_index,action,result FROM runtime_actions WHERE result IS NOT NULL AND json_extract(result,'$.result.version') IN ('native_blast_database_result_receipt_v1','native_blast_database_result_receipt_vdb_function_v1') AND EXISTS(SELECT 1 FROM json_each(runtime_actions.result,'$.record_refs') WHERE value=?) ORDER BY run_id,episode_id,decision_index", (observation['id'],))
    for action in actions:
        result, selected = (json.loads(action['result']), json.loads(action['action']))
        body = result['result']
        if result.get('status') != 'completed' or body['publication'] is None or selected != dict(kind='tool', tool='execution.results.collect', arguments={}) or (body['tool_name'] != selected['tool']) or (body['arguments'] != selected['arguments']) or (body['operation_key'] != f"{action['run_id']}:{action['episode_id']}:{action['decision_index']}") or (body['run_id'] != action['run_id']) or (body['episode_id'] != action['episode_id']) or (body['record_refs'] != result['record_refs']):
            raise ContractError('native_blast_database_original_publication_conflict')
        authority = EpisodeReturnRecords(store, action['run_id'], failure_prefix='native_blast_database_observation_')
        context = authority.context(action['episode_id'])
        if context.role != 'results' or plain(context.assignment) != body['assignment'] or plain(context.scope) != body['scope']:
            raise ContractError('native_blast_database_original_publication_conflict')
        publication = validate_native_blast_database_publication(store, context=context, publication=body['publication'])
        if publication['record_refs'] != body['record_refs'] or publication['failures'] != body['failures'] or _json(store, publication['preparation_artifact_ref']) != body['preparation']:
            raise ContractError('native_blast_database_original_publication_conflict')
        for row in publication['rows_by_family'].get('hsp', []):
            if row['observation_ref'] == observation['id']:
                if canonical(store.get(observation['id'])) != canonical(observation):
                    raise ContractError('native_blast_database_frozen_observation_conflict')
                prepared = body['preparation']
                frozen = _validate_preparation(store, context, prepared)
                if body['capture'] != frozen['capture'] or body['observation'] != frozen['observation']:
                    raise ContractError('native_blast_database_original_publication_conflict')
                return deepcopy(_one([r for r in _full_rows(store, prepared, frozen) if r['family'] == 'hsp' and r['record_key'] == row['record_key']], 'frozen_original_hsp_unavailable'))
    raise ContractError('native_blast_database_original_publication_required')
