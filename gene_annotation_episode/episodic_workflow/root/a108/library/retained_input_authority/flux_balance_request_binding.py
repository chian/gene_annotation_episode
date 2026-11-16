"""Compact FBA selections and their authenticated, private host materialization.

The original episode assignment stays compact. This module fills execution
bookkeeping only; existing FBA input witnesses and native contracts retain
scientific admission, and existing practical records retain endpoint credit.
"""
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.bvbrc_appservice_custody import AppServiceCustody
from gene_annotation_episode.episodic_workflow.root.a108.communication import plain
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a108.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.flux_balance_contracts import validate_flux_balance_record
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_file_capture import _metadata, retained_native_file
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_flux_balance_contracts import ATTEMPT_DIRECTORY_NAME, DRIVER_MODULE, RUN_PLAN_FILENAME, flux_balance_environment
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.practical_execution_records import validate_assignment
ASSIGNMENT_VERSION = 'flux_balance_scientific_assignment_v1'
LAUNCH_VERSION = 'flux_balance_scientific_launch_v1'
CONTROL_VERSION = 'flux_balance_request_binding_v2'
PUBLIC_OUTCOME_VERSION = 'flux_balance_practical_outcome_v2'
_SOURCE_FIELDS = ('artifact_ref', 'text_ref', 'request_ref', 'stdout_ref', 'stderr_ref')
OUTPUT_ROLES = ('original_model', 'selected_request', 'effective_model', 'effective_problem', 'solution', 'flux_csv', 'native_log', 'manifest')
_TABLE = 'runtime_flux_balance_request_bindings'

def _require(condition, code):
    if not condition:
        raise ValueError('flux_balance_request_' + code)

def is_compact_assignment(value):
    return value.get('version') == ASSIGNMENT_VERSION

def is_compact_launch(value):
    return value.get('version') == LAUNCH_VERSION

def _resolve_file(store, selection, records):
    record = records[selection['witness_ref']]
    _require(record.get('id') == selection['witness_ref'], 'witness_identity_conflict')
    version = selection['version']
    _require(version is None or str(record.get('revision')) == version, 'witness_version_conflict')
    field = selection['artifact_field']
    if record.get('record_type') == 'artifact':
        _require(field is None, 'artifact_field_conflict')
        reference = record['id']
    else:
        _require(record.get('record_type') == 'source' and field in _SOURCE_FIELDS, 'source_witness_required')
        reference = record.get(field)
        _require(type(reference) is str and reference, 'artifact_field_unavailable')
    metadata = _metadata(store, reference)
    _require(reference == 'artifact_' + metadata['sha256'], 'artifact_identity_conflict')
    return {'artifact_ref': reference, 'sha256': metadata['sha256'], 'size_bytes': metadata['size'], 'format': selection['format']}

def _materialize(store, row):
    selection, binding = (row['selection'], row['binding'])
    request, records = (selection['request'], {item['reference']: item['record'] for item in row['witness_records']})
    model_selection = request['model_input']
    model = _resolve_file(store, model_selection['file'], records)
    _require(model['format'] in binding['model_formats'], 'model_format_not_bound')
    model_path = str(store.path / 'artifacts' / model['sha256'][:2] / model['sha256'])
    acquisition = model_selection['acquisition_receipt_file']

    def bound(value):
        source = value.get('source')
        return validate_flux_balance_record('Bound', {'kind': value['kind'], 'value': value['value'], 'native_token': value.get('native_token'), 'float_hex': value.get('float_hex'), 'source': None if source is None else {'file': _resolve_file(store, source['file'], records), 'pointer': source['pointer']}})
    changes = request['constraints']
    job = {'version': 'native_flux_balance_job_v1', 'operation': request['operation'], 'mode': request['mode'], 'source_alias': 'biomni.tool.systems_biology.perform_flux_balance_analysis', 'model_input': {'file': {'path': model_path, 'sha256': model['sha256'], 'size_bytes': model['size_bytes']}, 'artifact_ref': model['artifact_ref'], 'format': model['format'], 'original_loader_selection': model_selection['original_loader_selection'], 'repository_identifier': model_selection['repository_identifier'], 'acquisition_receipt_file': None if acquisition is None else _resolve_file(store, acquisition, records)}, 'constraints': None if changes is None else [{'reaction_id': change['reaction_id'], 'lower': bound(change['lower']), 'upper': bound(change['upper'])} for change in changes], 'objective': deepcopy(request['objective']), 'solver_options': deepcopy(request['solver_options']), 'software': deepcopy(binding['software']), 'output_prefix': 'fba-output', 'flux_output_name': 'fluxes.csv'}
    software = binding['software']
    lifecycle = str(Path(row['workspace']) / '.fba-selected-runtime' / row['assignment_id'])
    environment = flux_balance_environment(software, attempt_directory=str(Path(lifecycle) / ATTEMPT_DIRECTORY_NAME), lifecycle_directory=lifecycle)
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': row['assignment_id'], 'resource_id': row['resource_id'], 'resource_kind': 'local', 'workspace': row['workspace'], 'endpoint': selection['endpoint'], 'requested_job': {'argv': [software['python']['path'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME], 'environment': environment, 'native_flux_balance': job}, 'progress_requirements': deepcopy(selection['progress_requirements']), 'completion_keys': deepcopy(selection['completion_keys']), 'initial_context': {'revision': 0, 'cwd': row['workspace'], 'environment': {}}, 'inventory_snapshot': {}, 'constraints': deepcopy(selection['constraints']), 'native_flux_balance_execution': {'version': 'flux_balance_execution_selection_v1', 'environment_realization': 'operation_scoped_tmp_and_cache_v1'}}
    if 'launch_instructions' in selection:
        assignment['launch_instructions'] = deepcopy(selection['launch_instructions'])
    return validate_assignment(assignment)

