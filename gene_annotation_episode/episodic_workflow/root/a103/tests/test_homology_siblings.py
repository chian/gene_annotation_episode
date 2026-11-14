"""Two real sibling tasks and actual legacy parent paths; controls are explicitly scoped."""
import asyncio,json,sqlite3
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from .homology_sibling_checks import *

@pytest.mark.parametrize('role',ROLES,ids=ROLES)
def test_actual_private_task_and_descriptor(tmp_path,role):
 with actual(tmp_path,role) as f:
  assert type(f.task) is getattr(f.binding,'decision_source_type',module('runtime').DecisionSource)
  if private(f):assert type(f.task).__module__.endswith(HOMES[role]+'.task') and not isinstance(f.task,module('runtime').DecisionSource)
  assert f.binding.roles==f.binding.entry_roles==(role,) and f.binding.binding_path==f.parent_home+'/'+HOMES[role]
  assert f.binding.as_record()['registry_directory']==str(f.jobs.directory)
  assert_parent_implementations(tmp_path/'paired-parents',role)
  assert set(f.binding.as_record()['role_credit_bindings'])=={'job_launch','job_monitor','job_results'}
  assert f.jobs._row(f.job)['submission_requested']==0

PARENTS=[(role,p,m,r) for role in ROLES for p in ('annotation','improvement') for m in (False,True) for r in (False,True)]
PIDS=[role+'-'+p+'-'+('declared' if m else 'markerless')+'-'+('receipts' if r else 'no-receipts') for role,p,m,r in PARENTS]
@pytest.mark.parametrize('role,parent,marker,receipts',PARENTS,ids=PIDS)
def test_actual_parent_request_replay(tmp_path,role,parent,marker,receipts):
 with actual(tmp_path,role,parent,marker,receipts) as f:
  first=observe(f);assert observe(f)==first
  assert json.loads(first['path'])==[[parent,'original-parent'],[role,'child_0']]
  assert first['commission']['request_raw']==first['child_request']
  assert ('knowledge_inheritance' in json.loads(first['child_request'])['message']) is receipts
  assert f.flow.journal.row('runtime_actions',f.source.episode_id,0)['result'] is None
  repeat=commission(f,1)
  assert repeat['child_id']!=first['commission']['child_id'] and repeat['path_raw']!=first['path']
  assert repeat['assignment']==first['assignment'] and repeat['descriptor']==first['descriptor']
  assert repeat['owner_module']==type(f.binding).__module__ and repeat['task_module']==type(f.task).__module__

REPORTS=[(*row,redelivery) for row in PARENTS for redelivery in (False,True)]
RIDS=[name+'-'+('redelivery' if redelivery else 'initial') for name in PIDS for redelivery in (False,True)]
@pytest.mark.parametrize('role,parent,marker,receipts,redelivery',REPORTS,ids=RIDS)
def test_actual_parent_receive_and_redelivery(tmp_path,role,parent,marker,receipts,redelivery):
 with actual(tmp_path,role,parent,marker,receipts) as f:
  f.flow.progress_provider=module('episode_monitoring').ProgressProvider(f.store,f.flow.execution_backend,run_id=f.flow.run_id)
  unit=f.flow.selected(f.source,deepcopy(f.selection),0);value={'state':'unresolved'}
  f.flow.save_attempt(f.source.episode_id,0,'original-delivery',f.task.episode_id,unit.child.request.report_contract,form=value)
  assert f.flow.receive_form(f.source,value,form(),0,redelivery=redelivery)==[]
  rows=raw_rows(f.flow);assert f.flow.receive_form(f.source,value,form(),0,redelivery=redelivery)==[] and raw_rows(f.flow)==rows

