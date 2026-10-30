"""Shared dispatch/observation wiring; synthetic files, not live overlap results."""
import base64
from copy import deepcopy
import json
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_progress import describe_execution_target
from gene_annotation_episode.native_genomic_overlap_contracts import validate_genomic_overlap_run_plan
from gene_annotation_episode.native_genomic_overlap_contracts import validate_genomic_overlap_independent_pair_manifest
from gene_annotation_episode.native_genomic_overlap_observations import (
    genomic_overlap_observed_files, read_genomic_overlap_output,
)
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import (
    REQUESTED_JOB_SCHEMA, validate_assignment, validate_outcome,
)
from gene_annotation_episode.progress_records import validate_resource_observation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_genomic_overlap_operands import f, problem_template


@pytest.fixture
def selected(tmp_path):
    original = json.loads((Path(__file__).resolve().parents[1] /
        'verification/tool_graders_genomic_overlap_native_contract_2026-10-27_425/WORKED_EXAMPLE.json').read_text())
    assignment, plan = deepcopy(original['assignment']), deepcopy(original['plan'])
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    assignment['workspace'] = assignment['initial_context']['cwd'] = str(workspace)
    owner = plan['identity']
    root = workspace / '.episode-operations' / digest({'run': owner['run_id'], 'episode': owner['episode_id']}) / digest(owner['operation_key'])
    root.mkdir(parents=True)
    owner['execution_id'] = str(root / 'native.json')
    owner['assignment_sha256'] = digest(assignment)
    plan['attempt_directory'] = str(root / 'genomic-overlap-attempt')
    plan = validate_genomic_overlap_run_plan(plan)
    assignment = validate_assignment(assignment)
    configuration = {'kind': 'local', 'workspace': str(workspace), 'policy': plan['policy'],
                     'native_genomic_overlap': [original['binding']]}
    return SimpleNamespace(plan=plan, assignment=assignment, root=root,
        operations=LocalPracticalOperations(configuration))


def output_path(selected, role, comparison=None):
    specs = selected.plan['requested_job']['native_genomic_overlap']['outputs']
    spec = next(row for row in specs if row['role'] == role and
                (comparison is None or row['comparison_key'] == comparison))
    path = Path(selected.plan['attempt_directory']) / spec['relative_path']
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def test_shared_request_and_explicit_local_binding(selected):
    Draft202012Validator(REQUESTED_JOB_SCHEMA).validate(selected.assignment['requested_job'])
    selected.operations.validate_assignment(selected.assignment)
    wrong = deepcopy(selected.assignment)
    wrong['constraints']['allocation']['memory_bytes'] -= 1
    with pytest.raises(ValueError, match='allocation_constraint_mismatch'):
        selected.operations.validate_assignment(wrong)
    wrong = deepcopy(selected.assignment)
    wrong['resource_kind'] = 'hpc'
    with pytest.raises(ValueError, match='local_resource_required'):
        validate_assignment(wrong)
    description = describe_execution_target({'resource_kind': 'local', 'assignment': selected.assignment})
    assert description == {'resource_kind': 'local', 'service_or_program': 'bedtools_intersect_all_pairs',
        'operation': 'analyze_genomic_region_overlap', 'mode': 'unstranded_outer_span',
        'output_format': 'genomic_overlap_native_batch_v1'}


def test_empty_pair_file_available_without_final_batch(selected):
    output = output_path(selected, 'overlap_stdout', 'comparison_0')
    output.write_bytes(b'')
    rows, logs, available = genomic_overlap_observed_files(selected.plan, {'terminal': False},
        log_window_bytes=8192, log_roles=())
    row = next(row for row in rows if row['role'] == 'requested_output:' + str(output))
    assert row == {'role': 'requested_output:' + str(output), 'available': True,
                   'bytes': 0, 'writer_closed': False}
    assert available and logs == []
    assert not output_path(selected, 'batch_manifest').exists()
    output.unlink()
    rows, _, available = genomic_overlap_observed_files(selected.plan, {'terminal': True},
        log_window_bytes=8192, log_roles=())
    row = next(row for row in rows if row['role'] == 'requested_output:' + str(output))
    assert not available and row['bytes'] is None and not row['writer_closed']


