"""Reusable controlled A110 source behavior checks; no autonomous-science claim.

Each episode imports these checks through its own tests and supplies its actual
binding type. The sources, service port outcomes and numerical credit below are
controlled fixtures. Actual admission, private task code, SQLite journal and
completed outcome replay execute unchanged.
"""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import pytest

from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, identity
from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a110.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.a110.state import Store

ROWS = json.loads((Path(__file__).parent / 'fixtures/private_literature/original_source_contracts.json').read_text())
SOURCE = identity('source', {'fixture': 'a110 private original source'})
OTHER = identity('source', {'fixture': 'a110 distinct source'})
ARTIFACT = identity('artifact', {'fixture': 'a110 source bytes'})
RECORDS = {
    SOURCE: {'id': SOURCE, 'record_type': 'source', 'artifact_ref': ARTIFACT,
        'text_ref': ARTIFACT, 'version': 'controlled_source_v1', 'parent_source_refs': []},
    OTHER: {'id': OTHER, 'record_type': 'source', 'artifact_ref': ARTIFACT,
        'text_ref': ARTIFACT, 'version': 'controlled_source_v1', 'parent_source_refs': []},
    ARTIFACT: {'id': ARTIFACT, 'record_type': 'artifact', 'size': 120},
}
PAGE = {'version': 'page_assignment_v1', 'source_ref': SOURCE, 'representation': 'text',
    'artifact_ref': ARTIFACT, 'question_context_refs': [], 'prior_delivery_refs': []}


def assignment(role):
    if role == 'literature_page': return deepcopy(PAGE)
    if role in {'literature_table', 'literature_ordered', 'literature_targeted'}:
        window = {'source_ref': SOURCE, 'representation': 'text', 'offset': 0, 'limit': 20}
        selected = {'spans': [window]} if role == 'literature_targeted' else window
        return {'version': 'reading_assignment_v1', 'page': deepcopy(PAGE), 'selection': selected}
    version,field = {'literature': ('literature_assignment_v1','source_refs'),
        'literature_strategy': ('strategy_assignment_v1','prior_search_refs'),
        'literature_search': ('search_assignment_v1','search_result_refs')}[role]
    return {'version': version, 'question_context_refs': [], field: []}


def service(db):
    workflow = SimpleNamespace(store=SimpleNamespace(db=db), run_id='source-fixture')
    return SimpleNamespace(workflow=workflow,
        reference_in_scope=lambda ref, scope, namespace: ref in RECORDS and (namespace is None or RECORDS[ref]['record_type']==namespace),
        read_record=lambda ref: deepcopy(RECORDS[ref]),
        tool_catalog=lambda scope: [], own_outcomes=lambda *a, **k: [],
        scientific_credit=lambda context, receiver_selection: {'credit': -0.5, 'qualified': True})


def context(role, value=None):
    return BindingContext('source-fixture', 'source-episode', role, ((role,'controlled'),),
        {'subject_refs': []}, assignment(role) if value is None else value, {}, tuple(RECORDS))


def test_own_original_schema_and_reader_parent_admission(binding_type):
    with sqlite3.connect(':memory:') as db:
        binding=binding_type(service(db)); role=binding.roles[0]
        baseline=next(row for row in ROWS if row['binding_path']==binding.binding_path)
        assert binding.assignment_schema(role)==baseline['assignment_schema']
        own=assignment(role); parent=context('literature_page',deepcopy(PAGE)) if role in {
            'literature_table','literature_ordered','literature_targeted'} else context('literature')
        assert binding.prepare_assignment(parent,role,own,{},'original-assignment')==own
        if role in {'literature_table','literature_ordered','literature_targeted'}:
            changed=deepcopy(own); changed['page']['source_ref']=OTHER
            if role=='literature_targeted': changed['selection']['spans'][0]['source_ref']=OTHER
            else: changed['selection']['source_ref']=OTHER
            with pytest.raises(ContractError,match='literature_reading_outside_assigned_source'):
                binding.prepare_assignment(parent,role,changed,{},'different-source')
        assert binding.credit_view(context(role),{})=={'credit':-0.5,'qualified':True}
        assert binding.yield_controller(context(role),0,'original-epoch') is None
        assert binding.continuation_task(context(role)) is None


