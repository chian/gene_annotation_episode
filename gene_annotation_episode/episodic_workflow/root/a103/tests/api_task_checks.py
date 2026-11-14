"""Actual API bindings/Store/action journal with controlled iterator/provider ports.

NCBI BLAST local preparation and invalid selections never contact a provider.
These checks prove task connections, not remote service custody or autonomy.
"""
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest

PACKAGE='gene_annotation_episode.episodic_workflow.root.a103'
HOMES=tuple(parent+'/api_job_execution' for parent in (
    'execution_job_submission','hpc_work_planning/execution_job_submission',
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission',
    'scientific_process/execution_job_submission','scientific_process/hpc_work_planning/execution_job_submission',
    'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission'))
def module(name): return import_module(PACKAGE+'.'+name)
def forbidden(*args,**kwargs): raise AssertionError('API task check cannot contact a provider or start a subprocess')
def caught(call):
    try: return {'status':'returned','value':module('communication').plain(call())}
    except Exception as error: return {'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,'message':str(error)}

@contextmanager
def actual(home,directory):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    with patch('subprocess.Popen',forbidden), patch('socket.socket.connect',forbidden), patch('socket.socket.connect_ex',forbidden):
        with module('state').Store(directory/'store') as store:
            store.create_problem(raw_sequence='MACDEFGH',molecule='protein')
            clients=SimpleNamespace(blast=forbidden)
            tools=module('tools').ToolRegistry(store,clients=clients)
            scope=store.validate_scope()
            assignment={'version':'api_service_assignment_v1','resource_id':'selected-api','service':'ncbi_blast',
                'request':{'subject_ref':store.targets()[0]['id'],'program':'blastp','database':'swissprot'},
                'endpoint':'usable_handoff','constraints':{}}
            run_id='api-private-task-check'; path=(('launch_api','selected-original-work'),)
            episode_id=module('method_loop.identities').EpisodeRef(run_id,path).episode_id
            request={'message':{'scope':module('communication').plain(scope),'episode_assignment':assignment,'initial_report':{}}}
            context=module('episode_bindings').BindingContext(run_id,episode_id,'launch_api',path,scope,assignment,request)
            selection={'run_id':run_id,'episode_id':episode_id,'known_record_refs':[],'initial_known_record_refs':[]}
            services=SimpleNamespace(record_selection=lambda c:deepcopy(selection),reference_in_context=lambda *args:False)
            cls=module(home.replace('/','.')+'.episode').ExecutionEpisode
            binding=cls(services,store=store,directory=directory/'work',run_id=run_id,
                resources={'selected-api':{'kind':'api','service':'ncbi_blast'}},initial_information={},
                tool_registry=tools,handoff_unit=2,acquired_record_unit=3,log_window_bytes=32,log_roles=[])
            runtime=module('runtime'); journal=module('episode_journal').Journal(store,run_id)
            registry=module('episode_bindings').EpisodeBindingRegistry((binding,))
            execution_keys=[]; received=[]; projections=[]
            def credit(source):
                result=binding.credit_view(context,selection); projections.append(deepcopy(result)); return result
            async def execute(source,name,arguments,**kw):
                execution_keys.append(kw['operation_key'])
                return await binding.execute(context,name,arguments,kw['operation_key'])
            async def score(source,index,result):
                assert not hasattr(binding,'automatic_score_judgments'); return result
            workflow=SimpleNamespace(context=object(),grains={'launch_api':object()},
                inprocess_completion_order=None,receipts=None,scientific_process_binding=None,
                episode_bindings=registry,contract_information_profile=lambda source:None,
                specialist=lambda source:binding,binding_context=lambda source:context,
                journal=journal,run_id=run_id,store=store,source_credit_view=credit,
                expose_assigned_job=lambda source:None,receive_tool_attributions=lambda *args,**kwargs:None,
                archive=SimpleNamespace(store=lambda value:value),launch_instructions=SimpleNamespace(materialize=lambda value:None),
                execution_binding=None,inprocess_replay=None,wait_inputs_version=None,completed_action_inputs_version=None,
                execute=execute,receive_native_outcome=lambda *args:None,
                receive_outcome=lambda source,selected,result,index:received.append((index,result['status'])),
                automatic_score_updates=score,controller_value=lambda source,index,credit:{'index':index,'credit':credit})
            workflow.legacy_parent_for_path=runtime.Workflow.legacy_parent_for_path.__get__(workflow)
            with patch.object(runtime.Episode,'identity',return_value=SimpleNamespace(episode_id=episode_id)), \
                    patch.object(runtime,'FeedbackEpisode',side_effect=lambda grain,key,source,*a,**kw:source):
                task=runtime.Workflow.build(workflow,'launch_api','selected-original-work',
                    'Prepare the fixed BLAST request and preserve its original handoff.',module('communication').plain(scope),
                    episode_assignment=deepcopy(assignment))
            # Checkpoint mechanics are source-audited separately. This harness
            # retains actual action rows but does not claim full restoration.
            task.checkpoint=lambda:None
            projections.clear()
            yield SimpleNamespace(binding=binding,context=context,task=task,workflow=workflow,store=store,
                journal=journal,assignment=assignment,selection=selection,execution_keys=execution_keys,
                received=received,projections=projections,runtime=runtime,directory=directory)


def parent_admission(f):
    launch={'version':'execution_launch_assignment_v1','requests':{'selected-api':deepcopy(f.assignment)},
        'immutable_input_versions':[],'constraints':{}}
    roles={'scientific_process':'scientific_process','hpc_work_planning':'hpc',
        'hpc_allocation_execution':'hpc_execution','execution_job_submission':'launch'}
    home=f.binding.binding_path.rsplit('/',1)[0]
    path=(('annotation','root'),*( (roles[part],'selected-'+part) for part in home.split('/') ))
    parent_id=module('method_loop.identities').EpisodeRef(f.context.run_id,path).episode_id
    request={'message':{'scope':module('communication').plain(f.context.scope),'episode_assignment':launch}}
    parent=replace(f.context,episode_id=parent_id,role='launch',path=path,assignment=launch,request=request)
    f.journal.save('runtime_episodes',{'episode_id':parent_id,'path':json.dumps(path),
        'request':json.dumps(request),'initial_credit':0,'state':'active','completion':None,'archive':None})
    return {'fixture_scope':'synthetic parent assignment with exact commissioning role ancestry and EpisodeRef identity; no native custody claimed',
        'parent_id':parent_id,'parent_path':module('communication').plain(path),
        'result':caught(lambda:f.binding.prepare_assignment(parent,'launch_api',f.assignment,f.context.scope,
            f'{f.context.run_id}:{parent.episode_id}:0'))}


def observe(home,directory):
    with actual(home,directory) as f:
        result={'constructor':'returned','task_type':type(f.task).__module__+'.'+type(f.task).__qualname__,
            'private_task':hasattr(f.binding,'decision_source_type'),'parent_admission':parent_admission(f),
            'actions':[],'settings':f.binding.as_record()}
        for index,name in enumerate(('api.blast.prepare','api.blast.not-an-operation')):
            selection={'kind':'tool','tool':name,'arguments':{}}
            value=asyncio.run(f.task.execute(selection,index)); replay=asyncio.run(f.task.execute(selection,index))
            row=f.journal.row('runtime_actions',f.context.episode_id,index)
            result['actions'].append({'selection':selection,'controller':value,'replay':replay,
                'outcome':json.loads(row['result']),'saved_credit':row['credit']})
        result.update(execution_keys=f.execution_keys,received=f.received,projections=f.projections)
        return result


def run_probe(output):
    from gene_annotation_episode.workflow_budget import active_budget
    output=Path(output).resolve(); assert output.is_relative_to(Path(active_budget()['run_directory']).resolve())
    output.mkdir(parents=True,exist_ok=True)
    axis=Path(module('runtime').__file__).parent; repository=axis.parents[3]
    report={'version':'a103_api_task_actual_baseline_v1','owners':{},'diagnostic_completed':False,
        'source_hashes':{str(p.relative_to(repository)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(axis.rglob('*.py')) if 'tests' not in p.relative_to(axis).parts},
        'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope':'Actual local BLAST preparation/invalid selection, action journal/replay and private runtime dispatch; no remote provider or full restoration.'}
    destination=output/'api-task-probe.json'
    for home in HOMES:
        try: report['owners'][home]=observe(home,output/'owners'/home)
        except Exception as error:
            report['owners'][home]={'diagnostic_error':{'type':type(error).__module__+'.'+type(error).__qualname__,'message':str(error)}}
        destination.write_text(json.dumps(report,indent=2)+'\n')
    report['diagnostic_completed']=True; destination.write_text(json.dumps(report,indent=2)+'\n'); return report


class APIJobTaskBehavior:
    @pytest.fixture
    def actual_task(self,tmp_path):
        with actual(self.home,tmp_path) as value: yield value

    def test_runtime_build_uses_registered_private_task_when_declared(self,actual_task):
        f=actual_task
        assert type(f.task) is getattr(f.binding,'decision_source_type',f.runtime.DecisionSource)
        assert f.task.episode_id==f.context.episode_id
        if hasattr(f.binding,'decision_source_type'):
            assert type(f.task).__module__==f.binding.__module__.removesuffix('.episode')+'.task'
            assert not isinstance(f.task,f.runtime.DecisionSource)

    def test_actual_local_prepare_invalid_outcome_and_saved_replay(self,actual_task):
        f=actual_task
        for index,(name,status) in enumerate((('api.blast.prepare','completed'),('api.blast.not-an-operation','invalid'))):
            selected={'kind':'tool','tool':name,'arguments':{}}
            value=asyncio.run(f.task.execute(selected,index))
            assert value=={'index':index,'credit':0}
            assert asyncio.run(f.task.execute(selected,index))==value
            row=f.journal.row('runtime_actions',f.context.episode_id,index)
            assert json.loads(row['action'])==selected and json.loads(row['result'])['status']==status
        assert f.received==[(0,'completed'),(1,'invalid')]
        assert f.execution_keys==[f'{f.context.run_id}:{f.context.episode_id}:{i}' for i in (0,1)]
        assert len(f.projections)==2

    @pytest.mark.parametrize('status',['failed','unavailable'])
    def test_executed_failure_returns_to_original_progress_and_replay(self,actual_task,status):
        f=actual_task
        async def fail(source,name,arguments,**kwargs):
            f.execution_keys.append(kwargs['operation_key'])
            return {'status':status,'record_refs':[],'changed_record_refs':[],'feedback':{'code':'controlled_return'}}
        f.workflow.execute=fail
        selected={'kind':'tool','tool':'api.blast.submit','arguments':{}}
        expected={'index':3,'credit':0}
        assert asyncio.run(f.task.execute(selected,3))==expected
        assert asyncio.run(f.task.execute(selected,3))==expected
        assert f.received==[(3,status)] and len(f.projections)==1 and len(f.execution_keys)==1
        assert json.loads(f.journal.row('runtime_actions',f.context.episode_id,3)['action'])==selected

    def test_wait_reuses_prior_credit_without_reprojection(self,actual_task):
        f=actual_task; waits=[]
        async def wait(source,condition,index):
            waits.append((deepcopy(condition),index))
            return {'status':'completed','record_refs':[],'changed_record_refs':[],'result':{'ready':True}}
        f.workflow.perform_selected_wait=wait; f.workflow.last_observed_credit=lambda source:2.
        selected={'kind':'wait','condition':{'original':'condition'}}
        assert asyncio.run(f.task.execute(selected,4))=={'index':4,'credit':2.}
        assert asyncio.run(f.task.execute(selected,4))=={'index':4,'credit':2.}
        assert waits==[(selected['condition'],4)] and not f.projections and not f.execution_keys
        assert f.received==[(4,'completed')]

    def test_ready_original_child_precedes_new_decision(self,actual_task):
        f=actual_task; child=object(); calls=[]
        f.task._execution_context=SimpleNamespace(_ready_owned_child=lambda path:calls.append(path) or child)
        assert asyncio.run(f.task.next(SimpleNamespace(units_consumed=0))) is child
        assert calls==[f.task.path] and f.task.calls==0

    @pytest.mark.parametrize('knowledge,launch,native',[(False,False,False),(True,False,False),(False,True,True),(True,True,True)],ids=['plain','knowledge','launch-native','all-guidance'])
    def test_original_goal_and_instruction_composition(self,actual_task,knowledge,launch,native):
        f=actual_task; prompt=module('runtime_prompt')
        f.workflow.is_job_source=lambda source:False
        f.workflow.permits_common_action=lambda source,action:action in f.binding.permitted_common_actions(f.context)
        f.workflow.knowledge=SimpleNamespace(instructions='Selected knowledge.')
        f.workflow.launch_instructions=SimpleNamespace(instructions='Selected launch instructions.')
        f.workflow.native_event_information=object() if native else None; f.workflow.decision_protocol=None
        f.workflow.services=SimpleNamespace(instructions=prompt.instructions)
        context={**({'tool_knowledge':{}} if knowledge else {}),**({'launch_instruction_library':{}} if launch else {})}
        assert f.task.instructions(context)==prompt.instructions(f.task,context)
        assert f.task.instructions(context).startswith('Carry out the assigned work through ncbi_blast')

    def test_private_ordinary_api_presentation_preserves_original(self,actual_task):
        f=actual_task
        state={'execution_assignment':deepcopy(f.assignment),'api_service':'ncbi_blast',
            'api_request':deepcopy(f.assignment['request'])}
        instructions=f.binding.instructions(f.context)
        original=module('execution_prompt').render_api_launch_prompt(state,instructions)
        renderer=getattr(f.binding,'decision_prompt_renderer',None)
        if renderer is not None:
            assert renderer.__module__==f.binding.__module__.removesuffix('.episode')+'.decision_presentation'
            assert renderer(state,instructions)==original
        assert 'TASK' in original

    @pytest.mark.parametrize('redelivery',[False,True],ids=['initial-delivery','redelivery'])
    def test_parent_saved_counterpart_routes_original_progress(self,actual_task,redelivery):
        f=actual_task
        cls=module(self.home.rsplit('/',1)[0].replace('/','.')+'.episode').ExecutionEpisode
        parent=cls(f.binding.services,store=f.store,directory=f.directory/'parent',run_id=f.context.run_id,
            resources=deepcopy(f.binding.resources),initial_information={},tool_registry=f.binding.tool_registry,
            handoff_unit=2,acquired_record_unit=3,log_window_bytes=32,log_roles=[])
        parent_path=(('launch','original-parent'),)
        parent_id=module('method_loop.identities').EpisodeRef(f.context.run_id,parent_path).episode_id
        source=SimpleNamespace(episode_id=parent_id,path=parent_path,scope=f.context.scope)
        parent_context=replace(f.context,episode_id=parent_id,path=parent_path,role='launch')
        selected={'kind':'episode_child','role':'launch_api','assignment':deepcopy(f.assignment)}
        f.journal.save('runtime_actions',{'episode_id':parent_id,'decision_index':7,
            'action':json.dumps(selected),'result':None,'credit':None})
        delivered=[]
        f.workflow.specialist=lambda current:parent
        f.workflow.binding_context=lambda current:parent_context
        f.workflow.is_job_source=lambda current:False
        f.workflow.progress_provider=SimpleNamespace(receive_form=lambda *args:delivered.append(args))
        f.workflow._receive_form=lambda *args,**kwargs:f.runtime.Workflow._receive_form(f.workflow,*args,**kwargs)
        value={'status':'original supplied progress'}; schema={'type':'object','properties':{},'additionalProperties':True}
        assert f.runtime.Workflow.receive_form(f.workflow,source,value,schema,7,redelivery=redelivery)==[]
        assert delivered==[(parent_id,value,schema,f.context.scope,f'{f.context.run_id}:{parent_id}:7:typed_form')]
        selector=getattr(parent,'child_report_receiver',None)
        if selector is not None:
            assert selector('launch_api').__module__==parent.__module__.removesuffix('.episode')+'.from_child_api_job_execution'
            # The private Launch names all three counterparts (same rule as launch_task_checks.py).
            assert hasattr(parent,'decision_source_type')
            assert selector('launch_local').__module__==parent.__module__.removesuffix('.episode')+'.from_child_local_job_execution'
            assert selector('launch_hpc').__module__==parent.__module__.removesuffix('.episode')+'.from_child_hpc_job_execution'
            assert selector('unrelated') is None
        f.journal.save('runtime_actions',{'episode_id':parent_id,'decision_index':8,
            'action':json.dumps({'kind':'tool','tool':'unrelated','arguments':{}}),'result':None,'credit':None})
        if selector is not None:
            with pytest.raises(f.runtime.WorkflowError,match='original_delivery_counterpart_unavailable'):
                f.runtime.Workflow.receive_form(f.workflow,source,value,schema,8,redelivery=redelivery)

    @pytest.mark.parametrize('scenario',['minimal','bootstrap-minimal','ordinary','bootstrap-api','update-api',
        'lost-task-update','lookup','lookup-without-state','higher-priority-science','higher-priority-hpc'])
    def test_actual_provider_preserves_original_frames_priority_and_fallback(self,actual_task,scenario):
        f=actual_task; providers=module('providers'); frames=module('decision_context')
        original=object.__new__(providers._SessionConnection); declared=object.__new__(providers._SessionConnection)
        original.scientific_prompt_states={}; declared.scientific_prompt_states={}
        state={'execution_assignment':deepcopy(f.assignment),'api_service':'ncbi_blast','api_request':deepcopy(f.assignment['request'])}
        key=(f.context.episode_id,'REASONING')
        if scenario=='minimal': context={}
        elif scenario=='bootstrap-minimal': context=frames.state_frame({})
        elif scenario=='ordinary': context=state
        elif scenario=='bootstrap-api': context=frames.state_frame(state)
        elif scenario in {'update-api','lost-task-update'}:
            original.scientific_prompt_states[key]=deepcopy(state); declared.scientific_prompt_states[key]=deepcopy(state)
            updated={**state,'original_step':'retained'} if scenario=='update-api' else {'unrecognized':'original'}
            context=frames.state_frame(updated,state)
        elif scenario in {'lookup','lookup-without-state'}:
            if scenario=='lookup':
                original.scientific_prompt_states[key]=deepcopy(state); declared.scientific_prompt_states[key]=deepcopy(state)
            context={'version':frames.VERSION,'kind':'decision_lookup_result','result':{'original':'lookup'}}
        elif scenario=='higher-priority-science':
            context={**state,'goal':{'objective':'Preserve actual scientific question'},'scope':{},
                'scientific_process':{'assignment':{},'evidence_axis':{
                    'instruction_status':'published_investigation_instructions','name':'Homology evidence',
                    'investigation_instructions':'Preserve source subjects and qualification.'},
                    'thought_pattern':{'name':'Compare alternatives','description':'Interpret actual source support.'},
                    'child_tool_info':[]}}
        else:
            context={**state,'hpc_commission':{'objective':'Preserve original allocation request'}}
        instructions=f.binding.instructions(f.context)+'\n'+frames.INSTRUCTIONS
        renderer=getattr(f.binding,'decision_prompt_renderer',None)
        expected=caught(lambda:original._presentation(*key,instructions,deepcopy(context)))
        if renderer is not None:
            declared._declared_presentation=forbidden
            observed=caught(lambda:declared._presentation(*key,instructions,deepcopy(context),prompt_renderer=renderer))
        else: observed=caught(lambda:declared._presentation(*key,instructions,deepcopy(context)))
        assert observed==expected
        assert declared.scientific_prompt_states==original.scientific_prompt_states
        if scenario in {'minimal','bootstrap-minimal','lookup-without-state'}:
            assert observed['status']=='returned'
            assert observed['value']==[json.dumps(context,allow_nan=False),instructions]
        if scenario in {'ordinary','bootstrap-api','update-api','lookup'}:
            assert observed['status']=='returned'
        if scenario in {'higher-priority-science','higher-priority-hpc'}:
            assert observed['status']=='returned'
            reference=(module('scientific_process_prompt').render_scientific_process_prompt
                if scenario=='higher-priority-science' else module('library.hpc_prompt').render_hpc_prompt)
            assert observed['value'][0]==reference(context,instructions)

    @pytest.mark.parametrize('declared',[False,True],ids=['legacy-transport','declared-transport'])
    def test_pending_original_decision_dispatch_and_completed_replay(self,actual_task,declared):
        f=actual_task; prompt=module('runtime_prompt'); providers=module('providers')
        f.workflow.is_job_source=lambda source:False
        f.workflow.permits_common_action=lambda source,action:action in f.binding.permitted_common_actions(f.context)
        f.workflow.native_event_information=None; f.workflow.decision_protocol=None
        f.workflow.services=SimpleNamespace(instructions=prompt.instructions)
        state={'execution_assignment':deepcopy(f.assignment),'api_service':'ncbi_blast','api_request':deepcopy(f.assignment['request'])}
        schema=f.runtime._object({'selection':f.runtime._object({'kind':{'const':'tool'},
            'tool':{'const':'api.blast.prepare'},'arguments':f.runtime._object({})}),'report_update':f.runtime._object({})})
        response={'selection':{'kind':'tool','tool':'api.blast.prepare','arguments':{}},'report_update':{}}
        f.journal.save('runtime_model_calls',{'episode_id':f.context.episode_id,'call_index':0,'purpose':'decision',
            'request':json.dumps({'context':state,'schema':schema}),'response':None})
        session=object.__new__(providers._SessionConnection); session.scientific_prompt_states={}
        calls=[]
        async def complete(episode,role,instructions,context,output_schema,**kwargs):
            calls.append((session._presentation(episode,role,instructions,context,**kwargs),kwargs,
                (episode,role,instructions,deepcopy(context))))
            return deepcopy(response)
        f.workflow.provider=SimpleNamespace(has_session=lambda *args:True,complete=complete)
        if declared: f.workflow.provider.complete_with_presentation=complete
        returned=asyncio.run(f.task.call({},schema))
        assert returned[0]==response and len(calls)==1
        if declared and hasattr(f.binding,'decision_source_type'):
            assert calls[0][1]=={'prompt_renderer':f.binding.decision_prompt_renderer}
        else: assert calls[0][1]=={}
        original=object.__new__(providers._SessionConnection); original.scientific_prompt_states={}
        assert calls[0][0]==original._presentation(*calls[0][2])
        f.task.calls=0
        assert asyncio.run(f.task.call({},schema))[0]==response and len(calls)==1
        assert f.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==0

    @pytest.mark.parametrize('history_state',['unfinished','completed'])
    def test_original_saved_reason_selection_retains_execution_and_replay(self,actual_task,history_state):
        """Saved-action dispatch fixture, not a new reasoning authorization/custody claim."""
        f=actual_task
        assert 'reason' not in f.binding.permitted_common_actions(f.context)
        # Historical selections bypass fresh-choice validation exactly as the
        # original task did. The controlled commit port checks that a saved
        # reason is never reinterpreted as a tool or silently discarded.
        selected={'kind':'reason','commit':{'interpretation_accounts':[]}}
        outcome={'status':'completed','record_refs':[],'changed_record_refs':[],
            'result':{'fixture':'original historical reasoning return'}}
        completed=history_state=='completed'; committed=[]
        f.journal.save('runtime_actions',{'episode_id':f.context.episode_id,'decision_index':11,
            'action':json.dumps(selected),'result':json.dumps(outcome) if completed else None,
            'credit':0 if completed else None})
        def commit(payload,scope,key,**kwargs):
            committed.append((deepcopy(payload),module('communication').plain(scope),key,kwargs))
            return deepcopy(outcome)
        f.workflow.execute=forbidden
        with patch.object(f.store,'commit_reasoning',side_effect=commit):
            assert asyncio.run(f.task.execute(selected,11))=={'index':11,'credit':0}
            assert asyncio.run(f.task.execute(selected,11))=={'index':11,'credit':0}
        expected=[] if completed else [(selected['commit'],module('communication').plain(f.context.scope),
            f'{f.context.run_id}:{f.context.episode_id}:11',{})]
        assert committed==expected
        assert f.received==([] if completed else [(11,'completed')])
        assert len(f.projections)==(0 if completed else 1)
        saved=f.journal.row('runtime_actions',f.context.episode_id,11)
        assert json.loads(saved['action'])==selected and json.loads(saved['result'])==outcome and saved['credit']==0
