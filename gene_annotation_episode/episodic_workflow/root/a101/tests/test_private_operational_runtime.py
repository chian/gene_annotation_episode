"""The original runtime selects each actual operational private task type."""
from contextlib import nullcontext
import importlib
from types import SimpleNamespace

import pytest

from .test_operational_task_connections import PACKAGE, HOMES
runtime=importlib.import_module(PACKAGE+'.runtime')


@pytest.mark.parametrize('home,name',HOMES)
def test_original_build_selects_actual_operational_task(home,name,monkeypatch):
    Binding=getattr(importlib.import_module(PACKAGE+'.'+home.replace('/','.')+'.episode'),name)
    binding=object.__new__(Binding)
    # This test isolates runtime selection; real constructors and descriptors
    # have independent Store-backed coverage in test_actual_private_registry.
    binding.as_record=lambda:{'binding_id':binding.binding_path,'version':'controlled-build'}
    binding.initialize=lambda context:None
    Registry=importlib.import_module(PACKAGE+'.episode_bindings').EpisodeBindingRegistry
    legacy=name=='HomologyEpisode'
    registry=Registry(()) if legacy else Registry((binding,))
    role,=binding.roles
    monkeypatch.setattr(runtime.Episode,'identity',lambda *args,**kwargs:SimpleNamespace(episode_id='operational-test'))
    monkeypatch.setattr(runtime,'FeedbackEpisode',lambda grain,key,source,*args,**kwargs:source)
    workflow=SimpleNamespace(context=object(),grains={role:object()},inprocess_completion_order=None,
        receipts=None,scientific_process_binding=None,episode_bindings=registry,
        job_episodes=binding if legacy else None,
        contract_information_profile=lambda source:None,binding_context=lambda source:source,
        specialist=lambda source:None if legacy else binding,
        journal=SimpleNamespace(row=lambda *args:None,save=lambda *args:None),
        run_id='run',store=SimpleNamespace(transaction=nullcontext,db=SimpleNamespace(execute=lambda *args:None)),
        source_credit_view=lambda source:{'credit':0},expose_assigned_job=lambda source:None,
        receive_tool_attributions=lambda *args,**kwargs:None,archive=SimpleNamespace(store=lambda value:value))
    task=runtime.Workflow.build(workflow,role,'original','Resolve original operational assignment',{})
    assert type(task) is binding.decision_source_type
    assert not isinstance(task,runtime.DecisionSource)
    assert type(task).__module__==Binding.__module__.rsplit('.',1)[0]+'.task'
    assert task.path==((role,'original'),)
