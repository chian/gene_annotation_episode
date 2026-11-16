"""Actual own-A102 scientific owners, build, Store/Journal and existing projectors.

Only the engineering tool's catalog/return and transport/release ports are
controlled. Instruction fixtures do not provide biological observations.
"""
import asyncio
from contextlib import contextmanager,ExitStack
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PREFIX='gene_annotation_episode.episodic_workflow.root.a102'
TASK_NAMES=('model_inventory','target_model_correspondence','synthesis','structural_discovery','native_comparison',
    'functional_feature_geometry','functional_contrast','reference_attribution','local_trait_attribution','interface_constraints',
    'experimental_source_discovery','experimental_model_identity','experimental_feature_geometry',
    'experimental_local_validation','experimental_assessment')
SCENARIOS=('original_instruction','merged_default',*TASK_NAMES)
ROOT_REQUIRES_COMMISSION={'functional_feature_geometry','functional_contrast','reference_attribution','local_trait_attribution','interface_constraints'}
STATUSES=('completed','partial','invalid','failed','unavailable')
def own(name):return import_module(PREFIX+'.'+name)
def plain(value):return own('communication').plain(value)
def forbidden(*args,**kwargs):raise AssertionError('no external acquisition in own-A102 scientific fixture')
def capture(callback):
    try:
        result=callback();return {'status':'returned','value':plain(result.as_record() if hasattr(result,'as_record') else result)}
    except Exception as error:return {'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,'message':str(error),'code':getattr(error,'code',None)}
@contextmanager
def actual(directory,scenario='original_instruction',standalone=False):
    from gene_annotation_episode.workflow_budget import active_budget
    from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import write_instruction_source
    directory=Path(directory).resolve();assert directory.is_relative_to(Path(active_budget()['run_directory']).resolve())
    directory.mkdir(parents=True,exist_ok=True)
    assert scenario in SCENARIOS
    with patch('subprocess.Popen',forbidden),patch('socket.socket.connect',forbidden),patch('socket.socket.connect_ex',forbidden):
        with own('state').Store(directory/'state') as store:
            problem=store.create_problem(raw_sequence='MACDEFGH',molecule='protein');target=problem['subject_refs'][0];scope=store.validate_scope()
            commit={key:[] for key in store.reasoning_schema()['properties']}
            commit['hypotheses']=[{'alias':'original','subject_refs':[target],'predicate':'sequence_integrity',
                'value':{'type':'enum','value':'unknown'},'context_refs':[]}]
            result=store.commit_reasoning(commit,scope,'original-head-commission');assert result['status'] in ('completed','partial')
            proposed=result['aliases']['original']
            instruction_source=directory/'instruction-source';write_instruction_source(instruction_source,'a102')
            merged=scenario!='original_instruction';structural=own('a102_structural_evidence')
            assert tuple(structural.TASKS)==TASK_NAMES
            if merged:
                path=instruction_source/'entries/A102.json';old=json.loads(path.read_bytes())
                entry=structural.merged_entry(old,{**deepcopy(old),'id':'A111'})
                path.write_text(json.dumps(entry)+'\n')
                index=json.loads((instruction_source/'index.json').read_bytes())
                evidence_ids=['E-A102-'+str(i+1).zfill(2) for i in range(len(entry['evidence']))]
                for item in index['entries']:
                    if item['id']=='A102':
                        item.update(name=entry['name'],description=entry['description'],source_evidence_ids=evidence_ids)
                sources_path=instruction_source/'option_sources.json'
                sources=json.loads(sources_path.read_bytes())
                sources['rows']=[row for row in sources['rows'] if row['option_id']!='A102']+[
                    {'evidence_id':evidence_id,'option_id':'A102',**deepcopy(evidence)}
                    for evidence_id,evidence in zip(evidence_ids,entry['evidence'])]
                sources_path.write_text(json.dumps(sources)+'\n')
                (instruction_source/'index.json').write_text(json.dumps(index)+'\n')
            library=own('scientific_process_library').ScientificProcessLibrary.freeze(directory/'scientific-library',source=instruction_source)
            catalog=[{'name':'fixture.inspect','resources':'local','description':'Return the explicitly controlled engineering outcome.',
                'instructions':'No external acquisition or biological inference.','input_schema':own('domain').obj({'record':{'type':'string'}})}]
            tools=own('scientific_tool_library').ScientificToolLibrary.freeze(directory/'tool-library',catalog=catalog)
            assignment_context={} if scenario in ('original_instruction','merged_default') else {'a102_task':structural.task_context(scenario)}
            assignment={'selection':{'version':own('scientific_process_records').SELECTION_VERSION,
                'evidence_axis':library.reference('A102'),'thought_pattern':library.reference('P01'),
                'child_tool_info':[{'name':'fixture.inspect','resources':'local'}]},'proposed_annotation_ref':proposed,
                'evidence_refs':[target,proposed],'constraints':{'fixture_only':True},'context':assignment_context}
            projector=own('scientific_process.task_projector').original_task_projector(assignment,merged_a102=merged)
            key='A102:'+(scenario if scenario in TASK_NAMES else projector.as_record()['kind'])
            declaration={'kind':projector.yield_method,'cutoff':.25,'parameters':{'uncertainty_alpha':.1},'credit_definition':projector.as_record()}
            runtime=own('runtime');host=object.__new__(runtime.Workflow);host.run_id='a102-scientific-head-fixture'
            host.store=store;host.directory=directory/'workflow';host.journal=own('episode_journal').Journal(store,host.run_id)
            host.receipts=own('episode_receipts').EpisodeReceipts(store,host.run_id);host.tools=SimpleNamespace()
            host.project_credit=projector;host.project_annotation_score=None;host.annotation_score_binding=None
            host.job_episodes=None;host.progress_provider=None;host.native_timing_information=None;host.native_event_information=None
            host.execution_binding=None;host.execution_handle=None;host.inprocess_replay=None;host.inprocess_completion_order=None
            host.wait_inputs_version=None;host.completed_action_inputs_version=None;host.progress_receipt_order='received_progress_order_v1'
            host.annotation_child_roles=None;host.decision_protocol=None;host.decision_exchanges=None;host.resource_estimator=None
            host.episode_branch_lifecycle=runtime.EPISODE_BRANCH_LIFECYCLE;host.initial_known_record_refs=(target,proposed)
            host.archive=runtime.JsonArchive(directory/'archive')
            host.launch_instructions=SimpleNamespace(materialize=lambda selected:None,instructions='Original empty fixture launch information.')
            host.services=own('episode_services').WorkflowServices(host)
            host.services.tool_catalog=lambda selected_scope:deepcopy(catalog)
            host.services.tool_information_catalog=lambda selected_scope:deepcopy(catalog)
            acquired=[];outcome={'status':'completed','record_refs':[],'changed_record_refs':[],
                'result':None,'feedback':{'code':'controlled_original_return'}}
            def execute_tool(name,arguments,**kwargs):
                acquired.append({'name':name,'arguments':deepcopy(arguments),'operands':plain(kwargs)});return deepcopy(outcome)
            host.services.execute_tool=execute_tool
            binding=own('scientific_process.episode').ScientificProcessEpisode(host.services,library=library,tool_library=tools,
                child_roles=('scientific_process',),yield_bindings={key:declaration})
            host.scientific_process_binding=binding;host.episode_bindings=own('episode_bindings').EpisodeBindingRegistry((binding,))
            host.grains={name:runtime.Grain(name,'Original scientific fixture action','Original typed fixture result',forbidden)
                for name in ('annotation','scientific_process')}
            graph={host.grains['annotation']:(host.grains['scientific_process'],),host.grains['scientific_process']:(host.grains['scientific_process'],)}
            if standalone:graph.pop(host.grains['annotation'])
            host.tree=runtime.EpisodeTree(host.grains['scientific_process' if standalone else 'annotation'],graph,self_nesting=('scientific_process',))
            host.context=runtime.ReleasingContext(tree=host.tree,run_id=host.run_id)
            parent_path=(('annotation','original-parent'),)
            parent_id=own('method_loop.identities').EpisodeRef(host.run_id,parent_path).episode_id
            parent=own('episode_bindings').BindingContext(host.run_id,parent_id,'annotation',parent_path,scope,
                {'proposed_annotation_ref':proposed},{},(target,proposed))
            host.receipts.bind(parent_id);host.receipts.receive(parent_id,[target,proposed],kind='initial')
            form=own('domain').obj({'status':{'type':'string','enum':['unresolved']}})
            invocation={'objective':'Preserve the original unresolved A102 question','purpose':'Return the original unresolved status',
                'report_schema':form,'initial_report':{'status':'unresolved'}}
            prepared=binding.prepare_invocation(parent,'scientific_process',assignment,scope,'original-head-commission',invocation=invocation)
            parent_goal=None if standalone else runtime.EpisodeGoal.root(objective='Original parent question',result_contract={'role':'annotation'})
            contract=runtime.TypedReportContract(invocation['purpose'],form,lambda reference:reference==target)
            try:
                episode=host.build('scientific_process','child_0',invocation['objective'],scope,parent=parent_goal,
                    parent_path=() if standalone else parent_path,contract=contract,initial=invocation['initial_report'],
                    episode_assignment=prepared['assignment'],scientific_process=prepared['scientific_process'])
            except own('a102_scoring').A102ScoringUnavailable as error:
                assert standalone and scenario in ROOT_REQUIRES_COMMISSION
                assert str(error)=='a102_credit_scope_differs_from_original_commission'
                assert acquired==[] and store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==0
                yield SimpleNamespace(binding=binding,projector=projector,scenario=scenario,standalone=standalone,
                    prepared=prepared,construction_failure={'type':type(error).__module__+'.'+type(error).__qualname__,
                        'message':str(error),'code':error.code})
                return
            assert not (standalone and scenario in ROOT_REQUIRES_COMMISSION),'original_missing_root_commission_behavior_changed'
            task=episode.source
            assert host.specialist(task) is binding and task.episode_id==own('method_loop.identities').EpisodeRef(host.run_id,task.path).episode_id
            binding.validate_execution_context(host.binding_context(task))
            yield SimpleNamespace(workflow=host,binding=binding,task=task,episode=episode,store=store,journal=host.journal,
                runtime=runtime,target=target,proposed=proposed,scenario=scenario,standalone=standalone,projector=projector,
                declaration=declaration,key=key,assignment=assignment,prepared=prepared,invocation=invocation,form=form,parent=parent,
                acquired=acquired,outcome=outcome,directory=directory)


def action(v,status,kind='tool',saved='fresh'):
    host=v.workflow;task=v.task;index=4;received=[];projected=[];scored=[];waits=[]
    original_receive=host.receive_outcome;original_credit=host.source_credit_view;original_score=host.automatic_score_updates
    def receive(source,selection,result,decision):received.append([decision,result['status']]);return original_receive(source,selection,result,decision)
    def project(source):result=original_credit(source);projected.append(deepcopy(result));return result
    async def score(source,decision,result):scored.append(decision);return await original_score(source,decision,result)
    async def execute(source,name,arguments,**kwargs):return await v.binding.execute(host.binding_context(source),name,arguments,kwargs['operation_key'])
    async def wait(source,condition,decision):waits.append([plain(condition),decision]);return deepcopy(v.outcome)
    host.receive_outcome=receive;host.source_credit_view=project;host.automatic_score_updates=score
    host.execute=execute;host.perform_selected_wait=wait;v.outcome['status']=status
    commit={key:[] for key in v.store.reasoning_schema()['properties']}
    selection=({'kind':'reason','commit':commit} if kind=='reason' else {'kind':'wait','condition':{'original_saved_dependency':True}} if kind=='wait'
        else {'kind':'tool','tool':'fixture.inspect','arguments':{'record':v.target}})
    if saved!='fresh':v.journal.save('runtime_actions',{'episode_id':task.episode_id,'decision_index':index,
        'action':v.runtime._json(selection),'result':None if saved=='unfinished' else v.runtime._json(v.outcome),'credit':None})
    if (kind,status,saved)==('wait','failed','result'):
        # Preserve the original saved-failed-wait exception and unchanged journal.
        saved_row=deepcopy(v.journal.row('runtime_actions',task.episode_id,index))
        assert saved_row['action']==v.runtime._json(selection)
        assert saved_row['result']==v.runtime._json(v.outcome) and saved_row['credit'] is None
        expected={'status':'raised','type':PREFIX+'.runtime.ActionFailure',
            'message':v.runtime._json(v.outcome['feedback']),'code':None}
        observations=[]
        with patch.object(host,'last_observed_credit',wraps=host.last_observed_credit) as wait_credit:
            for invoke in (
                lambda:asyncio.run(task.execute(selection,index)),
                lambda:asyncio.run(task.execute(selection,index)),
                lambda:asyncio.run(v.runtime.DecisionSource.execute(task,selection,index)),
            ):
                observed=capture(invoke)
                assert observed==expected,observed
                assert json.loads(observed['message'])==v.outcome['feedback']
                assert v.journal.row('runtime_actions',task.episode_id,index)==saved_row
                assert selection==json.loads(saved_row['action'])
                assert v.acquired==received==projected==scored==waits==[]
                assert wait_credit.call_count==0
                observations.append(observed)
        first,second,original_reference=observations
        assert first==second==original_reference==expected
        result=json.loads(saved_row['result'])
        assert result==v.outcome and result['status']=='failed' and saved_row['credit'] is None
        return {'selection':selection,'result':result,'credit':saved_row['credit'],'first':first,'second':second,
            'original_reference':original_reference,'acquired':v.acquired,'received':received,
            'projected':projected,'scored':scored,'waits':waits,'feedback':task.feedback}
    first=capture(lambda:asyncio.run(task.execute(selection,index)));second=capture(lambda:asyncio.run(task.execute(selection,index)))
    assert first==second and first['status']=='returned',(first,second)
    row=v.journal.row('runtime_actions',task.episode_id,index);result=json.loads(row['result'])
    assert json.loads(row['action'])==selection and row['credit']==0. and received==[[index,result['status']]]
    assert len(v.acquired)==(1 if kind=='tool' and saved!='result' else 0)
    assert len(waits)==(1 if kind=='wait' and saved!='result' else 0)
    assert len(projected)==len(scored)==(0 if kind=='wait' else 1)
    if kind!='reason' or saved=='result':assert result['status']==status
    return {'selection':selection,'result':result,'credit':row['credit'],'first':first,'second':second,
        'acquired':v.acquired,'received':received,'projected':projected,'scored':scored,'waits':waits,'feedback':task.feedback}


def instructions(v,exchange=False):
    host=v.workflow;host.decision_protocol='decision_exchange_v1' if exchange else None
    host.knowledge=SimpleNamespace(instructions='Original empty tool information.')
    context={'tool_knowledge':{},'launch_instruction_library':{}}
    original=own('runtime_prompt').instructions(v.task,context);selected=v.task.instructions(context)
    assert selected==original
    bound=host.binding_context(v.task)
    assert set(v.binding.permitted_common_actions(bound))=={'tool','reason','child','wait','redeliver_report'}
    assert v.binding.allowed_children(bound,None)==('scientific_process',)
    return {'instructions':selected,'exchange':exchange,'goal':v.binding.instructions(bound),
        'initial_context':v.binding.initial_decision_context(bound),'summary':v.binding.decision_context(bound,None)}


INSTRUCTION_SERVICES=('default','instance_shadow','nonparticipant','nonparticipant_shadow',
    'custom_return','custom_raise','subclass_return','subclass_raise','custom_delegates')
def instruction_service(v,case,exchange=False):
    assert case in INSTRUCTION_SERVICES
    host=v.workflow;host.decision_protocol='decision_exchange_v1' if exchange else None
    host.knowledge=SimpleNamespace(instructions='Original empty tool information.')
    context={'tool_knowledge':{},'launch_instruction_library':{}}
    task=v.task
    if case.startswith('nonparticipant'):
        task=object.__new__(own('runtime').DecisionSource);task.__dict__.update(v.task.__dict__)
    prompt=own('runtime_prompt');default=own('episode_services').WorkflowServices
    expected=prompt.instructions(task,context)
    selected=getattr(type(task),'instruction_composer',None)
    if selected is None:
        assert type(task) is own('runtime').DecisionSource
        original=prompt.instructions
    else:
        assert type(task) is own('scientific_process.task').ScientificProcessTask
        descriptor=vars(type(task))['instruction_composer'];assert isinstance(descriptor,staticmethod)
        original=own('scientific_process.task_instructions').compose_instructions
        assert descriptor.__func__ is selected is original
    events=[];marker=object();failure=ValueError('original_custom_instruction_failure')
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
        if case.startswith('subclass'):
            service=CustomServices(host)
            stack.enter_context(patch.object(host,'services',service))
        elif case.startswith('custom'):
            stack.enter_context(patch.object(host,'services',SimpleNamespace(instructions=custom)))
        if case.endswith('raise'):
            try:task.instructions(context)
            except ValueError as error:
                assert error is failure and type(error) is ValueError
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


PRESENTATIONS=('unrecognized','bootstrap_unrecognized','scientific','scientific_bootstrap','scientific_update',
    'scientific_lookup','lost_scientific_task','hpc_priority','missing_base')
def presentation(v,case):
    context=v.workflow.binding_context(v.task);frames=own('decision_context')
    state={'goal':{'objective':v.invocation['objective']},'scope':plain(context.scope),**v.binding.decision_context(context,None)}
    connection=object.__new__(own('providers')._SessionConnection);connection.scientific_prompt_states={}
    key=(v.task.episode_id,'REASONING')
    value=deepcopy(state)
    if case=='unrecognized':value={'unrecognized':True}
    elif case=='bootstrap_unrecognized':value=frames.state_frame({'unrecognized':True})
    elif case=='scientific_bootstrap':value=frames.state_frame(state)
    elif case in ('scientific_update','scientific_lookup','lost_scientific_task'):
        connection.scientific_prompt_states[key]=deepcopy(state)
        value=({'version':frames.VERSION,'kind':'decision_lookup_result','result':{'original_fixture':True}}
            if case=='scientific_lookup' else frames.state_frame({} if case=='lost_scientific_task' else {**state,'last_local_outcome':{'status':'invalid'}},state))
    elif case=='hpc_priority':value={**state,'hpc_commission':{'objective':'Original higher priority'}}
    elif case=='missing_base':value=frames.state_frame(state,{'previous':'unavailable'})
    elif case!='scientific':raise AssertionError(case)
    initial=deepcopy(connection.scientific_prompt_states)
    original=capture(lambda:connection._presentation(v.task.episode_id,'REASONING','Original scientific instructions',deepcopy(value)))
    original_cache=deepcopy(connection.scientific_prompt_states);connection.scientific_prompt_states=initial
    async def complete(episode,role,guidance,model_context,schema,**kwargs):
        return connection._presentation(episode,role,guidance,model_context,**kwargs)
    v.workflow.provider=SimpleNamespace(complete=complete,complete_with_presentation=complete)
    actual=(capture(lambda:asyncio.run(v.task.complete_decision('Original scientific instructions',deepcopy(value),{})))
        if hasattr(v.task,'complete_decision') else capture(lambda:asyncio.run(complete(v.task.episode_id,'REASONING','Original scientific instructions',deepcopy(value),{}))))
    assert actual==original and connection.scientific_prompt_states==original_cache
    if case=='missing_base':assert actual['status']=='raised'
    elif case in ('unrecognized','bootstrap_unrecognized','lost_scientific_task'):
        assert actual=={'status':'returned','value':[json.dumps(value,allow_nan=False),'Original scientific instructions']}
    else:assert actual['status']=='returned' and actual['value'][0].startswith('TASK')
    return {'context':value,'original':original,'actual':actual,'cache':[[list(k),data] for k,data in sorted(original_cache.items())]}


def saved_model(v,declared,answered):
    task=v.task;context={'scope':plain(task.scope),**v.binding.decision_context(v.workflow.binding_context(task),None)}
    schema=v.runtime._object({'selection':v.runtime._object({'kind':{'const':'tool'},'tool':{'const':'fixture.inspect'},
        'arguments':v.runtime._object({'record':{'type':'string'}})}),'report_update':v.runtime._object({})})
    response={'selection':{'kind':'tool','tool':'fixture.inspect','arguments':{'record':v.target}},'report_update':{}}
    v.journal.save('runtime_model_calls',{'episode_id':task.episode_id,'call_index':0,'purpose':'decision',
        'request':v.runtime._json({'context':context,'schema':schema}),'response':v.runtime._json(response) if answered else None})
    connection=object.__new__(own('providers')._SessionConnection);connection.scientific_prompt_states={};calls=[]
    async def complete(episode,role,guidance,value,output_schema,**kwargs):
        calls.append(connection._presentation(episode,role,guidance,value,**kwargs));return deepcopy(response)
    v.workflow.provider=SimpleNamespace(has_session=lambda *args:True,complete=complete)
    if declared:v.workflow.provider.complete_with_presentation=complete
    first=capture(lambda:asyncio.run(task.call({},schema)));task.calls=0
    second=capture(lambda:asyncio.run(task.call({},schema)))
    assert first==second and first['status']=='returned'
    assert len(calls)==(0 if answered else 1) and v.acquired==[]
    assert v.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==0
    return {'context':context,'response':response,'first':first,'second':second,'presentations':plain(calls),'answered':answered,'declared':declared}


def saved_state(v):
    task=v.task;result={'status':'invalid','record_refs':[],'changed_record_refs':[],'feedback':{'code':'saved_original_invalid'}}
    v.journal.save('runtime_actions',{'episode_id':task.episode_id,'decision_index':8,
        'action':v.runtime._json({'kind':'tool','tool':'fixture.inspect','arguments':{'record':v.target}}),
        'result':v.runtime._json(result),'credit':0.})
    task._restored_source_state={'last_outcome_index':8,'feedback':deepcopy(result['feedback'])};task.restore_checkpoint()
    assert task.last_outcome==result and task.feedback==result['feedback'] and task._restored_source_state is None
    task.restore_checkpoint();assert task.last_outcome_index==8
    token=object();task.bind_execution_context(token);assert task._execution_context is token
    suspension=[];handle=object();v.workflow.execution_handle=handle
    def change(actual,value):assert actual is handle;suspension.append(deepcopy(value))
    v.workflow.execution_backend=SimpleNamespace(set_suspension=change)
    condition={'original_dependency':True};task.suspension_changed(condition);task.suspension_changed(None)
    assert suspension==[{'episode_id':task.episode_id,'dependency':condition},None]
    form=deepcopy(v.invocation['initial_report']);v.journal.save('runtime_forms',{'episode_id':task.episode_id,'facts':'{}','form':v.runtime._json(form)})
    released=[]
    async def release(episode):released.append(episode)
    v.workflow.provider=SimpleNamespace(release=release);v.workflow.facts=forbidden
    first=capture(lambda:asyncio.run(task.finish(v.runtime.Record({'credit':0.}))))
    second=capture(lambda:asyncio.run(task.finish(v.runtime.Record({'credit':0.}))))
    assert first==second=={'status':'returned','value':{'form':form}}
    assert released==[task.episode_id,task.episode_id]
    return {'result':result,'feedback':task.feedback,'last_outcome_index':task.last_outcome_index,
        'suspension':suspension,'form':form,'first':first,'second':second,'released':released}


def monitor_exchange(v,role):
    context=v.workflow.binding_context(v.task)
    assignment={'version':'monitor_assignment_v1','target_handle':'original-owned-handle','requested_fields':['execution_status'],
        'known_progress_refs':[],'permitted_committed_record_types':[]}
    prepared=v.binding.prepare_child_request(context,role,assignment)
    assert prepared==assignment
    received=[];provider=SimpleNamespace(read_progress=forbidden,_receive_progress=lambda *args:received.append(plain(args)))
    schema=v.runtime._object({});outcome=v.binding.receive_child_progress_for_role(context,role,{},schema,'original-monitor-delivery',provider)
    assert outcome is (role=='monitor')
    signature=own('method_loop.durable').content_digest({'form':{},'schema':schema,'scope':plain(context.scope)})
    assert received==([[v.task.episode_id,[],signature,'original-monitor-delivery']] if role=='monitor' else [])
    return {'role':role,'assignment':assignment,'prepared':prepared,'outcome':outcome,'received':received}


def incoming_rejection(v,operand):
    context=v.workflow.binding_context(v.task);request=plain(context.request)
    if operand=='assignment':
        assignment=plain(context.assignment);assignment['selection']['thought_pattern']=v.binding.library.reference('P02')
        altered=replace(context,assignment=assignment)
    elif operand=='purpose':
        request['report_contract']['decision']='Different original meaning';altered=replace(context,request=request)
    elif operand=='path':altered=replace(context,path=context.path[:-1]+(('scientific_process','foreign-child'),))
    else:raise AssertionError(operand)
    failure=capture(lambda:v.binding.validate_context(altered))
    expected_type='builtins.ValueError' if operand=='path' else PREFIX+'.domain.ContractError'
    expected_message='scientific_closed_request_identity_mismatch' if operand=='path' else 'scientific_filled_identity_mismatch'
    assert failure['status']=='raised' and failure['type']==expected_type and failure['message']==expected_message
    assert v.acquired==[] and v.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==0
    return {'operand':operand,'failure':failure}


def revision(v):
    context=v.workflow.binding_context(v.task);before=context.as_record()
    arguments={'thought_pattern':v.binding.library.reference('P02'),'child_tool_info':[{'name':'fixture.inspect','resources':'local'}]}
    result=asyncio.run(v.binding.execute(context,'process.revise',arguments,'original-revision-operation'))
    assert result['status']=='completed' and result['record_refs']==result['changed_record_refs']==[] and v.acquired==[]
    assert context.as_record()==before
    assert result['result']['parent_selection_sha256']==own('scientific_process_records').scientific_digest(plain(context.assignment['selection']))
    assert result['result']['selection']['evidence_axis']==context.assignment['selection']['evidence_axis']
    assert result['result']['selection']['thought_pattern']==arguments['thought_pattern']
    return {'arguments':arguments,'result':result,'assignment_after':plain(context.assignment)}


def ready_child(v):
    calls=[];child=object()
    v.task._execution_context=SimpleNamespace(_ready_owned_child=lambda path:calls.append(plain(path)) or child)
    result=asyncio.run(v.task.next(SimpleNamespace(units_consumed=0)))
    assert result is child and calls==[plain(v.task.path)] and v.task.calls==0 and v.acquired==[]
    return {'returned_original_child':True,'paths':calls,'model_calls':v.task.calls}


def next_context(v):
    host=v.workflow
    # View-only engineering ports keep this a single task-context construction;
    # actual scientific projection, binding summary and task.next remain real.
    host.working_state=lambda source:{};host.local_outcome_preview=lambda value,**kwargs:value
    host.pending_work=lambda source:{'version':'pending_work_v2','captured_at':'controlled-fixture-clock','items':[]}
    host.delivery_status=lambda episode:[];host.controller_binding=None
    host.catalog=lambda scope,source:v.binding.catalog(host.binding_context(source))
    host.knowledge=SimpleNamespace(context=lambda:{},instructions='Original fixture tool information.')
    host.job_episode_options=lambda source:[];host.extra_report_sources=lambda source:{}
    host.annotation_context=lambda scope,source:{};host.action_schema=lambda source:v.runtime._object({})
    view=SimpleNamespace(units_consumed=0,child_reports=(),controller_state={},model_inputs=lambda fields,**kwargs:fields)
    captured=[]
    class ContextBoundary(Exception):pass
    async def receive(value,schema):captured.append({'context':deepcopy(value),'schema':deepcopy(schema)});raise ContextBoundary('original_context_ready')
    v.task.call=receive
    result=capture(lambda:asyncio.run(v.task.next(view)))
    assert result['status']=='raised' and result['message']=='original_context_ready' and len(captured)==1
    context=captured[0]['context']
    assert context['current_credit']==0. and context['credit_binding']==v.projector.as_record()
    assert context['scientific_process']==v.binding.decision_context(host.binding_context(v.task),view)['scientific_process']
    assert context['requested_report_purpose']==v.invocation['purpose'] and context['current_report_update']=={'status':'unresolved'}
    assert v.acquired==[]
    return captured[0]


def cold_import(directory,order):
    import os
    import subprocess
    import sys
    from gene_annotation_episode.workflow_budget import active_budget
    directory=Path(directory).resolve();assert directory.is_relative_to(Path(active_budget()['run_directory']).resolve())
    directory.mkdir(parents=True,exist_ok=True)
    assert order in ('head_first','runtime_first')
    source="import importlib,json; p='"+PREFIX+"'; first='"+('scientific_process.episode' if order=='head_first' else 'runtime')+"'; importlib.import_module(p+'.'+first); h=importlib.import_module(p+'.scientific_process.episode'); r=importlib.import_module(p+'.runtime'); t=getattr(h.ScientificProcessEpisode,'decision_source_type',r.DecisionSource); assert t is r.DecisionSource or (t.__name__=='ScientificProcessTask' and t.__module__==p+'.scientific_process.task'); print(json.dumps({'binding':h.ScientificProcessEpisode.__module__+'.'+h.ScientificProcessEpisode.__qualname__,'valid_original_or_private_task':True}))"
    environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(directory),'XDG_CACHE_HOME':str(directory/'cache')}
    result=subprocess.run([sys.executable,'-B','-c',source],env=environment,text=True,capture_output=True)
    assert result.returncode==0,(result.stdout,result.stderr)
    return {'order':order,'result':json.loads(result.stdout),'stderr':result.stderr}