def test_failed_driver_logs_use_original_lifecycle_paths(selected):
    error_path = selected.root / 'stderr.log'
    error_path.write_bytes(b'interpreter unavailable\n')
    outputs, logs, available = genomic_overlap_observed_files(selected.plan, {'terminal': True},
        log_window_bytes=12, log_roles=('stderr',))
    assert not available
    assert logs == [{'role': 'stderr', 'path': str(error_path), 'offset': 12,
        'observed_size': 24, 'bytes_base64': base64.b64encode(b'unavailable\n').decode()}]
    assert next(row for row in outputs if row['role'] == 'stderr')['writer_closed']
    assert read_genomic_overlap_output(selected.plan, path=str(error_path), offset=0, limit=11)['text_utf8'] == 'interpreter'


def test_selected_file_window_and_path_exclusion(selected):
    output = output_path(selected, 'overlap_stdout', 'comparison_0')
    output.write_bytes(b'abcdefgh')
    result = read_genomic_overlap_output(selected.plan, path=str(output), offset=2, limit=3)
    assert result == {'path': str(output), 'offset': 2, 'returned_bytes': 3, 'size_bytes': 8,
                      'bytes_base64': 'Y2Rl', 'text_utf8': 'cde'}
    assert read_genomic_overlap_output(selected.plan, path=str(output), offset=20, limit=3)['returned_bytes'] == 0
    foreign = selected.root / 'not-selected.txt'
    foreign.write_text('foreign')
    with pytest.raises(ValueError, match='original_output_path_required'):
        read_genomic_overlap_output(selected.plan, path=str(foreign), offset=0, limit=3)
    output.unlink()
    output.symlink_to(foreign)
    with pytest.raises(ValueError, match='capture_file_unavailable'):
        read_genomic_overlap_output(selected.plan, path=str(output), offset=0, limit=3)


@pytest.mark.parametrize('offset,limit', [(True, 1), (-1, 1), (0, True), (0, 0), (0, 1048577)])
def test_bounded_output_window_required(selected, offset, limit):
    with pytest.raises(ValueError, match='bounded_native_output_window_required'):
        read_genomic_overlap_output(selected.plan, path=str(output_path(selected, 'stdout')), offset=offset, limit=limit)


def test_shared_observation_calls_status_once_and_preserves_failed_partial_output(selected, monkeypatch):
    output_path(selected, 'pair_manifest', 'comparison_0').write_bytes(b'{}')
    calls = []
    def authenticate(assignment, execution_id, **identity):
        assert assignment == selected.assignment and execution_id == selected.plan['identity']['execution_id']
        calls.append(('authenticate', identity))
        return selected.plan
    monkeypatch.setattr(selected.operations, '_genomic_overlap_plan', authenticate)
    view = {'terminal': True, 'state': 'returned', 'metadata': {'native_returncode': 1,
            'elapsed_seconds': 2.5, 'duration_measure': 'systemd_service_wall_seconds'}}
    def status(handle):
        calls.append(('status', str(handle.path)))
        return deepcopy(view)
    monkeypatch.setattr('gene_annotation_episode.practical_execution_operations.native.status', status)
    owner = selected.plan['identity']
    result = selected.operations.observe_execution(selected.assignment, owner['execution_id'],
        run_id=owner['run_id'], origin_episode_id=owner['episode_id'],
        original_operation_key=owner['operation_key'], attempt_id=owner['attempt_id'])
    validate_resource_observation(result)
    assert [row[0] for row in calls] == ['authenticate', 'status']
    assert result['state'] == 'failed' and result['result_available']
    assert result['measurements'] == [{'measure': 'systemd_service_wall_seconds', 'seconds': 2.5}]


def test_selected_start_dispatches_overlap_reservation_and_records_original_identity(selected, monkeypatch):
    owner = selected.plan['identity']
    state = SimpleNamespace(assignment=selected.assignment, run_id=owner['run_id'],
        episode_id=owner['episode_id'], context=lambda: deepcopy(selected.assignment['initial_context']))
    def absent(state):
        raise ValueError('requested_job_not_started')
    monkeypatch.setattr(selected.operations, '_job_handle', absent)
    captured = []
    def handle(state, key, command, **options):
        captured.append((key, command, options))
        return SimpleNamespace(path=Path(owner['execution_id']))
    monkeypatch.setattr(selected.operations, '_handle', handle)
    monkeypatch.setattr(selected.operations, '_genomic_overlap_plan', lambda *a, **kw: selected.plan)
    monkeypatch.setattr('gene_annotation_episode.practical_execution_operations.native.status',
        lambda handle: {'terminal': False, 'state': 'running', 'metadata': {}})
    outcome, changed = selected.operations._execute(state, 'practical.job.start', {}, owner['operation_key'])
    validate_outcome(outcome)
    assert changed is None and len(captured) == 1
    assert captured[0][2]['native_genomic_overlap'] is True
    assert outcome['native_outcome']['attempt_id'] == owner['attempt_id']
    assert outcome['native_outcome']['attempt_operation_key'] == owner['operation_key']
    assert outcome['facts']['requested_job']['status'] == 'running'


