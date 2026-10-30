"""Actual selected NMF through the shared local episode and progress reader.

This checks the resource child, original native handoff and closed replay.
Scientific-parent composition and typed numerical returns have separate tests.
"""
import asyncio
import base64
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.expression_nmf_common import MODE, OPERATION, default_nmf_parameters, identity
from gene_annotation_episode.expression_nmf_sheet import load_expression_nmf_artifacts, populate_nmf_sheet
from gene_annotation_episode.expression_nmf_calculations import calculate_nmf_sheet
from gene_annotation_episode.execution_progress import ExecutionTargetReader, describe_execution_target
from gene_annotation_episode.native_expression_nmf_contracts import POLICY, expression_nmf_environment, requested_job_from_expression_nmf
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldParameters
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


RAW = b'gene,A,B,B\ng,1,2,0\ng,0,1,3\ng3,1,3,3\n'


def forbidden(*args, **kwargs):
    raise AssertionError('closed NMF resource replay attempted new work')


class StartOnly:
    calls = 0

    async def complete(self, episode_id, role, instructions, context, schema):
        self.calls += 1
        assert self.calls == 1
        return {'selection': {'kind': 'tool', 'tool': 'practical.job.start', 'arguments': {}}, 'report_update': {}}

    async def release(self, episode_id):
        pass


def assemble(store, directory, assignment, configuration, provider):
    descriptor = PracticalResourceEpisodes(None, directory=directory,
        resources={'local': configuration}).as_record()
    def controller(path, initial):
        return YieldController(str(path), initial, 0, YieldParameters(100, 50))
    workflow = Workflow(store, ToolRegistry(store), provider, directory, 'nmf488-resource',
        controller_factory=controller, project_credit=lambda *_: 0,
        episode_binding_descriptors=[descriptor],
        role_credit_bindings={'launch_local': {'definition': {'version': 'explicit-test-units'},
            'project': lambda *_: 0}}, root_role='launch_local',
        execution_binding={'factory_module': 'fixture', 'factory_name': 'unused',
            'arguments': {}, 'implementation_sha256': 'a'*64, 'settings_sha256': 'b'*64})
    scope = store.validate_scope({'subject_refs': store.problem()['subject_refs']})
    episode = workflow.build('launch_local', 'root', 'Run the supplied expression matrix factorization', scope,
        episode_assignment=assignment)
    return SimpleNamespace(workflow=workflow, episode=episode,
        binding=workflow.specialist(episode.source), context=workflow.binding_context(episode.source))


def run(bound):
    async def selected():
        record = await bound.episode.run_async(bound.workflow.context)
        await bound.episode.build_result(record)
        return record
    return asyncio.run(selected())


def observations(bound):
    return [dict(row) for row in bound.workflow.store.db.execute('SELECT * FROM runtime_observations '
        'WHERE run_id=? ORDER BY episode_id,unit_index', (bound.workflow.run_id,))]


@pytest.fixture(scope='module')
def selected_case(tmp_path_factory):
    root = tmp_path_factory.mktemp('expression-nmf488')
    workspace = root / 'project'
    workspace.mkdir()
    software = json.loads(Path(os.environ['NMF488_SOFTWARE']).read_text())
    store = Store(root / 'state')
    store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
    reference = store.artifact(RAW, 'text/csv')
    input_path = store.path / 'artifacts' / identity(RAW)['sha256'][:2] / identity(RAW)['sha256']
    job = {'version': 'native_expression_nmf_job_v1', 'operation': OPERATION, 'mode': MODE,
        'input': {'path': str(input_path), **identity(RAW), 'artifact_ref': reference,
            'delimiter': ',', 'metadata': {'units': 'counts'}},
        'parameters': default_nmf_parameters(rank=2, normalization='none'),
        'software': software, 'output_prefix': 'native-output'}
    request = requested_job_from_expression_nmf(job,
        environment=expression_nmf_environment(software, attempt_directory=str(workspace / 'selected-context')))
    configuration = {'kind': 'local', 'workspace': str(workspace), 'policy': POLICY,
        'native_expression_nmf': [{'operation': OPERATION, 'mode': MODE, 'software': software}]}
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'nmf488-selected',
        'resource_kind': 'local', 'resource_id': 'local', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': request,
        'progress_requirements': [{'key': 'selected_handoff', 'credit': 7,
            'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['selected_handoff'],
        'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': POLICY}}
    provider = StartOnly()
    bound = assemble(store, root / 'run', assignment, configuration, provider)
    record = run(bound)
    state = bound.binding.state(bound.context)
    receipt, = state.receipts()
    native_id = receipt['outcome']['facts']['requested_job']['execution_id']
    handle = native.NativeJobHandle(Path(native_id))
    result = native.wait_job(handle)
    assert result.returncode == 0, result.stderr_path.read_text()
    case = SimpleNamespace(root=root, store=store, assignment=assignment, configuration=configuration,
        provider=provider, bound=bound, record=record, state=state, receipt=receipt, handle=handle)
    try:
        yield case
    finally:
        store.close()


