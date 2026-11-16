"""Original root-credit context selects compatibility at either saved path."""
from copy import deepcopy

import pytest

from .test_scientific_task import make_task


def test_saved_model_request_with_zero_exchanges_retains_root_mode_at_provider(tmp_path):
    """Actual SQLite model/exchange rows; controlled provider, no selected unit."""
    import asyncio
    import json
    from types import SimpleNamespace
    from ...decision_exchanges import DecisionExchanges
    from ...decision_context import PROTOCOL, instructional_model_context, model_snapshot, state_frame
    from ...episode_journal import Journal
    from ...state import Store

    task,_,_,_=make_task({})
    task.path=(('annotation','saved-parent'),*task.path)
    task.calls=0
    task._presented_conversation_key=None
    task._model_snapshot=None
    observed=[]
    schema={'type':'object','properties':{'selection':{'type':'object','properties':{'kind':{'const':'reason'}},
        'required':['kind'],'additionalProperties':False},'report_update':{'type':'null'}},
        'required':['selection','report_update'],'additionalProperties':False}
    saved_context={'current_credit':{'mode':'annotation_axis_credit','root_score':0.25},
        'controller':{'arms':[{'original':'retained-arm'}]},'visible_record_refs':[],
        'original_scientific_context':{'qualification':'unresolved','native_value':3.5}}
    saved={'context':deepcopy(saved_context),'schema':deepcopy(schema),'decision_protocol':PROTOCOL}
    response={'response':{'response_type':'select_action','selection':{'kind':'reason'},'report_update':None}}
    async def complete(episode,purpose,instructions,context,output_schema):
        observed.append(deepcopy({'episode':episode,'purpose':purpose,'instructions':instructions,
            'context':context,'output_schema':output_schema}))
        return deepcopy(response)
    def forbidden(*args,**kwargs):pytest.fail('Saved call must not reconstruct fresh inputs or execute work')
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='ATGC',molecule='DNA')
        task.scope=store.validate_scope()
        journal=Journal(store,'saved-model-boundary')
        exchanges=DecisionExchanges(journal)
        journal.save('runtime_model_calls',{'episode_id':task.episode_id,'call_index':0,
            'purpose':'decision','request':json.dumps(saved),'response':None})
        assert exchanges.rows(task.episode_id,0)==[]
        original_request=journal.row('runtime_model_calls',task.episode_id,0)['request']
        records=[tuple(row) for row in store.db.execute('SELECT * FROM records ORDER BY rowid')]
        workflow=task.workflow
        workflow.journal=journal;workflow.store=store;workflow.decision_exchanges=exchanges
        workflow.decision_protocol=PROTOCOL;workflow.controller_binding=None
        workflow.contract_information_profile=lambda source:None
        workflow.available_child_roles=lambda source:()
        workflow.scientific_library_available=lambda source:False
        workflow.provider=SimpleNamespace(complete=complete)
        workflow.services=SimpleNamespace(decision_exchange_instructions=lambda:'ORIGINAL EXCHANGE INSTRUCTIONS')
        workflow.receipts=None
        task.instructions=lambda context:'ORIGINAL HEAD INSTRUCTIONS'
        task.decision_inputs=forbidden
        workflow.execute=forbidden
        value=asyncio.run(task.call({'discarded':'fresh argument'},{'discarded':'fresh schema'}))
        expected_table={'version':'annotation_axis_yield_table_v1','rows':saved_context['controller']['arms'],
            'forecast_unit':'another_whole_axis_invocation','source':'actual_root_controller'}
        expected_snapshot=instructional_model_context(model_snapshot(saved_context,expected_table))
        assert len(observed)==1
        assert observed[0]['instructions']=='ORIGINAL HEAD INSTRUCTIONS\nORIGINAL EXCHANGE INSTRUCTIONS'
        assert observed[0]['context']==instructional_model_context(state_frame(expected_snapshot))
        assert observed[0]['purpose']=='REASONING' and observed[0]['episode']==task.episode_id
        retained,=exchanges.rows(task.episode_id,0)
        assert retained['request']['restoration']=={'snapshot':expected_snapshot,'pending_public_exchanges':[]}
        assert retained['request']['output_schema']==observed[0]['output_schema']
        assert retained['response']==response
        assert value[2]==saved_context and value[3]==schema
        assert json.loads(journal.row('runtime_model_calls',task.episode_id,0)['request'])==json.loads(original_request)
        assert [tuple(row) for row in store.db.execute('SELECT * FROM records ORDER BY rowid')]==records
        assert journal.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==0
        assert journal.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==0
