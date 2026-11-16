"""Real private Results owners and journals; controlled target observation/read ports.

No native command, remote operation, live provider or scientific credit is invoked.
Target reads below are explicit boundary fixtures, never claimed as independently
proved native handoffs. The actual result receipt/source validators are unpatched.
"""
import asyncio
import base64
from contextlib import contextmanager,ExitStack
from copy import deepcopy
from dataclasses import replace
import hashlib
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HOMES=('execution_result_acquisition', 'scientific_process/execution_result_acquisition', 'hpc_work_planning/execution_result_acquisition', 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition', 'scientific_process/hpc_work_planning/execution_result_acquisition', 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition')
PREFIX='gene_annotation_episode.episodic_workflow.root.a103'
ROLES={'scientific_process':'scientific_process','hpc_work_planning':'hpc',
    'hpc_allocation_execution':'hpc_execution','execution_result_acquisition':'results'}
def own(name):return import_module(PREFIX+'.'+name)
def forbidden(*args,**kwargs):raise AssertionError('external acquisition forbidden in Results fixture')
def capture(call):
    try:return {'status':'returned','value':call()}
    except Exception as error:return {'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,
        'message':str(error),'code':getattr(error,'code',None)}

ROUTES=('local_file','masking','utility','standard_database','native_database','api','hmmer_preparation','hmmer','blast','generic')
CATALOG_MODULES={'masking':'native_blast_masking_results','utility':'native_blast_utility_results',
    'standard_database':'native_blast_standard_database_results','native_database':'native_blast_database_results',
    'hmmer_preparation':'native_hmmer_preparation_results','hmmer':'native_hmmer_results','blast':'native_blast_results'}

def catalog_for(v,route):
    if route=='api':return [{'name':'controlled.api','input_schema':own('domain').obj({})}]
    if route=='generic':return v.binding.catalog.__func__.__globals__['native_result_operation_catalog']()
    module=own(CATALOG_MODULES[route])
    return module.operation_catalog({'version':'controlled_original_selector'}) if route=='native_database' else module.operation_catalog()

@contextmanager
def dispatch_ports(v,route,operation=None):
    """Exercise original selection/exception branches through controlled ports.

    Lower priority predicates also return true. These are dispatch observations,
    not authenticated native targets, result parsing or scientific interpretation.
    """
    assert route in ROUTES;rank=ROUTES.index(route);b=v.binding;target=deepcopy(v.target)
    target['resource_kind']='api' if rank<=ROUTES.index('api') else 'local'
    async def unexpected(*args,**kwargs):raise AssertionError('unexpected native operation')
    callback=operation or unexpected
    predicates={
        'is_standard_blast_database_target':lambda value:rank<=ROUTES.index('standard_database'),
        'is_native_blast_database_target':lambda value:rank<=ROUTES.index('native_database'),
        'is_native_hmmer_preparation_target':lambda value:rank<=ROUTES.index('hmmer_preparation'),
        'is_native_hmmer_target':lambda value:rank<=ROUTES.index('hmmer'),
        'is_native_blast_target':lambda value:rank<=ROUTES.index('blast')}
    with ExitStack() as stack:
        stack.enter_context(patch.dict(b.execute.__func__.__globals__,predicates))
        if b.catalog.__func__.__globals__ is not b.execute.__func__.__globals__:
            stack.enter_context(patch.dict(b.catalog.__func__.__globals__,predicates))
        stack.enter_context(patch.object(b,'_target',lambda _:target))
        stack.enter_context(patch.object(b,'_selector',lambda *args:{'version':'controlled_original_selector'}))
        for key,attribute in [('local_file','local_file_sources'),('masking','native_blast_masking_results'),('utility','native_blast_utility_results')]:
            reader=getattr(b,attribute)
            stack.enter_context(patch.object(reader,'applies',lambda _,key=key:rank<=ROUTES.index(key)))
            stack.enter_context(patch.object(reader,'execute',callback))
        for attribute in ('native_blast_standard_database_results','native_blast_database_results',
                'native_hmmer_preparation_results','native_hmmer_results','native_blast_results'):
            stack.enter_context(patch.object(b,attribute,SimpleNamespace(execute=callback)))
        stack.enter_context(patch.object(b,'api_execution',SimpleNamespace(execute=callback,catalog=lambda _:catalog_for(v,'api'))))
        stack.enter_context(patch.object(b,'_execute_native_results',callback))
        yield

