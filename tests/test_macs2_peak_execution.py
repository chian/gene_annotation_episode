"""Single-call MACS2 controls; engineered controls never claim native science."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from macs2_peak_fixtures import (
    CHROMOSOME, GENOME_SIZE, READ_LENGTH, TAG_COUNT,
    engineered_bed6, file_identity, engineered_reference,
)
from gene_annotation_episode import native_macs2_peak_execution as native
from gene_annotation_episode import macs2_peak_request_binding as compact
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.flux_balance_request_binding import resource_assignment_schema as fba_assignment_schema
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_atac_differential_contracts import canonical, digest, _dependency_roots
from gene_annotation_episode.atac_differential_inputs import (
    parse_macs2_peaks_xls, parse_macs2_narrowpeak, parse_macs2_summits_bed,
)
from gene_annotation_episode.macs2_peak_components import build_macs2_peak_components
from gene_annotation_episode.macs2_peak_result_contracts import project_macs2_peak_values
from gene_annotation_episode import macs2_peak_result_worker as result_worker
from gene_annotation_episode.practical_execution_state import PracticalState
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.local_file_capture_results import (
    MACS2_SELECTOR_VERSION, resolve_macs2_peak_file_selector,
)
from gene_annotation_episode.runtime import Workflow
from test_native_atac_differential_contracts import fake_software as atac_control_software


def fake_software():
    """Deliberately fake engineering pins, never a native runtime witness."""
    value = atac_control_software()
    value['driver_runtime']['implementation_files'].append(
        dict(module=native.DRIVER_MODULE, sha256=digest(native.DRIVER_MODULE)))
    return value


def job_fixture(directory, *, software=None):
    directory.mkdir(parents=True, exist_ok=True)
    inputs, bindings, samples = [], [], []
    reference = engineered_reference()
    for role, raw in zip(('treatment', 'control'), engineered_bed6(), strict=True):
        path = directory / (role + '.bed')
        path.write_bytes(raw)
        file = file_identity(raw)
        inputs.append(dict(input_key=role, role=role, sample_id=role,
            reference_id=reference['reference_id'], file=file))
        bindings.append(dict(input_key=role, file=file, path=str(path)))
        samples.append(dict(sample_id=role, input_artifact_refs=[file['artifact_ref']],
            reference_id=reference['reference_id'], biospecimen_id=None,
            replicate_id=None, origin='synthetic_engineering_fixture'))
    request = dict(version='macs2_peak_request_v1', operation=native.OPERATION, mode=native.MODE,
        run_key='single-callpeak', condition_id='chipseq', reference=reference,
        samples=samples, inputs=inputs,
        callpeak=dict(genome_size_argument=str(GENOME_SIZE), qvalue_cutoff=0.05),
        output_prefix='chipseq_native')
    return dict(request=request, software=fake_software() if software is None else software,
        input_bindings=bindings)


def requested(job, directory):
    driver = job['software']['driver_runtime']
    environment = dict(PYTHONPATH=os.pathsep.join([driver['module_root'], *_dependency_roots(driver)]),
        PYTHONHOME=sys.base_prefix, PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1',
        PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
        TMP=str(directory / 'tmp'), TEMP=str(directory / 'tmp'), TMPDIR=str(directory / 'tmp'),
        XDG_CACHE_HOME=str(directory / 'cache'), PIP_CACHE_DIR=str(directory / 'cache/pip'))
    return native.requested_job_from_macs2_peak(job, environment=environment)


def plan_fixture(directory, *, job=None):
    job = job_fixture(directory) if job is None else job
    selected = requested(job, directory)
    operation, run, episode = 'selected-start', 'engineered-control', 'local-child'
    root = directory / '.episode-operations' / digest(dict(run=run, episode=episode)) / digest(operation)
    return native.validate_macs2_peak_run_plan(dict(version='macs2_peak_run_plan_v1',
        identity=dict(run_id=run, episode_id=episode, resource_id='local',
            execution_id=str(root / 'native.json'), attempt_id=digest(operation),
            operation_key=operation, requested_job_sha256=digest(selected),
            assignment_sha256=digest('engineered-control-not-episode-authority')),
        requested_job=selected, attempt_directory=str(root / native.ATTEMPT_DIRECTORY_NAME),
        policy=native.POLICY, outputs=native.macs2_peak_output_files(job['request'])))


def output_path(plan, key):
    return Path(plan['attempt_directory']) / next(row['relative_path'] for row in plan['outputs'] if row['file_key'] == key)


def practical_assignment(directory, job):
    return dict(version='practical_assignment_v1', assignment_id='engineered-macs2-assignment',
        resource_kind='local', resource_id='local', workspace=str(directory), endpoint='usable_handoff',
        requested_job=requested(job, directory), progress_requirements=[dict(key='handoff', credit=1,
            predicate=dict(kind='requested_job_handoff'))], completion_keys=['handoff'],
        initial_context=dict(revision=0, cwd=str(directory), environment={}),
        inventory_snapshot={}, constraints=deepcopy(native.POLICY))


def compact_selection(job, *, ordinal=0):
    request = deepcopy(job['request'])
    for row in request['inputs']:
        row['file'] = {key: row['file'][key] for key in ('artifact_ref', 'format')}
    return dict(version=compact.ASSIGNMENT_VERSION, resource_id='local', resource_kind='local',
        binding_ordinal_0based=ordinal, endpoint='usable_handoff', request=request,
        progress_requirements=[dict(key='handoff', credit=1, predicate=dict(kind='requested_job_handoff'))],
        completion_keys=['handoff'], constraints=dict(allocation=deepcopy(native.POLICY)))


def mocked_command(monkeypatch, *, returncode=0, omit=None):
    """One engineered subprocess response; no numerical or native validation."""
    calls = []
    monkeypatch.setattr(native, 'verify_software', lambda software: None)
    def run(argv, *, stdout, stderr, **kwargs):
        calls.append(dict(argv=list(argv), cwd=str(kwargs['cwd']), environment=deepcopy(kwargs['env'])))
        assert argv.count('callpeak') == 1 and '-c' in argv
        destination = Path(argv[argv.index('--outdir') + 1])
        prefix = argv[argv.index('-n') + 1]
        xls = (
            '# engineered native-command control, not scientific output\n'
            '# This file is generated by MACS version 2.2.9.1\n# format = AUTO\n'
            f"# ChIP-seq file = {[argv[argv.index('-t') + 1]]!r}\n"
            f"# control file = {[argv[argv.index('-c') + 1]]!r}\n"
            '# Paired-End mode is off\n# Broad region calling is off\n# d = 199\n'
            'chr\tstart\tend\tlength\tabs_summit\tpileup\t-log10(pvalue)\tfold_enrichment\t-log10(qvalue)\tname\n'
            'chrSynthetic\t2\t3\t2\t3\t1\t1\t1\t1\tengineered_peak\n'
        ).encode()
        for role, suffix, raw in (
            ('peaks_xls', '_peaks.xls', xls),
            ('narrowpeak', '_peaks.narrowPeak', b'chrSynthetic\t1\t3\tengineered_peak\t0\t.\t1\t1\t1\t1\n'),
            ('summits', '_summits.bed', b'chrSynthetic\t2\t3\tengineered_peak\t1\n'),
            ('model', '_model.r', b'# engineered model-file control; no model fit occurred\n'),
        ):
            if role != omit:
                (destination / (prefix + suffix)).write_bytes(raw)
        stdout.write(b'engineered subprocess control; no native scientific execution\n')
        stderr.write(b'engineered retained diagnostic prefix\n')
        return SimpleNamespace(returncode=returncode)
    monkeypatch.setattr(native.subprocess, 'run', run)
    return calls


@pytest.mark.parametrize('role,size,digest', [
    ('treatment', 483110, '9b81702cbe2873927fc520c7bfc86f0fe8e9d38c0c76cbd6805f2fa5f6c8cc41'),
    ('control', 471088, '0bf4200e249d0bef8fda64cb2484b67669d159238cd704632cbcfeeba31ea12a'),
])
def test_engineered_input_is_exact_bounded_bed6_with_distinct_native_cut_pairs(role, size, digest):
    supplied = dict(zip(('treatment', 'control'), engineered_bed6(), strict=True))
    raw = supplied[role]
    assert len(raw) == size < 1024 * 1024
    assert hashlib.sha256(raw).hexdigest() == digest
    assert file_identity(raw) == dict(artifact_ref='artifact_' + digest,
        sha256=digest, size_bytes=size, format='bed6')
    records = [line.decode('ascii').split('\t') for line in raw.splitlines()]
    assert len(records) == TAG_COUNT
    assert all(len(row) == 6 and row[0] == CHROMOSOME and row[4] == '0' for row in records)
    assert all(0 <= int(row[1]) < int(row[2]) <= GENOME_SIZE
        and int(row[2]) - int(row[1]) == READ_LENGTH and row[5] in ('+', '-') for row in records)
    assert len({(int(row[1]) if row[5] == '+' else int(row[2]), row[5]) for row in records}) == TAG_COUNT
    assert sum(row[5] == '+' for row in records) == sum(row[5] == '-' for row in records) == TAG_COUNT // 2


def test_engineered_treatment_has_explicit_islands_and_matched_control_remains_separate():
    treatment, control = engineered_bed6()
    treatment_rows = [line.decode('ascii').split('\t') for line in treatment.splitlines()]
    control_rows = [line.decode('ascii').split('\t') for line in control.splitlines()]
    assert treatment != control
    for island in range(1201):
        selected = treatment_rows[10 * island:10 * (island + 1)]
        center = 5000 + 10000 * island
        assert {int(row[1]) for row in selected if row[5] == '+'} == {center - 100 + j for j in range(5)}
        assert {int(row[2]) for row in selected if row[5] == '-'} == {center + 100 + j for j in range(5)}
    assert [int(row[1]) if row[5] == '+' else int(row[2]) for row in control_rows] == [
        500 + 1000 * ordinal for ordinal in range(TAG_COUNT)]


def test_exact_one_command_keeps_native_auto_and_model_defaults(tmp_path):
    plan = plan_fixture(tmp_path)
    argv = native.macs2_peak_command_argv(plan)
    runtime = plan['requested_job']['native_macs2_peak']['software']['macs2_runtime']
    assert argv[:4] == [runtime['python_executable'], '-B', '-S', runtime['macs2_script']]
    assert argv[4] == 'callpeak' and argv.count('-t') == argv.count('-c') == 1
    assert argv[argv.index('-g') + 1] == str(GENOME_SIZE)
    assert argv[argv.index('-q') + 1] == '0.05'
    assert argv[argv.index('-n') + 1] == 'chipseq_native'
    assert argv[argv.index('-t') + 1] != argv[argv.index('-c') + 1]
    assert all(flag not in argv for flag in ('--nomodel', '--fix-bimodal', '--shift', '--extsize',
        '--keep-dup', '--format', '-f', '--broad', '--SPMR', '--down-sample', 'bdgdiff'))
    assert [row['file_key'] for row in plan['outputs']] == [
        'peaks_xls', 'narrowpeak', 'summits', 'model', 'stdout', 'stderr', 'seal']
    assert output_path(plan, 'model').name == 'chipseq_native_model.r'
    assert next(row for row in plan['outputs'] if row['file_key'] == 'model')['required'] is False
    assert len({row['relative_path'] for row in plan['outputs']}) == 7


@pytest.mark.parametrize('mutation', [
    lambda j: j['request']['callpeak'].update(qvalue_cutoff=True),
    lambda j: j['request']['callpeak'].update(qvalue_cutoff=0),
    lambda j: j['request']['callpeak'].update(qvalue_cutoff=2),
    lambda j: j['request']['callpeak'].update(nomodel=True),
    lambda j: j['request'].update(output_prefix='../escape'),
    lambda j: j['request'].update(output_prefix='--version'),
    lambda j: j['request']['inputs'][1].update(role='treatment'),
    lambda j: j['request']['inputs'][1].update(sample_id='unselected'),
    lambda j: j['request']['inputs'][1].update(reference_id='different-reference'),
    lambda j: j['input_bindings'][1].update(file=j['input_bindings'][0]['file']),
    lambda j: j['software']['macs2_runtime'].update(macs2_version='2.2.9.2'),
])
def test_selected_contract_rejects_inconsistent_or_unselected_operands(tmp_path, mutation):
    job = job_fixture(tmp_path)
    mutation(job)
    with pytest.raises(ValueError):
        native.validate_macs2_peak_native_job(job)


def test_bound_requested_schema_rejects_extra_commands_and_unselected_software(tmp_path):
    job = job_fixture(tmp_path)
    selected = requested(job, tmp_path)
    binding = dict(operation=native.OPERATION, mode=native.MODE, software=job['software'])
    schema = native.macs2_peak_execution_schema('RequestedJob', bindings=[binding])
    assert Draft202012Validator(schema).is_valid(selected)
    changed = deepcopy(selected)
    changed['argv'].append('--unselected-command')
    assert not Draft202012Validator(schema).is_valid(changed)
    with pytest.raises(ValueError):
        native.validate_macs2_peak_requested_job(changed)
    changed = deepcopy(selected)
    changed['native_macs2_peak']['software']['macs2_runtime']['python_sha256'] = 'f' * 64
    assert not Draft202012Validator(schema).is_valid(changed)


def test_engineered_single_command_is_sealed_and_same_plan_never_repeats_it(tmp_path, monkeypatch):
    calls = mocked_command(monkeypatch)
    plan = plan_fixture(tmp_path)
    original = native.run_macs2_peak(plan)
    assert len(calls) == 1
    assert original['outcome'] == 'succeeded' and original['returncode'] == 0
    assert original['argv'] == native.macs2_peak_command_argv(plan)
    assert [row['role'] for row in original['inputs']] == ['treatment', 'control']
    assert len(original['outputs']) == 6
    assert output_path(plan, 'seal').read_bytes() == canonical(original)
    assert native.run_macs2_peak(plan) == original
    assert len(calls) == 1


def test_failed_command_keeps_actual_prefix_and_does_not_retry(tmp_path, monkeypatch):
    calls = mocked_command(monkeypatch, returncode=7, omit='peaks_xls')
    plan = plan_fixture(tmp_path)
    result = native.run_macs2_peak(plan)
    assert len(calls) == 1 and result['outcome'] == 'failed' and result['returncode'] == 7
    assert output_path(plan, 'stderr').read_bytes() == b'engineered retained diagnostic prefix\n'
    assert output_path(plan, 'narrowpeak').exists() and not output_path(plan, 'peaks_xls').exists()
    assert native.run_macs2_peak(plan) == result and len(calls) == 1


@pytest.mark.parametrize('defect', ['missing', 'changed', 'symlink', 'software'])
def test_unavailable_original_operands_never_reach_native_dispatch(tmp_path, monkeypatch, defect):
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch)
    source = Path(plan['requested_job']['native_macs2_peak']['input_bindings'][0]['path'])
    if defect == 'missing':
        source.unlink()
    elif defect == 'changed':
        source.write_bytes(b'changed original treatment')
    elif defect == 'symlink':
        replacement = source.with_name('other.bed')
        source.rename(replacement)
        source.symlink_to(replacement)
    else:
        def denied(_):
            raise ValueError('native_dependency_unavailable')
        monkeypatch.setattr(native, 'verify_software', denied)
    result = native.run_macs2_peak(plan)
    assert result['outcome'] == 'not_run' and calls == []
    assert result['returncode'] is None and result['started_at'] is None
    assert result['failures']


@pytest.mark.parametrize('mutation', [
    lambda s: s['argv'].__setitem__(s['argv'].index('-c') + 1, '/unselected/control'),
    lambda s: s['inputs'][1].update(role='treatment'),
    lambda s: s['inputs'][0]['file'].update(sha256='f' * 64),
    lambda s: s.update(outcome='failed', returncode=0),
    lambda s: s.update(finished_at='2000-01-01T00:00:00+00:00'),
    lambda s: s['environment'].update(PYTHONPATH='/unselected/modules'),
])
def test_original_seal_cannot_relabel_selected_operands_or_outcome(tmp_path, monkeypatch, mutation):
    mocked_command(monkeypatch)
    plan = plan_fixture(tmp_path)
    changed = deepcopy(native.run_macs2_peak(plan))
    mutation(changed)
    with pytest.raises(ValueError):
        native.validate_macs2_peak_seal(changed, plan=plan)


def test_undeclared_paths_are_not_native_output_handles(tmp_path, monkeypatch):
    mocked_command(monkeypatch)
    plan = plan_fixture(tmp_path)
    native.run_macs2_peak(plan)
    with pytest.raises(ValueError):
        native.read_macs2_peak_output(plan,
            path=plan['requested_job']['native_macs2_peak']['input_bindings'][0]['path'], offset=0, limit=32)
    selected = native.read_macs2_peak_output(plan, path=str(output_path(plan, 'stderr')), offset=0, limit=10)
    assert selected['returned_bytes'] == 10


def test_orphaned_started_attempt_never_dispatches_again(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch)
    directory = Path(plan['attempt_directory'])
    directory.mkdir(parents=True)
    native._immutable(directory / native.OWNER_FILENAME, plan)
    with pytest.raises(ValueError, match='unsealed_native_attempt'):
        native.run_macs2_peak(plan)
    assert calls == [] and not output_path(plan, 'seal').exists()


@pytest.mark.parametrize('change', ['changed_bytes', 'missing', 'symlink'])
def test_completed_output_tamper_is_not_resealed_or_reexecuted(tmp_path, monkeypatch, change):
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch)
    seal = native.run_macs2_peak(plan)
    original = output_path(plan, 'seal').read_bytes()
    selected = output_path(plan, 'narrowpeak')
    if change == 'changed_bytes':
        selected.write_bytes(b'changed native output')
    elif change == 'missing':
        selected.unlink()
    else:
        other = selected.with_name('other.narrowPeak')
        selected.rename(other)
        selected.symlink_to(other)
    with pytest.raises((OSError, ValueError)):
        native.run_macs2_peak(plan)
    assert len(calls) == 1
    assert output_path(plan, 'seal').read_bytes() == original == canonical(seal)


@pytest.mark.parametrize('terminal,quiescent,closed', [
    (False, False, False), (True, False, False), (True, True, True),
])
def test_observed_outputs_require_terminal_and_quiescent_for_closed_writers(tmp_path, monkeypatch,
        terminal, quiescent, closed):
    plan = plan_fixture(tmp_path)
    mocked_command(monkeypatch)
    native.run_macs2_peak(plan)
    outputs, logs, available = native.macs2_peak_observed_files(plan,
        dict(terminal=terminal, quiescent=quiescent), log_window_bytes=16, log_roles=('stderr',))
    assert len(outputs) == 7 and available is True
    assert all(row['available'] and row['writer_closed'] is closed for row in outputs)
    assert len(logs) == 1 and logs[0]['role'] == 'stderr'
    assert logs[0]['observed_size'] == len(b'engineered retained diagnostic prefix\n')


def test_missing_optional_model_and_missing_required_output_keep_distinct_native_declarations(tmp_path, monkeypatch):
    optional = plan_fixture(tmp_path / 'optional')
    calls = mocked_command(monkeypatch, omit='model')
    result = native.run_macs2_peak(optional)
    assert result['outcome'] == 'succeeded' and len(calls) == 1
    assert not result['failures']
    model = next(row for row in result['outputs'] if row['specification']['role'] == 'model')
    assert model['declaration']['state'] == 'absent'
    assert model['declaration']['sha256'] is model['declaration']['size_bytes'] is None
    required = plan_fixture(tmp_path / 'required')
    calls = mocked_command(monkeypatch, omit='summits')
    result = native.run_macs2_peak(required)
    assert result['outcome'] == 'succeeded' and len(calls) == 1
    assert any(row['code'] == 'native_output_unavailable' and row['file_key'] == 'summits'
        for row in result['failures'])


def test_callpeak_binding_preserves_original_selected_inputs_and_native_defaults(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    mocked_command(monkeypatch)
    seal = native.run_macs2_peak(plan)
    result = native.macs2_peak_callpeak_binding(plan, seal)
    request = plan['requested_job']['native_macs2_peak']['request']
    assert result['selected_format'] == 'AUTO' and result['paired_end'] is False
    assert result['sample_ids'] == ['treatment'] and result['supplied_control_sample_ids'] == ['control']
    assert result['treatment_input_refs'] == [request['inputs'][0]['file']['artifact_ref']]
    assert result['supplied_control_input_refs'] == [request['inputs'][1]['file']['artifact_ref']]
    assert result['selected_argv'] == seal['argv']
    assert result['selected_parameters']['genome_size_argument'] == str(GENOME_SIZE)
    assert result['selected_parameters']['effective_genome_size_bp'] is None
    assert result['selected_parameters']['nomodel'] is False
    assert result['selected_parameters']['keep_duplicates'] == 1
    assert result['selected_parameters']['shift_bp'] == 0
    assert result['artifact_roles']['signal_track'] is result['artifact_roles']['background_track'] is None
    assert result['producer_ref'] == seal['producer_ref']


def test_prepare_requires_actual_pending_practical_start_and_cached_plan_does_not_reopen_inputs(tmp_path):
    job = job_fixture(tmp_path)
    assignment = practical_assignment(tmp_path, job)
    state = PracticalState(tmp_path / 'state', 'engineered-run', 'local-child', assignment)
    root = tmp_path / '.episode-operations' / digest(dict(run='engineered-run', episode='local-child')) / digest('selected-start')
    policy = LocalJobPolicy(**native.POLICY)
    with pytest.raises(ValueError, match='selected_pending_start_required'):
        native.prepare_local_macs2_peak(state, 'selected-start', root=root, policy=policy)
    state.begin('selected-start', 'practical.job.start', {})
    handle = native.prepare_local_macs2_peak(state, 'selected-start', root=root, policy=policy)
    original = native.read_local_macs2_peak_plan(assignment, str(handle.path))
    before = handle.path.read_bytes()
    for row in job['input_bindings']:
        Path(row['path']).unlink()
    assert native.read_local_macs2_peak_plan(assignment, str(handle.path)) == original
    assert native.prepare_local_macs2_peak(state, 'selected-start', root=root, policy=policy).path == handle.path
    assert handle.path.read_bytes() == before


def test_saved_plan_rebuild_uses_only_original_metadata_without_any_filesystem_consumer(tmp_path, monkeypatch):
    job = job_fixture(tmp_path)
    assignment = practical_assignment(tmp_path, job)
    selected = assignment['requested_job']
    root = tmp_path / '.episode-operations' / digest(dict(run='engineered-run', episode='local-child')) / digest('selected-start')
    identity = dict(run_id='engineered-run', episode_id='local-child', resource_id='local',
        execution_id=str(root / 'native.json'), attempt_id=digest('selected-start'), operation_key='selected-start',
        requested_job_sha256=digest(selected), assignment_sha256=digest(assignment))
    def forbidden(*args, **kwargs):
        raise AssertionError('saved plan reconstruction consulted mutable filesystem metadata or payload')
    monkeypatch.setattr(native, '_directory', forbidden)
    monkeypatch.setattr(native, '_read_control', forbidden)
    monkeypatch.setattr(native, '_regular', forbidden)
    rebuilt = native.macs2_peak_plan(assignment, identity, policy=native.POLICY)
    assert rebuilt['identity'] == identity
    assert rebuilt['requested_job'] == selected
    assert rebuilt['outputs'] == native.macs2_peak_output_files(job['request'])


@pytest.mark.parametrize('defect', [None, 'command', 'environment', 'request_digest', 'duplicate_path', 'policy'])
def test_original_prepared_control_bytes_are_authenticated_without_filesystem_reopening(tmp_path, monkeypatch, defect):
    job = job_fixture(tmp_path)
    assignment = practical_assignment(tmp_path, job)
    state = PracticalState(tmp_path / 'state', 'engineered-run', 'local-child', assignment)
    root = tmp_path / '.episode-operations' / digest(dict(run='engineered-run', episode='local-child')) / digest('selected-start')
    state.begin('selected-start', 'practical.job.start', {})
    handle = native.prepare_local_macs2_peak(state, 'selected-start', root=root, policy=LocalJobPolicy(**native.POLICY))
    plan = native.read_local_macs2_peak_plan(assignment, str(handle.path))
    original = json.loads(handle.path.read_bytes())
    request_raw = Path(original['paths']['request']).read_bytes()
    if defect == 'command':
        original['command'].append('--unselected-command')
    elif defect == 'environment':
        document = json.loads(request_raw)
        document['env']['PYTHONPATH'] = '/unselected-driver'
        request_raw = canonical(document)
        original['request_sha256'] = hashlib.sha256(request_raw).hexdigest()
    elif defect == 'request_digest':
        original['request_sha256'] = 'f' * 64
    elif defect == 'duplicate_path':
        original['paths']['status'] = original['paths']['result']
    elif defect == 'policy':
        original['metadata']['policy']['memory_bytes'] = 1
    def forbidden(*args, **kwargs):
        raise AssertionError('retained original-control verification reopened filesystem metadata or payload')
    monkeypatch.setattr(native, '_directory', forbidden)
    monkeypatch.setattr(native, '_read_control', forbidden)
    monkeypatch.setattr(native, '_regular', forbidden)
    if defect is None:
        assert native.validate_macs2_peak_original_controls(plan, original, request_raw) == plan
        assert native.validate_macs2_peak_original_controls(plan, original, request_raw.decode('utf-8')) == plan
    else:
        with pytest.raises(ValueError):
            native.validate_macs2_peak_original_controls(plan, original, request_raw)


def test_successful_process_with_missing_native_role_keeps_failure_unknown_count_and_other_rows(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    mocked_command(monkeypatch, omit='summits')
    seal = native.run_macs2_peak(plan)
    binding = native.macs2_peak_callpeak_binding(plan, seal)
    reports = {}
    for field, role, parser in (
        ('peaks_xls', 'peaks_xls', parse_macs2_peaks_xls),
        ('narrowpeaks', 'narrowpeak', parse_macs2_narrowpeak),
        ('summits', 'summits', parse_macs2_summits_bed),
    ):
        row = next(row for row in seal['outputs'] if row['specification']['role'] == role)
        spec, declared = row['specification'], row['declaration']
        raw = output_path(plan, role).read_bytes() if declared['state'] == 'present' else None
        descriptor = dict(artifact_ref=binding['artifact_roles'][role], format=spec['format'],
            expected_sha256=declared['sha256'], expected_size_bytes=declared['size_bytes'],
            supplied_extent='complete' if raw is not None else 'unknown',
            producer_run_ref=seal['producer_ref'], producer_outcome=seal['outcome'], writer_closed=True,
            producer_name='MACS2', producer_version='2.2.9.1', producer_source_ref=None,
            origin='synthetic_engineering_fixture')
        reports[field] = [parser(raw, artifact=descriptor, callpeak=binding,
            parse_profile='matched_control_native_model')]
    components = build_macs2_peak_components(reference=plan['requested_job']['native_macs2_peak']['request']['reference'],
        callpeak_bindings=[binding], parse_profile='matched_control_native_model', **reports)
    value = project_macs2_peak_values(components, native_outcome=seal['outcome'],
        row_window=dict(offset=0, limit=6), failures=seal['failures'])
    assert value['native_outcome'] == 'succeeded' and value['status'] == 'partial'
    assert [row['count'] for row in value['native_peak_counts']] == [1, 1, None]
    assert value['peak_window']['total_rows'] is None and value['peak_window']['row_extent'] == 'partial'
    assert [row['representation'] for row in value['peak_window']['rows']] == ['xls', 'narrowpeak']
    assert value['failures'] == seal['failures']
    assert any(row['code'] == 'native_output_unavailable' and row['file_key'] == 'summits'
        for row in value['failures'])


@pytest.mark.parametrize('explicit_qualification', [False, True])
def test_engineered_retained_sha_conflict_excludes_bad_body_and_keeps_valid_siblings(tmp_path, monkeypatch,
        explicit_qualification):
    plan = plan_fixture(tmp_path)
    mocked_command(monkeypatch)
    seal = native.run_macs2_peak(plan)
    roles, bad_path = [], None
    for specification in plan['outputs']:
        role = specification['role']
        raw = output_path(plan, role).read_bytes()
        if role == 'narrowpeak':
            raw = b'conflicting retained bytes must not be consumed as the original native peak\n'
        file = file_identity(raw, specification['format'])
        path = tmp_path / 'retained' / 'artifacts' / file['sha256'][:2] / file['sha256']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        qualification = (dict(code='native_output_identity_conflict')
            if role == 'narrowpeak' and explicit_qualification else None)
        if role == 'narrowpeak':
            bad_path = path
        roles.append(dict(specification=deepcopy(specification),
            source_ref='source_' + digest(dict(engineered_role=role))[:24],
            file=file, path=str(path), availability='retained', qualification=qualification))
    original_regular = result_worker._regular
    def only_valid_siblings(path):
        assert Path(path) != bad_path, 'worker consumed a body conflicting with the sealed original native role'
        return original_regular(path)
    def forbidden(*args, **kwargs):
        raise AssertionError('retained output parsing attempted native execution')
    monkeypatch.setattr(result_worker, '_regular', only_valid_siblings)
    monkeypatch.setattr(native, 'run_macs2_peak', forbidden)
    output = tmp_path / 'parsed'
    output.mkdir()
    result = result_worker.run_macs2_peak_result_job(request=dict(
        version=result_worker.REQUEST_VERSION, mode='parse', row_window=dict(offset=0, limit=6),
        native=dict(plan=plan, seal=seal, roles=roles), saved=None), output_directory=str(output))
    value = result['value']
    assert value['native_outcome'] == 'succeeded' and value['status'] == 'partial'
    assert [row['count'] for row in value['native_peak_counts']] == [1, None, 1]
    assert value['peak_window']['total_rows'] is None
    assert [row['representation'] for row in value['peak_window']['rows']] == ['xls', 'summit']
    assert any(row['code'] == 'artifact_digest_mismatch' and row['stage'] == 'capture'
        and row['file_key'] == 'narrowpeak' for row in value['failures'])
    assert any(row['field'] == 'native_output_identity_conflict' for row in value['issues'])


@pytest.mark.parametrize('ordinal', [0, 1])
def test_public_selection_contains_only_scientific_fields_and_explicit_binding_choice(tmp_path, ordinal):
    job = job_fixture(tmp_path)
    first = dict(operation=native.OPERATION, mode=native.MODE, software=job['software'])
    second = deepcopy(first)
    second['software']['driver_runtime']['module_root'] = '/fixture/second-selected-driver'
    selected = compact_selection(job, ordinal=ordinal)
    assert compact.validate_compact_assignment(selected, 'local', bindings=[first, second]) == selected
    assert all(set(row['file']) == {'artifact_ref', 'format'} for row in selected['request']['inputs'])
    assert 'software' not in selected and 'requested_job' not in selected and 'workspace' not in selected
    assert all(field not in selected['request'] for field in ('software', 'input_bindings', 'environment', 'argv'))
    assert selected['request']['callpeak'] == job['request']['callpeak']
    assert selected['request']['reference'] == job['request']['reference']
    assert selected['binding_ordinal_0based'] == ordinal


@pytest.mark.parametrize('ordinal', [None, True, 0.0, -1, 2, 'missing'])
def test_public_binding_choice_is_required_and_never_guessed(tmp_path, ordinal):
    job = job_fixture(tmp_path)
    selected = compact_selection(job, ordinal=ordinal)
    if ordinal == 'missing':
        selected.pop('binding_ordinal_0based')
    bindings = [dict(operation=native.OPERATION, mode=native.MODE, software=job['software'])]
    with pytest.raises(ValueError, match='macs2_peak_request_invalid_assignment'):
        compact.validate_compact_assignment(selected, 'local', bindings=bindings)


def test_completed_output_selection_uses_only_registered_native_roles(tmp_path):
    selected = compact_selection(job_fixture(tmp_path))
    selected.update(endpoint='completed_job_outputs', progress_requirements=[dict(key='outputs', credit=1,
        predicate=dict(kind='requested_job_outputs', output_roles=['peaks_xls', 'narrowpeak', 'summits', 'seal']))],
        completion_keys=['outputs'])
    assert compact.validate_compact_assignment(selected, 'local') == selected
    selected['progress_requirements'][0]['predicate']['output_roles'].append('fabricated_future_path')
    with pytest.raises(ValueError, match='macs2_peak_request_invalid_assignment'):
        compact.validate_compact_assignment(selected, 'local')


def test_unrelated_resource_construction_never_creates_a_macs2_request_table(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
        factory = ExecutionServiceFactory(dict(local=dict(kind='local', workspace=str(tmp_path / 'workspace'),
            policy=deepcopy(native.POLICY))), {}, 3, 2, 1)
        tools = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
        factory(store, run_id='unrelated', directory=tmp_path / 'run', tool_registry=tools)
        before = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert 'runtime_macs2_peak_request_bindings' not in before
        factory(store, run_id='unrelated', directory=tmp_path / 'run',
            tool_registry=ToolRegistry(store, job_limits=deepcopy(native.POLICY)))
        assert {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")} == before


def test_macs2_output_roles_do_not_expand_the_existing_fba_public_contract():
    predicate = fba_assignment_schema('local')['properties']['progress_requirements']['items']['properties']['predicate']
    assert not Draft202012Validator(predicate).is_valid(dict(kind='requested_job_outputs', output_roles=['peaks_xls']))
    assert not Draft202012Validator(predicate).is_valid(dict(kind='requested_job_outputs', output_roles=['narrowpeak']))


def _public_role_target(directory):
    """Pure engineered target metadata; this fixture grants no Source authority."""
    job = job_fixture(directory)
    assignment = practical_assignment(directory, job)
    original = plan_fixture(directory, job=job)['identity']
    original['assignment_sha256'] = digest(assignment)
    original['requested_job_sha256'] = digest(assignment['requested_job'])
    plan = native.macs2_peak_plan(assignment, original, policy=native.POLICY)
    return dict(handle='source_' + '3' * 64, resource_kind='local', run_id=original['run_id'],
        origin_episode_id=original['episode_id'], resource_id=original['resource_id'],
        execution_id=original['execution_id'], request_sha256=original['requested_job_sha256'],
        assignment=assignment), plan


def test_public_output_roles_resolve_only_explicit_subset_in_selected_order(tmp_path):
    target, plan = _public_role_target(tmp_path)
    selected = dict(version=MACS2_SELECTOR_VERSION, output_roles=['seal', 'peaks_xls'])
    before = canonical((selected, target, plan))
    resolved = resolve_macs2_peak_file_selector(selected, target, plan)
    assert resolved == dict(version='local_file_source_selector_v1', files=[
        dict(path=str(Path(plan['attempt_directory']) / 'macs2-peak-seal.json'), format='macs2_peak_command_seal_v1'),
        dict(path=str(Path(plan['attempt_directory']) / 'native/chipseq_native_peaks.xls'), format='macs2_peaks_xls_narrow')])
    assert canonical((selected, target, plan)) == before


@pytest.mark.parametrize('roles', [[], ['seal', 'seal'], ['arbitrary_output']])
def test_public_output_roles_reject_empty_duplicate_and_unknown_selection(tmp_path, roles):
    target, plan = _public_role_target(tmp_path)
    with pytest.raises(ValueError, match='execution_file_capture_invalid_selector'):
        resolve_macs2_peak_file_selector(dict(version=MACS2_SELECTOR_VERSION, output_roles=roles), target, plan)


@pytest.mark.parametrize('field', ['run_id', 'execution_id', 'request_sha256', 'assignment'])
def test_public_output_roles_require_original_target_plan_association(tmp_path, field):
    target, plan = _public_role_target(tmp_path)
    if field == 'assignment':
        target['assignment']['requested_job']['native_macs2_peak']['request']['callpeak']['qvalue_cutoff'] = 0.04
    else:
        target[field] = {'run_id': 'different-original-run', 'execution_id': '/different/original/native.json',
            'request_sha256': '0' * 64}[field]
    with pytest.raises(ValueError):
        resolve_macs2_peak_file_selector(dict(version=MACS2_SELECTOR_VERSION, output_roles=['seal']), target, plan)


def test_public_output_roles_deny_unreceived_handoff_before_private_target_read(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('unreceived public handoff reached private target, plan, payload or dispatch')
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
        scope = store.validate_scope()
        workspace = tmp_path / 'workspace'
        workspace.mkdir()
        factory = ExecutionServiceFactory(dict(local=dict(kind='local', workspace=str(workspace),
            policy=deepcopy(native.POLICY))), {}, 3, 2, 1)
        tools = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
        application = factory(store, run_id='unreceived-public-output', directory=tmp_path / 'run', tool_registry=tools)
        flow = Workflow(store, tools, SimpleNamespace(complete=forbidden), tmp_path / 'run', 'unreceived-public-output',
            controller_factory=forbidden, project_credit=lambda *_a, **_k: 0, annotation_child_roles=('results',),
            episode_record_receipts=True, initial_known_record_refs=[],
            episode_binding_descriptors=application.episode_binding_descriptors,
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
        flow.build('annotation', 'deny-unreceived-selector', 'Acquire only explicitly received native outputs.', scope)
        row, = store.db.execute('SELECT episode_id FROM runtime_episodes WHERE run_id=?', ('unreceived-public-output',)).fetchall()
        context = EpisodeReturnRecords(store, 'unreceived-public-output', failure_prefix='test_').context(row['episode_id'])
        owner = flow.episode_bindings.for_role('results')
        monkeypatch.setattr(owner.job_progress_provider.targets, 'read_target', forbidden)
        monkeypatch.setattr(owner.job_progress_provider.targets, '_native', forbidden)
        monkeypatch.setattr(store, 'get_artifact', forbidden)
        assignment = dict(version='execution_results_assignment_v1', handoff_ref='source_' + '4' * 64,
            selector=dict(version=MACS2_SELECTOR_VERSION, output_roles=['peaks_xls']))
        with pytest.raises(ValueError, match='execution_file_capture_handoff_not_received'):
            owner.prepare_assignment(context, 'results', assignment, scope,
                f"unreceived-public-output:{context.episode_id}:0")
