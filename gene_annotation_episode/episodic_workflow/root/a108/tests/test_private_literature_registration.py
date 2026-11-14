"""Actual registry and Workflow.build selection; episode driver/provider ports are controlled."""
from contextlib import nullcontext
from importlib import import_module
from types import SimpleNamespace

import pytest
from .test_private_literature_boundaries import AXIS,HOMES

@pytest.fixture(params=HOMES)
def registered(request):
    science=request.param.startswith('scientific_process.')
    classes=[import_module(AXIS+'.'+home+'.episode').LiteratureEpisode for home in HOMES
        if home.startswith('scientific_process.')==science]
    bindings=[cls(SimpleNamespace()) for cls in classes]
    binding=next(b for b in bindings if b.__module__==AXIS+'.'+request.param+'.episode')
    registry=import_module(AXIS+'.episode_bindings').EpisodeBindingRegistry(bindings)
    # Both families also support the existing explicit standalone invocation.
    # Its descendants still follow this family's actual commissioning edges.
    relative=request.param.removeprefix('scientific_process.')
    by_name={b.binding_path.split('/')[-1]:b.roles[0] for b in bindings}
    path=tuple((by_name[name],'invocation-'+str(index)) for index,name in enumerate(relative.split('.')))
    return binding,registry,path


def test_actual_registry_and_build_select_private_task_and_preserve_descriptor(registered,monkeypatch):
    binding,registry,path=registered
    runtime=import_module(AXIS+'.runtime')
    assert registry.for_path(path) is binding
    descriptor=binding.as_record()
    assert descriptor['binding_id']==binding.binding_path
    assert len(descriptor['implementation_sha256'])==64
    assert descriptor['configuration']=={'outcome_page_size':8}
    identity=SimpleNamespace(episode_id='original-source')
    monkeypatch.setattr(runtime.Episode,'identity',lambda *args,**kwargs:identity)
    monkeypatch.setattr(runtime,'FeedbackEpisode',lambda grain,key,source,*args,**kwargs:source)
    workflow=SimpleNamespace(context=object(),grains={binding.roles[0]:object()},
        inprocess_completion_order=None,receipts=None,scientific_process_binding=None,
        episode_bindings=registry,contract_information_profile=lambda source:None,
        specialist=lambda source:registry.for_path(source.path),
        journal=SimpleNamespace(row=lambda *args:None,save=lambda *args:None),run_id='registered-task',
        store=SimpleNamespace(transaction=nullcontext,db=SimpleNamespace(execute=lambda *args:None)),
        source_credit_view=lambda source:{'credit':0},expose_assigned_job=lambda source:None,
        archive=SimpleNamespace(store=lambda value:value))
    source=runtime.Workflow.build(workflow,binding.roles[0],path[-1][1],
        'Investigate original contextual question',{},parent_path=path[:-1])
    assert type(source) is binding.decision_source_type
    assert runtime.DecisionSource not in type(source).__mro__
    assert source.path==path and source.report_values=={}
    assert source.episode_id=='original-source'


def test_duplicate_role_families_are_distinct_and_require_private_identity():
    bindings=[import_module(AXIS+'.'+home+'.episode').LiteratureEpisode(SimpleNamespace()) for home in HOMES]
    registry=import_module(AXIS+'.episode_bindings').EpisodeBindingRegistry(bindings)
    for binding in bindings:
        assert registry.for_binding_path(binding.binding_path) is binding
        with pytest.raises(LookupError,match='episode_role_requires_parent'):
            registry.for_role(binding.roles[0])