def inherited_observations(v):
    b=v.binding;base=own('a103_homology_execution').A103HomologyExecution
    assert isinstance(b,base) and type(b).__mro__[-2] is base
    identities={}
    for name,value in vars(base).items():
        if isinstance(value,(staticmethod,classmethod)):value=value.__func__
        if callable(value):
            resolved=getattr(type(b),name)
            assert resolved is value
            identities[name]={'module':value.__module__,'qualname':value.__qualname__}
    assert b._has_appservice() is b._has_uniprot() is False
    assert b.annotation_axis_yield_context(v.context,{})=={}
    assert b._blast_reference_source()==base._blast_reference_source()
    services=SimpleNamespace(services={name:SimpleNamespace(service=name)
        for name in ('bvbrc_appservice','uniprot','bvbrc_data','bvbrc_minhash')})
    with patch.object(b,'api_execution',services):
        assert b._has_appservice() is b._has_uniprot() is True
        flags={role:[b._forwards_bvbrc_reports(role),b._forwards_minhash_reports(role)]
            for role in ('annotation','scientific_process','results','launch','unknown')}
        assert flags=={'annotation':[True,True],'scientific_process':[True,True],
            'results':[False,False],'launch':[False,False],'unknown':[False,False]}
    selectors={version:[b._masking_selector({'selector':{'version':version}}),b._utility_selector({'selector':{'version':version}})]
        for version in ('native_blast_masking_result_selector_v1','native_blast_utility_result_selector_v1','native_blast_utility_result_selector_v2','unknown')}
    assert selectors=={'native_blast_masking_result_selector_v1':[True,False],
        'native_blast_utility_result_selector_v1':[False,True],'native_blast_utility_result_selector_v2':[False,True],'unknown':[False,False]}
    assert b._retained_masking_target(v.context,{},v.context.scope) is None
    assert b._retained_utility_target(v.context,{},v.context.scope) is None
    contracts=own('scientific_process.execution_result_acquisition.'+
        ('execution_contracts' if hasattr(b,'decision_source_type') else 'requests'))
    consumers={}
    for name in ('bvbrc_genome_alignment_tool_info','bvbrc_comparative_systems_tool_info',
            'bvbrc_proteome_tool_info','bvbrc_homology_tool_info'):
        module=own(name);assert module.RESULTS_SCHEMA is contracts.RESULTS_SCHEMA
        consumers[name]=deepcopy(module.RESULTS_SCHEMA)
    return {'homology_lexical_methods':identities,'forwarding_predicates':flags,
        'selectors':selectors,'appservice_sources':b._appservice_sources(),'blast_reference_source':b._blast_reference_source(),
        'original_contract_consumers':consumers}

def dispatch_observations(v):
    records={}
    for route in ROUTES:
        for status in ('returned','invalid','invalid_type','protected','oserror'):
            calls=[];marker={'status':'completed','original_route':route}
            error=(own('native_file_capture').NativeFileCaptureError('retained_artifact_unavailable')
                if status=='protected' else TypeError('original_type_failure') if status=='invalid_type'
                else OSError('original_os_failure') if status=='oserror' else ValueError('original_selected_failure'))
            async def operation(*args,**kwargs):
                calls.append(route)
                if status!='returned':raise error
                return marker
            with dispatch_ports(v,route,operation),patch.object(v.binding,'catalog',
                    lambda _:[{'name':'controlled','input_schema':own('domain').obj({})}]):
                try:
                    value=asyncio.run(v.binding.execute(v.context,'controlled',{},'original-key'))
                except Exception as caught:
                    assert caught is error and (status=='oserror' or (status=='protected' and route=='local_file'))
                    value={'raised_type':type(caught).__module__+'.'+type(caught).__qualname__,
                        'message':str(caught),'code':getattr(caught,'code',None)}
                else:
                    assert status!='oserror' and not (status=='protected' and route=='local_file')
                    if status=='returned':assert value is marker
                    else:assert value['status']=='invalid' and value['feedback']['code']==str(error)
            assert calls==[route];records[route+';'+status]={'outcome':value,'calls':calls}
    return records

