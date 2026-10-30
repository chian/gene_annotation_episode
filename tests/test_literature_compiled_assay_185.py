"""Synthetic source-component joins; no original paper or model science."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_assay_storage import LiteratureAssayRepository
from gene_annotation_episode.literature_assay_inputs import ASSAY_LITERAL_FIELDS, PRIMITIVE_ORDER
from gene_annotation_episode.literature_optical_storage import LiteratureOpticalRepository
from gene_annotation_episode.literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
from gene_annotation_episode.literature_active_site_storage import LiteratureActiveSiteRepository
from gene_annotation_episode.literature_compiled_assay_storage import (
    LiteratureCompiledAssayRepository, compiled_assay_cells_schema, COMPONENTS, REQUESTED,
)
from gene_annotation_episode.literature_compiled_assay_inputs import (
    NS_ASSAY, NS_OPTICAL, NS_RECOVERY, NS_ACTIVE, LINKS, ROLES,
    read_compiled_assay_inputs,
)
from gene_annotation_episode.literature_compiled_assay_calculations import populate_compiled_assay
from test_literature_assay_inputs import witness, measurement
from test_literature_optical_inputs import fixture as optical_fixture, TEXT as OPTICAL_TEXT, SOURCE as OPTICAL_SOURCE
from test_literature_calibration_recovery_169 import Source as RecoverySource
from test_literature_active_site_inputs import fixture as active_fixture, TEXT as ACTIVE_TEXT, SOURCE as ACTIVE_SOURCE


CONTEXT_TEXT = ('Synthetic enzyme P from organism O, construct C, preparation A, condition buffer. '
    'Oxygen consumption and NADH depletion are the measured endpoints. Growth phenotype is a different endpoint. '
    'A single preparation; deliberately tested substrate. '
    'The same molecule, construct, preparation and assay are linked to all selected controls. '
    'Net background subtraction already applied; contaminant correction not applied; reporter recovery not applied; '
    'molecule amount normalization not applied; nuisance correction not applied. '
    'The contaminant is additional; reporter standard uses the same matrix and endpoint; '
    'active sites represent one site per active molecule; nuisance controls exclude the intended change. '
    'A jointly known covariance and known normal source model are stipulated only for synthetic uncertainty tests. '
    'Additional distinct residual variance 0.001 per_min_squared. '
    'Already calibrated and contaminant corrected, active amount normalized and nuisance corrected native result.')
CONTROL_TEXT = ('Synthetic molecule P, organism O, genotype G, construct C, preparation A, condition buffer. '
    'Oxygen consumption from a single preparation, deliberately tested substrate. '
    'net 1.8 uM/min; contaminant 0.2 uM/min; recovery 0.98 fraction; amount 2 uM; '
    'nuisance test 0.9 uM/min; nuisance reference 1 uM/min.')


def remap(value, before, after):
    if isinstance(value, dict):
        return {key: remap(child, before, after) for key, child in value.items()}
    if isinstance(value, list):
        return [remap(child, before, after) for child in value]
    return after if value == before else value


def add_source(store, text, name, parents=()):
    artifact = store.artifact(text, 'text/plain')
    return store.put('source', {'provider': name, 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None,
        'retrieved_at': None, **({'parent_source_refs': list(parents)} if parents else {})}, origin='caller')['id']


def setup(path, *, control_kind='reporter_standard'):
    store = Store(path); store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    context_ref = add_source(store, CONTEXT_TEXT, 'compiled_synthetic_context')
    control_ref = add_source(store, CONTROL_TEXT, 'compiled_synthetic_controls', [context_ref])
    w = lambda quote: witness(CONTROL_TEXT, quote, source=control_ref)
    ordinary = {'source_ref': control_ref, 'source_kind': 'synthetic_fixture',
        'assay': {**dict.fromkeys(ASSAY_LITERAL_FIELDS),
            'endpoint': {'value': 'oxygen_consumption', 'witnesses': [w('Oxygen consumption')]},
            'arrangement': {'value': 'single_preparation', 'witnesses': [w('single preparation')]}},
        'primitives': {}, 'covariance_source_ref': None, 'distinct_residual_variance': None,
        'variance_status': 'unknown', 'observation_model': 'none', 'model_witnesses': []}
    for name, quote in [('molecule','molecule P'),('organism','organism O'),('construct','construct C'),
                        ('preparation','preparation A'),('condition','condition buffer')]:
        ordinary['assay'][name] = w(quote)
    for role, quote, token, unit in [('q','net 1.8 uM/min','1.8','uM/min'),
        ('g','contaminant 0.2 uM/min','0.2','uM/min'), ('k','recovery 0.98 fraction','0.98','fraction'),
        ('E','amount 2 uM','2','uM'), ('u','nuisance test 0.9 uM/min','0.9','uM/min'),
        ('v','nuisance reference 1 uM/min','1','uM/min')]:
        ordinary['primitives'][role] = measurement(CONTROL_TEXT, quote, token, unit, source=control_ref)
    ot = OPTICAL_TEXT.replace('-0.012', '-0.011')
    optical_ref = add_source(store, ot, 'compiled_synthetic_optical', [context_ref])
    optical = optical_fixture(ot, sample=('-0.011 AU/min','-0.011','AU/min'))[0]
    optical = remap(optical, OPTICAL_SOURCE, optical_ref)
    recovery_unit = 'nmol/min' if control_kind == 'enzyme_activity_spike' else 'nmol'
    recovery_source = RecoverySource(unit=recovery_unit)
    recovery_ref = add_source(store, recovery_source.text, 'compiled_synthetic_recovery', [context_ref])
    recovery = remap(recovery_source.args(unit=recovery_unit), recovery_source.reference, recovery_ref)
    recovery['applicability'] = {'value':'same_matrix_same_endpoint_supported','witnesses':[witness(CONTEXT_TEXT,'reporter standard uses the same matrix and endpoint',source=context_ref)]}
    if control_kind != 'reporter_standard':
        recovery['control_kind'] = remap(recovery_source.interpretation(control_kind, 'enzyme activity spike'), recovery_source.reference, recovery_ref)
    at = ACTIVE_TEXT.replace('Mass 4 ng/uL','Mass 400 ng/uL').replace('60 ± 3 nM','2000 ± 3 nM').replace('fraction 60%', 'fraction 20%').replace('Rate already active normalized', 'Rate uses total monomer concentration')
    active_ref = add_source(store, at, 'compiled_synthetic_active', [context_ref])
    active = active_fixture(at, mass=('400 ng/uL','400','ng/uL'), active=('2000 ± 3 nM','2000','nM'), reported=('20%','20','%'))[0]
    active = remap(active, ACTIVE_SOURCE, active_ref)
    active['interpretations']['normalization_stage'] = {'value': 'total_monomer', 'witnesses': [witness(at, 'Rate uses total monomer concentration', source=active_ref)]}
    refs = [context_ref, control_ref, optical_ref, recovery_ref, active_ref]
    context = BindingContext('compiled-run','compiled-child','literature',(('literature','case'),),
        store.validate_scope(), {'version':'literature_assignment_v1','question_context_refs':[], 'source_refs':refs,
            REQUESTED:list(COMPONENTS), 'requested_calibration_recovery_components':['recovery'],
            'requested_optical_components':['net_rate'], 'requested_active_site_components':['active_site_concentration']}, {}, refs)
    outputs = {}
    for name, cls, arguments in [('assay', LiteratureAssayRepository, ordinary), ('optical', LiteratureOpticalRepository, optical),
                                ('recovery', LiteratureCalibrationRecoveryRepository, recovery), ('active', LiteratureActiveSiteRepository, active)]:
        repo = cls(store, context.run_id); result = repo.populate(context, arguments, 'original-' + name)
        outputs[name] = {'repo':repo,'outcome':result,'arguments':arguments}
        context = replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs,*result['record_refs']))))
    cw = lambda quote: witness(CONTEXT_TEXT, quote, source=context_ref)
    arguments = {'source_ref':context_ref, 'source_kind':'synthetic_fixture',
        'assay':{**dict.fromkeys(ASSAY_LITERAL_FIELDS),
            'endpoint':{'value':'oxygen_consumption','witnesses':[cw('Oxygen consumption')]},
            'arrangement':{'value':'single_preparation','witnesses':[cw('single preparation')]}},
        'operands':{}, 'relationships':{role:{'value':LINKS[role][0], 'witnesses':[cw('The same molecule, construct, preparation and assay are linked to all selected controls')]} for role in ROLES},
        'correction_stages':{name:{'value':'already_applied' if name=='background' else 'not_applied',
            'witnesses':[cw('Net background subtraction already applied; contaminant correction not applied; reporter recovery not applied; molecule amount normalization not applied; nuisance correction not applied')]} for name in ('background','contaminant','recovery','molecule_amount','nuisance_condition')},
        'covariance_source_ref':None,'distinct_residual_variance':None,
        'residual_relationship':{'value':'unknown','witnesses':[]},
        'variance_status':'unknown','observation_model':'none','model_witnesses':[]}
    for field, quote in [('molecule','enzyme P'),('organism','organism O'),('construct','construct C'),('preparation','preparation A'),('condition','condition buffer'),('measured_entity','NADH')]:
        arguments['assay'][field] = cw(quote)
    for role, family, namespace, component in [('q','optical',NS_OPTICAL,'net_rate'),('g','assay',NS_ASSAY,'contaminant_rate'),
        ('k','recovery',NS_RECOVERY,'recovery'),('E','active',NS_ACTIVE,'active_site_concentration'),
        ('u','assay',NS_ASSAY,'condition_test_rate'),('v','assay',NS_ASSAY,'condition_reference_rate')]:
        arguments['operands'][role] = {'namespace':namespace,'sheet_ref':outputs[family]['outcome']['result']['sheet_ref'],'component':component}
    return store, context, arguments, outputs


def populate(store, context, arguments, key='compiled-selected'):
    repo = LiteratureCompiledAssayRepository(store, context.run_id)
    outcome = repo.populate(context, arguments, key)
    reference = outcome['result']['sheet_ref']
    return repo, outcome, repo.read(reference)


def extraction(store, context, arguments):
    def source(ref, representation):
        row = store.get(ref); artifact = row['artifact_ref'] if representation=='original' else row['text_ref']
        return {'artifact_ref':artifact,'content':store.get_artifact(artifact)}
    repo = LiteratureCompiledAssayRepository(store, context.run_id)
    return read_compiled_assay_inputs(arguments,read_source=source,
        read_component=lambda selector: repo._input_repository(selector['namespace']).fact_cells(context,[selector['sheet_ref']],components=[selector['component']]),
        read_record=store.get)


def with_covariance(store, context, arguments):
    ex = extraction(store,context,arguments)
    operands = ex['operands']; diagonal=[.04,.0025,.0001,.01,.0025,.0025]
    data = {'version':'a105_compiled_assay_covariance_v1','primitive_order':list(ROLES),
        'operand_keys':[operands[role]['quantity_key'] for role in ROLES],
        'primitive_units':[operands[role]['unit'] for role in ROLES],
        'dependency_keys':[list(dict.fromkeys((*operands[role]['canonical_physical_keys'],*operands[role]['recorded_dependency_keys']))) for role in ROLES],
        'covariance':[[diagonal[i] if i==j else 0 for j in range(6)] for i in range(6)],
        'origin':'synthetic','basis':'joint_covariance_of_canonical_compilation_operands'}
    ref = add_source(store, canonical(data),'compiled_synthetic_joint_covariance',[arguments['source_ref']])
    context=replace(context,received_record_refs=(*context.received_record_refs,ref))
    arguments=deepcopy(arguments);arguments.update(covariance_source_ref=ref,variance_status='known',observation_model='known_normal_nonnegative_presence',
        model_witnesses=[witness(CONTEXT_TEXT,'A jointly known covariance and known normal source model',source=arguments['source_ref'])])
    arguments['distinct_residual_variance']=measurement(CONTEXT_TEXT,'0.001 per_min_squared','0.001','per_min_squared',source=arguments['source_ref'])
    arguments['residual_relationship']={'value':'additional_corrected_scale_variance','witnesses':[witness(CONTEXT_TEXT,'Additional distinct residual variance',source=arguments['source_ref'])]}
    return context,arguments,data


def test_true_saved_component_join_has_actual_numerical_sections_and_partials(tmp_path):
    store,context,args,outputs=setup(tmp_path)
    with store:
        repo,outcome,saved=populate(store,context,args)
        c=saved['sheet']['cells']
        assert c['corrected_activity']['value']==pytest.approx(float(Fraction('1.6')/Fraction('.98')/2/Fraction('.9')))
        assert c['measured_endpoint_per_selected_amount']['value']==pytest.approx(.9)
        assert c['calibrated_measured_endpoint_per_selected_amount']['value']==pytest.approx(float(Fraction('1.8')/(Fraction('.98')*2)))
        assert c['effect_variance']['value'] is None
        assert c['effect_variance']['unavailable_reason']=='primitive_covariance_not_supplied'
        assert c['protein_amount']['value']==2 and c['protein_amount']['unit']=='uM'
        assert saved['extraction']['operands']['E']['row']['value']==2000
        assert saved['extraction']['operands']['k']['row']==outputs['recovery']['repo'].fact_cells(context,[args['operands']['k']['sheet_ref']],components=['recovery'])[0]
        assert not store.list('observation') and not store.list('assessment')
        assert repo.populate(context,args,'compiled-selected')==outcome
        validate_form({'numbers':outcome['result']['cells']},obj({'numbers':compiled_assay_cells_schema()}),lambda ref,ns:store.get(ref)['record_type']==ns)


def test_missing_contaminant_keeps_quantitative_partial_normalizations(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        args['operands']['g']=None
        _,_,saved=populate(store,ctx,args)
        c=saved['sheet']['cells']
        assert c['attributed_rate']['value'] is c['corrected_activity']['value'] is None
        assert c['measured_endpoint_per_selected_amount']['value']==pytest.approx(.9)
        assert c['calibrated_measured_endpoint_per_selected_amount']['value']==pytest.approx(.9183673469387755)
        assert saved['sheet']['effective_values']['g'] is None


def test_activity_spike_cannot_silently_become_instrument_recovery(tmp_path):
    store,ctx,args,_=setup(tmp_path,control_kind='enzyme_activity_spike')
    with store:
        _,_,saved=populate(store,ctx,args)
        cells=saved['sheet']['cells']
        assert cells['recovery']['value']==.98
        assert 'enzyme_activity_spike_is_not_reporter_recovery' in cells['recovery']['qualifications']
        assert cells['corrected_activity']['value'] is None
        assert cells['measured_endpoint_per_selected_amount']['value']==pytest.approx(.9)
        assert cells['calibrated_measured_endpoint_per_selected_amount']['value'] is None


def test_full_covariance_and_residual_match_independent_gradient_oracle(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        ctx,args,data=with_covariance(store,ctx,args)
        _,_,saved=populate(store,ctx,args)
        c=saved['sheet']['cells']; a=Fraction('1.6')/(Fraction('.98')*2*Fraction('.9'))
        f=Fraction(1)/(Fraction('.98')*2*Fraction('.9'))
        gradient=[f,-f,-a/Fraction('.98'),-a/2,-a/Fraction('.9'),a]
        expected=sum(gradient[i]*Fraction(str(data['covariance'][i][j]))*gradient[j] for i in range(6) for j in range(6))+Fraction('.001')
        assert c['effect_variance']['value']==pytest.approx(float(expected))
        assert c['effect_precision']['value']==pytest.approx(1/float(expected))
        assert c['source_profile_log_ratio']['value']==pytest.approx(float(a*a/(2*expected)))
        assert saved['extraction']['covariance_source']['data']['dependency_keys']==data['dependency_keys']


@pytest.mark.parametrize('role',['q','g','k','E','u','v'])
def test_absent_inputs_are_not_zero_or_one(tmp_path,role):
    store,ctx,args,_=setup(tmp_path)
    with store:
        args['operands'][role]=None
        _,_,saved=populate(store,ctx,args)
        assert saved['sheet']['effective_values'][role] is None
        assert saved['sheet']['cells']['corrected_activity']['value'] is None


@pytest.mark.parametrize('stage',['background','contaminant','recovery','molecule_amount','nuisance_condition'])
def test_unknown_stage_preserves_native_rows_and_qualifies_combination(tmp_path,stage):
    store,ctx,args,_=setup(tmp_path)
    with store:
        args['correction_stages'][stage]={'value':'unknown','witnesses':[]}
        _,_,saved=populate(store,ctx,args)
        assert saved['sheet']['cells']['net_rate']['value']==pytest.approx(1.8)
        assert saved['sheet']['cells']['corrected_activity']['value'] is None


def normalized_args(args, outputs):
    args=deepcopy(args)
    args['operands']['q']={'namespace':NS_ASSAY,'sheet_ref':outputs['assay']['outcome']['result']['sheet_ref'],'component':'corrected_activity'}
    args['relationships']['q']['value']='already_normalized_assay_activity'
    for stage in args['correction_stages']:
        args['correction_stages'][stage]={'value':'already_applied','witnesses':[witness(CONTEXT_TEXT,'Already calibrated and contaminant corrected, active amount normalized and nuisance corrected native result',source=args['source_ref'])]}
    return args


def test_already_normalized_native_result_is_copied_without_a_second_amount_division(tmp_path):
    store,ctx,args,outputs=setup(tmp_path)
    with store:
        args=normalized_args(args,outputs)
        _,_,saved=populate(store,ctx,args)
        native=outputs['assay']['repo'].read(args['operands']['q']['sheet_ref'])['sheet']['cells']['corrected_activity']['value']
        assert saved['sheet']['cells']['net_rate']['unit']=='per_min'
        assert saved['sheet']['cells']['corrected_activity']['value']==native
        assert saved['sheet']['cells']['corrected_activity']['formula']=='source_already_corrected_amount_normalized_value'


def test_normalized_native_shortcut_cannot_override_known_wrong_endpoint(tmp_path):
    store,ctx,args,outputs=setup(tmp_path)
    with store:
        args=normalized_args(args,outputs)
        args['assay']['endpoint']={'value':'growth','witnesses':[witness(CONTEXT_TEXT,'Growth phenotype',source=args['source_ref'])]}
        _,_,saved=populate(store,ctx,args)
        assert saved['sheet']['cells']['net_rate']['value'] is not None
        assert saved['sheet']['cells']['corrected_activity']['value'] is None
        assert saved['sheet']['cells']['corrected_activity']['unavailable_reason']=='endpoint_requires_different_model'


def test_native_rate_cannot_accept_covariance_declared_as_concentration_rate(tmp_path):
    store,ctx,args,outputs=setup(tmp_path)
    with store:
        ctx,args,data=with_covariance(store,ctx,args)
        args=normalized_args(args,outputs)
        # Rebind packet owners to the real native selection, retaining the wrong
        # uM/min declaration: dimension matching must use the actual quantity.
        ex_args=deepcopy(args);ex_args['covariance_source_ref']=None
        ex=extraction(store,ctx,ex_args)
        data['operand_keys']=[ex['operands'][role]['quantity_key'] for role in ROLES]
        data['dependency_keys']=[list(dict.fromkeys((*ex['operands'][role]['canonical_physical_keys'],*ex['operands'][role]['recorded_dependency_keys']))) for role in ROLES]
        ref=add_source(store,canonical(data),'compiled_wrong_covariance',[args['source_ref']]);ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,ref));args['covariance_source_ref']=ref
        with pytest.raises(Exception,match='compiled_covariance_unit_mismatch'):
            populate(store,ctx,args)


def test_dependency_selection_omits_optical_wavelength_and_active_spread(tmp_path):
    store,ctx,args,outputs=setup(tmp_path)
    with store:
        _,_,saved=populate(store,ctx,args)
        q=saved['extraction']['operands']['q'];e=saved['extraction']['operands']['E']
        assert len(q['canonical_physical_keys'])==4
        assert len(e['canonical_physical_keys'])==1
        assert not e['recorded_dependency_keys']
        assert q['quantity_key']!=e['quantity_key']


def test_unadmitted_cell_is_not_acquired_by_possessing_its_sheet_reference(tmp_path):
    store,ctx,args,outputs=setup(tmp_path)
    with store:
        receiver=replace(ctx,episode_id='receiver',received_record_refs=ctx.received_record_refs)
        recovery=outputs['recovery']['repo']; ref=args['operands']['k']['sheet_ref']
        rows=recovery.project_cells([ref],permitted_record_refs=[ref],components=['measured'])
        recovery.receive_cells(receiver,rows,'trusted-synthetic-subset')
        with pytest.raises(ContractError,match='selected_component_not_received'):
            populate(store,receiver,args)


def test_no_component_reference_receipt_is_rejected(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        ctx=replace(ctx,received_record_refs=tuple(ref for ref in ctx.received_record_refs if ref!=args['operands']['q']['sheet_ref']))
        with pytest.raises(ContractError,match='not_received'):
            populate(store,ctx,args)


def test_missing_scope_allows_point_arithmetic_but_not_conditional_function_profile(tmp_path):
    store,ctx,args,_=setup(tmp_path)
    with store:
        ctx,args,_=with_covariance(store,ctx,args)
        args['assay']['molecule']=None
        _,_,saved=populate(store,ctx,args)
        assert saved['sheet']['cells']['corrected_activity']['value'] is not None
        assert saved['sheet']['cells']['source_profile_log_ratio']['unavailable_reason']=='source_scientific_scope_unresolved'


def forbid(*args,**kwargs):
    raise AssertionError('saved compiled result cannot reacquire or recalculate science')


def readonly(path):
    store=Store.__new__(Store);store.path=path;store._savepoint=0
    store.db=sqlite3.connect((path/'state.sqlite3').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    store.db.row_factory=sqlite3.Row;store.db.execute('PRAGMA query_only=ON')
    return store


def test_saved_read_and_exact_admitted_subset_are_readonly_without_any_upstream_science(tmp_path,monkeypatch):
    store,ctx,args,_=setup(tmp_path)
    repo,outcome,saved=populate(store,ctx,args)
    ref=outcome['result']['sheet_ref']; rows=repo.project_cells([ref],permitted_record_refs=[ref],components=['corrected_activity'])
    parent=replace(ctx,episode_id='parent',role='annotation',path=(('annotation','parent'),),assignment={},received_record_refs=(ref,))
    repo.receive_cells(parent,rows,'trusted-synthetic-admission')
    allowed={store.get(ref)['artifact_ref'],store.get(ref)['request_ref']}
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.close()
    hashes={str(p.relative_to(tmp_path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob('*') if p.is_file()}
    for module,names in {'literature_compiled_assay_storage':('read_compiled_assay_inputs','populate_compiled_assay'),
        'literature_compiled_assay_inputs':('read_compiled_assay_inputs',),
        'literature_activity_calculations':('populate_corrected_activity',),
        'literature_optical_storage':('read_optical_rate_operands','calculate_nadh_optical_rate'),
        'literature_active_site_storage':('read_active_site_inputs','populate_active_site_components'),
        'literature_calibration_recovery_inputs':('read_calibration_recovery_inputs',)}.items():
        for name in names:monkeypatch.setattr('gene_annotation_episode.'+module+'.'+name,forbid)
    with readonly(tmp_path) as opened:
        raw=opened.get_artifact
        def committed_only(reference):
            assert reference in allowed
            return raw(reference)
        monkeypatch.setattr(opened,'get_artifact',committed_only)
        new=LiteratureCompiledAssayRepository(opened,ctx.run_id)
        assert new.read(ref)==saved
        assert new.received_cells(parent)==rows
        assert new.fact_cells(parent,[ref],components=list(COMPONENTS))==rows
        assert new.populate(ctx,args,'compiled-selected')==outcome
        assert opened.db.total_changes==0
        with pytest.raises(sqlite3.OperationalError,match='readonly'):
            opened.db.execute('DELETE FROM records')
    assert hashes=={str(p.relative_to(tmp_path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob('*') if p.is_file()}


def test_censored_original_active_amount_retains_native_limit_only_when_requested(tmp_path):
    store,ctx,args,outputs=setup(tmp_path)
    with store:
        text=ACTIVE_TEXT.replace('Mass 4 ng/uL','Mass 400 ng/uL').replace('60 ± 3 nM','<2003 nM').replace('Rate already active normalized','Rate uses total monomer concentration')
        ref=add_source(store,text,'compiled_synthetic_upper_limit',[args['source_ref']])
        active=active_fixture(text,mass=('400 ng/uL','400','ng/uL'),active=('<2003 nM','2003','nM'))[0]
        active=remap(active,ACTIVE_SOURCE,ref)
        active['quantities']['active_site_concentration']['reported_uncertainty']={
            'kind':{'value':'unreported','witnesses':[]},'measurement':None,
            'sampling_basis':{'value':'unknown','witnesses':[]},'statement':None}
        active['interpretations']['normalization_stage']={'value':'total_monomer','witnesses':[witness(text,'Rate uses total monomer concentration',source=ref)]}
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,ref))
        result=LiteratureActiveSiteRepository(store,ctx.run_id).populate(ctx,active,'bounded-original')
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,*result['record_refs']))
        args['operands']['E']['sheet_ref']=result['result']['sheet_ref']
        repo,outcome,saved=populate(store,ctx,args)
        native=next(row for row in outcome['result']['cells'] if row['component']=='protein_amount')
        domain=native['native_quantity']
        assert native['value'] is None and native['unavailable_reason']=='bounded_operand_compilation_unimplemented'
        assert domain['source_unit']=='nM' and domain['domain_conversion']=='not_converted'
        assert domain['reported_domain']['kind']=='finite_interval'
        assert domain['reported_domain']['lower']==0
        assert domain['reported_domain']['upper']==2003 and not domain['reported_domain']['upper_inclusive']
        derived=repo.project_cells([outcome['result']['sheet_ref']],permitted_record_refs=outcome['record_refs'],components=['corrected_activity'])
        assert derived[0]['native_quantity'] is None and derived[0]['value'] is None
        assert '2003' not in canonical(derived)
        assert derived[0]['operand_meanings']['E']=='same_assay_active_molecules'
        from gene_annotation_episode.literature_compiled_assay_render import render_received
        parts=[]
        render_received(parts,[native],section=lambda p,t,c:p.append(t+'\n'+c),table=lambda h,r:'\n'.join('|'.join(map(str,row)) for row in r))
        assert 'finite_interval' in '\n'.join(parts) and 'same_assay_active_molecules' in '\n'.join(parts)


def test_same_raw_measurement_with_different_component_keys_is_not_independent(tmp_path):
    store,ctx,args,outputs=setup(tmp_path)
    with store:
        ordinary=deepcopy(outputs['assay']['arguments'])
        ordinary['primitives']['g']=deepcopy(ordinary['primitives']['q'])
        out=LiteratureAssayRepository(store,ctx.run_id).populate(ctx,ordinary,'repeated-physical-source')
        ctx=replace(ctx,received_record_refs=(*ctx.received_record_refs,*out['record_refs']))
        for role,component in [('q','net_rate'),('g','contaminant_rate')]:
            args['operands'][role]={'namespace':NS_ASSAY,'sheet_ref':out['result']['sheet_ref'],'component':component}
        ex=extraction(store,ctx,args)
        q,g=ex['operands']['q'],ex['operands']['g']
        assert q['component_key']!=g['component_key']
        assert q['quantity_key']==g['quantity_key'] and q['canonical_physical_keys']==g['canonical_physical_keys']
        ctx,args,data=with_covariance(store,ctx,args)
        with pytest.raises(Exception,match='shared_measurement_covariance_mismatch'):
            populate(store,ctx,args)
