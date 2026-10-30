"""Actual sklearn fits, artifact integrity and original local reservation."""
from contextlib import contextmanager
import base64
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import time

import pytest

from gene_annotation_episode.expression_nmf_common import MODE, OPERATION, canonical, default_nmf_parameters, digest, identity
from gene_annotation_episode.expression_nmf_inputs import parse_expression_matrix, prepare_expression_matrix
from gene_annotation_episode.expression_nmf_sheet import load_expression_nmf_artifacts, populate_nmf_sheet
from gene_annotation_episode.expression_nmf_calculations import calculate_nmf_sheet
from gene_annotation_episode.native_expression_nmf_driver import retain_expression_nmf_artifacts, run_expression_nmf
from gene_annotation_episode.native_expression_nmf_contracts import (ARTIFACT_NAMES, POLICY,
    validate_expression_nmf_bindings, validate_expression_nmf_requested_job)
from gene_annotation_episode.native_expression_nmf_local import prepare_local_expression_nmf, local_expression_nmf_plan
from gene_annotation_episode.native_expression_nmf_observations import expression_nmf_observed_files, read_expression_nmf_output
from gene_annotation_episode.native_expression_nmf_tool_info import expression_nmf_tool_contracts
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode import native_lifecycle

RAW = b'gene,A,B,B\ng,1,2,0\ng,0,1,3\ng3,1,3,3\n'


@pytest.fixture(scope='module')
def packet():
    return Path(os.environ['NMF484_ATTEMPT'])


