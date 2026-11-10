"""Parent waits use existing owned tasks; they do not collect or score them."""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_prompt import render_episode_steering
from gene_annotation_episode.waiting import completed_action_context
from method_loop.durable import EventTargetError
from method_loop.episode import Context
from method_loop.suspension import SuspensionState


RECORDED = json.loads((Path(__file__).parent / 'fixtures/waiting/'
    'a11029-owned-child-wait.json').read_text())


def public_handle(parent, child):
    return 'pending_child_' + hashlib.sha256((parent + ':' + child).encode()).hexdigest()


def setup_owned(children=1):
    path = (('annotation', 'root'),)
    gates = [asyncio.Event() for _ in range(children)]
    invocations = []
    for index, gate in enumerate(gates):
        handle = RECORDED['child_episode_id'] if index == 0 else 'other-owned-child'
        invocation = SimpleNamespace(handle=handle, role='scientific_process',
            _task=asyncio.create_task(gate.wait()), _suspension=SuspensionState(),
            _delivered=False)
        invocation.status = lambda item=invocation: {
            'state': 'returned' if item._task.done() else 'running', 'delivered': item._delivered}
        invocations.append(invocation)
    context = SimpleNamespace(_independent_invocations={path: invocations},
        _suspension=SuspensionState())
    for name in ('_pending_children', '_ready_owned_child', '_next_owned_child'):
        setattr(context, name, MethodType(getattr(Context, name), context))
    source = SimpleNamespace(episode_id=RECORDED['episode_id'], path=path,
        _execution_context=context)

    def backend_forbidden(*args, **kwargs):
        raise AssertionError('owned child waiting reached the external job backend')

    def pending(_source):
        original = deepcopy(RECORDED['pending_work'])
        template = original['items'][0]
        original['items'] = [{**template, 'handle': public_handle(source.episode_id, item.handle),
            'return_available': item._task.done(),
            'lifecycle_state': 'returned' if item._task.done() else 'executing'}
            for item in invocations if not item._delivered]
        return original

    workflow = SimpleNamespace(execution_binding=None, native_event_information=None,
        pending_work=pending, run_id='owned-wait-case',
        execution_backend=SimpleNamespace(validate_event_targets=backend_forbidden),
        wait_store=SimpleNamespace(get=backend_forbidden),
        journal=SimpleNamespace(row=lambda *args: {'request': json.dumps({'context': {
            'pending_work': pending(source)}})}),
        wait_estimate=lambda *args: {'scientific_gain': None, 'monitoring_gain': None})
    workflow.validate_wait_selection = MethodType(Workflow.validate_wait_selection, workflow)
    return workflow, source, gates, invocations


async def finish(gates, invocations):
    for gate in gates:
        gate.set()
    await asyncio.gather(*(item._task for item in invocations))


def test_actual_root_return_condition_reaches_owned_scheduler():
    async def scenario():
        workflow, source, gates, invocations = setup_owned()
        try:
            assert public_handle(source.episode_id, invocations[0].handle) == RECORDED['condition']['events'][0]['handle']
            assert workflow.validate_wait_selection(source, RECORDED['condition']) == RECORDED['condition']
        finally:
            await finish(gates, invocations)
    asyncio.run(scenario())


def test_parent_presentation_keeps_inprocess_event_target_distinction():
    text = render_episode_steering({'pending_work': deepcopy(RECORDED['pending_work']),
        'completed_action_reports': [], 'working_state': {}})
    assert RECORDED['condition']['events'][0]['handle'] in text
    assert '| [0].event_target | false |' in text


def test_external_wait_keeps_its_existing_validation_route():
    async def scenario():
        workflow, source, gates, invocations = setup_owned()
        selected = deepcopy(RECORDED['condition'])
        selected['events'][0]['handle'] = 'original-external-job'
        received = []

        def validate(condition):
            received.append(deepcopy(condition))
            return condition

        workflow.execution_backend.validate_event_targets = validate
        try:
            assert workflow.validate_wait_selection(source, selected) == selected
            assert received == [selected]
            assert not invocations[0]._delivered
        finally:
            await finish(gates, invocations)
    asyncio.run(scenario())


@pytest.mark.parametrize('ready_index', [0, 1], ids=['selected-child', 'ready-sibling'])
def test_wait_releases_for_owned_return_without_receiving_or_cancelling(ready_index):
    async def scenario():
        workflow, source, gates, invocations = setup_owned(2)
        waiting = asyncio.create_task(Workflow.perform_selected_wait(
            workflow, source, deepcopy(RECORDED['condition']), 14))
        try:
            await asyncio.sleep(0)
            assert not waiting.done()
            gates[ready_index].set()
            result = await waiting
            assert result['status'] == 'completed'
            assert result['record_refs'] == result['changed_record_refs'] == []
            assert result['result']['ready_handle'] == public_handle(
                source.episode_id, invocations[ready_index].handle)
            assert result['result']['selected_return_available'] == (ready_index == 0)
            assert result['result']['receipt_status'] == 'awaiting_original_scheduler_collection'
            assert all(not item._delivered and not item._task.cancelled() for item in invocations)
            assert result['wait_estimate']['scientific_gain'] is None
            retained = completed_action_context({},
                pending_at_selection=RECORDED['pending_work'],
                pending_after_action=result['pending_work_after_action'],
                wait_estimate_at_selection=result['wait_estimate'])
            assert retained['wait_outcome'] is None
            assert retained['wait_estimate_at_selection']['scientific_gain'] is None
        finally:
            if not waiting.done():
                waiting.cancel()
                await asyncio.gather(waiting, return_exceptions=True)
            await finish(gates, invocations)
    asyncio.run(scenario())


def test_cancelling_wait_keeps_original_children_alive():
    async def scenario():
        workflow, source, gates, invocations = setup_owned(2)
        waiting = asyncio.create_task(Workflow.perform_selected_wait(
            workflow, source, deepcopy(RECORDED['condition']), 14))
        try:
            await asyncio.sleep(0)
            waiting.cancel()
            await asyncio.gather(waiting, return_exceptions=True)
            assert all(not item._task.cancelled() and not item._delivered for item in invocations)
        finally:
            await finish(gates, invocations)
    asyncio.run(scenario())


@pytest.mark.parametrize('defect', ['foreign-parent', 'state-changed', 'already-after-return', 'mixed'])
def test_unsupported_owned_wait_does_not_fall_back_to_timer_or_job_backend(defect):
    async def scenario():
        workflow, source, gates, invocations = setup_owned()
        selected = deepcopy(RECORDED['condition'])
        if defect == 'foreign-parent':
            selected['events'][0]['handle'] = public_handle('other-parent', invocations[0].handle)
        elif defect == 'state-changed':
            selected['events'][0]['event'] = 'state_changed'
        elif defect == 'already-after-return':
            selected['events'][0]['after_cursor'] = 1
        else:
            selected['events'].append({'handle': 'external-job', 'event': 'returned', 'after_cursor': 0})
        try:
            with pytest.raises(EventTargetError):
                workflow.validate_wait_selection(source, selected)
            assert not invocations[0]._delivered
        finally:
            await finish(gates, invocations)
    asyncio.run(scenario())
