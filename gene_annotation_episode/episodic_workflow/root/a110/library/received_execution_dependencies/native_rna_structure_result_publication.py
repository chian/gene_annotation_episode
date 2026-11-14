from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING
from gene_annotation_episode.episodic_workflow.root.a110.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_acquisition import decode_json, require, retained, validate_capture, rna_structure_source_payload
from gene_annotation_episode.episodic_workflow.root.a110.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_contracts import analyze_rna_input_sequence, issue, validate_rna_input, validate_rna_sheet, validate_rna_components
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_result_views import merge_issues, project_rna_prepublication, validate_rna_structure_row
from gene_annotation_episode.episodic_workflow.root.a110.tool_grading_artifacts import source_tool_gradings
if TYPE_CHECKING:
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_returns import NativeRNAStructureReturns
PREPARED_VERSION = 'native_rna_structure_prepared_grading_v1'
PREPARED_FIELDS = {'version', 'bundle_artifact_ref', 'source_grading_artifact_ref', 'grading_artifact_ref', 'sheet_artifact_ref', 'components_artifact_ref', 'selected_rows_artifact_ref', 'diagnostics_artifact_ref', 'worker_receipt_artifact_ref', 'sheet_schema', 'components_schema', 'selector', 'requested_cells_accounted_for', 'native_success', 'failures'}
STABLE_FIELDS = {'schema', 'sheet_artifact_ref', 'sheet_schema', 'components_artifact_ref', 'components_schema', 'captured_artifacts'}
SELECTED_FIELDS = {'schema', 'stable', 'selector', 'parameters', 'components_artifact_ref', 'components_schema', 'selected_rows_artifact_ref', 'diagnostics_artifact_ref', 'worker_receipt_artifact_ref', 'requested_cells_accounted_for', 'failures'}

def _artifact_json(store, reference):
    retained(store, reference)
    value = decode_json(store.get_artifact(reference), canonical_bytes=True)
    require(type(value) is dict, 'rna_invalid_component_schema')
    return value

def _envelope(store, reference, bundle_ref):
    retained(store, reference)
    body = decode_json(store.get_artifact(reference))
    require(type(body) is dict and set(body) == {'schema', 'provider', 'native_artifact_ref', 'grading'} and (body['schema'] == 'tool_grading_artifact_v1') and (body['provider'] == 'episode.execution_result') and (body['native_artifact_ref'] == bundle_ref), 'rna_invalid_component_schema')
    return body['grading']

