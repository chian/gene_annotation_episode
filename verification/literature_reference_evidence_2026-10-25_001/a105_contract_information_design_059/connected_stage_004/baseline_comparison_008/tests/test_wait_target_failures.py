"""Invalid wait references repair through ordinary loops, with no fake sample.

All work is isolated and synthetic. Providers are scripted; no model, native
command, private child history or preserved scientific run is used.
"""
import asyncio
from copy import deepcopy
import hashlib
import json

import pytest

from method_loop.durable import (DurableExecutionError, DurableExecutionStore,
    EventTargetError, native_target_handle)
from gene_annotation_episode.literature_experimental_prompt import (
    EXPERIMENTAL_TASK, render_literature_experimental_prompt)
from gene_annotation_episode.literature_reference_parent_prompt import (
    REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt)
from gene_annotation_episode.runtime import Workflow, run_workflow
from gene_annotation_episode.state import Store
from detached_workflow_fixture import (
    ControllerFactory, FixtureTools, ScriptedProvider, make_binding)
from test_durable_episode import commission_spec
from test_native_event_information import Case as NativeCase


PAST = '2026-10-21T12:00:00+00:00'


def condition(*handles, event='state_changed', reconsider_at=PAST):
    return {'version': 'event_condition_v1', 'events': [
        {'handle': handle, 'event': event, 'after_cursor': 0} for handle in handles],
        'reconsider_at': reconsider_at}


def wait(selected):
    return {'selection': {'kind': 'wait', 'condition': selected}, 'report_update': {}}


def rows(store, table):
    return [dict(row) for row in store.db.execute('SELECT * FROM ' + table + ' ORDER BY rowid')]


def zero_credit(store, scope):
    return 0.0


def configured(tmp_path):
    store = Store(tmp_path / 'state')
    subject, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    tools = FixtureTools(store)
    return store, tools, subject


def run(store, tools, provider, directory, controllers, **kwargs):
    return asyncio.run(run_workflow(store, tools, provider=provider, run_dir=directory,
        controller_factory=controllers, project_credit=zero_credit, **kwargs))


def assert_empty_accounting(store, controllers):
    assert rows(store, 'runtime_observations') == []
    assert rows(store, 'runtime_completion_slots') == []
    assert all(c.deltas == [] for c in controllers.controllers)
    assert store.count('observation') == 0


@pytest.mark.parametrize('placement', ['alone', 'before-valid', 'after-valid'])
def test_backend_unknown_identity_is_pure_specific_and_never_falls_back_to_timer(tmp_path, monkeypatch, placement):
    backend = DurableExecutionStore(tmp_path / 'executions')
    spec = commission_spec(tmp_path)
    backend.commission(spec)
    bad = 'source_synthetic_non_execution_record'
    handles = [bad] if placement == 'alone' else (
        [bad, spec['handle']] if placement == 'before-valid' else [spec['handle'], bad])
    selected = condition(*handles)
    monkeypatch.setattr(backend, 'status', lambda *a: pytest.fail('validation polled status'))
    assert backend.validate_event_targets(condition(spec['handle'])) == condition(spec['handle'])
    with backend._connect() as db:
        before = [tuple(row) for row in db.execute('SELECT * FROM events')]
    with pytest.raises(EventTargetError) as error:
        backend.validate_event_targets(selected)
    assert error.value.code == 'unknown_wait_target'
    assert error.value.affected_refs == (bad,)
    with pytest.raises(EventTargetError):
        asyncio.run(backend.wait_events(selected))
    with backend._connect() as db:
        assert [tuple(row) for row in db.execute('SELECT * FROM events')] == before
    assert backend.load_commission(spec['handle']) == spec


