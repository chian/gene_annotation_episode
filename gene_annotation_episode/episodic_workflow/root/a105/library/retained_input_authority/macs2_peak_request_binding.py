"""Explicit scientific MACS2 selections and private host materialization.

The model supplies received File handles and scientific associations. The host
fills only immutable File metadata, actual selected software and execution
coordinates. Existing practical records own the one original native job.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.bvbrc_appservice_custody import AppServiceCustody
from gene_annotation_episode.episodic_workflow.root.a105.communication import plain
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a105.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a105.native_file_capture import _metadata, retained_native_file
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.practical_execution_records import validate_assignment
ASSIGNMENT_VERSION = 'macs2_peak_scientific_assignment_v1'
LAUNCH_VERSION = 'macs2_peak_scientific_launch_v1'
CONTROL_VERSION = 'macs2_peak_request_binding_v1'
PUBLIC_OUTCOME_VERSION = 'macs2_peak_practical_outcome_v1'
OUTPUT_ROLES = ('peaks_xls', 'narrowpeak', 'summits', 'model', 'stdout', 'stderr', 'seal')
_TABLE = 'runtime_macs2_peak_request_bindings'

def _require(condition, code):
    if not condition:
        raise ValueError('macs2_peak_request_' + code)

def _macs2_resource_commission(custody, context):
    saved = custody.store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)).fetchone()
    return custody._commission(context, unsaved=saved is None)

def is_compact_assignment(value):
    return isinstance(value, dict) and value.get('version') == ASSIGNMENT_VERSION

def is_compact_launch(value):
    return isinstance(value, dict) and value.get('version') == LAUNCH_VERSION

def _materialize(store, row):
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_atac_differential_contracts import _dependency_roots
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_macs2_peak_execution import requested_job_from_macs2_peak, validate_macs2_peak_request
    selection = row['selection']
    request = deepcopy(selection['request'])
    bindings = []
    for selected, file in zip(request['inputs'], row['input_files']):
        _require(selected['file'] == {key: file[key] for key in ('artifact_ref', 'format')}, 'input_selection_conflict')
        metadata = _metadata(store, file['artifact_ref'])
        _require(file['artifact_ref'] == 'artifact_' + metadata['sha256'] and metadata['sha256'] == file['sha256'] and (metadata['size'] == file['size_bytes']), 'input_metadata_conflict')
        selected['file'] = deepcopy(file)
        bindings.append({'input_key': selected['input_key'], 'file': deepcopy(file), 'path': str(Path(row['store_path']) / 'artifacts' / file['sha256'][:2] / file['sha256'])})
    request = validate_macs2_peak_request(request)
    software = row['binding']['software']
    driver = software['driver_runtime']
    root = Path(row['workspace']) / '.macs2-selected-runtime' / row['assignment_id']
    environment = dict(PATH='/usr/bin:/bin', LC_ALL='C.UTF-8', PYTHONHOME=str(Path(driver['python_executable']).parent.parent), PYTHONPATH=os.pathsep.join([driver['module_root'], *_dependency_roots(driver)]), PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', TMP=str(root / 'tmp'), TEMP=str(root / 'tmp'), TMPDIR=str(root / 'tmp'), XDG_CACHE_HOME=str(root / 'cache'), PIP_CACHE_DIR=str(root / 'cache/pip'))
    requested = requested_job_from_macs2_peak(dict(request=request, software=deepcopy(software), input_bindings=bindings), environment=environment)
    assignment = dict(version='practical_assignment_v1', assignment_id=row['assignment_id'], resource_id=row['resource_id'], resource_kind='local', workspace=row['workspace'], endpoint=selection['endpoint'], requested_job=requested, progress_requirements=deepcopy(selection['progress_requirements']), completion_keys=deepcopy(selection['completion_keys']), initial_context=dict(revision=0, cwd=row['workspace'], environment={}), inventory_snapshot={}, constraints=deepcopy(selection['constraints']))
    if 'launch_instructions' in selection:
        assignment['launch_instructions'] = deepcopy(selection['launch_instructions'])
    return validate_assignment(assignment)

def read_request_binding(store, run_id, episode_id):
    _require(store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)).fetchone() is not None, 'original_control_missing')
    saved = store.db.execute(f'SELECT file FROM {_TABLE} WHERE run_id=? AND episode_id=?', (run_id, episode_id)).fetchone()
    _require(saved is not None, 'original_control_missing')
    file = json.loads(saved['file'])
    _require(file['format'] == CONTROL_VERSION, 'control_format_conflict')
    raw = retained_native_file(store, file).read_bytes()
    value = json.loads(raw)
    _require(raw == canonical(value).encode() and value['version'] == CONTROL_VERSION and (value['run_id'] == run_id) and (value['episode_id'] == episode_id), 'control_identity_conflict')
    context = BindingContext(**value['context'])
    custody = AppServiceCustody(store, run_id)
    custody.authenticate(context, allow_unsaved=True)
    _require(is_compact_launch(plain(context.assignment)) if context.role == 'launch' else context.role == 'launch_local' and is_compact_assignment(plain(context.assignment)), 'original_context_conflict')
    for row in value['requests']:
        _require(canonical(_materialize(store, row)) == canonical(row['assignment']), 'materialization_conflict')
    if context.role == 'launch':
        original = plain(context.assignment)
        _require(set(original['requests']) == {row['resource_id'] for row in value['requests']}, 'selection_conflict')
        for row in value['requests']:
            _require(canonical(row['selection']) == canonical({**original['requests'][row['resource_id']], 'resource_id': row['resource_id']}), 'selection_conflict')
    else:
        parent, _ = _macs2_resource_commission(custody, context)
        original = read_request_binding(store, run_id, parent.episode_id)
        _require(value['parent_file'] == original['file'] and len(value['requests']) == 1, 'parent_control_conflict')
        row = value['requests'][0]
        _require(canonical(row['selection']) == canonical(plain(context.assignment)) and any((canonical(row) == canonical(candidate) for candidate in original['requests'])), 'selection_conflict')
    return {**deepcopy(value), 'file': file}

def materialized_assignment(store, context):
    control = read_request_binding(store, context.run_id, context.episode_id)
    _require(canonical(control['context']) == canonical(context.as_record()) and len(control['requests']) == 1, 'original_context_conflict')
    return deepcopy(control['requests'][0]['assignment'])

def practical_outcome_view(receipt):
    if receipt is None:
        return None
    job = receipt['outcome'].get('facts', {}).get('requested_job')
    native = receipt['outcome'].get('native_outcome') or {}
    failure = native.get('failure') or {}
    return dict(version=PUBLIC_OUTCOME_VERSION, operation=receipt['tool_name'], job=None if job is None else {key: job[key] for key in ('status', 'returncode')}, failure={key: failure[key] for key in ('code', 'exception_type', 'errno') if key in failure} or None, validations=[{'key': row['key'], 'satisfied': row['satisfied']} for row in receipt['validations']])

def match_practical_public_outcome(value, receipt, reference):
    value = deepcopy(plain(value))
    if 'pending_work_after_action' in value:
        from gene_annotation_episode.episodic_workflow.root.a105.waiting import validate_pending
        validate_pending(value.pop('pending_work_after_action'))
    _require(canonical(value) == canonical(dict(status='completed', record_refs=[reference], changed_record_refs=[reference], result=practical_outcome_view(receipt))), 'public_outcome_conflict')