def test_repaired_metadata_is_read_only_and_preserves_failed_attempt(binding_type):
    with sqlite3.connect(':memory:') as db:
        db.row_factory=sqlite3.Row; binding=binding_type(service(db)); ctx=context(binding.roles[0])
        before=db.total_changes
        assert binding._owned_population_task_sources(ctx)==()
        assert binding._population_task_context(ctx)=={'literature_owned_population_sources':()}
        assert db.total_changes==before
        db.execute('CREATE TABLE runtime_actions (run_id TEXT, episode_id TEXT, decision_index INTEGER, action TEXT, result TEXT)')
        action={'kind':'tool','tool':'literature.reaction.source.populate','arguments':{'version':'selected-source'}}
        db.execute('INSERT INTO runtime_actions VALUES (?,?,?,?,?)',(ctx.run_id,ctx.episode_id,0,json.dumps(action),json.dumps({'status':'invalid'})))
        result=binding._population_task_context(ctx)
        assert result['literature_selected_population_attempt']=={
            'tool':'literature.reaction.source.populate','arguments':{'version':'selected-source'},'status':'invalid'}
        db.execute('INSERT INTO runtime_actions VALUES (?,?,?,?,?)',(ctx.run_id,ctx.episode_id,1,json.dumps({'kind':'tool','tool':'source.read','arguments':{}}),json.dumps({'status':'completed'})))
        assert 'literature_selected_population_attempt' not in binding._population_task_context(ctx)


def test_invalid_tool_return_keeps_original_action_identity(binding_type):
    with sqlite3.connect(':memory:') as db:
        binding=binding_type(service(db));ctx=context(binding.roles[0])
        result=asyncio.run(binding.execute(ctx,'not_a_declared_source_tool',{},'selected-original'))
        assert result['status']=='invalid'
        assert result['operation_ref']==identity('operation',{'key':'selected-original','name':'not_a_declared_source_tool','arguments':{}})
        assert result['record_refs']==result['changed_record_refs']==[]
        assert result['feedback']['code']=='tool_not_available_to_literature_role'


def test_injected_instruction_service_precedes_default_composer(binding_type):
    task=binding_type.decision_source_type.__new__(binding_type.decision_source_type)
    calls=[]
    task.workflow=SimpleNamespace(services=SimpleNamespace(instructions=lambda source,ctx:calls.append((source,ctx)) or 'injected-original'))
    value={'original':'context'}
    assert task.instructions(value)=='injected-original'
    assert calls==[(task,value)]
    assert task.instruction_composer.__module__.startswith(binding_type.__module__.rsplit('.',1)[0]+'.')


@pytest.mark.parametrize('status',['invalid','failed','unavailable','partial','completed'])
def test_executed_outcome_journal_credit_and_saved_replay(binding_type,tmp_path,status):
    store=Store(tmp_path/'source-state');journal=Journal(store,'private-source-run')
    result={'status':status,'record_refs':[],'changed_record_refs':[],
        'feedback':{'category':'controlled-source-result'},'result':None}
    visits=[]
    async def automatic(source,index,outcome):
        visits.append(('scores',index,outcome['status']));return outcome
    workflow=SimpleNamespace(store=store,journal=journal,run_id='private-source-run',
        execution_binding=None,inprocess_replay=None,wait_inputs_version=None,completed_action_inputs_version=None,
        execute=lambda source,name,args,**kw:visits.append(('execute',name,kw['operation_key'])) or deepcopy(result),
        receive_native_outcome=lambda source,outcome,index:visits.append(('native',index,outcome['status'])),
        receive_outcome=lambda source,selection,outcome,index:visits.append(('receipt',index,outcome['status'])),
        automatic_score_updates=automatic,source_credit_view=lambda source:{'credit':-0.5},
        controller_value=lambda source,index,credit:{'original_action':index,'credit':credit})
    task=binding_type.decision_source_type.__new__(binding_type.decision_source_type)
    task.workflow=workflow;task.path=((binding_type.roles[0],'fixture'),);task.scope={'subject_refs':[]}
    task.episode_id='original-source-episode';task.feedback=None;task.last_outcome=None;task.last_outcome_index=None
    selection={'kind':'tool','tool':'source.read','arguments':{'source_ref':SOURCE}}
    first=asyncio.run(task.execute(selection,7))
    assert first=={'original_action':7,'credit':-0.5}
    saved=journal.row('runtime_actions',task.episode_id,7)
    assert json.loads(saved['action'])==selection and json.loads(saved['result'])==result and saved['credit']==-0.5
    assert task.last_outcome==result and task.last_outcome_index==7
    again=asyncio.run(task.execute(selection,7))
    assert again==first
    assert [v[0] for v in visits].count('execute')==1
    assert [v[0] for v in visits].count('receipt')==1
    assert [v[0] for v in visits].count('scores')==1
    # Actual private next consumes the saved call context without reconstructing
    # a different request. Provider/apply ports are controlled at this boundary.
    task.calls=0;task._execution_context=None;task._restored=True
    request={'context':{'retained':'original-input'},'schema':{'type':'object'}}
    journal.save('runtime_model_calls',{'episode_id':task.episode_id,'call_index':0,'purpose':'decision',
        'request':json.dumps(request),'response':json.dumps({'selected':'original'})})
    captured=[]
    async def call(ctx,schema): captured.append((ctx,schema));return {'selected':'original'},0,ctx,schema
    task.call=call;sentinel=object();task.apply_response=lambda *args:sentinel
    returned=asyncio.run(task.next(SimpleNamespace(units_consumed=0)))
    assert returned is sentinel and captured==[(request['context'],request['schema'])]
    store.close()


