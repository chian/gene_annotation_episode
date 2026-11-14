"""Private operational endpoint identity with actual saved counterparts and controlled ports."""
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

AXIS=__package__.rsplit('.tests',1)[0]
ROOT=Path(__file__).resolve().parents[1]
HOMES={}
for path in ROOT.rglob('episode.py'):
    if 'tests' in path.parts:continue
    text=path.read_text()
    if not any('class '+name+'(' in text for name in ('ScientificProcessEpisode','ExecutionEpisode','ResourceEpisode','MonitorEpisode')):continue
    module=import_module(AXIS+'.'+str(path.parent.relative_to(ROOT)).replace('/','.')+'.episode')
    cls=next(getattr(module,name) for name in ('ScientificProcessEpisode','ExecutionEpisode','ResourceEpisode','MonitorEpisode') if hasattr(module,name))
    HOMES[path.parent]=cls
CASES=[(str(parent.relative_to(ROOT)),str(child.relative_to(ROOT)),child_cls.roles[0])
    for parent in HOMES for child,child_cls in HOMES.items() if child.parent==parent]

@pytest.fixture(params=CASES)
def edge(request):
    parent,child,role=request.param
    binding=object.__new__(HOMES[ROOT/parent])
    binding.allowed_children=lambda *args:(role,)
    return parent,child,role,binding


def outgoing(edge):
    parent,child,role,binding=edge
    context=SimpleNamespace(role=binding.roles[0],scope={'subject_refs':['target']})
    source=SimpleNamespace(path=(('annotation','root'),(binding.roles[0],'parent')),
        scope=context.scope,episode_id='original-parent')
    selection={'kind':'episode_child','role':role,'scope':context.scope,
        'goal':'Improve the original execution outcome','purpose':'Return original qualified result',
        'assignment':{'original':'assignment'}}
    if role=='monitor':
        selection['assignment']={'version':'monitor_assignment_v1','target_handle':'original-target',
            'requested_fields':['execution_status'],'known_progress_refs':[],'permitted_committed_record_types':[]}
    calls=[]
    target=SimpleNamespace(binding_path=child,required_return_sources=lambda *args:(),
        prepare_assignment=lambda context,role,assignment,scope,key:
            calls.append((context,role,assignment,scope,key)) or {'admitted':'original'})
    schema={'type':'object','properties':{},'required':[],'additionalProperties':False}
    workflow=SimpleNamespace(run_id='original-run',store=SimpleNamespace(validate_scope=lambda scope,**kwargs:scope),
        expanded_contract_form=lambda *args:(schema,{'original':'declaration'}),
        episode_bindings=SimpleNamespace(for_child=lambda *args:target),binding_context=lambda source:context,
        child_initial_report_input=lambda *args:'{}',specialist=lambda source:binding,
        annotation_child_roles=None,services=SimpleNamespace(capabilities=lambda:()),
        launch_instructions=SimpleNamespace(materialize=lambda selected:None))
    return workflow,source,selection,context,target,calls,schema


def test_named_parent_request_uses_actual_child_binding_path_and_original_admission(edge):
    parent,child,role,binding=edge
    workflow,source,selection,context,target,calls,schema=outgoing(edge)
    callback=binding.child_request_preparer_for_binding(role,child)
    assert callback.__module__==AXIS+'.'+parent.replace('/','.')+'.to_child_'+Path(child).name
    result=callback(workflow,source,selection,7)
    assert result=={'scope':selection['scope'],'role':role,'schema':schema,
        'report_declaration':{'original':'declaration'},'initial':{},
        'episode_assignment':{'admitted':'original'},'scientific_process':None,'assignment':None}
    assert calls==[(context,role,selection['assignment'],selection['scope'],'original-run:original-parent:7')]


def test_required_typed_result_is_checked_before_child_admission(edge):
    _,child,role,binding=edge
    workflow,source,selection,_,target,calls,_=outgoing(edge)
    target.required_return_sources=lambda *args:('original_qualified_result',)
    with pytest.raises(import_module(AXIS+'.domain').ContractError,match='child_return_requires_original_qualified_result'):
        binding.child_request_preparer_for_binding(role,child)(workflow,source,selection,7)
    assert calls==[]


