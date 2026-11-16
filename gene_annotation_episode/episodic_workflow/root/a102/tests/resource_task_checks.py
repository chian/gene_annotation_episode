"""Actual own-axis identities with controlled adapter ports; no external acquisition."""
import asyncio
from contextlib import contextmanager,ExitStack
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
PACKAGE='gene_annotation_episode.episodic_workflow.root.a102'
OWNERS=(('resource_work_submission','legacy_annotation','launch'),
 ('resource_work_submission/api_resource_work_execution','resource_work_submission','launch_api'),
 ('resource_work_submission/local_resource_work_execution','resource_work_submission','launch_local'),
 ('resource_work_submission/hpc_resource_work_execution','resource_work_submission','launch_hpc'),
 ('resource_result_acquisition','legacy_annotation','results'),
 ('scientific_process/resource_work_submission','scientific_process','launch'),
 ('scientific_process/resource_work_submission/api_resource_work_execution','scientific_process/resource_work_submission','launch_api'),
 ('scientific_process/resource_work_submission/local_resource_work_execution','scientific_process/resource_work_submission','launch_local'),
 ('scientific_process/resource_work_submission/hpc_resource_work_execution','scientific_process/resource_work_submission','launch_hpc'),
 ('scientific_process/resource_result_acquisition','scientific_process','results'))