@pytest.mark.parametrize('reported_summary',[False,True])
def test_original_reaction_population_saved_sheet_exact_cells_and_replay(binding_type,tmp_path,reported_summary):
    """Actual A110 source parser/calculator/storage, with declared synthetic bytes."""
    from dataclasses import replace
    from gene_annotation_episode.episodic_workflow.root.a110.communication import form_with_facts
    from gene_annotation_episode.episodic_workflow.root.a110.domain import canonical, obj
    from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_inputs import LITERAL_FIELDS
    from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_report_contracts import reaction_cells_schema
    store=Store(tmp_path/'reaction-state')
    store.create_problem(raw_sequence='ATGGCT',molecule='dna')
    raw=(b'SyntheticProtein produces ProductA per ProductB in independent preparations. '
         b'Matched synthetic reaction and resource budget with declared usable supply.')
    def source(payload,parents=()):
        artifact=store.artifact(payload,'application/octet-stream')
        return store.put('source',{'provider':'controlled_private_source','accession':None,'uri':None,
            'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':None,'retrieved_at':None,
            'parent_source_refs':list(parents)},origin='caller')
    paper=source(raw)
    def witness(quote):
        token=quote.encode();start=raw.index(token)
        return {'source_ref':paper['id'],'representation':'original','start':start,'end':start+len(token),'quote':quote}
    literals=dict.fromkeys(LITERAL_FIELDS)
    literals.update(molecule=witness('SyntheticProtein'),numerator=witness('ProductA'),denominator=witness('ProductB'),
        experiment=witness('independent preparations'),endpoint=witness('synthetic reaction'),resource_context=witness('declared usable supply'))
    ratio={'mode':'source_summary' if reported_summary else 'independent_units','ratio_kind':'product_pair','unit':'mol_per_mol',
        'origin':'synthetic','observations':[] if reported_summary else [{'measurement_key':'prep1','value':.7},{'measurement_key':'prep2','value':.9}],
        'mean':1. if reported_summary else None,'sample_sd':None,'independent_n':None,'claim':1.,
        'alternatives':[] if reported_summary else [{'key':'half_product_ratio','prediction':.5}]}
    data={'version':'a110_source_reaction_measurements_v1','ratio':ratio,'budget':None}
    dataset=source(canonical(data),[paper['id']])
    args={'source_ref':paper['id'],'data_source_ref':dataset['id'],'source_kind':'synthetic_fixture',
        'literals':literals,'interpretation_witnesses':[witness(raw.decode())]}
    workflow=SimpleNamespace(store=store,run_id='reaction-private-fixture')
    from gene_annotation_episode.episodic_workflow.root.a110.episode_services import WorkflowServices
    from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import EpisodeBindingRegistry
    services=WorkflowServices(workflow)
    services.tool_catalog=lambda scope:[{'name':'source.read','input_schema':{'type':'object'}}]
    services.own_outcomes=lambda *a,**kw:[]
    binding=binding_type(services);role=binding.roles[0];selected=assignment(role)
    workflow.episode_bindings=EpisodeBindingRegistry((binding,))
    page={'version':'page_assignment_v1','source_ref':paper['id'],'representation':'original','artifact_ref':paper['artifact_ref'],
        'question_context_refs':[],'prior_delivery_refs':[]}
    if role=='literature_page':selected=page
    elif role in {'literature_table','literature_ordered','literature_targeted'}:
        selected['page']=page
        window={'source_ref':paper['id'],'representation':'original','offset':0,'limit':len(raw)}
        selected['selection']={'spans':[window]} if role=='literature_targeted' else window
    components=['ratio_mean','claim_mean_squared_error','reaction_comparison']
    selected['requested_reaction_components']=components
    ctx=BindingContext(workflow.run_id,'reaction-private-child',role,((role,'fixture'),),store.validate_scope(),selected,{},(paper['id'],dataset['id']))
    outcome=asyncio.run(binding.execute(ctx,'literature.reaction.populate',args,'original-population'))
    assert outcome['status']=='completed',outcome
    sheet_ref=outcome['result']['sheet_ref']
    current=replace(ctx,received_record_refs=tuple(dict.fromkeys([*ctx.received_record_refs,*outcome['record_refs']])))
    facts=binding.facts(current,{'committed_record_refs':[sheet_ref]})
    form_schema=obj({'measurements':reaction_cells_schema()})
    form=form_with_facts({},form_schema,facts)
    binding.validate_report(current,form,form_schema)
    rows=form['measurements'];assert [row['component'] for row in rows]==components
    assert rows[0]['value']==pytest.approx(1. if reported_summary else .8)
    if reported_summary:
        assert rows[1]['value'] is rows[2]['value'] is None
        assert rows[0]['independent_n'] is rows[0]['reported_sample_sd'] is None
        assert rows[0]['ratio_uncertainty']=='unreported'
    else:
        assert rows[1]['value']==pytest.approx(.05) and rows[2]['value']==pytest.approx(1/3)
        assert rows[0]['independent_n']==2
    assert all(row['measurement_corrections']=='not_applied' for row in rows)
    assert binding._owned_population_task_sources(current)==('literature_reaction_cells',)
    publication=store.db.execute('SELECT adapter,method,receipt FROM literature_sheet_dependencies WHERE sheet_ref=?',(sheet_ref,)).fetchone()
    assert publication['adapter']=='gene_annotation_episode.episodic_workflow.root.a110.literature_reaction_storage:LiteratureReactionRepository'
    assert publication['method']=='populate'
    from gene_annotation_episode.episodic_workflow.root.a110.literature_sheet_updates import current_sheet_refs
    assert current_sheet_refs(store,current)==[sheet_ref]
    before_replay=store.db.total_changes
    replay=asyncio.run(binding.execute(ctx,'literature.reaction.populate',args,'original-population'))
    assert store.db.total_changes==before_replay
    assert replay==outcome
    assert store.db.execute('SELECT count(*) FROM literature_reaction_operations').fetchone()[0]==1
    tampered=deepcopy(form);tampered['measurements'][0]['value']=7.
    with pytest.raises(Exception) as caught:binding.validate_report(current,tampered,form_schema)
    assert 'differs' in str(caught.value)
    store.close()