def path_for(home):
    return (('annotation','original-root'),)+tuple((ROLES[part],'child_0' if part=='execution_result_acquisition'
        else 'original-'+str(i)) for i,part in enumerate(home.split('/')))

@contextmanager
def fixture(home,output,workspace=None):
    from gene_annotation_episode.workflow_budget import active_budget
    output=Path(output).resolve();assert output.is_relative_to(Path(active_budget()['run_directory']).resolve())
    output.mkdir(parents=True,exist_ok=True)
    supplied_workspace=workspace is not None
    workspace=(output/'selected-resource' if workspace is None else Path(workspace).resolve())
    root=next(p for p in Path(active_budget()['run_directory']).resolve().parents if (p/'AGENTS.md').is_file())
    assert workspace.is_relative_to(root/'runs')
    if supplied_workspace:assert workspace.is_dir() # immutable prepared operand; no job/file writes here
    else:workspace.mkdir(parents=True,exist_ok=True)
    with patch('subprocess.Popen',forbidden),patch('socket.socket.connect',forbidden),patch('socket.socket.connect_ex',forbidden):
        with own('state').Store(output/'state') as store:
            store.create_problem(raw_sequence='MACDEFGH',molecule='protein')
            scope=store.validate_scope();subject=store.problem()['subject_refs'][0]
            journal=own('episode_journal').Journal(store,'results-task-run')
            clients=own('acquisition').PublicClients(ncbi_email=None)
            tools=own('tools').ToolRegistry(store,clients=clients)
            assert tools.clients is clients and clients.ncbi_email is None
            services=SimpleNamespace(annotation_task_required=lambda:False,
                reference_in_context=lambda context,reference,namespace:reference in context.scope['subject_refs'])
            configuration=dict(resources={'selected-local':{'kind':'local','workspace':str(workspace),
                'policy':{'memory_bytes':5368709120,'scratch_bytes':4294967296}}},
                initial_information={},handoff_unit=2.5,acquired_record_unit=3.5,log_window_bytes=5,log_roles=['stdout'],
                require_private_yield=True,results_yield_profiles={'native_unbounded_local':{'cutoff':.25,'parameters':{}}},
                task_yield_profiles={'results:native_finite_local':{'cutoff':.125,'parameters':{}}})
            bindings={h:own(h.replace('/','.')+'.episode').ExecutionEpisode(services,store=store,
                directory=output/'workflow',run_id=journal.run_id,tool_registry=tools,**deepcopy(configuration)) for h in HOMES}
            from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import write_instruction_source
            library_source=output/'instruction-source';write_instruction_source(library_source,'a103')
            library=own('scientific_process_library').ScientificProcessLibrary.freeze(output/'scientific-library',source=library_source)
            tool_library=own('scientific_tool_library').ScientificToolLibrary.freeze(output/'tool-library',catalog=[{
                'name':'fixture.inspect','resources':'local','description':'Controlled engineering boundary.',
                'instructions':'No acquisition.','input_schema':own('domain').obj({})}])
            scientific=own('scientific_process.episode').ScientificProcessEpisode(services,library=library,
                tool_library=tool_library,child_roles=('scientific_process','hpc','results'))
            ancestors=[scientific]
            for h in ('hpc_work_planning','hpc_work_planning/hpc_allocation_execution',
                    'scientific_process/hpc_work_planning','scientific_process/hpc_work_planning/hpc_allocation_execution'):
                ancestors.append(own(h.replace('/','.')+'.episode').HPCEpisode(services,store=store,
                    run_id=journal.run_id,directory=output/'workflow',resources={'aurora':{'kind':'pbs_ssh'}},commissions={}))
            registry=own('episode_bindings').EpisodeBindingRegistry((*ancestors,*bindings.values()))
            for h,b in bindings.items():
                assert registry.for_path(path_for(h)) is b
                assert registry.for_child(path_for(h)[:-1],'results') is b
            binding=bindings[home];runtime=own('runtime');Context=own('episode_bindings').BindingContext
            assignment={'version':'execution_results_assignment_v1','handoff_ref':'controlled-original-handoff',
                'selector':{'path':str(workspace/'result.bin'),'offset':0,'limit':10}}
            parent_path=path_for(home)[:-1];path=path_for(home)
            parent_id=runtime.EpisodeRef(journal.run_id,parent_path).episode_id
            child_id=runtime.EpisodeRef(journal.run_id,path).episode_id
            receipts=own('episode_receipts').EpisodeReceipts(store,journal.run_id)
            parent_manifest=receipts.bind(parent_id)
            receipts.receive(parent_id,scope['subject_refs'],kind='initial')
            child_manifest=receipts.bind(child_id,parent_id)
            schema={'type':'object','additionalProperties':False,'properties':{
                'results':deepcopy(binding.fact_sources('results')['execution_result_refs']['report_schema'])},'required':['results']}
            contract={'decision':'Inspect the actual acquired result','measurements':{'schema':schema}}
            parent=Context(journal.run_id,parent_id,
                parent_path[-1][0],parent_path,scope,{},
                {'goal':{'objective':'Acquire the original requested result'},
                    'message':{'episode_assignment':{},'scope':scope,'knowledge_inheritance':parent_manifest}})
            context=Context(journal.run_id,child_id,'results',path,scope,assignment,
                {'goal':{'objective':'Acquire original result bytes'},
                    'report_contract':contract,'message':{'episode_assignment':assignment,'scope':scope,
                        'initial_report':{'results':[]},'knowledge_inheritance':child_manifest}})
            target={'resource_id':'selected-local','resource_kind':'local','execution_id':'controlled-original-attempt',
                'handle':assignment['handoff_ref'],'run_id':journal.run_id,'scope':deepcopy(scope),
                'assignment':{'workspace':str(workspace)}}
            events=[];state={'state':'running','returncode':None,'failure':None}
            def read_target(reference,scope):
                assert reference==assignment['handoff_ref'];store.validate_scope(own('communication').plain(scope))
                return deepcopy(target)
            def observe_target(value,*,operation_key):
                assert value==target;events.append(['observe',operation_key])
                return {'state':state['state'],'returncode':state['returncode'],'observed_at':'2026-11-12T00:00:00+00:00'}
            def read_file(value,*,path,offset,limit,operation_key):
                assert value==target;events.append(['read',operation_key,path,offset,limit])
                if state['failure']=='oserror':raise OSError('controlled unreadable result')
                if state['failure']=='invalid':raise ValueError('controlled invalid result window')
                data=bytes(range(10))[offset:offset+limit]
                return {'path':path,'offset':offset,'returned_bytes':len(data),'size_bytes':10,
                    'bytes_base64':base64.b64encode(data).decode()}
            with patch.object(binding.job_progress_provider.targets,'read_target',read_target), \
                    patch.object(binding.job_progress_provider.targets,'observe_target',observe_target), \
                    patch.object(binding.job_progress_provider.targets,'read_file',read_file):
                for ctx in (parent,context):
                    journal.save('runtime_episodes',{'episode_id':ctx.episode_id,'path':runtime._json(ctx.path),
                        'request':runtime._json(ctx.request),
                        'initial_credit':0.,'state':'active','completion':None,'archive':None})
                yield SimpleNamespace(home=home,binding=binding,bindings=bindings,store=store,journal=journal,tools=tools,
                    services=services,configuration=configuration,context=context,parent=parent,assignment=assignment,
                    target=target,events=events,state=state,runtime=runtime,output=output,workspace=workspace,registry=registry,
                    receipts=receipts,schema=schema,contract=contract,
                    api_assignment={'version':'api_service_assignment_v1','service':'ncbi_blast','request':{'original':True}})


