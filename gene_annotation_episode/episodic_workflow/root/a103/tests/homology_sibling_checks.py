"""Real Workflow/Store/job registry; explicitly controlled ordinary native ports.

No task, Episode identity, selected/build, receipt, credit or iterator is replaced.
No successful native worker or scientific evidence is claimed by returned-port controls.
"""
import asyncio,json
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from .homology_direction_checks import actual as parent_actual,commission,form,module,raw_rows
ROLES=('job_launch','job_results')
HOMES={'job_launch':'homology_job_submission','job_results':'homology_result_acquisition'}
TOOLS={'job_launch':('homology.environment','homology.configure','homology.stage','homology.submit','homology.resume_start','homology.check_handoff'),
 'job_results':('homology.extract','homology.coverage','homology.errors')}
@contextmanager
def actual(directory,role,parent='annotation',marker=False,receipts=False):
 with parent_actual(directory,parent=parent,marker=marker,receipts=receipts,role=role) as f:
  unit=f.flow.selected(f.source,deepcopy(f.selection),0);f.task=unit.child.source
  assert f.task.workflow is f.flow and type(f.flow) is module('runtime').Workflow
  assert f.task.path==(*f.source.path,(role,'child_0')) and f.task.episode_id!=f.source.episode_id
  yield f

def assigned(f):return f.binding.assignment(f.task)
def private(f):return hasattr(f.binding,'decision_source_type')
def action(f,status,index=3):
 selection={'kind':'tool','tool':TOOLS[f.role][0],'arguments':({'limit':0} if f.role=='job_results' else {})}
 result={'status':status,'record_refs':[],'changed_record_refs':[],'result':{'fixture':'controlled-native-port'},'feedback':None if status=='completed' else {'code':'controlled_'+status}}
 calls=[];pending_snapshots=[];original_pending_work=f.flow.pending_work
 async def port(source,name,args,*,operation_key):
  assert source is f.task and name==selection['tool'];calls.append(operation_key);return deepcopy(result)
 def capture_pending_work(source):
  assert source is f.task
  pending=original_pending_work(source)
  pending_snapshots.append(deepcopy(pending))
  return pending
 # Observe the actual producer: its captured_at belongs to this original action.
 # Replay must reuse the saved snapshot, without another producer or native call.
 with patch.object(f.binding,'execute',side_effect=port),patch.object(f.flow,'pending_work',side_effect=capture_pending_work):
  value=asyncio.run(f.task.execute(selection,index));replay=asyncio.run(f.task.execute(selection,index))
 assert value.as_record()==replay.as_record() and calls==[f'{f.flow.run_id}:{f.task.episode_id}:{index}']
 assert len(pending_snapshots)==1 and pending_snapshots[0]['version']=='pending_work_v2' and pending_snapshots[0]['items']==[]
 expected={**result,'pending_work_after_action':pending_snapshots[0]}
 row=dict(f.flow.journal.row('runtime_actions',f.task.episode_id,index));assert json.loads(row['result'])==expected and row['credit']==0
 assert json.loads(row['action'])==selection
 assert f.task.last_outcome==expected and f.task.last_outcome_index==index
 return {'action':json.loads(row['action']),'outcome':json.loads(row['result']),'credit':row['credit'],'controller':value.as_record()}

def observe(f):
 request=commission(f);descriptor=deepcopy(f.binding.as_record());row=f.flow.journal.row('runtime_episodes',f.task.episode_id)
 return {'commission':request,'descriptor':descriptor,'child_request':row['request'],'path':row['path'],
  'catalog':f.binding.catalog(f.task),'assignment':assigned(f),'credit':f.binding.credit_view(f.task),
  'instructions':f.task.instructions({}),'initial_credit':row['initial_credit']}

def presentation(f,scenario):
 providers=module('providers');frames=module('decision_context');left=object.__new__(providers._SessionConnection);right=object.__new__(providers._SessionConnection)
 left.scientific_prompt_states={};right.scientific_prompt_states={}
 state={'working_state':f.binding.working_state(f.task),'scope':f.task.scope,'goal':{'objective':'Preserve original assigned work'}}
 hpc={**state,'hpc_commission':{'objective':'Original higher priority'}}
 context={} if scenario=='minimal' else frames.state_frame(state) if scenario=='bootstrap' else state if scenario=='full-unrecognized' else {'version':frames.VERSION,'kind':'decision_lookup_result','result':{'original':'record'}} if scenario=='lookup-without-state' else hpc
 key=(f.task.episode_id,'REASONING')
 if scenario=='hpc-bootstrap':context=frames.state_frame(hpc)
 if scenario in ('hpc-update','hpc-lookup','lost-task-update'):
  left.scientific_prompt_states[key]=deepcopy(hpc);right.scientific_prompt_states[key]=deepcopy(hpc)
  context={'version':frames.VERSION,'kind':'decision_lookup_result','result':{'original':'record'}} if scenario=='hpc-lookup' else frames.state_frame(state,hpc) if scenario=='lost-task-update' else frames.state_frame({**hpc,'goal':{'objective':'Updated'}},hpc)
 instructions=f.task.instructions({});expected=left._presentation(f.task.episode_id,'REASONING',instructions,deepcopy(context))
 renderer=getattr(f.binding,'decision_prompt_renderer',None)
 observed=right._presentation(f.task.episode_id,'REASONING',instructions,deepcopy(context),**({'prompt_renderer':renderer} if renderer else {}))
 assert observed==expected and right.scientific_prompt_states==left.scientific_prompt_states
 return observed

from .homology_parent_private_checks import assert_parent_implementations, assert_saved_parent_counterpart

def private_home(f):
 return f.parent_home+'.'+HOMES[f.role]