def test_source_selected_recipe_retains_technical_count_and_publication_identity(binding_type,tmp_path):
    from dataclasses import replace
    from gene_annotation_episode.episodic_workflow.root.a110.communication import form_with_facts
    from gene_annotation_episode.episodic_workflow.root.a110.domain import obj
    from gene_annotation_episode.episodic_workflow.root.a110.episode_services import WorkflowServices
    from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import EpisodeBindingRegistry
    from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_inputs import LITERAL_FIELDS
    from gene_annotation_episode.episodic_workflow.root.a110.library.literature_reaction_native_inputs import VERSION
    from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_report_contracts import reaction_semantic_cells_schema
    store=Store(tmp_path/'native-source-state');store.create_problem(raw_sequence='ATGGCT',molecule='dna')
    raw=b'SyntheticProtein; ProductA; ProductB; synthetic reaction; ratio = 0.8; SD = 0.2; n = 4 technical injections.'
    artifact=store.artifact(raw,'application/octet-stream')
    paper=store.put('source',{'provider':'controlled_source_selection','accession':None,'uri':None,
        'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':None,'retrieved_at':None,'parent_source_refs':[]},origin='caller')
    def witness(quote):
        token=quote.encode();start=raw.index(token)
        return {'source_ref':paper['id'],'representation':'original','start':start,'end':start+len(token),'quote':quote}
    def number(token):
        quote=raw.decode();start=quote.index(token)
        return {'witness':witness(quote),'number_start':start,'number_end':start+len(token)}
    literals=dict.fromkeys(LITERAL_FIELDS)
    for field,text in [('molecule','SyntheticProtein'),('numerator','ProductA'),('denominator','ProductB'),('experiment','synthetic reaction')]:literals[field]=witness(text)
    model={'definition':None,'reaction':None,'function_relation':None,'prediction_evidence':None,'prediction_basis':'conditional_assumption'}
    recipe={'version':VERSION,'ratio':{'mode':'source_summary','ratio_kind':'product_pair','unit':'mol_per_mol',
        'measurement_basis':'reported_molar_ratio','basis_witnesses':[],'observations':[],
        'summary':{'value':{'kind':'point','number':number('0.8')},
            'uncertainty':{'kind':'sample_sd','number':number('0.2'),'basis_witnesses':[]},
            'count':{'number':number('4'),'basis':'technical_repeat','basis_witnesses':[witness('technical injections')]}},
        'claim':{'kind':'declared','value':1,'basis':'conditional_assumption','evidence':[]},'alternatives':[]},
        'budget':None,'meanings':{'ratio':{'claim':model,'alternatives':[]},'budget':None}}
    args={'source_ref':paper['id'],'source_kind':'synthetic_fixture','literals':literals,
        'interpretation_witnesses':[],'native_selection':recipe}
    workflow=SimpleNamespace(store=store,run_id='native-source-owner')
    services=WorkflowServices(workflow);services.tool_catalog=lambda scope:[{'name':'source.read','input_schema':{'type':'object'}}]
    services.own_outcomes=lambda *a,**kw:[]
    binding=binding_type(services);workflow.episode_bindings=EpisodeBindingRegistry((binding,));role=binding.roles[0]
    selected=assignment(role);page={'version':'page_assignment_v1','source_ref':paper['id'],'representation':'original',
        'artifact_ref':artifact,'question_context_refs':[],'prior_delivery_refs':[]}
    if role=='literature_page':selected=page
    elif role in {'literature_table','literature_ordered','literature_targeted'}:
        selected['page']=page;window={'source_ref':paper['id'],'representation':'original','offset':0,'limit':len(raw)}
        selected['selection']={'spans':[window]} if role=='literature_targeted' else window
    selected['requested_reaction_components']=['ratio_mean','claim_mean_squared_error']
    selected['requested_reaction_native_positions']=[0]
    ctx=BindingContext(workflow.run_id,'selected-reaction-child',role,((role,'fixture'),),store.validate_scope(),selected,{},(paper['id'],))
    result=asyncio.run(binding.execute(ctx,'literature.reaction.source.populate',args,'source-choice'))
    assert result['status']=='completed',result
    repo=binding.literature_reaction_repository();sheet=repo.read(result['result']['sheet_ref'])
    assert sheet['sheet']['cells']['ratio_mean']['value']==pytest.approx(.8)
    assert sheet['sheet']['inputs']['ratio']['independent_n'] is None
    assert sheet['sheet']['cells']['claim_mean_squared_error']['value'] is None
    assert result['result']['selection_source_ref'] in result['record_refs']
    current=replace(ctx,received_record_refs=tuple(dict.fromkeys([*ctx.received_record_refs,*result['record_refs']])))
    facts=binding.facts(current,{'committed_record_refs':[result['result']['sheet_ref']]})
    schema=obj({'source_cells':reaction_semantic_cells_schema()})
    form=form_with_facts({},schema,facts);binding.validate_report(current,form,schema)
    assert [row['component'] for row in form['source_cells']]==['ratio_mean','claim_mean_squared_error']
    saved=store.db.execute('SELECT adapter,method FROM literature_sheet_dependencies WHERE sheet_ref=?',(result['result']['sheet_ref'],)).fetchone()
    assert saved['adapter']=='gene_annotation_episode.episodic_workflow.root.a110.literature_reaction_storage:LiteratureReactionRepository'
    assert saved['method']=='populate'
    replay=asyncio.run(binding.execute(ctx,'literature.reaction.source.populate',args,'source-choice'))
    assert replay==result
    assert store.db.execute('SELECT count(*) FROM literature_reaction_operations').fetchone()[0]==1
    store.close()


