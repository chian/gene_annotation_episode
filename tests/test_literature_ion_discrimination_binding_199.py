"""Controlled original Fluc and explicitly synthetic integration; no live model."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema, validate_form, form_with_facts, plain
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_ion_discrimination_storage import (
    LiteratureIonDiscriminationRepository, ion_discrimination_cells_schema, COMPONENTS, NAMESPACE, REQUESTED)
from gene_annotation_episode.literature_ion_discrimination_inputs import activity_key, dependency_keys
from gene_annotation_episode.literature_ion_discrimination_prompt import ION_DISCRIMINATION_TASK
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.episode_contract_information import return_contract_information, expand_fact_form
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.runtime import run_workflow
from test_literature_ion_discrimination_components_194 import common, source_quantity, SOURCE
from test_literature_assay_inputs import witness, measurement
from test_literature_compiled_assay_185 import remap, add_source
from test_runtime import FixtureController, ScriptedProvider

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_ion_discrimination_design_194/original_application_001'
TEXT = ('Synthetic E. coli Ec2 construct V2 genotype K12 in liposomes. Fluoride versus chloride. '
    'NaF 300 mM at pH 7.0, voltage -100 mV. Matched conditions and protein/ion controls. '
    'Fluoride rate >11876.54321 ions/s; chloride rate <51.345678 ions/s. '
    'Another report has rate 732.49876 ions/s with spread ± 3.456789 ions/s. '
    'Ion-specific controls, molecular normalization and preparations are explicitly stipulated synthetic meanings.')
REQUEST = ['nominal_threshold_ratio']
FORM = obj({'numbers': ion_discrimination_cells_schema()})


def setup(path, requested=REQUEST, original=None):
    store=Store(path);store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    if original:
        packet=json.loads((PACKET/(original+'.json')).read_text());args=packet['selection']
        raw=(ROOT/'research/experimental_scoring_review_2026-10-23/a105_transport_channel_case_174/source/elife-01084-v1.xml').read_bytes()
        assert hashlib.sha256(raw).hexdigest()=='83867d6966a972f32899bdfe545c9952cb9d10393dc54d68dce29b6f4954b053'
    else:
        raw=TEXT.encode();args={**common(TEXT),'route':'reported_threshold_pair',
            'thresholds':{'preferred':source_quantity(TEXT,'11876.54321','ions/s'),
                'alternative':source_quantity(TEXT,'51.345678','ions/s')}}
        for role in ('preferred','alternative'):
            for name in args['context'][role]:args['context'][role][name]=witness(TEXT,TEXT,source=SOURCE)
        args['context']['preferred_ion']=witness(TEXT,'Fluoride',source=SOURCE)
        args['context']['alternative_ion']=witness(TEXT,'chloride',source=SOURCE)
    source=add_source(store,raw,'controlled_original_source' if original else 'synthetic_ion_fixture')
    args=remap(args,SOURCE,source)
    context=BindingContext('ion-run','ion-child','literature',(('literature','ion-child'),),store.validate_scope(),
        {'version':'literature_assignment_v1','question_context_refs':[],'source_refs':[source],REQUESTED:list(requested)}, {}, (source,))
    return store,context,args


def binding_for(store,context,enabled=True):
    host=SimpleNamespace(store=store,run_id=context.run_id,tools=ToolRegistry(store))
    binding=LiteratureEpisodes(WorkflowServices(host),rate_population=True,ion_discrimination_population=enabled)
    host.episode_bindings=EpisodeBindingRegistry((binding,));return binding


def hashes(path):
    return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}


def readonly(path):
    store=Store.__new__(Store);store.path=Path(path);store._savepoint=0
    store.db=sqlite3.connect((Path(path)/'state.sqlite3').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    store.db.row_factory=sqlite3.Row;store.db.execute('PRAGMA query_only=ON');return store


def forbid(*args,**kwargs):raise AssertionError('cold science function invoked')


def disable_science(monkeypatch):
    for module,names in {
        'literature_ion_discrimination_storage':('read_ion_discrimination_inputs','populate_ion_discrimination','_implementation_receipt'),
        'literature_ion_discrimination_inputs':('read_ion_discrimination_inputs','_read_quantity','_read_covariance','validate_ion_discrimination_extraction'),
        'literature_ion_discrimination_numbers':('read_ion_number','read_ion_unit','check_explicit_unit'),
        'literature_ion_discrimination_calculations':('populate_ion_discrimination','_compiled','_thresholds'),
        'literature_compiled_assay_storage':('read_compiled_assay_inputs','populate_compiled_assay'),
        'literature_assay_inputs':('read_assay_inputs',),
    }.items():
        for name in names:
            if name=='_implementation_receipt':monkeypatch.setattr(LiteratureIonDiscriminationRepository,name,forbid)
            else:monkeypatch.setattr('gene_annotation_episode.'+module+'.'+name,forbid)


def test_exact_selected_projection_retains_biology_and_conditions_without_operands(tmp_path):
    store,ctx,args=setup(tmp_path)
    with store:
        repo=LiteratureIonDiscriminationRepository(store,ctx.run_id)
        assert not repo._installed(repo.operations_table)
        out=repo.populate(ctx,args,'selected');rows=out['result']['cells']
        assert [r['component'] for r in rows]==REQUEST
        row,=rows;assert row['threshold']==pytest.approx(11876.54321/51.345678)
        validate_form({'numbers':rows},FORM,lambda ref,ns:bool(store.get(ref)))
        text=json.dumps(rows)
        for token in ('11876.54321','51.345678','732.49876','3.456789'):assert token not in text
        for token in ('Ec2','V2','K12','300 mM','7.0','-100 mV','Fluoride','chloride'):assert token in text
        assert row['nominal_domain'] is not None and row['physical_domain'] is None
        assert row['zero_denominator_case']=='possible_in_source_domain'
        assert repo.read(out['result']['sheet_ref'])['sheet']['cells']['preferred_activity']['threshold']==11876.54321
        assert not store.list('observation') and not store.list('assessment')


def test_empty_defaults_discovery_and_true_empty_report_are_readonly_and_no_optional_tables(tmp_path):
    store,ctx,args=setup(tmp_path,requested=[])
    with store:
        binding=binding_for(store,ctx)
        before=store.db.total_changes;store.db.execute('PRAGMA query_only=ON')
        repo=binding._ion_discrimination_repository()
        assert repo.project_cells([],permitted_record_refs=[])==[] and repo.received_cells(ctx)==[]
        assert repo.available_sheet_refs(ctx)==[] and repo.selected_sheet_refs(ctx)==[] and not repo.has_work(ctx)
        assert 'literature.ion_discrimination.populate' in {r['name'] for r in binding.catalog(ctx)}
        binding.validate_report(ctx,{'numbers':[]},FORM)
        assert store.db.total_changes==before and not repo._installed(repo.operations_table)
        assert not repo._installed(repo.received_table)


def test_selected_empty_request_populates_once_but_never_expands_components(tmp_path):
    store,ctx,args=setup(tmp_path,requested=[])
    with store:
        repo=LiteratureIonDiscriminationRepository(store,ctx.run_id);out=repo.populate(ctx,args,'empty')
        assert out['result']['cells']==[]
        current=replace(ctx,received_record_refs=(*ctx.received_record_refs,*out['record_refs']))
        assert repo.fact_cells(current,out['record_refs'],components=COMPONENTS)==[]
        with pytest.raises(ContractError,match='component_not_selected'):
            repo.project_cells(out['record_refs'],permitted_record_refs=out['record_refs'],components=['preferred_activity'])


def test_parent_only_admitted_subset_owner_only_original_request_and_malicious_omission(tmp_path):
    store,ctx,args=setup(tmp_path,requested=['preferred_activity','nominal_threshold_ratio'])
    with store:
        repo=LiteratureIonDiscriminationRepository(store,ctx.run_id);out=repo.populate(ctx,args,'selected')
        ref=out['result']['sheet_ref'];rows=out['result']['cells'][1:]
        parent=replace(ctx,episode_id='parent',role='annotation',path=(('annotation','parent'),),assignment={},received_record_refs=(ref,))
        repo.receive_cells(parent,rows,'trusted_fixture_admission')
        assert repo.received_cells(parent)==rows and repo.fact_cells(parent,[ref],components=COMPONENTS)==rows
        with pytest.raises(ContractError,match='cell_not_received'):repo.validate_fact_values(parent,out['result']['cells'][:1])
        current=replace(ctx,received_record_refs=(*ctx.received_record_refs,ref));binding=binding_for(store,ctx)
        binding.validate_report(current,{'numbers':out['result']['cells']},FORM)
        with pytest.raises(ReportBoundaryError,match='subset_mismatch'):binding.validate_report(current,{'numbers':rows},FORM)
        binding.services.workflow.record_selection=lambda episode:{'run_id':ctx.run_id,'episode_id':episode,'known_record_refs':list(current.received_record_refs)}
        with pytest.raises(ReportBoundaryError,match='subset_mismatch'):binding.validate_report(ctx,{'numbers':[]},FORM)
        with pytest.raises(ContractError,match='component_not_selected'):
            repo.project_cells([ref],permitted_record_refs=[ref],components=['alternative_activity'])


@pytest.mark.parametrize('mutation',['signature','value','meaning','omission','operation','unselected_copy','run'])
def test_saved_request_operation_result_and_source_are_authenticated(tmp_path,mutation):
    store,ctx,args=setup(tmp_path)
    with store:
        repo=LiteratureIonDiscriminationRepository(store,ctx.run_id);out=repo.populate(ctx,args,'selected');ref=out['result']['sheet_ref']
        if mutation=='signature':store.db.execute("UPDATE literature_ion_discrimination_operations SET signature='{}'")
        elif mutation=='unselected_copy':
            value={k:v for k,v in store.get(ref).items() if k not in ('id','origin','record_type')};value['accession']='copy'
            ref=store.put('source',value,origin='tool')['id']
        elif mutation=='run':repo=LiteratureIonDiscriminationRepository(store,'wrong-run')
        else:
            changed=deepcopy(out)
            if mutation=='value':changed['result']['cells'][0]['threshold']=999
            elif mutation=='meaning':changed['result']['cells'][0]['relationships']['normalization']['value']='unknown'
            elif mutation=='omission':changed['result']['cells']=[]
            else:changed['operation_ref']='operation_'+'a'*24
            store.db.execute('UPDATE literature_ion_discrimination_operations SET outcome=?',(canonical(changed),))
        with pytest.raises(ContractError):repo.read(ref)


def test_unreceived_sources_and_source_scope_do_not_acquire(tmp_path):
    store,ctx,args=setup(tmp_path)
    with store:
        repo=LiteratureIonDiscriminationRepository(store,ctx.run_id)
        with pytest.raises(ContractError,match='not_received'):repo.populate(replace(ctx,received_record_refs=()),args,'selected')
        assert not repo._installed(repo.operations_table)
        out=repo.populate(ctx,args,'selected')
        changed=deepcopy(args);changed['relationships']['normalization']={'value':'unknown','witnesses':[]}
        with pytest.raises(ContractError,match='reused_for_different_work'):repo.populate(ctx,changed,'selected')
        assert repo.populate(ctx,args,'selected')==out


@pytest.mark.parametrize('original,requested,threshold,kind',[
    ('efflux_summary_thresholds',['preferred_activity','alternative_activity','nominal_threshold_ratio'],1000,'nominal_threshold_comparison'),
    ('Ec2_biionic_reported_permeability',['reported_selectivity'],100,'reported_permeability_ratio'),
    ('Fluc_author_summary',['reported_selectivity'],10000,'reported_cross_assay_summary_ratio')])
def test_retained_primary_source_distinct_quantities_and_limit_meanings(tmp_path,original,requested,threshold,kind):
    store,ctx,args=setup(tmp_path,requested=requested,original=original)
    with store:
        out=LiteratureIonDiscriminationRepository(store,ctx.run_id).populate(ctx,args,'original-controlled')
        last=out['result']['cells'][-1]
        assert last['threshold']==threshold and last['quantity_kind']==kind and last['physical_domain'] is None
        if original=='efflux_summary_thresholds':
            f,cl,nominal=out['result']['cells']
            assert f['threshold']==30000 and f['origin']=='author_inferred' and f['approximation']=='source_qualified'
            assert cl['threshold']==30 and cl['derivation']=='unknown'
            assert nominal['zero_denominator_case']=='possible_in_source_domain'
        elif original=='Ec2_biionic_reported_permeability':assert last['relation']=='lower_limit' and last['approximation']=='source_qualified'
        else:assert last['relation']=='gt' and last['derivation']=='author_summary_inference'


def test_optional_binding_and_registered_schema_are_exact(tmp_path):
    store,ctx,args=setup(tmp_path)
    with store:
        disabled=binding_for(store,ctx,False);baseline=LiteratureEpisodes(disabled.services,rate_population=True)
        assert disabled.catalog(ctx)==baseline.catalog(ctx)
        assert disabled.assignment_schema('literature')==baseline.assignment_schema('literature')
        assert NAMESPACE not in disabled.fact_sources('literature') and 'ion_discrimination_population' not in disabled.as_record()['configuration']
        binding=binding_for(store,ctx);descriptor=binding.as_record()
        assert LiteratureEpisodes(binding.services,**descriptor['configuration']).as_record()==descriptor
        validate_closed_schema(FORM)
        changed=deepcopy(FORM);changed['properties']['numbers']['items']['properties'].pop('relationships')
        with pytest.raises(ReportBoundaryError):validate_closed_schema(changed)
        out=asyncio.run(binding.execute(ctx,'literature.ion_discrimination.populate',args,'bound'))
        assert out['status']=='completed',out
        current=replace(ctx,received_record_refs=(*ctx.received_record_refs,*out['record_refs']))
        form=form_with_facts({},FORM,binding.facts(current,{'committed_record_refs':out['record_refs']}))
        assert form['numbers']==out['result']['cells'];binding.validate_report(current,form,FORM)


def test_full_task_recurrence_safe_own_parent_lookup_current_history_and_aliases(tmp_path):
    store,ctx,args=setup(tmp_path,requested=['preferred_activity','nominal_threshold_ratio'])
    with store:
        out=LiteratureIonDiscriminationRepository(store,ctx.run_id).populate(ctx,args,'selected')
        admitted={'numbers':out['result']['cells'][1:]};marker={'literature_experimental_work':{'version':'literature_experimental_task_v1'}}
        raw=store.get(args['source_ref']);anchor={**witness(TEXT,TEXT,source=args['source_ref']),'artifact_ref':raw['artifact_ref']};anchor.pop('representation')
        alias={'id':'reference_alias','record_type':'reference','origin':'tool','label':TEXT,'anchor':anchor}
        history={'result':{'view':'records','records':[{'selection':{'tool':'literature.ion_discrimination.populate','arguments':args},'outcome':out,'admitted_report':admitted}]}}
        states=[{**marker,'literature_assignment':{REQUESTED:REQUEST}}, {**marker,'last_local_outcome':{'result':{**out['result'],'cells':admitted['numbers']}}},
            {**marker,'current_report_update':admitted},{**marker,'child_reports':[admitted]},
            {**marker,'child_reports':[admitted],'last_local_outcome':out,'current_report_basis_refs':['reference_alias'],
                'literature_received_fact_display':{'records':{'reference_alias':alias},'received_refs':['reference_alias']}}]
        for state,lookups in [(s,[]) for s in states]+[(marker,[{'result':{**out['result'],'cells':admitted['numbers']}}]),(marker,[history])]:
            task,steering=render_literature_experimental_prompt(state,'Examine the source experiment.',lookup_results=lookups).split('\n\nSTEERING\n')
            assert ION_DISCRIMINATION_TASK in task
            for token in ('11876.54321','51.345678','732.49876','3.456789','artifact_'):assert token not in steering
            if state!=states[0]:assert 'Ec2' in steering and '300 mM' in steering and '7.0' in steering
        parent={**marker,'literature_experimental_work':{'version':'literature_experimental_task_v1','aspect':'reference_evidence_parent'},
            'reference_evidence_parent':{'version':'reference_evidence_parent_v1','source_refs':[args['source_ref']]},'child_reports':[admitted]}
        task,steering=render_literature_experimental_prompt(parent,'Retain the parent job.').split('\n\nSTEERING\n')
        assert ION_DISCRIMINATION_TASK in task and 'Retain the parent job.' in task and 'Ec2' in steering


@pytest.mark.parametrize('profile',[None,CONTRACT_INFORMATION_PROFILE])
def test_actual_prompt_and_form_information_keep_internal_sheet_out(profile):
    original=obj({'numbers':ion_discrimination_cells_schema(),'judgment':{'type':'string','enum':['conditional','unresolved']}})
    facts={NAMESPACE:{'type':'array','meaning':'Requested ion components.','report_schema':ion_discrimination_cells_schema()}}
    state={'literature_experimental_work':{'version':'literature_experimental_task_v1'},'literature_assignment':{REQUESTED:REQUEST},
        'requested_form':original,'available_report_facts':facts,'goal':{'result_contract':original}}
    if profile:state['contract_information_profile']=profile
    before=deepcopy(state)
    for parent in (False,True):
        value=deepcopy(state)
        if parent:
            value['literature_experimental_work']['aspect']='reference_evidence_parent'
            value['reference_evidence_parent']={'version':'reference_evidence_parent_v1','source_refs':['source_'+'a'*24]}
        prompt=render_literature_experimental_prompt(value,'Evaluate ion discrimination.')
        task=prompt.split('\n\nSTEERING\n')[0]
        assert ION_DISCRIMINATION_TASK in task and 'conditional' in task and 'unresolved' in task
        assert 'host supplies the saved values' in task
        for internal in ('formula_code','source_meanings','J_R*C*J_R_transpose','withheld_locations'):assert internal not in task
    assert state==before;validate_closed_schema(original)
    lookup=return_contract_information(facts_by_role={'literature':facts},permitted_child_roles=['literature'],role='literature',source=NAMESPACE)
    value={'literature_experimental_work':{'version':'literature_experimental_task_v1'},'contract_information_profile':CONTRACT_INFORMATION_PROFILE}
    task=render_literature_experimental_prompt(value,'Choose the needed numerical return.',lookup_results=[lookup]).split('\n\nSTEERING\n')[0]
    assert ION_DISCRIMINATION_TASK in task and 'episode-fact:'+NAMESPACE in task
    assert 'formula_code' not in task and 'source_meanings' not in task
    submitted=obj({'chosen':{'$ref':'episode-fact:'+NAMESPACE}})
    expanded=expand_fact_form(json.dumps(submitted),child_role='literature',facts_by_role={'literature':facts},permitted_child_roles=['literature'])
    assert expanded['expanded_schema']['properties']['chosen']==ion_discrimination_cells_schema()


def actual_compiled_pair(store,ctx):
    """Actual selected assay -> compiled operations, entirely synthetic data."""
    from gene_annotation_episode.literature_assay_storage import LiteratureAssayRepository
    from gene_annotation_episode.literature_assay_inputs import ASSAY_LITERAL_FIELDS
    from gene_annotation_episode.literature_compiled_assay_storage import LiteratureCompiledAssayRepository
    from gene_annotation_episode.literature_compiled_assay_inputs import LINKS
    rows=[];selections={}
    for role,q in [('preferred','1.8'),('alternative','0.3')]:
        text=('Synthetic E. coli Ec2 construct V2 genotype K12 liposome transport. Fluoride chloride. '
            'All source corrections and normalization are applied in the selected saved native activity. '
            f'Net {q} uM/min; contaminant 0 uM/min; recovery 1 fraction; amount 2 uM; '
            'nuisance test 1 uM/min; nuisance reference 1 uM/min.')
        source=add_source(store,text,'synthetic_transport_'+role)
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,source))
        w=lambda quote:witness(text,quote,source=source)
        assay={**dict.fromkeys(ASSAY_LITERAL_FIELDS),
            'endpoint':{'value':'transport_flux','witnesses':[w('liposome transport')]},
            'arrangement':{'value':'single_preparation','witnesses':[w('liposome')]}}
        for name,quote in [('molecule','Ec2'),('construct','V2'),('organism','E. coli'),('genotype','K12'),('condition','liposome transport')]:assay[name]=w(quote)
        assay['preparation']=w(text)
        primitives={r:measurement(text,quote,token,unit,source=source) for r,quote,token,unit in [
            ('q',f'Net {q} uM/min',q,'uM/min'),('g','contaminant 0 uM/min','0','uM/min'),
            ('k','recovery 1 fraction','1','fraction'),('E','amount 2 uM','2','uM'),
            ('u','nuisance test 1 uM/min','1','uM/min'),('v','nuisance reference 1 uM/min','1','uM/min')]}
        assay_args={'source_ref':source,'source_kind':'synthetic_fixture','assay':assay,'primitives':primitives,
            'covariance_source_ref':None,'distinct_residual_variance':None,'variance_status':'unknown','observation_model':'none','model_witnesses':[]}
        native=LiteratureAssayRepository(store,ctx.run_id).populate(ctx,assay_args,'native-'+role)
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,*native['record_refs']),
            assignment={**plain(ctx.assignment),'requested_compiled_assay_components':['corrected_activity']})
        compiled_args={'source_ref':source,'source_kind':'synthetic_fixture','assay':assay,
            'operands':{r:{'namespace':'literature_assay_cells','sheet_ref':native['result']['sheet_ref'],
                'component':{'q':'corrected_activity','g':'contaminant_rate','k':'recovery','E':'protein_amount','u':'condition_test_rate','v':'condition_reference_rate'}[r]} for r in LINKS},
            'relationships':{r:{'value':'already_normalized_assay_activity' if r=='q' else LINKS[r][0],
                'witnesses':[w('All source corrections and normalization are applied in the selected saved native activity')]} for r in LINKS},
            'correction_stages':{stage:{'value':'already_applied','witnesses':[w('All source corrections and normalization are applied in the selected saved native activity')]}
                for stage in ('background','contaminant','recovery','molecule_amount','nuisance_condition')},
            'covariance_source_ref':None,'distinct_residual_variance':None,'residual_relationship':{'value':'unknown','witnesses':[]},
            'variance_status':'unknown','observation_model':'none','model_witnesses':[]}
        out=LiteratureCompiledAssayRepository(store,ctx.run_id).populate(ctx,compiled_args,'compiled-'+role)
        row,=out['result']['cells'];assert row['value']==(.9 if role=='preferred' else .15)
        rows.append(row);selections[role]={'namespace':'literature_compiled_assay_cells','sheet_ref':row['sheet_ref'],'component':'corrected_activity'}
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,*out['record_refs']))
    return ctx,rows,selections


def test_actual_possessed_compiled_activities_and_explicit_joint_covariance(tmp_path,monkeypatch):
    store,ctx,args=setup(tmp_path,requested=['activity_ratio','activity_ratio_variance','log_activity_ratio_variance'])
    with store:
        ctx,rows,selections=actual_compiled_pair(store,ctx)
        args={**{k:v for k,v in args.items() if k not in ('thresholds','route')},'route':'compiled_activity_pair','activities':selections,
            'activity_covariance_source_ref':None,'variance_status':'unknown','variance_witnesses':[],'adjustment_bindings':[]}
        packet={'version':'a105_ion_activity_covariance_v1','activity_order':['preferred','alternative'],
            'activity_keys':[activity_key(selections[r]) for r in ('preferred','alternative')],
            'activity_units':['per_min','per_min'],'dependency_keys':[dependency_keys(row) for row in rows],
            'matrix':[[.0081,.000675],[.000675,.000225]],'variance_status':'known','origin':'synthetic',
            'basis':'joint_covariance_of_selected_per_unit_activity_estimators'}
        cov=add_source(store,canonical(packet),'synthetic_joint_activity_covariance')
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,cov))
        args.update(activity_covariance_source_ref=cov,variance_status='known',variance_witnesses=[witness(TEXT,'explicitly stipulated synthetic meanings',source=args['source_ref'])])
        repo=LiteratureIonDiscriminationRepository(store,ctx.run_id);out=repo.populate(ctx,args,'selected')
        assert [r['value'] for r in out['result']['cells']]==pytest.approx([6,.36,.01])
        assert all(r['physical_domain'] is None for r in out['result']['cells'])
        for operand in out['result']['cells'][0]['operands']:
            meanings=operand['compiled_meanings']
            assert meanings['assay_meanings']['molecule']=='Ec2'
            assert meanings['assay_meanings']['construct']=='V2' and meanings['assay_meanings']['genotype']=='K12'
            assert meanings['assay_meanings']['preparation'] is None
            assert meanings['literal_display_status']['preparation']=='unrequested_numerical_scope_unresolved'
            assert meanings['literal_location_status']=='not_available_in_possessed_compiled_row'
        display=json.dumps(out['result']['cells'])
        assert '1.8 uM/min' not in display and '0.3 uM/min' not in display and '2 uM' not in display and '1 fraction' not in display
        saved=repo.read(out['result']['sheet_ref']);assert len(saved['input_snapshots'])==2
        assert [r['selection']['component'] for r in saved['input_snapshots']]==['corrected_activity']*2
        # Saved row custody needs no upstream reader or private full sheet.
        from gene_annotation_episode.literature_compiled_assay_storage import LiteratureCompiledAssayRepository
        with monkeypatch.context() as blocked:
            blocked.setattr(LiteratureCompiledAssayRepository,'read',forbid)
            blocked.setattr(LiteratureCompiledAssayRepository,'fact_cells',forbid)
            assert repo.read(out['result']['sheet_ref'])==saved
            assert repo.populate(ctx,args,'selected')==out
        # A distinct episode possessing a sheet reference alone cannot obtain its activity.
        stranger=replace(ctx,episode_id='stranger')
        with pytest.raises(ContractError,match='selected_activity_not_received'):
            repo.populate(stranger,args,'not-authorized')


def test_saved_reconstruction_science_blocked_before_factory_readonly_exact_bytes(tmp_path,monkeypatch):
    store,ctx,args=setup(tmp_path,requested=['preferred_activity','nominal_threshold_ratio'])
    binding=binding_for(store,ctx);out=asyncio.run(binding.execute(ctx,'literature.ion_discrimination.populate',args,'selected'))
    repo=binding._ion_discrimination_repository();ref=out['result']['sheet_ref'];saved=repo.read(ref)
    parent=replace(ctx,episode_id='parent',role='annotation',path=(('annotation','parent'),),assignment={},received_record_refs=(ref,))
    rows=out['result']['cells'][1:];repo.receive_cells(parent,rows,'trusted_fixture_admission')
    descriptors=[binding.as_record()]
    allowed={row[field] for row in store.list('source') if row['origin']=='tool' for field in ('artifact_ref','request_ref')}
    # Ensure legacy optional tables existed in the original real binding, not cold reconstruction.
    binding.received_report_facts(parent)
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close();before=hashes(tmp_path)
    disable_science(monkeypatch)
    with readonly(tmp_path) as cold:
        raw=cold.get_artifact
        def saved_only(ref):assert ref in allowed;return raw(ref)
        monkeypatch.setattr(cold,'get_artifact',saved_only)
        host=SimpleNamespace(store=cold,run_id=ctx.run_id,tools=None);services=WorkflowServices(host)
        restored=compose_episode_bindings(services,store=cold,journal=SimpleNamespace(store=cold,run_id=ctx.run_id),execution_backend=None,
            descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
        current,=restored.bindings;host.episode_bindings=EpisodeBindingRegistry(restored.bindings)
        assert current.received_report_facts(parent)[NAMESPACE]==rows
        assert current._ion_discrimination_repository().read(ref)==saved
        assert current._ion_discrimination_repository().populate(ctx,args,'selected')==out
        assert cold.db.total_changes==0
    assert before==hashes(tmp_path)


def test_selected_original_fluc_shared_loop_exact_typed_admission_and_cold_compose(tmp_path,monkeypatch):
    proof=Path(os.environ['ION_DISCRIMINATION_PROOF_DIR']) if os.environ.get('ION_DISCRIMINATION_PROOF_DIR') else tmp_path/'proof'
    proof.mkdir(parents=True,exist_ok=False)
    store,ctx,args=setup(proof/'state',original='efflux_summary_thresholds',requested=['preferred_activity','alternative_activity','nominal_threshold_ratio'])
    request=plain(ctx.assignment);forms=[];prompts=[];controllers=[]
    alias=obj({'numbers':{'$ref':'episode-fact:'+NAMESPACE}})
    child={'selection':{'kind':'episode_child','role':'literature','assignment':request,
        'goal':'Examine original Fluc fluoride/chloride thresholds, actual source subject, construct ownership, derivation, experimental controls and applicability. Preserve reported estimates separately from nominal arithmetic and physical parameter bounds.',
        'scope':plain(ctx.scope),'purpose':'Return exactly the requested original-source native thresholds and nominal threshold comparison, preserving actual ion and construct scope, missing chloride derivation and approximate fluoride inference.',
        'schema_json':json.dumps(alias),'initial_report_json':'{}'},'report_update':{}}
    def select(inputs):
        text=render_literature_experimental_prompt(inputs,'Examine source ion specificity and preserve experimental limitations.')
        assert ION_DISCRIMINATION_TASK in text.split('\n\nSTEERING\n')[0];prompts.append(text)
        return {'selection':{'kind':'tool','tool':'literature.ion_discrimination.populate','arguments':json.dumps(args)},'report_update':{}}
    def integrate(inputs):
        form,=inputs['child_reports'];forms.append(deepcopy(form));rows=form['numbers']
        assert [r['threshold'] for r in rows]==[30000,30,1000]
        assert rows[0]['approximation']=='source_qualified' and rows[1]['derivation']=='unknown'
        assert all(r['physical_domain'] is None for r in rows)
        assert all(r['relationships']['subject_construct']['value']=='unknown' for r in rows)
        assert rows[0]['operands'][0]['source_quantity_meanings']['quantity_scope']['value']=='paper_summary_unresolved'
        assert any(r['source_meanings']['preferred_ion'] is not None for r in rows)
        assert any(r['source_meanings']['alternative_ion'] is not None for r in rows)
        text=render_literature_experimental_prompt(inputs,'Evaluate the returned Fluc experimental evidence.')
        assert ION_DISCRIMINATION_TASK in text.split('\n\nSTEERING\n')[0]
        assert 'paper_summary_unresolved' in text.split('\n\nSTEERING\n')[1]
        prompts.append(text)
        commit={name:[] for name in store.reasoning_schema()['required']}
        original=store.get(args['source_ref']);text=store.get_artifact(original['artifact_ref']).decode()
        w=witness(text,'Fluc',source=args['source_ref'])
        commit['source_subjects']=[{'alias':'original_fluc_source_subject','reference_type':'assay','source_ref':args['source_ref'],
            'label':'Fluc','anchor':{**{name:w[name] for name in ('source_ref','start','end','quote')},'artifact_ref':original['artifact_ref']}}]
        return {'selection':{'kind':'reason','commit':commit},'report_update':{}}
    def controller(path,initial):
        value=FixtureController(str(path),initial,2 if len(path)==1 else 1);controllers.append(value);return value
    from gene_annotation_episode.providers import _SessionConnection
    class ControlledProvider:
        def __init__(self):
            self.connection=_SessionConnection.__new__(_SessionConnection)
            self.connection.scientific_prompt_states={};self.index=0;self.presentations=[]
        async def complete(self,episode_id,role,instructions,context,output_schema):
            rendered=self.connection._presentation(episode_id,role,instructions,context)[0]
            self.presentations.append(rendered)
            state=self.connection.scientific_prompt_states[(episode_id,role)]
            step=self.index;self.index+=1
            if step in (0,2):
                operation='episode.return_contract' if step==0 else 'episode.operation_contract'
                operands={'role':'literature','source':NAMESPACE} if step==0 else {'operation':'literature.ion_discrimination.populate'}
                return {'response':{'response_type':'request_context','lookup':{
                    'view':'composition_information','operation':operation,'arguments':operands}}}
            if step==1:
                assert 'episode-fact:'+NAMESPACE in rendered and 'formula_code' not in rendered
                action=child
            elif step==3:action=select(state)
            elif step==4:action=integrate(state)
            else:raise AssertionError('unexpected extra model exchange')
            return {'response':{'response_type':'select_action',**action}}
        async def release(self,episode_id):pass
    provider=ControlledProvider();scorer=ScientificFindingProgress(FindingProgressPolicy(1))
    summary=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=proof/'run',controller_factory=controller,
        project_credit=scorer,initial_known_record_refs=list(ctx.received_record_refs),
        episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,ion_discrimination_population=True,
            reference_parent_sources=[args['source_ref']],contract_information_profile=CONTRACT_INFORMATION_PROFILE),),
        binding_definitions={'credit':scorer.as_record()},decision_protocol='decision_exchange_v1'))
    assert len(forms)==1 and summary['credit']==0
    assert [c.scores for c in controllers]==[[0,0],[0]]
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==3
    run_id,parent_id=store.db.execute('SELECT run_id,episode_id FROM literature_ion_discrimination_received').fetchone()
    assert store.db.execute('SELECT count(*) FROM literature_ion_discrimination_operations').fetchone()[0]==1
    descriptors=json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',(run_id,)).fetchone()[0])['episode_bindings']
    receiver=replace(ctx,run_id=run_id,episode_id=parent_id,role='annotation',path=(('annotation',parent_id),),assignment={},
        received_record_refs=tuple(LiteratureIonDiscriminationRepository.cell_record_refs(forms[0]['numbers'])))
    ref=forms[0]['numbers'][0]['sheet_ref'];saved=LiteratureIonDiscriminationRepository(store,run_id).read(ref)
    allowed={row[field] for row in store.list('source') if row['origin']=='tool' for field in ('artifact_ref','request_ref')}
    for name,value in [('ORIGINAL_ADMITTED_FORM_001.json',forms[0]),('ORIGINAL_SHEET_001.json',saved),('BINDING_DESCRIPTOR_001.json',descriptors),('CONTROLLED_PROMPTS_001.json',provider.presentations)]:
        (proof/name).write_text(json.dumps(value,indent=2)+'\n')
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close();before=hashes(proof/'state');disable_science(monkeypatch)
    with readonly(proof/'state') as cold:
        raw=cold.get_artifact
        def saved_only(reference):assert reference in allowed;return raw(reference)
        monkeypatch.setattr(cold,'get_artifact',saved_only)
        host=SimpleNamespace(store=cold,run_id=run_id,tools=None);services=WorkflowServices(host)
        restored=compose_episode_bindings(services,store=cold,journal=SimpleNamespace(store=cold,run_id=run_id),execution_backend=None,
            descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
        binding,=restored.bindings;host.episode_bindings=EpisodeBindingRegistry(restored.bindings)
        assert binding.received_report_facts(receiver)[NAMESPACE]==forms[0]['numbers']
        assert binding._ion_discrimination_repository().read(ref)==saved and cold.db.total_changes==0
    assert before==hashes(proof/'state')
    (proof/'PROOF_RESULT_001.json').write_text(json.dumps({'provider':'controlled ScriptedProvider; retained original Fluc bytes',
        'actual_model_science':False,'population_operations':1,'pending_information_lookups':2,'runtime_observations':3,'synthetic_observations':0,
        'full_task_recurred':True,'explicit_contract_information_profile':True,'episode_fact_alias_expanded':True,
        'cold_science_blocked_before_compose_factory':True,'cold_mode':'ro&immutable=1; query_only=ON',
        'cold_writes':0,'exact_admitted_form':True,'exact_original_sheet':True,'database_bytes_unchanged':True,
        'legacy_none_profile_construction_verified':False,'goal_complete':False,'a105_adequacy_claim':False},indent=2)+'\n')


def test_empty_mixed_registered_forms_use_only_their_lazy_routes(tmp_path,monkeypatch):
    from gene_annotation_episode.literature_channel_storage import channel_cells_schema
    store,ctx,args=setup(tmp_path,requested=[])
    with store:
        host=SimpleNamespace(store=store,run_id=ctx.run_id,tools=ToolRegistry(store))
        binding=LiteratureEpisodes(WorkflowServices(host),rate_population=True,channel_population=True,ion_discrimination_population=True,
            controlled_response_population=True,gel_population=True)
        host.episode_bindings=EpisodeBindingRegistry((binding,))
        ctx=replace(ctx,assignment={**plain(ctx.assignment),'requested_channel_components':[]})
        # Neither route discovery nor ion/channel validation may construct
        # an unrelated science adapter, even when other capabilities are enabled.
        for name in ('literature_rate_repository','literature_perturbation_repository','literature_reaction_repository',
                'literature_controlled_response_repository','literature_gel_repository'):
            monkeypatch.setattr(binding.services,name,forbid)
        form=obj({'ions':ion_discrimination_cells_schema(),'electrical':channel_cells_schema()})
        before=store.db.total_changes;store.db.execute('PRAGMA query_only=ON')
        binding.validate_report(ctx,{'ions':[],'electrical':[]},form)
        assert store.db.total_changes==before
        assert not store.db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'literature_%'").fetchall()


def test_empty_admitted_history_cannot_expand_a_private_ion_outcome(tmp_path):
    store,ctx,args=setup(tmp_path,requested=['preferred_activity','nominal_threshold_ratio'])
    with store:
        out=LiteratureIonDiscriminationRepository(store,ctx.run_id).populate(ctx,args,'selected')
        history={'result':{'view':'records','records':[{'outcome':out,'admitted_report':{'numbers':[]}}]}}
        state={'literature_experimental_work':{'version':'literature_experimental_task_v1'}}
        steering=render_literature_experimental_prompt(state,'Evaluate only admitted information.',lookup_results=[history]).split('\n\nSTEERING\n')[1]
        assert '11876.54321' not in steering and 'nominal_threshold_ratio' not in steering


def test_reversed_model_object_order_has_identical_saved_activity_role_binding(tmp_path):
    store,ctx,args=setup(tmp_path,requested=['activity_ratio'])
    with store:
        ctx,rows,selections=actual_compiled_pair(store,ctx)
        args={**{k:v for k,v in args.items() if k not in ('thresholds','route')},'route':'compiled_activity_pair',
            'activities':{'alternative':selections['alternative'],'preferred':selections['preferred']},
            'activity_covariance_source_ref':None,'variance_status':'unknown','variance_witnesses':[],'adjustment_bindings':[]}
        repo=LiteratureIonDiscriminationRepository(store,ctx.run_id);out=repo.populate(ctx,args,'reversed')
        saved=repo.read(out['result']['sheet_ref'])
        assert out['result']['cells'][0]['value']==6
        assert [s['selection'] for s in saved['input_snapshots']]==[selections['preferred'],selections['alternative']]
