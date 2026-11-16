"""Actual A102 owners, Store/Journal/receipts/projectors and provider presentation.

Only acquisition and wait ports are controlled. Original scientific projection,
reasoning commits, registry resolution, report receivers and provider renderers
execute their real methods. No external work or autonomous investigation claimed.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HOMES = (('published_evidence_assessment', 'literature'), ('published_evidence_assessment/evidence_search_strategy_improvement', 'literature_strategy'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', 'literature_search'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_page'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction', 'literature_table'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement', 'literature_ordered'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'literature_targeted'), ('scientific_process/published_evidence_assessment', 'literature'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement', 'literature_strategy'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', 'literature_search'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_page'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction', 'literature_table'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement', 'literature_ordered'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'literature_targeted'))
CHILDREN = {'literature': (('literature_strategy', 'evidence_search_strategy_improvement'),), 'literature_strategy': (('literature_search', 'source_relevance_assessment'),), 'literature_search': (('literature_page', 'source_evidence_examination'),), 'literature_page': (('literature_table', 'table_evidence_extraction'), ('literature_ordered', 'source_coverage_improvement'), ('literature_targeted', 'passage_evidence_extraction'))}
PREFIX = 'gene_annotation_episode.episodic_workflow.root.a102'
ROLES = {home.rsplit('/',1)[-1]:role for home,role in HOMES}
ROLES['scientific_process']='scientific_process'
STATUSES=('completed','partial','invalid','failed','unavailable')


def own(name):return import_module(PREFIX+'.'+name)
def plain(value):return own('communication').plain(value)
def forbidden(*args,**kwargs):raise AssertionError('external acquisition forbidden in source family check')
def capture(call):
    try:
        value=call()
        return {'status':'returned','value':plain(value.as_record() if hasattr(value,'as_record') else value)}
    except Exception as error:return {'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,
        'message':str(error),'code':getattr(error,'code',None)}
def request_record(assignment,schema):
    return {'goal':{'objective':'Examine the original source question'},
        'report_contract':{'decision':'Choose further source examination','measurements':{'schema':schema}},
        'message':{'episode_assignment':deepcopy(assignment),'initial_report':{key:[] for key in schema['properties']}}}
def path_for(home):
    return (('annotation','original-root'),)+tuple((ROLES[part],'original-'+str(i)) for i,part in enumerate(home.split('/')))


@contextmanager
def fixture(home,output,task_kind='verified_source_leads'):
    from gene_annotation_episode.workflow_budget import active_budget
    from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import write_instruction_source
    output=Path(output).resolve();assert output.is_relative_to(Path(active_budget()['run_directory']).resolve())
    output.mkdir(parents=True,exist_ok=True)
    with patch('subprocess.Popen',forbidden),patch('socket.socket.connect',forbidden),patch('socket.socket.connect_ex',forbidden):
        with own('state').Store(output/'state') as store:
            store.create_problem(raw_sequence='MACDEFGH',molecule='protein')
            scope=store.validate_scope();subject=store.problem()['subject_refs'][0]
            payload={name:[] for name in store.reasoning_schema()['properties']}
            payload['hypotheses']=[{'alias':'original','subject_refs':[subject],'predicate':'sequence_integrity',
                'value':{'type':'enum','value':'unknown'},'context_refs':[]}]
            committed=store.commit_reasoning(payload,scope,'original-commission')
            assert committed['status'] in ('completed','partial'),committed
            proposed=committed['aliases']['original']
            raw=b'Original synthetic source claim; no biological finding is asserted.'
            artifact=store.artifact(raw)
            source=store.put('source',{'provider':'source_family_engineering_fixture','accession':None,'uri':None,
                'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None,
                'parent_source_refs':[]},origin='caller')
            runtime=own('runtime');host=object.__new__(runtime.Workflow)
            host.store=store;host.run_id='a102-source-family-run';host.directory=output/'workflow'
            host.root_action_boundary=runtime.ROOT_BOUNDARY_VERSION
            host.journal=own('episode_journal').Journal(store,host.run_id)
            host.receipts=own('episode_receipts').EpisodeReceipts(store,host.run_id)
            clients=own('acquisition').PublicClients(ncbi_email=None)
            host.tools=own('tools').ToolRegistry(store,clients=clients);host.job_episodes=None;host.progress_provider=None
            assert host.tools.clients is clients and type(clients) is own('acquisition').PublicClients
            assert clients.ncbi_email is None
            host.native_timing_information=None;host.native_event_information=None
            host.project_credit=forbidden;host.project_annotation_score=None;host.annotation_score_binding=None
            host.execution_binding=None;host.inprocess_replay=None;host.pending_work=lambda source:[]
            host.episode_branch_lifecycle=runtime.EPISODE_BRANCH_LIFECYCLE;host.resource_estimator=None
            host.progress_receipt_order='received_progress_order_v1'
            host.decision_protocol=None;host.annotation_child_roles=None;host.execution_handle=None
            host.services=own('episode_services').WorkflowServices(host)
            declarations={key:{'credit_unit':2.5,'kind':'accumulation' if key.endswith('verified_source_leads') else 'remaining_commissioned_credit',
                'cutoff':.25,'uncertainty_alpha':.1} for key in own('literature_task_credit').YIELD_TASKS}
            configuration={'outcome_page_size':3,'structure_population':False,'private_yield_binding':True,'yield_bindings':declarations}
            bindings={h:own(h.replace('/','.')+'.episode').LiteratureEpisode(host.services,**deepcopy(configuration)) for h,_ in HOMES}
            library_source=output/'instruction-source';write_instruction_source(library_source,'a102')
            library=own('scientific_process_library').ScientificProcessLibrary.freeze(output/'scientific-library',source=library_source)
            tools=own('scientific_tool_library').ScientificToolLibrary.freeze(output/'tool-library',catalog=[{
                'name':'fixture.inspect','resources':'local','description':'Engineering fixture only.',
                'instructions':'No external work or scientific inference.','input_schema':own('domain').obj({})}])
            scientific=own('scientific_process.episode').ScientificProcessEpisode(host.services,library=library,tool_library=tools,
                child_roles=('scientific_process','literature'))
            host.scientific_process_binding=scientific
            host.episode_bindings=own('episode_bindings').EpisodeBindingRegistry((scientific,*bindings.values()))
            names=('annotation','scientific_process',*dict.fromkeys(role for _,role in HOMES))
            host.grains={name:runtime.Grain(name,'One original fixture action','Original typed fixture result',forbidden) for name in names}
            graph={host.grains[name]:tuple(host.grains[child] for child in
                (('scientific_process','literature') if name in {'annotation','scientific_process'} else
                    tuple(child for child,_ in CHILDREN.get(name,())))) for name in names}
            host.tree=runtime.EpisodeTree(host.grains['annotation'],graph,self_nesting=('scientific_process',))
            host.context=runtime.ReleasingContext(tree=host.tree,run_id=host.run_id)
            binding=bindings[home];role=dict(HOMES)[home];path=path_for(home)
            assert host.episode_bindings.for_path(path) is binding
            page={'version':'page_assignment_v1','source_ref':source['id'],'representation':'original',
                'artifact_ref':artifact,'question_context_refs':[],'prior_delivery_refs':[]}
            window={'source_ref':source['id'],'representation':'original','offset':0,'limit':len(raw)}
            if role=='literature_page':assignment=deepcopy(page)
            elif role in ('literature_table','literature_ordered','literature_targeted'):
                assignment={'version':'reading_assignment_v1','page':deepcopy(page),
                    'selection':{'spans':[window]} if role=='literature_targeted' else window}
            else:
                version,field={'literature':('literature_assignment_v1','source_refs'),
                    'literature_strategy':('strategy_assignment_v1','prior_search_refs'),
                    'literature_search':('search_assignment_v1','search_result_refs')}[role]
                assignment={'version':version,'question_context_refs':[],field:[source['id']]}
            credit=own('literature_task_credit')
            task={'version':credit.VERSION,'evidence_axis':'A102','credit_unit':2.5,
                'kind':'verified_source_leads' if task_kind=='verified_source_leads' else 'source_answer'}
            if task_kind=='assessment':task.update(answer_kind='assessment',source_refs=[source['id']])
            elif task_kind=='screening':task.update(answer_kind='screening',examined=[{
                'source_ref':source['id'],'artifact_ref':artifact,'start':0,'end':len(raw)}])
            task['yield_settings']={key:declarations[credit._task_key(task)][key] for key in ('kind','cutoff','uncertainty_alpha')}
            assignment.update(proposed_annotation_ref=proposed,literature_task=task)
            return_source=credit.LEADS if task_kind=='verified_source_leads' else 'changed_assessment_refs' if task_kind=='assessment' else credit.SCREENING
            result_schema=(credit.lead_return_schema() if task_kind=='verified_source_leads' else
                {'type':'array','x-source':return_source,'items':{'type':'string','format':'reference'}} if task_kind=='assessment'
                else credit.screening_schema())
            schema=own('domain').obj({'answers':result_schema});request=request_record(assignment,schema)
            request['message']['scope']=plain(scope)
            episode_id=own('method_loop.identities').EpisodeRef(host.run_id,path).episode_id
            context=own('episode_bindings').BindingContext(host.run_id,episode_id,role,path,scope,assignment,request)
            host.journal.save('runtime_episodes',{'episode_id':context.episode_id,'path':runtime._json(path),
                'request':runtime._json(request),'initial_credit':0.,'state':'active','completion':None,'archive':None})
            host.receipts.bind(context.episode_id)
            host.receipts.receive(context.episode_id,[subject,proposed,source['id'],artifact],kind='initial')
            context=replace(context,received_record_refs=tuple(host.receipts.known(context.episode_id)))
            yield SimpleNamespace(home=home,role=role,binding=binding,bindings=bindings,workflow=host,store=store,
                journal=host.journal,context=context,configuration=configuration,runtime=runtime,output=output,
                source=source,artifact=artifact,raw=raw,request=request,assignment=assignment,schema=schema,proposed=proposed)


def make_task(v):
    cls=getattr(v.binding,'decision_source_type',v.runtime.DecisionSource)
    request=SimpleNamespace(as_record=lambda:deepcopy(v.request),
        goal=SimpleNamespace(as_record=lambda:deepcopy(v.request['goal'])),
        message=SimpleNamespace(as_record=lambda:deepcopy(v.request['message'])),report_contract=None)
    task=cls(v.workflow,v.context.path,request,plain(v.context.scope))
    assert task.episode_id==v.context.episode_id and v.workflow.specialist(task) is v.binding
    if hasattr(v.binding,'decision_source_type'):
        assert not isinstance(task,v.runtime.DecisionSource)
    return task


def credit_view(v):
    context=v.workflow.binding_context(make_task(v));projector=v.workflow.scientific_projector_for_context(context)
    assert type(projector) is own('literature_task_credit').LiteratureTaskCredit
    request=plain(context.request);assignment={'goal':request['goal'],'scope':plain(context.scope),
        'purpose':request['report_contract']['decision'],'schema':request['report_contract']['measurements']['schema'],
        'initial_report':request['message']['initial_report'],'proposed_annotation_ref':v.proposed}
    result=projector(v.store,plain(context.scope),known_record_refs=context.received_record_refs,assignment=assignment,
        episode_id=context.episode_id,run_id=context.run_id)
    assert set(result)=={'credit','scope','proposed_annotation_ref','policy','task_status','unresolved','source_contributions','commission_ref'}
    assert result['policy']['credit_unit']==2.5 and result['policy']['activity_credit'] is False
    return result


def action_trace(v,status='completed',kind='tool',saved='fresh'):
    task=make_task(v);host=v.workflow;executions=[];received=[];scored=[];projections=[]
    async def execute(source,name,arguments,**kwargs):
        executions.append(kwargs['operation_key'])
        return {'status':status,'record_refs':[],'changed_record_refs':[],'feedback':{'code':'controlled_returned_outcome'}}
    async def wait(source,condition,index):
        executions.append({'wait':deepcopy(condition),'index':index})
        return {'status':status,'record_refs':[],'changed_record_refs':[],'feedback':{'code':'controlled_saved_wait'}}
    host.execute=execute;host.perform_selected_wait=wait
    original_receive=host.receive_outcome;original_score=host.automatic_score_updates;original_credit=host.source_credit_view
    def receive(source,selection,result,index):
        received.append((index,result['status']));return original_receive(source,selection,result,index)
    async def score(source,index,result):
        scored.append(index);return await original_score(source,index,result)
    def project(source):
        projections.append(credit_view(v));return original_credit(source)
    host.receive_outcome=receive;host.automatic_score_updates=score;host.source_credit_view=project
    commit={key:[] for key in v.store.reasoning_schema()['properties']}
    selection=({'kind':'reason','commit':commit} if kind=='reason' else
        {'kind':'wait','condition':{'original_target':'controlled_wait'}} if kind=='wait' else
        {'kind':'tool','tool':'fixture.inspect','arguments':{'original_request':True}})
    index=4
    if saved!='fresh':
        recorded={'status':status,'record_refs':[],'changed_record_refs':[],'feedback':{'code':'saved_original_outcome'}}
        v.journal.save('runtime_actions',{'episode_id':task.episode_id,'decision_index':index,'action':v.runtime._json(selection),
            'result':None if saved=='unfinished' else v.runtime._json(recorded),'credit':None})
    if (kind,status,saved)==('wait','failed','result'):
        # The original iterator does not observe a failed wait. A saved failed
        # wait raises the same ActionFailure without acquisition or projection.
        saved_row=deepcopy(v.journal.row('runtime_actions',task.episode_id,index))
        assert saved_row['action']==v.runtime._json(selection)
        assert saved_row['result']==v.runtime._json(recorded) and saved_row['credit'] is None
        expected={'status':'raised','type':PREFIX+'.runtime.ActionFailure',
            'message':v.runtime._json(recorded['feedback']),'code':None}
        observations=[]
        with patch.object(host,'last_observed_credit',wraps=host.last_observed_credit) as wait_credit:
            for invoke in (
                lambda:asyncio.run(task.execute(selection,index)),
                lambda:asyncio.run(task.execute(selection,index)),
                lambda:asyncio.run(v.runtime.DecisionSource.execute(task,selection,index)),
            ):
                observed=capture(invoke)
                assert observed==expected,observed
                assert json.loads(observed['message'])==recorded['feedback']
                assert v.journal.row('runtime_actions',task.episode_id,index)==saved_row
                assert selection==json.loads(saved_row['action'])
                assert executions==received==scored==projections==[]
                assert wait_credit.call_count==0
                observations.append(observed)
        first,second,original_reference=observations
        assert first==second==original_reference==expected
        result=json.loads(saved_row['result'])
        assert result==recorded and result['status']=='failed' and saved_row['credit'] is None
        return {'selection':selection,'result':result,'credit':saved_row['credit'],'first':first,'second':second,
            'original_reference':original_reference,'executions':executions,'received':received,
            'scored':scored,'projections':projections,'feedback':task.feedback}
    first=capture(lambda:asyncio.run(task.execute(selection,index)))
    second=capture(lambda:asyncio.run(task.execute(selection,index)))
    row=v.journal.row('runtime_actions',task.episode_id,index);result=json.loads(row['result'])
    assert first['status']==second['status']=='returned' and first==second,(first,second)
    assert json.loads(row['action'])==selection and received==[(index,result['status'])]
    assert len(executions)==(0 if kind=='reason' or saved=='result' else 1)
    assert scored==([] if kind=='wait' else [index])
    assert len(projections)==(0 if kind=='wait' else 1)
    assert row['credit']==0.0 and result['status'] in STATUSES
    if kind!='reason' or saved=='result':assert result['status']==status
    return {'selection':selection,'result':result,'credit':row['credit'],'first':first,'second':second,
        'executions':executions,'received':received,'scored':scored,'projections':projections,'feedback':task.feedback}


def task_credit_trace(v):
    before=credit_view(v);assert before['credit']==0.0 and before['task_status']=='unanswered'
    controller=v.binding.yield_controller(v.context,0.,'original-yield-epoch')
    task=v.assignment['literature_task'];key=own('literature_task_credit').continuation_task(v.context)
    assert key in v.configuration['yield_bindings']
    missing=replace(v.context,assignment={key:value for key,value in plain(v.context.assignment).items() if key!='literature_task'})
    failure=capture(lambda:own('literature_task_credit').commissioned_task(missing))
    assert failure['status']=='raised' and failure['message']=='literature_original_task_credit_required'
    wrong=replace(v.context,run_id='foreign-run')
    projector=v.binding.credit_projector(wrong)
    assert type(projector) is own('literature_task_credit').LiteratureTaskCredit
    request=plain(v.context.request)
    assignment={'goal':request['goal'],'scope':plain(v.context.scope),
        'purpose':request['report_contract']['decision'],'schema':request['report_contract']['measurements']['schema'],
        'initial_report':request['message']['initial_report'],'proposed_annotation_ref':v.proposed}
    foreign=capture(lambda:projector(v.store,plain(v.context.scope),known_record_refs=v.context.received_record_refs,
        assignment=assignment,episode_id=v.context.episode_id,run_id=v.context.run_id))
    assert foreign['status']=='raised' and foreign['message']=='literature_task_credit_commission_mismatch'
    initial=plain(controller.state().as_record())
    step=plain(controller.observe('original-zero-credit',{'credit':before['credit']}).as_record())
    state=plain(controller.state().as_record())
    rebuilt=v.binding.yield_controller(v.context,0.,'original-yield-epoch')
    assert plain(rebuilt.state().as_record())==json.loads(json.dumps(initial,allow_nan=False))
    assert plain(rebuilt.observe('original-zero-credit',{'credit':before['credit']}).as_record())==step
    assert plain(rebuilt.state().as_record())==state
    return {'actual':before,'task_key':key,'controller_class':type(controller).__module__+'.'+type(controller).__qualname__,
        'missing_original_task':failure,'foreign_commission':foreign,'declared_yield':deepcopy(v.configuration['yield_bindings'][key]),
        'original_yield_initial_state':initial,'original_yield_step':step,'original_yield_recreated_state':state,
        'fresh_wait_offered':v.workflow.permits_common_action(make_task(v),'wait')}


def presentation_trace(v,case):
    connection=object.__new__(own('providers')._SessionConnection);connection.scientific_prompt_states={}
    episode_id=v.context.episode_id
    frames=own('decision_context')
    hpc={'hpc_commission':{},'execution_assignment':{'version':'api_service_assignment_v1','service':'ncbi_blast','request':{}},
        'api_service':'ncbi_blast','api_request':{}}
    context={'unrecognized':'source fixture'}
    if case=='source_marker':context={'literature_experimental_work':{'role':v.role}}
    elif case=='bootstrap_unrecognized':context=frames.state_frame({'unrecognized':True})
    elif case=='saved_unrecognized':
        connection.scientific_prompt_states[(episode_id,'REASONING')]={'unrecognized':'old'}
        context={'version':own('providers').DECISION_CONTEXT_VERSION,'kind':'decision_lookup_result','result':{'value':'lookup'}}
    elif case=='update_missing_base':context=frames.state_frame(hpc,{'previous':'unavailable'})
    elif case=='receiver_minimal':context={'goal':{'objective':'Inspect received original source'},'scope':plain(v.context.scope),
        'working_state':{'subjects':[],'scope':plain(v.context.scope)},'tools':[],'requested_form':None,
        'controller':{},'current_report_update':{},'last_local_outcome':None}
    elif case=='priority_hpc_api':context=hpc
    elif case=='bootstrap_recognized':context=frames.state_frame(hpc)
    elif case=='saved_recognized':
        connection.scientific_prompt_states[(episode_id,'REASONING')]=deepcopy(hpc)
        context={'version':frames.VERSION,'kind':'decision_lookup_result','result':{'value':'original_lookup'}}
    elif case=='update_recognized':
        connection.scientific_prompt_states[(episode_id,'REASONING')]=deepcopy(hpc)
        context=frames.state_frame({**hpc,'last_local_outcome':{'status':'invalid'}},hpc)
    elif case=='restored_recognized':
        context={**frames.state_frame(hpc),'restored_public_exchanges':[{'lookup_result':{'original':True}}],
            'restored_pending_decision_index':4}
    elif case!='legacy_unrecognized':raise AssertionError(case)
    initial=deepcopy(connection.scientific_prompt_states)
    original=capture(lambda:connection._presentation(episode_id,'REASONING','Original instructions',deepcopy(context)))
    original_state=deepcopy(connection.scientific_prompt_states);connection.scientific_prompt_states=initial
    task=make_task(v)
    async def complete(episode,role,instructions,value,schema,**kwargs):
        return connection._presentation(episode,role,instructions,value,**kwargs)
    task.workflow.provider=SimpleNamespace(complete=complete,complete_with_presentation=complete)
    # Exercise the real private completion method, not a provider double that
    # merely accepts and records a renderer argument.
    if hasattr(task,'complete_decision'):
        current=capture(lambda:asyncio.run(task.complete_decision('Original instructions',deepcopy(context),{})))
    else:current=capture(lambda:asyncio.run(complete(episode_id,'REASONING','Original instructions',deepcopy(context),{})))
    assert current==original and connection.scientific_prompt_states==original_state
    if case=='update_missing_base':assert original['status']=='raised'
    elif case in {'priority_hpc_api','bootstrap_recognized','saved_recognized','update_recognized','restored_recognized','receiver_minimal'}:
        assert original['status']=='returned' and original['value'][0].startswith('TASK')
    else:assert original['status']=='returned' and original['value'][0]==json.dumps(context,allow_nan=False)
    return {'context':context,'actual_original':original,'actual_selected':current,
        'cache':[[list(key),value] for key,value in sorted(original_state.items())]}


def exchange_trace(v,child_role,redelivery):
    task=make_task(v);registry=v.workflow.episode_bindings
    child=registry.for_child(task.path,child_role);child_home=child.binding_path
    assert child.commissioning_parent==v.home
    with fixture(child_home,v.output/'child') as child_case:
        assignment=deepcopy(child_case.assignment)
        schema=deepcopy(child_case.schema)
        # Rebind operands into the same Store; never compare different fixture identities by aliases.
        assert child_case.proposed==v.proposed and child_case.source['id']==v.source['id']
        admitted=capture(lambda:child.prepare_assignment(v.context,child_role,assignment,plain(v.context.scope),'original-parent:3'))
    assert admitted['status']=='returned',admitted
    assignment=admitted['value'];form={key:[] for key in schema['properties']}
    child_path=task.path+((child_role,'original-child'),)
    child_id=own('method_loop.identities').EpisodeRef(v.workflow.run_id,child_path).episode_id
    child_request=request_record(assignment,schema);child_request['message']['scope']=plain(v.context.scope)
    child_request['message']['initial_report']={}
    v.journal.save('runtime_episodes',{'episode_id':child_id,'path':v.runtime._json(child_path),
        'request':v.runtime._json(child_request),'initial_credit':0.,'state':'active','completion':None,'archive':None})
    v.workflow.receipts.bind(child_id)
    v.workflow.receipts.receive(child_id,list(v.context.received_record_refs),kind='initial')
    child_context=replace(v.context,episode_id=child_id,role=child_role,path=child_path,
        assignment=assignment,request=child_request,received_record_refs=tuple(v.workflow.receipts.known(child_id)))
    outgoing=capture(lambda:child.validate_report(child_context,form,schema))
    assert outgoing['status']=='returned',outgoing
    construction=[];pins=[]
    class ConstructionBoundary(Exception):pass
    def capture_build(role,key,goal,scope,**kwargs):
        construction.append({'role':role,'key':key,'goal':goal,'scope':plain(scope),
            'parent_path':plain(kwargs['parent_path']),'episode_assignment':deepcopy(kwargs['episode_assignment']),
            'initial':deepcopy(kwargs['initial']),'contract':kwargs['contract'].as_record()})
        raise ConstructionBoundary('observed_original_child_construction_boundary')
    selection={'kind':'episode_child','role':child_role,'goal':'Inspect the original source question',
        'purpose':'Decide whether further examination is useful','scope':plain(v.context.scope),'assignment':assignment,
        'schema_json':v.runtime._json(schema),'initial_report_json':'{}'}
    v.workflow.launch_instructions=SimpleNamespace(materialize=lambda selected:pins.append(selected))
    with patch.object(v.workflow,'build',capture_build):
        assembly=capture(lambda:v.workflow.selected(task,selection,2))
    assert len(construction)==1,(assembly,admitted)
    assert assembly['status']=='raised' and assembly['message']=='observed_original_child_construction_boundary'
    assert construction[0]['role']==child_role and construction[0]['episode_assignment']==admitted['value']
    assert pins==[None]
    index=3
    v.journal.save('runtime_actions',{'episode_id':task.episode_id,'decision_index':index,
        'action':v.runtime._json({'kind':'episode_child','role':child_role,'assignment':assignment}), 'result':None,'credit':None})
    assert own('delivery_counterpart').child_role_for_delivery(v.workflow,task,index)==child_role
    # The original child lead declaration carries zero records. Force redelivery
    # on the baseline oracle to bypass the independent admission-cache shortcut only
    # when that is the actual requested mode; all ordinary receipt methods stay real.
    receive=capture(lambda:v.workflow._receive_form(task,form,schema,index,redelivery=redelivery))
    repeated=capture(lambda:v.workflow._receive_form(task,form,schema,index,redelivery=redelivery))
    assert receive==repeated=={'status':'returned','value':[]},(receive,repeated)
    return {'parent':v.home,'child':child_home,'child_role':child_role,'assignment':assignment,
        'original_parent_request_assembly':construction,'original_parent_selection':selection,
        'incoming_child_admission':admitted,'outgoing_child_report':outgoing,'parent_receive':receive,
        'repeat_receive':repeated,'redelivery':redelivery,'original_counterpart':child_role,
        'child_episode_id':child_id,'child_context':child_context.as_record()}


def instructions_trace(v,exchange):
    task=make_task(v);host=v.workflow
    host.decision_protocol='decision_exchange_v1' if exchange else None
    host.knowledge=SimpleNamespace(instructions=' Fixture tool information.')
    host.launch_instructions=SimpleNamespace(instructions=' Fixture launch information.')
    context={'tool_knowledge':{},'launch_instruction_library':{}}
    expected=own('runtime_prompt').instructions(task,context)
    actual=task.instructions(context)
    assert actual==expected and own('runtime_prompt').REASONING_COMMIT_REQUIREMENT in actual
    assert not host.permits_common_action(task,'wait')
    return {'instructions':actual,'exchange':exchange,'fresh_wait_offered':False}


def saved_state_trace(v):
    task=make_task(v);index=8
    result={'status':'invalid','record_refs':[],'changed_record_refs':[],
        'feedback':{'code':'original_saved_invalid'}}
    v.journal.save('runtime_actions',{'episode_id':task.episode_id,'decision_index':index,
        'action':v.runtime._json({'kind':'tool','tool':'fixture.inspect','arguments':{}}),
        'result':v.runtime._json(result),'credit':0.})
    task._restored_source_state={'last_outcome_index':index,'feedback':deepcopy(result['feedback'])}
    task.restore_checkpoint()
    assert task.last_outcome==result and task.last_outcome_index==index
    assert task.feedback==result['feedback'] and task._restored_source_state is None
    task.restore_checkpoint();assert task.last_outcome==result
    token=object();task.bind_execution_context(token);assert task._execution_context is token
    calls=[];handle=object();v.workflow.execution_handle=handle
    def suspension(actual,value):
        assert actual is handle;calls.append(deepcopy(value))
    v.workflow.execution_backend=SimpleNamespace(set_suspension=suspension)
    condition={'original_saved_dependency':True}
    task.suspension_changed(condition);assert task._suspension_condition is condition
    task.suspension_changed(None);assert task._suspension_condition is None
    assert calls==[{'episode_id':task.episode_id,'dependency':condition},None]
    form={key:[] for key in v.schema['properties']}
    task.request.report_contract=SimpleNamespace(schema=deepcopy(v.schema))
    v.journal.save('runtime_forms',{'episode_id':task.episode_id,'facts':'{}','form':v.runtime._json(form)})
    v.workflow.facts=forbidden;released=[]
    async def release(episode_id):released.append(episode_id)
    v.workflow.release=release
    finished=capture(lambda:asyncio.run(task.finish(v.runtime.Record({'credit':0.}))))
    repeated=capture(lambda:asyncio.run(task.finish(v.runtime.Record({'credit':0.}))))
    assert finished==repeated=={'status':'returned','value':{'form':form}}
    assert released==[task.episode_id,task.episode_id]
    assert json.loads(v.journal.row('runtime_forms',task.episode_id)['form'])==form
    return {'outcome':task.last_outcome,'outcome_index':task.last_outcome_index,'feedback':task.feedback,
        'suspension':calls,'saved_form':form,'finish':finished,'repeat_finish':repeated,'released':released}


def scientific_trace(v):
    """Original scientific contracts, including a returned invalid interpretation.

    A retained source subject and qualification are fixture operands, not a claim
    that A102's structural numeric components establish biological target support.
    """
    task=make_task(v);kind=v.assignment['literature_task'].get('answer_kind','verified_source_leads')
    before=credit_view(v)
    commit={key:[] for key in v.store.reasoning_schema()['properties']}
    anchor={'source_ref':v.source['id'],'artifact_ref':v.artifact,'start':0,'end':len(v.raw)}
    commit['source_subjects']=[{'alias':'construct','reference_type':'construct','source_ref':v.source['id'],
        'label':'Original synthetic source subject','anchor':anchor}]
    if kind=='assessment':
        commit['observations']=[{'alias':'observed','subject_refs':['@construct'],'source_subject_refs':['@construct'],
            'kind':'source_content','source_ref':v.source['id'],'measurements':[],'dependencies':[],'anchor':anchor}]
        commit['assessments']=[{'alias':'qualified','hypothesis_ref':v.proposed,'observation_ref':'@observed',
            'relation':'mixed','applicability':'scope_limited','condition_refs':[],'assumption_refs':[],
            'extent_basis':'observed_extent','expected_revision':0,'investigation_finding':{
                'source_claim':{'subject_refs':['@construct'],'predicate':'sequence_integrity',
                    'value':{'type':'enum','value':'unknown'},'context_refs':[]},
                'qualification':{'kind':'measurement_does_not_establish_claim','context_refs':[],'assumption_refs':[]},
                'status':'retained','withdrawal_reason':'not_withdrawn','same_source_claim_as_ref':None,'replaces_refs':[]}}]
    selection={'kind':'reason','commit':commit}
    if kind=='verified_source_leads':
        selection['source_lead']={'proposed_annotation_ref':v.proposed,'source_ref':v.source['id'],'subject_ref':'@construct',
            'disposition':'relevant','relevance_rationale':'The exact source-bound synthetic subject is the selected engineering question.',
            'witness':{'source_ref':v.source['id'],'representation':'original','start':0,'end':len(v.raw)}}
    if kind=='screening':
        selection['evidence_processing']={'kind':'no_applicable_evidence','reason':'The engineering source explicitly contains no biological result.',
            'examined':[{'source_ref':v.source['id'],'representation':'original','start':0,'end':len(v.raw)}]}
    outcome=capture(lambda:asyncio.run(task.execute(selection,9)))
    row=v.journal.row('runtime_actions',task.episode_id,9)
    result=None if row is None or row['result'] is None else json.loads(row['result'])
    after=capture(lambda:credit_view(v))
    replay=capture(lambda:asyncio.run(task.execute(selection,9)))
    assert outcome==replay and outcome['status']=='returned',(outcome,replay)
    assert result is not None and json.loads(row['action'])==selection and result['status'] in STATUSES
    assert after['status']=='returned',after
    findings=[]
    for reference in (() if result is None else result.get('record_refs',())):
        record=v.store.get(reference)
        if record['record_type']=='assessment' and 'investigation_finding' in record:
            findings.append(record['investigation_finding'])
            assert record['investigation_finding']['qualification']['kind']=='measurement_does_not_establish_claim'
            assert record['investigation_finding']['source_claim']['subject_refs']!=list(v.context.scope['subject_refs'])
    # A returned invalid interpretation remains an executed original action.
    # Unexpected setup/credit exceptions are not admitted as scientific behavior;
    # preserve their baseline artifact and review an exact successor if encountered.
    return {'before':before,'selection':selection,'outcome':outcome,'result':result,'after':after,'replay':replay,
        'actual_typed_findings':findings,'automatic_scoring_declared':hasattr(v.binding,'automatic_score_judgments')}

"""Actual source-family private/default/custom instruction dispatch for every original home."""
from contextlib import ExitStack

INSTRUCTION_CASES=('default','instance_shadow','nonparticipant','nonparticipant_shadow',
    'custom_return','custom_raise','subclass_return','subclass_raise','custom_delegates')
def instruction_observation(v,case,exchange=False):
    assert case in INSTRUCTION_CASES
    task=make_task(v);host=v.workflow
    host.decision_protocol='decision_exchange_v1' if exchange else None
    host.knowledge=SimpleNamespace(instructions=' Fixture tool information.')
    host.launch_instructions=SimpleNamespace(instructions=' Fixture launch information.')
    default=own('episode_services').WorkflowServices
    assert type(host.services) is default
    if case.startswith('nonparticipant'):
        other=object.__new__(v.runtime.DecisionSource);other.__dict__.update(task.__dict__);task=other
    context={'tool_knowledge':{},'launch_instruction_library':{}}
    prompt=own('runtime_prompt');expected=prompt.instructions(task,context)
    selected=getattr(type(task),'instruction_composer',None)
    if selected is None:
        assert type(task) is v.runtime.DecisionSource
        original=prompt.instructions
    else:
        assert type(task) is own(v.home.replace('/','.')+'.task').SourceTask
        descriptor=vars(type(task))['instruction_composer'];assert isinstance(descriptor,staticmethod)
        original=own(v.home.replace('/','.')+'.task_instructions').compose_instructions
        assert descriptor.__func__ is selected is original
    events=[];marker=object();failure=ValueError('original_custom_source_instruction_failure')
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
