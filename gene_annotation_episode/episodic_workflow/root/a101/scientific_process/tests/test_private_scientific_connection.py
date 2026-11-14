"""Private scientific binding selection and prompt composition connections."""
from contextlib import nullcontext
import importlib
from types import SimpleNamespace

import pytest

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a101'
runtime = importlib.import_module(PACKAGE + '.runtime')
Binding = importlib.import_module(PACKAGE + '.scientific_process.episode').ScientificProcessEpisode
Task = importlib.import_module(PACKAGE + '.scientific_process.task').ScientificInvestigationTask


def test_private_binding_declares_independent_task_and_responsibilities():
    assert Binding.decision_source_type is Task
    assert not issubclass(Task, runtime.DecisionSource)
    expected = {'instructions': 'goal', 'prepare_assignment': 'from_parent',
        'facts': 'to_parent', 'decision_context': 'internal_summary', 'execute': 'scientific_operations',
        'credit_view': 'credit', 'yield_controller': 'yield_estimator', 'restore_saved_process': 'process_state'}
    for name, module in expected.items():
        assert getattr(Binding, name).__module__ == PACKAGE + '.scientific_process.' + module
    for name, module in {'execute': 'task', 'next': 'task', 'call': 'task_decision',
        'decision_inputs': 'decision_inputs', 'decision_state': 'decision_state',
        'finish': 'report_delivery', 'restore': 'task_state', 'suspension_changed': 'waiting'}.items():
        assert getattr(Task, name).__module__ == PACKAGE + '.scientific_process.' + module


def test_original_runtime_constructs_declared_private_scientific_task(monkeypatch):
    Registry = importlib.import_module(PACKAGE + '.episode_bindings').EpisodeBindingRegistry
    binding = Binding(SimpleNamespace(), library=SimpleNamespace(as_record=lambda: {'version': 'fixture'}, headers=lambda: []), tool_library=SimpleNamespace(as_record=lambda: {'version': 'fixture'}), child_roles=('scientific_process',))
    binding.restore_closed_process = lambda context: None
    binding.validate_context = lambda context: None
    monkeypatch.setattr(runtime.Episode, 'identity', lambda *args, **kwargs: SimpleNamespace(episode_id='science'))
    monkeypatch.setattr(runtime, 'FeedbackEpisode', lambda grain, key, source, *args, **kwargs: source)
    workflow = SimpleNamespace(context=object(), grains={'scientific_process': object()},
        inprocess_completion_order=None, receipts=None, scientific_process_binding=binding,
        episode_bindings=Registry((binding,)), contract_information_profile=lambda source: None,
        binding_context=lambda source: source, specialist=lambda source: binding,
        journal=SimpleNamespace(row=lambda *args: None, save=lambda *args: None),
        run_id='run', store=SimpleNamespace(transaction=nullcontext, db=SimpleNamespace(execute=lambda *args: None)),
        source_credit_view=lambda source: {'credit': 0}, expose_assigned_job=lambda source: None,
        receive_tool_attributions=lambda *args, **kwargs: None, archive=SimpleNamespace(store=lambda value: value))
    task = runtime.Workflow.build(workflow, 'scientific_process', 'science', 'Resolve qualified scientific findings', {})
    assert type(task) is Task
    assert task.path == (('scientific_process', 'science'),)


@pytest.mark.parametrize('replace_default', [False, True])
@pytest.mark.parametrize('exchange', [False, True])
@pytest.mark.parametrize('wait', [False, True])
def test_private_instruction_composer_preserves_actual_scientific_guidance(replace_default, exchange, wait):
    private = importlib.import_module(PACKAGE + '.scientific_process.task_instructions')
    original = importlib.import_module(PACKAGE + '.runtime_prompt')
    binding = SimpleNamespace(instructions=lambda context: 'Actual selected scientific goal',
        replaces_default_instructions=replace_default)
    source = SimpleNamespace(path=(('scientific_process', 'science'),))
    source.workflow = SimpleNamespace(is_job_source=lambda source: False,
        specialist=lambda source: binding, binding_context=lambda source: source,
        permits_common_action=lambda source, action: action == 'reason' or wait,
        knowledge=SimpleNamespace(instructions='Actual selected tool instructions'),
        launch_instructions=SimpleNamespace(instructions='Actual selected resource instructions'),
        native_event_information=object(), decision_protocol='decision_exchange_v1' if exchange else None)
    context = {'tool_knowledge': {}, 'launch_instruction_library': {}}
    assert private.instructions(source, context) == original.instructions(source, context)