FAILS=[(r,p,s) for r in ROLES for p in ('annotation','improvement') for s in ('initial','selection','receipt-parent')]
@pytest.mark.parametrize('role,parent,scenario',FAILS,ids=['-'.join(v) for v in FAILS])
def test_actual_parent_failure_order_and_rollback(tmp_path,role,parent,scenario):
 with actual(tmp_path,role,parent,receipts=True) as f:
  changed=deepcopy(f.selection);index=0 if scenario=='selection' else 1
  if scenario=='initial':changed['initial_report_json']=json.dumps({'state':'invented'})
  elif scenario=='selection':changed['goal']='Changed selected original goal'
  else:
   other=f.flow.build(parent,'different-parent','Other original parent',f.scope)
   identity=module('runtime').Episode.identity(f.flow.context,f.flow.grains[role],'child_1',parent_path=f.source.path)
   f.flow.receipts.bind(identity.episode_id,other.source.episode_id)
  before=raw_rows(f.flow)
  error=module('communication').ReportBoundaryError if scenario=='initial' else module('episode_journal').WorkflowError if scenario=='selection' else ValueError
  with pytest.raises(error):f.flow.selected(f.source,changed,index)
  assert raw_rows(f.flow)==before

OPERATIONS=[(r,n,failure) for r in ROLES for n in TOOLS[r] for failure in (False,True)]
@pytest.mark.parametrize('role,name,failure',OPERATIONS,ids=[r+'-'+n+'-'+('failure' if f else 'returned') for r,n,f in OPERATIONS])
def test_original_operation_dispatch_and_returned_failure(tmp_path,role,name,failure):
 with actual(tmp_path,role) as f:
  # Replace only the external/native operation boundary. Binding dispatch, CPU/search identity,
  # exception translation and actual Store remain real. Parser evidence success is not claimed.
  args={'limit':0} if name=='homology.extract' else {'snapshot_ref':'source_missing'} if name=='homology.coverage' else {'snapshot_ref':'source_missing','offset':0,'limit':1} if name=='homology.errors' else {}
  error=sqlite3.OperationalError('controlled ordinary storage failure')
  target=f.jobs;attribute=name.split('.')[1]
  if name in ('homology.extract','homology.errors'):target=module('homology_results').HomologyResults
  elif name=='homology.coverage':target=module(private_home(f)+('.execution_operations' if private(f) else '.episode'));attribute='recorded_coverage'
  if name=='homology.extract':
   async def extract(*args,**kwargs):
    if failure:raise error
    return {'status':'unavailable','record_refs':[],'changed_record_refs':[],'feedback':{'code':'controlled_no_native_evidence'}}
   native=module('homology_results').NativePhmmerInput
   with patch.object(native,'from_job',return_value=object()),patch.object(target,attribute,side_effect=extract):result=asyncio.run(f.binding.execute(f.task,name,args,operation_key='original-selected-port'))
  else:
   with patch.object(target,attribute,side_effect=error if failure else None,return_value={'controlled':'native-port-return'}):
    result=asyncio.run(f.binding.execute(f.task,name,args,operation_key='original-selected-port'))
  assert result['status']==('failed' if failure else 'unavailable' if name=='homology.extract' else 'completed')
  if failure:assert result['feedback']['exception_type']=='OperationalError' and result['feedback']['operation']==name

OUTCOMES=[(r,s) for r in ROLES for s in ('completed','failed','unavailable','invalid')]
@pytest.mark.parametrize('role,status',OUTCOMES,ids=['-'.join(v) for v in OUTCOMES])
def test_returned_action_enters_original_task_progress(tmp_path,role,status):
 with actual(tmp_path,role) as f:action(f,status)

REASONS=[(r,c) for r in ROLES for c in (False,True)]
@pytest.mark.parametrize('role,completed',REASONS,ids=[r+'-'+('completed' if c else 'unfinished') for r,c in REASONS])
def test_saved_reason_keeps_identity_and_replay(tmp_path,role,completed):
 with actual(tmp_path,role) as f:
  selection={'kind':'reason','commit':{'interpretation_accounts':[]}};result={'status':'completed','record_refs':[],'changed_record_refs':[]}
  f.flow.journal.save('runtime_actions',{'episode_id':f.task.episode_id,'decision_index':9,'action':json.dumps(selection),'result':json.dumps(result) if completed else None,'credit':0 if completed else None})
  with patch.object(f.store,'commit_reasoning',return_value=result) as commit:
   observed=asyncio.run(f.task.execute(selection,9));assert asyncio.run(f.task.execute(selection,9)).as_record()==observed.as_record()
  assert commit.call_count==(0 if completed else 1)

