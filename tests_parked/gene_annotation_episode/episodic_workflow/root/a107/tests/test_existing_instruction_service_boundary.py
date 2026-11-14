"""Actual installed decision-method service dispatch, with controlled ports.

These checks construct the actual decision mixin normally. They do not build a
whole Workflow, execute an iterator, or claim scientific/saved restoration.
"""
import importlib
import os
from types import SimpleNamespace

import pytest

AXIS = 'a107'
PHASE = os.environ['FOURTH_EXISTING_INSTRUCTION_PHASE']
assert PHASE in {'baseline', 'connected'}
HOMES = (
    ('execution_progress_assessment', 'MonitorTaskDecision'),
    ('scientific_process/execution_progress_assessment', 'MonitorTaskDecision'),
    ('hpc_work_planning', 'HPCWorkTaskDecision'),
    ('hpc_work_planning/hpc_allocation_execution', 'HPCWorkTaskDecision'),
    ('hpc_work_planning/hpc_resource_prediction', 'PredictionTaskDecision'),
    ('hpc_work_planning/execution_progress_assessment', 'MonitorTaskDecision'),
    ('hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', 'MonitorTaskDecision'),
    ('scientific_process/hpc_work_planning', 'HPCWorkTaskDecision'),
    ('scientific_process/hpc_work_planning/hpc_allocation_execution', 'HPCWorkTaskDecision'),
    ('scientific_process/hpc_work_planning/hpc_resource_prediction', 'PredictionTaskDecision'),
    ('scientific_process/hpc_work_planning/execution_progress_assessment', 'MonitorTaskDecision'),
    ('scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', 'MonitorTaskDecision'),
)


@pytest.fixture(params=HOMES, ids=[row[0] for row in HOMES])
def decision(request):
    home, name = request.param
    prefix = 'gene_annotation_episode.episodic_workflow.root.' + AXIS
    module = importlib.import_module(prefix + '.' + home.replace('/', '.') + '.task_decision')
    source = getattr(module, name)()
    return source, module


def forbidden(*args, **kwargs):
    raise AssertionError('custom_service_dispatch_called_default_composer')


def test_custom_service_return_is_preserved_without_default_lookup(decision):
    source, _ = decision
    context, returned, calls = {'input': object()}, object(), []
    def callback(actual_source, actual_context):
        calls.append((actual_source, actual_context))
        return returned
    source.workflow = SimpleNamespace(services=SimpleNamespace(instructions=callback), specialist=forbidden)
    if PHASE == 'baseline':
        with pytest.raises(AssertionError, match='^custom_service_dispatch_called_default_composer$'):
            source.instructions(context)
        assert calls == []
        return
    assert source.instructions(context) is returned
    assert len(calls) == 1 and calls[0][0] is source and calls[0][1] is context


def test_custom_service_exception_identity_is_preserved(decision):
    source, _ = decision
    class CallbackFailure(Exception):
        pass
    failure, calls, context = CallbackFailure('controlled original callback failure'), [], {}
    def callback(actual_source, actual_context):
        calls.append((actual_source, actual_context))
        raise failure
    source.workflow = SimpleNamespace(services=SimpleNamespace(instructions=callback), specialist=forbidden)
    if PHASE == 'baseline':
        with pytest.raises(AssertionError, match='^custom_service_dispatch_called_default_composer$'):
            source.instructions(context)
        assert calls == []
        return
    with pytest.raises(CallbackFailure) as caught:
        source.instructions(context)
    assert caught.value is failure
    assert len(calls) == 1 and calls[0][0] is source and calls[0][1] is context


def _check_default_service_preserves_installed_composer_and_call_order(decision, exchange):
    source, module = decision
    prefix = 'gene_annotation_episode.episodic_workflow.root.' + AXIS
    services_type = importlib.import_module(prefix + '.episode_services').WorkflowServices
    calls, marker = [], object()
    def specialized(context):
        assert context is marker
        calls.append('binding.instructions')
        return 'controlled original commissioned goal'
    binding = SimpleNamespace(instructions=specialized, replaces_default_instructions=True)
    def specialist(actual_source):
        assert actual_source is source
        calls.append('specialist')
        return binding
    def binding_context(actual_source):
        assert actual_source is source
        calls.append('binding_context')
        return marker
    def permits(actual_source, action):
        assert actual_source is source
        calls.append(('permits', action))
        return action == 'wait'
    workflow = SimpleNamespace(specialist=specialist, binding_context=binding_context,
        permits_common_action=permits, native_event_information=object(),
        decision_protocol='decision_exchange_v1' if exchange else None,
        knowledge=SimpleNamespace(instructions=' original knowledge'),
        launch_instructions=SimpleNamespace(instructions=' original launch library'))
    workflow.services = services_type(workflow)
    source.workflow = workflow
    context = {'tool_knowledge': {}, 'launch_instruction_library': {}}
    expected = module.instructions(source, context)
    expected_calls = list(calls)
    calls.clear()
    assert source.instructions(context) == expected
    assert calls == expected_calls


def test_default_service_preserves_ordinary_composer_and_call_order(decision):
    _check_default_service_preserves_installed_composer_and_call_order(decision, False)


def test_default_service_preserves_exchange_composer_and_call_order(decision):
    _check_default_service_preserves_installed_composer_and_call_order(decision, True)
