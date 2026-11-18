"""Actual Launch bindings/Store/action Journal with controlled loop/transport ports.

No provider/native process or network call. Child receipt tests are controlled
saved-counterpart routing, not native custody or complete restoration proof.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import asyncio
import hashlib
import json
import pytest
PACKAGE='gene_annotation_episode.episodic_workflow.root.a103'
HOMES=('execution_job_submission','hpc_work_planning/execution_job_submission',
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission','gene_context_evidence/execution_job_submission',
    'gene_context_evidence/hpc_work_planning/execution_job_submission',
    'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission')
CHILDREN={'launch_api':'api_job_execution','launch_local':'local_job_execution','launch_hpc':'hpc_job_execution'}
def module(name): return import_module(PACKAGE+'.'+name)
def forbidden(*args,**kwargs): raise AssertionError('Launch task check cannot execute provider/native work')
def plain(value): return module('communication').plain(value)
def caught(call):
    try: return {'status':'returned','value':plain(call())}
    except Exception as error: return {'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,'message':str(error)}

@contextmanager
def actual(home,directory):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    with patch('subprocess.Popen',forbidden),patch('socket.socket.connect',forbidden),patch('socket.socket.connect_ex',forbidden):
        with module('state').Store(directory/'store') as store:
            store.create_problem(raw_sequence='MACDEFGH',molecule='protein')
            tools=module('tools').ToolRegistry(store,clients=SimpleNamespace(blast=forbidden))
            scope=store.validate_scope(); run_id='launch-private-task-check'; path=(('launch','original-portfolio'),)
            episode_id=module('method_loop.identities').EpisodeRef(run_id,path).episode_id
            api={'version':'api_service_assignment_v1','resource_id':'selected-api','service':'ncbi_blast',
                'request':{'subject_ref':store.targets()[0]['id'],'program':'blastp','database':'swissprot'},
                'endpoint':'usable_handoff','constraints':{}}
            assignment={'version':'execution_launch_assignment_v1','requests':{'selected-api':api},'immutable_input_versions':[],'constraints':{}}
            request={'message':{'scope':plain(scope),'episode_assignment':assignment,'initial_report':{}}}
            context=module('episode_bindings').BindingContext(run_id,episode_id,'launch',path,scope,assignment,request)
            selected={'run_id':run_id,'episode_id':episode_id,'known_record_refs':[],'initial_known_record_refs':[]}
            services=SimpleNamespace(record_selection=lambda c:deepcopy(selected),reference_in_context=lambda *a:False)
            configuration=dict(store=store,run_id=run_id,resources={'selected-api':{'kind':'api','service':'ncbi_blast'}},
                initial_information={},tool_registry=tools,handoff_unit=2,acquired_record_unit=3,log_window_bytes=32,log_roles=[])
            binding=module(home.replace('/','.')+'.episode').ExecutionEpisode(services,directory=directory/'launch',**configuration)
            children={role:module((home+'/'+child).replace('/','.')+'.episode').ExecutionEpisode(services,
                directory=directory/child,**configuration) for role,child in CHILDREN.items()}
            registry=module('episode_bindings').EpisodeBindingRegistry((binding,*children.values()))
            journal=module('episode_journal').Journal(store,run_id); runtime=module('runtime')
            execution_keys=[]; received=[]; projections=[]
            def credit(source):
                value=binding.credit_view(context,selected); projections.append(deepcopy(value)); return value
            async def execute(source,name,arguments,**kw):
                execution_keys.append(kw['operation_key']); return await binding.execute(context,name,arguments,kw['operation_key'])
            async def unchanged_score(source,index,result): return result
            workflow=SimpleNamespace(context=object(),grains={'launch':object()},inprocess_completion_order=None,
                receipts=None,gene_context_evidence_binding=None,episode_bindings=registry,contract_information_profile=lambda s:None,
                specialist=lambda s:binding,binding_context=lambda s:context,journal=journal,run_id=run_id,store=store,
                source_credit_view=credit,expose_assigned_job=lambda s:None,receive_tool_attributions=lambda *a,**kw:None,
                archive=SimpleNamespace(store=lambda value:value),launch_instructions=SimpleNamespace(materialize=lambda value:None),
                execution_binding=None,inprocess_replay=None,pending_work=lambda source:[],
                execute=execute,receive_native_outcome=lambda *a:None,
                receive_outcome=lambda source,selection,result,index:received.append((index,result['status'])),
                automatic_score_updates=unchanged_score,controller_value=lambda source,index,credit:{'index':index,'credit':credit})
            workflow.legacy_parent_for_path=runtime.Workflow.legacy_parent_for_path.__get__(workflow)
            with patch.object(runtime.Episode,'identity',return_value=SimpleNamespace(episode_id=episode_id)),patch.object(runtime,'FeedbackEpisode',side_effect=lambda grain,key,source,*a,**kw:source):
                task=runtime.Workflow.build(workflow,'launch','original-portfolio','Commission the original permitted execution request.',plain(scope),episode_assignment=deepcopy(assignment))
            task.checkpoint=lambda:None; projections.clear()
            yield SimpleNamespace(binding=binding,children=children,registry=registry,context=context,task=task,
                workflow=workflow,store=store,journal=journal,runtime=runtime,assignment=assignment,api=api,
                execution_keys=execution_keys,received=received,projections=projections,directory=directory)

def child_admission(f):
    roles={'gene_context_evidence':'gene_context_evidence','hpc_work_planning':'hpc',
        'hpc_allocation_execution':'hpc_execution','execution_job_submission':'launch'}
    path=(('annotation','root'),*((roles[part],'selected-'+part) for part in f.binding.binding_path.split('/')))
    parent_id=module('method_loop.identities').EpisodeRef(f.context.run_id,path).episode_id
    request={'message':{'scope':plain(f.context.scope),'episode_assignment':deepcopy(f.assignment)}}
    parent=replace(f.context,episode_id=parent_id,path=path,assignment=deepcopy(f.assignment),request=request)
    f.journal.save('runtime_episodes',{'episode_id':parent_id,'path':json.dumps(path),'request':json.dumps(request),
        'initial_credit':0,'state':'active','completion':None,'archive':None})
    return {'fixture_scope':'synthetic exact commissioning role ancestry and saved parent Journal identity; no native custody claimed',
        'parent_id':parent_id,'parent_path':plain(path),'result':caught(lambda:f.children['launch_api'].prepare_assignment(
            parent,'launch_api',f.api,f.context.scope,f'{f.context.run_id}:{parent_id}:7'))}

def observe(home,directory):
    with actual(home,directory) as f:
        row={'constructor':'returned','task_type':type(f.task).__module__+'.'+type(f.task).__qualname__,
            'private_task':hasattr(f.binding,'decision_source_type'),'settings':f.binding.as_record(),
            'children':{role:child.binding_path for role,child in f.children.items()},
            'allowed_children':list(f.binding.allowed_children(f.context,{})),
            'child_admission':child_admission(f),'actions':[]}
        for index,name in enumerate(('execution.capabilities','execution.not-an-operation')):
            selection={'kind':'tool','tool':name,'arguments':{}}
            value=asyncio.run(f.task.execute(selection,index)); replay=asyncio.run(f.task.execute(selection,index))
            record=f.journal.row('runtime_actions',f.context.episode_id,index)
            row['actions'].append({'selection':selection,'controller':value,'replay':replay,
                'outcome':json.loads(record['result']),'saved_credit':record['credit']})
        row.update(execution_keys=f.execution_keys,received=f.received,projections=f.projections)
        return row


class LaunchTaskBehavior:
    @pytest.fixture
    def actual_task(self,tmp_path):
        with actual(self.home,tmp_path) as value: yield value

    def test_actual_runtime_private_task_selection(self,actual_task):
        f=actual_task
        assert type(f.task) is getattr(f.binding,'decision_source_type',f.runtime.DecisionSource)
        if hasattr(f.binding,'decision_source_type'):
            assert not isinstance(f.task,f.runtime.DecisionSource)

    def test_actual_capability_invalid_outcomes_and_replay(self,actual_task):
        f=actual_task
        for index,(name,status) in enumerate((('execution.capabilities','completed'),('execution.not-an-operation','invalid'))):
            action={'kind':'tool','tool':name,'arguments':{}}
            assert asyncio.run(f.task.execute(action,index))=={'index':index,'credit':0}
            assert asyncio.run(f.task.execute(action,index))=={'index':index,'credit':0}
            row=f.journal.row('runtime_actions',f.context.episode_id,index)
            assert json.loads(row['action'])==action and json.loads(row['result'])['status']==status
        assert f.execution_keys==[f'{f.context.run_id}:{f.context.episode_id}:{i}' for i in (0,1)]
        assert f.received==[(0,'completed'),(1,'invalid')] and len(f.projections)==2

    @pytest.mark.parametrize('status',['failed','unavailable'])
    def test_original_returned_failure_progress(self,actual_task,status):
        f=actual_task
        async def fail(source,name,arguments,**kw):
            f.execution_keys.append(kw['operation_key']); return {'status':status,'record_refs':[],'changed_record_refs':[],'feedback':{'code':'controlled_return'}}
        f.workflow.execute=fail; action={'kind':'tool','tool':'execution.capabilities','arguments':{}}
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

    def test_actual_child_registry_and_portfolio(self,actual_task):
        f=actual_task
        assert f.binding.child_roles('launch')==('launch_api','launch_local','launch_hpc')
        assert f.binding.allowed_children(f.context,{})==('launch_api',)
        for role,child in f.children.items():
            assert f.registry.for_child(f.context.path,role) is child
            assert child.binding_path==self.home+'/'+CHILDREN[role] and child.commissioning_parent==self.home

    def test_actual_api_child_admission_retains_inherited_contract(self,actual_task):
        f=actual_task; original=deepcopy(f.api); observation=child_admission(f); outcome=observation['result']
        expected_roles=['annotation',*({'gene_context_evidence':'gene_context_evidence','hpc_work_planning':'hpc',
            'hpc_allocation_execution':'hpc_execution','execution_job_submission':'launch'}[part] for part in self.home.split('/'))]
        assert [role for role,key in observation['parent_path']]==expected_roles
        assert observation['parent_id']==module('method_loop.identities').EpisodeRef(f.context.run_id,observation['parent_path']).episode_id
        retained=f.store.db.execute('SELECT path,request FROM runtime_episodes WHERE episode_id=?',(observation['parent_id'],)).fetchone()
        assert json.loads(retained['path'])==observation['parent_path']
        assert json.loads(retained['request'])['message']=={'scope':plain(f.context.scope),'episode_assignment':f.assignment}
        if 'hpc_work_planning' in self.home:
            assert outcome=={'status':'returned','value':original}
        else:
            assert outcome=={'status':'raised','type':'builtins.ValueError','message':'unknown_execution_episode_role'}
        assert f.api==original

    @pytest.mark.parametrize('ancestry,knowledge',[('ordinary',False),('ordinary',True),('hpc',False),('hpc',True)],ids=['ordinary','ordinary-library','hpc','hpc-library'])
    def test_original_ancestry_actions_and_instruction_composition(self,actual_task,ancestry,knowledge):
        f=actual_task; path=f.context.path if ancestry=='ordinary' else (('hpc','original-owner'),*f.context.path)
        context=replace(f.context,path=path,episode_id=module('method_loop.identities').EpisodeRef(f.context.run_id,path).episode_id)
        f.workflow.binding_context=lambda source:context
        f.workflow.is_job_source=lambda source:False
        f.workflow.permits_common_action=lambda source,kind:kind in f.binding.permitted_common_actions(context)
        f.workflow.native_event_information=None; f.workflow.decision_protocol=None
        f.workflow.knowledge=SimpleNamespace(instructions='Selected knowledge.'); f.workflow.services=SimpleNamespace(instructions=module('runtime_prompt').instructions)
        actions=f.binding.permitted_common_actions(context)
        assert actions==(('tool','reason','child','wait','redeliver_report') if ancestry=='ordinary' else ('tool','child','redeliver_report'))
        state={'tool_knowledge':{}} if knowledge else {}
        assert f.task.instructions(state)==module('runtime_prompt').instructions(f.task,state)
        assert f.task.instructions(state).startswith('Choose which permitted concrete execution request')
        assert (module('runtime_prompt').REASONING_COMMIT_REQUIREMENT in f.task.instructions(state))==(ancestry=='ordinary')

    @pytest.mark.parametrize('role,redelivery',[('launch_api',False),('launch_api',True),
        ('launch_local',False),('launch_local',True),('launch_hpc',False),('launch_hpc',True)],
        ids=['api-initial','api-redelivery','local-initial','local-redelivery','hpc-initial','hpc-redelivery'])
    def test_actual_saved_child_counterpart_routes_progress(self,actual_task,role,redelivery):
        f=actual_task; values=[]
        f.journal.save('runtime_actions',{'episode_id':f.context.episode_id,'decision_index':7,
            'action':json.dumps({'kind':'episode_child','role':role,'assignment':{}}),'result':None,'credit':None})
        f.workflow.is_job_source=lambda source:False
        f.workflow.progress_provider=SimpleNamespace(receive_form=lambda *a:values.append(a))
        f.workflow._receive_form=lambda *a,**kw:f.runtime.Workflow._receive_form(f.workflow,*a,**kw)
        form={'progress':'original controlled return'}; schema={'type':'object','properties':{},'additionalProperties':True}
        assert f.runtime.Workflow.receive_form(f.workflow,f.task,form,schema,7,redelivery=redelivery)==[]
        assert values==[(f.context.episode_id,form,schema,f.task.scope,f'{f.context.run_id}:{f.context.episode_id}:7:typed_form')]
        callback=f.binding.child_report_receiver(role)
        if not (hasattr(f.binding,'decision_source_type') or role=='launch_api'): assert callback is None
        assert f.binding.child_report_receiver('unrelated') is None

    def test_original_yield_opt_in_error_identity(self,actual_task):
        with pytest.raises(ValueError,match='^execution_private_yield_binding_not_enabled$'):
            actual_task.binding.yield_controller(actual_task.context,0,'original-epoch')

    def presentation_state(self,f):
        return {'goal':{'objective':'Commission the fixed original portfolio.'},'scope':plain(f.context.scope),
            'execution_assignment':deepcopy(f.assignment),'selected_execution_task':{'version':'selected_execution_task_v1',
                'scientific_question':'Interpret the actual assigned homologous sequence comparison.',
                'selected_tool_info':[],'requests':[{'resource_id':'selected-api','resource_kind':'api',
                    'endpoint':'usable_handoff','resource':{'service':'ncbi_blast'},'job':deepcopy(f.api)}]}}

    @pytest.mark.parametrize('scenario',['minimal','unrecognized-bootstrap','selected-full','selected-bootstrap',
        'selected-lookup','hpc-override','lost-task-update'])
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
        else: context={**state,'hpc_commission':{'objective':'Preserve the original HPC allocation.'}}
        instructions=f.binding.instructions(f.context)+'\n'+frames.INSTRUCTIONS
        expected=a._presentation(*key,instructions,deepcopy(context))
        callback=getattr(f.binding,'decision_prompt_renderer',None)
        if callback is not None:
            b._declared_presentation=forbidden
            observed=b._presentation(*key,instructions,deepcopy(context),prompt_renderer=callback)
        else: observed=b._presentation(*key,instructions,deepcopy(context))
        assert observed==expected and b.scientific_prompt_states==a.scientific_prompt_states
        if scenario in {'minimal','unrecognized-bootstrap'}: assert observed==(json.dumps(context,allow_nan=False),instructions)
        if scenario=='hpc-override': assert observed[0]==module('library.hpc_prompt').render_hpc_prompt(context,instructions)
        if scenario=='selected-full': assert observed[0]==module('gene_context_evidence_prompt').render_selected_execution_prompt(context,instructions)

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
