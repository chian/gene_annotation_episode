"""Six real API constructors; controlled task ports, no provider/native acquisition.

Store/Journal and binding constructors are actual. The registry and transport
ports are explicit engineering fixtures; they do not authenticate scientific
results, fix receiving authority, or establish a complete workflow reopening.
"""
import asyncio
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HOMES = ('execution_job_submission/api_job_execution', 'scientific_process/execution_job_submission/api_job_execution', 'hpc_work_planning/execution_job_submission/api_job_execution', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution', 'scientific_process/hpc_work_planning/execution_job_submission/api_job_execution', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution')
PREFIX = 'gene_annotation_episode.episodic_workflow.root.a102'
ROLES = {'scientific_process':'scientific_process','hpc_work_planning':'hpc',
    'hpc_allocation_execution':'hpc_execution','execution_job_submission':'launch','api_job_execution':'launch_api'}


def own(name):
    return import_module(PREFIX + '.' + name)


def forbidden(*args, **kwargs):
    raise AssertionError('external acquisition is forbidden in the controlled API task check')


def capture(call):
    try:
        return {'status':'returned','value':call()}
    except Exception as error:
        return {'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,'message':str(error)}


@contextmanager
def fixture(home, output):
    from gene_annotation_episode.workflow_budget import active_budget
    output = Path(output).resolve()
    assert output.is_relative_to(Path(active_budget()['run_directory']).resolve())
    output.mkdir(parents=True,exist_ok=True)
    with patch('subprocess.Popen',forbidden),patch('socket.socket.connect',forbidden),patch('socket.socket.connect_ex',forbidden):
        with own('state').Store(output / 'state') as store:
            store.create_problem(raw_sequence='MACDEFGH',molecule='protein')
            subject = store.problem()['subject_refs'][0]
            journal = own('episode_journal').Journal(store,'api-task-run')
            tools = SimpleNamespace(store=store,clients=SimpleNamespace(),
                _check_sequence_operand=lambda reference,scope:store.get(reference),
                _sequence=lambda reference,**kwargs:'MACDEFGH')
            services = SimpleNamespace(annotation_task_required=lambda:False,
                reference_in_context=lambda context,reference,namespace:reference in context.scope['subject_refs'])
            configuration = dict(resources={'selected-api':{'kind':'api','service':'ncbi_blast'}},
                initial_information={},handoff_unit=2.5,acquired_record_unit=3.5,
                log_window_bytes=96,log_roles=['stdout'],require_private_yield=True,
                task_yield_profiles={'launch_api:api_ncbi_blast_handoff':
                    {'cutoff':.3,'parameters':{'uncertainty_alpha':.1}}})
            binding = own(home.replace('/','.')+'.episode').ExecutionEpisode(services,
                store=store,directory=output/'workflow',run_id=journal.run_id,tool_registry=tools,**configuration)
            assignment = {'version':'api_service_assignment_v1','resource_id':'selected-api','service':'ncbi_blast',
                'request':{'subject_ref':subject,'program':'blastp','database':'nr'},'endpoint':'usable_handoff','constraints':{}}
            path = tuple((ROLES[part],'original-'+str(i)) for i,part in enumerate(home.split('/')))
            scope = {'subject_refs':[subject]}
            parent_assignment = {'version':'execution_launch_assignment_v1','requests':{'selected-api':deepcopy(assignment)},
                'immutable_input_versions':[],'constraints':{}}
            Context = own('episode_bindings').BindingContext
            parent = Context(journal.run_id,'api-parent','launch',path[:-1],scope,parent_assignment,{'goal':{'objective':'Obtain original handoff'}})
            context = Context(journal.run_id,'api-child','launch_api',path,scope,assignment,{'goal':{'objective':'Execute assigned API request'}})
            journal.save('runtime_episodes',{'episode_id':parent.episode_id,'path':own('runtime')._json(parent.path),
                'request':own('runtime')._json({'message':{'episode_assignment':parent_assignment}}),
                'initial_credit':0.,'state':'active','completion':None,'archive':None})
            yield SimpleNamespace(home=home,binding=binding,store=store,journal=journal,tools=tools,
                services=services,configuration=configuration,context=context,parent=parent,assignment=assignment,
                runtime=own('runtime'),output=output)


def make_task(v):
    cls = getattr(v.binding,'decision_source_type',v.runtime.DecisionSource)
    task = object.__new__(cls)
    task.episode_id,task.path,task.scope = v.context.episode_id,v.context.path,v.runtime._plain(v.context.scope)
    task.calls=0;task._execution_context=None;task._delivery_resolution_ref=None
    task._suspension_condition=None;task.report_values={};task.report_basis=[]
    task.interpret_schema=v.runtime._object({});task.last_outcome=None;task.last_outcome_index=None;task.feedback=None
    task.request=SimpleNamespace(goal=SimpleNamespace(as_record=lambda:{'objective':'Execute assigned API request'}),
        message=SimpleNamespace(as_record=lambda:{'episode_assignment':deepcopy(v.assignment)}),report_contract=None)
    task.checkpoint=lambda:None
    return task


def action_trace(v, status='completed', kind='tool'):
    task=make_task(v);executions=[];receipts=[];projections=[];scorings=[]
    async def execute(source,name,arguments,**kwargs):
        executions.append(kwargs['operation_key'])
        return {'status':status,'record_refs':[],'changed_record_refs':[],
            'feedback':{'code':'controlled_returned_outcome'}}
    async def wait(source,condition,index):
        executions.append({'wait':deepcopy(condition),'index':index})
        return {'status':status,'record_refs':[],'changed_record_refs':[],'feedback':{'code':'controlled_wait'}}
    async def score(source,index,result):
        scorings.append(index)
        return result
    def credit(source):
        projections.append('actual_action_progress')
        return {'credit':2.5}
    task.workflow=SimpleNamespace(run_id=v.journal.run_id,execution_binding=None,pending_work=lambda source:[],
        journal=v.journal,execute=execute,perform_selected_wait=wait,
        receive_native_outcome=lambda *args:None,receive_outcome=lambda source,selection,result,index:receipts.append((index,result['status'])),
        automatic_score_updates=score,source_credit_view=credit,last_observed_credit=lambda source:1.25,
        controller_value=lambda source,index,credit:{'index':index,'credit':credit})
    selection=({'kind':'wait','condition':{'original_target':'controlled_dependency'}} if kind=='wait' else
        {'kind':'tool','tool':'api.status','arguments':{'original_request':True}})
    index=4
    first=asyncio.run(task.execute(selection,index));second=asyncio.run(task.execute(selection,index))
    row=v.journal.row('runtime_actions',task.episode_id,index)
    result={'first':first,'replay':second,'executions':executions,'receipts':receipts,'projections':projections,
        'score_callback_indices':scorings,'selection':json.loads(row['action']),'result':json.loads(row['result']),
        'credit':row['credit'],'feedback':task.feedback}
    assert first==second=={'index':index,'credit':1.25 if kind=='wait' else 2.5}
    assert len(executions)==1 and receipts==[(index,status)]
    assert projections==([] if kind=='wait' else ['actual_action_progress'])
    assert scorings==([] if kind=='wait' else [index])
    assert result['selection']==selection and result['result']['status']==status
    return result


def configuration_observations(v):
    binding,context=v.binding,v.context
    record=binding.as_record()
    assert record['binding_id']==v.home and binding.roles==('launch_api',) and binding.commissioning_parent==v.home.rsplit('/',1)[0]
    assert binding.store is v.store and binding.tool_registry is v.tools and binding.services is v.services
    assert record['configuration']==v.configuration
    assert binding.api_execution.store is v.store and binding.api_execution.tools is v.tools
    admission=capture(lambda:binding.prepare_assignment(v.parent,'launch_api',deepcopy(v.assignment),
        v.runtime._plain(context.scope),v.journal.run_id+':api-parent:0'))
    initialization=capture(lambda:(binding.initialize(context),True)[1])
    return {'constructor':'returned','class':type(binding).__module__+'.'+type(binding).__qualname__,
        'descriptor':record,'task_class':getattr(binding,'decision_source_type',v.runtime.DecisionSource).__module__,
        'fixture_operands':{'scope':v.runtime._plain(context.scope),'assignment':deepcopy(v.assignment),
            'parent_assignment':v.runtime._plain(v.parent.assignment),'subject_record':v.store.get(v.context.scope['subject_refs'][0]),
            'problem':v.store.problem(),'parser_version':own('material_parsing').VERSION},
        'actions':list(binding.permitted_common_actions(context)),
        'instructions':binding.instructions(context),'admission':admission,'initialization':initialization,
        'unsupported_foreign_role':capture(lambda:binding.assignment_schema('launch_local')),
        'yield_class':type(binding.yield_controller(context,0.,'original-epoch')).__name__}


"""Original lexical estimator identities, actual numerical states and saved replay.

This is a constructor/serialization check, not a fabricated terminal handoff. It
never replaces a completion verifier or assigns callable identity attributes.
"""
from copy import deepcopy
import json


def estimator_observations(v):
    module=own(v.home.replace('/','.')+'.yield_estimator')
    cls=module.ExecutionEpisodeYield
    expected_module='gene_annotation_episode.episodic_workflow.root.a102.'+v.home.replace('/','.')+'.yield_estimator'
    assert cls.__qualname__=='ExecutionEpisodeYield'
    lexical={}
    for name,value in vars(cls).items():
        if isinstance(value,(staticmethod,classmethod)):value=value.__func__
        if callable(value):
            lexical[name]={'module':value.__module__,'qualname':value.__qualname__}
            assert value.__qualname__=='ExecutionEpisodeYield.'+name
    assert v.binding.practical_estimator.__func__ is cls.practical_estimator
    assert v.binding.yield_controller.__func__ is cls.yield_controller
    estimator=v.binding.practical_estimator(v.context)
    descriptor=estimator.as_record()
    assert descriptor['completion_verifier']==expected_module+'.ExecutionEpisodeYield.practical_estimator.<locals>.<lambda>'
    assert estimator.verify_completion({}) is False
    parameters=own('numerical').YieldParameters()
    empty=estimator((),parameters,()).as_record()
    malformed=capture(lambda:estimator((0.,),parameters,({'practical_completion':{}},)).as_record())
    assert malformed['status']=='raised' and malformed['message']=='invalid_practical_completion_proof'
    def controller_record(binding):
        controller=binding.yield_controller(v.context,0.,'original-estimator-epoch')
        callback=controller.estimator.estimate_with_context if hasattr(controller.estimator,'estimate_with_context') else None
        record={'class':type(controller).__module__+'.'+type(controller).__qualname__,'state':controller.state().as_record(),
            'callback':None if callback is None else (callback.as_record() if hasattr(callback,'as_record') else
                {'module':callback.__module__,'qualname':callback.__qualname__})}
        if v.context.role=='launch_api':
            assert record['callback']['completion_verifier']==expected_module+'.ExecutionEpisodeYield._launch_api_yield_controller.<locals>.<lambda>'
        return record
    controller=capture(lambda:controller_record(v.binding))
    # Fresh reconstruction uses every actual constructor operand; descriptors
    # alone are not silently expanded into configuration they never serialized.
    fresh=type(v.binding)(v.services,store=v.store,directory=v.output/'workflow',run_id=v.journal.run_id,
        tool_registry=v.tools,**deepcopy(v.configuration))
    assert fresh.practical_estimator(v.context).as_record()==descriptor
    assert capture(lambda:controller_record(fresh))==controller
    saved={'lexical_methods':lexical,'practical_estimator':descriptor,'empty_estimate':empty,
        'malformed_completion':malformed,'owner_controller':controller}
    v.journal.save('runtime_model_calls',{'episode_id':v.context.episode_id,'call_index':71,
        'purpose':'yield_binding_reconstruction_fixture','request':json.dumps(saved,allow_nan=False),'response':None})
    reopened=json.loads(v.journal.row('runtime_model_calls',v.context.episode_id,71)['request'])
    assert json.dumps(reopened,sort_keys=True)==json.dumps(saved,sort_keys=True)
    assert reopened['practical_estimator']==fresh.practical_estimator(v.context).as_record()
    assert reopened['owner_controller']==capture(lambda:controller_record(fresh))
    return saved

"""Actual API private/default/custom instruction dispatch for every original home."""
from contextlib import ExitStack

INSTRUCTION_CASES=('default','instance_shadow','nonparticipant','nonparticipant_shadow',
    'custom_return','custom_raise','subclass_return','subclass_raise','custom_delegates')
def instruction_observation(v,case,exchange=False):
    assert case in INSTRUCTION_CASES
    task=make_task(v);binding=v.binding
    host=SimpleNamespace(specialist=lambda source:binding,binding_context=lambda source:v.context,
        is_job_source=lambda source:False,
        permits_common_action=lambda source,kind:kind in binding.permitted_common_actions(v.context),
        knowledge=SimpleNamespace(instructions='\nOriginal API knowledge guidance'),
        launch_instructions=SimpleNamespace(instructions='\nOriginal pinned API launch guidance'),
        native_event_information=object(),decision_protocol='decision_exchange_v1' if exchange else None)
    default=own('episode_services').WorkflowServices;host.services=default(host);task.workflow=host
    if case.startswith('nonparticipant'):
        other=object.__new__(v.runtime.DecisionSource);other.__dict__.update(task.__dict__);task=other
    context={'tool_knowledge':{},'launch_instruction_library':{}}
    prompt=own('runtime_prompt');expected=prompt.instructions(task,context)
    selected=getattr(type(task),'instruction_composer',None)
    if selected is None:
        assert type(task) is v.runtime.DecisionSource
        original=prompt.instructions
    else:
        assert type(task) is own(v.home.replace('/','.')+'.task').APIJobTask
        descriptor=vars(type(task))['instruction_composer'];assert isinstance(descriptor,staticmethod)
        original=own(v.home.replace('/','.')+'.instructions').instructions
        assert descriptor.__func__ is selected is original
    events=[];marker=object();failure=ValueError('original_custom_api_instruction_failure')
    def compose(source,value):
        assert source is task and value is context;events.append('composer')
        return original(source,value)
    def custom(source,value):
        assert source is task and value is context;events.append('custom')
        if case.endswith('raise'):raise failure
        if case=='custom_delegates':return default.instructions(host.services,source,value)
        return marker
    class CustomServices(default):
        def instructions(self,source,value):return custom(source,value)
    with ExitStack() as stack:
        if selected is None:stack.enter_context(patch.object(prompt,'instructions',compose))
        else:
            stack.enter_context(patch.object(type(task),'instruction_composer',staticmethod(compose)))
            stack.enter_context(patch.object(prompt,'instructions',forbidden))
        if case in {'instance_shadow','nonparticipant_shadow'}:
            stack.enter_context(patch.object(task,'instruction_composer',forbidden,create=True))
        if case.startswith('subclass'):stack.enter_context(patch.object(host,'services',CustomServices(host)))
        elif case.startswith('custom'):stack.enter_context(patch.object(host,'services',SimpleNamespace(instructions=custom)))
        if case.endswith('raise'):
            try:task.instructions(context)
            except ValueError as error:assert error is failure and type(error) is ValueError
            else:raise AssertionError('original_custom_exception_not_propagated')
            assert events==['custom'];outcome={'raised':'builtins.ValueError','message':str(failure),'same_exception':True}
        else:
            result=task.instructions(context)
            if case in {'custom_return','subclass_return'}:
                assert result is marker and events==['custom'];outcome={'same_return_object':True}
            else:
                assert result==expected and type(result) is type(expected)
                assert events==(['custom','composer'] if case=='custom_delegates' else ['composer'])
                outcome={'instructions':result}
    return {'case':case,'exchange':exchange,'events':events,'outcome':outcome,
        'composer_owner':original.__module__+'.'+original.__qualname__}