@pytest.mark.parametrize('role',ROLES,ids=ROLES)
def test_ready_owned_child_precedes_new_decision(tmp_path,role):
 with actual(tmp_path,role) as f:
  ready=object();calls=[];f.task._execution_context=SimpleNamespace(_ready_owned_child=lambda path:calls.append(path) or ready)
  assert asyncio.run(f.task.next(SimpleNamespace(units_consumed=0))) is ready and calls==[f.task.path] and f.task.calls==0

@pytest.mark.parametrize('role',ROLES,ids=ROLES)
def test_selected_wait_retains_prior_credit(tmp_path,role):
 with actual(tmp_path,role) as f:
  calls=[]
  async def wait(source,condition,index):calls.append((source.episode_id,condition,index));return {'status':'completed','record_refs':[],'changed_record_refs':[]}
  selection={'kind':'wait','condition':{'original':'controlled-readiness'}}
  with patch.object(f.flow,'perform_selected_wait',side_effect=wait):
   first=asyncio.run(f.task.execute(selection,4));assert asyncio.run(f.task.execute(selection,4)).as_record()==first.as_record()
  assert calls==[(f.task.episode_id,selection['condition'],4)] and f.flow.journal.row('runtime_actions',f.task.episode_id,4)['credit']==0

CALLBACKS=[(r,s) for r in ROLES for s in ('return','exception')]
@pytest.mark.parametrize('role,scenario',CALLBACKS,ids=['-'.join(v) for v in CALLBACKS])
def test_custom_instruction_service_is_original_authority(tmp_path,role,scenario):
 with actual(tmp_path,role) as f:
  assert f.task.instructions({})==module('runtime_prompt').instructions(f.task,{})
  error=RuntimeError('original custom instruction failure')
  with patch.object(f.flow.services,'instructions',return_value='exact custom instructions',side_effect=error if scenario=='exception' else None) as call:
   if scenario=='exception':
    with pytest.raises(RuntimeError) as caught:f.task.instructions({'retained':True})
    assert caught.value is error
   else:assert f.task.instructions({'retained':True})=='exact custom instructions'
   call.assert_called_once_with(f.task,{'retained':True})

PRESENTATIONS=[(r,s) for r in ROLES for s in ('minimal','bootstrap','full-unrecognized','lookup-without-state','hpc-priority','hpc-bootstrap','hpc-update','hpc-lookup','lost-task-update')]
@pytest.mark.parametrize('role,scenario',PRESENTATIONS,ids=['-'.join(v) for v in PRESENTATIONS])
def test_actual_provider_dispatch_is_preserved(tmp_path,role,scenario):
 with actual(tmp_path,role) as f:presentation(f,scenario)

CROSS=[(r,saved) for r in ROLES for saved in ('job_launch','job_monitor','job_results')]
@pytest.mark.parametrize('role,saved_role',CROSS,ids=['-'.join(v) for v in CROSS])
def test_saved_cross_role_binding_and_report_API(tmp_path,role,saved_role):
 with actual(tmp_path,role) as f:
  assert f.binding.binding_for(saved_role)==f.binding.as_record()['role_credit_bindings'][saved_role]
  # Typed interpretation with no native x-source is a genuine retained API, not new foreign work.
  f.binding.validate_report({'state':'unresolved'},assigned(f),role=saved_role,store=f.store,schema=form())
  schema={'type':'object','properties':{'native':{'type':'string','x-source':'job_not_owned'}},'required':['native']}
  with pytest.raises(module('communication').ReportBoundaryError,match='Fact does not belong'):
   f.binding.validate_report({'native':'x'},assigned(f),role=saved_role,store=f.store,schema=schema)