def select(v,index,name,arguments):
    key=v.journal.run_id+':'+v.context.episode_id+':'+str(index)
    action={'kind':'tool','tool':name,'arguments':deepcopy(arguments)}
    v.journal.save('runtime_actions',{'episode_id':v.context.episode_id,'decision_index':index,
        'action':v.runtime._json(action),'result':None,'credit':None})
    outcome=asyncio.run(v.binding.execute(v.context,name,arguments,key))
    v.journal.save('runtime_actions',{'episode_id':v.context.episode_id,'decision_index':index,
        'action':v.runtime._json(action),'result':v.runtime._json(outcome),'credit':None})
    v.receipts.receive(v.context.episode_id,outcome.get('record_refs',[]),kind='own_action',source_index=index)
    return key,outcome


def acquisition_trace(v,case):
    assert case in ('partial','terminal','oserror','invalid')
    v.state.update(state='completed' if case=='terminal' else 'running',returncode=0 if case=='terminal' else None,
        failure=case if case in ('oserror','invalid') else None)
    key,outcome=select(v,0,'execution.results.collect',{})
    assert outcome['status']=='completed';reference,=outcome['record_refs']
    body=v.binding._read_result(reference,v.context.scope)
    assert body==outcome['result']
    before=deepcopy(v.events)
    replay=asyncio.run(v.binding.execute(v.context,'execution.results.collect',{},key))
    assert replay==outcome and before==v.events
    origin={'content_location':'current_resource_filesystem','attempt_output_version':'unverified',
        'window_consistency':'separate_reads_no_atomic_file_snapshot',
        'completion_basis':'requested_acquisition_and_observed_successful_attempt'}
    assert body['acquisition_origin']==origin
    assert len(body['failures'])==(1 if case in ('oserror','invalid') else 0)
    if body['failures']:
        assert body['windows']==[]
        assert body['failures'][0]['exception_type']==('OSError' if case=='oserror' else 'ValueError')
    else:assert body['windows'][0]['returned_bytes']==5
    assert not v.binding._native_results_complete(v.context,[body])
    credit=v.binding.credit_view(v.context,None)
    assert credit['credit']==(0. if body['failures'] else 1.75)
    receipt_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(v.binding._result_directory(v.context).iterdir()) if p.is_file()}
    # Journal/source IDs, complete result bytes, qualification, actual units and
    # every immutable receipt remain compared; only workspace is shared explicitly.
    return {'outcome':outcome,'replay':replay,'events':v.events,'credit':credit,'receipt_files':receipt_files,
        'source':v.store.get(reference),'artifact':v.store.get_artifact(v.store.get(reference)['artifact_ref']).decode()}