@pytest.mark.parametrize('kind', ['source', 'unknown', 'native-unbound'])
@pytest.mark.parametrize('detached', [False, True], ids=['ordinary', 'durable'])
def test_rejected_new_selection_supplies_precise_feedback_then_episode_chooses_repair(tmp_path, kind, detached):
    store, tools, subject = configured(tmp_path)
    controllers = ControllerFactory(1)
    try:
        if kind == 'source':
            bad = tools.execute('fixture.publish', {'label': 'parent_one'},
                scope={'subject_refs': [subject]}, operation_key='fixture-source')['record_refs'][0]
        elif kind == 'unknown':
            bad = 'unknown_execution_target_fixture'
        else:
            bad = 'native_event_target_' + 'a' * 24
        selected = condition(bad)

        def repair(context):
            expected = 'wait_target_unavailable' if kind == 'native-unbound' else 'unknown_wait_target'
            assert context['feedback']['category'] == 'wait_target'
            assert context['feedback']['status'] == 'invalid'
            assert context['feedback']['code'] == expected
            assert context['feedback']['affected_refs'] == [bad]
            assert_empty_accounting(store, controllers)
            assert rows(store, 'episode_waits') == rows(store, 'runtime_actions') == []
            # This choice belongs to the fixture episode after receiving failure.
            return wait(condition())

        provider = ScriptedProvider([wait(selected), repair])
        directory = tmp_path / 'run'
        options = ({'execution_binding': make_binding(tmp_path / 'state', directory),
            'episode_binding_descriptors': []} if detached else {})
        summary = run(store, tools, provider, directory, controllers, **options)
        assert summary['completed_actions'] == 1
        assert len(provider.contexts) == 2
        assert len(rows(store, 'runtime_observations')) == 1
        assert len(rows(store, 'episode_waits')) == 1
        assert json.loads(rows(store, 'episode_waits')[0]['request'])['condition'] == condition()
        assert controllers.controllers[0].deltas == [0.0]
    finally:
        store.close()


def test_native_visibility_rules_keep_existing_meaning_and_precise_references(tmp_path):
    case = NativeCase(tmp_path)
    try:
        target = case.register()
        selected = condition(target['handle'], reconsider_at=None)
        assert case.reader.validate_wait(case.launch, selected) == selected
        with pytest.raises(EventTargetError, match='native_event_information_target_not_visible') as error:
            case.reader.validate_wait(case.root, selected)
        assert error.value.code == 'wait_target_not_visible'
        assert error.value.affected_refs == (target['handle'],)
        for event in ('returned', 'progress_committed'):
            with pytest.raises(EventTargetError, match='native_event_information_unsupported_event') as error:
                case.reader.validate_wait(case.launch, condition(target['handle'], event=event))
            assert error.value.code == 'unsupported_wait_event'
            assert error.value.affected_refs == (target['handle'],)
        # A target received from another owner remains legitimate, unchanged.
        case.attempt(case.root, [case.source(target, 4)])
        assert case.reader.validate_wait(case.root, selected) == selected
    finally:
        case.store.close()


def test_bound_native_rejection_returns_to_episode_without_completing_failed_wait(tmp_path, monkeypatch):
    from test_native_event_runtime import setup, fixture_dispatch, run as run_native
    from native_event_worker_fixture import launch, tool as native_tool

    store, jobs, query = setup(tmp_path)
    handles = fixture_dispatch(monkeypatch)
    selected = []
    def excluded(context):
        assert context['native_event_targets'] == []
        job = jobs.db.execute('SELECT job_ref FROM orders').fetchone()[0]
        target, = jobs.native_event_targets(job)
        selected.append(target['handle'])
        return wait(condition(target['handle']))
    def repaired(context):
        assert context['feedback']['category'] == 'wait_target'
        assert context['feedback']['code'] == 'wait_target_not_visible'
        assert context['feedback']['detail'] == 'native_event_information_target_not_visible'
        assert context['feedback']['affected_refs'] == selected
        assert rows(store, 'episode_waits') == []
        # Three completed child operations and the returned launch are the
        # existing four observations; rejected native selection adds none.
        assert len(rows(store, 'runtime_observations')) == 4
        assert context['controller']['deltas'] == [0.0]
        return wait(condition())
    try:
        provider = ScriptedProvider([launch(query, {'subject_refs': [query]}, requested=False),
            native_tool('homology.configure'), native_tool('homology.stage'),
            native_tool('homology.submit'), excluded, repaired])
        summary = run_native(store, jobs, provider, tmp_path / 'run')
        assert summary['completed_actions'] == 2
        assert len(handles) == 1
        assert len(rows(store, 'runtime_observations')) == 5
        assert len(rows(store, 'episode_waits')) == 1
    finally:
        jobs.close()
        store.close()


