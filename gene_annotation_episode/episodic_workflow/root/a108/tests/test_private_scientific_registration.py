"""Actual Workflow.build selects the scientific head's registered task factory."""
from contextlib import nullcontext
from types import SimpleNamespace

from gene_annotation_episode.episodic_workflow.root.a108 import runtime
from gene_annotation_episode.episodic_workflow.root.a108.episode_bindings import EpisodeBindingRegistry
from .test_private_scientific_process import scientific_binding


def test_actual_build_uses_declared_scientific_task(monkeypatch):
    binding=scientific_binding();registry=EpisodeBindingRegistry([binding]);validated=[]
    binding.restore_closed_process=lambda context:None
    binding.validate_context=lambda context:validated.append(context)
    monkeypatch.setattr(runtime.Episode,'identity',lambda *args,**kwargs:SimpleNamespace(episode_id='original-head'))
    monkeypatch.setattr(runtime,'FeedbackEpisode',lambda grain,key,source,*args,**kwargs:source)
    workflow=SimpleNamespace(context=object(),grains={'scientific_process':object()},
        inprocess_completion_order=None,receipts=None,scientific_process_binding=binding,
        episode_bindings=registry,contract_information_profile=lambda source:None,
        specialist=lambda source:registry.for_path(source.path),
        binding_context=lambda source:SimpleNamespace(role='scientific_process',path=source.path,request=source.request),
        journal=SimpleNamespace(row=lambda *args:None,save=lambda *args:None),run_id='scientific-construction',
        store=SimpleNamespace(transaction=nullcontext,db=SimpleNamespace(execute=lambda *args:None)),
        source_credit_view=lambda source:{'credit':0},expose_assigned_job=lambda source:None,
        archive=SimpleNamespace(store=lambda value:value))
    source=runtime.Workflow.build(workflow,'scientific_process','original',
        'Investigate original contextual findings',{})
    expected=getattr(binding,'decision_source_type',runtime.DecisionSource)
    assert type(source) is expected
    if hasattr(binding,'decision_source_type'):
        assert expected.__module__.endswith('.scientific_process.task')
        assert runtime.DecisionSource not in expected.__mro__
    assert source.path==( ('scientific_process','original'), )
    assert source.episode_id=='original-head'
    assert len(validated)==1 and validated[0].request is source.request
