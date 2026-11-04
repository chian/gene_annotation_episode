"""Recovery consumers using the stable, real detached Workflow fixture.

Only selected failures, interruption points and provider choices are fixtures.
These checks establish persistence and accounting, not scientific validity.
"""
import asyncio
from copy import deepcopy
import json
import os

import pytest

from method_loop.durable import DurableExecutionStore
from gene_annotation_episode.runtime import DecisionSource
from gene_annotation_episode.state import Store
from detached_workflow_fixture import FixtureTools, ScriptedProvider, commission, tool
from test_detached_workflow import (InterruptedParent, Scenario,
                                    assert_original_child_closure)


@pytest.fixture
def scenario(tmp_path):
    return Scenario(tmp_path)


async def retire_selected_worker(scenario):
    """Release actual selected work even when a parent-side assertion fails."""
    await scenario.cleanup()
    with Store(scenario.workspace) as store:
        installed = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='runtime_commission_intents'").fetchone()
        selected = (store.db.execute('SELECT 1 FROM runtime_commission_intents').fetchone()
                    if installed else None)
    if selected:
        returned = await scenario.returned()
        assert_original_child_closure(scenario, returned)
        return returned


def test_restart_preserves_failed_tool_outcome_and_feedback_without_observation(
        scenario, monkeypatch):
    feedback = {'status': 'failed', 'category': 'fixture_selected_work',
        'code': 'fixture_input_unavailable', 'affected_refs': [scenario.subject]}
    failed_result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [],
        'error_code': 'fixture_input_unavailable', 'feedback': feedback}
    attempts = []
    original_execute = FixtureTools.execute
    original_next = DecisionSource.next
    interrupted = []

    def fail_parent_one(self, name, arguments, *, scope, operation_key):
        # This patch exists only in the parent interpreter. The pinned worker
        # module and its child_one/read operations remain unchanged.
        if name == 'fixture.publish' and arguments['label'] == 'parent_one':
            attempts.append({'operation_key': operation_key, 'pid': os.getpid()})
            return deepcopy(failed_result)
        return original_execute(self, name, arguments, scope=scope,
                                operation_key=operation_key)

    monkeypatch.setattr(FixtureTools, 'execute', fail_parent_one)

    async def interrupt_before_another_decision(self, view):
        if not interrupted and (self.last_outcome or {}).get('status') == 'failed':
            assert self.last_outcome['feedback'] == self.feedback == feedback
            with Store(scenario.workspace) as store:
                assert scenario.observations(store) == scenario.frozen_slots(store) == []
            interrupted.append(True)
            # Interrupt before call() can save a future provider request. The
            # restart must restore source state rather than reuse such a request.
            raise InterruptedParent('interrupt after failed own action')
        return await original_next(self, view)

    monkeypatch.setattr(DecisionSource, 'next', interrupt_before_another_decision)

    async def exercise():
        try:
            first = ScriptedProvider([commission(scenario.subject), scenario.child_live])
            with pytest.raises(InterruptedParent, match='after failed own action'):
                await scenario.run(first, completed_actions=1)
            spec = scenario.spec()
            identity = scenario.backend.status(spec['handle'])['execution_identity']
            assert scenario.backend.status(spec['handle'])['liveness'] == 'live'
            with Store(scenario.workspace) as store:
                root = scenario.root(store)
                row = store.db.execute('SELECT * FROM runtime_actions WHERE episode_id=? '
                    'AND decision_index=1', (root['episode_id'],)).fetchone()
                original_failure = dict(row)
                original_outcome = json.loads(row['result'])
                assert {key: original_outcome[key] for key in failed_result} == failed_result
                assert row['credit'] is None
                assert scenario.observations(store) == scenario.frozen_slots(store) == []
                assert store.db.execute('SELECT count(*) FROM runtime_model_calls '
                    'WHERE episode_id=?', (root['episode_id'],)).fetchone()[0] == 2
                checkpoint = json.loads(store.db.execute('SELECT source_state FROM '
                    'runtime_source_states WHERE episode_id=?', (root['episode_id'],)).fetchone()[0])
                assert checkpoint['last_outcome_index'] == 1
                assert checkpoint['feedback'] == feedback

            def explicit_followup(context):
                assert context['last_local_outcome'] == original_outcome
                assert context['feedback'] == feedback
                assert context['current_credit'] == 0
                assert context['controller']['deltas'] == []
                assert context['child_reports'] == []
                pending = context['pending_work']['items']
                assert len(pending) == 1 and pending[0]['handle'] == spec['handle']
                status = scenario.backend.status(spec['handle'])
                assert status['execution_identity'] == identity and status['liveness'] == 'live'
                with Store(scenario.workspace) as store:
                    assert scenario.observations(store) == scenario.frozen_slots(store) == []
                # A new useful action is an explicit episode choice. The failed
                # parent_one selection is never automatically tried again.
                return tool('parent_followup')

            second = ScriptedProvider([explicit_followup])
            summary = await scenario.run(second, completed_actions=1, resume=True)
            assert len(first.contexts) == 2 and len(second.contexts) == 1
            assert summary['state'] == 'yielded_with_pending_work'
            assert summary['pending_handles'] == [spec['handle']]
            assert summary['completed_actions'] == 1 and summary['credit'] == 1
            assert attempts == [{'operation_key':
                f"{spec['run_id']}:{spec['parent']['episode_id']}:1", 'pid': os.getpid()}]
            with Store(scenario.workspace) as store:
                assert dict(store.db.execute('SELECT * FROM runtime_actions WHERE episode_id=? '
                    'AND decision_index=1', (spec['parent']['episode_id'],)).fetchone()) == original_failure
                observations = deepcopy(scenario.observations(store))
                slots = deepcopy(scenario.frozen_slots(store))
                assert [row['decision_index'] for row in observations] == [2]
                assert [row['step']['delta'] for row in observations] == [1]
                assert [row['original_decision_index'] for row in slots] == [2]
                assert store.db.execute('SELECT count(*) FROM runtime_commission_intents').fetchone()[0] == 1
                operations = [json.loads(row[0]) for row in store.db.execute(
                    'SELECT selection FROM detached_fixture_operations')]
                assert [row['arguments']['label'] for row in operations] == ['parent_followup']
            return spec, identity, original_failure, observations, slots
        finally:
            await retire_selected_worker(scenario)

    spec, identity, original_failure, observations, slots = asyncio.run(exercise())
    with Store(scenario.workspace) as store:
        assert scenario.observations(store) == observations
        assert scenario.frozen_slots(store) == slots
        assert dict(store.db.execute('SELECT * FROM runtime_actions WHERE episode_id=? '
            'AND decision_index=1', (spec['parent']['episode_id'],)).fetchone()) == original_failure
    status = scenario.backend.status(spec['handle'])
    assert status['execution_identity'] == identity
    assert status['lifecycle_state'] == 'returned' and status['acknowledgment_id'] is None
    assert len(attempts) == 1


