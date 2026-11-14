"""Actual A103 libraries, registered head, Journal and original task boundaries.

The shared instruction/tool fixture is engineering data. The runtime harness
uses the actual A103 projector with explicit empty received evidence. Transport,
controller result packaging and model responses are controlled ports. No native
job, network request or autonomous scientific decision is asserted.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace, MethodType
from unittest.mock import patch
import pytest
from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import ScientificHeadBoundaryChecks
PACKAGE='gene_annotation_episode.episodic_workflow.root.a103'
def module(name): return import_module(PACKAGE+'.'+name)
def forbidden(*a,**kw): raise AssertionError('no process/network/native work in scientific task checks')
class BoundaryFixture(ScientificHeadBoundaryChecks): axis='a103'

@contextmanager
def actual(directory,standalone=False,timing=False):
 directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
 with patch('subprocess.Popen',forbidden),patch('socket.socket.connect',forbidden),patch('socket.socket.connect_ex',forbidden):
  generator=ScientificHeadBoundaryChecks.scientific.__wrapped__(BoundaryFixture(),directory)
  v=next(generator)
  try:
   runtime=module('runtime'); binding=v.binding; run_id=v.parent.run_id
   path=(('scientific_process','child_0'),) if standalone else v.context.path
   episode_id=module('method_loop.identities').EpisodeRef(run_id,path).episode_id
   journal=module('episode_journal').Journal(v.store,run_id); projected=[]; received=[]; operations=[]
   projector=binding.credit_projector(v.context)
   def science(context,selection):
    value=projector(v.store,module('communication').plain(context.scope),known_record_refs=selection['known_record_refs'],run_id=run_id,episode_id=context.episode_id)
    projected.append(deepcopy(value)); return value
   v.services.scientific_credit=science; v.services.instructions=module('runtime_prompt').instructions; v.services.received_progress_refs=lambda episode:[]
   async def execute(source,name,arguments,**kw):
    operations.append(kw['operation_key']); return await binding.execute(w.binding_context(source),name,arguments,kw['operation_key'])
   async def updates(source,index,result): return result
   w=SimpleNamespace(context=object(),grains={'annotation':object(),'scientific_process':object()},run_id=run_id,store=v.store,journal=journal,
    episode_bindings=module('episode_bindings').EpisodeBindingRegistry((binding,)),scientific_process_binding=binding,job_episodes=None,
    receipts=None,inprocess_completion_order=None,inprocess_replay=None,execution_binding=None,
    wait_inputs_version=None,completed_action_inputs_version=None,progress_receipt_order='received_progress_order_v1',
    contract_information_profile=lambda source:None,specialist=lambda source:binding,is_job_source=lambda source:False,
    launch_instructions=SimpleNamespace(materialize=lambda value:None,instructions='Controlled empty launch manual.'),
    receive_tool_attributions=lambda *a,**kw:None,expose_assigned_job=lambda source:None,archive=SimpleNamespace(store=lambda value:value),
    resolver=lambda *a,**kw:lambda ref:ref==v.target,validate_report=lambda form,scope,grain,schema,source:binding.validate_report(w.binding_context(source),form,schema),
    services=v.services,native_timing_information=None,native_event_information=None,decision_protocol=None,progress_provider=None,
    execute=execute,receive_native_outcome=lambda *a:None,receive_outcome=lambda source,selection,result,index:received.append((index,result['status'])),
    automatic_score_updates=updates,controller_value=lambda source,index,value:{'index':index,'credit':value})
   w.legacy_parent_for_path=MethodType(runtime.Workflow.legacy_parent_for_path,w)
   w.binding_context=lambda source:runtime.Workflow.binding_context(w,source)
   w.record_selection=lambda episode:runtime.Workflow.record_selection(w,episode)
   w.progress_selection=lambda source:runtime.Workflow.progress_selection(w,source)
   w.source_credit_view=lambda source:runtime.Workflow.source_credit_view(w,source)
   w.permits_common_action=lambda source,kind:runtime.Workflow.permits_common_action(w,source,kind)
   if timing:
    w.native_timing_information=lambda *a,**kw:{'monitoring_information_credit':5,'monitoring_information_binding':{'kind':'controlled-native-duration-port'}}
    w.native_timing_arguments=lambda source:{'received_native_timing_refs':[]}
   contract=runtime.TypedReportContract(v.invocation['purpose'],v.form,lambda ref:ref==v.target)
   parent=None if standalone else runtime.EpisodeGoal.root(objective='Original commissioning task',result_contract={'role':'annotation'})
   with patch.object(runtime.Episode,'identity',return_value=SimpleNamespace(episode_id=episode_id)),patch.object(runtime,'FeedbackEpisode',side_effect=lambda grain,key,source,*a,**kw:source):
    task=runtime.Workflow.build(w,'scientific_process','child_0',v.invocation['objective'],module('communication').plain(v.context.scope),parent=parent,parent_path=path[:-1],contract=contract,initial=v.invocation['initial_report'],episode_assignment=v.prepared['assignment'],scientific_process=v.prepared['scientific_process'])
   projected.clear()
   yield SimpleNamespace(v=v,binding=binding,runtime=runtime,workflow=w,task=task,path=path,episode_id=episode_id,journal=journal,store=v.store,projector=projector,projected=projected,received=received,operations=operations)
  finally: generator.close()

def action(f,status,index):
 f.v.outcome['status']=status
 return asyncio.run(f.task.execute({'kind':'tool','tool':'fixture.inspect','arguments':{'record':f.v.target}},index))

class TestScientificHeadTask(ScientificHeadBoundaryChecks):
 axis='a103'

 @pytest.mark.parametrize('standalone',[False,True],ids=['commissioned','standalone'])
 @pytest.mark.parametrize('timing',[False,True],ids=['science','native-timing'])
 def test_actual_build_registry_credit_and_original_invocation(self,tmp_path,standalone,timing):
  with actual(tmp_path,standalone,timing) as f:
   assert type(f.task) is getattr(f.binding,'decision_source_type',f.runtime.DecisionSource)
   if hasattr(f.binding,'decision_source_type'): assert type(f.task).__module__==PACKAGE+'.scientific_process.task' and not isinstance(f.task,f.runtime.DecisionSource)
   assert f.binding.binding_path=='scientific_process' and f.binding.commissioning_parent=='legacy_annotation'
   f.binding.validate_execution_context(f.workflow.binding_context(f.task))
   view=f.workflow.source_credit_view(f.task); assert view['credit']==0
   assert f.projector.as_record()==module('a103_credit').A103ContextCredit().as_record()
   assert ('monitoring_information_credit' in view)==timing
   if timing: assert view['monitoring_information_credit']==5 and view['credit']==0
   assert json.loads(f.journal.row('runtime_episodes',f.episode_id)['request'])==module('communication').plain(f.task.request.as_record())
   with pytest.raises(ValueError,match='scientific_parent_invocation_required'):
    f.binding.prepare_assignment(None,'scientific_process',f.v.assignment,f.task.scope,'rejected-before-acquisition')

 @pytest.mark.parametrize('status',['completed','invalid','failed','unavailable'])
 def test_returned_original_action_projects_and_replays_once(self,tmp_path,status):
  with actual(tmp_path) as f:
   first=action(f,status,0); again=action(f,status,0)
   row=f.journal.row('runtime_actions',f.episode_id,0)
   assert first==again=={'index':0,'credit':0} and row['credit']==0
   assert json.loads(row['result'])==f.v.outcome
   assert f.received==[(0,status)] and len(f.projected)==len(f.operations)==len(f.v.calls)==1
   assert f.operations==[f'{f.workflow.run_id}:{f.episode_id}:0']

 @pytest.mark.parametrize('completed',[False,True],ids=['unfinished','completed'])
 def test_saved_historical_reason_branch(self,tmp_path,completed):
  with actual(tmp_path) as f:
   selection={'kind':'reason','commit':{'interpretation_accounts':[]}}
   result={'status':'completed','record_refs':[],'changed_record_refs':[]}
   f.journal.save('runtime_actions',{'episode_id':f.episode_id,'decision_index':8,'action':json.dumps(selection),'result':json.dumps(result) if completed else None,'credit':0 if completed else None})
   with patch.object(f.store,'commit_reasoning',return_value=result) as commit:
    assert asyncio.run(f.task.execute(selection,8))=={'index':8,'credit':0}
    assert asyncio.run(f.task.execute(selection,8))=={'index':8,'credit':0}
    assert commit.call_count==(0 if completed else 1)
   assert len(f.projected)==len(f.received)==(0 if completed else 1)

 def test_wait_uses_original_prior_credit_and_caller_controller(self,tmp_path):
  with actual(tmp_path) as f:
   calls=[]
   async def wait(source,condition,index): calls.append((condition,index)); return {'status':'completed','record_refs':[],'changed_record_refs':[]}
   f.workflow.perform_selected_wait=wait; f.workflow.last_observed_credit=lambda source:0
   assert asyncio.run(f.task.execute({'kind':'wait','condition':{'original':'controlled'}},3))=={'index':3,'credit':0}
   assert calls==[({'original':'controlled'},3)] and f.projected==[]
   controller=object(); selections=[]; f.workflow.controller_factory=lambda path,credit:selections.append((path,credit)) or controller
   f.workflow.has_native_estimation=lambda:False
   with patch.object(f.runtime.Episode,'identity',return_value=SimpleNamespace(episode_id=f.episode_id)),patch.object(f.runtime,'ExecutionContextController',side_effect=lambda value,*a,**kw:value):
    assert f.runtime.Workflow.controller(f.workflow,f.path) is controller
   assert selections==[(f.path,f.journal.row('runtime_episodes',f.episode_id)['initial_credit'])]

 def test_original_scientific_guidance_and_dynamic_action_predicates(self,tmp_path):
  with actual(tmp_path) as f:
   assert f.task.instructions({})==module('runtime_prompt').instructions(f.task,{})
   context=f.workflow.binding_context(f.task)
   assert f.binding.allowed_children(context,None)==('scientific_process',)
   assert set(f.binding.permitted_common_actions(context))=={'tool','reason','child','wait','redeliver_report'}
   assert f.binding.initial_decision_context(context)=={}
   assert f.binding.decision_context(context,None)['scientific_process']['selection']['evidence_axis']==f.v.selected['evidence_axis']

 @pytest.mark.parametrize('standalone',[False,True],ids=['commissioned','standalone'])
 @pytest.mark.parametrize('timing',[False,True],ids=['science','native-timing'])
 def test_actual_next_assembles_original_scientific_context(self,tmp_path,standalone,timing):
  with actual(tmp_path,standalone,timing) as f:
   w=f.workflow
   w.working_state=lambda source:{}; w.local_outcome_preview=lambda value,**kw:value
   w.receipt_projection=lambda source:False; w.source_credit_binding=lambda source:f.projector.as_record()
   w.pending_work=lambda source:[]; w.delivery_status=lambda episode:[]; w.controller_binding=None
   w.catalog=lambda scope,source:f.binding.catalog(w.binding_context(source))
   w.knowledge=SimpleNamespace(context=lambda:{},instructions='Controlled empty tool information.')
   w.job_episode_options=lambda source:[]; w.extra_report_sources=lambda source:{}
   w.is_scientific_source=lambda source:True; w.annotation_context=lambda scope,source:{}; w.tools=SimpleNamespace()
   w.action_schema=lambda source:f.runtime._object({})
   view=SimpleNamespace(units_consumed=0,child_reports=(),controller_state={},model_inputs=lambda fields,**kw:fields)
   class Captured(Exception): pass
   observed=[]
   async def capture(context,schema): observed.append(deepcopy(context)); raise Captured()
   f.task.call=capture
   with pytest.raises(Captured): asyncio.run(f.task.next(view))
   context,=observed
   assert context['current_credit']==0 and context['credit_binding']==f.projector.as_record()
   assert context['scientific_process']==f.binding.decision_context(w.binding_context(f.task),view)['scientific_process']
   assert context['requested_report_purpose']==f.v.invocation['purpose'] and context['current_report_update']=={'status':'unresolved'}
   assert ('monitoring_information_credit' in context)==timing
   if timing: assert context['monitoring_information_credit']==5
   assert f.projected and f.received==[] and f.operations==[]

 @pytest.mark.parametrize('scenario',['minimal','bootstrap-unrecognized','scientific','scientific-bootstrap','scientific-update','scientific-lookup','lost-task-update','hpc-priority'])
 def test_actual_provider_original_priority_state_and_fallback(self,tmp_path,scenario):
  with actual(tmp_path) as f:
   providers=module('providers'); frames=module('decision_context')
   original=object.__new__(providers._SessionConnection); private=object.__new__(providers._SessionConnection)
   original.scientific_prompt_states={}; private.scientific_prompt_states={}; key=(f.episode_id,'REASONING')
   state={'goal':{'objective':f.v.invocation['objective']},'scope':f.task.scope,**f.binding.decision_context(f.workflow.binding_context(f.task),None)}
   context={} if scenario=='minimal' else frames.state_frame({}) if scenario=='bootstrap-unrecognized' else state
   if scenario=='scientific-bootstrap': context=frames.state_frame(state)
   if scenario in {'scientific-update','scientific-lookup','lost-task-update'}:
    original.scientific_prompt_states[key]=deepcopy(state); private.scientific_prompt_states[key]=deepcopy(state)
    context=({'version':frames.VERSION,'kind':'decision_lookup_result','result':{'original':'fixture'}} if scenario=='scientific-lookup' else frames.state_frame({} if scenario=='lost-task-update' else {**state,'goal':{'objective':'Retain original question'}},state))
   if scenario=='hpc-priority': context={**state,'hpc_commission':{'objective':'Original higher priority'}}
   instructions=f.task.instructions({}); expected=original._presentation(f.episode_id,'REASONING',instructions,deepcopy(context))
   renderer=getattr(f.binding,'decision_prompt_renderer',None)
   observed=private._presentation(f.episode_id,'REASONING',instructions,deepcopy(context),**({'prompt_renderer':renderer} if renderer else {}))
   assert observed==expected and private.scientific_prompt_states==original.scientific_prompt_states
   if scenario in {'minimal','bootstrap-unrecognized','lost-task-update'}: assert observed==(json.dumps(context,allow_nan=False),instructions)
   else: assert observed[0] and key in private.scientific_prompt_states

 @pytest.mark.parametrize('declared',[False,True],ids=['legacy','declared'])
 @pytest.mark.parametrize('saved_kind',['scientific','root-credit'])
 def test_saved_model_context_resumes_without_new_action(self,tmp_path,declared,saved_kind):
  with actual(tmp_path) as f:
   state={'scope':f.task.scope,**f.binding.decision_context(f.workflow.binding_context(f.task),None)}
   if saved_kind=='root-credit': state={'current_credit':{'mode':'annotation_axis_credit','root_score':0},'controller':{'arms':[],'annotation_credits':{},'root_score':0,'decision':None}}
   schema=f.runtime._object({'selection':f.runtime._object({'kind':{'const':'tool'},'tool':{'const':'fixture.inspect'},'arguments':f.runtime._object({'record':{'type':'string'}})}),'report_update':f.runtime._object({})})
   response={'selection':{'kind':'tool','tool':'fixture.inspect','arguments':{'record':f.v.target}},'report_update':{}}
   f.journal.save('runtime_model_calls',{'episode_id':f.episode_id,'call_index':0,'purpose':'decision','request':json.dumps({'context':state,'schema':schema}),'response':None})
   provider=object.__new__(module('providers')._SessionConnection); provider.scientific_prompt_states={}; calls=[]
   async def complete(episode,role,instructions,context,output_schema,**kw): calls.append(provider._presentation(episode,role,instructions,context,**kw)); return deepcopy(response)
   f.workflow.provider=SimpleNamespace(has_session=lambda *a:True,complete=complete)
   if declared: f.workflow.provider.complete_with_presentation=complete
   first=asyncio.run(f.task.call({},schema)); f.task.calls=0; second=asyncio.run(f.task.call({},schema))
   assert first==second and first[0]==response and first[2]==state and len(calls)==1
   assert f.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==0 and f.projected==[]

 @pytest.mark.parametrize('order',['head-first','runtime-first'])
 def test_cold_import_order_retains_real_class(self,tmp_path,order):
  import os
  import subprocess
  import sys
  code="import importlib; p='"+PACKAGE+"'; order='"+order+"'; first='scientific_process.episode' if order=='head-first' else 'runtime'; importlib.import_module(p+'.'+first); h=importlib.import_module(p+'.scientific_process.episode'); r=importlib.import_module(p+'.runtime'); t=getattr(h.ScientificProcessEpisode,'decision_source_type',r.DecisionSource); assert t is r.DecisionSource or (t.__name__=='ScientificProcessTask' and t.__module__==p+'.scientific_process.task')"
  env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(tmp_path),'XDG_CACHE_HOME':str(tmp_path/'cache')}
  completed=subprocess.run([sys.executable,'-B','-c',code],env=env,text=True,capture_output=True)
  assert completed.returncode==0,(completed.stdout,completed.stderr)

 @pytest.mark.parametrize('role',['monitor','unrelated'])
 def test_existing_parent_monitor_directions_remain_connected(self,tmp_path,role):
  with actual(tmp_path) as f:
   assignment={'version':'monitor_assignment_v1','target_handle':'original-owned-handle','requested_fields':['execution_status'],'known_progress_refs':[],'permitted_committed_record_types':[]}
   prepared=f.binding.prepare_child_request(f.workflow.binding_context(f.task),role,assignment)
   assert prepared==assignment
   received=[]; provider=SimpleNamespace(read_progress=lambda *a:forbidden(),_receive_progress=lambda *a:received.append(a))
   schema=f.runtime._object({}); context=f.workflow.binding_context(f.task)
   result=f.binding.receive_child_progress_for_role(context,role,{},schema,'original-parent-delivery',provider)
   assert result is (role=='monitor')
   if role=='monitor':
    signature=module('method_loop.durable').content_digest({'form':{},'schema':schema,'scope':module('communication').plain(context.scope)})
    assert received==[(f.episode_id,[],signature,'original-parent-delivery')]
   else: assert received==[]
   assert f.projected==[] and f.operations==[]

 def test_rejected_context_is_not_an_acquired_action(self,tmp_path):
  with actual(tmp_path) as f:
   f.task.path=f.task.path[:-1]+(('scientific_process','different-child'),)
   with pytest.raises(ValueError,match='scientific_filled_identity_mismatch'):
    action(f,'completed',0)
   assert f.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==0
   assert f.operations==f.projected==f.received==[]

 def test_ready_original_child_precedes_new_decision(self,tmp_path):
  with actual(tmp_path) as f:
   child=object(); calls=[]; f.task._execution_context=SimpleNamespace(_ready_owned_child=lambda path:calls.append(path) or child)
   assert asyncio.run(f.task.next(SimpleNamespace(units_consumed=0))) is child
   assert calls==[f.path] and f.task.calls==0 and f.projected==[]

 @pytest.mark.parametrize('mode',['returned','raised'])
 def test_original_instruction_service_callback(self,tmp_path,mode):
  with actual(tmp_path) as f:
   context=object(); marker=object(); error=RuntimeError('original callback exception'); calls=[]
   def callback(source,state):
    calls.append((source,state))
    if mode=='raised': raise error
    return marker
   f.workflow.services=SimpleNamespace(instructions=callback)
   with patch.object(type(f.task),'instruction_composer',staticmethod(forbidden),create=True):
    if mode=='raised':
     with pytest.raises(RuntimeError) as caught_error: f.task.instructions(context)
     assert caught_error.value is error
    else: assert f.task.instructions(context) is marker
   assert calls==[(f.task,context)]

 def test_default_instruction_service_uses_private_composer(self,tmp_path):
  with actual(tmp_path) as f:
   context={}; calls=[]; prompt=module('runtime_prompt'); f.workflow.services=module('episode_services').WorkflowServices(f.workflow)
   original=getattr(type(f.task),'instruction_composer',None)
   if hasattr(f.binding,'decision_source_type'):
    assert original is module('scientific_process.instructions').instructions
    def composer(source,state):
     calls.append((source,state)); return original(source,state)
    expected=original(f.task,context)
    with patch.object(type(f.task),'instruction_composer',staticmethod(composer)),patch.object(prompt,'instructions',side_effect=forbidden):
     assert f.task.instructions(context)==expected
   else:
    assert original is None; original=prompt.instructions; expected=original(f.task,context)
    def composer(source,state):
     calls.append((source,state)); return original(source,state)
    with patch.object(prompt,'instructions',side_effect=composer): assert f.task.instructions(context)==expected
   assert calls==[(f.task,context)] and f.projected==f.operations==f.received==[]

 def test_default_instruction_service_nonparticipant_fallback(self,tmp_path):
  with actual(tmp_path) as f:
   context=object(); marker=object(); calls=[]; source=SimpleNamespace(instruction_composer=forbidden)
   service=module('episode_services').WorkflowServices(f.workflow)
   with patch.object(module('runtime_prompt'),'instructions',side_effect=lambda owner,state:calls.append((owner,state)) or marker):
    assert service.instructions(source,context) is marker
   assert calls==[(source,context)]
