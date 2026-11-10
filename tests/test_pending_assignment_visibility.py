"""A waiting parent retains its own assignment, without child-private work."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from method_loop import EpisodeGoal, EpisodeRequest

from gene_annotation_episode.runtime import Record, Workflow
from gene_annotation_episode.episode_commissions import CommissionCoordinator
from gene_annotation_episode.scientific_process_prompt import render_episode_steering
from gene_annotation_episode.waiting import validate_pending
from test_episode_commissions import setup_case


RECORDED = json.loads((Path(__file__).parent / 'fixtures/waiting/'
    'a11031-pending-assignment.json').read_text())
TASK_CONTEXT = json.loads((Path(__file__).parent / 'fixtures/waiting/'
    'a11032-pending-task-context.json').read_text())


def pending_frame(axis, *, returned=False, recorded=RECORDED):
    original = recorded['original_assignment']
    goal = EpisodeGoal.root(objective=original['objective'],
        result_contract={'private_contract': 'child_contract_not_pending_work'},
        task_context={'private_state': 'child_task_context_not_pending_work'})
    message = Record({'scope': deepcopy(original['scope']), 'episode_assignment': {
        'selection': {'evidence_axis': {'option_id': axis}},
        'context': deepcopy(original['context']),
        'constraints': deepcopy(original['constraints']),
        'evidence_refs': deepcopy(original['evidence_refs']),
        'private_configuration': 'child_configuration_not_pending_work'}})
    request = EpisodeRequest(goal, message)
    pending = recorded['pending_work']['items'][0]
    child = SimpleNamespace(handle=recorded['child_episode_id'], role='scientific_process',
        _request=request, decision_index=recorded['decision_index'],
        _task=SimpleNamespace(done=lambda: returned), selected_at=pending['selected_at'],
        _suspension=SimpleNamespace(condition={**pending['suspension'],
            'schedule_ref': 'private_child_schedule_not_pending_work'}))
    context = SimpleNamespace(_pending_children=lambda _path: [child])
    source = SimpleNamespace(episode_id=recorded['parent_episode_id'],
        path=(('annotation', 'root'),), _execution_context=context)
    workflow = SimpleNamespace(execution_binding=None)
    return workflow, source, child


@pytest.mark.parametrize('axis', ['A107', 'A110'])
@pytest.mark.parametrize('returned', [False, True], ids=['executing', 'returned'])
@pytest.mark.parametrize('recorded', [RECORDED, TASK_CONTEXT], ids=['focus-key', 'task-key'])
def test_original_assignment_survives_pending_view_and_actual_parent_renderer(axis, returned, recorded):
    workflow, source, child = pending_frame(axis, returned=returned, recorded=recorded)
    before = deepcopy(child._request.as_record())
    pending = Workflow.pending_work(workflow, source)
    assert validate_pending(pending) == pending
    item = pending['items'][0]
    assert item.get('original_assignment') == recorded['original_assignment']
    assert item['handle'] == recorded['pending_work']['items'][0]['handle']
    assert item['return_available'] is returned
    assert item['lifecycle_state'] == ('returned' if returned else 'executing')
    assert item['event_target'] is False
    assert 'schedule_ref' not in item['suspension']

    rendered = render_episode_steering({'pending_work': pending,
        'completed_action_reports': [], 'working_state': {}})
    assert recorded['original_assignment']['objective'] in rendered
    for value in recorded['original_assignment']['context'].values():
        assert value in rendered
    assert recorded['original_assignment']['scope']['subject_refs'][0] in rendered
    assert 'original_assignment.decision_index' in rendered
    for private in (recorded['child_episode_id'], child._request.goal.goal_id,
            'child_contract_not_pending_work', 'child_task_context_not_pending_work',
            'child_configuration_not_pending_work',
            'private_child_schedule_not_pending_work'):
        assert private not in json.dumps(pending)
        assert private not in rendered

    item['original_assignment']['scope']['subject_refs'].append('presentation_only')
    assert child._request.as_record() == before


def test_legacy_invocation_without_original_request_keeps_unknown_assignment():
    workflow, source, child = pending_frame('A107')
    del child._request
    item = Workflow.pending_work(workflow, source)['items'][0]
    assert item.get('original_assignment') is None
    assert item['handle'] == RECORDED['pending_work']['items'][0]['handle']
    assert item['event_target'] is False


@pytest.mark.parametrize('legacy_backend', [False, True], ids=['coordinator', 'legacy-backend'])
@pytest.mark.parametrize('task_inputs', [False, True], ids=['goal-only', 'complete-task-inputs'])
def test_external_pending_work_retains_frozen_assignment_without_new_receipts(tmp_path, legacy_backend, task_inputs):
    store, journal, backend, operands, _receipts = setup_case(tmp_path)
    with store:
        expected = {'objective': operands['child']['request']['goal']['objective'],
            'scope': operands['child']['scope'], 'decision_index': 7}
        if task_inputs:
            supplied = {'context': {'task': 'Preserve the original parent question.',
                'caller_named_detail': {'nested': ['source quantities', 'unknown identity']}},
                'constraints': {'preserve_source_scope': True},
                'evidence_refs': [operands['input_versions'][0]['reference']]}
            operands['child']['request']['message']['episode_assignment'] = deepcopy(supplied)
            store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
                (json.dumps(operands['child']['request']), operands['child']['episode_id']))
            expected.update(supplied)
        coordinator = CommissionCoordinator(store, journal, backend)
        spec = coordinator.select(**operands)
        if legacy_backend:
            coordinator.dispatch(spec['handle'])
        source = SimpleNamespace(episode_id=spec['parent']['episode_id'],
            _execution_context=None)
        workflow = SimpleNamespace(execution_binding=None if legacy_backend else object(),
            commissions=coordinator, store=store, run_id=journal.run_id,
            execution_backend=backend)
        pending = Workflow.pending_work(workflow, source)
        assert validate_pending(pending) == pending
        item = pending['items'][0]
        assert item['original_assignment'] == expected
        assert item['handle'] == spec['handle']
        assert item['event_target'] is True
        for private in (spec['child']['episode_id'],
                spec['child']['request']['goal']['goal_id']):
            assert private not in json.dumps(item['original_assignment'])
        assert store.db.execute('SELECT count(*) FROM runtime_record_receipts').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        assert journal.row('runtime_actions', source.episode_id, 7)['credit'] is None
