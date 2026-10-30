"""FBA capability metadata and opaque file observations; no scientific run.

Compact plans/software and malformed files are deliberately synthetic. Only the
two retained688 cases use authentic previous native output, never another solve.
"""
import base64
import builtins
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_flux_balance_bindings import (
    FLUX_BALANCE_BINDING_SCHEMA, flux_balance_binding_accepts_job,
    validate_flux_balance_bindings,
)
from gene_annotation_episode.native_flux_balance_contracts import (
    ATTEMPT_DIRECTORY_NAME, ENVIRONMENT_FILENAME, OWNER_FILENAME, POLICY,
    SOURCE_FUNCTION_SHA256, STARTED_FILENAME, bind_flux_balance_environment,
    flux_balance_environment, flux_balance_output_files, validate_flux_balance_run_plan,
)
from gene_annotation_episode.native_flux_balance_observations import (
    flux_balance_observed_files, read_flux_balance_output,
)
from test_flux_balance_operands_694 import software


pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires bounded529')
ROOT = Path(__file__).resolve().parents[1]
EMITTED = ROOT / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions'
SELECTION = {'version': 'flux_balance_execution_selection_v1',
    'environment_realization': 'operation_scoped_tmp_and_cache_v1'}


@pytest.fixture
def job():
    return {'version': 'native_flux_balance_job_v1', 'operation': 'perform_flux_balance_analysis',
        'mode': 'steady_state_linear_fba',
        'source_alias': 'biomni.tool.systems_biology.perform_flux_balance_analysis',
        'source_function_sha256': SOURCE_FUNCTION_SHA256, 'software': software(),
        'model_input': {'file': {'path': '/synthetic705/input.json', 'sha256': 'a' * 64, 'size_bytes': 1},
            'artifact_ref': None, 'format': 'cobra_json', 'original_loader_selection': 'json_file',
            'repository_identifier': None, 'acquisition_receipt_file': None},
        'constraints': None, 'objective': {'kind': 'model_default', 'reaction_id': None},
        'solver_options': {'feasibility_tolerance': None, 'optimality_tolerance': None,
            'integrality_tolerance': None}, 'output_prefix': 'outputs', 'flux_output_name': 'flux.csv'}


@pytest.fixture
def binding(job):
    return {'version': 'flux_balance_local_binding_v1', 'operation': job['operation'],
        'mode': job['mode'], 'software': deepcopy(job['software']), 'model_formats': ['sbml', 'cobra_json']}


@pytest.fixture
def plan(job, tmp_path):
    owner = {'run_id': 'fba705', 'episode_id': 'local705', 'resource_id': 'selected-local',
        'operation_key': 'original selected start', 'attempt_id': digest('original selected start'),
        'assignment_sha256': digest({'fixture': 'synthetic705'})}
    root = tmp_path / '.episode-operations' / digest({'run': owner['run_id'], 'episode': owner['episode_id']}) / owner['attempt_id']
    request = {'argv': [job['software']['python']['path'], '-B', '-S', '-m',
        'gene_annotation_episode.native_flux_balance_driver', 'flux-balance-plan.json'],
        'environment': flux_balance_environment(job['software'], attempt_directory='/synthetic705/selected/flux-balance-attempt',
            lifecycle_directory='/synthetic705/selected'), 'native_flux_balance': job}
    owner.update(execution_id=str(root / 'native.json'), requested_job_sha256=digest(request))
    value = {'version': 'flux_balance_run_plan_v2', 'identity': owner, 'requested_job': request,
        'attempt_directory': str(root / ATTEMPT_DIRECTORY_NAME), 'policy': deepcopy(POLICY),
        'outputs': flux_balance_output_files(job)}
    value['environment_binding'] = bind_flux_balance_environment(request, execution_id=owner['execution_id'],
        attempt_directory=value['attempt_directory'], selection=SELECTION)
    return validate_flux_balance_run_plan(value)


def _files(plan, *, native=True, lifecycle=True, omit=()):
    values = {}
    if native:
        for i, row in enumerate(plan['outputs']):
            if row['role'] in omit:
                continue
            path = Path(plan['attempt_directory']) / row['relative_path']
            raw = (row['role'] + ':opaque\n').encode() + bytes([255, 254, i])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            values[row['role']] = (path, raw)
    if lifecycle:
        root = Path(plan['identity']['execution_id']).parent
        root.mkdir(parents=True, exist_ok=True)
        for role in ('stdout', 'stderr'):
            raw = (role + ':0123456789\n').encode()
            path = root / (role + '.log');path.write_bytes(raw)
            values[role] = (path, raw)
    return values


