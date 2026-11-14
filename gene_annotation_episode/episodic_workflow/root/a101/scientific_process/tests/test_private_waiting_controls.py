"""Original selected head waits retain saved identity and failure semantics."""
import asyncio
import json
import pytest
from gene_annotation_episode.episodic_workflow.root.a101.scientific_process.tests.test_scientific_task import make_task,runtime

@pytest.mark.parametrize('unavailable',[False,True])
def test_original_wait_success_or_unavailable_replays_without_new_scientific_credit(unavailable):
    task,saved,tool_calls,events=make_task({})
    calls=[]
    async def wait(source,condition,index):
        calls.append((condition,index))
        if unavailable:raise runtime.EventTargetError('wait_target_unavailable',affected_refs=['original-target'])
        return {'status':'completed','record_refs':[],'changed_record_refs':[],'result':{'ready':False}}
    task.workflow.perform_selected_wait=wait
    task.workflow.last_observed_credit=lambda source:2.5
    task.workflow.automatic_score_updates=lambda *args:pytest.fail('selected wait cannot create scientific grading')
    task.workflow.source_credit_view=lambda *args:pytest.fail('selected wait must retain prior observed credit')
    selection={'kind':'wait','condition':{'original':'condition'}}
    for _ in range(2):
        if unavailable:
            with pytest.raises(runtime.ActionFailure) as failure:asyncio.run(task.execute(selection,5))
            assert failure.value.feedback['code']=='wait_target_unavailable'
        else:assert asyncio.run(task.execute(selection,5))=={'index':5,'credit':2.5}
    assert calls==[(selection['condition'],5)] and tool_calls==[]
    assert events==([] if unavailable else ['received'])
    assert json.loads(saved[5]['action'])==selection
    assert saved[5]['credit']==(None if unavailable else 2.5)
    assert json.loads(saved[5]['result'])['status']==('failed' if unavailable else 'completed')
