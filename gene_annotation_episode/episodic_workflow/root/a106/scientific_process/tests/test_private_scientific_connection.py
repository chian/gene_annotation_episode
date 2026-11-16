"""Private scientific binding selection and prompt composition connections."""
from contextlib import nullcontext
import importlib
from types import SimpleNamespace

import pytest

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a106'
runtime = importlib.import_module(PACKAGE + '.runtime')
Binding = importlib.import_module(PACKAGE + '.scientific_process.episode').ScientificProcessEpisode
Task = importlib.import_module(PACKAGE + '.scientific_process.task').ScientificInvestigationTask




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
