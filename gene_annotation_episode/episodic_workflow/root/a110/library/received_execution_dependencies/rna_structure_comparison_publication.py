from __future__ import annotations
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a110.materials import artifact_path
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_contracts import CALCULATOR_VERSION, validate_rna_comparison_selector
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_inputs import populate_rna_comparison_sheet
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_calculations import calculate_rna_comparison_components
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_views import project_rna_comparison
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_worker import PLAN_VERSION, RESULT_VERSION, RESULT_FIELDS, _absolute, _decode, _json_bytes, _key, _require, _sha, _validate_plan, comparison_input_digests, comparison_calculation_key
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_result_views import result_receipt_key as original_receipt_key
RESOLVED_VERSION = 'rna_structure_comparison_resolved_operands_v1'
PREPARED_VERSION = 'rna_structure_comparison_prepared_v1'
PREPARED_FIELDS = {'version', 'selector_sha256', 'input_data_sha256', 'original_receipt_keys', 'selected_input_digests', 'result_receipt_key', 'calculation_key', 'comparison_sheet_artifact_ref', 'comparison_sheet_sha256', 'components_artifact_ref', 'components_sha256', 'calculator_version', 'projection_rows_artifact_ref', 'worker_receipt_artifact_ref', 'projection_rows', 'issues', 'preparation_failure', 'delivery_complete'}
POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4294967296}
_WORKER = 'gene_annotation_episode.rna_structure_comparison_worker'
_OUTPUTS = {'sheet': 'sheet.json', 'components': 'components.json', 'projections': 'projections.json', 'worker_result': 'worker-result.json'}
_RECEIPT_VERSION = 'rna_structure_comparison_worker_receipt_v1'
_EXECUTION_VERSION = 'rna_structure_comparison_worker_execution_v1'
_INTENT_VERSION = 'rna_structure_comparison_preparation_intent_v1'
_START_VERSION = 'rna_structure_comparison_worker_start_v1'
_RECEIPT_FIELDS = {'version', 'intent_artifact_ref', 'plan_artifact_ref', 'input_data_artifact_ref', 'worker_start_artifact_ref', 'execution_receipt_artifact_ref', 'output_artifacts', 'input_observation', 'capture_errors'}
_EXECUTION_FIELDS = {'version', 'returncode', 'metadata', 'stdout_artifact_ref', 'stderr_artifact_ref', 'error'}

def _same(left, right):
    return canonical(left) == canonical(right)

def _resolved(selector, operands):
    selector = validate_rna_comparison_selector(selector)
    _require(type(operands) is dict and set(operands) == {'version', 'data', 'original_receipts', 'selected_references'} and (operands['version'] == RESOLVED_VERSION), 'rna_comparison_operand_mismatch')
    digests = comparison_input_digests(selector, operands['data'])
    members = [m for m in selector['question']['membership'] if m['kind'] in ('saved_sheet', 'received_failure')]
    originals = operands['original_receipts']
    _require(type(originals) is dict and set(originals) == {m['member_id'] for m in members}, 'rna_comparison_original_receipt_mismatch')
    keys = []
    for member in members:
        receipt = originals[member['member_id']]
        _require(type(receipt) is dict and all((type(receipt.get(k)) is str and receipt[k] for k in ('run_id', 'episode_id', 'operation_key'))), 'rna_comparison_original_receipt_mismatch')
        key = original_receipt_key(receipt)
        selected = member['saved_input' if member['kind'] == 'saved_sheet' else 'failure']
        _require(key == selected['result_receipt_key'], 'rna_comparison_original_receipt_mismatch')
        if member['kind'] == 'saved_sheet':
            original = operands['data'][member['member_id']]['original_sheet']
            _require(_sha(_json_bytes(original)) == selected['sheet_sha256'], 'rna_comparison_retained_input_digest_mismatch')
        keys.append(key)
    references = operands['selected_references']
    _require(type(references) is list and all((type(ref) is str and ref and (not any((c in ref for c in '\x00\r\n'))) for ref in references)) and (len(references) == len(set(references))), 'rna_comparison_operand_mismatch')
    return (selector, keys, digests)

def _raw(store, reference):
    metadata = store._require(reference, {'artifact'})
    _require(reference == 'artifact_' + metadata['sha256'], 'rna_comparison_artifact_mismatch')
    path = artifact_path(store, reference)
    raw = path.read_bytes()
    _require(len(raw) == metadata['size'] and _sha(raw) == metadata['sha256'], 'rna_comparison_artifact_mismatch')
    return raw

def _artifact_value(store, reference):
    return _decode(_raw(store, reference))

def _failure(code, role=None):
    return {'code': code, 'member_id': None, 'artifact_role': role}

