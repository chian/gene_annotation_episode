"""Run one finite FBA result worker under the existing native boundary.

The selected action owns a common scratch root. Numerical output and immutable
adapter controls are separate siblings beneath that root; native scratch
accounting covers both. This adapter neither authenticates episode commissions
nor performs scientific parsing/calculation in the host.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
from gene_annotation_episode.episodic_workflow.root.a105 import native_lifecycle as native
from gene_annotation_episode.episodic_workflow.root.a105.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.flux_balance_contracts import validate_flux_balance_record
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.flux_balance_worker_contracts import PLAN_VERSION, validate_flux_balance_worker_plan
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_flux_balance_contracts import ATTEMPT_DIRECTORY_NAME, POLICY, flux_balance_environment, path_value, validate_flux_balance_software
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_flux_balance_storage import decode_json
WORKER_MODULE = 'gene_annotation_episode.flux_balance_result_worker'
EXECUTION_VERSION = 'flux_balance_worker_execution_v1'
_INTENT_VERSION = 'flux_balance_worker_intent_v1'
_SELECTED_INTENT_VERSION = 'flux_balance_worker_intent_v2'
_CONTROL_NAMES = ('plan.json', 'intent.json', 'worker.handle.json', 'worker.stdout', 'worker.stderr', 'execution.json', 'capture.json', '.preparation.lock')
_CGROUP = {'memory_max': POLICY['memory_bytes'], 'memory_swap_max': 0, 'kill_mode': 'control-group', 'oom_policy': 'kill'}

def _require(condition, code):
    if not condition:
        raise ValueError('fba_preparation_' + code)

def _same(left, right):
    return canonical(left) == canonical(right)

def _json(raw):
    value = decode_json(raw)
    canonical(value)
    return value

def _file(value, format_=None):
    value = validate_flux_balance_record('File', value)
    _require(value['artifact_ref'] == 'artifact_' + value['sha256'] and (format_ is None or value['format'] == format_), 'file_invalid')
    return value

def _pin(value):
    _require(type(value) is dict and set(value) == {'path', 'sha256', 'size_bytes'}, 'pin_invalid')
    path_value(value['path'], absolute=True)
    _file({'artifact_ref': 'artifact_' + str(value['sha256']), 'sha256': value['sha256'], 'size_bytes': value['size_bytes'], 'format': 'runtime_file'})
    return value

def _paths(value):
    if type(value) is dict:
        for name, child in value.items():
            if name == 'path' and type(child) is str and child.startswith('/'):
                yield child
            elif name in ('python_home', 'module_root', 'attempt_directory') and type(child) is str:
                yield child
            elif name == 'dependency_roots' and type(child) is list:
                yield from child
            else:
                yield from _paths(child)
    elif type(value) is list:
        for child in value:
            yield from _paths(child)

def _overlap(left, right):
    left, right = (Path(left), Path(right))
    return left == right or left in right.parents or right in left.parents

def _layout(plan):
    output = Path(path_value(plan['directory'], absolute=True))
    root = Path(path_value(plan['directory'] + '.execution', absolute=True))
    common = Path(path_value(str(output.parent), absolute=True))
    selected = list(_paths(plan['original_plan'])) + list(_paths(plan['capture'])) if plan['mode'] == 'native_result' else [plan['sheet']['path']]
    _require(not any((_overlap(common, path) for path in selected)), 'directory_overlap')
    _require(output.parent == root.parent == common and (not _overlap(root, output)), 'directory_overlap')
    return (common, root, output)

def _dependency_roots(rows):
    from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_atac_differential_contracts import _dependency_roots as roots
    return roots({'dependencies': rows})

def _environment(root, common, home, dependencies):
    return {'PYTHONPATH': os.pathsep.join([str(root / 'source_snapshot'), *_dependency_roots(dependencies)]), 'PYTHONHOME': home, 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(common), 'TMP': str(common), 'TEMP': str(common), 'XDG_CACHE_HOME': str(root / 'cache'), 'PIP_CACHE_DIR': str(root / 'cache/pip'), 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}

def _selected_source_pins(software, root):
    selected_root = Path(software['module_root'])
    result = []
    for pin in sorted(software['implementation_files'], key=lambda row: row['path']):
        try:
            relative = Path(pin['path']).relative_to(selected_root)
        except ValueError as error:
            raise ValueError('fba_preparation_selected_source_root_invalid') from error
        _require(relative.parts and '..' not in relative.parts, 'selected_source_root_invalid')
        result.append({**pin, 'path': str(root / 'source_snapshot' / relative)})
    _require({str(root / 'source_snapshot' / 'gene_annotation_episode' / name) for name in ('__init__.py', 'flux_balance_result_worker.py')} <= {pin['path'] for pin in result}, 'selected_worker_source_missing')
    return result

def _selected_environment(root, software):
    environment = flux_balance_environment(software, attempt_directory=str(root / ATTEMPT_DIRECTORY_NAME), lifecycle_directory=str(root))
    environment['PYTHONPATH'] = os.pathsep.join([str(root / 'source_snapshot'), *software['dependency_roots']])
    return environment

def _all_pins(intent):
    if intent['version'] == _SELECTED_INTENT_VERSION:
        return [*intent['source_pins'], intent['interpreter'], *intent['software']['runtime_files'], *intent['software']['solver_runtime_files']]
    return [*intent['source_pins'], intent['interpreter'], *intent['runtime_files'], *(pin for row in intent['dependencies'] for pin in row['files'])]

def _validate_selected_intent(value, plan):
    _require(type(value) is dict and set(value) == {'version', 'plan', 'execution_directory', 'policy', 'command', 'environment', 'source_pins', 'interpreter', 'software'} and (value['version'] == _SELECTED_INTENT_VERSION) and _same(value['plan'], plan) and _same(value['policy'], POLICY), 'intent_mismatch')
    software = validate_flux_balance_software(value['software'])
    _, root, _ = _layout(plan)
    _require(value['execution_directory'] == str(root) and value['command'] == [str(root / 'runtime/python'), '-B', '-S', '-m', WORKER_MODULE, str(root / 'plan.json')], 'intent_mismatch')
    _require(_same(value['source_pins'], _selected_source_pins(software, root)) and _same(value['interpreter'], {**software['python'], 'path': str(root / 'runtime/python')}), 'selected_runtime_mismatch')
    pins = [_pin(pin) for pin in _all_pins(value)]
    _require(len({pin['path'] for pin in pins}) == len(pins), 'duplicate_pin')
    _require(_same(value['environment'], _selected_environment(root, software)), 'environment_mismatch')
    return value

def _validate_intent(value, plan, *, software=None):
    if software is not None:
        selected = validate_flux_balance_software(software)
        _require(type(value) is dict and value.get('version') == _SELECTED_INTENT_VERSION and _same(value.get('software'), selected), 'selected_software_mismatch')
    if type(value) is dict and value.get('version') == _SELECTED_INTENT_VERSION:
        return _validate_selected_intent(value, plan)
    _require(type(value) is dict and set(value) == {'version', 'plan', 'execution_directory', 'policy', 'command', 'environment', 'source_pins', 'interpreter', 'dependencies', 'python_version', 'python_home', 'runtime_files'} and (value['version'] == _INTENT_VERSION) and _same(value['plan'], plan) and _same(value['policy'], POLICY), 'intent_mismatch')
    common, root, _ = _layout(plan)
    path_value(value['python_home'], absolute=True)
    _require(type(value['python_version']) is str and bool(value['python_version']), 'runtime_invalid')
    _require(value['execution_directory'] == str(root) and value['command'] == [str(root / 'runtime/python'), '-B', '-S', '-m', WORKER_MODULE, str(root / 'plan.json')], 'intent_mismatch')
    for field in ('source_pins', 'runtime_files', 'dependencies'):
        _require(type(value[field]) is list and bool(value[field]), 'runtime_missing')
    names = []
    for row in value['dependencies']:
        _require(type(row) is dict and set(row) == {'distribution', 'version', 'package_root', 'files'} and all((type(row[k]) is str and bool(row[k]) for k in ('distribution', 'version', 'package_root'))) and (type(row['files']) is list) and bool(row['files']), 'dependency_invalid')
        path_value(row['package_root'], absolute=True)
        names.append(row['distribution'])
    _require(len(names) == len(set(names)), 'dependency_invalid')
    pins = [_pin(pin) for pin in _all_pins(value)]
    _require(len({p['path'] for p in pins}) == len(pins), 'duplicate_pin')
    source_root = root / 'source_snapshot'
    _require(all((Path(p['path']).is_relative_to(source_root) for p in value['source_pins'])) and str(source_root / 'gene_annotation_episode/flux_balance_result_worker.py') in {p['path'] for p in value['source_pins']} and (str(source_root / 'gene_annotation_episode/__init__.py') in {p['path'] for p in value['source_pins']}) and (value['interpreter']['path'] == str(root / 'runtime/python')), 'source_missing')
    _require(all((Path(p['path']).is_relative_to(Path(value['python_home']) / 'lib') for p in value['runtime_files'])), 'runtime_invalid')
    _require(_same(value['environment'], _environment(root, common, value['python_home'], value['dependencies'])), 'environment_mismatch')
    return value

def _controls(body, request, intent):
    common, root, output = _layout(intent['plan'])
    _require(type(body) is dict and body.get('version') == native.VERSION and (body.get('stage') in ('prepared', 'submitting', 'released')) and (body.get('command') == intent['command']) and (body.get('cwd') == str(common)) and (type(body.get('metadata')) is dict) and _same(body['metadata'].get('policy'), POLICY) and (body.get('stdout') == str(root / 'worker.stdout')) and (body.get('stderr') == str(root / 'worker.stderr')), 'handle_mismatch')
    paths = body.get('paths')
    keys = {'request', 'ready', 'release', 'status', 'result', 'launcher'}
    _require(type(paths) is dict and set(paths) == keys and all((type(p) is str for p in paths.values())), 'handle_paths_invalid')
    for path in paths.values():
        path_value(path, absolute=True)
    token = Path(paths['request']).name.removesuffix('.request')
    _require(re.fullmatch('\\.local-job-[0-9a-f]{32}', token) is not None and paths == {name: str(common / (token + '.' + name)) for name in keys}, 'handle_paths_invalid')
    fixed = {str(root / name) for name in _CONTROL_NAMES} | {str(root), str(output)}
    _require(len(set(paths.values())) == len(paths) and (not fixed.intersection(paths.values())), 'handle_paths_invalid')
    expected = {'command': intent['command'], 'cwd': str(common), 'file_bytes': POLICY['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'], 'stdin_path': None, 'env': intent['environment']}
    _require(_same(request, expected), 'request_mismatch')
    return body

def validate_flux_balance_worker_execution(value, *, plan, plan_file):
    """Validate original frozen execution records without current runtime I/O."""
    plan = validate_flux_balance_worker_plan(plan)
    _file(plan_file, PLAN_VERSION)
    _require(type(value) is dict and set(value) == {'version', 'plan_file', 'intent', 'terminal', 'quiescent', 'policy', 'returncode', 'metadata', 'failure', 'handle_file', 'request_file', 'stdout_file', 'stderr_file', 'handle', 'request', 'request_raw'} and (value['version'] == EXECUTION_VERSION) and _same(value['plan_file'], plan_file) and (value['terminal'] is True) and (value['quiescent'] is True) and _same(value['policy'], POLICY), 'execution_mismatch')
    for name, format_ in (('plan_file', PLAN_VERSION), ('handle_file', native.VERSION), ('request_file', 'native_local_job_request'), ('stdout_file', 'native_worker_stdout'), ('stderr_file', 'native_worker_stderr')):
        _file(value[name], format_)
    intent = _validate_intent(value['intent'], plan)
    body = _controls(value['handle'], value['request'], intent)
    _require(type(value['request_raw']) is str, 'request_mismatch')
    raw = value['request_raw'].encode('utf-8')
    _require(_same(_json(raw), value['request']) and hashlib.sha256(raw).hexdigest() == body.get('request_sha256') == value['request_file']['sha256'] and (len(raw) == value['request_file']['size_bytes']), 'request_mismatch')
    meta = value['metadata']
    _require(type(meta) is dict and _same(meta.get('policy'), POLICY) and (type(meta.get('service_exit')) is dict) and _same(meta.get('verified_cgroup'), _CGROUP), 'allocation_mismatch')
    if value['failure'] is None:
        _require(type(value['returncode']) is int and _same(meta.get('native_returncode'), value['returncode']), 'exit_mismatch')
    else:
        failure = value['failure']
        _require(value['returncode'] is None and type(failure) is dict and (set(failure) == {'code', 'phase', 'diagnostic', 'operational'}) and (type(failure['code']) is str) and bool(failure['code']), 'exit_mismatch')
    canonical(value)
    return deepcopy(value)