def test_restart_acknowledges_staged_child_before_replay_immediately_stops(
        scenario, monkeypatch):
    original_acknowledge = DurableExecutionStore.acknowledge
    calls, committed = [], {}

    def interrupt_acknowledge_once(self, handle, return_id, admission_id):
        calls.append({'handle': handle, 'return_id': return_id, 'admission_id': admission_id})
        if len(calls) == 1:
            # A separate Store connection proves C4 admission and F2 staging
            # committed together before the interrupted backend acknowledgment.
            with Store(scenario.workspace) as store:
                committed['observations'] = deepcopy(scenario.observations(store))
                committed['slots'] = deepcopy(scenario.frozen_slots(store))
                committed['admission'] = dict(store.db.execute(
                    'SELECT * FROM runtime_return_admissions').fetchone())
                committed['action'] = dict(store.db.execute('SELECT * FROM runtime_actions '
                    'WHERE episode_id=? AND decision_index=0',
                    (scenario.root(store)['episode_id'],)).fetchone())
                assert [row['decision_index'] for row in committed['observations']] == [1, 2]
                assert [row['original_decision_index'] for row in committed['slots']] == [1, 2, 0]
                slot = committed['slots'][-1]
                assert slot['kind'] == 'child_return' and slot['sequence'] == 2
                assert slot['child_return'] == calls[0]
                admission = json.loads(committed['admission']['admission'])
                assert admission['state'] == 'admitted'
                assert admission['controller_input'] == slot['controller_input']
                assert admission['admission_id'] == admission_id
                assert admission['original_decision_index'] == 0
                assert committed['action']['credit'] == 2
            status = self.status(handle)
            assert status['return_id'] == return_id
            assert status['lifecycle_state'] == 'returned' and status['acknowledgment_id'] is None
            committed['identity'] = status['execution_identity']
            raise InterruptedParent('interrupt after admission and staging commit')
        assert calls[-1] == calls[0]
        return original_acknowledge(self, handle, return_id, admission_id)

    monkeypatch.setattr(DurableExecutionStore, 'acknowledge', interrupt_acknowledge_once)

    async def exercise():
        try:
            first = ScriptedProvider([commission(scenario.subject), scenario.child_live,
                                      scenario.select_wait])
            with pytest.raises(InterruptedParent, match='after admission and staging commit'):
                await scenario.run(first, completed_actions=3)
            await asyncio.gather(*scenario.tasks)
            assert len(first.contexts) == 3 and len(calls) == 1
            with Store(scenario.workspace) as store:
                assert scenario.observations(store) == committed['observations']
                assert scenario.frozen_slots(store) == committed['slots']

            def no_recovery_inbox_drain(*_args, **_kwargs):
                raise AssertionError('staged child replay must stop before inbox inspection')

            monkeypatch.setattr(DurableExecutionStore, 'return_page', no_recovery_inbox_drain)
            unused = ScriptedProvider([])
            summary = await scenario.run(unused, completed_actions=3, resume=True)
            assert unused.contexts == []
            assert len(calls) == 2 and calls[1] == calls[0]
            assert summary['state'] == 'yielded' and summary['pending_handles'] == []
            assert summary['completed_actions'] == 3 and summary['credit'] == 2
            with Store(scenario.workspace) as store:
                observations = scenario.observations(store)
                assert observations[:2] == committed['observations']
                assert [row['decision_index'] for row in observations] == [1, 2, 0]
                assert [row['step']['delta'] for row in observations] == [1, 0, 1]
                assert observations[-1]['step']['stop'] is True
                assert scenario.frozen_slots(store) == committed['slots']
                assert dict(store.db.execute('SELECT * FROM runtime_return_admissions').fetchone()) == committed['admission']
                assert dict(store.db.execute('SELECT * FROM runtime_actions WHERE episode_id=? '
                    'AND decision_index=0', (scenario.root(store)['episode_id'],)).fetchone()) == committed['action']
                assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1
                assert store.db.execute('SELECT count(*) FROM runtime_report_attempts').fetchone()[0] == 1
                assert store.db.execute('SELECT count(*) FROM runtime_commission_intents').fetchone()[0] == 1
                assert store.db.execute('SELECT count(*) FROM detached_fixture_operations').fetchone()[0] == 3
            status = scenario.backend.status(calls[0]['handle'])
            assert status['lifecycle_state'] == 'admitted'
            assert status['acknowledgment_id'] == calls[0]['admission_id']
            assert status['execution_identity'] == committed['identity']
            assert scenario.backend.start(calls[0]['handle'])['execution_identity'] == committed['identity']
        finally:
            await retire_selected_worker(scenario)

    asyncio.run(exercise())
