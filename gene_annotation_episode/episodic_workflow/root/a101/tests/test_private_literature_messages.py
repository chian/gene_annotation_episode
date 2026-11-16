"""Named A101/A106 child exchanges with real saved identity and controlled child/receipt ports."""
from importlib import import_module
import json
from types import SimpleNamespace

import pytest
from .test_literature_private_boundaries import PACKAGE as AXIS, HOMES
HOMES = [home.replace('/', '.') for home in HOMES]

EDGES={'literature':{'literature_strategy':'evidence_search_strategy_improvement'},
 'literature_strategy':{'literature_search':'source_relevance_assessment'},
 'literature_search':{'literature_page':'source_evidence_examination'},
 'literature_page':{'literature_table':'table_evidence_extraction','literature_ordered':'source_coverage_improvement','literature_targeted':'passage_evidence_extraction'}}
CASES=[]
for home in HOMES:
    cls=import_module(AXIS+'.'+home+'.episode').LiteratureEpisode
    CASES.extend((home,role,name) for role,name in EDGES.get(cls.roles[0],{}).items())

@pytest.fixture(params=CASES)
def edge(request):
    home,role,name=request.param
    binding=import_module(AXIS+'.'+home+'.episode').LiteratureEpisode(SimpleNamespace())
    return home,role,name,binding


def outgoing_fixture(edge):
    home,role,name,binding=edge
    parent=SimpleNamespace(role=binding.roles[0],scope={'subject_refs':['target']})
    source=SimpleNamespace(path=(('annotation','root'),(binding.roles[0],'parent')),scope=parent.scope,episode_id='original-parent')
    selected={'kind':'episode_child','role':role,'scope':{'subject_refs':['target']},
        'goal':'Read actual source conditions','purpose':'Return qualified context',
        'assignment':{'original':'selected-assignment'}}
    calls=[]
    child=SimpleNamespace(required_return_sources=lambda context,role:(),
        prepare_assignment=lambda context,child_role,assignment,scope,key:
            calls.append((context,child_role,assignment,scope,key)) or {'admitted':'original'})
    schema={'type':'object','properties':{},'required':[],'additionalProperties':False}
    workflow=SimpleNamespace(run_id='run-original',store=SimpleNamespace(validate_scope=lambda scope,**kwargs:scope),
        expanded_contract_form=lambda *args:(schema,{'original':'contract-declaration'}),
        episode_bindings=SimpleNamespace(for_child=lambda path,role:child),binding_context=lambda source:parent,
        child_initial_report_input=lambda *args:'{}',specialist=lambda source:binding,
        annotation_child_roles=None,services=SimpleNamespace(capabilities=lambda:()),
        launch_instructions=SimpleNamespace(materialize=lambda selected:None))
    return workflow,source,selected,parent,child,calls,schema


def test_parent_owns_original_scoped_request_and_child_admission(edge):
    home,role,name,binding=edge
    workflow,source,selection,parent,child,calls,schema=outgoing_fixture(edge)
    handler=binding.child_request_preparer(role)
    result=handler(workflow,source,selection,6)
    assert result['scope']==selection['scope'] and result['schema'] is schema
    assert result['role']==role and result['initial']=={}
    assert result['report_declaration']=={'original':'contract-declaration'}
    assert result['episode_assignment']=={'admitted':'original'}
    assert calls==[(parent,role,selection['assignment'],selection['scope'],'run-original:original-parent:6')]


def test_missing_required_typed_result_is_rejected_before_child_admission(edge):
    *_,binding=edge
    workflow,source,selection,parent,child,calls,schema=outgoing_fixture(edge)
    child.required_return_sources=lambda *args:('actual_context_sheets',)
    with pytest.raises(import_module(AXIS+'.domain').ContractError,match='child_return_requires_actual_context_sheets'):
        binding.child_request_preparer(selection['role'])(workflow,source,selection,6)
    assert calls==[]


@pytest.mark.parametrize('redelivery',[False,True])
def test_receipt_dispatch_uses_saved_original_child_counterpart(edge,tmp_path,monkeypatch,redelivery):
    home,role,name,binding=edge
    runtime=import_module(AXIS+'.runtime');Store=import_module(AXIS+'.state').Store
    Journal=import_module(AXIS+'.episode_journal').Journal
    ParentRecords=import_module(AXIS+'.episode_return_records').EpisodeReturnRecords
    monkeypatch.setattr(ParentRecords,'recorded_admission_references',lambda *args:None)
    source=SimpleNamespace(path=(('annotation','root'),(binding.roles[0],'parent')),episode_id='parent',scope={})
    called=[]
    receiver=binding.child_report_receiver(role)
    def selected_receiver(actual_role):
        assert actual_role==role
        called.append(actual_role)
        return receiver
    binding.child_report_receiver=selected_receiver
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        source.scope=store.validate_scope()
        journal=Journal(store,'original-run')
        child_path=source.path+((role,'original-child'),)
        journal.save('runtime_episodes',{'episode_id':'child','path':json.dumps(child_path),
            'request':'{}','initial_credit':0,'state':'yielded','completion':None,'archive':None})
        journal.save('runtime_actions',{'episode_id':'parent','decision_index':8,
            'action':json.dumps({'kind':'redeliver_report','delivery_ref':'original-delivery'} if redelivery else
                {'kind':'episode_child','role':role}), 'result':None,'credit':None})
        journal.save('runtime_report_attempts',{'parent_episode_id':'parent','decision_index':8,
            'delivery_ref':'original-delivery','child_episode_id':'child','contract':'{}','form':'{}','failure':None})
        receipts=[];progress=[]
        workflow=SimpleNamespace(run_id='original-run',store=store,journal=journal,
            specialist=lambda source:binding,is_job_source=lambda source:False,binding_context=lambda source:source,
            progress_provider=SimpleNamespace(receive_form=lambda *args:progress.append(args)),
            native_timing_information=None,job_episodes=None,receive_tool_attributions=lambda *args,**kwargs:[],
            receipts=SimpleNamespace(receive=lambda *args,**kwargs:receipts.append((args,kwargs))),
            episode_bindings=SimpleNamespace(received_form_references=lambda *args:['typed-finding','saved-sheet']))
        references=runtime.Workflow._receive_form(workflow,source,{}, {'type':'object','properties':{},'required':[],'additionalProperties':False},8,redelivery=redelivery)
        assert references==['typed-finding','saved-sheet'] and called==[role]
        assert len(progress)==1
        assert receipts==[(('parent',['typed-finding','saved-sheet']),
            {'kind':'report_redelivery' if redelivery else 'child_form','source_index':8})]