def _observe(plan, *, terminal=True, quiescent=True, logs=(), window=7):
    return flux_balance_observed_files(plan, {'terminal': terminal, 'quiescent': quiescent},
        log_window_bytes=window, log_roles=logs)


def test_binding_schema_detached_and_empty_selection(binding):
    before = deepcopy(binding)
    Draft202012Validator.check_schema(FLUX_BALANCE_BINDING_SCHEMA)
    assert Draft202012Validator(FLUX_BALANCE_BINDING_SCHEMA).is_valid(binding)
    result, = validate_flux_balance_bindings([binding])
    result['model_formats'].reverse();result['software']['python_version'] = 'changed'
    assert binding == before and validate_flux_balance_bindings([]) == []


@pytest.mark.parametrize('formats', [['sbml'], ['cobra_json'], ['cobra_json', 'sbml']])
@pytest.mark.parametrize('format_', ['sbml', 'cobra_json'])
def test_binding_matches_actual_selected_format_without_substitution(binding, job, formats, format_):
    binding['model_formats'] = formats
    job['model_input']['format'] = format_
    job['model_input']['original_loader_selection'] = 'sbml_file' if format_ == 'sbml' else 'json_file'
    assert flux_balance_binding_accepts_job(binding, job) is (format_ in formats)
    job['software']['python']['sha256'] = 'b' * 64
    assert not flux_balance_binding_accepts_job(binding, job)


@pytest.mark.parametrize('fault', ['row_type', 'extra', 'version', 'operation', 'mode', 'formats_type',
    'empty_formats', 'duplicate_formats', 'unknown_format', 'bool_format', 'missing_software',
    'wrong_solver', 'wrong_distribution', 'bool_size', 'nonfinite_size'])
def test_binding_rejects_unsupported_or_invalid_metadata(binding, fault):
    if fault == 'row_type': binding = []
    elif fault == 'extra': binding['path'] = '/unselected'
    elif fault in ('version', 'operation', 'mode'): binding[fault] = 'automatic'
    elif fault == 'formats_type': binding['model_formats'] = 'cobra_json'
    elif fault == 'empty_formats': binding['model_formats'] = []
    elif fault == 'duplicate_formats': binding['model_formats'] = ['sbml', 'sbml']
    elif fault == 'unknown_format': binding['model_formats'] = ['matlab']
    elif fault == 'bool_format': binding['model_formats'] = [True]
    elif fault == 'missing_software': del binding['software']
    elif fault == 'wrong_solver': binding['software']['solver_interface'] = 'optlang.unselected_interface'
    elif fault == 'wrong_distribution': binding['software']['distributions'][0]['version'] = 'unselected'
    elif fault == 'bool_size': binding['software']['python']['size_bytes'] = True
    else: binding['software']['python']['size_bytes'] = float('inf')
    with pytest.raises(ValueError): validate_flux_balance_bindings([binding])


def test_duplicate_rows_and_invalid_jobs_are_errors(binding, job):
    with pytest.raises(ValueError, match='duplicate'): validate_flux_balance_bindings([binding, deepcopy(binding)])
    with pytest.raises(ValueError): validate_flux_balance_bindings(binding)
    job['model_input']['format'] = 'automatic'
    with pytest.raises(ValueError): flux_balance_binding_accepts_job(binding, job)


