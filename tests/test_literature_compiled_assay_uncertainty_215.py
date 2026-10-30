"""Synthetic engineering repair of the same compiler; no paper/model adequacy claim."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from functools import partial
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain, validate_closed_schema
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_compiled_assay_inputs import POPULATION_V2, ROLES, compiled_assay_population_schema
from gene_annotation_episode.literature_compiled_assay_calculations import COMPONENTS_V2
from gene_annotation_episode.literature_compiled_assay_storage import (
    LiteratureCompiledAssayRepository, VERSION_V2, NAMESPACE, NAMESPACE_V2, REQUESTED, REQUESTED_V2,
    compiled_assay_cells_schema, compiled_assay_v2_cells_schema)
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_compiled_assay_prompt import COMPILED_ASSAY_TASK
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode import literature_numerical_contracts as contracts
from gene_annotation_episode.episode_contract_information import validate_saved_fact_form
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_compiled_assay_185 import setup, extraction, add_source, populate, readonly, forbid, CONTEXT_TEXT, with_covariance
from test_literature_compiled_assay_binding_185 import binding_for, disable_science, hashes
from test_literature_assay_inputs import witness
from test_runtime import FixtureController, ScriptedProvider

PART = 'measured_endpoint_per_selected_amount'
CAL = 'calibrated_measured_endpoint_per_selected_amount'
VAR = PART + '_propagated_variance'
SE = PART + '_propagated_standard_uncertainty'
FULL = 'corrected_activity_propagated_variance'


def v2(ctx, args, *, requested=(PART, VAR, SE), roles=('q', 'E')):
    args = deepcopy(args)
    args.pop('covariance_source_ref')
    args.update(population_version=POPULATION_V2, covariance_source_refs=[])
    for role in ROLES:
        if role not in roles:
            args['operands'][role] = None
            args['relationships'][role] = {'value': 'unknown', 'witnesses': []}
    for stage, needed in [('contaminant', ('g',)), ('recovery', ('k',)), ('nuisance_condition', ('u', 'v'))]:
        if not set(needed) <= set(roles):
            args['correction_stages'][stage] = {'value': 'unknown', 'witnesses': []}
    return replace(ctx, assignment={**plain(ctx.assignment), REQUESTED_V2: list(requested)}), args


def block(store, ctx, args, *, order=('q', 'E'), matrix=((.04, .005), (.005, .01)), status='estimated', change=None):
    bare = deepcopy(args); bare['covariance_source_refs'] = []
    ex = extraction(store, ctx, bare)
    operands = ex['operands']
    data = {'version': 'a105_compiled_assay_covariance_v2', 'primitive_order': list(order),
        'operand_keys': [operands[r]['quantity_key'] for r in order],
        'primitive_units': [operands[r]['unit'] for r in order],
        'dependency_keys': [list(dict.fromkeys((*operands[r]['canonical_physical_keys'], *operands[r]['recorded_dependency_keys']))) for r in order],
        'covariance': None if matrix is None else [list(row) for row in matrix], 'variance_status': status,
        'origin': 'synthetic', 'basis': 'joint_covariance_of_canonical_compilation_operands'}
    if change:
        change(data)
    ref = add_source(store, canonical(data), 'synthetic215covariance', [args['source_ref']])
    args = deepcopy(args); args['covariance_source_refs'].append(ref)
    return replace(ctx, received_record_refs=(*ctx.received_record_refs, ref)), args, data


def selected(store, ctx, args, key='selected215'):
    binding = binding_for(store, ctx)
    outcome = asyncio.run(binding.execute(ctx, 'literature.assay.components.populate', args, key))
    assert outcome['status'] == 'completed', outcome
    current = replace(ctx, received_record_refs=(*ctx.received_record_refs, *outcome['record_refs']))
    form = obj({'numbers': compiled_assay_v2_cells_schema()})
    rows = form_with_facts({}, form, binding.facts(current, {'committed_record_refs': outcome['record_refs']}))
    binding.validate_report(current, rows, form)
    repo = LiteratureCompiledAssayRepository(store, ctx.run_id).v2_projection()
    return binding, current, repo, outcome, repo.read(outcome['result']['sheet_ref']), rows['numbers']


@pytest.mark.parametrize('cross', [.005, -.005])
def test_actual_selected_owned_two_operand_uncertainty_and_signed_covariance(tmp_path, cross):
    store, ctx, args, _ = setup(tmp_path)
    with store:
        ctx, args = v2(ctx, args)
        ctx, args, _ = block(store, ctx, args, matrix=((.04, cross), (cross, .01)))
        binding, current, repo, outcome, saved, rows = selected(store, ctx, args)
        q, e = (saved['extraction']['operands'][r]['value'] for r in ('q', 'E'))
        expected = .04/e**2 + q*q*.01/e**4 - 2*q*cross/e**3
        assert [r['component'] for r in rows] == [PART, VAR, SE]
        assert rows[1]['value'] == pytest.approx(expected)
        assert rows[2]['value'] == pytest.approx(expected**.5)
        assert rows[1]['uncertainty']['variance_status'] == 'estimated'
        assert rows[1]['variance_status'] == 'unknown'  # legacy full-model declaration stays separate
        assert rows[1]['uncertainty']['covariance_origin'] == 'synthetic'
        assert rows[1]['uncertainty']['operand_order'] == ['q', 'E']
        assert saved['sheet']['cells']['corrected_activity']['value'] is None
        assert all(saved['extraction']['operands'][r] is None for r in ('g','k','u','v'))
        assert not store.list('observation') and not store.list('assessment')
        assert repo.populate(ctx, args, 'selected215') == outcome
        with pytest.raises(ContractError, match='sheet_required'):
            LiteratureCompiledAssayRepository(store, ctx.run_id).read(outcome['result']['sheet_ref'])
        parent = replace(ctx, episode_id='parent215', role='annotation', path=(('annotation','parent215'),),
            assignment={}, received_record_refs=tuple(binding.received_form_references(current, {'numbers': rows}, obj({'numbers': compiled_assay_v2_cells_schema()}), 'trusted215')))
        chosen = [rows[1]]
        repo.receive_cells(parent, chosen, 'trusted-subset215')
        assert repo.fact_cells(parent, [rows[0]['sheet_ref']], components=COMPONENTS_V2) == chosen
        assert 'covariance' not in chosen[0] and chosen[0]['native_quantity'] is None
        assert not any('value' in d or 'row' in d for d in chosen[0]['dependencies'])
        text = render_literature_experimental_prompt({'literature_experimental_work': {'version':'literature_experimental_task_v1'},
            'literature_assignment': {REQUESTED_V2:[VAR]}, 'child_reports':[{'numbers':chosen}]}, 'Examine synthetic uncertainty.')
        task, steering = text.split('\n\nSTEERING\n')
        assert COMPILED_ASSAY_TASK in task and 'signed covariance' in task
        assert 'operand_propagated' in steering and 'estimated' in steering
        assert args['covariance_source_refs'][0] not in steering and 'selected_source_component_' not in steering


def test_calibrated_uncertainty_uses_named_joint_block_not_two_marginals(tmp_path):
    store, ctx, args, _ = setup(tmp_path)
    with store:
        ctx, args = v2(ctx, args, requested=(CAL, CAL+'_propagated_variance'), roles=('q','k','E'))
        # Source order differs from formula order. Positive and negative cross terms survive.
        order = ('E','q','k'); matrix = [[.01,.005,.0002],[.005,.04,-.0005],[.0002,-.0005,.0001]]
        ctx, args, _ = block(store, ctx, args, order=order, matrix=matrix)
        _, _, _, _, saved, rows = selected(store, ctx, args)
        val = {r: Fraction(str(saved['extraction']['operands'][r]['value'])) for r in order}
        q,k,e = val['q'],val['k'],val['E']; j={'q':1/(k*e),'k':-q/(k*k*e),'E':-q/(k*e*e)}
        expected = sum(j[a]*Fraction(str(matrix[i][l]))*j[b] for i,a in enumerate(order) for l,b in enumerate(order))
        assert rows[1]['value'] == pytest.approx(float(expected))
        assert rows[1]['uncertainty']['source_primitive_order'] == list(order)
        args['covariance_source_refs'] = []
        ctx, args, _ = block(store, ctx, args, order=('q','E'))
        ctx, args, _ = block(store, ctx, args, order=('k',), matrix=[[.0001]])
        _, _, _, _, _, rows = selected(store, ctx, args, 'marginals215')
        assert rows[0]['value'] is not None
        assert rows[1]['unavailable_reason'] == 'component_joint_covariance_not_supplied'


@pytest.mark.parametrize('status,matrix,reason', [('unknown',None,'component_covariance_status_unknown'),
    ('unknown',[[.04,.005],[.005,.01]],'component_covariance_status_unknown'),
    (None,None,'component_covariance_unreported')])
def test_missing_and_valid_unknown_covariance_preserve_point(tmp_path,status,matrix,reason):
    store,ctx,args,_=setup(tmp_path)
    with store:
        ctx,args=v2(ctx,args)
        if status:
            ctx,args,_=block(store,ctx,args,status=status,matrix=matrix)
        *_,rows=selected(store,ctx,args)
        assert rows[0]['value']==pytest.approx(.9) and rows[1]['value'] is None
        assert rows[1]['unavailable_reason']==reason


@pytest.mark.parametrize('change,code', [
    (lambda d:d['operand_keys'].__setitem__(0,'wrong_owner'),'compiled_covariance_owner_mismatch'),
    (lambda d:d['primitive_units'].__setitem__(0,'per_min'),'compiled_covariance_unit_mismatch'),
    (lambda d:d['dependency_keys'].__setitem__(0,[]),'compiled_covariance_dependency_mismatch'),
    (lambda d:d.__setitem__('covariance',[[.04,.01],[.005,.01]]),'symmetric_covariance_required'),
    (lambda d:d.__setitem__('covariance',[[.04,.1],[.1,.01]]),'positive_semidefinite_covariance_required'),
    (lambda d:d.__setitem__('covariance',[[True,0],[0,.01]]),'finite_number_required'),
    (lambda d:d.__setitem__('covariance',[[1]]),'named_subset_covariance_shape_mismatch'),
    (lambda d:d.__setitem__('variance_status','vibe'),'unsupported_variance_status')])
def test_invalid_covariance_fails_actual_selected_operation(tmp_path,change,code):
    store,ctx,args,_=setup(tmp_path)
    with store:
        ctx,args=v2(ctx,args);ctx,args,_=block(store,ctx,args,change=change)
        result=asyncio.run(binding_for(store,ctx).execute(ctx,'literature.assay.components.populate',args,'bad215'))
        assert result['status']=='invalid' and code in result['feedback']['code']
        assert not store.list('assessment') and not store.list('observation')


@pytest.mark.parametrize('mutation,code', [('entry','overlapping_covariance_entry_mismatch'),
    ('status','overlapping_covariance_status_ambiguity'),('agree',None)])
def test_overlapping_blocks_require_exact_consistent_entries_and_status(tmp_path,mutation,code):
    store,ctx,args,_=setup(tmp_path)
    with store:
        ctx,args=v2(ctx,args,roles=('q','k','E'))
        ctx,args,_=block(store,ctx,args)
        matrix=[[.01,.005,0],[.005,.04,0],[0,0,.0001]]
        if mutation=='entry':matrix[0][0]=.02
        ctx,args,_=block(store,ctx,args,order=('E','q','k'),matrix=matrix,status='known' if mutation=='status' else 'estimated')
        result=asyncio.run(binding_for(store,ctx).execute(ctx,'literature.assay.components.populate',args,'overlap215'))
        if code:assert result['status']=='invalid' and code in result['feedback']['code']
        else:
            assert result['status']=='completed'
            assert result['result']['cells'][1]['value']==pytest.approx(.009775)
            assert result['result']['cells'][1]['uncertainty']['covariance_source_ref']==args['covariance_source_refs'][0]


def test_full_propagated_variance_available_without_distinct_residual(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        ctx,args=v2(ctx,args,requested=(FULL,'effect_variance','source_profile_log_ratio'),roles=ROLES)
        diagonal=[.04,.0025,.0001,.01,.0025,.0025]
        matrix=[[diagonal[i] if i==j else 0 for j in range(6)] for i in range(6)]
        ctx,args,_=block(store,ctx,args,order=ROLES,matrix=matrix,status='known')
        args['variance_status']='known';args['model_witnesses']=[witness(CONTEXT_TEXT,'A jointly known covariance and known normal source model',source=args['source_ref'])]
        _,_,_,_,_,rows=selected(store,ctx,args)
        assert rows[0]['value']>0
        assert rows[0]['uncertainty']['scope']=='operand_propagated'
        assert rows[1]['value'] is None and rows[1]['unavailable_reason']=='distinct_residual_variance_not_supplied'
        assert rows[1]['uncertainty']['scope']=='total_with_distinct_residual'
        assert rows[2]['value'] is None


def test_same_physical_quantity_requires_identical_covariance_rows(tmp_path):
    from gene_annotation_episode.literature_assay_storage import LiteratureAssayRepository
    store,ctx,args,outputs=setup(tmp_path)
    with store:
        ordinary=deepcopy(outputs['assay']['arguments']);ordinary['primitives']['g']=deepcopy(ordinary['primitives']['q'])
        out=LiteratureAssayRepository(store,ctx.run_id).populate(ctx,ordinary,'reused215')
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,*out['record_refs']))
        for role,component in [('q','net_rate'),('g','contaminant_rate')]:
            args['operands'][role]={'namespace':'literature_assay_cells','sheet_ref':out['result']['sheet_ref'],'component':component}
        ctx,args=v2(ctx,args,roles=('q','g','E'))
        ctx,args,_=block(store,ctx,args,order=('q','g','E'),matrix=[[.04,0,0],[0,.04,0],[0,0,.01]])
        outcome=asyncio.run(binding_for(store,ctx).execute(ctx,'literature.assay.components.populate',args,'reusedbad215'))
        assert 'shared_measurement_covariance_mismatch' in outcome['feedback']['code']
        args['covariance_source_refs']=[]
        ctx,args,_=block(store,ctx,args,order=('q','g','E'),matrix=[[.04,.04,.005],[.04,.04,.005],[.005,.005,.01]])
        *_,rows=selected(store,ctx,args)
        assert rows[1]['value']==pytest.approx(.009775)


def test_v1_defaults_and_original_record_do_not_promote_to_v2(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        repo,outcome,saved=populate(store,ctx,args)
        before=canonical(saved);cells=deepcopy(outcome['result']['cells'])
        ctx,args=v2(ctx,args);ctx,args,_=block(store,ctx,args)
        selected(store,ctx,args)
        assert canonical(repo.read(outcome['result']['sheet_ref']))==before
        assert repo.project_cells(outcome['record_refs'],permitted_record_refs=outcome['record_refs'])==cells
        assert all(r['partial_uncertainty_status']=='unimplemented' and 'uncertainty' not in r for r in cells)
        with pytest.raises(ContractError,match='sheet_required'):
            repo.v2_projection().read(outcome['result']['sheet_ref'])
        baseline=Path(__file__).resolve().parents[1]/'verification/literature_reference_evidence_2026-10-25_001/a105_component_uncertainty_repair_215/V1_SCHEMA_BASELINE_001.json'
        expected=json.loads(baseline.read_text())
        assert compiled_assay_population_schema()==expected['population']
        assert compiled_assay_cells_schema()==expected['cells']


def test_exact_mixed_v1_v2_declarations_preserve_original_snapshot_without_factories(monkeypatch):
    binding=LiteratureEpisodes(None,rate_population=True,compiled_assay_population=True)
    facts=binding.fact_sources('literature');action=obj({'fixture':{'type':'boolean'}})
    frozen=contracts.freeze_contracts(facts_by_role={'literature':facts},permitted_child_roles=['literature'],action_schema=action)
    saved={contracts.SAVED_MEMBER:frozen,'schema':action}
    submitted=obj({'old':compiled_assay_cells_schema(),'new':{'$ref':'episode-fact:'+NAMESPACE_V2}})
    expanded=contracts.expand_numerical_form(json.dumps(submitted),child_role='literature',saved=saved)
    expected=obj({'old':compiled_assay_cells_schema(),'new':compiled_assay_v2_cells_schema()})
    assert expanded['expanded_schema']==expected
    monkeypatch.setattr(contracts,'registered_schema',forbid)
    assert contracts.expand_numerical_form(json.dumps(submitted),child_role='literature',saved=saved)==expanded
    assert validate_saved_fact_form(child_role='literature',submitted_schema_json=json.dumps(submitted),expanded_schema=expected,declaration=expanded['declaration'])==expected
    changed=deepcopy(expected);changed['properties']['new']['items']['properties']['component']['enum'].append('invented')
    with pytest.raises(ReportBoundaryError,match='registered source'):
        validate_closed_schema(changed)


def test_mixed_actual_shared_loop_delivery_and_cold_readonly_reconstruction(tmp_path, monkeypatch):
    import os
    proof = Path(os.environ['COMPILED_UNCERTAINTY_PROOF_DIR']) if os.environ.get('COMPILED_UNCERTAINTY_PROOF_DIR') else tmp_path/'proof'
    proof.mkdir(parents=True, exist_ok=False)
    store,seed,args,outputs=setup(proof/'state')
    # The primitive source q and active E have canonical physical-span owners,
    # independent of their future runtime-selected sheet identities. The packet
    # is an explicitly synthetic caller input available before commissioning.
    source_args=deepcopy(args)
    source_args['operands']['q']={'namespace':'literature_assay_cells','sheet_ref':outputs['assay']['outcome']['result']['sheet_ref'],'component':'net_rate'}
    seed,v2args=v2(seed,source_args,requested=(VAR,))
    seed,v2args,_=block(store,seed,v2args)
    raw_refs=[ref for ref in seed.received_record_refs if store.get(ref)['record_type']=='source' and store.get(ref)['origin']=='caller']
    assignment={'version':'literature_assignment_v1','question_context_refs':[],'source_refs':raw_refs,
        REQUESTED:['corrected_activity'],REQUESTED_V2:[VAR],
        'requested_calibration_recovery_components':['recovery'],
        'requested_active_site_components':['active_site_concentration'],'requested_optical_components':['net_rate']}
    literal=obj({'old':compiled_assay_cells_schema(),'new':compiled_assay_v2_cells_schema()})
    submitted=obj({'old':compiled_assay_cells_schema(),'new':{'$ref':'episode-fact:'+NAMESPACE_V2}})
    child={'selection':{'kind':'episode_child','role':'literature','assignment':assignment,
        'goal':'Evaluate source activity and its component-specific uncertainty in the supplied synthetic experiment.',
        'scope':plain(seed.scope),'purpose':'Return corrected activity and partial activity propagated variance with their distinct meanings.',
        'schema_json':json.dumps(submitted),'initial_report_json':'{}'},'report_update':{}}
    selected_refs={};forms=[];controllers=[];prompts=[]
    def work(tool,arguments,previous=None):
        def select(inputs):
            prompt=render_literature_experimental_prompt(inputs,'Examine the supplied experimental measurements.')
            assert COMPILED_ASSAY_TASK in prompt.split('\n\nSTEERING\n')[0]
            prompts.append(prompt)
            if previous:selected_refs[previous]=inputs['last_local_outcome']['result']['sheet_ref']
            return {'selection':{'kind':'tool','tool':tool,'arguments':arguments() if callable(arguments) else arguments},'report_update':{}}
        return select
    def operands(value):
        value=deepcopy(value)
        for role,selector in value['operands'].items():
            if selector:
                family={'literature_assay_cells':'assay','literature_optical_cells':'optical',
                    'literature_calibration_recovery_cells':'recovery','literature_active_site_cells':'active'}[selector['namespace']]
                selector['sheet_ref']=selected_refs[family]
        return value
    def integrate(inputs):
        form,=inputs['child_reports'];forms.append(deepcopy(form))
        assert [row['component'] for row in form['old']]==['corrected_activity']
        assert [row['component'] for row in form['new']]==[VAR]
        assert form['old'][0]['value']==pytest.approx(.9070294784580499)
        assert form['new'][0]['value']==pytest.approx(.009775)
        prompt=render_literature_experimental_prompt(inputs,'Evaluate the returned experimental evidence.')
        assert COMPILED_ASSAY_TASK in prompt.split('\n\nSTEERING\n')[0]
        commit={name:[] for name in store.reasoning_schema()['required']}
        source=store.get(args['source_ref']);w=witness(CONTEXT_TEXT,'enzyme P',source=args['source_ref'])
        commit['source_subjects']=[{'alias':'synthetic215_enzyme','reference_type':'assay','source_ref':args['source_ref'],'label':'enzyme P',
            'anchor':{'source_ref':args['source_ref'],'artifact_ref':source['artifact_ref'],'start':w['start'],'end':w['end'],'quote':'enzyme P'}}]
        return {'selection':{'kind':'reason','commit':commit},'report_update':{}}
    def controller(path,initial):
        value=FixtureController(str(path),initial,2 if len(path)==1 else 6);controllers.append(value);return value
    provider=ScriptedProvider([child,
        work('literature.assay.populate',outputs['assay']['arguments']),
        work('literature.optical.populate',outputs['optical']['arguments'],'assay'),
        work('literature.calibration.recovery.populate',outputs['recovery']['arguments'],'optical'),
        work('literature.active_site.populate',outputs['active']['arguments'],'recovery'),
        work('literature.assay.components.populate',lambda:operands(args),'active'),
        work('literature.assay.components.populate',lambda:operands(v2args)),integrate])
    scorer=ScientificFindingProgress(FindingProgressPolicy(1))
    summary=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=proof/'run',controller_factory=controller,
        project_credit=scorer,initial_known_record_refs=raw_refs,
        episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,active_site_population=True,compiled_assay_population=True,
            reference_parent_sources=[args['source_ref']]),),binding_definitions={'credit':scorer.as_record()}))
    assert len(forms)==1 and summary['credit']==0
    assert [c.scores for c in controllers]==[[0,0],[0,0,0,0,0,0]]
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==8
    assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]==8
    run_id,parent_id=store.db.execute('SELECT run_id,episode_id FROM literature_compiled_assay_v2_received').fetchone()
    assert store.db.execute('SELECT count(*) FROM literature_compiled_assay_operations WHERE run_id=?',(run_id,)).fetchone()[0]==2
    descriptors=json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',(run_id,)).fetchone()[0])['episode_bindings']
    request=json.loads(store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND json_array_length(path)=2',(run_id,)).fetchone()[0])
    assert request['report_contract']['measurements']['schema']==literal
    declaration=request['message']['report_contract_declaration']
    assert validate_saved_fact_form(child_role='literature',submitted_schema_json=json.dumps(submitted),expanded_schema=literal,declaration=declaration)==literal
    refs=list(dict.fromkeys(ref for rows in forms[0].values() for ref in LiteratureCompiledAssayRepository.cell_record_refs(rows)))
    receiver=replace(seed,run_id=run_id,episode_id=parent_id,role='annotation',path=(('annotation',parent_id),),assignment={},received_record_refs=refs)
    repositories=[LiteratureCompiledAssayRepository(store,run_id),LiteratureCompiledAssayRepository(store,run_id,2)]
    saved=[repo.read(forms[0][field][0]['sheet_ref']) for repo,field in zip(repositories,('old','new'))]
    allowed={store.get(forms[0][field][0]['sheet_ref'])[name] for field in ('old','new') for name in ('artifact_ref','request_ref')}
    for name,value in [('ORIGINAL_MIXED_FORM_001.json',forms[0]),('ORIGINAL_CHILD_REQUEST_001.json',request),('SAVED_SHEETS_001.json',saved),('TASKS_001.json',prompts)]:
        (proof/name).write_text(json.dumps(value,indent=2)+'\n')
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close();before=hashes(proof/'state')
    disable_science(monkeypatch)
    monkeypatch.setattr('gene_annotation_episode.literature_compiled_assay_inputs._covariance_v2',forbid)
    monkeypatch.setattr('gene_annotation_episode.literature_compiled_assay_calculations._populate_v2',forbid)
    monkeypatch.setattr(LiteratureCompiledAssayRepository,'receive_cells',forbid)
    with readonly(proof/'state') as cold:
        raw=cold.get_artifact
        def committed_only(reference):
            assert reference in allowed,'cold reconstruction cannot read original or upstream scientific bytes'
            return raw(reference)
        monkeypatch.setattr(cold,'get_artifact',committed_only)
        host=SimpleNamespace(store=cold,run_id=run_id,tools=None);services=WorkflowServices(host)
        restored=compose_episode_bindings(services,store=cold,journal=SimpleNamespace(store=cold,run_id=run_id),execution_backend=None,
            descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
        binding,=restored.bindings;host.episode_bindings=EpisodeBindingRegistry(restored.bindings)
        actual=binding.received_report_facts(receiver)
        assert actual[NAMESPACE]==forms[0]['old'] and actual[NAMESPACE_V2]==forms[0]['new']
        assert binding._compiled_assay_repository().read(forms[0]['old'][0]['sheet_ref'])==saved[0]
        assert binding._compiled_assay_v2_repository().read(forms[0]['new'][0]['sheet_ref'])==saved[1]
        assert cold.db.total_changes==0
        assert cold.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==8
    assert hashes(proof/'state')==before
    (proof/'PROOF_RESULT_001.json').write_text(json.dumps({'scope':'synthetic engineering; no paper or actual model',
        'mixed_original_typed_admission':True,'v1_to_v2_promotion':False,'source_operations':4,'compiler_operations':2,
        'ordinary_runtime_actions':8,'ordinary_runtime_observations':8,'synthetic_observations_added':0,
        'cold_database_writes':0,'cold_original_sources_upstream_science_and_receive_blocked':True,
        'unchanged_state_hashes':True,'a105_adequacy_claim':False},indent=2)+'\n')


def test_bypassed_correction_has_no_measurement_owner_and_does_not_block_q_over_e(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        ctx,args=v2(ctx,args,requested=(VAR,CAL+'_propagated_variance'))
        args['correction_stages']['recovery']={'value':'already_applied','witnesses':[
            witness(CONTEXT_TEXT,'Already calibrated and contaminant corrected, active amount normalized and nuisance corrected native result',source=args['source_ref'])]}
        ctx,args,_=block(store,ctx,args)
        _,_,_,_,saved,rows=selected(store,ctx,args)
        assert rows[0]['value']==pytest.approx(.009775)
        assert rows[1]['value'] is None
        assert rows[1]['unavailable_reason']=='covariance_for_bypassed_correction_stages_unimplemented'
        k,= [d for d in rows[1]['dependencies'] if d['role']=='k']
        assert k['quantity_key'] is None and k['selection'] is None
        assert saved['extraction']['operands']['k'] is None


def test_covariance_does_not_authorize_an_ineligible_or_unreceived_operand(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        ctx,args=v2(ctx,args);ctx,args,_=block(store,ctx,args)
        bad=deepcopy(args);bad['relationships']['E']={'value':'unknown','witnesses':[]}
        binding=binding_for(store,ctx)
        result=asyncio.run(binding.execute(ctx,'literature.assay.components.populate',bad,'ineligible215'))
        assert 'eligible_covariance_owners_required' in result['feedback']['code']
        missing=replace(ctx,received_record_refs=tuple(ref for ref in ctx.received_record_refs if ref!=args['operands']['q']['sheet_ref']))
        result=asyncio.run(binding.execute(missing,'literature.assay.components.populate',args,'unreceived215'))
        assert 'not_received' in result['feedback']['code']


def test_larger_joint_block_supplies_marginal_and_v2_total_preserves_v1_formula(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        original_ctx,original_args,_=with_covariance(store,ctx,args)
        _,_,old=populate(store,original_ctx,original_args)
        ctx,args=v2(original_ctx,original_args,requested=(VAR,FULL,'effect_variance','source_profile_log_ratio'),roles=ROLES)
        diagonal=[.04,.0025,.0001,.01,.0025,.0025]
        matrix=[[diagonal[i] if i==j else 0 for j in range(6)] for i in range(6)]
        # This is the actually owned six-dimensional joint source, not padding.
        ctx,args,_=block(store,ctx,args,order=tuple(reversed(ROLES)),matrix=[list(reversed(row)) for row in reversed(matrix)],status='known')
        _,_,_,_,new,rows=selected(store,ctx,args)
        assert rows[0]['value']==pytest.approx(.012025)
        assert rows[2]['value']==old['sheet']['cells']['effect_variance']['value']
        assert rows[3]['value']==old['sheet']['cells']['source_profile_log_ratio']['value']
        assert rows[2]['value']==pytest.approx(rows[1]['value']+.001)
        assert new['sheet']['cells'][PART]['value']==old['sheet']['cells'][PART]['value']


@pytest.mark.parametrize('asymmetric', [True, False], ids=['exact_asymmetry_rejected', 'large_exact_symmetry_preserved'])
def test_selected_large_integer_covariance_symmetry_before_float_projection(tmp_path, asymmetric):
    store, ctx, args, _ = setup(tmp_path)
    with store:
        ctx, args = v2(ctx, args, requested=(VAR,))
        matrix = [[10**18, 10**17], [10**17 + int(asymmetric), 10**18]]
        # The exact off-diagonal difference in the failing case is lost by a
        # float cast. This is a synthetic validator regression, not paper data.
        assert float(matrix[0][1]) == float(matrix[1][0])
        ctx, args, _ = block(store, ctx, args, matrix=matrix)
        binding = binding_for(store, ctx)
        outcome = asyncio.run(binding.execute(ctx, 'literature.assay.components.populate', args, 'exact-symmetry215'))
        if asymmetric:
            assert matrix[0][1] != matrix[1][0]
            assert outcome['status'] == 'invalid'
            assert outcome['feedback']['code'] == 'symmetric_covariance_required:covariance'
            assert outcome['record_refs'] == [] and outcome['changed_record_refs'] == []
        else:
            assert outcome['status'] == 'completed', outcome
            current = replace(ctx, received_record_refs=(*ctx.received_record_refs, *outcome['record_refs']))
            schema = obj({'numbers': compiled_assay_v2_cells_schema()})
            form = form_with_facts({}, schema, binding.facts(current, {'committed_record_refs': outcome['record_refs']}))
            binding.validate_report(current, form, schema)
            saved = LiteratureCompiledAssayRepository(store, ctx.run_id, 2).read(outcome['result']['sheet_ref'])
            assert saved['extraction']['covariance_sources'][0]['data']['covariance'] == matrix
            q, e = (Fraction(str(saved['extraction']['operands'][r]['value'])) for r in ('q', 'E'))
            gradient = (1/e, -q/e**2)
            expected = sum(gradient[i] * matrix[i][j] * gradient[j] for i in range(2) for j in range(2))
            assert form['numbers'][0]['value'] == float(expected)
            assert form['numbers'][0]['uncertainty']['covariance_origin'] == 'synthetic'
        assert not store.list('observation') and not store.list('assessment')