def test_backend_native_kind_and_original_receipt_custody_survive_validation(tmp_path, monkeypatch):
    backend = DurableExecutionStore(tmp_path / 'executions')
    native = {'kind': 'systemd_user_service', 'unit': 'fixture.service', 'request_sha256': 'a' * 64}
    handle = native_target_handle(native)
    registration = {'version': 'native_event_registration_v1', 'handle': handle,
        'run_id': 'fixture', 'owner_episode_id': 'original-child-owner', 'job_ref': 'fixture-job',
        'registry_ref': 'fixture-registry', 'resource_id': 'fixture-resource', 'native_identity': native}
    backend.register_native_target(registration)
    monkeypatch.setattr(backend, 'status', lambda *a: pytest.fail('native target polled as commission'))
    assert backend.validate_event_targets(condition(handle)) == condition(handle)
    for event in ('returned', 'progress_committed'):
        with pytest.raises(EventTargetError) as error:
            backend.validate_event_targets(condition(handle, event=event))
        assert error.value.code == 'unsupported_wait_event'
        assert error.value.affected_refs == (handle,)
    raw = b'synthetic-exit-receipt-only'
    digest = hashlib.sha256(raw).hexdigest()
    publication = {'version': 'native_event_publication_v1', 'event': 'state_changed',
        'cause': 'service_exit_receipt_committed', 'record_ref': 'native_event_record_' + digest[:24],
        'receipt_sha256': digest, 'occurred_at': PAST}
    event = backend.publish_native_event(handle, publication, receipt_bytes=raw)
    wake = asyncio.run(backend.wait_events(condition(handle)))
    assert wake['events'] == [event]
    assert wake['reason'] == 'state_changed'
    assert backend.native_publication(handle, publication['record_ref'])['receipt_bytes'] == raw
    assert backend.native_target(handle) == registration


def test_persisted_unfinished_invalid_wait_restores_through_failed_action_without_sample(tmp_path, monkeypatch):
    store, tools, subject = configured(tmp_path)
    directory = tmp_path / 'run'
    binding = make_binding(tmp_path / 'state', directory)
    controllers = ControllerFactory(1)
    bad = 'source_original_unfinished_fixture'
    selected = condition(bad)
    options = {'execution_binding': binding, 'episode_binding_descriptors': []}

    async def interrupted_provider(self, condition):
        raise RuntimeError('synthetic interruption after durable wait selection')

    try:
        # Construct an isolated interrupted selected wait, emulating the old
        # admission gap; never reopen or modify a preserved scientific run.
        with monkeypatch.context() as initial:
            initial.setattr(DurableExecutionStore, 'validate_event_targets', lambda self, c: c)
            initial.setattr(DurableExecutionStore, 'wait_events', interrupted_provider)
            with pytest.raises(RuntimeError, match='synthetic interruption'):
                run(store, tools, ScriptedProvider([wait(selected)]), directory, controllers, **options)
        assert_empty_accounting(store, controllers)
        original_wait, = rows(store, 'episode_waits')
        original_action, = rows(store, 'runtime_actions')
        assert original_action['result'] is original_action['credit'] is None
        original_request = json.loads(original_wait['request'])
        assert original_request['condition'] == selected
        assert json.loads(original_wait['timing'])['intervals'][-1]['state'] == 'raised'

        def repair(context):
            assert context['feedback']['category'] == 'wait_target'
            assert context['feedback']['status'] == 'failed'
            assert context['feedback']['code'] == 'unknown_wait_target'
            assert context['feedback']['affected_refs'] == [bad]
            assert_empty_accounting(store, controllers)
            failed, = rows(store, 'runtime_actions')
            assert json.loads(failed['result'])['status'] == 'failed'
            assert failed['credit'] is None
            assert rows(store, 'episode_waits') == [original_wait]
            # Episode selects a separate reconsideration action, without
            # changing the failed selection, snapshot or original wait timer.
            return wait(condition())

        provider = ScriptedProvider([repair])
        summary = run(store, tools, provider, directory, controllers, resume=True, **options)
        assert summary['completed_actions'] == 1
        assert len(provider.contexts) == 1
        assert rows(store, 'episode_waits')[0] == original_wait
        failed, completed = rows(store, 'runtime_actions')
        assert failed['action'] == original_action['action']
        assert json.loads(failed['timing'])['intervals'][0] == json.loads(original_action['timing'])['intervals'][0]
        assert failed['credit'] is None and completed['credit'] == 0
        observations = rows(store, 'runtime_observations')
        slots = rows(store, 'runtime_completion_slots')
        assert len(observations) == len(slots) == 1
        assert json.loads(observations[0]['observation'])['decision_index'] == 1
        assert sum(len(c.deltas) for c in controllers.controllers) == 1
        unused = ScriptedProvider([])
        assert run(store, tools, unused, directory, controllers, resume=True, **options) == summary
        assert unused.contexts == []
        assert rows(store, 'runtime_observations') == observations
        assert rows(store, 'runtime_completion_slots') == slots
    finally:
        store.close()