def coverage_trace(v):
    rows=[]
    for index,(offset,limit) in enumerate(((0,5),(5,5),(0,10))):
        _,outcome=select(v,index,'execution.results.read',{'path':v.assignment['selector']['path'],'offset':offset,'limit':limit})
        assert outcome['status']=='completed';rows.append(outcome['record_refs'][0])
    selection={'run_id':v.journal.run_id,'episode_id':v.context.episode_id,'known_record_refs':rows,'initial_known_record_refs':[]}
    first=v.binding.credit_view(v.context,selection)
    assert first['credit']==3.5
    selection['initial_known_record_refs']=[rows[0]]
    remaining=v.binding.credit_view(v.context,selection)
    assert remaining['credit']==1.75
    assert not v.binding._native_results_complete(v.context,[v.binding._read_result(r,v.context.scope) for r in rows])
    return {'first':first,'remaining':remaining,'references':rows}
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
    task.workflow=SimpleNamespace(run_id=v.journal.run_id,execution_binding=None,wait_inputs_version=None,
        completed_action_inputs_version=None,journal=v.journal,execute=execute,perform_selected_wait=wait,
        receive_native_outcome=lambda *args:None,receive_outcome=lambda source,selection,result,index:receipts.append((index,result['status'])),
        automatic_score_updates=score,source_credit_view=credit,last_observed_credit=lambda source:1.25,
        controller_value=lambda source,index,credit:{'index':index,'credit':credit})
    selection=({'kind':'wait','condition':{'original_target':'controlled_dependency'}} if kind=='wait' else
        {'kind':'tool','tool':'execution.results.status','arguments':{}})
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

"""Actual Results private/default/custom instruction dispatch for every original home."""
from contextlib import ExitStack

INSTRUCTION_CASES=('default','instance_shadow','nonparticipant','nonparticipant_shadow',
    'custom_return','custom_raise','subclass_return','subclass_raise','custom_delegates')