def _table_exists(store):
    return store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)).fetchone() is not None

def _commission(custody, context):
    saved = custody.store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)).fetchone()
    return custody._commission(context, unsaved=saved is None)

def read_request_binding(store, run_id, episode_id):
    """Read only this host's original control and authenticate its commission."""
    _require(_table_exists(store), 'original_control_missing')
    saved = store.db.execute(f'SELECT file FROM {_TABLE} WHERE run_id=? AND episode_id=?', (run_id, episode_id)).fetchone()
    _require(saved is not None, 'original_control_missing')
    file = validate_flux_balance_record('File', json.loads(saved['file']))
    _require(file['format'] == CONTROL_VERSION, 'control_format_conflict')
    raw = retained_native_file(store, file).read_bytes()
    value = json.loads(raw)
    _require(raw == canonical(value).encode('utf-8') and value['version'] == file['format'] and (value['run_id'] == run_id) and (value['episode_id'] == episode_id), 'control_identity_conflict')
    context = BindingContext(**value['context'])
    custody = AppServiceCustody(store, run_id)
    custody.authenticate(context, allow_unsaved=True)
    _require(is_compact_launch(plain(context.assignment)) if context.role == 'launch' else context.role == 'launch_local' and is_compact_assignment(plain(context.assignment)), 'original_context_conflict')
    for row in value['requests']:
        _require(_materialize(store, row) == row['assignment'], 'materialization_conflict')
    if context.role == 'launch':
        original = plain(context.assignment)
        _require(set(original['requests']) == {row['resource_id'] for row in value['requests']}, 'selection_conflict')
        for row in value['requests']:
            _require(row['selection'] == {**original['requests'][row['resource_id']], 'resource_id': row['resource_id']}, 'selection_conflict')
    else:
        parent, _ = _commission(custody, context)
        original = read_request_binding(store, run_id, parent.episode_id)
        _require(value['parent_file'] == original['file'] and len(value['requests']) == 1 and (value['version'] == original['version']), 'parent_control_conflict')
        row = value['requests'][0]
        _require(row['selection'] == plain(context.assignment) and row in original['requests'], 'selection_conflict')
    return {**deepcopy(value), 'file': file}

def materialized_assignment(store, context):
    control = read_request_binding(store, context.run_id, context.episode_id)
    _require(control['context'] == context.as_record() and len(control['requests']) == 1, 'original_context_conflict')
    return deepcopy(control['requests'][0]['assignment'])

def practical_outcome_view(receipt, *, assignment=None):
    """Project facts under the original control's fixed presentation contract."""
    if receipt is None:
        return None
    facts = receipt['outcome'].get('facts', {})
    job = facts.get('requested_job')
    native = receipt['outcome'].get('native_outcome') or {}
    failure = native.get('failure') or {}
    outputs = [{key: row[key] for key in ('role', 'available', 'bytes', 'writer_closed') if key in row} for row in native.get('observed_outputs', [])]
    if outputs:
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.practical_execution_records import flux_balance_role_paths
        _require(type(assignment) is dict and type(job) is dict and (job.get('requested_job_sha256') == digest(assignment['requested_job'])), 'public_output_request_conflict')
        paths = flux_balance_role_paths(assignment, job, OUTPUT_ROLES)
        _require(len(paths) == len(set(paths)), 'public_output_role_ambiguous')
        roles = {'requested_output:' + path: role for role, path in zip(OUTPUT_ROLES, paths)}
        roles.update({role: role for role in ('stdout', 'stderr')})
        for row in outputs:
            _require(row.get('role') in roles, 'public_output_role_conflict')
            row['role'] = roles[row['role']]
        _require(len(outputs) == len({row['role'] for row in outputs}), 'public_output_role_ambiguous')
    return {'version': PUBLIC_OUTCOME_VERSION, 'operation': receipt['tool_name'], 'job': None if job is None else {key: job[key] for key in ('status', 'returncode')}, 'outputs': outputs, 'failure': {key: failure[key] for key in ('code', 'exception_type', 'errno') if key in failure} or None, 'validations': [{'key': row['key'], 'satisfied': row['satisfied']} for row in receipt['validations']]}

def match_practical_public_outcome(value, receipt, reference, *, assignment=None):
    """Authenticate the exact committed view; pending metadata belongs to runtime."""
    value = deepcopy(plain(value))
    if 'pending_work_after_action' in value:
        from gene_annotation_episode.episodic_workflow.root.a108.waiting import validate_pending
        validate_pending(value.pop('pending_work_after_action'))
    expected = {'status': 'completed', 'record_refs': [reference], 'changed_record_refs': [reference], 'result': practical_outcome_view(receipt, assignment=assignment)}
    _require(canonical(value) == canonical(expected), 'public_outcome_conflict')
