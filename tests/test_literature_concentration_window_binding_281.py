"""Controlled engineering integration of the already converted concentration case."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts,plain,validate_closed_schema,validate_form,ReportBoundaryError
from gene_annotation_episode.domain import ContractError,canonical,obj,validate_schema
from gene_annotation_episode.episode_bindings import BindingContext,EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_a105_worksheet import a105_worksheet_template,FAMILIES,VERSION as WORKSHEET
from gene_annotation_episode.literature_concentration_window_prompt import CONCENTRATION_WINDOW_TASK
from gene_annotation_episode.literature_concentration_window_storage import (
    LiteratureConcentrationWindowRepository,concentration_window_cells_schema,concentration_window_operation_schema,
    ORIGINAL_SCHEMAS,NAMESPACE,REQUESTED,VIEW,VERSION,OPERATION,POPULATION,COMPONENTS)
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_concentration_window_275 import synthetic,load,CASE

ROOT=Path(__file__).resolve().parents[1]
SELECTED=['substrate_loss','chemical_discrepancy','fate_fraction','source_interval_average_total_product',
    'scenario_interval_average_total_product','chemical_discrepancy_variance']


def setup(path,components=SELECTED,*,original=False,covariance=None,partial_pair=False):
    if original:
        selection=load('SOURCE_SELECTION_PROPOSAL_002.json')
        docs={'source:elife65773_original_fig6_xlsx':(CASE/'elife65773_fig6.xlsx').read_bytes(),
            'source:elife65773_original_html':(CASE/'elife65773.html').read_bytes()}
    else:selection,docs=synthetic()
    store=Store(path);manifest=path/'empty-manifest.json';manifest.write_text(json.dumps({'schema_version':1,'entries':[]}));store.create_problem(manifest_path=manifest)
    def source(raw,parents=(),origin='caller'):
        artifact=store.artifact(raw)
        return store.put('source',dict(provider='retained_original_concentration281' if original else 'explicit_synthetic_concentration281',
            accession=None,uri=None,artifact_ref=artifact,text_ref=artifact,request_ref=None,version=None,retrieved_at=None,parent_source_refs=list(parents)),origin=origin)['id']
    mapping={}
    for old,data in docs.items():mapping[old]=source(data,parents=list(mapping.values())[:1])
    def remap(value):
        if isinstance(value,dict):return {k:remap(v) for k,v in value.items()}
        if isinstance(value,list):return [remap(v) for v in value]
        return mapping.get(value,value) if isinstance(value,str) else value
    selection=remap(selection);selection['requested_cells']=list(components);sources=list(mapping.values())
    def read(ref,rep):
        r=store.get(ref);a=r['artifact_ref'] if rep=='original' else r['text_ref'];return dict(artifact_ref=a,content=store.get_artifact(a))
    if covariance is not None:
        from gene_annotation_episode.literature_concentration_window_inputs import read_concentration_window_inputs
        if covariance=='unsupported':raw=b'explicit synthetic observation table; no implemented C estimator'
        else:
            e=read_concentration_window_inputs(selection,read_source=read);doc=load('SYNTHETIC_COVARIANCE_DOCUMENT_001.json')
            doc['owner_keys']=[e['quantities'][r]['owner_key'] for r in doc['roles']]
            doc['dependency_keys']=[e['quantities'][r]['dependency_keys'] for r in doc['roles']]
            doc['variance_status']=covariance
            if covariance=='unknown':doc['covariance']=None
            raw=json.dumps(doc).encode()
        ref=source(raw,parents=[selection['source_ref']]);sources.append(ref)
        selection['covariance_source_ref']=ref
        selection['covariance_material']='unsupported_observation_table' if covariance=='unsupported' else 'closed_joint_estimator_covariance_document'
    if partial_pair:
        selection['pair_relationships']['total_product']['endpoint_comparability']=dict(value='unknown',witnesses=[])
    context=[]
    for name,field in selection['assay'].items():
        if name not in ('arrangement','participants') and field is not None:
            context.append(dict(field='assay.'+name,participant_index=None,windows=[dict(start=0,end=len(field['quote'].encode()))]))
    for i,p in enumerate(selection['assay']['participants']):context.append(dict(field='assay.participants.identity',participant_index=i,
        windows=[dict(start=0,end=len(p['identity']['quote'].encode()))]))
    for role,q in selection['quantities'].items():
        if q:
            for name in ('analyte','unit'):
                if q[name] is not None:context.append(dict(field='quantities.'+role+'.'+name,participant_index=None,windows=[dict(start=0,end=len(q[name]['quote'].encode()))]))
    args=dict(version=POPULATION,selection=selection,return_context=context)
    assignment=dict(version='literature_assignment_v1',source_refs=sources,question_context_refs=[],**{REQUESTED:list(components)})
    ctx=BindingContext('window281','child281','literature',(('literature','child281'),),store.validate_scope(),assignment,{},tuple(sources))
    host=SimpleNamespace(store=store,run_id=ctx.run_id,tools=ToolRegistry(store))
    binding=LiteratureEpisodes(WorkflowServices(host),rate_population=True,reference_parent_sources=sources)
    host.episode_bindings=EpisodeBindingRegistry((binding,))
    return store,ctx,args,binding,source


def selected(store,ctx,args,binding,key='selected281'):
    outcome=asyncio.run(binding.execute(ctx,OPERATION,args,key));assert outcome['status']=='completed',outcome
    current=replace(ctx,received_record_refs=(*ctx.received_record_refs,*outcome['record_refs']))
    schema=obj(dict(numbers=concentration_window_cells_schema()))
    form=form_with_facts({},schema,binding.facts(current,dict(committed_record_refs=outcome['record_refs'])))
    binding.validate_report(current,form,schema)
    return current,outcome,form['numbers']


def forbid(*args,**kwargs):raise AssertionError('Source/science/current factory/projection/receive/model/write forbidden')


def block_science(monkeypatch):
    from gene_annotation_episode import literature_concentration_window_inputs as inputs
    from gene_annotation_episode import literature_concentration_window_calculations as calculations
    from gene_annotation_episode import literature_concentration_window_storage as storage
    from gene_annotation_episode import literature_numerical_contracts as contracts
    from gene_annotation_episode import providers
    for module,names in ((inputs,['read_concentration_window_inputs','compile_concentration_window_inputs',
            'validate_concentration_window_extraction','validate_concentration_window_calculation_inputs',
            'concentration_window_selection_schema','concentration_window_extraction_schema','concentration_window_calculation_inputs_schema',
            'concentration_window_sheet_schema','concentration_window_covariance_schema']),
            (calculations,['populate_concentration_window','validate_concentration_window_sheet','concentration_window_sheet_schema']),
            (storage,['concentration_window_cells_schema','concentration_window_operation_schema','_project_once','_scoped_context_once','_validate_windows','_withheld']),
            (contracts,['registered_schema']),
            (providers.ModelConnection,['complete']),(providers._SessionConnection,['complete']),
            (LiteratureConcentrationWindowRepository,['populate','receive_cells','_original_implementation'])):
        for name in names:monkeypatch.setattr(module,name,forbid)


def test_exact_contracts_registration_lazy_discovery(tmp_path):
    from gene_annotation_episode.episode_contract_information import expand_fact_form
    from gene_annotation_episode import literature_concentration_window_inputs as i
    released=json.loads((ROOT/'verification/a105_concentration_window_binding_281/PROPOSED_SCHEMAS_003.json').read_text())
    assert ORIGINAL_SCHEMAS==released
    assert ORIGINAL_SCHEMAS['selection']==i.concentration_window_selection_schema()
    assert 'selected_integration_unimplemented' not in released['rows']['items']['properties']['limits']['items']['enum']
    assert 'selected_integration_unimplemented' in released['sheet']['properties']['limits']['items']['enum']
    store,ctx,args,binding,_=setup(tmp_path/'state')
    try:
        before=store.db.total_changes
        assert REQUESTED in binding.assignment_schema('literature')['properties']
        assert NAMESPACE in binding.fact_sources('literature')
        assert sum(r['name']==OPERATION for r in binding.catalog(ctx))==1
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_concentration_window_operations'").fetchone()
        assert store.db.total_changes==before
        literal=obj(dict(numbers=concentration_window_cells_schema()));validate_closed_schema(literal)
        alias=obj(dict(numbers={'$ref':'episode-fact:'+NAMESPACE}))
        out=expand_fact_form(json.dumps(alias),child_role='literature',facts_by_role={'literature':binding.fact_sources('literature')},permitted_child_roles=['literature'])
        assert out['expanded_schema']==literal
        changed=deepcopy(literal);changed['properties']['numbers']['minItems']=0
        with pytest.raises(ReportBoundaryError):validate_closed_schema(changed)
        with pytest.raises(ReportBoundaryError):validate_closed_schema(obj(dict(nested=literal)))
        disabled=LiteratureEpisodes(WorkflowServices(binding.services.workflow))
        assert NAMESPACE not in disabled.fact_sources('literature')
        assert not any(r['name']==OPERATION for r in disabled.catalog(ctx))
        assert len(FAMILIES)==9
    finally:store.close()


@pytest.mark.parametrize('components',[[],['substrate_start'],SELECTED])
def test_original_selected_rows_order_partials_and_replay(tmp_path,components):
    store,ctx,args,binding,_=setup(tmp_path/'state',components,original=True)
    try:
        current,out,rows=selected(store,ctx,args,binding)
        assert [r['component'] for r in rows]==components
        by={r['component']:r for r in rows}
        if components==SELECTED:
            assert by['substrate_loss']['cell']['value']==100
            assert by['chemical_discrepancy']['cell']['value']==5.5
            assert by['fate_fraction']['cell']['exact_value']==dict(numerator='104',denominator='945')
            assert by['source_interval_average_total_product']['cell']['value'] is None
            assert by['scenario_interval_average_total_product']['cell']['conditional_exact_value']==dict(numerator='810',denominator='7')
            assert by['chemical_discrepancy_variance']['cell']['reasons']['selection']==['covariance_not_selected']
            assert by['chemical_discrepancy']['scientific_context']['stoichiometry']['substrate']['value']==1
            assert by['substrate_loss']['scientific_context']['stoichiometry']=={}
            assert set(by['substrate_loss']['scientific_context']['quantities'])=={'substrate_start','substrate_end'}
            assert by['substrate_loss']['operand_metadata'][0]['origin']=='reported'
            assert 'matrix' not in canonical(rows)
            assert all('selected_integration_unimplemented' not in r['limits'] for r in rows)
        repo=binding._concentration_window_repository();saved=repo.read(out['result']['sheet_ref'])
        assert 'selected_integration_unimplemented' in saved['sheet']['limits']
        assert set(saved['artifacts'])=={'extraction','inputs','sheet','projection'}
        assert asyncio.run(binding.execute(ctx,OPERATION,args,'selected281'))==out
        assert store.db.execute('SELECT count(*) FROM literature_concentration_window_operations').fetchone()[0]==1
    finally:store.close()


def test_one_selected_population_not_internal_or_replay_observations(tmp_path,monkeypatch):
    from gene_annotation_episode import literature_concentration_window_inputs as i
    from gene_annotation_episode import literature_concentration_window_calculations as c
    store,ctx,args,binding,_=setup(tmp_path/'state',['substrate_loss'])
    calls=dict(read=0,compile=0,populate=0)
    def counted(name,function):
        def call(*a,**k):calls[name]+=1;return function(*a,**k)
        return call
    try:
        monkeypatch.setattr(i,'read_concentration_window_inputs',counted('read',i.read_concentration_window_inputs))
        monkeypatch.setattr(i,'compile_concentration_window_inputs',counted('compile',i.compile_concentration_window_inputs))
        monkeypatch.setattr(c,'populate_concentration_window',counted('populate',c.populate_concentration_window))
        _,out,_=selected(store,ctx,args,binding)
        assert calls==dict(read=1,compile=1,populate=1)
        for module,names in ((i,('read_concentration_window_inputs','compile_concentration_window_inputs')),(c,('populate_concentration_window',))):
            for name in names:monkeypatch.setattr(module,name,forbid)
        assert asyncio.run(binding.execute(ctx,OPERATION,args,'selected281'))==out
        assert store.db.execute('SELECT count(*) FROM literature_concentration_window_operations').fetchone()[0]==1
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_observations'").fetchone()
    finally:store.close()


def test_source_bytes_and_nested_covariance_custody(tmp_path):
    store,ctx,args,binding,source=setup(tmp_path/'state',['substrate_loss_variance'])
    try:
        alien=source(b'unreceived covariance');args['selection'].update(covariance_source_ref=alien,covariance_material='unsupported_observation_table')
        out=asyncio.run(binding.execute(ctx,OPERATION,args,'unreceived281'))
        assert out['status']=='invalid' and 'not_received' in out['feedback']['code']
        page=dict(version='page_assignment_v1',source_ref=args['selection']['source_ref'],representation='original',
            artifact_ref=store.get(args['selection']['source_ref'])['artifact_ref'],question_context_refs=[],prior_delivery_refs=[],**{REQUESTED:['substrate_loss_variance']})
        page_ctx=replace(ctx,role='literature_page',path=(('literature_page',ctx.episode_id),),assignment=page,received_record_refs=(*ctx.received_record_refs,alien))
        out=asyncio.run(binding.execute(page_ctx,OPERATION,args,'outside281'))
        assert out['status']=='invalid' and 'outside_assigned_source' in out['feedback']['code']
    finally:store.close()


def test_actual_source_callback_rejects_changed_bytes(tmp_path,monkeypatch):
    store,ctx,args,binding,_=setup(tmp_path/'state',['substrate_loss'])
    try:
        artifact=store.get(args['selection']['source_ref'])['artifact_ref'];get=store.get_artifact
        monkeypatch.setattr(store,'get_artifact',lambda ref:get(ref)+b'changed' if ref==artifact else get(ref))
        outcome=asyncio.run(binding.execute(ctx,OPERATION,args,'changed_bytes281'))
        assert outcome['status']=='invalid' and outcome['feedback']['code']=='concentration_window_source_artifact_hash_mismatch'
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_concentration_window_operations'").fetchone()
    finally:store.close()


@pytest.mark.parametrize('failure',['roster','source','context_number','participant','utf8','overlap'])
def test_selected_preflight_failures_do_not_commit(tmp_path,failure):
    store,ctx,args,binding,source=setup(tmp_path/'state',original=failure=='utf8')
    try:
        if failure=='roster':args['selection']['requested_cells'].reverse()
        elif failure=='source':args['selection']['source_ref']=source(b'not received')
        elif failure=='context_number':
            q=args['selection']['quantities']['substrate_start'];args['selection']['assay']['conditions']=deepcopy(q['number']['field'])
            entry=next(v for v in args['return_context'] if v['field']=='assay.conditions');entry['windows']=[dict(start=0,end=len(q['number']['field']['quote'].encode()))]
        elif failure=='participant':args['return_context'][0]['participant_index']=0
        elif failure=='utf8':
            field=args['selection']['assay']['conditions'];raw=field['quote'].encode();index=next(i for i,b in enumerate(raw) if b>=128)
            entry=next(v for v in args['return_context'] if v['field']=='assay.conditions')
            entry['windows']=[dict(start=index+1,end=len(raw))]
        else:args['return_context'][0]['windows']*=2
        outcome=asyncio.run(binding.execute(ctx,OPERATION,args,'bad281'))
        assert outcome['status']=='invalid' and outcome['feedback']
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_concentration_window_operations'").fetchone()
    finally:store.close()


@pytest.mark.parametrize('covariance',['known','estimated','unknown','unsupported'])
def test_covariance_metadata_scoped_without_matrix(tmp_path,covariance):
    store,ctx,args,binding,_=setup(tmp_path/'state',['substrate_loss','substrate_loss_variance'],covariance=covariance)
    try:
        _,_,rows=selected(store,ctx,args,binding)
        c=rows[-1]['covariance_context']
        assert c['selection_status']=='selected'
        assert c['variance_status']==(None if covariance=='unsupported' else covariance)
        def field_names(value):
            if isinstance(value,dict):
                for key,child in value.items():yield key;yield from field_names(child)
            elif isinstance(value,list):
                for child in value:yield from field_names(child)
        assert not {'matrix','matrix_exact','covariance','derived_covariance','raw_document_utf8'} & set(field_names(rows))
        assert rows[0]['cell']['value']==60
        if covariance in ('known','estimated'):
            assert rows[1]['cell']['value'] is not None
            assert c['origin']=='synthetic' and c['roles'] and len(c['roles'])==len(c['owner_keys'])==len(c['units'])==len(c['dependency_keys'])
        else:
            assert rows[1]['cell']['value'] is None
            assert ('covariance_estimation_from_table_unimplemented' in rows[1]['cell']['reasons']['implementation'])==(covariance=='unsupported')
    finally:store.close()


def test_partial_pair_meaning_and_exact_nonowner_subset(tmp_path):
    store,ctx,args,binding,_=setup(tmp_path/'state',['substrate_loss','total_product_gain','chemical_ratio'],partial_pair=True)
    try:
        current,out,rows=selected(store,ctx,args,binding);repo=binding._concentration_window_repository()
        assert rows[0]['cell']['value']==60 and rows[1]['cell']['value'] is None and rows[2]['cell']['value'] is None
        receiver=replace(current,episode_id='parent281',role='annotation',path=(('annotation','parent281'),),assignment={})
        subset=[rows[2],rows[0]];repo.receive_cells(receiver,subset,'trusted-engineering-subset')
        assert repo.fact_cells(receiver,[out['result']['sheet_ref']],components=['total_product_gain','chemical_ratio','substrate_loss'])==subset
        with pytest.raises(ContractError,match='not_received'):repo.validate_fact_values(receiver,[rows[1]])
        with pytest.raises(ContractError,match='private'):repo.authorize_source_access(receiver,out['result']['sheet_ref'],'original','source.read')
        binding.validate_received_report(replace(receiver,assignment={REQUESTED:['chemical_ratio','substrate_loss']}),dict(numbers=subset),obj(dict(numbers=concentration_window_cells_schema())))
    finally:store.close()


def test_recurring_full_task_from_actual_sources_not_capabilities(tmp_path):
    from gene_annotation_episode.literature_task_selection import selected_literature_task_sections as select
    store,ctx,args,binding,_=setup(tmp_path/'state',[])
    try:
        state=dict(literature_assignment={REQUESTED:[]})
        assert (NAMESPACE,CONCENTRATION_WINDOW_TASK) in select(state)
        assert not select(dict(tools=binding.catalog(ctx),literature_concentration_window_work=True))
        for form in (obj(dict(numbers=concentration_window_cells_schema())),obj(dict(numbers={'$ref':'episode-fact:'+NAMESPACE}))):
            assert (NAMESPACE,CONCENTRATION_WINDOW_TASK) in select(dict(requested_form=form))
        assert (NAMESPACE,CONCENTRATION_WINDOW_TASK) in select(dict(literature_selected_population_attempt=dict(tool=OPERATION,status='invalid',arguments=dict(version=POPULATION))))
        for result in (dict(information_kind='operation_contract_information_v1',operation=OPERATION),dict(information_kind='return_contract_information_v1',source=NAMESPACE)):
            assert (NAMESPACE,CONCENTRATION_WINDOW_TASK) in select({},[dict(status='completed',result=result)])
        current,out,rows=selected(store,ctx,args,binding)
        assert NAMESPACE in binding._owned_population_task_sources(current)
        assert not binding._owned_population_task_sources(replace(current,received_record_refs=ctx.received_record_refs))
        assert (NAMESPACE,CONCENTRATION_WINDOW_TASK) in select({},[dict(status='completed',result=dict(view='records',records=[dict(selection=dict(tool=OPERATION,arguments=args))]))])
    finally:store.close()


@pytest.mark.parametrize('parent',[False,True])
@pytest.mark.parametrize('route',['empty_roster','alias','literal'])
def test_full_recurring_task_both_directions_preserves_base_caller_and_steering(parent,route):
    from test_literature_task_selection_274 import state
    from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK,SAVED_NUMERICAL_RETURN_TASK
    from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
    value=state(parent);caller='Keep the original caller concentration-evidence question and constraints in full.'
    if route=='empty_roster':value['literature_assignment'][REQUESTED]=[]
    else:value['requested_form']=obj(dict(chosen={'$ref':'episode-fact:'+NAMESPACE} if route=='alias' else concentration_window_cells_schema()))
    before=deepcopy(value)
    for current in (value,deepcopy(value)):
        task,steering=render_literature_experimental_prompt(current,caller).split('\n\nSTEERING\n')
        assert task.count(CONCENTRATION_WINDOW_TASK)==1 and caller in task and SAVED_NUMERICAL_RETURN_TASK in task
        assert (REFERENCE_PARENT_TASK if parent else EXPERIMENTAL_TASK) in task
        assert value['goal']['objective'] in task and 'Own action yields' in steering
    assert value==before


@pytest.mark.parametrize('alias,nested,original',[(False,False,False),(True,True,False),(True,False,True)])
def test_shared_loop_common_worksheet_typed_delivery_and_fresh_cold(tmp_path,monkeypatch,alias,nested,original):
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.investigation_progress import ScientificFindingProgress,FindingProgressPolicy
    from test_runtime import FixtureController,ScriptedProvider
    requested=SELECTED if original else ['substrate_loss','chemical_discrepancy','fate_fraction']
    store,ctx,args,_,_=setup(tmp_path/'state',requested,original=original)
    sources=list(ctx.received_record_refs);outer_components=list(reversed(requested[:2])) if nested else requested
    template=a105_worksheet_template([dict(field='window',source=NAMESPACE,components=outer_components)])
    context=dict(version=WORKSHEET,assertion_refs=[],quantity_links=[],assertion_links=[])
    submitted=template['submitted_form'] if alias else obj(dict(window=concentration_window_cells_schema(),assessment_context=template['submitted_form']['properties']['assessment_context']))
    inner_template=a105_worksheet_template([dict(field='window',source=NAMESPACE,components=requested)])
    inner_submitted=inner_template['submitted_form'] if alias else submitted
    captured=[];prompts=[]
    def commission(role,assignment,form):return dict(selection=dict(kind='episode_child',role=role,assignment=assignment,
        goal='Evaluate the selected concentration window for the actual reference molecule.',scope=plain(ctx.scope),
        purpose='Return requested concentration components with actual experimental qualifications.',schema_json=json.dumps(form),
        initial_report_json=json.dumps(dict(assessment_context=context))),report_update={})
    def work(inputs):
        assert CONCENTRATION_WINDOW_TASK in render_literature_experimental_prompt(inputs,'Read the selected concentration window.')
        return dict(selection=dict(kind='tool',tool=OPERATION,arguments=args),report_update=dict(assessment_context=context))
    def integrate(inputs):
        form,=inputs['child_reports'];captured.append(deepcopy(form))
        wanted=outer_components if nested and len(captured)==2 else requested
        assert [r['component'] for r in form['window']]==wanted
        prompt=render_literature_experimental_prompt(inputs,'Integrate received source evidence.');prompts.append(prompt)
        assert CONCENTRATION_WINDOW_TASK in prompt and 'A105 experimental evidence worksheet' in prompt
        assert 'matrix_exact' not in prompt.split('\n\nSTEERING\n')[1]
        if original:
            assert 'Wild-type PARP1' in prompt and 'Nuc165' in prompt
            assert 'conditional timing sensitivity' in prompt and 'timing meaning unknown' in prompt
        commit={k:[] for k in store.reasoning_schema()['required']};w=args['selection']['assay']['molecule']
        commit['source_subjects']=[dict(alias='studied_window281',reference_type='assay',source_ref=w['source_ref'],label=w['quote'],
            anchor=dict(source_ref=w['source_ref'],artifact_ref=store.get(w['source_ref'])['artifact_ref'],start=w['start'],end=w['end'],quote=w['quote']))]
        return dict(selection=dict(kind='reason',commit=commit),report_update=dict(assessment_context=context) if nested and len(captured)==1 else {})
    script=[commission('literature',{**plain(ctx.assignment),REQUESTED:outer_components},submitted)]
    if nested:script.append(commission('literature_strategy',dict(version='strategy_assignment_v1',question_context_refs=[],prior_search_refs=sources,**{REQUESTED:requested}),inner_submitted))
    script += [work,integrate,*([integrate] if nested else [])]
    provider=ScriptedProvider(script);progress=ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=tmp_path/'run',
            controller_factory=lambda path,initial:FixtureController(str(path),initial,2 if len(path)==1 or nested and len(path)==2 else 1),
            project_credit=progress,binding_definitions={'credit':progress.as_record()},initial_known_record_refs=sources,
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,reference_parent_sources=sources),)))
        assert len(captured)==(2 if nested else 1)
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==(5 if nested else 3)
        assert store.db.execute('SELECT count(*) FROM literature_concentration_window_operations').fetchone()[0]==1
        run_id,parent=store.db.execute('SELECT run_id,episode_id FROM literature_concentration_window_received ORDER BY rowid DESC LIMIT 1').fetchone()
        form=captured[-1];ref=form['window'][0]['sheet_ref'];repo=LiteratureConcentrationWindowRepository(store,run_id);saved=repo.read(ref)
        descriptors=json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])['episode_bindings']
        assert saved['original_implementation']['bound_descriptor']==descriptors[0]
        receiver=replace(ctx,run_id=run_id,episode_id=parent,role='annotation',path=(('annotation',parent),),assignment={},
            received_record_refs=tuple(repo.cell_record_refs(form['window'])))
        literal=obj(dict(window=concentration_window_cells_schema(),assessment_context=template['submitted_form']['properties']['assessment_context']))
        allowed={store.get(ref)[k] for k in ('artifact_ref','request_ref')}|set(saved['artifacts'].values())
        for name,value in [('ORIGINAL_FORM_281.json',form),('ORIGINAL_SCHEMA_281.json',literal),('ORIGINAL_DESCRIPTOR_281.json',descriptors),
                ('ORIGINAL_RECEIVER_281.json',receiver.as_record()),('ORIGINAL_ARTIFACTS_281.json',sorted(allowed)),('ORIGINAL_SAVED_281.json',saved)]:
            (tmp_path/name).write_text(json.dumps(value,indent=2)+'\n')
        (tmp_path/'RECEIVING_PROMPT_281.txt').write_text(prompts[-1])
        store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close()
        completed=subprocess.run([sys.executable,'-B',str(ROOT/'verification/a105_concentration_window_binding_281/first_cold_process_003.py'),str(tmp_path)],cwd=ROOT,text=True,capture_output=True)
        (tmp_path/'FRESH_COLD_STDOUT_281.txt').write_text(completed.stdout);(tmp_path/'FRESH_COLD_STDERR_281.txt').write_text(completed.stderr)
        assert completed.returncode==0,completed.stderr
        proof=json.loads((tmp_path/'FRESH_COLD_PROCESS_281.json').read_text())
        assert proof['fresh_process'] and proof['state_byte_hashes_unchanged'] and proof['sqlite_changes']==0 and proof['only_original_receipt_artifacts_read']
    finally:
        try:store.close()
        except Exception:pass