@pytest.fixture(scope='module')
def helpers(packet):
    path = packet / 'source_snapshot/verification/tool_graders_expression_nmf_native_grader_2026-10-27_484/fixture_helpers.py'
    spec = importlib.util.spec_from_file_location('nmf484_helpers', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def software(packet, helpers):
    binding = helpers.prepared_software(packet)
    (packet / 'native-software.json').write_bytes(canonical(binding) + b'\n')
    return binding


def loaded_sheet(output, raw=RAW):
    bundle = load_expression_nmf_artifacts(output / ARTIFACT_NAMES['manifest'], expected_input_identity=identity(raw))
    return bundle, populate_nmf_sheet(**{k: bundle[k] for k in ('input_data', 'prepared_data', 'native_result')})


@pytest.mark.parametrize('normalization', ['none', 'column_sum_1000'])
def test_actual_complete_sklearn_fit_retained(packet, normalization):
    output = packet / ('native-' + normalization)
    manifest = retain_expression_nmf_artifacts(RAW, delimiter=',', metadata={'units': 'counts'},
        parameters=default_nmf_parameters(rank=2, normalization=normalization), output_directory=output)
    bundle, sheet = loaded_sheet(output)
    assert not bundle['failures']
    assert sheet['calculation_eligible'], sheet['failures']
    assert sheet['native_diagnostics']['fit_call_count'] == 1
    assert sheet['source']['versions']['scikit-learn'] == '1.7.2'
    c = calculate_nmf_sheet(sheet)
    assert abs(c['native_minus_calculated_frobenius']) < 1e-10
    assert c['sse'] < 1e-3
    assert (output / 'original-input.bin').read_bytes() == RAW
    assert len(sheet['W']) == 3 and len(sheet['H']) == 2 and len(sheet['H'][0]) == 3
    (output / 'sheet-example.json').write_bytes(canonical(sheet) + b'\n')
    (output / 'calculations-example.json').write_bytes(canonical(c) + b'\n')


def test_actual_native_nonconvergence_is_warning_with_full_factors(packet):
    output = packet / 'native-nonconvergence'
    retain_expression_nmf_artifacts(RAW, delimiter=',', metadata=None,
        parameters=default_nmf_parameters(rank=2, normalization='none', max_iter=1, tol=1e-12), output_directory=output)
    bundle, sheet = loaded_sheet(output)
    assert sheet['outcome'] == 'qualified'
    assert sheet['native_diagnostics']['n_iter_'] == 1
    assert sheet['native_diagnostics']['convergence_warning'] is True
    assert sheet['warnings'][0]['category'] == 'sklearn.exceptions.ConvergenceWarning'
    assert sheet['calculation_eligible']


@pytest.mark.parametrize('normalization', ['none', 'column_sum_1000'])
def test_negative_raw_values_preserved_and_rejected_before_fit(tmp_path, monkeypatch, normalization):
    from sklearn.decomposition import NMF
    def forbidden(*args, **kwargs):
        raise AssertionError('negative values must not be fitted')
    monkeypatch.setattr(NMF, 'fit_transform', forbidden)
    raw = b'gene,s\ng,-2\nh,-3\n'
    output = tmp_path / 'negative'
    retain_expression_nmf_artifacts(raw, delimiter=',', metadata=None,
        parameters=default_nmf_parameters(rank=1, normalization=normalization), output_directory=output)
    bundle, sheet = loaded_sheet(output, raw)
    assert sheet['raw_matrix'] == [[-2], [-3]]
    if normalization == 'column_sum_1000':
        assert sheet['fit_matrix'] == [[400], [600]]
    assert sheet['outcome'] == 'rejected_input'
    assert sheet['native_diagnostics']['fit_call_count'] == 0
    assert sheet['W'] is sheet['H'] is None
    assert not (output / 'factors.json').exists()


def test_actual_all_zero_and_rank_above_min_shape():
    for raw, rank in ((b'gene,s\ng,0\nh,0\n', 1), (b'gene,s\ng,1\nh,2\n', 5)):
        inp = parse_expression_matrix(raw, delimiter=',')
        prepared = prepare_expression_matrix(inp, normalization='none')
        result = run_expression_nmf(prepared, parameters=default_nmf_parameters(rank=rank, normalization='none'))
        assert result['outcome'] in ('complete', 'qualified')
        assert len(result['H']) == rank
        sheet = populate_nmf_sheet(input_data=inp, prepared_data=prepared, native_result=result)
        assert sheet['calculation_eligible']
        if rank == 1:
            assert calculate_nmf_sheet(sheet)['sse'] == 0


@pytest.mark.parametrize('damage', ['missing', 'malformed', 'byte_identity', 'axis_swap', 'partial_H', 'shape', 'original_identity'])
def test_partial_or_malformed_artifacts_keep_valid_inputs_and_diagnostics(tmp_path, packet, damage):
    import shutil
    source = packet / 'native-none'
    target = tmp_path / damage
    shutil.copytree(source, target)
    factor = target / 'factors.json'
    manifest_path = target / 'fit-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if damage == 'missing':
        factor.unlink()
    elif damage == 'malformed':
        factor.write_text('{')
    elif damage == 'byte_identity':
        factor.write_bytes(factor.read_bytes() + b' ')
    elif damage == 'original_identity':
        (target / 'original-input.bin').write_bytes(b'wrong')
    else:
        factors = json.loads(factor.read_text())
        if damage == 'axis_swap':
            factors['axes']['samples'].reverse()
        elif damage == 'partial_H':
            factors.pop('H')
        else:
            factors['W'][0].pop()
        factor.write_bytes(canonical(factors))
        declaration = next(r for r in manifest['files'] if r['role'] == 'factors')
        declaration.update(identity(factor.read_bytes()))
        manifest_path.write_bytes(canonical(manifest))
    bundle, sheet = loaded_sheet(target)
    assert sheet['raw_matrix'] == [[1, 2, 0], [0, 1, 3], [1, 3, 3]]
    assert sheet['native_diagnostics']['n_iter_'] is not None
    assert not sheet['calculation_eligible']
    assert calculate_nmf_sheet(sheet)['sse'] is None
    if damage == 'partial_H':
        assert sheet['W'] is not None and sheet['H'] is None


def test_wrong_expected_input_identity_explicit_failure(packet):
    bundle = load_expression_nmf_artifacts(packet / 'native-none/fit-manifest.json',
        expected_input_identity={'sha256': '0'*64, 'size_bytes': len(RAW)})
    assert bundle['failures']


@pytest.mark.parametrize('bad_result', [None, [], 3, 'invalid'])
def test_malformed_manifest_keeps_independent_original_input(tmp_path, packet, bad_result):
    import shutil
    target = tmp_path / 'malformed-manifest'
    shutil.copytree(packet / 'native-none', target)
    path = target / 'fit-manifest.json'
    manifest = json.loads(path.read_text())
    manifest['result'] = bad_result
    path.write_bytes(canonical(manifest))
    bundle, sheet = loaded_sheet(target)
    assert bundle['manifest'] is None
    assert sheet['raw_matrix'] == [[1, 2, 0], [0, 1, 3], [1, 3, 3]]
    assert sheet['W'] is None and sheet['H'] is None
    assert not sheet['calculation_eligible']


def test_original_bytes_are_retained_before_parser_failure(tmp_path, monkeypatch):
    from gene_annotation_episode import native_expression_nmf_driver as driver
    def failure(*args, **kwargs):
        raise MemoryError('selected_fixture_parse_failure')
    monkeypatch.setattr(driver, 'parse_expression_matrix', failure)
    with pytest.raises(MemoryError):
        retain_expression_nmf_artifacts(RAW, delimiter=',', metadata=None,
            parameters=default_nmf_parameters(rank=2, normalization='none'), output_directory=tmp_path / 'retained')
    assert (tmp_path / 'retained/original-input.bin').read_bytes() == RAW
    assert not (tmp_path / 'retained/factors.json').exists()


def test_native_fit_exception_has_no_synthetic_factors(monkeypatch):
    from sklearn.decomposition import NMF
    calls = []
    def failure(*args, **kwargs):
        calls.append(1)
        raise ArithmeticError('selected_fixture_fit_failure')
    monkeypatch.setattr(NMF, 'fit_transform', failure)
    inp = parse_expression_matrix(RAW, delimiter=',')
    prepared = prepare_expression_matrix(inp, normalization='none')
    result = run_expression_nmf(prepared, parameters=default_nmf_parameters(rank=2, normalization='none'))
    assert result['outcome'] == 'failed' and result['W'] is None and result['H'] is None
    assert len(calls) == result['diagnostics']['fit_call_count'] == 1


def test_multiple_explicit_software_bindings_are_not_infrastructure_selected(software):
    binding = {'operation': OPERATION, 'mode': MODE, 'software': software}
    second = deepcopy(binding)
    second['software']['distributions'][0]['version'] += '.distinct'
    assert len(validate_expression_nmf_bindings([binding, second])) == 2
    with pytest.raises(ValueError, match='duplicate_nmf_binding'):
        validate_expression_nmf_bindings([binding, binding])
    info = expression_nmf_tool_contracts([binding, second], resource_kind='local', resource_id='local')[0]
    assert len(info['input_schema']['properties']['native_expression_nmf']['properties']['software']['enum']) == 2


class SelectedState:
    """Narrow durable pending-intent fixture; full Workflow is owned by root."""
    run_id, episode_id = 'nmf484-native-run', 'local-child'
    def __init__(self, assignment, operation):
        self.assignment = assignment
        self.pending = {'operation_key': operation, 'tool_name': 'practical.job.start', 'run_id': self.run_id,
            'episode_id': self.episode_id, 'assignment_sha256': digest(assignment)}
    @contextmanager
    def _locked(self):
        yield
    def _load(self):
        return None, None, None, None, self.pending


def test_actual_selected_local_driver_original_handle_and_replay(packet, helpers, software):
    workspace = packet / 'selected-workspace'
    workspace.mkdir()
    input_path = packet / 'selected-input.csv'
    input_path.write_bytes(RAW)
    request = helpers.selected_request(software, input_path)
    validate_expression_nmf_requested_job(request)
    assignment = {'resource_kind': 'local', 'resource_id': 'local', 'workspace': str(workspace),
        'requested_job': request, 'constraints': {}}
    operation = 'selected-start'
    state = SelectedState(assignment, operation)
    root = workspace / '.episode-operations' / digest({'run': state.run_id, 'episode': state.episode_id}) / digest(operation)
    handle = prepare_local_expression_nmf(state, operation, root=root, policy=LocalJobPolicy(**POLICY))
    original = handle.read()
    assert original['stage'] == 'prepared'
    assert prepare_local_expression_nmf(state, operation, root=root, policy=LocalJobPolicy(**POLICY)).read() == original
    plan = local_expression_nmf_plan(assignment, str(handle.path))
    (packet / 'selected-native-plan.json').write_bytes(canonical(plan) + b'\n')
    native_lifecycle.resume_start(handle)
    # This waits only for the explicitly selected original physical handle;
    # no replacement fit/submission is made if it remains live.
    while not native_lifecycle.status(handle)['terminal']:
        time.sleep(0.05)
    result = native_lifecycle.collect(handle)
    (packet / 'selected-native-outcome.json').write_bytes(canonical({'returncode': result.returncode,
        'metadata': result.metadata, 'handle': str(handle.path)}) + b'\n')
    assert result.returncode == 0, result.stderr_path.read_text()
    output = Path(plan['attempt_directory']) / 'native-output'
    bundle, sheet = loaded_sheet(output)
    assert sheet['calculation_eligible'] and sheet['native_diagnostics']['fit_call_count'] == 1
    observed, logs, available = expression_nmf_observed_files(plan, native_lifecycle.status(handle),
        log_window_bytes=512, log_roles=('stdout', 'stderr'))
    assert available and len({row['role'] for row in observed}) == len(observed)
    assert any('nmf_fit_finished' in base64.b64decode(row['bytes_base64']).decode() for row in logs if row['role'] == 'stdout')
    read = read_expression_nmf_output(plan, path=str(root / 'stdout.log'), offset=0, limit=80)
    assert read['returned_bytes'] <= 80 and 'W' not in read
    with pytest.raises(ValueError, match='nmf_original_output_path_required'):
        read_expression_nmf_output(plan, path=str(input_path), offset=0, limit=80)
    assert local_expression_nmf_plan(assignment, str(handle.path)) == plan
    assert handle.read()['unit'] == original['unit']
    state.pending = None
    with pytest.raises(ValueError, match='nmf_selected_pending_start_required'):
        prepare_local_expression_nmf(state, operation, root=root, policy=LocalJobPolicy(**POLICY))
