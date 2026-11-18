"""Private scientific binding selection and prompt composition connections."""
from contextlib import nullcontext
import importlib
from types import SimpleNamespace

import pytest

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a101'
runtime = importlib.import_module(PACKAGE + '.runtime')
Binding = importlib.import_module(PACKAGE + '.sequence_homology_evidence.episode').SequenceHomologyEvidenceEpisode
Task = importlib.import_module(PACKAGE + '.sequence_homology_evidence.task').ScientificInvestigationTask




def test_original_runtime_constructs_declared_private_scientific_task(monkeypatch):
    Registry = importlib.import_module(PACKAGE + '.episode_bindings').EpisodeBindingRegistry
    binding = Binding(SimpleNamespace(), library=SimpleNamespace(as_record=lambda: {'version': 'fixture'}, headers=lambda: []), tool_library=SimpleNamespace(as_record=lambda: {'version': 'fixture'}), child_roles=('sequence_homology_evidence',))
    binding.restore_closed_process = lambda context: None
    binding.validate_context = lambda context: None
    monkeypatch.setattr(runtime.Episode, 'identity', lambda *args, **kwargs: SimpleNamespace(episode_id='science'))
    monkeypatch.setattr(runtime, 'FeedbackEpisode', lambda grain, key, source, *args, **kwargs: source)
    workflow = SimpleNamespace(context=object(), grains={'sequence_homology_evidence': object()},
        inprocess_completion_order=None, receipts=None, sequence_homology_evidence_binding=binding,
        episode_bindings=Registry((binding,)), contract_information_profile=lambda source: None,
        binding_context=lambda source: source, specialist=lambda source: binding,
        journal=SimpleNamespace(row=lambda *args: None, save=lambda *args: None),
        run_id='run', store=SimpleNamespace(transaction=nullcontext, db=SimpleNamespace(execute=lambda *args: None)),
        source_credit_view=lambda source: {'credit': 0}, expose_assigned_job=lambda source: None,
        receive_tool_attributions=lambda *args, **kwargs: None, archive=SimpleNamespace(store=lambda value: value))
    task = runtime.Workflow.build(workflow, 'sequence_homology_evidence', 'science', 'Resolve qualified scientific findings', {})
    assert type(task) is Task
    assert task.path == (('sequence_homology_evidence', 'science'),)


@pytest.mark.parametrize('replace_default', [False, True])
@pytest.mark.parametrize('exchange', [False, True])
@pytest.mark.parametrize('wait', [False, True])
def test_private_instruction_composer_preserves_actual_scientific_guidance(replace_default, exchange, wait):
    private = importlib.import_module(PACKAGE + '.sequence_homology_evidence.task_instructions')
    original = importlib.import_module(PACKAGE + '.runtime_prompt')
    binding = SimpleNamespace(instructions=lambda context: 'Actual selected scientific goal',
        replaces_default_instructions=replace_default)
    source = SimpleNamespace(path=(('sequence_homology_evidence', 'science'),))
    source.workflow = SimpleNamespace(is_job_source=lambda source: False,
        specialist=lambda source: binding, binding_context=lambda source: source,
        permits_common_action=lambda source, action: action == 'reason' or wait,
        knowledge=SimpleNamespace(instructions='Actual selected tool instructions'),
        launch_instructions=SimpleNamespace(instructions='Actual selected resource instructions'),
        native_event_information=object(), decision_protocol='decision_exchange_v1' if exchange else None)
    context = {'tool_knowledge': {}, 'launch_instruction_library': {}}
    assert private.instructions(source, context) == original.instructions(source, context)
