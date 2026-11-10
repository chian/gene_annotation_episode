"""One-shot scoring runs within the existing action, outside transactions."""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import json
import sqlite3
from types import MethodType, SimpleNamespace

import pytest

from gene_annotation_episode.runtime import DecisionSource, Workflow
from gene_annotation_episode.state import Store


def fixture(*, fail=False):
    database = sqlite3.connect(':memory:')
    calls, receipts, completions = [], [], []
    source = SimpleNamespace(episode_id='episode_original')
    context = SimpleNamespace(episode_id=source.episode_id, received_record_refs=())
    judgment = {'judgment_ref': 'judgment_original', 'instructions': 'Interpret the received design.',
        'context': {'assessments': ['assessment_original']}, 'output_schema': {'type': 'object'}}
    cached = {}

    def prepare(bound):
        assert bound is context and not database.in_transaction
        return [{**judgment, **cached}]

    def complete(bound, reference, response=None, *, provenance, failure=None):
        assert bound is context and reference == judgment['judgment_ref']
        assert not database.in_transaction
        completions.append({'response': response, 'provenance': provenance, 'failure': failure})
        outcome = ({'status': 'unavailable', 'record_refs': [], 'changed_record_refs': []}
            if failure else {'status': 'completed', 'record_refs': ['source_final'],
                'changed_record_refs': ['source_final']})
        cached['completed_outcome'] = deepcopy(outcome)
        cached['completed_provenance'] = deepcopy(provenance)
        return outcome

    async def provider(session_key, phase, instructions, inputs, schema):
        assert not database.in_transaction
        calls.append((session_key, phase, instructions, inputs, schema))
        if fail:
            raise RuntimeError('synthetic provider failure')
        return {'selection': {'scope_statement': 'synthetic received scope'}}

    binding = SimpleNamespace(automatic_score_judgments=prepare, complete_score_judgment=complete)
    def receive(episode, refs, **kwargs):
        receipts.append((episode, refs, kwargs))
        context.received_record_refs = tuple(dict.fromkeys([*context.received_record_refs, *refs]))

    workflow = SimpleNamespace(store=SimpleNamespace(db=database),
        specialist=lambda selected: binding, binding_context=lambda selected: context,
        provider=SimpleNamespace(complete=provider),
        receipts=SimpleNamespace(receive=receive))
    result = {'status': 'completed', 'record_refs': ['source_assessment'],
        'changed_record_refs': ['source_assessment'], 'result': {'measurement': 2}}
    return workflow, source, result, calls, receipts, completions


def test_score_judgment_is_one_call_and_replays_its_outcome_into_original_action():
    workflow, source, original, calls, receipts, completions = fixture()
    try:
        updated = asyncio.run(Workflow.automatic_score_updates(workflow, source, 7, original))
        assert len(calls) == len(completions) == 1
        assert calls[0][:2] == ('judgment_original', 'REASONING')
        assert completions[0]['provenance']['episode_id'] == source.episode_id
        assert completions[0]['provenance']['decision_index'] == 7
        assert updated['record_refs'] == ['source_assessment', 'source_final']
        assert updated['changed_record_refs'] == ['source_assessment', 'source_final']
        assert updated['result'] == original['result']
        assert original['record_refs'] == ['source_assessment']
        # Crash after owner publication but before the original action's journal
        # update: recover from its saved owner outcome, without another call.
        replay = asyncio.run(Workflow.automatic_score_updates(workflow, source, 7, original))
        assert replay == updated and len(calls) == len(completions) == 1
        assert receipts == [(source.episode_id, ['source_final'],
            {'kind': 'own_action', 'source_index': 7})] * 2
        later = asyncio.run(Workflow.automatic_score_updates(workflow, source, 8, original))
        assert later == original and len(calls) == 1
        assert len(receipts) == 2
    finally:
        workflow.store.db.close()


def test_failed_judgment_stays_unresolved_without_retry_or_fabricated_score():
    workflow, source, original, calls, receipts, completions = fixture(fail=True)
    try:
        first = asyncio.run(Workflow.automatic_score_updates(workflow, source, 2, original))
        second = asyncio.run(Workflow.automatic_score_updates(workflow, source, 2, original))
        assert first == second == original
        assert len(calls) == len(completions) == 1
        assert completions[0]['failure'] == {'code': 'automatic_score_judgment_call_failed',
            'exception_type': 'RuntimeError'}
        assert all(not refs for _, refs, _ in receipts)
    finally:
        workflow.store.db.close()


def test_open_write_transaction_prevents_model_call():
    workflow, source, original, calls, receipts, completions = fixture()
    try:
        workflow.store.db.execute('BEGIN')
        with pytest.raises(ValueError, match='requires_committed_inputs'):
            asyncio.run(Workflow.automatic_score_updates(workflow, source, 2, original))
        assert not calls and not receipts and not completions
    finally:
        workflow.store.db.rollback()
        workflow.store.db.close()


def test_original_action_commits_receives_judges_then_projects_once():
    workflow, source, original, calls, receipts, completions = fixture()
    action_rows, stages = {}, {}
    workflow.store._savepoint = 0
    workflow.store.transaction = MethodType(Store.transaction, workflow.store)
    workflow.run_id = 'run_fixture'
    workflow.execution_binding = object()
    workflow.wait_inputs_version = workflow.completed_action_inputs_version = None
    workflow.pending_work = lambda selected: {}
    workflow.execute = lambda *args, **kwargs: deepcopy(original)
    workflow.journal = SimpleNamespace(
        row=lambda table, episode, index: action_rows.get(index),
        save=lambda table, row: action_rows.update({row['decision_index']: deepcopy(row)}),
        measure=lambda *args: nullcontext())
    workflow.receive_native_outcome = lambda *args: None
    def receive(selected, selection, result, index):
        assert workflow.store.db.in_transaction
        workflow.receipts.receive(selected.episode_id, result['record_refs'],
            kind='own_action', source_index=index)
    workflow.receive_outcome = receive
    workflow.automatic_score_updates = MethodType(Workflow.automatic_score_updates, workflow)
    projections = []
    def project(selected):
        assert workflow.store.db.in_transaction
        assert any('source_final' in refs for _, refs, _ in receipts)
        assert len(calls) == 1
        projections.append(selected.episode_id)
        return {'credit': 5}
    workflow.source_credit_view = project
    workflow.controller_value = lambda selected, index, credit: credit
    workflow.completions = SimpleNamespace(stage=lambda episode, index, **kwargs:
        stages.update({index: kwargs}))
    source.workflow = workflow
    source.path = (('annotation', 'root'), ('literature', 'child'))
    source.checkpoint = lambda: None
    selection = {'kind': 'tool', 'tool': 'fixture.grade', 'arguments': {}}
    try:
        assert asyncio.run(DecisionSource.execute(source, selection, 7)) == 5
        assert len(action_rows) == len(stages) == len(calls) == len(projections) == 1
        saved = json.loads(action_rows[7]['result'])
        assert saved['record_refs'] == ['source_assessment', 'source_final']
        assert action_rows[7]['credit'] == 5
        assert asyncio.run(DecisionSource.execute(source, selection, 7)) == 5
        assert len(action_rows) == len(stages) == len(calls) == len(projections) == 1
    finally:
        workflow.store.db.close()
