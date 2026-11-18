"""Actual native owners, retained Journal, state, and controlled transport boundary.

No native shell/provider/network work. Controlled transport outcomes prove the
adapter/iterator connection, not live submission or scientific validity.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import asyncio
import json
import pytest
PACKAGE='gene_annotation_episode.episodic_workflow.root.a102'
PARENTS=('execution_job_submission','hpc_work_planning/execution_job_submission',
'hpc_work_planning/hpc_allocation_execution/execution_job_submission','structural_homology_evidence/execution_job_submission',
'structural_homology_evidence/hpc_work_planning/execution_job_submission',
'structural_homology_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission')
HOMES=tuple(parent+'/'+child for parent in PARENTS for child in ('local_job_execution','hpc_job_execution'))
TIME='2026-11-12T00:00:00+00:00'
def module(name):return import_module(PACKAGE+'.'+name)
def forbidden(*args,**kwargs):raise AssertionError('native connection fixture forbids uncontrolled process/network/provider work')
def controlled_tool_port(store):
 """Explicit inactive tool boundary; not a production ToolRegistry constructor.

 The real native binding receives this exact Store. Native-only fixture resources
 construct no API execution service. Any unexpected ordinary tool/science/API call
 fails instead of executing or manufacturing a successful result. The retained V1
 default-constructor KeyError remains a separate original diagnostic.
 """
 return SimpleNamespace(store=store,clients=SimpleNamespace(blast=forbidden),
  _protein_structure_configuration=None,catalog=forbidden,execute=forbidden,
  execute_async=forbidden,publish_hmmer_result=forbidden,
  _check_sequence_operand=forbidden,_sequence=forbidden)
def plain(value):return module('communication').plain(value)
def caught(call):
 try:return {'status':'returned','value':plain(call())}
 except Exception as error:return {'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,'message':str(error)}
class Clock(datetime):
 @classmethod
 def now(cls,tz=None):return datetime.fromisoformat(TIME).astimezone(tz or timezone.utc)
def configuration(home):
 kind='local' if home.endswith('/local_job_execution') else 'hpc'
 root=Path(__file__).resolve().parents[5]
 workspace=str(root/'runs/native-task-fixture') if kind=='local' else '/lus/flare/projects/BioReason-Aurora-Test/chian/runs/native-task-fixture'
 resource=({'kind':'local','workspace':workspace,'policy':{'memory_bytes':5368709120,'scratch_bytes':1073741824}}
  if kind=='local' else {'kind':'pbs_ssh','workspace':workspace,'ssh_argv':['ssh','-o','BatchMode=yes','aurora'],
   'python_executable':'/usr/bin/python3','account':'BioReason-Aurora-Test','scheduler':{'kind':'pbs','required_resources':[]}})
 assignment={'version':'practical_assignment_v1','assignment_id':'original-native-assignment','resource_id':'selected-native',
 'resource_kind':kind,'workspace':workspace,'endpoint':'completed_job_outputs',
 'requested_job':{'argv':['original-analysis'],'environment':{}},
 'progress_requirements':[{'key':'outputs','credit':3,'predicate':{'kind':'requested_job_outputs','output_paths':[workspace+'/result']}}],
 'completion_keys':['outputs'],'initial_context':{'revision':0,'cwd':workspace,'environment':{}},'inventory_snapshot':{},'constraints':{}}
 return kind,resource,assignment
@contextmanager
def actual(home,directory):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
 with patch('subprocess.Popen',forbidden),patch('socket.socket.connect',forbidden),patch('socket.socket.connect_ex',forbidden),patch.object(module('practical_execution_state'),'_now',return_value=TIME),patch.object(module('practical_execution_records'),'datetime',Clock):
  with module('state').Store(directory/'store') as store:
   store.create_problem(raw_sequence='MACDEFGH',molecule='protein')
   tools=controlled_tool_port(store)
   scope=store.validate_scope();kind,resource,assignment=configuration(home);role='launch_'+kind
   run_id='native-private-task-check';path=((role,'original-native'),)
   episode_id=module('method_loop.identities').EpisodeRef(run_id,path).episode_id
   request={'message':{'scope':plain(scope),'episode_assignment':deepcopy(assignment),'initial_report':{}}}
   context=module('episode_bindings').BindingContext(run_id,episode_id,role,path,scope,assignment,request)
   selected={'run_id':run_id,'episode_id':episode_id,'known_record_refs':[],'initial_known_record_refs':[]}
   services=SimpleNamespace(record_selection=lambda c:deepcopy(selected),reference_in_context=lambda *a:False)
   binding=module(home.replace('/','.')+'.episode').ExecutionEpisode(services,store=store,directory=directory/'native',
    run_id=run_id,resources={'selected-native':resource},initial_information={},tool_registry=tools,
    handoff_unit=2,acquired_record_unit=3,log_window_bytes=32,log_roles=[])
   registry=module('episode_bindings').EpisodeBindingRegistry((binding,));journal=module('episode_journal').Journal(store,run_id);runtime=module('runtime')
   execution_keys=[];received=[];projections=[]
   def credit(source):
    value=binding.credit_view(workflow.binding_context(source),selected);projections.append(deepcopy(value));return value
   async def execute(source,name,arguments,**kw):
    execution_keys.append(kw['operation_key']);return await binding.execute(context,name,arguments,kw['operation_key'])
   async def unchanged_score(source,index,result):return result
   workflow=SimpleNamespace(context=object(),grains={role:object()},inprocess_completion_order=None,
    receipts=None,structural_homology_evidence_binding=None,episode_bindings=registry,contract_information_profile=lambda s:None,
    specialist=lambda s:binding,binding_context=lambda s:replace(context,request=plain(s.request.as_record())),journal=journal,run_id=run_id,store=store,
    source_credit_view=credit,expose_assigned_job=lambda s:None,receive_tool_attributions=lambda *a,**kw:None,
    archive=SimpleNamespace(store=lambda value:value),launch_instructions=SimpleNamespace(materialize=lambda value:None),
    execution_binding=None,inprocess_replay=None,pending_work=lambda source:[],
    execute=execute,receive_native_outcome=lambda *a:None,
    receive_outcome=lambda source,selection,result,index:received.append((index,result['status'])),
    automatic_score_updates=unchanged_score,controller_value=lambda source,index,credit:{'index':index,'credit':credit})
   with patch.object(runtime.Episode,'identity',return_value=SimpleNamespace(episode_id=episode_id)),patch.object(runtime,'FeedbackEpisode',side_effect=lambda grain,key,source,*a,**kw:source):
    task=runtime.Workflow.build(workflow,role,'original-native','Execute the actual original native assignment.',plain(scope),episode_assignment=deepcopy(assignment))
   context=replace(context,request=plain(task.request.as_record()))
   task.checkpoint=lambda:None;projections.clear()
   yield SimpleNamespace(home=home,kind=kind,resource=resource,binding=binding,registry=registry,context=context,task=task,
    workflow=workflow,store=store,journal=journal,runtime=runtime,assignment=assignment,
    execution_keys=execution_keys,received=received,projections=projections,directory=directory)
def parent_admission(f):
 parent_home=f.home.rsplit('/',1)[0]
 roles={'structural_homology_evidence':'structural_homology_evidence','hpc_work_planning':'hpc','hpc_allocation_execution':'hpc_execution','execution_job_submission':'launch'}
 path=(('annotation','root'),*((roles[p],'selected-'+p) for p in parent_home.split('/')))
 parent_id=module('method_loop.identities').EpisodeRef(f.context.run_id,path).episode_id
 assignment={'version':'execution_launch_assignment_v1','requests':{'selected-native':deepcopy(f.assignment)},'immutable_input_versions':[],'constraints':{}}
 request={'message':{'scope':plain(f.context.scope),'episode_assignment':assignment}}
 parent=replace(f.context,episode_id=parent_id,role='launch',path=path,assignment=assignment,request=request)
 f.journal.save('runtime_episodes',{'episode_id':parent_id,'path':json.dumps(path),'request':json.dumps(request),'initial_credit':0,'state':'active','completion':None,'archive':None})
 return {'fixture_scope':'controlled full commissioning ancestry and saved parent request; no actual parent action execution claim',
  'parent_path':plain(path),'parent_id':parent_id,'result':caught(lambda:f.binding.prepare_assignment(parent,f.context.role,deepcopy(f.assignment),f.context.scope,f'{f.context.run_id}:{parent_id}:7'))}
def actions(f):
 transport=[];result=[]
 async def controlled(operations,state,tool_name,arguments,operation_key):
  transport.append({'tool':tool_name,'arguments':deepcopy(arguments),'operation_key':operation_key,'resource':deepcopy(operations.configuration)})
  return {'facts':{}},None
 with patch.object(module('terminal_execution').TerminalExecution,'execute',controlled):
  for index,(name,args) in enumerate((('exec_command',{'cmd':'original-analysis','workdir':f.assignment['workspace'],'env':{}}),('not-an-operation',{}))):
   selection={'kind':'tool','tool':name,'arguments':args}
   value=asyncio.run(f.task.execute(selection,index));replay=asyncio.run(f.task.execute(selection,index))
   row=f.journal.row('runtime_actions',f.context.episode_id,index)
   result.append({'selection':selection,'controller':value,'replay':replay,'outcome':json.loads(row['result']),'saved_credit':row['credit']})
 return result,transport
def observe(home,directory):
 with actual(home,directory) as f:
  action_rows,transport=actions(f)
  return {'constructor':'returned','task_type':type(f.task).__module__+'.'+type(f.task).__qualname__,
   'private_task':hasattr(f.binding,'decision_source_type'),'settings':f.binding.as_record(),
   'role':f.context.role,'assignment':deepcopy(f.assignment),'parent_admission':parent_admission(f),
   'allowed_actions':list(f.binding.permitted_common_actions(f.context)),'allowed_children':list(f.binding.allowed_children(f.context,{})),
   'catalog':f.binding.catalog(f.context),'actions':action_rows,'transport':transport,
   'terminal_estimator':f.binding._delegate(f.context).practical_estimator(f.context).as_record(),
   'execution_keys':f.execution_keys,'received':f.received,'projections':f.projections}
class NativeTaskBehavior:
    @pytest.fixture
    def actual_task(self,tmp_path):
        with actual(self.home,tmp_path) as value: yield value

    def test_actual_runtime_private_task_selection(self,actual_task):
        f=actual_task
        assert type(f.task) is getattr(f.binding,'decision_source_type',f.runtime.DecisionSource)
        if hasattr(f.binding,'decision_source_type'):
            assert not isinstance(f.task,f.runtime.DecisionSource)

    @pytest.mark.parametrize('status',['failed','unavailable'])
    def test_original_returned_failure_progress(self,actual_task,status):
        f=actual_task
        async def fail(source,name,arguments,**kw):
            f.execution_keys.append(kw['operation_key']); return {'status':status,'record_refs':[],'changed_record_refs':[],'feedback':{'code':'controlled_return'}}
        f.workflow.execute=fail; action={'kind':'tool','tool':'exec_command','arguments':{}}
        assert asyncio.run(f.task.execute(action,3))=={'index':3,'credit':0}
        assert asyncio.run(f.task.execute(action,3))=={'index':3,'credit':0}
        assert f.received==[(3,status)] and len(f.projections)==1 and len(f.execution_keys)==1

    @pytest.mark.parametrize('state',['unfinished','completed'])
    def test_original_saved_reason_execution_and_replay(self,actual_task,state):
        f=actual_task; action={'kind':'reason','commit':{'interpretation_accounts':[]}}
        result={'status':'completed','record_refs':[],'changed_record_refs':[],'result':{'fixture':'historical reason'}}
        complete=state=='completed'; calls=[]
        f.journal.save('runtime_actions',{'episode_id':f.context.episode_id,'decision_index':11,'action':json.dumps(action),
            'result':json.dumps(result) if complete else None,'credit':0 if complete else None})
        def commit(payload,scope,key,**kw): calls.append((payload,plain(scope),key,kw)); return deepcopy(result)
        f.workflow.execute=forbidden
        with patch.object(f.store,'commit_reasoning',side_effect=commit):
            assert asyncio.run(f.task.execute(action,11))=={'index':11,'credit':0}
            assert asyncio.run(f.task.execute(action,11))=={'index':11,'credit':0}
        assert calls==([] if complete else [(action['commit'],plain(f.context.scope),f'{f.context.run_id}:{f.context.episode_id}:11',{})])
        assert f.received==([] if complete else [(11,'completed')]) and len(f.projections)==(0 if complete else 1)
        assert json.loads(f.journal.row('runtime_actions',f.context.episode_id,11)['action'])==action

    def test_selected_wait_preserves_prior_credit(self,actual_task):
        f=actual_task; calls=[]
        async def wait(source,condition,index):
            calls.append((condition,index)); return {'status':'completed','record_refs':[],'changed_record_refs':[]}
        f.workflow.perform_selected_wait=wait; f.workflow.last_observed_credit=lambda source:2.
        action={'kind':'wait','condition':{'original':'condition'}}
        assert asyncio.run(f.task.execute(action,4))=={'index':4,'credit':2.}
        assert asyncio.run(f.task.execute(action,4))=={'index':4,'credit':2.}
        assert calls==[(action['condition'],4)] and not f.projections and f.received==[(4,'completed')]

    def test_original_ready_child_precedes_decision(self,actual_task):
        f=actual_task; child=object(); paths=[]
        f.task._execution_context=SimpleNamespace(_ready_owned_child=lambda path:paths.append(path) or child)
        assert asyncio.run(f.task.next(SimpleNamespace(units_consumed=0))) is child
        assert paths==[f.task.path] and f.task.calls==0

    def test_original_yield_opt_in_error_identity(self,actual_task):
        with pytest.raises(ValueError,match='^execution_private_yield_binding_not_enabled$'):
            actual_task.binding.yield_controller(actual_task.context,0,'original-epoch')

    def presentation_state(self,f):
        return {'goal':{'objective':'Execute the actual selected native assignment.'},'scope':plain(f.context.scope),
            'execution_assignment':deepcopy(f.assignment),'selected_execution_task':{'version':'selected_execution_task_v1',
                'scientific_question':'Interpret the actual assigned protein-structure operation and its retained inputs.',
                'selected_tool_info':[],'requests':[{'resource_id':'selected-native','resource_kind':f.kind,
                    'endpoint':'usable_handoff','resource':deepcopy(f.resource),'job':deepcopy(f.assignment)}]}}

    @pytest.mark.parametrize('scenario',['minimal','unrecognized-bootstrap','selected-full','selected-bootstrap',
        'selected-lookup','hpc-override','lost-task-update','science-override','missing-base-update'])
    def test_actual_provider_frame_priority_and_fallback(self,actual_task,scenario):
        f=actual_task; providers=module('providers'); frames=module('decision_context'); state=self.presentation_state(f)
        a=object.__new__(providers._SessionConnection); b=object.__new__(providers._SessionConnection)
        a.scientific_prompt_states={}; b.scientific_prompt_states={}; key=(f.context.episode_id,'REASONING')
        if scenario=='minimal': context={}
        elif scenario=='unrecognized-bootstrap': context=frames.state_frame({})
        elif scenario=='selected-full': context=state
        elif scenario=='selected-bootstrap': context=frames.state_frame(state)
        elif scenario in {'selected-lookup','lost-task-update'}:
            a.scientific_prompt_states[key]=deepcopy(state); b.scientific_prompt_states[key]=deepcopy(state)
            context=({'version':frames.VERSION,'kind':'decision_lookup_result','result':{'original':'lookup'}}
                if scenario=='selected-lookup' else frames.state_frame({'unrecognized':'original'},state))
        elif scenario=='science-override':
            context={**state,'structural_homology_evidence':{'evidence_axis':{'instruction_status':'published_investigation_instructions',
                'investigation_instructions':'Original supplied protein-structure investigation instruction.'}}}
        elif scenario=='missing-base-update':
            context=frames.state_frame(state,{})
        else: context={**state,'hpc_commission':{'objective':'Preserve the original HPC allocation.'}}
        instructions=f.binding.instructions(f.context)+'\n'+frames.INSTRUCTIONS
        calls=[]
        async def complete(episode,role,text,observed,schema,**kwargs):
            calls.append(kwargs)
            return b._presentation(episode,role,text,observed,**kwargs)
        f.workflow.provider=SimpleNamespace(complete=complete,complete_with_presentation=complete)
        async def actual_dispatch():
            if hasattr(f.task,'complete_decision'):
                return await f.task.complete_decision(instructions,deepcopy(context),{})
            return await f.workflow.provider.complete(*key,instructions,deepcopy(context),{})
        if scenario=='missing-base-update':
            with pytest.raises(TypeError,match='^previous_model_state_requires_object$') as original:
                a._presentation(*key,instructions,deepcopy(context))
            with pytest.raises(TypeError,match='^previous_model_state_requires_object$') as proposed:
                asyncio.run(actual_dispatch())
            assert type(original.value) is type(proposed.value) is TypeError
            assert str(original.value)==str(proposed.value)=='previous_model_state_requires_object'
        else:
            expected=a._presentation(*key,instructions,deepcopy(context))
            observed=asyncio.run(actual_dispatch())
            assert observed==expected
            if scenario in {'minimal','unrecognized-bootstrap'}: assert observed==(json.dumps(context,allow_nan=False),instructions)
            if scenario=='hpc-override': assert observed[0]==module('library.hpc_prompt').render_hpc_prompt(context,instructions)
            if scenario=='selected-full': assert observed[0]==module('structural_homology_evidence_prompt').render_selected_execution_prompt(context,instructions)
        assert b.scientific_prompt_states==a.scientific_prompt_states
        selected_private=scenario=='selected-full' and hasattr(f.binding,'decision_source_type')
        assert calls==([{'prompt_renderer':f.binding.decision_prompt_renderer}] if selected_private else [{}])

    @pytest.mark.parametrize('declared',[False,True],ids=['legacy','declared'])
    def test_original_pending_decision_and_completed_replay(self,actual_task,declared):
        f=actual_task; state=self.presentation_state(f); providers=module('providers')
        f.workflow.is_job_source=lambda s:False
        f.workflow.permits_common_action=lambda s,action:action in f.binding.permitted_common_actions(f.context)
        f.workflow.native_event_information=None; f.workflow.decision_protocol=None
        f.workflow.services=SimpleNamespace(instructions=module('runtime_prompt').instructions)
        schema=f.runtime._object({'selection':f.runtime._object({'kind':{'const':'tool'},'tool':{'const':'exec_command'},'arguments':f.runtime._object({})}),
            'report_update':f.runtime._object({})})
        response={'selection':{'kind':'tool','tool':'exec_command','arguments':{}},'report_update':{}}
        f.journal.save('runtime_model_calls',{'episode_id':f.context.episode_id,'call_index':0,'purpose':'decision',
            'request':json.dumps({'context':state,'schema':schema,'assignment_transport':{'version':f.runtime._ASSIGNMENT_TRANSPORT,
                'action_schema_sha256':f.runtime._digest(schema)}}),'response':None})
        session=object.__new__(providers._SessionConnection); session.scientific_prompt_states={}; calls=[]
        async def complete(episode,role,instructions,context,output_schema,**kw):
            calls.append((session._presentation(episode,role,instructions,context,**kw),kw,(episode,role,instructions,deepcopy(context))))
            return deepcopy(response)
        f.workflow.provider=SimpleNamespace(has_session=lambda *a:True,complete=complete)
        if declared: f.workflow.provider.complete_with_presentation=complete
        assert asyncio.run(f.task.call({},schema))[0]==response and len(calls)==1
        assert calls[0][1]==({'prompt_renderer':f.binding.decision_prompt_renderer}
            if declared and hasattr(f.binding,'decision_source_type') else {})
        original=object.__new__(providers._SessionConnection); original.scientific_prompt_states={}
        assert calls[0][0]==original._presentation(*calls[0][2])
        f.task.calls=0
        assert asyncio.run(f.task.call({},schema))[0]==response and len(calls)==1
        assert f.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==0

    @pytest.mark.parametrize('mode',['returned','raised'])
    def test_original_instruction_service_callback(self,actual_task,mode):
        f=actual_task; context=object(); marker=object(); error=RuntimeError('original callback exception'); calls=[]
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

    def test_default_instruction_service_uses_private_composer(self,actual_task):
        f=actual_task; context={}; calls=[]; prompt=module('runtime_prompt')
        f.workflow.is_job_source=lambda source:False
        f.workflow.permits_common_action=lambda source,kind:kind in f.binding.permitted_common_actions(f.context)
        f.workflow.native_event_information=None; f.workflow.decision_protocol=None
        f.workflow.services=module('episode_services').WorkflowServices(f.workflow)
        original=getattr(type(f.task),'instruction_composer',None)
        if hasattr(f.binding,'decision_source_type'):
            assert original is module(self.home.replace('/','.')+'.instructions').instructions
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
        assert calls==[(f.task,context)] and f.projections==f.execution_keys==f.received==[]

    def test_default_instruction_service_nonparticipant_fallback(self,actual_task):
        f=actual_task; context=object(); marker=object(); calls=[]
        source=SimpleNamespace(instruction_composer=forbidden)
        service=module('episode_services').WorkflowServices(f.workflow)
        with patch.object(module('runtime_prompt'),'instructions',side_effect=lambda owner,state:calls.append((owner,state)) or marker):
            assert service.instructions(source,context) is marker
        assert calls==[(source,context)]


    def test_actual_terminal_outcomes_and_replay(self,actual_task):
        f=actual_task;rows,transport=actions(f)
        assert [row['outcome']['status'] for row in rows]==['completed','invalid']
        assert all(row['controller']==row['replay']=={'index':i,'credit':0} for i,row in enumerate(rows))
        assert len(transport)==1 and transport[0]['resource']==f.resource
        assert f.received==[(0,'completed'),(1,'invalid')] and len(f.projections)==2
        assert f.execution_keys==[f'{f.context.run_id}:{f.context.episode_id}:{i}' for i in (0,1)]
        state=f.binding.state(f.context);assert len(state.receipts())==1
        assert state.receipts()[0]==rows[0]['outcome']['result']
        snapshot=(deepcopy(state.receipts()),deepcopy(state.context()),deepcopy(state.credit_view()))
        f.binding._delegate(f.context)._states.clear()
        restored=f.binding.state(f.context)
        assert restored is not state and (restored.receipts(),restored.context(),restored.credit_view())==snapshot

    def test_actual_parent_admission_and_registered_identity(self,actual_task):
        f=actual_task;result=parent_admission(f)
        assert f.registry.for_path(f.context.path) is f.binding
        assert f.binding.binding_path==self.home and f.binding.commissioning_parent==self.home.rsplit('/',1)[0]
        assert f.binding.permitted_common_actions(f.context)==('tool',)
        assert f.binding.child_roles(f.context.role)==() and f.binding.allowed_children(f.context,{})==()
        if 'hpc_work_planning' in self.home:assert result['result']=={'status':'returned','value':f.assignment}
        else:assert result['result']=={'status':'raised','type':'builtins.ValueError','message':'unknown_execution_episode_role'}

    def test_actual_a102_native_resource_and_scientific_authority(self,actual_task):
        f=actual_task
        assert type(f.binding.native_protein_structure_results) is module('native_protein_structure_results').NativeProteinStructureResults
        assert type(f.binding.native_protein_structure_returns) is module('native_protein_structure_returns').NativeProteinStructureReturns
        assert f.binding.native_protein_structure_results.owner is f.binding
        assert f.binding.native_protein_structure_returns.owner is f.binding
        assert f.binding.native_protein_structure_returns.results is f.binding.native_protein_structure_results
        operations=f.binding._delegate(f.context)._operations(f.kind)
        assert operations.artifact_selector is module('terminal_scientific_evidence').terminal_artifact_paths
        def construct(resource):
            return type(f.binding)(f.binding.services,store=f.store,directory=f.directory/'rejected-resource',
                run_id=f.context.run_id,resources={'selected-native':resource},initial_information={},
                tool_registry=f.binding.tool_registry,handoff_unit=2,acquired_record_unit=3,log_window_bytes=32,log_roles=[])
        with pytest.raises(ValueError,match='^a102_execution_foreign_native_binding:native_foreign$'):
            construct({**f.resource,'native_foreign':[]})
        if f.kind=='hpc':
            with pytest.raises(ValueError,match='^native_protein_structure_resource_execution_binding_unfinished:hpc$'):
                construct({**f.resource,'native_protein_structure':[]})
        assert f.projections==f.execution_keys==f.received==[]

    def test_original_terminal_state_estimator_identity(self,actual_task):
        f=actual_task;delegate=f.binding._delegate(f.context);estimator=delegate.practical_estimator(f.context)
        assert type(estimator) is module('practical_yield').PracticalYieldEstimator
        assert type(delegate.state(f.context)) is module('practical_execution_state').PracticalState

    def test_original_private_yield_profile_is_required(self,actual_task):
        f=actual_task;f.binding.private_yield_binding=True
        key=f.context.role+':'+f.binding._request_yield_class(f.assignment)
        with pytest.raises(ValueError) as error:f.binding.yield_controller(f.context,0,'original-epoch')
        assert str(error.value)=='execution_original_task_yield_profile_required:'+key

    @pytest.mark.parametrize('order',['episode-first','runtime-first'])
    def test_cold_import_order(self,tmp_path,order):
        import os
        import subprocess
        import sys
        from gene_annotation_episode.workflow_budget import active_budget
        budget=active_budget();directory=Path(budget['run_directory']).resolve()
        assert tmp_path.resolve().is_relative_to(directory)
        script="import importlib,json; names="+repr([PACKAGE+'.'+self.home.replace('/','.')+'.episode',PACKAGE+'.runtime'])+"; "
        script+="names=names if "+repr(order)+"=='episode-first' else names[::-1]; modules=[importlib.import_module(n) for n in names]; "
        script+="owner=importlib.import_module("+repr(PACKAGE+'.'+self.home.replace('/','.')+'.episode')+").ExecutionEpisode; print(json.dumps({'binding_path':owner.binding_path,'task':getattr(owner,'decision_source_type',None) is not None}))"
        environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(tmp_path)}
        result=subprocess.run([sys.executable,'-B','-c',script],cwd=directory,env=environment,capture_output=True,text=True)
        (tmp_path/'cold.stdout').write_text(result.stdout);(tmp_path/'cold.stderr').write_text(result.stderr)
        assert result.returncode==0,result.stderr
        row=json.loads(result.stdout);assert row['binding_path']==self.home
        assert row['task']==hasattr(module(self.home.replace('/','.')+'.episode').ExecutionEpisode,'decision_source_type')

    def test_original_fresh_context_snapshot_and_invalid_outcome(self, actual_task, monkeypatch):
        """The original task.next boundary, independent of where context is built."""
        f = actual_task
        task = f.task
        order, observed = [], []
        unit = object()
        outcome = {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
            'feedback': {'code': 'original_controlled_invalid'}}
        task.last_outcome, task.last_outcome_index = deepcopy(outcome), 2
        task.feedback = deepcopy(outcome['feedback'])
        monkeypatch.setattr(f.binding, 'decision_context',
            lambda context, view: {'execution_assignment': deepcopy(f.assignment)})
        original_snapshot = f.store.read_snapshot
        @contextmanager
        def snapshot():
            order.append('snapshot_enter')
            with original_snapshot():
                yield
            order.append('snapshot_exit')
        monkeypatch.setattr(f.store, 'read_snapshot', snapshot)
        def credit(source):
            order.append('credit')
            return {'credit': 2.5}
        def model_inputs(value, **kwargs):
            order.append('model_inputs')
            return value
        def action_schema(source):
            order.append('action_schema')
            return {}
        workflow = SimpleNamespace(run_id=f.context.run_id, inprocess_replay=None, execution_binding=None,
            journal=f.journal, store=f.store, working_state=lambda source: {'records': []},
            local_outcome_preview=lambda value, **kwargs: deepcopy(value), source_credit_view=credit,
            receipt_projection=lambda source: False, source_credit_binding=lambda source: {'kind': 'operational'},
            pending_work=lambda source: [], delivery_status=lambda episode: [], controller_binding={},
            catalog=lambda *args, **kwargs: [], knowledge=SimpleNamespace(context=lambda: {}),
            job_episode_options=lambda source: [], extra_report_sources=lambda source: {},
            specialist=lambda source: f.binding, binding_context=lambda source: f.context,
            tools=object(), action_schema=action_schema)
        workflow.is_scientific_source = f.runtime.Workflow.is_scientific_source.__get__(workflow)
        task.workflow = workflow
        async def call(context, schema):
            order.append('call')
            observed.append(deepcopy(context))
            return {}, 0, context, schema
        task.call = call
        task.apply_response = lambda *args: unit
        view = SimpleNamespace(units_consumed=0, controller_state={}, child_reports=(), model_inputs=model_inputs)
        assert asyncio.run(task.next(view)) is unit
        assert order == ['snapshot_enter', 'credit', 'model_inputs', 'snapshot_exit', 'action_schema', 'call']
        assert observed[0]['goal'] == task.request.goal.as_record()
        assert observed[0]['scope'] == task.scope and observed[0]['current_credit'] == 2.5
        assert observed[0]['last_local_outcome'] == outcome and observed[0]['feedback'] == outcome['feedback']
        assert observed[0]['execution_assignment'] == f.assignment
        assert f.execution_keys == [] and f.received == []