def validate_prepared_rna_grading(store, prepared, *, bundle, capture, selector):
    require(type(prepared) is dict and set(prepared) == PREPARED_FIELDS and (prepared['version'] == PREPARED_VERSION), 'rna_invalid_component_schema')
    require(type(prepared['requested_cells_accounted_for']) is bool and type(prepared['native_success']) is bool, 'rna_invalid_component_schema')
    require(all(((prepared[reference] is None) == (prepared[schema] is None) for reference, schema in (('sheet_artifact_ref', 'sheet_schema'), ('components_artifact_ref', 'components_schema')))), 'rna_invalid_component_schema')
    require(prepared['selector'] == selector and prepared['bundle_artifact_ref'] == capture['bundle_artifact_ref'])
    stable = _envelope(store, prepared['source_grading_artifact_ref'], prepared['bundle_artifact_ref'])
    selected = _envelope(store, prepared['grading_artifact_ref'], prepared['bundle_artifact_ref'])
    require(set(stable) == STABLE_FIELDS and stable['schema'] == 'native_rna_structure_retained_grading_v1' and (set(selected) == SELECTED_FIELDS) and (selected['schema'] == 'native_rna_structure_selected_grading_v1') and (selected['stable'] == stable) and (selected['selector'] == selector), 'rna_invalid_component_schema')
    require(stable['captured_artifacts'] == capture['artifacts'], 'rna_original_attempt_mismatch')
    for name in ('components_artifact_ref', 'components_schema', 'selected_rows_artifact_ref', 'diagnostics_artifact_ref', 'worker_receipt_artifact_ref', 'requested_cells_accounted_for', 'failures'):
        require(selected[name] == prepared[name], 'rna_invalid_component_schema')
    parameters = selector['parameters'] if selector['acquisition'] == 'retained_sheet_only' else bundle['requested_job']['native_rna_structure']['grading_parameters']
    require(selected['parameters'] == parameters and prepared['native_success'] == (bundle['returncode'] == 0 and bundle['native_status'] == 'complete'), 'rna_invalid_component_schema')
    if selector['acquisition'] == 'complete_bound_bundle':
        require(all((prepared[name] == stable[name] for name in ('sheet_artifact_ref', 'sheet_schema', 'components_artifact_ref', 'components_schema'))), 'rna_invalid_component_schema')
    elif prepared['sheet_artifact_ref'] is not None:
        require(prepared['sheet_artifact_ref'] == stable['sheet_artifact_ref'] == selector['saved_input']['sheet_artifact_ref'])
    sheet = components = document = None
    if prepared['sheet_artifact_ref'] is not None:
        sheet = validate_rna_sheet(_artifact_json(store, prepared['sheet_artifact_ref']))
        require(sheet['schema'] == prepared['sheet_schema'] and all((sheet[name] == bundle[name] for name in ('operation', 'mode', 'record_key'))), 'rna_input_identity_mismatch')
    if prepared['components_artifact_ref'] is not None:
        require(sheet is not None, 'rna_invalid_component_schema')
        components = validate_rna_components(_artifact_json(store, prepared['components_artifact_ref']), sheet=sheet)
        require(components['parameters'] == parameters and components['schema'] == prepared['components_schema'], 'rna_invalid_component_schema')
    for name in ('diagnostics_artifact_ref', 'worker_receipt_artifact_ref'):
        if prepared[name] is not None:
            retained(store, prepared[name])
    if prepared['selected_rows_artifact_ref'] is not None:
        document = _artifact_json(store, prepared['selected_rows_artifact_ref'])
        diagnostics = _artifact_json(store, prepared['diagnostics_artifact_ref'])
        require(set(diagnostics) == {'schema', 'record_key', 'capture_failures', 'parse_issues', 'sheet_issues', 'calculation_issues', 'selection_issues'} and diagnostics['schema'] == 'rna_structure_grading_diagnostics_v1' and (diagnostics['record_key'] == bundle['record_key']), 'rna_invalid_component_schema')
        require(diagnostics['capture_failures'] == (capture['failures'] if selector['acquisition'] == 'complete_bound_bundle' else []), 'rna_invalid_component_schema')
        failures = merge_issues(bundle['failures'] if selector['acquisition'] == 'complete_bound_bundle' else [], diagnostics['capture_failures'], diagnostics['parse_issues'], diagnostics['sheet_issues'], diagnostics['calculation_issues'])
        if components is not None:
            expected, selection = project_rna_prepublication(sheet, components, selector=selector, components_sha256=store.get(prepared['components_artifact_ref'])['sha256'], failures=failures)
            require(document == expected and diagnostics['selection_issues'] == selection, 'rna_invalid_component_schema')
        else:
            selection = []
            projection = selector['projection']
            if projection['family'] != 'failure':
                choices = projection['rows']
                for index in range(len(choices['record_keys'])) if 'record_keys' in choices else [None]:
                    selection.append(issue('rna_requested_row_missing', stage='selection', record_key=bundle['record_key'], field='/selector/projection/rows' if index is None else f'/selector/projection/rows/record_keys/{index}', index=index))
            expected = {'schema': 'rna_structure_prepublication_v1', **{key: bundle[key] for key in ('record_key', 'operation', 'mode')}, 'selector': selector, 'sheet_schema': prepared['sheet_schema'], 'components_sha256': None, 'parameters': parameters, 'population_count': None, 'rows': [], 'failures': merge_issues(failures, selection), 'requested_cells_accounted_for': projection['family'] != 'failure'}
            require(document == expected and diagnostics['selection_issues'] == selection, 'rna_invalid_component_schema')
        require(document['failures'] == prepared['failures'] and document['requested_cells_accounted_for'] == prepared['requested_cells_accounted_for'], 'rna_invalid_component_schema')
    else:
        require(not prepared['requested_cells_accounted_for'], 'rna_invalid_component_schema')
    return {'stable': stable, 'selected': selected, 'sheet': sheet, 'components': components, 'document': document}

