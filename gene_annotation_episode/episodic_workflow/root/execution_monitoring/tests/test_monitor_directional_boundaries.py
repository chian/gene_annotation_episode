"""Monitor outgoing/admission callbacks preserve current original exchange bodies.

Actual private callbacks and typed contract are used. Parent registry/transport
ports are controlled; Main's shared hook integration is separately validated.
"""
from __future__ import annotations
import ast
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT='gene_annotation_episode.episodic_workflow.root'
HOMES=tuple(prefix+home for prefix in ('','legacy_annotation/','scientific_process/')
    for home in ('execution_monitoring','hpc_coordination/execution_monitoring',
                 'hpc_coordination/hpc_allocation_execution/execution_monitoring'))
SOURCE_SHA='38357b6d866f973f2b8d0f68163f6a3b13a05e1f0f947cd4adda960af0d27fca'
SCHEMA={'type':'object','properties':{'qualified':{'type':'boolean'}},
        'required':['qualified'],'additionalProperties':False}


def original_callbacks():
    path=Path(__file__).with_name('fixtures')/'original_boundary/action_execution.py.source'
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
    cls=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='ActionExecution')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='selected')
    start=next(i for i,n in enumerate(method.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Tuple)
               and [getattr(t,'id',None) for t in n.targets[0].elts]==['schema','report_declaration'])
    end=next(i for i,n in enumerate(method.body) if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=='assignment' for t in n.targets))
    request=ast.parse('def prepare_request(workflow, source, selection, index, scope, role, selected_owner): pass').body[0]
    request.body=ast.parse('episode_assignment=None\nscientific_process=None').body+deepcopy(method.body[start:end+1])
    request.body+=ast.parse('return schema, report_declaration, initial, episode_assignment, scientific_process, assignment').body
    admission=deepcopy(next(n for n in method.body if isinstance(n,ast.FunctionDef) and n.name=='admitted_report'))
    admission.name='admit_return'
    admission.args=ast.parse('def admit_return(workflow, source, child, index, schema, contract, result, request): pass').body[0].args
    class Rename(ast.NodeTransformer):
        def visit_Name(self,node):
            return ast.copy_location(ast.Name(id='workflow',ctx=node.ctx),node) if node.id=='self' else node
    nodes=Rename().visit(ast.Module(body=[request,admission],type_ignores=[]))
    communication=importlib.import_module(ROOT+'.communication')
    values=importlib.import_module(ROOT+'.task_values')
    namespace=dict(globals(),__package__=ROOT,
        ContractError=importlib.import_module('gene_annotation_episode.domain').ContractError,
        parse_json_object=importlib.import_module(ROOT+'.boundary_validation').parse_json_object,
        interpretation_schema=communication.interpretation_schema,validate_form=communication.validate_form,
        ReportBoundaryError=communication.ReportBoundaryError,
        EPISODE_BRANCH_LIFECYCLE=importlib.import_module(ROOT+'.workflow_values').EPISODE_BRANCH_LIFECYCLE,
        ReportDeliveryError=importlib.import_module(ROOT+'.method_loop.episode').ReportDeliveryError,
        Record=values.Record,_digest=values._digest,_json=values._json)
    exec(compile(ast.fix_missing_locations(nodes),str(path),'exec'),namespace)
    return namespace['prepare_request'],namespace['admit_return']


def monitor_assignment(target):
    return {'version':'monitor_assignment_v1','target_handle':target,'requested_fields':['execution_status'],
            'known_progress_refs':[],'permitted_committed_record_types':[]}


def context(path,target='execution:parent'):
    return importlib.import_module(ROOT+'.episode_bindings').BindingContext(
        'run:original','episode:original','monitor',path,{'subject_refs':[]},monitor_assignment(target),{})