from types import MethodType
import traceback
PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a110'



def observed(callback):
    try:
        value = callback()
        return {'status': 'returned', 'is_none': value is None, 'type': type(value).__module__ + '.' + type(value).__qualname__}
    except Exception as error:
        return {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
                'message': str(error), 'traceback': traceback.format_exc()}


def original_admission_observation(output, binding_type):
    output = Path(output)
    output.mkdir()
    runtime = importlib.import_module(PACKAGE + '.runtime')
    state = importlib.import_module(PACKAGE + '.state')
    bindings_module = importlib.import_module(PACKAGE + '.episode_bindings')
    services_type = importlib.import_module(PACKAGE + '.episode_services').WorkflowServices
    journal_type = importlib.import_module(PACKAGE + '.episode_journal').Journal
    store = state.Store(output / 'state')
    run_id = 'a110-original-action-admission'
    journal = journal_type(store, run_id)
    result = {'version': 'a110_original_source_action_admission_v1', 'source_only_fixture': True,
              'scope': 'Controlled fresh/recorded wire admission, actual original permission and child-role checks, completed tool replay; no historical unsupported-action claim.',
              'rows': [], 'application_modified': False}
    try:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        host = SimpleNamespace(store=store, run_id=run_id)
        services = services_type(host)
        services.tool_catalog = lambda scope: [{'name': 'source.read', 'input_schema': runtime._object({})}]
        services.capabilities = lambda: {}
        services.own_outcomes = lambda *args, **kwargs: []
        for family in (binding_type.__module__.removeprefix(PACKAGE + '.').split('.published_evidence_assessment')[0] + '.published_evidence_assessment' if '.published_evidence_assessment' in binding_type.__module__.removeprefix(PACKAGE + '.') else 'published_evidence_assessment',):
            bindings = importlib.import_module(PACKAGE + '.' + family + '.episode').create_binding_tree(services)
            by_role = {binding.roles[0]: binding for binding in bindings}
            for binding in (next(item for item in bindings if type(item) is binding_type),):
                role, = binding.roles
                source = object.__new__(binding.decision_source_type)
                source.episode_id, source.path = binding.binding_path, ((role, 'controlled'),)
                source.scope = store.validate_scope()
                source._delivery_resolution_ref = None
                source.interpret_schema = runtime._object({})
                source.report_values, source.report_basis = {}, []
                source.request = SimpleNamespace(message=SimpleNamespace(as_record=lambda: {}))
                source.last_outcome = source.last_outcome_index = source.feedback = None
                context = bindings_module.BindingContext(run_id, source.episode_id, role, source.path, source.scope, {}, {}, ())
                effects, acquired = [], []
                workflow = SimpleNamespace(store=store, journal=journal, run_id=run_id,
                    specialist=lambda source, binding=binding: binding, binding_context=lambda source, context=context: context,
                    services=services, job_episodes=None, project_credit=lambda **kwargs: {}, annotation_child_roles=('literature',),
                    scientific_process_binding=None, execution_binding=None, inprocess_replay=None, decision_exchanges=None,
                    receipts=None, root_action_boundary=None,
                    catalog=lambda scope, source, binding=binding, context=context: binding.catalog(context),
                    available_child_roles=lambda source, binding=binding, role=role: binding.child_roles(role),
                    declared_child_roles=lambda selected, path, binding=binding: binding.child_roles(selected),
                    episode_bindings=SimpleNamespace(roles=tuple(by_role), for_child=lambda path, role: by_role[role]),
                    root_child_return_sources=lambda source, role: (),
                    _closed_child_commission=lambda *args: None, resolver=lambda *args, **kwargs: (lambda ref: None),
                    validate_report=lambda *args, **kwargs: None,
                    receive_native_outcome=lambda *args: None, controller_value=lambda source, index, credit: credit)
                for method in ('permits_common_action', 'is_job_source', 'validate_child_choice', 'selected', 'action_schema'):
                    setattr(workflow, method, MethodType(getattr(runtime.Workflow, method), workflow))
                source.workflow = workflow
                source.record_effect = lambda index, effect: effects.append((index, effect))
                source.checkpoint = lambda: None
                schema = workflow.action_schema(source)
                kinds = sorted({branch['properties']['kind']['const'] for branch in schema['properties']['selection']['anyOf']})
                row = {'binding_path': binding.binding_path, 'role': role, 'fresh_schema_kinds': kinds,
                       'reason_permitted': workflow.permits_common_action(source, 'reason'),
                       'wait_permitted': workflow.permits_common_action(source, 'wait'), 'cases': []}
                selections = [
                    ('reason', {'kind': 'reason', 'commit': {}}),
                    ('wait', {'kind': 'wait', 'condition': {}}),
                    ('job_child', {'kind': 'job_child', 'role': 'job_launch'}),
                    ('reads_map', {'kind': 'tool', 'tool': 'reads.map', 'arguments': {}}),
                    ('results', {'kind': 'episode_child', 'role': 'results', 'assignment': {'version': 'execution_results_assignment_v1',
                        'selector': {'version': 'bvbrc_minhash_result_selector_v2'}}}),
                    ('source_tool', {'kind': 'tool', 'tool': 'source.read', 'arguments': {}})]
                for index, (name, selection) in enumerate(selections):
                    source.feedback = None
                    observation = observed(lambda selection=selection, index=index: source.apply_response(
                        {'selection': deepcopy(selection), 'report_update': {}}, index, {'visible_record_refs': []}, schema))
                    selected_row = journal.row('runtime_actions', source.episode_id, index)
                    row['cases'].append({'case': name, 'admission': observation, 'feedback': deepcopy(source.feedback),
                        'effects': deepcopy(effects), 'selected_action_created': selected_row is not None})
                    effects.clear()
                selection = {'kind': 'tool', 'tool': 'source.read', 'arguments': {}}
                saved_outcome = {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                                 'feedback': {'category': 'controlled_original_invalid_return'}}
                journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': 50,
                    'action': json.dumps(selection), 'result': json.dumps(saved_outcome), 'credit': -0.5})
                workflow.execute = lambda *args, **kwargs: acquired.append('unexpected_reexecution')
                row['completed_invalid_tool_replay'] = observed(lambda: asyncio.run(source.execute(selection, 50)))
                row['replay_outcome'] = deepcopy(source.last_outcome)
                row['replay_action_unchanged'] = json.loads(journal.row('runtime_actions', source.episode_id, 50)['action']) == selection
                row['replay_acquisitions'] = acquired
                source.feedback = None
                row['saved_selection_mismatch'] = observed(lambda: source.apply_response(
                    {'selection': {'kind': 'reason', 'commit': {}}, 'report_update': {}}, 50, {'visible_record_refs': []}, schema))
                row['saved_selection_mismatch_feedback'] = deepcopy(source.feedback)
                result['rows'].append(row)
    finally:
        store.close()
    return result


def test_original_action_admission_and_completed_replay(binding_type, tmp_path):
    expected_rows = json.loads((Path(__file__).parent /
        'fixtures/private_literature/original_action_admission.json').read_text())['rows']
    result = original_admission_observation(tmp_path / 'admission', binding_type)
    assert len(result['rows']) == 1
    # The original probe serialized effects as JSON; compare the same wire value.
    row = json.loads(json.dumps(result['rows'][0]))
    expected = next(item for item in expected_rows if item['binding_path'] == row['binding_path'])
    # Retain every original observed boundary: fresh unsupported choices,
    # allowed source acquisition, completed invalid replay, and mismatched replay.
    assert row == expected