def _family(store, directory, resources):
    return ExecutionEpisodes(None, store=store, directory=directory, run_id='overlap-registration',
        resources=resources, initial_information={}, tool_registry=ToolRegistry(store),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=['stdout', 'stderr'])


def _resource(selected):
    job = selected.assignment['requested_job']['native_genomic_overlap']
    return {'kind': 'local', 'workspace': selected.assignment['workspace'],
        'policy': deepcopy(selected.plan['policy']), 'native_genomic_overlap': [{
            'operation': job['request']['operation'], 'mode': job['request']['mode'],
            'software': deepcopy(job['software'])}]}


def test_bound_overlap_is_a_launch_contract_and_reopens_without_native_work(selected, tmp_path, monkeypatch):
    resource_id = selected.assignment['resource_id']
    resources = {resource_id: _resource(selected)}
    def deny(*args, **kwargs):
        raise AssertionError('resource registration must not execute or observe native work')
    monkeypatch.setattr('gene_annotation_episode.practical_execution_operations.native.status', deny)
    monkeypatch.setattr('gene_annotation_episode.practical_execution_operations.native.start_prepared', deny)
    with Store(tmp_path / 'store') as store:
        family = _family(store, tmp_path / 'run', resources)
        launch = {'version': 'execution_launch_assignment_v1', 'requests': {
            resource_id: deepcopy(selected.assignment)}, 'immutable_input_versions': [], 'constraints': {}}
        assert Draft202012Validator(family.assignment_schema('launch')).is_valid(launch)
        assert Draft202012Validator(family.assignment_schema('launch_local')).is_valid(selected.assignment)
        assert family._validate_request(selected.assignment) == selected.assignment
        row, = [row for row in family.resource_tool_contracts() if row['name'] == 'analyze_genomic_region_overlap']
        assert row['description'] and row['instructions'] and row['resources'] == 'local'
        assert row['invocation_route'] == {'kind': 'commission', 'routes': [{
            'entry_role': 'launch', 'resource_id': resource_id, 'resource_role': 'launch_local'}]}
        assert 'analyze_genomic_region_overlap' not in ToolRegistry(store).catalog()
        restored = ExecutionEpisodes(None, store=store, directory=tmp_path / 'restored',
            run_id='overlap-registration', tool_registry=ToolRegistry(store), **family.as_record()['configuration'])
        assert restored.as_record() == family.as_record()
        assert restored.resource_tool_contracts() == family.resource_tool_contracts()
        wrong = deepcopy(selected.assignment)
        wrong['requested_job']['native_genomic_overlap']['software']['bedtools_sha256'] = '0' * 64
        assert not Draft202012Validator(family.assignment_schema('launch_local')).is_valid(wrong)
        with pytest.raises(ValueError, match='native_genomic_overlap_operation_mode_software_not_bound'):
            family._validate_request(wrong)


@pytest.mark.parametrize('empty', [False, True])
def test_unbound_overlap_does_not_appear_as_available(selected, tmp_path, empty):
    configuration = _resource(selected)
    if empty:
        configuration['native_genomic_overlap'] = []
    else:
        del configuration['native_genomic_overlap']
    with Store(tmp_path / 'store') as store:
        family = _family(store, tmp_path / 'run', {selected.assignment['resource_id']: configuration})
        assert not any(row['name'] == 'analyze_genomic_region_overlap' for row in family.resource_tool_contracts())
        assert not Draft202012Validator(family.assignment_schema('launch_local')).is_valid(selected.assignment)


@pytest.mark.parametrize('kind', ['api', 'pbs_ssh'])
def test_overlap_binding_cannot_claim_an_unimplemented_resource(selected, tmp_path, kind):
    configuration = {**_resource(selected), 'kind': kind}
    with Store(tmp_path / 'store') as store:
        with pytest.raises(ValueError, match='native_genomic_overlap_resource_execution_binding_unfinished'):
            _family(store, tmp_path / 'run', {selected.assignment['resource_id']: configuration})


