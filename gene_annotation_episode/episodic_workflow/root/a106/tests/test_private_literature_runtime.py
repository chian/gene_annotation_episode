"""Runtime selection of every parent's private literature task and instruction composition."""
from contextlib import nullcontext
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

PACKAGE='gene_annotation_episode.episodic_workflow.root.a106'
ROOT=Path(__file__).resolve().parents[1]
HOMES=sorted(str(p.parent.relative_to(ROOT)) for p in ROOT.rglob('episode.py')
    if 'published_evidence_assessment' in p.parts and 'tests' not in p.parts and 'class LiteratureEpisode(' in p.read_text())
runtime=importlib.import_module(PACKAGE+'.runtime')


@pytest.fixture(params=HOMES)
def binding(request):
    return importlib.import_module(PACKAGE+'.'+request.param.replace('/','.')+'.episode').LiteratureEpisode(SimpleNamespace())


def test_original_runtime_selects_parent_private_literature_task(binding,monkeypatch):
    Registry=importlib.import_module(PACKAGE+'.episode_bindings').EpisodeBindingRegistry
    role,=binding.roles
    monkeypatch.setattr(runtime.Episode,'identity',lambda *args,**kwargs:SimpleNamespace(episode_id='literature-test'))
    monkeypatch.setattr(runtime,'FeedbackEpisode',lambda grain,key,source,*args,**kwargs:source)
    workflow=SimpleNamespace(context=object(),grains={role:object()},inprocess_completion_order=None,
        receipts=None,scientific_process_binding=None,episode_bindings=Registry((binding,)),
        contract_information_profile=lambda source:None,binding_context=lambda source:source,
        specialist=lambda source:binding,journal=SimpleNamespace(row=lambda *args:None,save=lambda *args:None),
        run_id='run',store=SimpleNamespace(transaction=nullcontext,db=SimpleNamespace(execute=lambda *args:None)),
        source_credit_view=lambda source:{'credit':0},expose_assigned_job=lambda source:None,
        receive_tool_attributions=lambda *args,**kwargs:None,archive=SimpleNamespace(store=lambda value:value))
    task=runtime.Workflow.build(workflow,role,'child','Resolve original source question',{})
    assert type(task) is binding.decision_source_type
    assert not isinstance(task,runtime.DecisionSource)
    assert type(task).__module__==binding.__class__.__module__.rsplit('.',1)[0]+'.task'
    assert task.path==((role,'child'),)


@pytest.mark.parametrize('exchange',[False,True])
def test_private_prompt_uses_exact_original_axis_and_role_guidance(binding,exchange):
    private=importlib.import_module(binding.__class__.__module__.rsplit('.',1)[0]+'.task_instructions')
    original=importlib.import_module(PACKAGE+'.runtime_prompt')
    source=SimpleNamespace(path=((binding.roles[0],'child'),))
    context=SimpleNamespace(role=binding.roles[0],scope={},assignment={})
    source.workflow=SimpleNamespace(is_job_source=lambda source:False,
        specialist=lambda source:binding,binding_context=lambda source:context,
        permits_common_action=lambda source,action:action in binding.permitted_common_actions(context),
        knowledge=SimpleNamespace(instructions='Selected source guidance'),
        launch_instructions=SimpleNamespace(instructions='Selected resource guidance'),
        native_event_information=None,decision_protocol='decision_exchange_v1' if exchange else None)
    actual_context={'tool_knowledge':{},'launch_instruction_library':{}}
    assert private.instructions(source,actual_context)==original.instructions(source,actual_context)