def instruction_observation(v,case,exchange=False):
    assert case in INSTRUCTION_CASES
    task=make_task(v);binding=v.binding
    host=SimpleNamespace(specialist=lambda source:binding,binding_context=lambda source:v.context,
        is_job_source=lambda source:False,
        permits_common_action=lambda source,kind:kind in binding.permitted_common_actions(v.context),
        knowledge=SimpleNamespace(instructions='\nOriginal Results knowledge guidance'),
        launch_instructions=SimpleNamespace(instructions='\nOriginal pinned Results launch guidance'),
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
        assert type(task) is own(v.home.replace('/','.')+'.task').ResultsTask
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


def parent_exchange_trace(v):
    key,outcome=select(v,0,'execution.results.collect',{})
    schema=v.schema
    form={'results':outcome['record_refs']}
    v.binding.validate_report(v.context,form,schema)
    v.journal.save('runtime_forms',{'episode_id':v.context.episode_id,
        'facts':v.runtime._json(v.binding.facts(v.context,{})),'form':v.runtime._json(form)})
    action={'kind':'episode_child','role':'results','assignment':deepcopy(v.assignment),
        'scope':v.runtime._plain(v.context.scope),'purpose':v.contract['decision'],
        'goal':v.context.request['goal']['objective'],'schema_json':v.runtime._json(schema),'initial_report_json':'{"results":[]}'}
    v.journal.save('runtime_actions',{'episode_id':v.parent.episode_id,'decision_index':0,
        'action':v.runtime._json(action),'result':None,'credit':None})
    attempt={'parent_episode_id':v.parent.episode_id,'decision_index':0,'delivery_ref':'controlled-original-delivery',
        'child_episode_id':v.context.episode_id,'contract':v.runtime._json(v.contract),'form':v.runtime._json(form),
        'failure':None,'timing_receipts':None,'report_contract_declaration':None}
    v.journal.save('runtime_report_attempts',attempt)
    # Workflow sources retain plain scope; the binding-facing view stays frozen.
    parent_source=SimpleNamespace(episode_id=v.parent.episode_id,role=v.parent.role,
        path=v.parent.path,scope=v.runtime._plain(v.parent.scope))
    def binding_context(source):
        assert source is parent_source
        return v.parent
    def specialist(source):return None if source.role=='annotation' else v.registry.for_path(source.path)
    host=SimpleNamespace(store=v.store,run_id=v.journal.run_id,journal=v.journal,receipts=v.receipts,
        specialist=specialist,binding_context=binding_context,is_job_source=lambda source:False,
        progress_provider=None,episode_bindings=v.registry,native_timing_information=None,job_episodes=None,
        receive_tool_attributions=lambda *args,**kwargs:[])
    admitted=v.runtime.Workflow._receive_form(host,parent_source,form,schema,0)
    assert admitted==outcome['record_refs']
    returned={'status':'completed','record_refs':admitted,'changed_record_refs':[]}
    v.journal.save('runtime_actions',{'episode_id':v.parent.episode_id,'decision_index':0,
        'action':v.runtime._json(action),'result':v.runtime._json(returned),'credit':None})
    with patch.object(v.registry,'received_form_references',forbidden):
        replay=v.runtime.Workflow._receive_form(host,parent_source,form,schema,0)
    assert replay==admitted
    episode=dict(v.journal.row('runtime_episodes',v.context.episode_id));episode['state']='yielded'
    v.journal.save('runtime_episodes',{name:value for name,value in episode.items() if name!='run_id'})
    with patch.object(v.binding.job_progress_provider.targets,'read_target',forbidden):
        restored=v.binding.prepare_assignment(v.parent,'results',deepcopy(v.assignment),v.runtime._plain(v.context.scope),
            v.journal.run_id+':'+v.parent.episode_id+':0')
    assert restored==v.assignment
    attempt={**attempt,'decision_index':1};v.journal.save('runtime_report_attempts',attempt)
    redelivery=v.runtime.Workflow._receive_form(host,parent_source,form,schema,1,redelivery=True)
    assert redelivery==admitted and v.journal.row('runtime_actions',v.parent.episode_id,1) is None
    return {'operation_key':key,'schema':schema,'form':form,'parent_admission':admitted,'replay':replay,'redelivery':redelivery,
        'saved_commission_restored_without_target_read':restored,
        'parent_role':v.parent.role,'parent_path':v.runtime._plain(v.parent.path),
        'child_form':dict(v.journal.row('runtime_forms',v.context.episode_id)),
        'parent_receipts':[list(row) for row in v.store.db.execute('SELECT record_ref,receipt_kind,source_index FROM runtime_record_receipts '
            'WHERE run_id=? AND episode_id=? ORDER BY receipt_index',(v.journal.run_id,v.parent.episode_id))]}


def configuration_observations(v):
    b=v.binding
    assert type(v.tools.clients) is own('acquisition').PublicClients and v.tools.clients.ncbi_email is None
    assert b.as_record()['configuration']==v.configuration and b.as_record()['binding_id']==v.home
    assert b.store is v.store and b.tool_registry is v.tools and b.services is v.services
    assert v.registry.for_child(v.parent.path,'results') is b and v.registry.for_path(v.context.path) is b
    return {'descriptor':b.as_record(),'class':type(b).__module__+'.'+type(b).__qualname__,
        'public_client_configuration':{'class':type(v.tools.clients).__module__+'.'+type(v.tools.clients).__qualname__,
            'ncbi_email':None,'explicit_null_contact':True,'ambient_configuration_selected':False},
        'task_class':getattr(b,'decision_source_type',v.runtime.DecisionSource).__module__,
        'parent_role':v.parent.role,'parent_path':v.runtime._plain(v.parent.path),
        'incoming':capture(lambda:b.prepare_assignment(v.parent,'results',deepcopy(v.assignment),
            v.runtime._plain(v.context.scope),v.journal.run_id+':'+v.parent.episode_id+':0')),
        'inherited_foreign_role':capture(lambda:b.assignment_schema('launch')),
        'initialization':capture(lambda:(b.initialize(v.context),True)[1]),
        'instructions':b.instructions(v.context),'actions':b.permitted_common_actions(v.context),
        'catalog':b.catalog(v.context)}




def connected_build_trace(v):
    runtime=v.runtime
    names=('annotation','scientific_process','hpc','hpc_execution','results')
    grains={name:runtime.Grain(name,'Original fixture boundary','Original result',forbidden) for name in names}
    edges={'annotation':('scientific_process','hpc','results'),'scientific_process':('scientific_process','hpc','results'),
        'hpc':('hpc_execution','results'),'hpc_execution':('results',),'results':()}
    tree=runtime.EpisodeTree(grains['annotation'],{grains[n]:tuple(grains[c] for c in edges[n]) for n in names},
        self_nesting=('scientific_process',))
    host=SimpleNamespace(context=runtime.ReleasingContext(tree=tree,run_id=v.journal.run_id),grains=grains,
        inprocess_completion_order=None,receipts=None,scientific_process_binding=None,episode_bindings=v.registry,
        contract_information_profile=lambda source:None,journal=v.journal,run_id=v.journal.run_id,store=v.store,
        expose_assigned_job=lambda source:None,receive_tool_attributions=lambda *args,**kwargs:None,
        archive=SimpleNamespace(store=forbidden),launch_instructions=SimpleNamespace(materialize=lambda value:None))
    host.specialist=lambda source:v.registry.for_path(source.path)
    host.legacy_parent_for_path = runtime.Workflow.legacy_parent_for_path.__get__(host)
    host.binding_context=lambda source:own('episode_bindings').BindingContext(host.run_id,source.episode_id,
        source.path[-1][0],source.path,source.scope,source.request.message.as_record()['episode_assignment'],source.request.as_record())
    host.source_credit_view=lambda source:host.specialist(source).credit_view(host.binding_context(source),None)
    built=runtime.Workflow.build(host,'results','connected', 'Acquire original bytes',v.runtime._plain(v.context.scope),
        parent_path=v.parent.path,episode_assignment=deepcopy(v.assignment))
    task=built.source
    assert type(task) is getattr(v.binding,'decision_source_type',runtime.DecisionSource)
    assert v.registry.for_path(task.path) is v.binding and task.path[:-1]==v.parent.path
    assert task.episode_id==runtime.EpisodeRef(v.journal.run_id,task.path).episode_id
    saved=dict(v.journal.row('runtime_episodes',task.episode_id))
    assert json.loads(saved['request'])==v.runtime._plain(task.request.as_record())
    return {'path':v.runtime._plain(task.path),'episode_id':task.episode_id,'saved':saved,'initial_report':task.report_values}


def yield_trace(v,mode):
    binding=v.binding;context=v.context;module=PREFIX+'.'+v.home.replace('/','.')+'.yield_estimator'
    if mode=='finite':
        controller=binding.yield_controller(context,0.,'original-finite')
        first=controller.observe('original-first-window',{'credit':1.75}).as_record()
        final=controller.observe('original-all-requested-positions',{'credit':3.5}).as_record()
        return {'first':first,'final':final,'state':controller.state().as_record(),
            'callback':controller.estimator.estimate_with_context.__module__+'.'+controller.estimator.estimate_with_context.__qualname__}
    if mode in ('unbounded','missing_unbounded'):
        assignment={**v.assignment,'selector':{'paths':[v.assignment['selector']['path']]}}
        context=replace(context,assignment=assignment)
        if mode=='missing_unbounded':
            with patch.object(binding,'results_yield_profiles',{}):
                return capture(lambda:binding.yield_controller(context,0.,'original-unbounded'))
        controller=binding.yield_controller(context,0.,'original-unbounded')
        assert controller.cost==.25 and controller.estimator.estimate_with_context is None
        return controller.state().as_record()
    assert mode in ('typed','api')
    target=deepcopy(v.target);selector={'version':'native_blast_masking_result_selector_v1'}
    key='results:typed_local_native_blast_masking_result_selector_v1'
    if mode=='api':
        target['resource_kind']='api';target['service']='ncbi_blast';selector={};key='results:api_ncbi_blast'
    # Selector/target boundary already belongs to the actual typed acquisition
    # service; this checks only the original profile dispatch and callback identity.
    with patch.object(binding,'_target',lambda _:target),patch.object(binding,'_selector',lambda *args:selector), \
            patch.object(binding,'task_yield_profiles',{key:{'cutoff':.125,'parameters':{}}}):
        controller=binding.yield_controller(context,0.,'original-typed')
        descriptor=controller.estimator.estimate_with_context.as_record()
        assert descriptor['completion_verifier']==module+'.ExecutionEpisodeYield._results_yield_controller.<locals>.<lambda>'
        return {'profile_key':key,'estimator':descriptor,'state':controller.state().as_record()}

"""Original lexical estimator identities, actual numerical states and saved replay.

This is a constructor/serialization check, not a fabricated terminal handoff. It
never replaces a completion verifier or assigns callable identity attributes.
"""
from copy import deepcopy
import json


def estimator_observations(v):
    module=own(v.home.replace('/','.')+'.yield_estimator')
    cls=module.ExecutionEpisodeYield
    expected_module='gene_annotation_episode.episodic_workflow.root.a103.'+v.home.replace('/','.')+'.yield_estimator'
    assert cls.__module__==expected_module and cls.__qualname__=='ExecutionEpisodeYield'
    lexical={}
    for name,value in vars(cls).items():
        if isinstance(value,(staticmethod,classmethod)):value=value.__func__
        if callable(value):
            lexical[name]={'module':value.__module__,'qualname':value.__qualname__}
            assert value.__module__==expected_module and value.__qualname__=='ExecutionEpisodeYield.'+name
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
        assert record['callback']=={'module':expected_module,
            'qualname':'ExecutionEpisodeYield._results_yield_controller.<locals>.finite_result_yield'}
        return record
    controller=capture(lambda:controller_record(v.binding))
    # Fresh reconstruction uses every actual constructor operand; descriptors
    # alone are not silently expanded into configuration they never serialized.
    fresh=type(v.binding)(v.services,store=v.store,directory=v.output/'workflow',run_id=v.journal.run_id,
        tool_registry=v.tools,**deepcopy(v.configuration))
    assert fresh.practical_estimator(v.context).as_record()==descriptor
    with patch.object(fresh.job_progress_provider.targets,'read_target',v.binding.job_progress_provider.targets.read_target):
        assert capture(lambda:controller_record(fresh))==controller
    saved={'lexical_methods':lexical,'practical_estimator':descriptor,'empty_estimate':empty,
        'malformed_completion':malformed,'owner_controller':controller}
    v.journal.save('runtime_model_calls',{'episode_id':v.context.episode_id,'call_index':71,
        'purpose':'yield_binding_reconstruction_fixture','request':json.dumps(saved,allow_nan=False),'response':None})
    reopened=json.loads(v.journal.row('runtime_model_calls',v.context.episode_id,71)['request'])
    assert json.dumps(reopened,sort_keys=True)==json.dumps(saved,sort_keys=True)
    assert reopened['practical_estimator']==fresh.practical_estimator(v.context).as_record()
    with patch.object(fresh.job_progress_provider.targets,'read_target',v.binding.job_progress_provider.targets.read_target):
        assert reopened['owner_controller']==capture(lambda:controller_record(fresh))
    return saved
