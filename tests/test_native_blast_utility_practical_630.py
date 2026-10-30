"""Controlled practical/progress binding checks; no BLAST executable is run.

Real reservation, producer custody, receipt and endpoint code consumes explicit
fixture bytes. Native dispatch/status and the selected subprocess are fixtures.
These checks do not establish scientific measurements or live-resource coverage.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode import native_blast_utility_driver as driver
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_progress import ExecutionProgressProvider, ExecutionTargetReader
from gene_annotation_episode.native_blast_utility_contracts import (
    LEGACY_MODES, requested_job_from_native_blast_utility)
from gene_annotation_episode.native_blast_utility_local import local_blast_utility_plan
from gene_annotation_episode.numerical import NumericBand, YieldParameters
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import (
    ASSIGNMENT_SCHEMA, assess_validations, canonical, digest, validate_assignment, validate_outcome)
from gene_annotation_episode.practical_execution_state import PracticalState
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.practical_yield import PracticalYieldEstimator
from gene_annotation_episode.progress_records import validate_resource_observation
from gene_annotation_episode.state import Store

from test_native_blast_utility_producer_628 import POLICY, controlled_native, job_fixture
from test_practical_yield import completion_context


def environment(tmp_path, monkeypatch, *, mode='create_sequence_database', endpoint='completed_job_outputs'):
    job = job_fixture(tmp_path, mode)
    request = requested_job_from_native_blast_utility(job)
    run, episode, resource = 'run-630', 'episode-630', 'local-630'
    key = f'{run}:{episode}:0'
    root = tmp_path / '.episode-operations' / digest({'run': run, 'episode': episode}) / digest(key)
    attempt = root / 'blast-utility-attempt'
    predicate = ({'kind': 'requested_job_handoff'} if endpoint == 'usable_handoff' else
        {'kind': 'requested_job_outputs', 'output_paths': [str(attempt / 'bundle.json')]})
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'selected-utility',
        'resource_kind': 'local', 'resource_id': resource, 'workspace': str(tmp_path),
        'endpoint': endpoint, 'requested_job': request,
        'progress_requirements': [{'key': 'requested', 'credit': 3.0, 'predicate': predicate}],
        'completion_keys': ['requested'], 'initial_context': {'revision': 0, 'cwd': str(tmp_path), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}
    configuration = {'kind': 'local', 'workspace': str(tmp_path), 'policy': deepcopy(POLICY),
        'native_blast_utility': [{'program': job['operation']['program'], 'mode': mode,
            'software': job['software'], 'molecules': ['dna']}]}
    operations = LocalPracticalOperations(configuration)
    state = PracticalState(tmp_path / 'practical', run, episode, assignment,
        initial_outcome=operations.initial_outcome(assignment))
    e = SimpleNamespace(assignment=assignment, configuration=configuration, operations=operations,
        state=state, root=root, attempt=attempt, key=key, starts=[], views={}, run=run,
        episode=episode, resource=resource, tmp_path=tmp_path)

    def start(handle):
        e.starts.append(str(handle.path))
        body = handle.read()
        body['stage'] = 'released'
        handle.path.write_text(json.dumps(body))
        e.views[str(handle.path)] = {'state': 'running', 'terminal': False,
            'metadata': {**body['metadata'], 'native_returncode': None}}

    monkeypatch.setattr(native, 'start_prepared', start)
    monkeypatch.setattr(native, 'resume_start', lambda *a, **k: pytest.fail('unexpected resubmission'))
    monkeypatch.setattr(native, 'status', lambda handle: deepcopy(e.views[str(handle.path)]))

    def act(index, tool='practical.job.start', arguments=None):
        arguments = {} if arguments is None else arguments
        selected_key = f'{run}:{episode}:{index}'
        intent = state.begin(selected_key, tool, arguments)
        if intent['state'] == 'completed':
            return intent['receipt']
        outcome, after = operations._execute(state, tool, arguments, selected_key)
        return state.finish(selected_key, outcome, assess_validations(assignment, outcome,
            state.context() if after is None else after, tool_name=tool), context_after=after)

    def seal(*, returncode=0, family=None):
        handle = native.NativeJobHandle(root / 'native.json')
        plan = local_blast_utility_plan(assignment, str(handle.path))
        calls = controlled_native(monkeypatch, returncode=returncode, family=family)
        bundle = driver.run_native_blast_utility(plan)
        e.views[str(handle.path)] = {'state': 'returned', 'terminal': True,
            'metadata': {**handle.read()['metadata'], 'native_returncode': 0 if not bundle['failures'] else 1,
                'duration_measure': 'service_wall_seconds', 'elapsed_seconds': 2.5}}
        assert len(calls) == 1
        return plan, bundle

    e.act, e.seal = act, seal
    return e


@pytest.mark.parametrize('mode', [mode for _, mode in LEGACY_MODES])
def test_all_five_modes_reach_original_receipt_and_terminal_proof(tmp_path, monkeypatch, mode):
    e = environment(tmp_path, monkeypatch, mode=mode)
    Draft202012Validator(ASSIGNMENT_SCHEMA).validate(e.assignment)
    assert validate_assignment(e.assignment) == e.assignment
    started = e.act(0)
    assert e.state.completion_proof() is None
    assert started['outcome']['native_outcome']['native_blast_utility_plan']['policy'] == POLICY
    plan, bundle = e.seal()
    closed = e.act(1, 'practical.job.collect')
    detail = closed['outcome']['native_outcome']
    assert detail['native_blast_utility_validation'] == {
        'version': 'native_blast_utility_validation_v1', 'bundle': bundle,
        'bundle_sha256': digest(bundle), 'files_validated': True, 'failure_code': None}
    assert detail['native_blast_utility_plan'] == plan
    assert detail['attempt_operation_key'] == e.key
    assert detail['attempt_id'] == digest(e.key)
    assert len(e.starts) == 1
    assert closed['validations'][0]['satisfied'] is True
    proof = e.state.completion_proof()
    assert e.state.verify_completion(proof)
    assert e.state.credit_view()['credit'] == 3.0
    context = completion_context(run_id=e.run, episode_id=e.episode, unit_index=1, action_index=1)
    context['practical_completion'].update(proof)
    estimate = PracticalYieldEstimator(e.state.verify_completion)((0.0, 3.0), YieldParameters(), (None, context))
    assert estimate.expected_next_gain == NumericBand.exact(0)
    assert estimate.turns == 2
    monkeypatch.setattr(native, 'status', lambda *a: pytest.fail('receipt replay polled native work'))
    assert e.act(1, 'practical.job.collect') == closed
    assert e.state.receipts() == [started, closed]


@pytest.mark.parametrize('change', [
    lambda c: c['native_blast_utility'].clear(),
    lambda c: c['native_blast_utility'][0]['software'].update(sha256='a' * 64),
    lambda c: c['native_blast_utility'][0].update(program='blastdbcmd', mode='info'),
    lambda c: c['native_blast_utility'][0].update(molecules=['protein']),
    lambda c: c['policy'].update(memory_bytes=POLICY['memory_bytes'] - 1),
    lambda c: c['policy'].update(memory_bytes=POLICY['memory_bytes'] + 1),
    lambda c: c['policy'].update(scratch_bytes=POLICY['scratch_bytes'] + 1),
    lambda c: c['policy'].update(wall_seconds=10),
    lambda c: c.update(workspace='/outside-selected-workspace'),
])
def test_bound_selection_and_allocation_cannot_be_substituted(tmp_path, monkeypatch, change):
    e = environment(tmp_path, monkeypatch)
    changed = deepcopy(e.configuration)
    change(changed)
    with pytest.raises(ValueError):
        LocalPracticalOperations(changed).validate_assignment(e.assignment)
    assert e.starts == [] and e.state.receipts() == []


@pytest.mark.parametrize('change', [
    lambda a: a.pop('resource_id'),
    lambda a: a.update(resource_kind='hpc'),
    lambda a: a['requested_job']['argv'].append('-unselected'),
])
def test_assignment_rejects_missing_identity_wrong_resource_or_command(tmp_path, monkeypatch, change):
    e = environment(tmp_path, monkeypatch)
    changed = deepcopy(e.assignment)
    change(changed)
    with pytest.raises(ValueError):
        validate_assignment(changed)


def test_failed_partial_build_retains_outputs_without_success_or_prefix_file(tmp_path, monkeypatch):
    e = environment(tmp_path, monkeypatch)
    e.act(0)
    plan, bundle = e.seal(returncode=7, family={'nin': b'partial fixture index'})
    receipt = e.act(1, 'practical.job.collect')
    assert receipt['outcome']['facts']['requested_job']['status'] == 'failed'
    assert receipt['outcome']['native_outcome']['native_blast_utility_validation']['bundle']['returncode'] == 7
    assert not receipt['validations'][0]['satisfied']
    assert e.state.completion_proof() is None and e.state.credit_view()['credit'] == 0
    observed = e.operations.observe_execution(e.assignment, str(e.root / 'native.json'),
        run_id=e.run, origin_episode_id=e.episode, resource_id=e.resource,
        requested_job_sha256=digest(e.assignment['requested_job']),
        attempt_id=digest(e.key), original_operation_key=e.key)
    validate_resource_observation(observed)
    assert observed['state'] == 'failed' and observed['result_available']
    assert any(row['role'] == 'database_file:db/tiny.nin' and row['available'] for row in observed['outputs'])
    assert 'database_family' not in {row['role'] for row in observed['outputs']}
    assert str(e.attempt / 'db/tiny') not in receipt['outcome']['facts']['requested_job']['output_paths']
    assert {row['role'] for row in observed['logs']} == {'stdout', 'stderr'}
    assert bundle['output_completeness_basis'] == 'captured_bytes'
    assert next(row for row in bundle['artifacts'] if row['role'] == 'database_file')['completeness'] == 'complete'
    assert len(e.starts) == 1


@pytest.mark.parametrize('damage', ['missing', 'changed', 'extra_member', 'bundle_missing', 'bundle_changed'])
def test_missing_or_changed_originals_never_complete_endpoint(tmp_path, monkeypatch, damage):
    e = environment(tmp_path, monkeypatch)
    e.act(0)
    e.seal()
    if damage == 'missing':
        (e.attempt / 'db/tiny.nsq').unlink()
    elif damage == 'changed':
        (e.attempt / 'db/tiny.nsq').write_bytes(b'changed after sealing')
    elif damage == 'extra_member':
        (e.attempt / 'db/tiny.unrecorded').write_bytes(b'unrecorded')
    elif damage == 'bundle_missing':
        (e.attempt / 'bundle.json').unlink()
    else:
        (e.attempt / 'bundle.json').write_bytes(b'not the original bundle')
    receipt = e.act(1, 'practical.job.collect')
    # Preserve the real native exit; missing custody is separate evidence.
    assert receipt['outcome']['facts']['requested_job']['status'] == 'completed'
    detail = receipt['outcome']['native_outcome']
    assert detail['metadata']['native_returncode'] == 0
    assert detail['native_blast_utility_validation']['failure_code'] is not None
    assert not receipt['validations'][0]['satisfied']
    assert e.state.completion_proof() is None
    if damage in {'missing', 'changed', 'extra_member'}:
        value = e.operations.read_output(e.assignment, str(e.root / 'native.json'),
            path=str(e.attempt / 'logs/native.stdout'), offset=0, limit=64)
        assert value['text_utf8'] == 'controlled utility fixture\n'
    if damage == 'changed':
        with pytest.raises(ValueError, match='output_identity_conflict'):
            e.operations.read_output(e.assignment, str(e.root / 'native.json'),
                path=str(e.attempt / 'db/tiny.nsq'), offset=0, limit=64)


def test_unrelated_existing_file_and_database_prefix_cannot_satisfy_outputs(tmp_path, monkeypatch):
    e = environment(tmp_path, monkeypatch)
    e.act(0)
    e.seal()
    outcome, _ = e.operations._execute(e.state, 'practical.job.collect', {}, 'read')
    for path in (e.tmp_path / 'unrelated', e.attempt / 'db/tiny'):
        path.write_bytes(b'not a produced artifact')
        assignment, supplied = deepcopy(e.assignment), deepcopy(outcome)
        assignment['progress_requirements'][0]['predicate']['output_paths'] = [str(path)]
        supplied['facts']['requested_job']['output_paths'].append(str(path))
        supplied['facts']['paths'].append({'path': str(path), 'exists': True, 'object_type': 'file', 'sha256': None})
        assert not assess_validations(assignment, supplied, e.state.context(),
            tool_name='practical.job.collect')[0]['satisfied']
        with pytest.raises(ValueError, match='original_output_path_required'):
            e.operations.read_output(e.assignment, str(e.root / 'native.json'), path=str(path), offset=0, limit=64)


@pytest.mark.parametrize('state_name,returncode,terminal', [
    ('running', None, False), ('execution_unknown', None, False), ('returned', None, True)])
def test_uncertain_or_active_attempt_cannot_be_retried(tmp_path, monkeypatch, state_name, returncode, terminal):
    e = environment(tmp_path, monkeypatch)
    e.act(0)
    view = e.views[str(e.root / 'native.json')]
    view.update(state=state_name, terminal=terminal)
    view['metadata']['native_returncode'] = returncode
    receipt = e.act(1, arguments={'retry_failed_execution_id': str(e.root / 'native.json')})
    assert receipt['outcome']['native_outcome']['failure']['code'] == 'practical_retry_requires_original_failed_execution'
    assert len(e.starts) == 1
    assert not (e.root.parent / digest(f'{e.run}:{e.episode}:1')).exists()


def test_confirmed_failed_selected_retry_gets_new_identity_and_preserves_receipt(tmp_path, monkeypatch):
    e = environment(tmp_path, monkeypatch)
    e.act(0)
    e.seal(returncode=7)
    failed = e.act(1, 'practical.job.collect')
    retry = e.act(2, arguments={'retry_failed_execution_id': str(e.root / 'native.json')})
    assert len(e.starts) == 2
    assert retry['outcome']['facts']['requested_job']['execution_id'] != str(e.root / 'native.json')
    assert retry['outcome']['native_outcome']['attempt_operation_key'] == f'{e.run}:{e.episode}:2'
    assert e.state.receipts()[1] == failed
    assert e.act(2, arguments={'retry_failed_execution_id': str(e.root / 'native.json')}) == retry
    assert len(e.starts) == 2


def test_missing_original_handle_is_uncertain_and_never_replaced(tmp_path, monkeypatch):
    e = environment(tmp_path, monkeypatch)
    e.state.begin(e.key, 'practical.job.start', {})
    e.operations._execute(e.state, 'practical.job.start', {}, e.key)
    (e.root / 'native.json').unlink()
    with pytest.raises(ValueError, match='missing_reservation_execution_uncertain'):
        e.operations._execute(e.state, 'practical.job.start', {}, e.key)
    assert len(e.starts) == 1 and e.state.receipts() == []


def test_running_handoff_keeps_existing_endpoint_semantics(tmp_path, monkeypatch):
    e = environment(tmp_path, monkeypatch, endpoint='usable_handoff')
    receipt = e.act(0)
    assert receipt['outcome']['facts']['requested_job']['status'] == 'running'
    assert e.state.verify_completion(e.state.completion_proof())
    assert e.state.credit_view()['credit'] == 3.0


def publish(store, e, receipt, *, scope, assignment=None, episode=None):
    assignment = e.assignment if assignment is None else assignment
    episode = e.episode if episode is None else episode
    context = BindingContext(e.run, episode, 'launch_local',
        (('annotation', 'root'), ('launch_local', episode)), scope, assignment,
        {'message': {'scope': scope, 'episode_assignment': assignment}})
    journal = Journal(store, e.run)
    index = int(receipt['operation_key'].rsplit(':', 1)[1])
    with store.transaction():
        journal.save('runtime_episodes', {'episode_id': episode, 'path': canonical(plain(context.path)),
            'request': canonical(plain(context.request)), 'initial_credit': 0, 'state': 'running'})
        journal.save('runtime_actions', {'episode_id': episode, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': receipt['tool_name'], 'arguments': receipt['arguments']}),
            'result': None, 'credit': None})
    reference = PracticalReceiptInformation(store, e.run).publish(context, receipt)
    return reference


def test_original_receipt_observer_ancestry_progress_replay_and_closed_history(tmp_path, monkeypatch):
    e = environment(tmp_path, monkeypatch)
    started = e.act(0)
    plan, _ = e.seal()
    completed = e.act(1, 'practical.job.collect')
    original = deepcopy(e.state.receipts())
    with Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
        scope = store.validate_scope()
        first = publish(store, e, started, scope=scope)
        closed = publish(store, e, completed, scope=scope)
        observer = PracticalState(tmp_path / 'observer', e.run, 'observer-630', e.assignment)
        key = f'{e.run}:observer-630:0'
        observer.begin(key, 'practical.job.collect', {'receipt_ref': closed})
        outcome, _ = e.operations._execute(e.state, 'practical.job.collect', {}, key)
        observed = observer.finish(key, outcome, assess_validations(e.assignment, outcome,
            observer.context(), tool_name='practical.job.collect'))
        observed_ref = publish(store, e, observed, scope=scope, episode='observer-630')
        progress = ExecutionProgressProvider(store, run_id=e.run, directory=tmp_path / 'progress',
            resources={e.resource: e.configuration}, api_execution=None, log_window_bytes=9,
            log_roles=('stdout', 'stderr'))
        target = progress.targets.read_target(observed_ref, scope)
        assert target['origin_episode_id'] == e.episode
        assert target['execution_id'] == plan['identity']['execution_id']
        assert progress.targets._native_identity(target) == {
            'run_id': e.run, 'origin_episode_id': e.episode, 'attempt_id': digest(e.key),
            'original_operation_key': e.key, 'resource_id': e.resource,
            'requested_job_sha256': digest(e.assignment['requested_job'])}
        descriptor = progress.targets.describe_target(first, scope)
        assert descriptor['output_format'] == 'native_blast_utility_bundle_v1'
        assert descriptor['extractors'][1]['implementation'] == (
            'gene_annotation_episode.native_blast_utility_results.NativeBLASTUtilityResults.execute')
        snapshot = progress.observe(observed_ref, ['execution_status', 'measurements', 'log_windows', 'result_available'],
            scope, operation_key='observer-progress:0')
        assert snapshot['execution_status']['native']['state'] == 'completed'
        assert snapshot['measurements'][0]['value'] == 2.5
        assert len(snapshot['log_windows']) == 2
        monkeypatch.setattr(native, 'status', lambda *a: pytest.fail('original observation replay polled'))
        (e.attempt / 'bundle.json').unlink()
        assert progress.observe(observed_ref, ['execution_status', 'measurements', 'log_windows', 'result_available'],
            scope, operation_key='observer-progress:0') == snapshot
        assert progress.targets.read_target(observed_ref, scope) == target
        assert e.state.receipts() == original
        alien = ExecutionTargetReader(store, run_id='other-run', directory=tmp_path / 'alien',
            resources={e.resource: e.configuration}, api_execution=None)
        with pytest.raises(ContractError):
            alien.read_target(first, scope)


@pytest.mark.parametrize('change', [
    lambda r: r['outcome']['native_outcome'].update(attempt_id='a' * 64),
    lambda r: r['outcome']['native_outcome'].update(attempt_operation_key='other'),
    lambda r: r['outcome']['native_outcome']['native_blast_utility_plan']['identity'].update(run_id='other'),
    lambda r: r['outcome']['native_outcome']['native_blast_utility_plan']['identity'].update(episode_id='other'),
    lambda r: r['outcome']['native_outcome']['native_blast_utility_plan']['identity'].update(resource_id='other'),
    lambda r: r['outcome']['native_outcome']['metadata']['policy'].update(memory_bytes=1),
    lambda r: r['arguments'].update(receipt_ref='unavailable-original'),
])
def test_forged_or_cross_episode_original_identity_is_rejected(tmp_path, monkeypatch, change):
    e = environment(tmp_path, monkeypatch)
    receipt = e.act(0)
    changed = deepcopy(receipt)
    change(changed)
    with Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
        scope = store.validate_scope()
        reader = ExecutionTargetReader(store, run_id=e.run, directory=tmp_path / 'progress',
            resources={e.resource: e.configuration}, api_execution=None)
        with pytest.raises(ValueError):
            reference = publish(store, e, changed, scope=scope)
            reader.read_target(reference, scope)


def test_saved_validation_digest_cannot_be_changed_or_self_declared(tmp_path, monkeypatch):
    e = environment(tmp_path, monkeypatch)
    e.act(0)
    e.seal()
    receipt = e.act(1, 'practical.job.collect')
    outcome = deepcopy(receipt['outcome'])
    outcome['native_outcome']['native_blast_utility_validation']['bundle_sha256'] = 'a' * 64
    with pytest.raises(ValueError, match='validation_invalid'):
        validate_outcome(outcome)