class Services:
    def __init__(self,events):self.events=events
    def reference_in_scope(self,reference,scope,namespace):self.events.append(('reference',reference,namespace));return True
    def dependencies(self,target,scope):self.events.append(('dependencies',target));return [{'handle':'execution:child'}]
    def macs2_peak_monitor_task(self,parent,*,assignment):self.events.append(('admission',parent.episode_id,dict(assignment)))


class Registry:
    roles=('monitor','scientific_process');entry_roles=('monitor',)
    def __init__(self,binding,owner,events):self.binding=binding;self.owner=owner;self.events=events;self.scientific=object()
    def for_child(self,path,role,*,owner):
        self.events.append(('for_child',path,role,owner))
        if owner!=self.owner:raise ValueError('controlled_owner_conflict')
        return self.binding
    def for_role(self,role,*,owner):
        self.events.append(('for_role',role,owner));return self.scientific


def outgoing(callback,home,scenario):
    events=[];module=ROOT+'.'+home.replace('/','.')
    binding=importlib.import_module(module+'.episode').MonitorEpisodes(Services(events))
    names=home.split('/')
    role_names={'legacy_annotation':'improvement','scientific_process':'scientific_process',
        'hpc_coordination':'hpc','hpc_allocation_execution':'hpc_execution','execution_monitoring':'monitor'}
    parts=[] if names[0]=='legacy_annotation' else [('annotation','original')]
    parts.extend((role_names[name],name+'_'+str(index)) for index,name in enumerate(names))
    path=tuple(parts);source=SimpleNamespace(path=path,episode_id='episode:original')
    ctx=context(path);scope=ctx.scope
    selection={'kind':'episode_child','role':'monitor','assignment':monitor_assignment('execution:child'),
               'goal':'Observe the assigned original dependency.','purpose':'Typed progress information.'}
    if scenario=='expanded_types':selection['assignment']['permitted_committed_record_types']=['source']
    wf=SimpleNamespace(run_id='run:original',annotation_child_roles=('monitor',),
        episode_bindings=Registry(binding,home,events),binding_context=lambda unused:ctx,
        specialist=lambda unused:binding,available_child_roles=lambda unused:() if scenario=='unavailable' else ('monitor',),
        launch_instructions=SimpleNamespace(materialize=lambda value:events.append(('materialize',value))))
    def form(*args,**kwargs):events.append(('form',args[2],args[3],kwargs));return deepcopy(SCHEMA),{'version':'original_declaration'}
    wf.expanded_contract_form=form
    wf.child_initial_report_input=lambda *args:json.dumps({'qualified':'wrong' if scenario=='invalid_initial' else False})
    chosen='foreign_owner' if scenario=='foreign_owner' else home
    result=capture(lambda:callback(wf,source,selection,3,scope,'monitor',chosen))
    return result,events


def capture(callback):
    try:return ('returned',callback())
    except Exception as error:
        feedback=getattr(error,'feedback',None)
        if hasattr(feedback,'as_record'):feedback=feedback.as_record()
        return ('raised',type(error),str(error),getattr(error,'code',None),feedback)


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('scenario',('valid','expanded_types','invalid_initial','unavailable','foreign_owner'))
def test_original_outgoing_request_typed_admission_and_selected_owner(home,scenario):
    cls=importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode').MonitorEpisodes
    exchange=cls.child_message_exchange('monitor');assert exchange is not None
    assert cls.child_message_exchange('job_monitor') is None
    actual=outgoing(exchange[0],home,scenario);expected=outgoing(original_callbacks()[0],home,scenario)
    assert actual==expected
    if scenario=='valid':
        assert actual[0][0]=='returned' and len(actual[0][1])==6
        assert actual[0][1][3]['target_handle']=='execution:child'
        assert actual[0][1][4:] == (None,None)
        assert any(row[0]=='for_role' for row in actual[1])
    else:assert actual[0][0]=='raised'


