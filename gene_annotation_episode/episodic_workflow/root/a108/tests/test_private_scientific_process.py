"""Existing A108 scientific commissioning bindings and selected-task connection."""
import asyncio
from contextlib import nullcontext
from types import SimpleNamespace
import pytest

from gene_annotation_episode.episodic_workflow.root.a108 import runtime
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.episode import ScientificProcessEpisode


def scientific_binding():
    library=SimpleNamespace(as_record=lambda:{'fixture':'original-scientific-library'},headers=lambda:[])
    tools=SimpleNamespace(as_record=lambda:{'fixture':'original-tool-library'})
    return ScientificProcessEpisode(SimpleNamespace(),library=library,tool_library=tools,
        child_roles=('scientific_process','literature'))


def test_declared_scientific_children_and_configuration():
    binding=scientific_binding()
    assert binding.child_roles('scientific_process')==('scientific_process','literature')
    assert binding.as_record()['configuration']=={'library':{'fixture':'original-scientific-library'},
        'tool_library':{'fixture':'original-tool-library'},'child_roles':['scientific_process','literature']}
    with pytest.raises(runtime.ContractError,match='scientific_process_role_not_bound'):
        binding.child_roles('literature')


def test_scientific_task_validates_original_assignment_before_operation():
    binding=scientific_binding()
    source=object.__new__(getattr(binding,'decision_source_type',runtime.DecisionSource))
    source.episode_id='scientific';source.path=(('scientific_process','original'),);source.scope={}
    source.last_outcome=source.last_outcome_index=source.feedback=None
    source.checkpoint=lambda:None
    saved={};seen=[]
    async def operation(*args,**kwargs):
        seen.append(('execute',kwargs['operation_key']))
        return {'status':'unavailable','record_refs':[],'changed_record_refs':[],'result':None}
    async def scores(source,index,result):return result
    source.workflow=SimpleNamespace(run_id='run',execution_binding=None,wait_inputs_version=None,
        completed_action_inputs_version=None,binding_context=lambda source:'original-context',
        scientific_process_binding=SimpleNamespace(validate_execution_context=lambda context:seen.append(('validated',context))),
        journal=SimpleNamespace(row=lambda table,episode,index:saved.get(index),
            save=lambda table,row:saved.__setitem__(row['decision_index'],dict(row)),measure=lambda *args:nullcontext()),
        execute=operation,receive_native_outcome=lambda *args:None,receive_outcome=lambda *args:None,
        automatic_score_updates=scores,source_credit_view=lambda source:{'credit':0},
        controller_value=lambda source,index,credit:{'credit':credit})
    selection={'kind':'tool','tool':'source.read','arguments':{}}
    assert asyncio.run(source.execute(selection,2))=={'credit':0}
    assert asyncio.run(source.execute(selection,2))=={'credit':0}
    assert seen==[('validated','original-context'),('execute','run:scientific:2')]