def test_completed_wait_replays_original_outcome_without_validation_or_resampling(tmp_path, monkeypatch):
    store, tools, subject = configured(tmp_path)
    captured = {}
    actual_perform = Workflow.perform_selected_wait

    async def capture(self, source, selected, index):
        captured.update(workflow=self, source=source, index=index, selected=deepcopy(selected))
        return await actual_perform(self, source, selected, index)

    monkeypatch.setattr(Workflow, 'perform_selected_wait', capture)
    try:
        summary = run(store, tools, ScriptedProvider([wait(condition())]), tmp_path / 'run', ControllerFactory(1))
        assert summary['completed_actions'] == 1
        before = {name: rows(store, name) for name in ('episode_waits', 'runtime_actions',
            'runtime_observations', 'runtime_estimation_contexts')}
        wf, source = captured['workflow'], captured['source']
        def forbidden(*args, **kwargs):
            pytest.fail('completed wait revalidated or resampled')
        monkeypatch.setattr(wf, 'validate_wait_selection', forbidden)
        monkeypatch.setattr(wf, 'wait_estimate', forbidden)
        monkeypatch.setattr(wf.execution_backend, 'wait_events', forbidden)
        unit = wf.selected(source, {'kind': 'wait', 'condition': captured['selected']}, captured['index'])
        assert unit.decision_index == captured['index']
        replay = asyncio.run(actual_perform(wf, source, captured['selected'], captured['index']))
        assert replay['wait_outcome'] == json.loads(before['episode_waits'][0]['outcome'])
        assert replay['wait_estimate'] == json.loads(before['episode_waits'][0]['request'])['estimate_snapshot']
        assert replay['wait_outcome']['trigger'] is None
        assert {name: rows(store, name) for name in before} == before
    finally:
        store.close()


def test_dispatch_unrelated_keyerror_is_not_converted_to_target_feedback(tmp_path, monkeypatch):
    store, tools, subject = configured(tmp_path)
    async def broken(self, condition):
        raise KeyError('unrelated_provider_bug')
    monkeypatch.setattr(DurableExecutionStore, 'wait_events', broken)
    controllers = ControllerFactory(1)
    try:
        with pytest.raises(KeyError, match='unrelated_provider_bug'):
            run(store, tools, ScriptedProvider([wait(condition())]), tmp_path / 'run', controllers)
        assert_empty_accounting(store, controllers)
        action, = rows(store, 'runtime_actions')
        assert action['result'] is action['credit'] is None
    finally:
        store.close()


def test_backend_storage_failure_is_not_misreported_as_unknown_identity(tmp_path, monkeypatch):
    backend = DurableExecutionStore(tmp_path / 'executions')
    def unavailable(*args, **kwargs):
        raise DurableExecutionError('storage_failure', affected_refs=['fixture-database'])
    monkeypatch.setattr(backend, '_connect', unavailable)
    with pytest.raises(DurableExecutionError) as error:
        backend.validate_event_targets(condition('unknown_fixture'))
    assert error.value.failure['code'] == 'storage_failure'


def test_wait_failure_is_visible_in_literature_steering_with_complete_task():
    feedback = {'status': 'failed', 'category': 'wait_target', 'code': 'unknown_wait_target',
        'affected_refs': ['source_invalid_fixture'], 'detail': 'unknown_wait_target'}
    parent = {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
        'aspect': 'reference_evidence_parent'}, 'reference_evidence_parent': {
            'version': 'reference_evidence_parent_v1', 'source_refs': ['source_supplied_fixture']},
        'goal': {'objective': 'Evaluate the assigned experimental reference'}, 'feedback': feedback}
    rendered = render_reference_evidence_parent_prompt(parent, 'Retain the assigned experimental question.')
    task, steering = rendered.split('\n\nSTEERING', 1)
    assert REFERENCE_PARENT_TASK in task
    assert 'source_invalid_fixture' in steering and 'unknown_wait_target' in steering
    child = {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
        'aspect': 'assay'}, 'feedback': feedback}
    rendered = render_literature_experimental_prompt(child, 'Read the assigned original experiment.')
    task, steering = rendered.split('\n\nSTEERING', 1)
    assert EXPERIMENTAL_TASK in task
    assert 'source_invalid_fixture' in steering and 'unknown_wait_target' in steering