def test_selected_resource_child_executes_exact_job_and_closes_once(selected_case):
    c = selected_case
    assert c.provider.calls == c.record.units_consumed == len(observations(c.bound)) == 1
    assert c.record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
    assert c.state.credit_view()['credit'] == 7
    operations = LocalPracticalOperations(c.configuration)
    plan = operations._expression_nmf_plan(c.assignment, str(c.handle.path), run_id=c.bound.context.run_id,
        origin_episode_id=c.bound.context.episode_id)
    assert plan['requested_job'] == c.assignment['requested_job'] and plan['policy'] == POLICY
    manifest = Path(plan['attempt_directory']) / 'native-output/fit-manifest.json'
    loaded = load_expression_nmf_artifacts(manifest, expected_input_identity=identity(RAW))
    assert not loaded['failures']
    sheet = populate_nmf_sheet(**{key: loaded[key] for key in ('input_data', 'prepared_data', 'native_result')})
    calculations = calculate_nmf_sheet(sheet)
    assert sheet['native_diagnostics']['fit_call_count'] == 1
    assert calculations['sse'] < 1e-3
    assert abs(calculations['native_minus_calculated_frobenius']) < 1e-10
    assert sheet['raw_matrix'] == [[1, 2, 0], [0, 1, 3], [1, 3, 3]]
    Path(os.environ['NMF488_ATTEMPT']).joinpath('selected-resource-example.json').write_text(json.dumps({
        'operation': OPERATION, 'mode': MODE, 'native_handle': str(c.handle.path),
        'observations': len(observations(c.bound)), 'fit_call_count': sheet['native_diagnostics']['fit_call_count'],
        'sse': calculations['sse'], 'frobenius_residual': calculations['frobenius_residual'],
        'native_reconstruction_error': calculations['native_reconstruction_error']}, indent=2))


def test_handoff_monitoring_and_selected_output_use_original_attempt(selected_case):
    c = selected_case
    before = deepcopy(c.state.receipts()), observations(c.bound)
    reference, = c.bound.binding.facts(c.bound.context, {})['practical_receipt_refs']
    reader = ExecutionTargetReader(c.store, run_id=c.bound.context.run_id, directory=c.root / 'run',
        resources={'local': c.configuration}, api_execution=None)
    target = reader.read_target(reference, c.bound.context.scope)
    assert target['execution_id'] == str(c.handle.path)
    assert describe_execution_target(target)['operation'] == OPERATION
    observed = reader.observe_target(target, operation_key='selected-monitor-observation')
    assert observed['state'] == 'completed' and observed['result_available']
    assert len(observed['outputs']) == len({row['role'] for row in observed['outputs']}) == 7
    assert any(b'nmf_fit_finished' in base64.b64decode(row['bytes_base64']) for row in observed['logs'])
    output = reader.read_file(target, path=str(c.handle.path.parent / 'stdout.log'), offset=0, limit=80)
    assert output['offset'] == 0 and 0 < output['returned_bytes'] <= 80
    with pytest.raises(ValueError, match='original_output_path_required'):
        reader.read_file(target, path=c.assignment['requested_job']['native_expression_nmf']['input']['path'],
            offset=0, limit=80)
    assert (c.state.receipts(), observations(c.bound)) == before


def test_foreign_attempt_and_software_are_rejected(selected_case):
    c = selected_case
    operations = LocalPracticalOperations(c.configuration)
    with pytest.raises(ValueError, match='original_attempt_mismatch'):
        operations.observe_execution(c.assignment, str(c.handle.path), origin_episode_id='foreign')
    changed = deepcopy(c.assignment)
    changed['requested_job']['native_expression_nmf']['software']['python_version'] += '-different'
    with pytest.raises(ValueError, match='not_bound'):
        operations.validate_assignment(changed)
    changed = deepcopy(c.assignment)
    changed['constraints']['allocation']['memory_bytes'] -= 1
    with pytest.raises(ValueError, match='allocation_constraint_mismatch'):
        operations.validate_assignment(changed)


def test_completed_resource_replay_has_no_new_work_or_observations(selected_case, monkeypatch):
    c = selected_case
    before = deepcopy(c.state.receipts()), observations(c.bound)
    monkeypatch.setattr(LocalPracticalOperations, 'execute', forbidden)
    monkeypatch.setattr(LocalPracticalOperations, 'initial_outcome', forbidden)
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr(native, name, forbidden)
    provider = StartOnly()
    monkeypatch.setattr(provider, 'complete', forbidden)
    restored = assemble(c.store, c.root / 'run', c.assignment, c.configuration, provider)
    assert run(restored).as_record() == c.record.as_record()
    assert (restored.binding.state(restored.context).receipts(), observations(restored)) == before