def _environment(directory):
    return {'PYTHONPATH': str(Path(__file__).resolve().parents[6]), 'PYTHONDONTWRITEBYTECODE': '1', **{key: str(directory / 'tmp') for key in ('TMPDIR', 'TMP', 'TEMP')}, 'XDG_CACHE_HOME': str(directory / 'cache'), 'PIP_CACHE_DIR': str(directory / 'cache' / 'pip')}

def _intent(selector, operands, key, directory):
    return {'version': _INTENT_VERSION, 'selector': selector, 'operands': operands, 'result_receipt_key': key, 'directory': str(directory), 'policy': POLICY}

def _read_context(store, receipt, *, selector, operands, key):
    """Check the worker's complete immutable request chain, never E authority."""
    _require(type(receipt) is dict and set(receipt) == _RECEIPT_FIELDS and (receipt['version'] == _RECEIPT_VERSION))
    intent = _artifact_value(store, receipt['intent_artifact_ref'])
    _require(type(intent) is dict and type(intent.get('directory')) is str)
    directory = _absolute(intent['directory'])
    _require(_same(intent, _intent(selector, operands, key, directory)), 'rna_comparison_intent_mismatch')
    plan = _artifact_value(store, receipt['plan_artifact_ref'])
    _validate_plan(plan)
    data_raw = _raw(store, receipt['input_data_artifact_ref'])
    _require(data_raw == _json_bytes(operands['data']), 'rna_comparison_input_digest_mismatch')
    expected_plan = {'version': PLAN_VERSION, 'selector': selector, 'input_data': {'path': str(directory / 'input-data.json'), 'sha256': _sha(data_raw), 'size_bytes': len(data_raw)}, 'result_receipt_key': key, 'calculation_key': comparison_calculation_key(selector, operands['data']), 'directory': str(directory)}
    _require(_same(plan, expected_plan), 'rna_comparison_plan_mismatch')
    start = _artifact_value(store, receipt['worker_start_artifact_ref'])
    _require(type(start) is dict and set(start) == {'version', 'plan_sha256', 'command', 'cwd', 'policy', 'environment'} and (start['version'] == _START_VERSION) and (start['plan_sha256'] == _sha(_json_bytes(plan))) and (start['cwd'] == str(directory)) and _same(start['policy'], POLICY), 'rna_comparison_start_mismatch')
    command = start['command']
    _require(type(command) is list and len(command) == 5 and (type(command[0]) is str) and Path(command[0]).is_absolute() and (command[1:] == ['-B', '-m', _WORKER, str(directory / 'plan.json')]), 'rna_comparison_start_mismatch')
    env = start['environment']
    expected_env = _environment(directory)
    _require(type(env) is dict and set(env) == set(expected_env) and (type(env['PYTHONPATH']) is str) and Path(env['PYTHONPATH']).is_absolute() and all((env[name] == value for name, value in expected_env.items() if name != 'PYTHONPATH')), 'rna_comparison_start_mismatch')
    execution = _artifact_value(store, receipt['execution_receipt_artifact_ref'])
    _require(type(execution) is dict and set(execution) == _EXECUTION_FIELDS and (execution['version'] == _EXECUTION_VERSION))
    _require(execution['returncode'] is None or type(execution['returncode']) is int)
    _require(execution['metadata'] is None or type(execution['metadata']) is dict)
    _require(execution['error'] is None or type(execution['error']) is dict)
    for name in ('stdout_artifact_ref', 'stderr_artifact_ref'):
        if execution[name] is not None:
            _raw(store, execution[name])
    if execution['returncode'] == 0 and execution['error'] is None:
        metadata = execution['metadata']
        _require(metadata is not None and _same(metadata.get('policy'), POLICY) and (metadata.get('verified_cgroup', {}).get('memory_max') == POLICY['memory_bytes']) and (metadata.get('verified_cgroup', {}).get('memory_swap_max') == 0) and (execution['stdout_artifact_ref'] is not None) and (execution['stderr_artifact_ref'] is not None), 'rna_comparison_worker_receipt_mismatch')
    outputs = receipt['output_artifacts']
    _require(type(outputs) is list and all((type(row) is dict and set(row) == {'role', 'artifact_ref', 'sha256'} and (row['role'] in _OUTPUTS) for row in outputs)))
    roles = [row['role'] for row in outputs]
    _require(roles == [role for role in _OUTPUTS if role in roles])
    raw_outputs = {}
    for row in outputs:
        raw = _raw(store, row['artifact_ref'])
        _require(_sha(raw) == row['sha256'], 'rna_comparison_artifact_mismatch')
        raw_outputs[row['role']] = raw
    observed = receipt['input_observation']
    _require(type(observed) is dict and set(observed) == {'artifact_ref', 'error'})
    _require(observed['error'] is None or type(observed['error']) is dict)
    observed_raw = None if observed['artifact_ref'] is None else _raw(store, observed['artifact_ref'])
    _require(observed_raw is not None or observed['error'] is not None)
    _require(type(receipt['capture_errors']) is list and all((type(e) is dict and set(e) == {'role', 'error'} and (e['role'] in _OUTPUTS) and (type(e['error']) is dict) for e in receipt['capture_errors'])))
    return (plan, execution, raw_outputs, observed_raw)