def _authority(store, context, *, baseline=False, allow_unsaved=False):
    EpisodeReturnRecords(store, context.run_id, failure_prefix='rna_').authenticate(context, allow_unsaved=allow_unsaved)
    return set(EpisodeReceipts(store, context.run_id).known(context.episode_id, baseline=baseline))

def authenticate_rna_results_commission(store, context, *, allow_unsaved=False):
    """The original parent action defines this results child's exact request."""
    records = EpisodeReturnRecords(store, context.run_id, failure_prefix='rna_')
    records.authenticate(context, allow_unsaved=allow_unsaved)
    require(context.role == 'results' and len(context.path) > 1 and (context.path[-1][0] == 'results'))
    slot = context.path[-1][1]
    require(slot.startswith('child_') and slot[6:].isdecimal() and (str(int(slot[6:])) == slot[6:]))
    parent_id = EpisodeRef(context.run_id, context.path[:-1]).episode_id
    parent = records.context(parent_id)
    store.validate_scope(plain(context.scope), parent_scope=plain(parent.scope))
    row = store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (context.run_id, parent_id, int(slot[6:]))).fetchone()
    if row is None and allow_unsaved:
        saved = store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)).fetchone()
        require(saved is None)
        manifest = EpisodeReceipts(store, context.run_id).manifest(context.episode_id)
        require(manifest['parent_episode_id'] == parent_id and records._equal(plain(context.request)['message'].get('knowledge_inheritance'), manifest))
        own = store.db.execute('SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? UNION ALL SELECT 1 FROM runtime_forms WHERE run_id=? AND episode_id=? LIMIT 1', (context.run_id, context.episode_id, context.run_id, context.episode_id)).fetchone()
        require(own is None)
        return context
    require(row is not None)
    action = decode_json(row['action'])
    contract = plain(context.request)['report_contract']
    require(action.get('kind') in {'episode_child', 'job_child'} and action.get('role') == 'results' and (action.get('assignment') == plain(context.assignment)) and (action.get('scope') == plain(context.scope)) and (action.get('purpose') == contract['decision']) and (decode_json(action['schema_json']) == contract['measurements']['schema']))
    return context

def _qualify_original_handoff(store, context, bundle):
    authenticate_rna_results_commission(store, context)
    assignment = plain(context.assignment)
    handle = assignment['handoff_ref']
    require(handle in _authority(store, context, baseline=True))
    original = PracticalReceiptInformation(store, context.run_id).read(handle, context.scope)
    source = store.get(handle)
    snapshot = decode_json(store.get_artifact(source['request_ref']))
    selected, receipt = (snapshot['assignment'], original['receipt'])
    job = receipt['outcome'].get('facts', {}).get('requested_job')
    identity = bundle['identity']
    require(isinstance(job, dict) and isinstance(job.get('handoff'), dict) and (receipt['tool_name'] in {'practical.job.start', 'practical.job.status', 'practical.job.collect'}) and (selected['requested_job'] == bundle['requested_job']) and (selected['resource_kind'] == 'local') and (selected['resource_id'] == identity['resource_id']) and (original['run_id'] == identity['run_id'] == context.run_id) and (original['episode_id'] == identity['episode_id']) and (job['requested_job_sha256'] == identity['requested_job_sha256'] == digest(selected['requested_job'])) and (job['argv'] == selected['requested_job']['argv']) and (job['environment'] == selected['requested_job']['environment']) and (job['resource_kind'] == selected['resource_kind']) and (job['execution_id'] == identity['execution_id'] == job['handoff']['execution_id']) and (job['handoff']['monitor_operation'] == 'practical.job.status') and (job['handoff']['results_operation'] == 'practical.job.collect'))
    root = Path(selected['workspace']) / '.episode-operations' / digest({'run': identity['run_id'], 'episode': identity['episode_id']}) / digest(identity['operation_key'])
    require(Path(identity['execution_id']) == root / 'native.json')
    requested = selected['requested_job']['native_rna_structure']
    require(all((bundle[name] == requested[name] for name in ('operation', 'mode', 'record_key'))))