def test_independent_seal_retains_original_facts_without_set_observations(monkeypatch):
    fixtures = import_module('verification.tool_graders_genomic_overlap_execution_contracts_2026-10-27_426.fixtures')
    def denied(*args, **kwargs):
        raise AssertionError('independent seal must not invent batch set observations')
    monkeypatch.setattr('gene_annotation_episode.native_genomic_overlap_contracts._set_outputs', denied)
    for case in (None, 'empty', 'invalid'):
        plan, batch = fixtures.fixture() if case is None else fixtures.c_case(case)
        for pair in batch['pairs']:
            original = deepcopy(pair['manifest'])
            result = validate_genomic_overlap_independent_pair_manifest(original,
                plan=plan, comparison=pair['comparison'])
            assert result == original and result is not original


@pytest.mark.parametrize('mutate', [
    lambda m: m['identity'].update(operation_key='another-action'),
    lambda m: m['input_fingerprints'][0].update(sha256='0' * 64),
    lambda m: m.update(writer_closed=False),
    lambda m: m['software'].update(observed_version='another-version'),
    lambda m: m['realized_argv'].extend(['-f', '0.5']),
    lambda m: m['files'][0].update(role='canonical_b'),
    lambda m: m['files'][2]['declaration'].update(relative_path='elsewhere.tsv'),
    lambda m: m.update(returncode=1),
    lambda m: m.update(finished_at='2000-01-01T00:00:00+00:00'),
])
def test_independent_seal_rejects_foreign_or_contradictory_original_facts(mutate):
    fixtures = import_module('verification.tool_graders_genomic_overlap_execution_contracts_2026-10-27_426.fixtures')
    plan, batch = fixtures.fixture()
    pair = batch['pairs'][0]
    mutate(pair['manifest'])
    with pytest.raises(ValueError):
        validate_genomic_overlap_independent_pair_manifest(pair['manifest'], plan=plan, comparison=pair['comparison'])


def test_received_overlap_inputs_cross_actual_launch_and_resource_commission_hooks(f, tmp_path, monkeypatch):
    from test_genomic_overlap_operands import assignment, context, refs, set_spec
    requested = assignment(f.store, f.specs)['requested_job']
    workspace = tmp_path / 'work'
    workspace.mkdir()
    policy = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}
    selected = {'version': 'practical_assignment_v1', 'assignment_id': 'selected-overlap',
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': requested,
        'progress_requirements': [{'key': 'handoff', 'credit': 3, 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': policy}}
    resource = {'kind': 'local', 'workspace': str(workspace), 'policy': policy, 'native_genomic_overlap': [{
        'operation': 'analyze_genomic_region_overlap', 'mode': 'unstranded_outer_span',
        'software': requested['native_genomic_overlap']['software']}]}
    family = ExecutionEpisodes(None, store=f.store, directory=tmp_path / 'run', run_id=f.run_id,
        resources={'here': resource}, initial_information={}, tool_registry=ToolRegistry(f.store),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=['stdout', 'stderr'])
    def denied(*args, **kwargs):
        raise AssertionError('commission validation and initialization must not start a job')
    monkeypatch.setattr('gene_annotation_episode.practical_execution_operations.native.prepare_job', denied)
    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'here': selected},
        'immutable_input_versions': [], 'constraints': {}}
    prepared = family.prepare_assignment(f.root, 'launch', launch, f.scope, 'commission-launch')
    launch_context = context(f, parent=f.root, role='launch', label='child_0', assigned=prepared)
    family.initialize(launch_context)
    assert family.initial_references(launch_context) == refs(f.specs)
    local = family.prepare_assignment(launch_context, 'launch_local', selected, f.scope, 'commission-local')
    local_context = context(f, parent=launch_context, role='launch_local', label='child_0', assigned=local)
    family.initialize(local_context)
    assert family.initial_references(local_context) == refs(f.specs)
    assert plain(local_context.assignment)['requested_job'] == requested
    assert not list(workspace.rglob('native.json'))
    # A valid Store source that this parent has never received cannot enter a
    # new launch merely because it has a file, metadata and matching byte pins.
    unreceived = set_spec(f.store, 'B', b'chr2\t2\t4\n')
    changed = deepcopy(launch)
    changed['requests']['here']['requested_job'] = assignment(f.store, [f.specs[0], unreceived])['requested_job']
    with pytest.raises(ValueError, match='genomic_overlap_input_not_received'):
        family.prepare_assignment(f.root, 'launch', changed, f.scope, 'unreceived-input')
