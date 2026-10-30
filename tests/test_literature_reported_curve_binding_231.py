"""Selected reported-curve integration: controlled source fixtures, not model science."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain, validate_closed_schema, ReportBoundaryError
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_rate_observation_storage import (
    LiteratureRateObservationRepository, LiteratureReportedCurveRepository, GRID_NAMESPACE,
    GRID_REQUESTED, GRID_RECORD, GRID_POPULATION, GRID_VIEW, rate_grid_cells_schema, rate_observation_operation_schema,
    _grid_scoped_label)
from gene_annotation_episode.literature_rate_observation_prompt import (
    REPORTED_CURVE_TASK, REPORTED_CURVE_SCOPE_TASK, RATE_OBSERVATION_TASK, render_received)
from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK, render_literature_experimental_prompt
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_reported_curve_precision_228 import source_setup, edit_workbook, select

BASE=Path(__file__).resolve().parents[1]/'verification/literature_reference_evidence_2026-10-25_001/a105_reported_curve_binding_231'
SELECTORS=[select('point','cv',concentration_cell='Q196'),
    select('estimator','Km',estimator='fit_of_point_means'),
    select('estimator','log_efficiency_variance',estimator='fit_of_point_means')]


def setup(path,*,selectors=SELECTORS,nondetection=False):
    raw,grid,docs,_=source_setup()
    if nondetection:
        from xml.etree import ElementTree as ET
        def mutate(_,cells):
            c=cells['R196'];c.set('t','inlineStr')
            for child in list(c):c.remove(child)
            ET.SubElement(ET.SubElement(c,'{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is'),
                '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t').text='ND'
        raw=edit_workbook(mutate);grid['source_kind']='synthetic_fixture'
    store=Store(path);manifest=path/'empty-manifest.json';manifest.write_text(json.dumps({'schema_version':1,'entries':[]}));store.create_problem(manifest_path=manifest)
    def put(content,provider,parents=None):
        artifact=store.artifact(content)
        return store.put('source',{'provider':provider,'accession':None,'uri':None,'artifact_ref':artifact,
            'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None,
            **({'parent_source_refs':parents} if parents else {})},origin='caller')['id']
    article=put(docs[0]['content'],'retained_original_225_article')
    source=put(raw,'synthetic_grid231' if nondetection else 'retained_original_225_xlsx',[article])
    original_source=grid['source_ref'];original_context=docs[0]['source_ref']
    def replace_refs(v):
        if isinstance(v,dict):return {k:replace_refs(c) for k,c in v.items()}
        if isinstance(v,list):return [replace_refs(c) for c in v]
        return source if v==original_source else article if v==original_context else v
    grid=replace_refs(grid)
    assignment={'version':'literature_assignment_v1','question_context_refs':[],'source_refs':[source,article],GRID_REQUESTED:deepcopy(selectors)}
    ctx=BindingContext('curve231','child231','literature',(('literature','child231'),),store.validate_scope(),assignment,{},(source,article))
    args={'version':GRID_POPULATION,'grid':grid,'calculation':{'version':'a105_reported_curve_precision_request_v1',
        'fit_model':'unweighted_positive_km_mm','requested_components':deepcopy(selectors)}}
    return store,ctx,args,source,article


def binding_for(store,ctx,profile=None):
    host=SimpleNamespace(store=store,run_id=ctx.run_id,tools=ToolRegistry(store))
    services=WorkflowServices(host)
    binding=LiteratureEpisodes(services,rate_population=True,reference_parent_sources=list(ctx.received_record_refs[:2]),contract_information_profile=profile)
    host.episode_bindings=EpisodeBindingRegistry((binding,));return binding


def selected(store,ctx,args,key='selected231'):
    binding=binding_for(store,ctx)
    outcome=asyncio.run(binding.execute(ctx,'literature.rate.observations.populate',args,key))
    assert outcome['status']=='completed',outcome
    current=replace(ctx,received_record_refs=(*ctx.received_record_refs,*outcome['record_refs']))
    form=obj({'numbers':rate_grid_cells_schema()})
    rows=form_with_facts({},form,binding.facts(current,{'committed_record_refs':outcome['record_refs']}))['numbers']
    binding.validate_report(current,{'numbers':rows},form)
    return binding,current,outcome,rows


def state_hashes(path):
    return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file()}


def forbid(*args,**kw):raise AssertionError('Scientific source/parse/fit/model/receive/current attestation forbidden')


def block_science(monkeypatch):
    from gene_annotation_episode import literature_rate_observation_inputs as inputs
    from gene_annotation_episode import literature_rate_observation_calculations as calculations
    from gene_annotation_episode import spreadsheet_tools
    for module,names in [(inputs,['read_reported_rate_grid','validate_reported_rate_grid_extraction','_grid_validate_unit_mapping','_grid_quantity','Workbook']),
        (calculations,['populate_reported_curve_precision','_grid_fit','_grid_covariance']),
        (spreadsheet_tools,['Workbook']),
        (LiteratureReportedCurveRepository,['_original_implementation','populate','receive_cells'])]:
        for name in names:monkeypatch.setattr(module,name,forbid)


def test_source_selected_scalars_exact_contract_and_saved_scope(tmp_path):
    store,ctx,args,source,article=setup(tmp_path/'state')
    try:
        binding=binding_for(store,ctx);before=store.db.total_changes
        assert 'literature.rate.observations.populate' in {r['name'] for r in binding.catalog(ctx)}
        assert len(rate_observation_operation_schema()['anyOf'])==2
        assert GRID_REQUESTED in binding.assignment_schema('literature')['properties']
        assert GRID_NAMESPACE in binding.fact_sources('literature')
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_rate_observation_operations'").fetchone()
        assert store.db.total_changes==before
        proposal=json.loads((BASE/'EXACT_SCHEMA_PROPOSAL_002.json').read_text())
        assert rate_observation_operation_schema()==proposal['operation_schema']
        assert rate_grid_cells_schema()==proposal['return_schema']
        binding,current,out,rows=selected(store,ctx,args)
        assert [r['selector'] for r in rows]==SELECTORS
        assert rows[0]['value']==pytest.approx(.03488479236954927)
        assert rows[0]['coordinate_context'][0]['exact_value']=={'numerator':'10','denominator':'1'}
        assert not rows[1]['coordinate_context'] and not rows[2]['coordinate_context']
        assert rows[2]['value'] is None and rows[2]['conditional_value']==pytest.approx(.0033927323393825364)
        assert rows[2]['scientific_scope']['physical_preparation_count'] is None
        assert rows[2]['scientific_scope']['endpoint_relationship']=='conflicting'
        repo=LiteratureRateObservationRepository(store,ctx.run_id).grid_projection();saved=repo.read(out['result']['sheet_ref'])
        assert saved['sheet']['extraction']==saved['extraction']
        assert saved['selection']==args and saved['original_implementation']['files']
        assert repo.populate(ctx,args,'selected231')==out
        assert not any(k in json.dumps(rows) for k in ['rate_cells','raw_value','matrix_exact','context_witnesses'])
        assert not store.list('assessment') and not store.list('observation')
        with pytest.raises(ContractError,match='sheet_required'):LiteratureRateObservationRepository(store,ctx.run_id).read(out['result']['sheet_ref'])
    finally:store.close()


def test_empty_order_possession_page_and_exact_admitted_subset(tmp_path):
    store,ctx,args,source,article=setup(tmp_path/'state')
    try:
        binding=binding_for(store,ctx)
        bad=deepcopy(args);bad['calculation']['requested_components'].reverse()
        assert asyncio.run(binding.execute(ctx,'literature.rate.observations.populate',bad,'order'))['feedback']['code']=='literature_rate_grid_requested_subset_mismatch'
        denied=replace(ctx,received_record_refs=(source,))
        assert asyncio.run(binding.execute(denied,'literature.rate.observations.populate',args,'missing'))['feedback']['code']=='literature_source_not_received'
        page=replace(ctx,role='literature_page',path=(('literature_page',ctx.episode_id),),assignment={
            'version':'page_assignment_v1','source_ref':source,'representation':'original','artifact_ref':store.get(source)['artifact_ref'],
            'question_context_refs':[],'prior_delivery_refs':[],GRID_REQUESTED:SELECTORS})
        assert asyncio.run(binding.execute(page,'literature.rate.observations.populate',args,'page'))['feedback']['code']=='literature_reading_outside_assigned_source'
        binding,current,out,rows=selected(store,ctx,args)
        repo=LiteratureRateObservationRepository(store,ctx.run_id).grid_projection()
        parent=replace(current,episode_id='parent231',role='annotation',path=(('annotation','parent231'),),assignment={})
        repo.receive_cells(parent,rows[:1],'trusted231')
        assert repo.fact_cells(parent,[out['result']['sheet_ref']],components=SELECTORS)==rows[:1]
        with pytest.raises(ContractError,match='not_received'):repo.validate_fact_values(parent,rows[1:])
        changed=deepcopy(rows[:1]);changed[0]['value']=999
        with pytest.raises(ContractError,match='differs_from_saved'):repo.validate_fact_values(parent,changed)
        empty=deepcopy(args);empty['calculation']['requested_components']=[]
        _,_,emptyout,emptyrows=selected(store,replace(ctx,assignment={**plain(ctx.assignment),GRID_REQUESTED:[]}),empty,'empty')
        assert emptyrows==[] and emptyout['result']['cells']==[]
        validate_closed_schema(obj({'numbers':rate_grid_cells_schema()}))
    finally:store.close()


@pytest.mark.parametrize('status',['supported','unknown','conflicting'])
def test_selected_sampling_qualification_never_becomes_physical_total_uncertainty(tmp_path,status):
    store,ctx,args,_,_=setup(tmp_path/'state')
    try:
        sampling=args['grid']['curve_sampling'];sampling['status']=status
        sampling['source_claim']={'supported':'iid_reporting_vectors_supported','unknown':'unknown','conflicting':'conflicting'}[status]
        if status=='unknown':sampling.update(assumption='none',witnesses=[])
        # A supported branch is an explicitly controlled claim scenario. The
        # original paper's actual grouping remains the stipulated fixture above.
        if status=='supported':args['grid']['source_kind']='synthetic_fixture'
        _,_,_,rows=selected(store,ctx,args)
        assert rows[0]['status']=='populated' and rows[0]['value'] is not None
        assert rows[2]['status']==('conditional_scenario' if status=='supported' else 'unavailable')
        assert rows[2]['sampling']['status']==status and rows[2]['value'] is None
        assert rows[2]['scientific_scope']['physical_preparation_count'] is None
        assert rows[2]['scientific_scope']['published_estimate_covariance'] is None
        if status!='supported':assert 'sampling_model_'+status in rows[2]['relationship_reasons']
    finally:store.close()


def test_each_public_selector_scope_keeps_order_and_only_named_coordinate_context(tmp_path):
    selectors=[*deepcopy(SELECTORS[:2]),select('curve','Vmax',curve_header_cell='R192'),
        select('reported_curve_covariance','sample_covariance',left_concentration_cell='Q196',right_concentration_cell='Q197'),
        select('parameter_covariance','covariance',estimator='mean_of_reported_curve_fits',left_parameter='Vmax',right_parameter='Km'),
        select('sensitivity','d_parameter_d_point_mean',estimator='fit_of_point_means',parameter='Vmax',concentration_cell='Q196'),
        select('variance_term','signed_log_efficiency_variance_term',estimator='fit_of_point_means',left_parameter='Vmax',right_parameter='Km'),
        select('grid','complete_curve_count')]
    store,ctx,args,_,_=setup(tmp_path/'state',selectors=selectors)
    try:
        _,_,out,rows=selected(store,ctx,args)
        assert [r['selector'] for r in rows]==selectors
        assert [len(r['coordinate_context']) for r in rows]==[1,0,0,2,0,1,0,0]
        assert rows[3]['value'] is not None and rows[4]['conditional_value'] is not None
        assert rows[6]['conditional_value']<0 and rows[7]['value']==3
        saved=LiteratureReportedCurveRepository(store,ctx.run_id).read(out['result']['sheet_ref'])
        assert len(saved['projected_cells'])==8
        assert [c['location']['cell'] for c in rows[3]['coordinate_context']]==['Q196','Q197']
    finally:store.close()


@pytest.mark.parametrize('label,withheld', [('dose5mM',True),('pH8.0',True),('Kd34uM',True),('CV=0.5',True),
    ('P450cam',False),('K116A',False),('5-methyluridine',False),('NADH consumption rate µmol min-1',False)])
def test_bounded_label_scope_preserves_names_and_hides_values(label,withheld):
    w={'value':label,'source_ref':'source_'+'1'*24,'artifact_ref':'artifact_'+'2'*64,'member':'sheet.xml','cell':'A1'}
    projected=_grid_scoped_label(w)
    assert (projected['implementation_reason'] is not None)==withheld
    assert projected['display_text']!=label if withheld else projected['display_text']==label


def test_broad_alias_history_current_own_and_direct_parent_do_not_expand_private_cells(tmp_path):
    store,ctx,args,source,article=setup(tmp_path/'state')
    try:
        _,current,out,rows=selected(store,ctx,args)
        w=args['grid']['endpoint_relationship']['witnesses'][-1]
        secret='reference_'+'a'*24
        record={'id':secret,'record_type':'reference','origin':'tool','reference_type':'assay','label':'broad numerical context',
            'source_ref':article,'anchor':{**{k:w[k] for k in ('source_ref','artifact_ref','start','end','quote')}}}
        base={'literature_experimental_work':{'version':'literature_experimental_task_v1','aspect':'source_experimental_evidence'},
            'literature_assignment':{GRID_REQUESTED:SELECTORS[:1]},'working_state':{},
            'literature_received_fact_display':{'records':{secret:record},'received_refs':[secret]},'goal':{'objective':'Evaluate reported precision.'}}
        narrow={'numbers':rows[:1],'alias':secret}
        surfaces=[({**base,'child_reports':[narrow]},()),({**base,'current_report_update':narrow},()),
            ({**base,'last_local_outcome':{'status':'completed','result':{**out['result'],'cells':rows[:1]}}},()),
            ({**base,'child_reports':[narrow]},({'status':'completed','result':{'view':'records','records':[{'outcome':out,'admitted_report':narrow}]}},))]
        private=str(rows[1]['value'])
        for state,lookups in surfaces:
            text=render_literature_experimental_prompt(state,'Evaluate the requested source evidence.',lookup_results=lookups)
            assert REPORTED_CURVE_TASK in text.split('\n\nSTEERING\n')[0]
            assert private not in text and w['quote'] not in text and secret not in text
        parent={**base,'child_reports':[narrow],'literature_experimental_work':{'version':'literature_experimental_task_v1','aspect':'reference_evidence_parent'},
            'reference_evidence_parent':{'version':'reference_evidence_parent_v1','source_refs':[source,article]}}
        text=render_reference_evidence_parent_prompt(parent,'Evaluate source precision.')
        assert REPORTED_CURVE_TASK in text and REPORTED_CURVE_SCOPE_TASK in text and private not in text and secret not in text
        def rendered(values):
            p=[];render_received(p,values,section=lambda p,t,c:p.append(t+'\n'+c),table=lambda h,r:'\n'.join('|'.join(map(str,x)) for x in r));return '\n'.join(p)
        assert rendered(rows[:1])==rendered(iter(rows[:1]))
    finally:store.close()


@pytest.mark.parametrize('alter',['request','owner','context','coordinate','source_metadata'])
def test_decoded_saved_tampering_rejects_without_scientific_repair(tmp_path,monkeypatch,alter):
    store,ctx,args,source,article=setup(tmp_path/'state')
    try:
        _,_,out,_=selected(store,ctx,args)
        repo=LiteratureRateObservationRepository(store,ctx.run_id).grid_projection();ref=out['result']['sheet_ref'];meta=store.get(ref);original=repo._json_artifact
        def changed(reference):
            value=deepcopy(original(reference))
            if reference==meta['request_ref'] and alter=='request':value['components']=[]
            if reference==meta['artifact_ref']:
                if alter=='owner':value['extraction']['points'][0]['concentration']['measurement_key']='changed'
                elif alter=='context':value['projected_cells'][0]['source_context']['subject']['display_text']='changed'
                elif alter=='coordinate':value['projected_cells'][0]['coordinate_context'][0]['exact_value']['numerator']='1'
                elif alter=='source_metadata':value['source_metadata'][source]['version']='changed'
            return value
        monkeypatch.setattr(repo,'_json_artifact',changed);block_science(monkeypatch)
        with pytest.raises(ContractError,match='saved_'):repo.read(ref)
    finally:store.close()


@pytest.mark.parametrize('profile',[None,'operation_contract_information_v1'],ids=['legacy','explicit'])
@pytest.mark.parametrize('alias',[False,True],ids=['literal','alias'])
@pytest.mark.parametrize('nondetection',[False,True],ids=['point','nondetection'])
def test_selected_shared_loop_original_return_and_first_readonly_composer(tmp_path,monkeypatch,profile,alias,nondetection):
    shared_case(tmp_path,monkeypatch,profile,alias,nondetection)


def shared_case(tmp_path,monkeypatch,profile,alias,nondetection,*,nested=False):
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy,ScientificFindingProgress
    from gene_annotation_episode.runtime import run_workflow
    from test_runtime import FixtureController,ScriptedProvider
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime_decision_exchanges import select as action
    from test_literature_compiled_assay_185 import readonly
    store,ctx,args,source,article=setup(tmp_path/'state',nondetection=nondetection)
    limit={'type':'string','enum':['attribution_unknown']}
    literal=obj({'numbers':rate_grid_cells_schema(),'limitation':limit})
    submitted=obj({'numbers':{'$ref':'episode-fact:'+GRID_NAMESPACE},'limitation':limit}) if alias else literal
    assignment=plain(ctx.assignment);captured=[]
    def response(value):
        if not profile:return value
        value=deepcopy(value)
        if value['selection']['kind']=='tool':value['selection']['arguments']=json.dumps(value['selection']['arguments'])
        return action(value)
    def commission(role,assignment):return {'selection':{'kind':'episode_child','role':role,'assignment':assignment,
        'goal':'Evaluate what the reported curves establish about source activity and precision.','scope':plain(ctx.scope),
        'purpose':'Return exactly requested source scalars and their scientific limits.','schema_json':json.dumps(submitted),
        'initial_report_json':json.dumps({'limitation':'attribution_unknown'})},'report_update':{}}
    outer=deepcopy(assignment)
    if nested:outer[GRID_REQUESTED]=SELECTORS[:1]
    def received_state(inputs):return provider.views[provider.active_episode] if profile else inputs
    def work(inputs):
        inputs=received_state(inputs)
        task=render_literature_experimental_prompt(inputs,'Evaluate the requested reported curves.').split('\n\nSTEERING\n')[0]
        assert REPORTED_CURVE_TASK in task and REPORTED_CURVE_SCOPE_TASK in task and RATE_OBSERVATION_TASK not in task
        return response({'selection':{'kind':'tool','tool':'literature.rate.observations.populate','arguments':args},'report_update':{'limitation':'attribution_unknown'}})
    def integrate(inputs):
        inputs=received_state(inputs);form,=inputs['child_reports'];captured.append(deepcopy(form))
        wanted=SELECTORS[:1] if nested and len(captured)==2 else SELECTORS
        assert [r['selector'] for r in form['numbers']]==wanted
        assert form['numbers'][0]['status']==('unavailable' if nondetection else 'populated')
        prompt=render_literature_experimental_prompt(inputs,'Evaluate returned source precision.')
        task,steering=prompt.split('\n\nSTEERING\n')
        own_parent=inputs['literature_experimental_work']['aspect']=='reference_evidence_parent'
        assert (REFERENCE_PARENT_TASK if own_parent else EXPERIMENTAL_TASK) in task
        assert 'Evaluate returned source precision.' in task
        own_curve_request=GRID_REQUESTED in inputs.get('literature_assignment',{})
        assert (REPORTED_CURVE_TASK in task)==own_curve_request
        assert (REPORTED_CURVE_SCOPE_TASK in task)==own_curve_request
        assert 'Requested curve precision results' in steering
        assert 'Reporter precision does not establish product identity' in steering
        assert all(row['selector']['component'] in steering for row in form['numbers'])
        commit={k:[] for k in store.reasoning_schema()['required']};raw=store.get_artifact(store.get(article)['artifact_ref']);token=b'BbPK';start=raw.index(token)
        commit['source_subjects']=[{'alias':'studied_molecule231','reference_type':'assay','source_ref':article,'label':token.decode(),
            'anchor':{'source_ref':article,'artifact_ref':store.get(article)['artifact_ref'],'start':start,'end':start+len(token),'quote':token.decode()}}]
        return response({'selection':{'kind':'reason','commit':commit},'report_update':{'limitation':'attribution_unknown'} if nested and len(captured)==1 else {}})
    script=[response(commission('literature',outer))]
    if nested:
        inner={'version':'strategy_assignment_v1','question_context_refs':[],'prior_search_refs':[source,article],GRID_REQUESTED:SELECTORS}
        script.append(response(commission('literature_strategy',inner)))
    script += [work,integrate,*([integrate] if nested else [])]
    class FixturePresented(PresentedProvider):
        async def complete(self,episode_id,*args):self.active_episode=episode_id;return await super().complete(episode_id,*args)
    provider=FixturePresented(script) if profile else ScriptedProvider(script)
    progress=ScientificFindingProgress(FindingProgressPolicy(1))
    asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=tmp_path/'run',
        controller_factory=lambda path,initial:FixtureController(str(path),initial,2 if len(path)==1 or nested and len(path)==2 else 1),
        project_credit=progress,initial_known_record_refs=[source,article],
        episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,reference_parent_sources=[source,article],contract_information_profile=profile),),
        binding_definitions={'credit':progress.as_record()},**({'decision_protocol':'decision_exchange_v1'} if profile else {})))
    observations=5 if nested else 3
    assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==observations
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==observations
    assert store.db.execute('SELECT count(*) FROM literature_rate_observation_operations').fetchone()[0]==1
    run_id,parent=store.db.execute('SELECT run_id,episode_id FROM literature_rate_grid_received ORDER BY rowid DESC LIMIT 1').fetchone()
    original=captured[-1];ref=original['numbers'][0]['sheet_ref'];repo=LiteratureReportedCurveRepository(store,run_id);saved=repo.read(ref)
    descriptors=json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])['episode_bindings']
    allowed={store.get(ref)[key] for key in ('artifact_ref','request_ref')}
    receiver=replace(ctx,run_id=run_id,episode_id=parent,role='annotation',path=(('annotation',parent),),assignment={},received_record_refs=tuple(repo.cell_record_refs(original['numbers'])))
    for name,value in [('ORIGINAL_FORM_231.json',original),('ORIGINAL_SCHEMA_231.json',literal),('ORIGINAL_SHEET_231.json',saved),('ORIGINAL_DESCRIPTOR_231.json',descriptors)]:
        (tmp_path/name).write_text(json.dumps(value,indent=2)+'\n')
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close();before=state_hashes(tmp_path/'state')
    block_science(monkeypatch);monkeypatch.setattr(type(provider),'complete',forbid)
    with readonly(tmp_path/'state') as cold:
        get=cold.get_artifact
        def saved_only(reference):assert reference in allowed,'Only original saved sheet/request artifacts permitted';return get(reference)
        monkeypatch.setattr(cold,'get_artifact',saved_only)
        host=SimpleNamespace(store=cold,run_id=run_id,tools=None)
        restored=compose_episode_bindings(WorkflowServices(host),store=cold,journal=SimpleNamespace(store=cold,run_id=run_id),
            execution_backend=None,descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
        host.episode_bindings=EpisodeBindingRegistry(restored.bindings);binding,=restored.bindings
        assert binding.received_report_facts(receiver)[GRID_NAMESPACE]==original['numbers']
        assert binding._rate_grid_repository().read(ref)==saved
        assert binding._rate_fact_sources()[GRID_NAMESPACE]['report_schema']==literal['properties']['numbers']
        assert cold.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==observations
        assert cold.db.total_changes==0
    assert before==state_hashes(tmp_path/'state')
    (tmp_path/'COLD_PROOF_231.json').write_text(json.dumps({'profile':profile,'alias':alias,'nondetection':nondetection,'nested':nested,
        'original_form_schema_rows_descriptor':True,'first_readonly_composer':True,'scientific_source_parser_fit_model_receive_attestation_blocked':True,
        'ordinary_actions_and_observations':observations,'selected_population_operations':1,'changed_rows':0,'state_files':before,
        'actual_model_execution':False,'A105_adequacy_claim':False},indent=2)+'\n')


def test_nested_narrower_return_preserves_exact_admitted_scalar(tmp_path,monkeypatch):
    shared_case(tmp_path,monkeypatch,None,True,False,nested=True)


def test_actual_old_v1_closed_data_is_exact_without_reinterpretation(tmp_path,monkeypatch):
    from test_literature_compiled_assay_185 import readonly
    baseline=json.loads((BASE/'OLD_V1_BASELINE_001.json').read_text());proof=Path(baseline['proof_directory']);state=proof/'state'
    before=state_hashes(state);assert before==baseline['state_files']
    expected=json.loads((proof/'ADMITTED_ROWS_001.json').read_text())['activity']
    saved=json.loads((proof/'SAVED_SHEET_001.json').read_text());block_science(monkeypatch)
    import gene_annotation_episode.literature_rate_observation_storage as storage
    monkeypatch.setattr(storage,'read_rate_observations',forbid);monkeypatch.setattr(storage,'populate_rate_observation_contrast',forbid)
    with readonly(state) as cold:
        run_id,parent=cold.db.execute('SELECT run_id,episode_id FROM literature_rate_observation_received').fetchone()
        repo=LiteratureRateObservationRepository(cold,run_id);ref=expected[0]['sheet_ref'];meta=cold.get(ref)
        get=cold.get_artifact;allowed={meta['artifact_ref'],meta['request_ref']}
        def saved_only(r):assert r in allowed;return get(r)
        monkeypatch.setattr(cold,'get_artifact',saved_only)
        ctx=BindingContext(run_id,parent,'annotation',(('annotation',parent),),cold.validate_scope(),{}, {},(ref,))
        assert repo.read(ref)==saved and repo.received_cells(ctx)==expected
        assert cold.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==3 and cold.db.total_changes==0
    assert before==state_hashes(state)


@pytest.mark.parametrize('profile',[None,'operation_contract_information_v1'])
def test_pending_grid_alias_uses_original_frozen_declaration(tmp_path,monkeypatch,profile):
    from gene_annotation_episode import literature_numerical_contracts as contracts
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy,ScientificFindingProgress
    from gene_annotation_episode.runtime import Workflow
    from test_contract_information_runtime_059 import PresentedProvider
    from test_runtime import FixtureController
    from test_runtime_decision_exchanges import select as action
    store,ctx,args,source,article=setup(tmp_path/'state')
    limit={'type':'string','enum':['attribution_unknown']}
    literal=obj({'numbers':rate_grid_cells_schema(),'limits':limit})
    submitted=obj({'numbers':{'$ref':'episode-fact:'+GRID_NAMESPACE},'limits':limit})
    choice=action({'selection':{'kind':'episode_child','role':'literature','assignment':plain(ctx.assignment),
        'goal':'Evaluate reported precision.','scope':plain(ctx.scope),'purpose':'Return selected scalar source evidence.',
        'schema_json':json.dumps(submitted),'initial_report_json':json.dumps({'limits':'attribution_unknown'})},'report_update':{}})
    provider=PresentedProvider([OSError('Controlled pending231 interruption')])
    workflow=Workflow(store,ToolRegistry(store),provider,tmp_path/'run',ctx.run_id,
        lambda path,initial:FixtureController(str(path),initial,2),ScientificFindingProgress(FindingProgressPolicy(1)),
        initial_known_record_refs=[source,article],episode_binding_factories=(partial(LiteratureEpisodes,
            rate_population=True,reference_parent_sources=[source,article],contract_information_profile=profile),),
        decision_protocol='decision_exchange_v1')
    root=workflow.build('annotation','root','Evaluate source experimental evidence.',plain(ctx.scope))
    try:
        with pytest.raises(OSError,match='pending231'):asyncio.run(root.run_async(workflow.context))
        # This is a controlled fixture request, never a private provider payload.
        original=workflow.journal.row('runtime_model_calls',root.source.episode_id,0)['request']
        for name in ('report_sources','catalog','action_schema'):monkeypatch.setattr(Workflow,name,forbid)
        factory=contracts.registered_schema;monkeypatch.setattr(contracts,'registered_schema',forbid)
        schema,declaration=workflow.expanded_contract_form(root.source,choice['response']['selection'],0,'literature')
        assert schema==literal and declaration['submitted_schema_json']==choice['response']['selection']['schema_json']
        assert workflow.journal.row('runtime_model_calls',root.source.episode_id,0)['request']==original
        monkeypatch.setattr(contracts,'registered_schema',factory)
        provider.script=iter([choice]);root.source.calls=0
        async def choose_only():return await root.source.next(SimpleNamespace())
        assert asyncio.run(choose_only()) is not None
        child=json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE json_array_length(path)=2').fetchone()[0])
        assert child['report_contract']['measurements']['schema']==literal
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==0
    finally:store.close()