ADAPTERS=[(r,s) for r in ROLES for s in ('catalog','context')]
@pytest.mark.parametrize('role,scenario',ADAPTERS,ids=['-'.join(v) for v in ADAPTERS])
def test_resource_adapter_keeps_exact_private_owner(tmp_path,role,scenario):
 with actual(tmp_path,role) as f:
  adapter=module('a103_homology_resource_adapter').HomologyResourceAdapter(f.bindings,f.store,f.flow.journal)
  current='launch_local' if role=='job_launch' else 'results'
  context=SimpleNamespace(role=current,path=(('scientific_process','actual'),(current,'original-key')),episode_id=f.task.episode_id,
   scope=f.scope,assignment={'adapter_assignment':assigned(f)},run_id=f.flow.run_id)
  internal=adapter._legacy(context)
  assert adapter.homology[role] is f.binding and internal.episode_id==context.episode_id and internal.path[-1]==(role,'original-key')
  if scenario=='catalog':assert adapter.catalog(context)==f.binding.catalog(internal)
  else:assert internal.request.message.as_record()['job_assignment']==assigned(f) and internal.workflow.store is f.store

@pytest.mark.parametrize('role',ROLES,ids=ROLES)
def test_credit_and_foreign_wrapper_destinations(tmp_path,role):
 with actual(tmp_path,role) as f:
  own='_launch_credit' if role=='job_launch' else '_results_credit';foreign='_results_credit' if role=='job_launch' else '_launch_credit'
  assert callable(getattr(f.binding,own)) and hasattr(f.binding,foreign) is (not private(f))
  assert hasattr(f.binding,'_monitor_credit') is (not private(f))
  assert callable(getattr(f.bindings['job_monitor'],'_monitor_credit')) and f.binding.credit_view(f.task)['credit']==0
  assert f.binding.credit_kind(role)=='operational'

@pytest.mark.parametrize('role',ROLES,ids=ROLES)
def test_foreign_tool_rejection_precedes_action(tmp_path,role):
 with actual(tmp_path,role) as f:
  before=raw_rows(f.flow)
  with pytest.raises(ValueError,match='tool_not_owned_by_job_role'):
   asyncio.run(f.binding.execute(f.task,'homology.sample',{},operation_key='never-acquired'))
  assert raw_rows(f.flow)==before

@pytest.mark.parametrize('role',ROLES,ids=ROLES)
def test_nested_improvement_inherited_failure_unchanged(tmp_path,role):
 with actual(tmp_path,role) as f:
  selection={'kind':'child','goal':'Unresolved nested task','scope':deepcopy(f.scope),'purpose':'Original missing task-credit boundary','schema_json':json.dumps(form()),'initial_report_json':json.dumps({'state':'unresolved'})}
  before=raw_rows(f.flow)
  with pytest.raises(ValueError,match='scientific_task_credit_not_declared:improvement'):f.flow.selected(f.source,selection,1)
  assert raw_rows(f.flow)==before

@pytest.mark.parametrize('role',ROLES,ids=ROLES)
def test_actual_saved_source_restore_keeps_unfinished_identity(tmp_path,role):
 with actual(tmp_path,role) as f:
  action(f,'failed',7);expected=f.flow.completions.restore_source(f.task.episode_id)
  rows=raw_rows(f.flow);f.task.restore()
  assert f.task._restored is True and f.task.calls==expected['next_call_index']
  assert f.task._unfinished_own_actions==expected['unfinished_own_action_indices']==[7]
  assert raw_rows(f.flow)==rows

FINISH=[(r,s) for r in ROLES for s in ('fresh','saved')]
@pytest.mark.parametrize('role,scenario',FINISH,ids=['-'.join(v) for v in FINISH])
def test_actual_finish_preserves_original_form_and_replay(tmp_path,role,scenario):
 with actual(tmp_path,role) as f:
  if scenario=='saved':f.flow.journal.save('runtime_forms',{'episode_id':f.task.episode_id,'facts':json.dumps({'retained':'original'}),'form':json.dumps({'state':'unresolved'})})
  first=asyncio.run(f.task.finish(None));rows=raw_rows(f.flow);record=dict(f.flow.journal.row('runtime_forms',f.task.episode_id))
  second=asyncio.run(f.task.finish(None))
  assert first.as_record()==second.as_record()=={'form':{'state':'unresolved'}}
  assert dict(f.flow.journal.row('runtime_forms',f.task.episode_id))==record and raw_rows(f.flow)==rows