def test_binding_validation_performs_no_io_or_scientific_work(binding, job, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('metadata validation performed work')
    original = builtins.__import__
    def imports(name, *args, **kwargs):
        if any(word in name for word in ('cobra', 'optlang', 'swiglpk', 'flux_balance_readers',
            'flux_balance_sheet', 'flux_balance_calculations', 'native_flux_balance_driver')): forbidden()
        return original(name, *args, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(builtins, 'open', forbidden);m.setattr(io, 'open', forbidden)
        m.setattr(socket, 'socket', forbidden);m.setattr(subprocess, 'run', forbidden);m.setattr(subprocess, 'Popen', forbidden)
        m.setattr(builtins, '__import__', imports)
        assert validate_flux_balance_bindings([binding]) == [binding]
        assert flux_balance_binding_accepts_job(binding, job)


@pytest.mark.parametrize('terminal,quiescent', [(False, False), (False, True), (True, False), (True, True)])
def test_native_order_and_actual_writer_closure_both_required(plan, terminal, quiescent):
    values = _files(plan)
    outputs, logs, available = _observe(plan, terminal=terminal, quiescent=quiescent)
    assert len(outputs) == 10 and logs == [] and available
    assert [r['role'] for r in outputs] == ['requested_output:' + str(Path(plan['attempt_directory']) / r['relative_path'])
        for r in plan['outputs']] + ['stdout', 'stderr']
    assert all(r['writer_closed'] is (terminal and quiescent) for r in outputs)
    assert [r['bytes'] for r in outputs] == [len(values[r['role']][1]) for r in plan['outputs']] + [len(values[r][1]) for r in ('stdout', 'stderr')]


def test_absent_attempt_and_missing_parent_directories_are_unavailable(plan):
    outputs, logs, available = _observe(plan, logs=('native_log', 'stdout', 'stderr'))
    assert not available and not logs and len(outputs) == 10
    assert all(r == {'role': r['role'], 'available': False, 'bytes': None, 'writer_closed': False} for r in outputs)
    assert not Path(plan['attempt_directory']).exists()


def test_missing_manifest_does_not_erase_available_siblings(plan):
    _files(plan, omit=('manifest',))
    outputs, logs, available = _observe(plan, logs=('native_log',))
    assert available and len(logs) == 1
    assert sum(r['available'] for r in outputs[:8]) == 7
    assert outputs[7]['available'] is False and outputs[7]['bytes'] is None


@pytest.mark.parametrize('native', [False, True])
def test_empty_file_is_available_without_inventing_scientific_progress(plan, native):
    values = _files(plan, native=False)
    target = Path(plan['attempt_directory']) / plan['outputs'][5]['relative_path'] if native else values['stdout'][0]
    target.parent.mkdir(parents=True, exist_ok=True);target.write_bytes(b'')
    outputs, _, available = _observe(plan)
    row = outputs[5] if native else outputs[8]
    assert row['available'] and row['bytes'] == 0 and row['writer_closed']
    assert available is native


@pytest.mark.parametrize('roles', [('native_log', 'stderr', 'stdout'), ['stderr', 'native_log'], ()])
def test_selected_log_order_and_exact_opaque_tail_bytes(plan, roles):
    values = _files(plan)
    _, logs, _ = _observe(plan, logs=roles, window=7)
    assert [r['role'] for r in logs] == list(roles)
    for row in logs:
        path, raw = values[row['role']]
        assert row['path'] == str(path) and row['observed_size'] == len(raw)
        assert row['offset'] == max(0, len(raw) - 7)
        assert base64.b64decode(row['bytes_base64']) == raw[-7:]


def test_only_original_declared_outputs_and_lifecycle_logs_can_be_read(plan):
    values = _files(plan)
    for path, raw in values.values():
        result = read_flux_balance_output(plan, path=str(path), offset=2, limit=7)
        assert result == {'path': str(path), 'offset': 2, 'returned_bytes': len(raw[2:9]),
            'size_bytes': len(raw), 'bytes_base64': base64.b64encode(raw[2:9]).decode(),
            'text_utf8': raw[2:9].decode('utf-8', errors='replace')}
    path, raw = values['native_log']
    end = read_flux_balance_output(plan, path=str(path), offset=len(raw) + 5, limit=1)
    assert end['returned_bytes'] == 0 and end['offset'] == len(raw) + 5 and end['size_bytes'] == len(raw)


@pytest.mark.parametrize('field', ['owner', 'started', 'environment', 'binding', 'model', 'software', 'sibling', 'alternate', 'type'])
def test_internal_controls_inputs_and_other_attempts_are_not_readable(plan, field):
    attempt = Path(plan['attempt_directory']);root = Path(plan['identity']['execution_id']).parent
    paths = {'owner': attempt / OWNER_FILENAME, 'started': attempt / STARTED_FILENAME,
        'environment': attempt / ENVIRONMENT_FILENAME, 'binding': root / 'flux-balance-input-binding.json',
        'model': plan['requested_job']['native_flux_balance']['model_input']['file']['path'],
        'software': plan['requested_job']['native_flux_balance']['software']['python']['path'],
        'sibling': attempt / 'unselected.txt', 'alternate': root.parent / 'another/flux.csv', 'type': []}
    path = paths[field];path = str(path) if isinstance(path, Path) else path
    with pytest.raises(ValueError, match='original_output_path_required'):
        read_flux_balance_output(plan, path=path, offset=0, limit=1)


@pytest.mark.parametrize('offset,limit', [(True, 1), (-1, 1), (0.5, 1), (0, True), (0, 0), (0, -1), (0, 1048577)])
def test_bounded_window_coordinates_are_strict_integers(plan, offset, limit):
    path = str(Path(plan['attempt_directory']) / plan['outputs'][0]['relative_path'])
    with pytest.raises(ValueError, match='bounded_native_output_window_required'):
        read_flux_balance_output(plan, path=path, offset=offset, limit=limit)


@pytest.mark.parametrize('fault', ['window_bool', 'window_zero', 'duplicate_roles', 'unknown_role', 'role_type',
    'terminal_bool', 'quiescent_bool', 'missing_terminal', 'missing_quiescent'])
def test_observation_selection_and_closure_must_be_explicit(plan, fault):
    view = {'terminal': True, 'quiescent': True};roles = ();window = 1
    if fault == 'window_bool': window = True
    elif fault == 'window_zero': window = 0
    elif fault == 'duplicate_roles': roles = ['native_log', 'native_log']
    elif fault == 'unknown_role': roles = ['inferred_progress']
    elif fault == 'role_type': roles = [True]
    elif fault == 'terminal_bool': view['terminal'] = 1
    elif fault == 'quiescent_bool': view['quiescent'] = 1
    elif fault == 'missing_terminal': del view['terminal']
    else: del view['quiescent']
    with pytest.raises(ValueError): flux_balance_observed_files(plan, view, log_window_bytes=window, log_roles=roles)


@pytest.mark.parametrize('fault', ['file_symlink', 'parent_symlink', 'directory', 'fifo'])
def test_symlink_and_nonregular_output_is_technical_failure(plan, tmp_path, fault):
    values = _files(plan)
    path = values['original_model'][0]
    if fault == 'parent_symlink':
        parent = path.parent;destination = tmp_path / 'elsewhere';parent.rename(destination);parent.symlink_to(destination, target_is_directory=True)
    else:
        path.unlink()
        if fault == 'file_symlink':
            other = tmp_path / 'elsewhere';other.write_bytes(b'unselected');path.symlink_to(other)
        elif fault == 'directory': path.mkdir()
        else: os.mkfifo(path)
    with pytest.raises((ValueError, OSError)): _observe(plan)
    with pytest.raises((ValueError, OSError)): read_flux_balance_output(plan, path=str(path), offset=0, limit=1)


def test_observations_never_poll_parse_acquire_or_dispatch(plan, monkeypatch):
    _files(plan)
    def forbidden(*args, **kwargs): raise AssertionError('file observation attempted execution or scientific work')
    original = builtins.__import__
    def imports(name, *args, **kwargs):
        if any(word in name for word in ('cobra', 'optlang', 'swiglpk', 'flux_balance_readers',
            'flux_balance_sheet', 'flux_balance_calculations', 'native_flux_balance_driver', 'state', 'native_lifecycle')): forbidden()
        return original(name, *args, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(subprocess, 'run', forbidden);m.setattr(subprocess, 'Popen', forbidden);m.setattr(socket, 'socket', forbidden)
        m.setattr(builtins, '__import__', imports)
        assert _observe(plan, logs=('native_log',))[2]


@pytest.mark.parametrize('format_', ['sbml', 'cobra_json'])
def test_actual_retained688_native_formats_keep_exact_declared_file_bytes(format_):
    plan = json.loads((EMITTED / format_ / 'selected-plan.json').read_text())
    outputs, logs, available = _observe(plan, logs=('native_log',), window=31)
    assert available and len(outputs) == 10
    actual_sizes = []
    for row, observed in zip(plan['outputs'], outputs):
        path = Path(plan['attempt_directory']) / row['relative_path']
        actual_sizes.append(path.stat().st_size)
        assert observed == {'role': 'requested_output:' + str(path), 'available': True,
            'bytes': path.stat().st_size, 'writer_closed': True}
    assert sum(actual_sizes) == (5533618 if format_ == 'sbml' else 5495431)
    log = next(row for row in plan['outputs'] if row['role'] == 'native_log')
    path = Path(plan['attempt_directory']) / log['relative_path'];raw = path.read_bytes()
    assert len(logs) == 1 and logs[0]['role'] == 'native_log'
    assert base64.b64decode(logs[0]['bytes_base64']) == raw[-31:]
    csv = next(row for row in plan['outputs'] if row['role'] == 'flux_csv')
    path = Path(plan['attempt_directory']) / csv['relative_path'];raw = path.read_bytes()
    selected = read_flux_balance_output(plan, path=str(path), offset=3, limit=17)
    assert base64.b64decode(selected['bytes_base64']) == raw[3:20]