def _rna_reverse(sequence):
    require(all((letter in 'ACGURYSWKMBDHVNacguryswkmbdhvn' for letter in sequence)), 'rna_subject_binding_conflict')
    return sequence.translate(str.maketrans('ACGURYSWKMBDHVNacguryswkmbdhvn', 'UGCAYRSWMKVHDBNugcayrswmkvhdbn'))[::-1]

def _subject_sequence(store, reference):
    row = store.get(reference)
    if row['record_type'] == 'feature':
        parent = _subject_sequence(store, row['subject_ref'])
        sequence = ''.join((parent[part['start']:part['end']] for part in row['segments']))
        return _rna_reverse(sequence) if row['strand'] == '-' else sequence
    if row['record_type'] == 'read_subject':
        from gene_annotation_episode.episodic_workflow.root.a110.materials_packing import component_window
        return component_window(store, store.get(row['member_ref']), 'sequence', 0, row['length']).decode('ascii')
    require(row.get('sequence_ref') is not None, 'rna_subject_binding_conflict')
    return store.get_artifact(row['sequence_ref']).decode('ascii')

def validate_rna_structure_publication_inputs(store, context, *, original_input, capture):
    if original_input is None:
        return None
    try:
        mode = 'mfe_prediction' if original_input['schema'] == 'rna_prediction_input_v1' else 'supplied_features'
        request = validate_rna_input(original_input, mode=mode)
        binding = request['subject_binding']
        provenance = request.get('structure_source_ref')
        if binding is None and provenance is None:
            return None
        known = _authority(store, context, baseline=True)
        if provenance is not None:
            require(provenance in known and store.get(provenance)['record_type'] == 'source', 'rna_subject_binding_conflict')
        if binding is None:
            return None
        subject, artifact = (binding['subject_ref'], binding['sequence_artifact_ref'])
        require({subject, artifact} <= known, 'rna_subject_binding_conflict')
        require(store.subject_unit(subject) == 'nt' and store.subject_molecule(subject) == 'rna', 'rna_subject_binding_conflict')
        sequence = _subject_sequence(store, subject)
        require(store.get_artifact(artifact).decode('ascii') == sequence and len(sequence) == store.subject_length(subject), 'rna_subject_binding_conflict')
        start, end = (binding['start'], binding['end'])
        require(0 <= start < end <= len(sequence), 'rna_subject_binding_conflict')
        footprint = store.map_segments(subject, [{'start': start, 'end': end}])
        require(bool(footprint) and store.scope_covers(footprint, plain(context.scope)), 'rna_subject_binding_conflict')
        selected = sequence[start:end]
        if binding['strand'] == '-':
            selected = _rna_reverse(selected)
        if request['normalization'] == 'uppercase_ascii':
            selected = selected.translate(str.maketrans('abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        analysis, _ = analyze_rna_input_sequence(request, mode=mode)
        require(analysis is not None and analysis['analysis_sequence'] == selected, 'rna_subject_binding_conflict')
        return deepcopy(binding)
    except (ValueError, OSError, KeyError, UnicodeError) as error:
        raise ValueError('rna_subject_binding_conflict') from error

def validate_rna_structure_job_inputs(store, context, assignment):
    request = assignment.get('requested_job', {})
    if 'native_rna_structure' not in request:
        return []
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_contracts import validate_rna_structure_requested_job
    job = validate_rna_structure_requested_job(request)['native_rna_structure']
    known, refs, original = (_authority(store, context, allow_unsaved=True), [], None)
    for operand in job['operands']:
        ref = operand['artifact_ref']
        if ref is None:
            continue
        require(ref in known, 'rna_subject_binding_conflict')
        metadata, _ = retained(store, ref)
        require((metadata['sha256'], metadata['size']) == (operand['sha256'], operand['size_bytes']), 'rna_capture_digest_mismatch')
        refs.append(ref)
        if operand['role'] == 'input':
            original = validate_rna_input(decode_json(store.get_artifact(ref)), mode=job['mode'])
            require(original['record_key'] == job['record_key'], 'rna_input_identity_mismatch')
    if original is not None:
        binding = original['subject_binding']
        refs.extend([] if binding is None else [binding['subject_ref'], binding['sequence_artifact_ref']])
        if original.get('structure_source_ref') is not None:
            refs.append(original['structure_source_ref'])
        require(set(refs) <= known, 'rna_subject_binding_conflict')
    return list(dict.fromkeys(refs))

def publish_selected_rna_structure_rows(store, context, *, source_ref, bundle, capture, prepared, selector):
    EpisodeReturnRecords(store, context.run_id, failure_prefix='rna_').authenticate(context)
    require(context.role == 'results' and plain(context.assignment)['selector'] == selector)
    scope = store.validate_scope(plain(context.scope))
    require(bundle['identity']['run_id'] == context.run_id)
    _qualify_original_handoff(store, context, bundle)
    if selector['acquisition'] == 'complete_bound_bundle':
        validate_capture(store, capture, bundle=bundle)
    source = store.get(source_ref)
    expected = rna_structure_source_payload(bundle=bundle, capture=capture, prepared=prepared)
    require(source.get('record_type') == 'source' and source.get('origin') == 'tool' and ({k: v for k, v in source.items() if k not in {'id', 'record_type', 'origin'}} == expected))
    checked = validate_prepared_rna_grading(store, prepared, bundle=bundle, capture=capture, selector=selector)
    require(checked['stable'] in source_tool_gradings(store, source_ref), 'rna_invalid_component_schema')
    failures, binding = (deepcopy(prepared['failures']), None)
    sheet, components, document = (checked[name] for name in ('sheet', 'components', 'document'))
    binding_failed = False
    if sheet is not None:
        try:
            binding = validate_rna_structure_publication_inputs(store, context, original_input=sheet['original_input'], capture=capture)
        except ValueError:
            binding_failed = True
            failures = merge_issues(failures, [issue('rna_subject_binding_conflict', stage='binding', record_key=bundle['record_key'], field='/subject_binding')])
    rows = []
    for pre in [] if document is None else document['rows']:
        row = {key: deepcopy(value) for key, value in pre.items() if key not in ('ordinal', 'sheet_status', 'cells')}
        row.update(source_ref=source_ref, subject_ref=None if binding is None else binding['subject_ref'], calculation_key='rna_calculation:' + store.get(prepared['components_artifact_ref'])['sha256'], calculation_parameters=deepcopy(components['parameters']), measurements=[], unavailable=[])
        for cell in pre['cells']:
            names = ('name', 'value', 'unit', 'numerator', 'denominator', 'origin') if cell['state'] == 'present' else ('name', 'state', 'reason', 'unit', 'numerator', 'denominator', 'origin')
            row['measurements' if cell['state'] == 'present' else 'unavailable'].append({key: cell[key] for key in names})
        row['status'] = 'invalid' if pre['sheet_status'] == 'invalid' else 'partial' if pre['sheet_status'] == 'partial' or row['unavailable'] or binding_failed else 'bound' if binding is not None else 'unbound'
        if binding_failed and 'rna_subject_binding_conflict' not in row['qualification_codes']:
            row['qualification_codes'].append('rna_subject_binding_conflict')
        rows.append(validate_rna_structure_row(row))
    return {'version': 'native_rna_structure_publication_v1', 'source_ref': source_ref, 'record_refs': [source_ref], 'rows': rows, 'failures': failures, 'requested_cells_accounted_for': prepared['requested_cells_accounted_for']}