HOMES=tuple(x[0] for x in OWNERS)
def own(name):return import_module(PACKAGE+'.'+name)
def forbidden(*args,**kwargs):raise AssertionError('unexpected external acquisition or replay')
def capture(call):
    try:return {'status':'returned','value':call()}
    except Exception as error:return {'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,'message':str(error)}
def path_for(home):
    role=dict((h,r) for h,_,r in OWNERS)[home]
    prefix=(('annotation','root'),)
    if home.startswith('scientific_process/'):prefix+=(('scientific_process','science'),)
    if role not in ('launch','results'):prefix+=(('launch','child_0'),)
    return prefix+((role,'child_0'),)
def handoff(selection,handle='original-controlled-job'):
    receiver={'provider_id':selection['resource_id'],'target_handle':handle,'contract_ref':'original-receiver'}
    return {'version':'execution_handoff_v1','execution_handle':handle,'resource_selection':deepcopy(selection),
        'submitted_input_versions':[],'monitoring':receiver,'results':deepcopy(receiver),
        'checked_at':'original-check','check_record_refs':['original-check-receipt'],'state':'usable','failure':None}

class ControlledAdapter:
    """Explicit engineering port; never presented as an A102 API/HPC science adapter."""
    def __init__(self,kind):
        self.kind=kind;self.resource_id='controlled-'+kind;self.events=[];self.availability='available'
        self.outcome={'status':'completed','record_refs':[],'changed_record_refs':[],'result':{'original':kind},'feedback':None}
        self.selection={'resource_id':self.resource_id,'kind':kind,'allocation':{'cpu':1,'memory_bytes':5368709120,'scratch_bytes':1073741824},'capability_binding_ref':'registry-'+kind}
        self.handoffs=[handoff(self.selection)];self.receipt=None
    def bind_record_selection(self,selection):self.selection_callback=selection
    def as_record(self):return {'version':'controlled_resource_protocol_fixture_v1','kind':self.kind,'resource_id':self.resource_id}
    def capability(self):return {'resource_id':self.resource_id,'kind':self.kind,'availability':self.availability,
        'observed_at':'original-controlled-observation','provenance_refs':['registry-'+self.kind],
        'knowledge_entry_ids':[],'tool_names':['controlled.execute']}
    def prepare_assignment(self,parent,role,assignment,scope,key):
        self.events.append(['prepare',parent.episode_id,role,key]);return deepcopy(assignment)
    def catalog(self,context):return [{'name':'controlled.execute','description':'Controlled original outcome','input_schema':own('domain').obj({})}]
    async def execute(self,context,name,arguments,key):
        self.events.append(['execute',context.episode_id,name,key]);return self.outcome
    def fact_sources(self,role):return {}
    def facts(self,context,snapshot):return {'execution_handoffs':deepcopy(self.handoffs)}
    def resolve(self,context,reference,namespace):return reference==self.resource_id
    def validate_report(self,context,form,schema):self.events.append(['validate',context.episode_id])
    def credit_view(self,context,selection):return {'credit':0.}
    def initial_references(self,context):return [] if self.receipt is None else [self.receipt]
    def received_form_references(self,context,value,schema,key):
        self.events.append(['receive',context.episode_id,key]);return [] if self.receipt is None else [self.receipt]
    def check_handoff(self,context,value,key):return self.outcome

@contextmanager
def fixture(home,output,stable_workspace=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    # This protocol fixture controls host activity; real native enforcement is
    # exercised separately by test_operational_configuration.
    with patch.object(own('local_resources').LocalResources, '_refresh', lambda self, db: []), \
         patch.dict('os.environ', {'GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY': str(output/'capacity')}), \
         patch('subprocess.Popen',forbidden),patch('socket.socket.connect',forbidden),patch('socket.socket.connect_ex',forbidden):
      with own('state').Store(output/'state') as store:
        store.create_problem(raw_sequence='MACDEFGH',molecule='protein');scope=store.validate_scope()
        journal=own('episode_journal').Journal(store,'resource-task-run');runtime=own('runtime')
        services=SimpleNamespace(capabilities=lambda:[],record_selection=lambda context:{'original':True},
            reference_in_context=lambda context,reference,namespace:reference in context.scope['subject_refs'],
            bound_role_credit=lambda context,selection:{'credit':0.,'original_selection':deepcopy(selection)})
        adapters={kind:ControlledAdapter(kind) for kind in ('api','local','hpc')}
        bindings={h:own(h.replace('/','.')+'.episode').ResourceEpisode(services,resource_adapters=tuple(adapters.values())) for h,_,_ in OWNERS}
        from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import write_instruction_source
        library_source=output/'instruction-source';write_instruction_source(library_source,'a102')
        library=own('scientific_process_library').ScientificProcessLibrary.freeze(output/'scientific-library',source=library_source)
        tool_library=own('scientific_tool_library').ScientificToolLibrary.freeze(output/'tool-library',catalog=[{
            'name':'fixture.inspect','resources':'local','description':'Controlled protocol port','instructions':'No acquisition.',
            'input_schema':own('domain').obj({})}])
        scientific=own('scientific_process.episode').ScientificProcessEpisode(services,library=library,tool_library=tool_library,
            child_roles=('scientific_process','launch','results'))
        registry=own('episode_bindings').EpisodeBindingRegistry((scientific,*bindings.values()))
        for h,b in bindings.items():
            assert registry.for_path(path_for(h)) is b
            assert registry.for_child(path_for(h)[:-1],b.roles[0]) is b
        role=bindings[home].roles[0];kind={'launch_api':'api','launch_local':'local','launch_hpc':'hpc'}.get(role,'local')
        selected=adapters[kind];assignment={'version':'resource_launch_assignment_v1','job_request':{'original':True},
            'immutable_input_versions':[],'constraints':{},'resource_selection':None if role=='launch' else deepcopy(selected.selection),
            'software_knowledge_refs':[],'resource_knowledge_refs':[]}
        if role=='results':assignment={'version':'resource_results_assignment_v1','handoff':handoff(selected.selection),'requested_data_selector':{}}
        Context=own('episode_bindings').BindingContext;path=path_for(home);parent_path=path[:-1]
        def context(path,assignment):
            identity=runtime.EpisodeRef(journal.run_id,path).episode_id
            request={'goal':{'objective':'Preserve the original assigned resource work'},
                'message':{'scope':scope,'episode_assignment':deepcopy(assignment),'initial_report':{}}}
            result=Context(journal.run_id,identity,path[-1][0],path,scope,assignment,request)
            journal.save('runtime_episodes',{'episode_id':identity,'path':runtime._json(path),
                'request':runtime._json(request),'initial_credit':0.,'state':'active','completion':None,'archive':None})
            return result
        parent_assignment=deepcopy(assignment) if parent_path[-1][0]=='launch' else {}
        if parent_assignment:parent_assignment['resource_selection']=None
        parent=context(parent_path,parent_assignment);ctx=context(path,assignment)
        receipts=own('episode_receipts').EpisodeReceipts(store,journal.run_id)
        receipts.bind(parent.episode_id);receipts.receive(parent.episode_id,scope['subject_refs'],kind='initial')
        receipts.bind(ctx.episode_id,parent.episode_id);receipts.receive(ctx.episode_id,scope['subject_refs'],kind='initial')
        clients=own('acquisition').PublicClients(ncbi_email=None)
        assert clients.ncbi_email is None
        tools=own('a102_tools').A102ToolRegistry(store,clients=clients,a102_work_directory=Path(stable_workspace or output/'native'))
        assert tools.clients is clients
        native=own('a102_resources').A102ResourceAdapter(tools,store,journal.run_id)
        yield SimpleNamespace(home=home,role=role,binding=bindings[home],bindings=bindings,adapters=adapters,adapter=selected,
            context=ctx,parent=parent,assignment=assignment,services=services,registry=registry,store=store,journal=journal,
            runtime=runtime,receipts=receipts,tools=tools,native=native,output=output,scope=scope)
def make_task(v):
    cls = getattr(v.binding,'decision_source_type',v.runtime.DecisionSource)
    task = object.__new__(cls)
    task.episode_id,task.path,task.scope = v.context.episode_id,v.context.path,v.runtime._plain(v.context.scope)
    task.calls=0;task._execution_context=None;task._delivery_resolution_ref=None
    task._suspension_condition=None;task.report_values={};task.report_basis=[]
    task.interpret_schema=v.runtime._object({});task.last_outcome=None;task.last_outcome_index=None;task.feedback=None
    task.request=SimpleNamespace(goal=SimpleNamespace(as_record=lambda:{'objective':'Acquire original result bytes'}),
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
        inprocess_replay=None,scientific_process_binding=None,
        permits_common_action=lambda source,kind:kind in v.binding.permitted_common_actions(v.context),
        _closed_child_commission=lambda *args:None,validate_wait_selection=lambda *args:None,
        receive_native_outcome=lambda *args:None,receive_outcome=lambda source,selection,result,index:receipts.append((index,result['status'])),
        automatic_score_updates=score,source_credit_view=credit,last_observed_credit=lambda source:1.25,
        controller_value=lambda source,index,credit:{'index':index,'credit':credit})
    selection=({'kind':'wait','condition':{'original_target':'controlled_dependency'}} if kind=='wait' else
        {'kind':'tool','tool':'resource.capabilities','arguments':{}})
    index=4
    unit=v.runtime.Workflow.selected(task.workflow,task,selection,index)
    assert type(unit) is v.runtime.ActionLeaf and unit.label==kind+':4' and unit.decision_index==4
    first=asyncio.run(unit.acquire_async(None)).contribution.controller_input
    controller=own('numerical').YieldController('controlled-original-caller',1.25 if kind=='wait' else 0.,.25)
    step=controller.observe(unit.label,first).as_record();state=controller.state().as_record()
    second=asyncio.run(v.runtime.Workflow.selected(task.workflow,task,selection,index).acquire_async(None)).contribution.controller_input
    assert controller.state().as_record()==state
    assert step['credit']==first['credit'] and step['marginal_credit']==(0. if kind=='wait' else 2.5)
    row=v.journal.row('runtime_actions',task.episode_id,index)
    result={'first':first,'replay':second,'executions':executions,'receipts':receipts,'projections':projections,
        'score_callback_indices':scorings,'selection':json.loads(row['action']),'result':json.loads(row['result']),
        'credit':row['credit'],'feedback':task.feedback,'yield_step':step,'yield_state':state,
        'unit_label':unit.label,'decision_index':unit.decision_index}
    assert first==second=={'index':index,'credit':1.25 if kind=='wait' else 2.5}
    assert len(executions)==1 and receipts==[(index,status)]
    assert projections==([] if kind=='wait' else ['actual_action_progress'])
    assert scorings==([] if kind=='wait' else [index])
    assert result['selection']==selection and result['result']['status']==status
    return result

"""Actual resource private/default/custom instruction dispatch for every original home."""
from contextlib import ExitStack

INSTRUCTION_CASES=('default','instance_shadow','nonparticipant','nonparticipant_shadow',
    'custom_return','custom_raise','subclass_return','subclass_raise','custom_delegates')
def instruction_observation(v,case,exchange=False):
    assert case in INSTRUCTION_CASES
    task=make_task(v);binding=v.binding
    host=SimpleNamespace(specialist=lambda source:binding,binding_context=lambda source:v.context,
        is_job_source=lambda source:False,
        permits_common_action=lambda source,kind:kind in binding.permitted_common_actions(v.context),
        knowledge=SimpleNamespace(instructions='\nOriginal resource knowledge guidance'),
        launch_instructions=SimpleNamespace(instructions='\nOriginal pinned resource launch guidance'),
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
        assert type(task) is own(v.home.replace('/','.')+'.task').ResourceTask
        descriptor=vars(type(task))['instruction_composer'];assert isinstance(descriptor,staticmethod)
        original=own(v.home.replace('/','.')+'.instructions').instructions
        assert descriptor.__func__ is selected is original
    events=[];marker=object();failure=ValueError('original_custom_launch_instruction_failure')
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


def native_trace(v,status='completed',retryable=False):
    """Saved original adapter job; only the external native execution port is controlled."""
    adapter=v.native;plain=v.runtime._plain;events=[]
    local_home=('scientific_process/' if v.home.startswith('scientific_process/') else '')+'resource_work_submission/local_resource_work_execution'
    local_binding=own(local_home.replace('/','.')+'.episode').ResourceEpisode(v.services,resource_adapters=(adapter,))
    local_path=path_for(local_home);job={'operation':'structure.align','arguments':{'original_fixture_operands':True}}
    assignment={'version':'resource_launch_assignment_v1','job_request':job,'immutable_input_versions':[],
        'constraints':{},'resource_selection':adapter.selection(),'software_knowledge_refs':[],'resource_knowledge_refs':[],
        'adapter_assignment':{'job_ref':'seeded-original-job'}}
    identity=v.runtime.EpisodeRef(v.journal.run_id,local_path).episode_id
    request={'goal':{'objective':'Original structural job'},'message':{'scope':v.scope,'episode_assignment':assignment,'initial_report':{}}}
    context=own('episode_bindings').BindingContext(v.journal.run_id,identity,'launch_local',local_path,v.scope,assignment,request)
    v.journal.save('runtime_episodes',{'episode_id':identity,'path':v.runtime._json(local_path),'request':v.runtime._json(request),
        'initial_credit':0.,'state':'active','completion':None,'archive':None})
    v.store.db.execute('INSERT INTO a102_resource_jobs VALUES(?,?,?,?,NULL,NULL,NULL,?,NULL,NULL,NULL)',
        ('seeded-original-job',v.journal.run_id,v.runtime._json(job),v.runtime._json(v.scope),'prepared'))
    source=v.tools._source('controlled.resource.original_native_return',{'original':True})
    outcome={'status':status,'record_refs':[source] if status=='completed' else [],'changed_record_refs':[],
        'result':{'original':True},'feedback':None if status=='completed' else {'code':'original_return','retryable':retryable}}
    async def execute(name,arguments,**kwargs):
        assert name==job['operation'] and arguments==job['arguments'];events.append(kwargs['operation_key']);return outcome
    key=v.journal.run_id+':'+identity+':2'
    with patch.object(v.tools,'execute_async',execute),patch.object(own('a102_resources'),'now',lambda:'2026-11-12T00:00:00+00:00'):
        with v.tools.current_invocation(context,read_received=lambda:[],tool_name='a102.native.execute',arguments={},operation_key=key):
            result=asyncio.run(local_binding.execute(context,'a102.native.execute',{},key))
        if status=='completed':
            with patch.object(v.tools,'execute_async',forbidden):assert asyncio.run(local_binding.execute(context,'a102.native.execute',{},key))==result
        else:assert result is outcome
    row=dict(adapter._job('seeded-original-job'))
    assert row['state']==('completed' if status=='completed' else 'prepared' if retryable else 'failed')
    assert events==[key]
    report={'result':result,'job':row,'events':events,'descriptor':adapter.as_record(),
        'credit_definition':own('a102_resources').A102ResourceCredit(adapter).as_record(),
        'prepared_job_fixture':True,'native_science_executed':False}
    if status=='completed':
        parent_path=local_path[:-1];parent_id=v.runtime.EpisodeRef(v.journal.run_id,parent_path).episode_id
        parent=replace(context,episode_id=parent_id,role='launch',path=parent_path,assignment={},
            request={'message':{'scope':v.scope,'episode_assignment':{}}})
        handoff_value=result['result']['handoff']
        refs=adapter.received_form_references(parent,handoff_value,{},'original-delivery')
        assert adapter.check_handoff(parent,handoff_value,'original-check')['record_refs']==refs
        result_home=('scientific_process/' if v.home.startswith('scientific_process/') else '')+'resource_result_acquisition'
        result_binding=own(result_home.replace('/','.')+'.episode').ResourceEpisode(v.services,resource_adapters=(adapter,))
        outer_path=local_path[:-2];outer_id=v.runtime.EpisodeRef(v.journal.run_id,outer_path).episode_id
        outer=replace(parent,episode_id=outer_id,role=outer_path[-1][0],path=outer_path)
        outer_refs=adapter.received_form_references(outer,handoff_value,{},'original-outer-delivery')
        assert outer_refs==refs
        result_assignment=result_binding.prepare_assignment(outer,'results',{'version':'resource_results_assignment_v1',
            'handoff':handoff_value,'requested_data_selector':{}},v.scope,'original-results-commission')
        result_path=path_for(result_home);result_id=v.runtime.EpisodeRef(v.journal.run_id,result_path).episode_id
        request={'message':{'scope':v.scope,'episode_assignment':result_assignment}}
        result_context=own('episode_bindings').BindingContext(v.journal.run_id,result_id,'results',result_path,v.scope,result_assignment,request)
        v.journal.save('runtime_episodes',{'episode_id':result_id,'path':v.runtime._json(result_path),'request':v.runtime._json(request),
            'initial_credit':0.,'state':'active','completion':None,'archive':None})
        collected=asyncio.run(result_binding.execute(result_context,'a102.native.collect',{},'original-collection'))
        assert collected['record_refs']==[source] and collected['result']['native_result']==outcome['result']
        selection={'run_id':v.journal.run_id,'episode_id':result_id,'known_record_refs':[source,*refs],'initial_known_record_refs':[]}
        credit=own('a102_resources').A102ResourceCredit(adapter)(result_context,selection)
        assert credit=={'credit':1.,'handoff_count':1,'collected_native_comparison_count':0,
            'interpretation':'operational_information_not_scientific_function_support'}
        baseline={**selection,'initial_known_record_refs':list(selection['known_record_refs'])}
        assert own('a102_resources').A102ResourceCredit(adapter)(result_context,baseline)['credit']==0.
        report.update(collection=collected,credit=credit,delivery=refs,outer_delivery=outer_refs,
            results_parent_path=plain(outer.path),prepared_result=result_assignment)
    return report


def configuration_observations(v):
    b=v.binding;descriptor=b.as_record()
    assert type(v.tools.clients) is own('acquisition').PublicClients and v.tools.clients.ncbi_email is None
    foreign_role='results' if v.role=='launch' else 'launch'
    foreign=replace(v.context,role=foreign_role,path=v.context.path[:-1]+((foreign_role,v.context.path[-1][1]),))
    assert descriptor['binding_id']==v.home
    assert descriptor['configuration']=={'resource_adapters':[a.as_record() for a in v.adapters.values()]}
    assert b.services is v.services and all(b.adapters[k] is a for k,a in ((a.resource_id,a) for a in v.adapters.values()))
    assert all(a.selection_callback is v.services.record_selection for a in v.adapters.values())
    return {'descriptor':descriptor,'class':type(b).__module__+'.'+type(b).__qualname__,
        'public_client_configuration':{'class':type(v.tools.clients).__module__+'.'+type(v.tools.clients).__qualname__,
            'ncbi_email':None,'explicit_null_contact':True,'ambient_configuration_selected':False},
        'task_class':getattr(b,'decision_source_type',v.runtime.DecisionSource).__module__,
        'path':v.runtime._plain(v.context.path),'parent_path':v.runtime._plain(v.parent.path),
        'prepared':capture(lambda:b.prepare_assignment(v.parent,v.role,deepcopy(v.assignment),v.scope,'original-commission')),
        'instructions':b.instructions(v.context),'catalog':b.catalog(v.context),
        'direct_foreign_goal':{'role':foreign_role,'instructions':b.instructions(foreign)},
        'facts':b.facts(v.context,{}),'credit':b.credit_view(v.context,{'original':True}),
        'unrecognized_schema':capture(lambda:b.assignment_schema('unrecognized')),
        'controller_callback_absent':not hasattr(b,'yield_controller') and not hasattr(b,'practical_estimator')}


def connected_build_trace(v):
    runtime=v.runtime
    names=('annotation','scientific_process','launch','launch_api','launch_local','launch_hpc','results')
    grains={name:runtime.Grain(name,'Original fixture boundary','Original resource result',forbidden) for name in names}
    edges={'annotation':('scientific_process','launch','results'),'scientific_process':('scientific_process','launch','results'),
        'launch':('launch_api','launch_local','launch_hpc'),'launch_api':(),'launch_local':(),'launch_hpc':(),'results':()}
    tree=runtime.EpisodeTree(grains['annotation'],{grains[n]:tuple(grains[c] for c in edges[n]) for n in names},self_nesting=('scientific_process',))
    host=SimpleNamespace(context=runtime.ReleasingContext(tree=tree,run_id=v.journal.run_id),grains=grains,
        inprocess_completion_order=None,receipts=None,scientific_process_binding=None,episode_bindings=v.registry,
        contract_information_profile=lambda source:None,journal=v.journal,run_id=v.journal.run_id,store=v.store,
        expose_assigned_job=lambda source:None,receive_tool_attributions=lambda *args,**kwargs:None,
        archive=SimpleNamespace(store=forbidden),launch_instructions=SimpleNamespace(materialize=lambda value:None))
    host.specialist=lambda source:v.registry.for_path(source.path)
    host.binding_context=lambda source:own('episode_bindings').BindingContext(host.run_id,source.episode_id,
        source.path[-1][0],source.path,source.scope,source.request.message.as_record()['episode_assignment'],source.request.as_record())
    host.source_credit_view=lambda source:host.specialist(source).credit_view(host.binding_context(source),None)
    built=runtime.Workflow.build(host,v.role,'connected','Preserve the original resource job',v.scope,
        parent_path=v.parent.path,episode_assignment=deepcopy(v.assignment))
    task=built.source
    assert type(task) is getattr(v.binding,'decision_source_type',runtime.DecisionSource)
    assert v.registry.for_path(task.path) is v.binding and task.path[:-1]==v.parent.path
    assert task.episode_id==runtime.EpisodeRef(v.journal.run_id,task.path).episode_id
    saved=dict(v.journal.row('runtime_episodes',task.episode_id));assert json.loads(saved['request'])==runtime._plain(task.request.as_record())
    return {'path':runtime._plain(task.path),'episode_id':task.episode_id,'saved':saved,'initial_report':task.report_values}


def presentation_trace(v,case):
    if case in ('receiver','bootstrap','saved_update'):
        # The original handoff schema deliberately contains generic references.
        records=own('resource_records');prompt=own('scientific_process_prompt')
        schema=deepcopy(records.HANDOFF_SCHEMA)
        rows=list(prompt._schema_rows(schema,'handoff'))
        for path,presence,kind in (
            ('handoff.failure.affected_refs[]','each item','string; reference'),
            ('handoff.failure.partial_record_refs[]','each item','string; reference'),
            ('handoff.failure.diagnostic_ref','required','string or null; reference'),
            ('handoff.submitted_input_versions[].reference','required','string; reference'),
            ('handoff.execution_handle','required','string; reference to resource_execution'),
        ):
            assert (path,presence,kind,'') in rows
        generic=records.FAILURE_SCHEMA['properties']['affected_refs']['items']
        assert generic['x-reference-namespace'] is None
        unqualified={key:value for key,value in generic.items() if key!='x-reference-namespace'}
        assert list(prompt._schema_rows(generic))==list(prompt._schema_rows(unqualified))
        assert schema==records.HANDOFF_SCHEMA
    providers=own('providers');frames=own('decision_context')
    connection=object.__new__(providers._SessionConnection);connection.scientific_prompt_states={}
    instructions='Original instructions';key=(v.context.episode_id,'REASONING')
    state={'goal':{'objective':'Original resource task'},'scope':v.scope,'working_state':{'subjects':[],'scope':v.scope},
        'tools':v.binding.catalog(v.context),'requested_form':None,'controller':{},'current_report_update':{},
        'last_local_outcome':None,'role':v.role,'assignment':deepcopy(v.assignment)}
    def bootstrap(fields):return {'version':frames.VERSION,'kind':'decision_bootstrap','base_revision':None,
        'revision':frames.revision(fields),'fields':fields,'removed_fields':[]}
    if case=='unrecognized':context={'role':v.role}
    elif case=='saved_minimal':context={'saved_minimal_context':True}
    elif case=='empty_bootstrap':context=bootstrap({})
    elif case=='receiver':context=state
    elif case=='bootstrap':context=bootstrap(state)
    elif case=='saved_update':
        connection._presentation(*key,instructions,bootstrap(state))
        changed={**state,'last_local_outcome':{'status':'failed'}}
        context={'version':frames.VERSION,'kind':'decision_update','base_revision':frames.revision(state),
            'revision':frames.revision(changed),'fields':{'last_local_outcome':{'status':'failed'}},'removed_fields':[]}
    else:
        assert case=='missing_base'
        context={'version':frames.VERSION,'kind':'decision_update','base_revision':frames.revision(state),
            'revision':frames.revision(state),'fields':state,'removed_fields':[]}
    observed=capture(lambda:connection._presentation(*key,instructions,context))
    if case=='missing_base':
        assert observed=={'status':'raised','type':'builtins.TypeError','message':'previous_model_state_requires_object'}
    elif case in ('unrecognized','saved_minimal','empty_bootstrap'):
        assert observed=={'status':'returned','value':(json.dumps(context,allow_nan=False),instructions)}
    else:
        expected=own('receiver_prompt').render_receiver_prompt(connection.scientific_prompt_states[key],instructions,lookup_results=[])
        assert observed['value']==(expected,own('scientific_process_prompt').text_instructions(instructions))
    return {'observation':observed,'saved_state':connection.scientific_prompt_states.get(key)}


def parent_exchange_trace(v):
    reference=v.tools._source('controlled.resource.receipt',{'original':True});v.adapter.receipt=reference
    for adapter in v.adapters.values():adapter.handoffs=[]
    value=handoff(v.adapter.selection);v.adapter.handoffs=[value]
    schema={'type':'object','additionalProperties':False,'properties':{
        'handoff':v.binding.fact_sources(v.role)['execution_handoff']['report_schema']},'required':['handoff']}
    form={'handoff':value};contract={'decision':'Return the original receiving interface','measurements':{'schema':schema}}
    child=replace(v.context,request={**v.runtime._plain(v.context.request),'report_contract':contract})
    v.journal.save('runtime_episodes',{'episode_id':child.episode_id,'path':v.runtime._json(child.path),
        'request':v.runtime._json(child.request),'initial_credit':0.,'state':'active','completion':None,'archive':None})
    v.binding.validate_report(child,form,schema)
    v.journal.save('runtime_forms',{'episode_id':child.episode_id,'facts':v.runtime._json(v.binding.facts(child,{})),
        'form':v.runtime._json(form)})
    selection={'kind':'episode_child','role':v.role,'assignment':deepcopy(v.assignment),'scope':v.scope,
        'purpose':contract['decision'],'schema_json':v.runtime._json(schema)}
    v.journal.save('runtime_actions',{'episode_id':v.parent.episode_id,'decision_index':0,
        'action':v.runtime._json(selection),'result':None,'credit':None})
    attempt={'parent_episode_id':v.parent.episode_id,'decision_index':0,'delivery_ref':'original-resource-delivery',
        'child_episode_id':child.episode_id,'contract':v.runtime._json(contract),'form':v.runtime._json(form),
        'failure':None,'timing_receipts':None,'report_contract_declaration':None}
    v.journal.save('runtime_report_attempts',attempt)
    # Workflow receives a runtime source; its separate binding view is immutable.
    parent_source=SimpleNamespace(episode_id=v.parent.episode_id,path=v.parent.path,
        scope=v.runtime._plain(v.parent.scope))
    def binding_context(source):
        assert source is parent_source
        return v.parent
    host=SimpleNamespace(store=v.store,run_id=v.journal.run_id,journal=v.journal,receipts=v.receipts,
        specialist=lambda source:None if source.path[-1][0]=='annotation' else v.registry.for_path(source.path),
        binding_context=binding_context,is_job_source=lambda source:False,progress_provider=None,
        episode_bindings=v.registry,native_timing_information=None,job_episodes=None,receive_tool_attributions=lambda *args,**kwargs:[])
    first=v.runtime.Workflow._receive_form(host,parent_source,form,schema,0);assert first==[reference]
    v.journal.save('runtime_actions',{'episode_id':v.parent.episode_id,'decision_index':0,'action':v.runtime._json(selection),
        'result':v.runtime._json({'status':'completed','record_refs':first,'changed_record_refs':[]}), 'credit':None})
    with patch.object(v.registry,'received_form_references',forbidden):
        replay=v.runtime.Workflow._receive_form(host,parent_source,form,schema,0)
    v.journal.save('runtime_report_attempts',{**attempt,'decision_index':1})
    redelivery=v.runtime.Workflow._receive_form(host,parent_source,form,schema,1,redelivery=True)
    assert replay==redelivery==first and v.journal.row('runtime_actions',v.parent.episode_id,1) is None
    return {'form':form,'schema':schema,'first':first,'replay':replay,'redelivery':redelivery,
        'child_form':dict(v.journal.row('runtime_forms',child.episode_id)),
        'receipts':[list(row) for row in v.store.db.execute('SELECT record_ref,receipt_kind,source_index FROM runtime_record_receipts '
            'WHERE run_id=? AND episode_id=? ORDER BY receipt_index',(v.journal.run_id,v.parent.episode_id))]}
