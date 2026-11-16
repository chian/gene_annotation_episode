"""A waiting parent retains its own assignment, without child-private work."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeGoal, EpisodeRequest

from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.episodic_workflow.root.library.decision_steering_display import render_episode_steering
from gene_annotation_episode.episodic_workflow.root.wait_events import validate_pending


RECORDED = json.loads((Path(__file__).resolve().parents[1] / 'gene_annotation_episode/episodic_workflow/root/a110/tests/fixtures/waiting/'
    'a11031-pending-assignment.json').read_text())
TASK_CONTEXT = json.loads((Path(__file__).resolve().parents[1] / 'gene_annotation_episode/episodic_workflow/root/a110/tests/fixtures/waiting/'
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