def test_same_role_other_binding_cannot_enter_this_named_endpoint(edge):
    _,child,role,binding=edge
    workflow,source,selection,_,target,calls,_=outgoing(edge)
    target.binding_path='different_parent/different_child'
    with pytest.raises(ValueError,match='child_binding_path_conflict'):
        binding.child_request_preparer_for_binding(role,child)(workflow,source,selection,7)
    assert calls==[]


@pytest.mark.parametrize('redelivery',[False,True])
def test_saved_counterpart_dispatch_retains_private_path_and_receipt_identity(edge,tmp_path,monkeypatch,redelivery):
    parent,child,role,binding=edge
    runtime=import_module(AXIS+'.runtime');Store=import_module(AXIS+'.state').Store
    Journal=import_module(AXIS+'.episode_journal').Journal
    ParentRecords=import_module(AXIS+'.episode_return_records').EpisodeReturnRecords
    monkeypatch.setattr(ParentRecords,'recorded_admission_references',lambda *args:None)
    source=SimpleNamespace(path=(('annotation','root'),(binding.roles[0],'parent')),episode_id='parent',scope={})
    receiver=binding.child_report_receiver_for_binding(role,child);calls=[]
    assert receiver.__module__==AXIS+'.'+parent.replace('/','.')+'.from_child_'+Path(child).name
    def choose(actual_role,actual_path):
        calls.append((actual_role,actual_path));assert (actual_role,actual_path)==(role,child)
        return receiver
    binding.child_report_receiver_for_binding=choose
    with Store(tmp_path/'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        source.scope=store.validate_scope()
        journal=Journal(store,'original-run')
        journal.save('runtime_episodes',{'episode_id':'child','path':json.dumps(source.path+((role,'original-child'),)),
            'request':'{}','initial_credit':0,'state':'yielded','completion':None,'archive':None})
        journal.save('runtime_actions',{'episode_id':'parent','decision_index':8,
            'action':json.dumps({'kind':'redeliver_report','delivery_ref':'original-delivery'} if redelivery else
                {'kind':'episode_child','role':role}),'result':None,'credit':None})
        journal.save('runtime_report_attempts',{'parent_episode_id':'parent','decision_index':8,
            'delivery_ref':'original-delivery','child_episode_id':'child','contract':'{}','form':'{}','failure':None})
        receipts=[];progress=[]
        workflow=SimpleNamespace(run_id='original-run',store=store,journal=journal,
            specialist=lambda source:binding,is_job_source=lambda source:False,binding_context=lambda source:source,
            progress_provider=SimpleNamespace(receive_form=lambda *args:progress.append(args),
                _receive_progress=lambda *args:progress.append(args)),
            native_timing_information=None,job_episodes=None,receive_tool_attributions=lambda *args,**kwargs:[],
            receipts=SimpleNamespace(receive=lambda *args,**kwargs:receipts.append((args,kwargs))),
            episode_bindings=SimpleNamespace(received_form_references=lambda *args:['original-qualified-result'],
                for_child=lambda *args:SimpleNamespace(binding_path=child)))
        references=runtime.Workflow._receive_form(workflow,source,{}, {'type':'object','properties':{},'required':[],'additionalProperties':False},8,redelivery=redelivery)
        assert references==['original-qualified-result'] and calls==[(role,child)]
        assert len(progress)==1
        if role=='monitor':
            schema={'type':'object','properties':{},'required':[],'additionalProperties':False}
            signature=import_module(AXIS+'.method_loop.durable').content_digest({
                'form':{},'schema':schema,'scope':import_module(AXIS+'.communication').plain(source.scope)})
            assert progress==[('parent',[],signature,'original-run:parent:8:typed_form')]
        assert receipts==[(('parent',['original-qualified-result']),
            {'kind':'report_redelivery' if redelivery else 'child_form','source_index':8})]


def test_original_hpc_handoff_requirement_precedes_native_assignment(edge):
    _,child,role,binding=edge
    if role not in {'launch','launch_hpc'}:
        pytest.skip('Original HPC handoff condition cannot apply to this fixed child role')
    workflow,source,selection,_,_,calls,_=outgoing(edge)
    source.path=(('hpc','original-planner'),) if role=='launch' else (
        ('hpc','original-planner'),('launch','original-parent'))
    with pytest.raises(import_module(AXIS+'.domain').ContractError,
            match='hpc_launch_requires_original_handoff_fact_in_return_form'):
        binding.child_request_preparer_for_binding(role,child)(workflow,source,selection,7)
    assert calls==[]