class AdmissionPorts:
    run_id='run:original'
    def __init__(self,scenario):
        self.events=[];self.saved=None;self.scenario=scenario
        self.episode_branch_lifecycle=importlib.import_module(ROOT+'.workflow_values').EPISODE_BRANCH_LIFECYCLE
        self.store=SimpleNamespace(db=self)
        self.journal=SimpleNamespace(row=lambda *args:{'result':json.dumps({'delivery_resolution_index':8}) if scenario=='redelivery' else None})
        if scenario in ('saved','redelivery','saved_failure'):
            self.saved={'decision_index':8 if scenario=='redelivery' else 3,
                        'form':json.dumps({'qualified':True}),'failure':None,
                        'contract':json.dumps({'measurements':{'schema':SCHEMA}})}
            if scenario=='saved_failure':self.saved['failure']=json.dumps({'code':'original_saved_failure'})
    def execute(self,sql,parameters):
        self.events.append(('query',sql,parameters));return SimpleNamespace(fetchone=lambda:deepcopy(self.saved))
    def delivery_feedback(self,reference,error):return {'delivery_ref':reference,'code':error.diagnostic['code']}
    def save_attempt(self,parent,index,delivery,child,contract,**value):
        self.events.append(('save_attempt',parent,index,delivery,child,deepcopy(value)))
        self.saved={'decision_index':index,'form':json.dumps(value.get('form')),
                    'failure':json.dumps(value['failure']) if 'failure' in value else None,
                    'contract':json.dumps({'measurements':{'schema':SCHEMA}})}
    def receive_form(self,source,admitted,schema,index,*,redelivery):
        self.events.append(('receive',source.episode_id,deepcopy(admitted),deepcopy(schema),index,redelivery))
        return ['record_'+'4'*24]


def incoming(callback,scenario):
    wf=AdmissionPorts(scenario);source=SimpleNamespace(episode_id='episode:original')
    child=SimpleNamespace(source=SimpleNamespace(episode_id='episode:child'))
    request=SimpleNamespace(goal=SimpleNamespace(goal_id='goal:original'))
    cls=importlib.import_module(ROOT+'.workflow_values').TypedReportContract
    # A primitive Boolean form needs the real typed validator, with no optional
    # scientific semantic callback. Do not load unrelated protein assessment.
    contract=cls('Original typed Boolean qualification.',deepcopy(SCHEMA),lambda *args:True)
    Record=importlib.import_module(ROOT+'.task_values').Record
    result=Record({'form':{'qualified':'invalid' if scenario in ('invalid','saved','redelivery') else False}})
    first=capture(lambda:callback(wf,source,child,3,deepcopy(SCHEMA),contract,result,request))
    replay=capture(lambda:callback(wf,source,child,3,deepcopy(SCHEMA),contract,result,request))
    return first,replay,wf.events


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('scenario',('fresh','invalid','saved','saved_failure','redelivery'))
def test_original_incoming_typed_admission_replay_failure_and_redelivery(home,scenario):
    actual=importlib.import_module(ROOT+'.'+home.replace('/','.')+'.episode').MonitorEpisodes.child_message_exchange('monitor')[1]
    observed=incoming(actual,scenario);expected=incoming(original_callbacks()[1],scenario)
    assert observed==expected and observed[0]==observed[1]
    calls=[row[0] for row in observed[2]]
    if scenario in ('invalid','saved_failure'):
        assert observed[0][0]=='raised'
        assert observed[0][1] is importlib.import_module(ROOT+'.method_loop.episode').ReportDeliveryError
        assert 'receive' not in calls
    else:
        assert observed[0][0]=='returned'
        assert observed[0][1][1]==['record_'+'4'*24]
        assert calls.count('receive')==2
    if scenario=='fresh':assert calls.count('save_attempt')==1
    if scenario in ('saved','saved_failure','redelivery'):assert 'save_attempt' not in calls
    if scenario=='redelivery':assert all(row[-1] is True and row[-2]==8 for row in observed[2] if row[0]=='receive')