PENDING=[(r,d) for r in ROLES for d in (False,True)]
@pytest.mark.parametrize('role,declared',PENDING,ids=[r+'-'+('declared' if d else 'legacy') for r,d in PENDING])
def test_pending_model_call_and_completed_replay_use_actual_provider_dispatch(tmp_path,role,declared):
 with actual(tmp_path,role) as f:
  runtime=module('runtime');state={'working_state':f.binding.working_state(f.task),'scope':f.task.scope}
  tool=TOOLS[role][0];arguments={'limit':0} if role=='job_results' else {}
  schema=runtime._object({'selection':runtime._object({'kind':{'const':'tool'},'tool':{'const':tool},'arguments':{'type':'object'}}),'report_update':runtime._object({})})
  response={'selection':{'kind':'tool','tool':tool,'arguments':arguments},'report_update':{}}
  f.flow.journal.save('runtime_model_calls',{'episode_id':f.task.episode_id,'call_index':0,'purpose':'decision','request':json.dumps({'context':state,'schema':schema}),'response':None})
  renderer=object.__new__(module('providers')._SessionConnection);renderer.scientific_prompt_states={};calls=[]
  async def complete(episode,mode,instructions,context,output_schema,**kw):
   calls.append(renderer._presentation(episode,mode,instructions,context,**kw));return deepcopy(response)
  provider=SimpleNamespace(has_session=lambda *args:True,complete=complete)
  if declared:provider.complete_with_presentation=complete
  with patch.object(f.flow,'provider',provider):
   first=asyncio.run(f.task.call({},schema));f.task.calls=0;second=asyncio.run(f.task.call({},schema))
  assert first==second and first[0]==response and len(calls)==1
  assert f.flow.journal.row('runtime_actions',f.task.episode_id,0) is None

@pytest.mark.parametrize('role',ROLES,ids=ROLES)
def test_default_service_invokes_exact_private_composer(tmp_path,role):
 with actual(tmp_path,role) as f:
  expected=module('runtime_prompt').instructions(f.task,{})
  if not private(f):
   assert not hasattr(type(f.task),'instruction_composer') and f.task.instructions({})==expected
  else:
   composer=module(private_home(f)+'.instructions').instructions
   assert type(f.task).instruction_composer is composer
   calls=[]
   def observed(source,context):calls.append((source,context));return composer(source,context)
   with patch.object(type(f.task),'instruction_composer',staticmethod(observed)):
    assert f.task.instructions({})==expected
   assert calls==[(f.task,{})]

FOREIGN=[(r,s) for r in ROLES for s in ('job_launch','job_monitor','job_results') if r!=s]
@pytest.mark.parametrize('role,foreign',FOREIGN,ids=['-'.join(v) for v in FOREIGN])
def test_fresh_foreign_credit_api_narrowing_has_actual_owner(tmp_path,role,foreign):
 with actual(tmp_path,role) as f:
  arguments=(f.store,foreign,assigned(f),f.task.episode_id,f.flow.run_id)
  destination=f.bindings[foreign].initial_credit(*arguments)
  if private(f):
   with pytest.raises(ValueError,match='^unknown_job_episode_role$'):f.binding.initial_credit(*arguments)
  else:assert f.binding.initial_credit(*arguments)==destination
  assert f.binding.binding_for(foreign)==f.bindings[foreign].binding_for(foreign)


@pytest.mark.parametrize('role',('job_launch','job_monitor','job_results'),ids=('job_launch','job_monitor','job_results'))
def test_saved_counterpart_stays_with_actual_parent_type(tmp_path,role):
 assert_saved_parent_counterpart(tmp_path,role)