def _derive(store, receipt_ref, *, selector, operands, result_receipt_key):
    selector, original_keys, input_digests = _resolved(selector, operands)
    _key(result_receipt_key, 'rna_comparison_receipt')
    receipt = _artifact_value(store, receipt_ref)
    plan, execution, raw_outputs, observed_input = _read_context(store, receipt, selector=selector, operands=operands, key=result_receipt_key)
    failure = None
    if observed_input is None:
        failure = _failure('retained_input_missing', 'input_data')
    elif observed_input != _json_bytes(operands['data']):
        failure = _failure('retained_input_digest_mismatch', 'input_data')
    elif execution['returncode'] != 0 or execution['error'] is not None:
        failure = _failure('calculation_worker_failed')
    elif receipt['capture_errors']:
        failure = _failure('calculation_output_invalid', receipt['capture_errors'][0]['role'])
    artifacts = {row['role']: row for row in receipt['output_artifacts']}
    expected_sheet = populate_rna_comparison_sheet(selector, operands=_decode(_json_bytes(operands['data'])))
    valid, values = ({}, {'sheet': None, 'components': None, 'projections': []})
    for role in ('sheet', 'components', 'projections'):
        try:
            _require(role in raw_outputs, 'rna_comparison_output_missing')
            value = _decode(raw_outputs[role])
            if role == 'sheet':
                expected = expected_sheet
            elif role == 'components':
                _require(values['sheet'] is not None)
                expected = calculate_rna_comparison_components(expected_sheet)
            else:
                _require(values['components'] is not None)
                expected = project_rna_comparison(expected_sheet, values['components'], projections=selector['projections'], result_receipt_key=result_receipt_key, calculation_key=plan['calculation_key'])
            _require(_same(value, expected), 'rna_comparison_output_mismatch')
            valid[role], values[role] = (artifacts[role], value)
        except (ValueError, TypeError, KeyError, OverflowError):
            failure = failure or _failure('calculation_output_invalid', role)
    try:
        _require('worker_result' in raw_outputs)
        manifest = _decode(raw_outputs['worker_result'])
        _require(type(manifest) is dict and set(manifest) == RESULT_FIELDS)
        expected = {'version': RESULT_VERSION, 'input_data_sha256': plan['input_data']['sha256'], 'sheet_file': 'sheet.json', 'sheet_sha256': _sha(raw_outputs['sheet']), 'components_file': 'components.json', 'components_sha256': _sha(raw_outputs['components']), 'projection_rows_file': 'projections.json', 'projection_rows_sha256': _sha(raw_outputs['projections']), 'calculator_version': CALCULATOR_VERSION, 'result_receipt_key': result_receipt_key, 'calculation_key': plan['calculation_key']}
        _require(_same(manifest, expected), 'rna_comparison_output_mismatch')
    except (ValueError, TypeError, KeyError):
        failure = failure or _failure('calculation_output_invalid', 'worker_result')
    prepared = {'version': PREPARED_VERSION, 'selector_sha256': digest(selector), 'input_data_sha256': plan['input_data']['sha256'], 'original_receipt_keys': original_keys, 'selected_input_digests': input_digests, 'result_receipt_key': result_receipt_key, 'calculation_key': plan['calculation_key'], 'comparison_sheet_artifact_ref': valid.get('sheet', {}).get('artifact_ref'), 'comparison_sheet_sha256': valid.get('sheet', {}).get('sha256'), 'components_artifact_ref': valid.get('components', {}).get('artifact_ref'), 'components_sha256': valid.get('components', {}).get('sha256'), 'calculator_version': CALCULATOR_VERSION, 'projection_rows_artifact_ref': valid.get('projections', {}).get('artifact_ref'), 'worker_receipt_artifact_ref': receipt_ref, 'projection_rows': values['projections'], 'issues': deepcopy(values['components']['issues'] if values['components'] is not None else values['sheet']['issues'] if values['sheet'] is not None else []), 'preparation_failure': failure, 'delivery_complete': failure is None}
    return (prepared, {'sheet': values['sheet'], 'components': values['components'], 'projection_rows': values['projections']})

def validate_prepared_rna_comparison(store, prepared: dict, *, selector: dict, operands: dict, result_receipt_key: str) -> dict:
    """Check bytes, exact input reconstruction, all numbers and selected views."""
    _require(type(prepared) is dict and set(prepared) == PREPARED_FIELDS and (prepared['version'] == PREPARED_VERSION))
    expected, checked = _derive(store, prepared['worker_receipt_artifact_ref'], selector=selector, operands=operands, result_receipt_key=result_receipt_key)
    _require(_same(prepared, expected), 'rna_comparison_prepared_mismatch')
    return deepcopy(checked)
