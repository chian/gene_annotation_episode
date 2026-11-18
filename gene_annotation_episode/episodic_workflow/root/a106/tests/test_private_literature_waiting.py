"""A106 literature waiting preserves successful credit reuse and failed-action propagation."""
import asyncio
from contextlib import nullcontext
import json
from types import SimpleNamespace

import pytest
from gene_annotation_episode.episodic_workflow.root.a106 import runtime
from importlib import import_module
from .test_literature_private_boundaries import PACKAGE, HOMES


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('unavailable',[False,True])
def test_literature_wait_preserves_original_outcome_without_new_credit(home,unavailable):
    binding=import_module(PACKAGE+'.'+home.replace('/','.')+'.episode').LiteratureEpisode(SimpleNamespace());source=object.__new__(getattr(binding,'decision_source_type',runtime.DecisionSource))
    source.path=((binding.roles[0],'original'),);source.episode_id='scientific';source.scope={}
    source.last_outcome=source.last_outcome_index=source.feedback=None;source.checkpoint=lambda:None
    rows={};calls=[];received=[]
    async def wait(source,condition,index):
        calls.append((condition,index))
        if unavailable:raise runtime.EventTargetError('wait_target_unavailable',affected_refs=['original-handle'])
        return {'status':'completed','record_refs':[],'changed_record_refs':[],'result':{'ready':False}}
    source.workflow=SimpleNamespace(run_id='run',execution_binding=None,pending_work=lambda source: [],
        binding_context=lambda source:'original-context',
        perturbation_evidence_binding=SimpleNamespace(validate_execution_context=lambda context:None),
        journal=SimpleNamespace(row=lambda table,episode,index:rows.get(index),
            save=lambda table,row:rows.__setitem__(row['decision_index'],dict(row)),measure=lambda *args:nullcontext()),
        perform_selected_wait=wait,receive_native_outcome=lambda *args:None,
        receive_outcome=lambda source,selection,result,index:received.append((index,result['status'])),
        automatic_score_updates=lambda *args:pytest.fail('waiting must not trigger new scientific scoring'),
        source_credit_view=lambda *args:pytest.fail('waiting must reuse actual prior observed credit'),
        last_observed_credit=lambda source:3.,controller_value=lambda source,index,credit:credit)
    selection={'kind':'wait','condition':{'original':'condition'}}
    if unavailable:
        for _ in range(2):
            with pytest.raises(runtime.ActionFailure) as failure:
                asyncio.run(source.execute(selection,5))
            assert failure.value.feedback['code']=='wait_target_unavailable'
    else:
        assert asyncio.run(source.execute(selection,5))==3.
        assert asyncio.run(source.execute(selection,5))==3.
    assert calls==[(selection['condition'],5)]
    assert received==([] if unavailable else [(5,'completed')])
    saved=rows[5];assert json.loads(saved['action'])==selection
    assert saved['credit']==(None if unavailable else 3.)
    if unavailable:assert json.loads(saved['result'])['feedback']['code']=='wait_target_unavailable'
