"""Controlled synthetic typed activities and retained original-source limit reads.

The activity rows below are explicit synthetic contract fixtures, not claimed
outputs of an original paper or a selected episode. Original source cases use
actual retained bytes but supplied scientific interpretations, not a model.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import pytest
from gene_annotation_episode.domain import identity,validate_schema
from gene_annotation_episode.literature_assay_inputs import ASSAY_LITERAL_FIELDS
from gene_annotation_episode.literature_compiled_assay_inputs import LINKS,ROLES as SIX
from gene_annotation_episode.literature_compiled_assay_calculations import MEANINGS,FORMULAS
from gene_annotation_episode.literature_compiled_assay_storage import compiled_assay_cells_schema
from gene_annotation_episode.literature_ion_discrimination_inputs import (
    ion_discrimination_population_schema,ion_discrimination_sheet_schema,read_ion_discrimination_inputs,activity_key,dependency_keys)
from gene_annotation_episode.literature_ion_discrimination_calculations import populate_ion_discrimination
from gene_annotation_episode.literature_ion_discrimination_prompt import ION_DISCRIMINATION_TASK
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError

SOURCE='source_'+('194b'*6)
TEXT=('Synthetic protein P construct C in a liposome preparation. Fluoride and chloride are distinct tested ions. '
      'Ion-specific per-unit transport-flux estimators have matched nonintended conditions, molecular basis and controls. '
      'Actual ion and protein attribution is stipulated for this synthetic case. '
      'Detector difference is addressed by measured reporter recovery in each saved corrected activity. '
      'The synthetic joint covariance of activity estimators is supplied explicitly; no independence is inferred.')
ROOT=Path(__file__).resolve().parents[1]


def w(text,quote=None,*,at=None):
    quote=text if quote is None else quote;i=text.index(quote) if at is None else at
    return {'source_ref':SOURCE,'representation':'original','start':len(text[:i].encode()),'end':len(text[:i+len(quote)].encode()),'quote':quote}


def interpretation(value,text=TEXT):return {'value':value,'witnesses':[] if value=='unknown' else [w(text)]}


def row(role,value):
    ref='source_'+hashlib.sha256(role.encode()).hexdigest()[:24]
    selectors={r:{'namespace':'literature_assay_cells','sheet_ref':ref,'component':{'q':'net_rate','g':'contaminant_rate','k':'recovery','E':'protein_amount','u':'condition_test_rate','v':'condition_reference_rate'}[r]} for r in SIX}
    deps=[{'role':r,'selection':selectors[r],'component_key':identity('synthetic_component',{'role':role,'operand':r}),
        'quantity_key':identity('synthetic_quantity',{'role':role,'operand':r}),
        'canonical_physical_keys':[identity('physical_source_span',{'arm':role,'operand':r})],
        'recorded_dependency_keys':[],'physical_identity_status':'partly_canonical','identity_stage':None} for r in SIX]
    result={'sheet_ref':ref,'evidence_source_ref':SOURCE,'evaluation_scope':'compiled_source_endpoint','component':'corrected_activity',
        'value':value,'unit':'per_min','status':'populated','unavailable_reason':None,'formula':FORMULAS['corrected_activity'],
        'origin':'synthetic','section':'compiled_source_endpoint_effect','meaning':MEANINGS['corrected_activity'],
        'conditional_on':[],'qualifications':[],'formula_code':'corrected_activity_compiled_v1','dependencies':deps,
        'native_quantity':None,'operand_meanings':{r:LINKS[r][0] for r in SIX},
        'assay_meanings':{x:None for x in ASSAY_LITERAL_FIELDS},'endpoint_kind':'transport_flux','arrangement_kind':'single_preparation',
        'correction_stages':{s:'already_applied' if s=='background' else 'not_applied' for s in ('background','contaminant','recovery','molecule_amount','nuisance_condition')},
        'variance_status':'unknown','observation_model':'none','covariance_source_ref':None,'residual_variance_source_ref':None,
        'operand_eligibility':dict.fromkeys(SIX),'partial_uncertainty_status':'unimplemented','covariance_input_status':'not_selected','annotation_credit':None}
    validate_schema([result],compiled_assay_cells_schema());return result


def common(text=TEXT):
    schema=ion_discrimination_population_schema()
    contexts={r:{name:None for name in schema['$defs']['Context']['properties'][r]['properties']} for r in ('preferred','alternative')}
    contexts.update({name:None for name in ('preferred_ion','alternative_ion','intended_change','assertion')})
    contexts['preferred_ion']=w(text);contexts['alternative_ion']=w(text);contexts['intended_change']=w(text)
    vals={'subject_construct':'same_construct','quantity':'same_ion_specific_rate_kind','normalization':'same_molecular_basis',
        'nonintended_conditions':'matched','preferred_ion_attribution':'intended_protein_and_ion_supported',
        'alternative_ion_attribution':'intended_protein_and_ion_supported','preparations':'same_preparation','intended_ions':'different_ions'}
    return {'version':'a105_ion_discrimination_selection_v1','source_ref':SOURCE,'source_kind':'synthetic_fixture',
        'context':contexts,'relationships':{k:interpretation(v,text) for k,v in vals.items()},'nonintended_differences':[]}


def setup(A=.9,B=.15):
    rows=[row('preferred',A),row('alternative',B)]
    args={**common(),'route':'compiled_activity_pair','activities':{r:{'namespace':'literature_compiled_assay_cells','sheet_ref':x['sheet_ref'],'component':'corrected_activity'} for r,x in zip(('preferred','alternative'),rows)},
        'activity_covariance_source_ref':None,'variance_status':'unknown','variance_witnesses':[],'adjustment_bindings':[]}
    sources={SOURCE:TEXT.encode()}
    return args,rows,sources


def read(args,rows,sources):
    def source(ref,representation):
        assert representation=='original' and ref in sources
        raw=sources[ref];return {'artifact_ref':'artifact_'+hashlib.sha256(raw).hexdigest(),'content':raw}
    def component(selected):
        assert selected['namespace']=='literature_compiled_assay_cells'
        return [deepcopy(r) for r in rows if r['sheet_ref']==selected['sheet_ref'] and r['component']==selected['component']]
    return read_ion_discrimination_inputs(args,read_source=source,read_component=component)


def calculate(args,rows,sources):
    e=read(args,rows,sources);return e,populate_ion_discrimination(e)


def covariance(args,rows,sources,matrix,status='known'):
    args=deepcopy(args);sources=deepcopy(sources);ref='source_'+('194c'*6)
    packet={'version':'a105_ion_activity_covariance_v1','activity_order':['preferred','alternative'],
        'activity_keys':[activity_key(args['activities'][r]) for r in ('preferred','alternative')],
        'activity_units':['per_min','per_min'],'dependency_keys':[dependency_keys(r) for r in rows],
        'matrix':matrix,'variance_status':status,'origin':'synthetic','basis':'joint_covariance_of_selected_per_unit_activity_estimators'}
    sources[ref]=json.dumps(packet).encode();args.update(activity_covariance_source_ref=ref,variance_status=status,variance_witnesses=[w(TEXT)])
    return args,sources,packet


def test_actual_zero_and_signed_estimator_ratios_are_not_clipped_or_promoted():
    for A,expected in [(0,0),(-.03,-.2),(.9,6)]:
        args,rows,sources=setup(A)
        _,s=calculate(args,rows,sources);r=s['cells']['activity_ratio']
        assert r['value']==pytest.approx(expected) and r['status']=='populated'
        assert r['physical_domain'] is None
        if A<=0:assert s['cells']['log_activity_ratio']['unavailable_reasons']==['ratio_not_positive']
        if A<0:assert r['scientific_applicability']=='estimator_comparison_only'
        assert s['cells']['activity_ratio_variance']['unavailable_reasons']==['covariance_not_selected']
    assert s['cells']['log_activity_ratio']['value']==pytest.approx(math.log(6))


def test_zero_denominator_does_not_become_infinity_or_missing_measurement():
    args,rows,sources=setup(B=0);_,s=calculate(args,rows,sources)
    assert s['cells']['alternative_activity']['value']==0
    assert s['cells']['activity_ratio']['value'] is None
    assert s['cells']['activity_ratio']['unavailable_reasons']==['zero_denominator_estimator']


def test_explicit_joint_correlated_covariance_and_estimated_status():
    args,rows,sources=setup();args,sources,_=covariance(args,rows,sources,[[.0081,.000675],[.000675,.000225]])
    _,s=calculate(args,rows,sources);c=s['cells']
    assert c['activity_ratio']['value']==6
    assert c['activity_ratio_variance']['value']==pytest.approx(.36)
    assert c['activity_ratio_standard_uncertainty']['value']==pytest.approx(.6)
    assert c['log_activity_ratio_variance']['value']==pytest.approx(.01)
    assert c['log_activity_ratio_standard_uncertainty']['value']==pytest.approx(.1)
    args['variance_status']='estimated';packet=json.loads(sources[args['activity_covariance_source_ref']]);packet['variance_status']='estimated';sources[args['activity_covariance_source_ref']]=json.dumps(packet).encode()
    _,s=calculate(args,rows,sources)
    assert s['cells']['activity_ratio_variance']['variance_status']=='estimated'


@pytest.mark.parametrize('matrix',[[[.01,.1],[.1,.01]],[[.01,0],[.001,.01]],[[True,0],[0,.01]]])
def test_bad_joint_source_covariance_preserves_mean_and_native_activities(matrix):
    args,rows,sources=setup();args,sources,_=covariance(args,rows,sources,matrix)
    _,s=calculate(args,rows,sources)
    assert s['cells']['activity_ratio']['value']==6
    assert s['cells']['activity_ratio_variance']['unavailable_reasons']==['covariance_invalid']


def test_covariance_ownership_cannot_be_borrowed_from_a_different_activity():
    args,rows,sources=setup();args,sources,p=covariance(args,rows,sources,[[.01,0],[0,.01]])
    p['activity_keys'][0]='wrong';sources[args['activity_covariance_source_ref']]=json.dumps(p).encode()
    _,s=calculate(args,rows,sources)
    assert s['cells']['activity_ratio']['value']==6
    assert s['cells']['activity_ratio_variance']['unavailable_reasons']==['covariance_owner_or_dependency_mismatch']


@pytest.mark.parametrize('field,state,reason',[('subject_construct','paper_summary_unresolved','subject_construct_unresolved'),('quantity','different_physical_quantity','different_physical_quantities'),('normalization','different_molecular_basis','different_molecular_basis'),('nonintended_conditions','different','nonintended_conditions_different'),('preferred_ion_attribution','mixed_contributors_unresolved','ion_attribution_unresolved')])
def test_different_or_unknown_scientific_relationship_preserves_native_partial(field,state,reason):
    args,rows,sources=setup();args['relationships'][field]=interpretation(state)
    _,s=calculate(args,rows,sources)
    assert s['cells']['preferred_activity']['value']==.9
    assert reason in s['cells']['activity_ratio']['unavailable_reasons']


def test_adjustment_enum_requires_real_compiled_control_binding_for_every_difference():
    args,rows,sources=setup();args['relationships']['nonintended_conditions']=interpretation('source_supported_adjustment')
    args['nonintended_differences']=[{'aspect':'detector','witnesses':[w(TEXT)]}]
    _,s=calculate(args,rows,sources)
    assert 'adjustment_binding_required' in s['cells']['activity_ratio']['unavailable_reasons']
    args['adjustment_bindings']=[{'difference_index':0,'arm':'preferred','compiled_stage':'recovery','control_application':'addresses_selected_nonintended_difference','witnesses':[w(TEXT)]}]
    _,s=calculate(args,rows,sources);assert s['cells']['activity_ratio']['value']==6
    rows[0]['operand_meanings']['k']='unknown'
    _,s=calculate(args,rows,sources)
    assert 'adjustment_not_in_compiled_activity' in s['cells']['activity_ratio']['unavailable_reasons']


def test_same_selected_activity_and_different_normalization_are_not_discrimination():
    args,rows,sources=setup();args['activities']['alternative']=deepcopy(args['activities']['preferred'])
    _,s=calculate(args,rows,sources);assert 'reused_activity_not_ion_discrimination' in s['cells']['activity_ratio']['unavailable_reasons']
    args,rows,sources=setup();rows[1]['operand_meanings']['E']='same_assay_total_molecules'
    _,s=calculate(args,rows,sources);assert 'different_molecular_basis' in s['cells']['activity_ratio']['unavailable_reasons']


def test_unreceived_activity_row_fails_without_acquiring_a_private_sheet():
    args,rows,sources=setup()
    with pytest.raises(ExperimentalContractError,match='selected_activity_not_received'):
        calculate(args,rows[:1],sources)


def source_quantity(text,token,unit,*,meaning='per_unit_ion_efflux_rate',approx=False,physical=False,scope='specific_construct',at=None):
    i=text.index(token) if at is None else at
    number={'witness':w(text,token,at=i),'number_start':0,'number_end':len(token)}
    paragraph_start=text.rfind('<p>',0,i)
    paragraph_end=text.find('</p>',i)
    evidence=text[paragraph_start:paragraph_end+4] if paragraph_start>=0 and paragraph_end>=0 else text
    interp=lambda v: {'value':v,'witnesses':[] if v=='unknown' else [w(text,evidence)]}
    return {'number':number,'unit':None if unit is None else w(text,unit,at=text.index(unit,i+len(token))),
        'meaning':interp(meaning),'derivation':interp('source_parameter_bound_derivation_supported' if physical else 'author_inferred_dead_time_and_geometry'),
        'qualification':interp('source_qualified_approximate' if approx else 'no_additional_source_qualification_selected'),
        'quantity_scope':interp(scope),'domain_bearer':interp('physical_parameter' if physical else 'author_estimate'),
        'physical_domain_support':interp('explicit_nonnegative_parameter_limit_supported' if physical else 'reported_estimate_only')}


def test_exact_conditional_physical_bounds_preserve_possible_zero_denominator():
    text='Synthetic preferred rate >30000 per_s; alternative rate <30 ions/s.'
    args={**common(text),'route':'reported_threshold_pair','thresholds':{'preferred':source_quantity(text,'30000','per_s',physical=True),'alternative':source_quantity(text,'30','ions/s',physical=True,at=text.index('<30')+1)}}
    _,s=calculate(args,[],{SOURCE:text.encode()});c=s['cells']['nominal_threshold_ratio']
    assert c['threshold']==1000 and c['physical_domain']['lower']==1000 and c['physical_domain']['lower_inclusive'] is False
    assert c['physical_domain']['upper_unbounded'] and 'denominator_positive_condition' in c['limitations']
    assert s['cells']['alternative_activity']['physical_domain']['lower']==0


def original_common(text):
    args=common(TEXT)
    for role in ('preferred','alternative'):
        args['context'][role]=dict.fromkeys(args['context'][role])
    for name in ('preferred_ion','alternative_ion','intended_change','assertion'):args['context'][name]=None
    args['context']['preferred_ion']=w(text,'F<sup>−</sup>')
    args['context']['alternative_ion']=w(text,'Cl<sup>−</sup>')
    args['relationships']={k:{'value':'unknown','witnesses':[]} for k in args['relationships']}
    args['relationships']['intended_ions']={'value':'different_ions','witnesses':[w(text,'F<sup>−</sup>'),w(text,'Cl<sup>−</sup>')]}
    return args


def original_source():
    p=ROOT/'research/experimental_scoring_review_2026-10-23/a105_transport_channel_case_174/source/elife-01084-v1.xml'
    raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='83867d6966a972f32899bdfe545c9952cb9d10393dc54d68dce29b6f4954b053'
    return raw.decode(),raw


def test_original_fluoride_thresholds_keep_approximation_summary_ownership_and_native_counts():
    text,raw=original_source();args=original_common(text);args['source_kind']='primary_source';args['relationships']['subject_construct']=interpretation('paper_summary_unresolved',text)
    discussion=text.index('Anion-efflux assays measure');F=text.index('30,000',discussion);Cl=text.index('30 ions/s',discussion)
    preferred=source_quantity(text,'30,000','s<sup>−1</sup>',approx=True,scope='paper_summary_unresolved',at=F)
    alternative=source_quantity(text,'30','ions/s',scope='paper_summary_unresolved',at=Cl)
    alternative['derivation']={'value':'unknown','witnesses':[]}
    result_start=text.index('<p>Purified Fluc proteins are functional')
    result_end=text.index('channel.<fig',result_start)+len('channel.')
    results_witness=w(text,text[result_start:result_end])
    preferred['qualification']={'value':'source_qualified_approximate','witnesses':[results_witness]}
    preferred['derivation']={'value':'author_inferred_dead_time_and_geometry','witnesses':[results_witness]}
    args.update(route='reported_threshold_pair',thresholds={'preferred':preferred,'alternative':alternative})
    _,s=calculate(args,[],{SOURCE:raw});c=s['cells']['nominal_threshold_ratio']
    assert c['threshold']==1000 and c['nominal_domain']['lower']==1000
    assert c['physical_domain'] is None and 'subject_construct_unresolved' in c['unavailable_reasons']
    assert 'approximation_model_missing' in c['unavailable_reasons']
    assert s['cells']['alternative_activity']['threshold']==30 and s['cells']['alternative_activity']['value'] is None
    assert s['cells']['alternative_activity']['derivation']=='unknown'
    assert s['cells']['alternative_activity']['origin']=='reported'
    assert s['cells']['preferred_activity']['derivation']=='author_inferred_dead_time_and_geometry'
    assert 'nonadjacent_source_approximation' in s['cells']['preferred_activity']['source_qualifications']


@pytest.mark.parametrize('token,meaning,expected', [('100','reported_permeability_ratio',100),('10<sup>4</sup>','reported_cross_assay_summary_ratio',10000)])
def test_original_reported_biionic_and_author_summary_values_are_separate(token,meaning,expected):
    text,raw=original_source();args=original_common(text);args['source_kind']='primary_source'
    at=text.index('lower limit of ∼100')+len('lower limit of ∼') if token=='100' else text.index('10<sup>4</sup>',text.index('Anion-efflux assays measure'))
    q=source_quantity(text,token,None,meaning=meaning,approx=token=='100',at=at,scope='paper_summary_unresolved' if token!='100' else 'specific_construct')
    q['derivation']=interpretation('author_inferred_electrical_model' if token=='100' else 'author_summary_inference',text)
    args.update(route='reported_ratio',reported_ratio=q)
    _,s=calculate(args,[],{SOURCE:raw});c=s['cells']['reported_selectivity']
    assert c['threshold']==expected and c['physical_domain'] is None
    assert c['relation']==('lower_limit' if token=='100' else 'gt')
    assert s['cells']['nominal_threshold_ratio']['value'] is None


def test_full_task_matches_root_printed_proposal_and_schema_formulas_are_closed():
    task=(ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_ion_discrimination_design_194/PROPOSED_TASK_001.txt').read_text().rstrip()
    assert ION_DISCRIMINATION_TASK==task
    args,rows,sources=setup();_,s=calculate(args,rows,sources)
    bad=deepcopy(s);bad['cells']['activity_ratio']['formula_code']='unknown fake interpretation'
    with pytest.raises(Exception):validate_schema(bad,ion_discrimination_sheet_schema())


@pytest.mark.parametrize('A,B,expected',[(.03,-.15,-.2),(-.9,-.15,6)])
def test_negative_denominator_is_estimator_arithmetic_only(A,B,expected):
    args,rows,sources=setup(A,B);_,s=calculate(args,rows,sources);c=s['cells']['activity_ratio']
    assert c['value']==pytest.approx(expected) and c['scientific_applicability']=='estimator_comparison_only'
    assert c['physical_domain'] is None and s['cells']['alternative_activity']['value']==B


def test_reported_rate_cannot_masquerade_as_dimensionless_selectivity():
    text='A reported rate >30 per_s.'
    args={**common(text),'route':'reported_ratio','reported_ratio':source_quantity(text,'30','per_s')}
    e,s=calculate(args,[],{SOURCE:text.encode()})
    assert e['operands']['reported']['number']['value']==30
    assert s['cells']['reported_selectivity']['value'] is None and s['cells']['reported_selectivity']['threshold'] is None
    assert s['cells']['reported_selectivity']['unavailable_reasons']==['different_physical_quantities']


def test_synthetic_covariance_cannot_supply_uncertainty_for_a_primary_source():
    args,rows,sources=setup();args,sources,_=covariance(args,rows,sources,[[.01,0],[0,.01]])
    args['source_kind']='primary_source'
    for r in rows:r['origin']='reported'
    _,s=calculate(args,rows,sources)
    assert s['cells']['activity_ratio']['value']==6
    assert s['cells']['activity_ratio_variance']['unavailable_reasons']==['covariance_invalid']


def test_physical_domain_requires_meaning_derivation_scope_and_nonapproximate_support():
    text='A selectivity lower limit of 100-fold.'
    base={**common(text),'route':'reported_ratio','reported_ratio':source_quantity(text,'100',None,
        meaning='reported_transport_selectivity_ratio',physical=True)}
    _,s=calculate(base,[],{SOURCE:text.encode()})
    assert s['cells']['reported_selectivity']['physical_domain']['lower']==100
    assert s['cells']['reported_selectivity']['physical_domain']['lower_inclusive'] is None
    for field,value,expected in [('meaning','reported_cross_assay_summary_ratio','reported_estimate_not_physical_bound'),
        ('derivation','author_inferred_electrical_model','physical_parameter_model_unimplemented'),
        ('quantity_scope','paper_summary_unresolved','subject_construct_unresolved'),
        ('qualification','source_qualified_approximate','approximation_model_missing'),
        ('domain_bearer','measured_estimator','physical_domain_support_missing')]:
        args=deepcopy(base);args['reported_ratio'][field]=interpretation(value,text)
        _,s=calculate(args,[],{SOURCE:text.encode()});c=s['cells']['reported_selectivity']
        assert c['threshold']==100 and c['physical_domain'] is None
        assert expected in c['unavailable_reasons']


def test_native_missing_numbers_and_unimplemented_representation_are_distinct():
    text='A selectivity >10^4-fold.'
    args={**common(text),'route':'reported_ratio','reported_ratio':source_quantity(text,'10^4',None,meaning='reported_transport_selectivity_ratio')}
    _,s=calculate(args,[],{SOURCE:text.encode()})
    assert 'unimplemented_number_representation' in s['cells']['reported_selectivity']['unavailable_reasons']
    args['reported_ratio']['number']=None
    _,s=calculate(args,[],{SOURCE:text.encode()})
    assert 'source_number_not_selected' in s['cells']['reported_selectivity']['unavailable_reasons']


def test_singular_shared_factor_covariance_cancels_without_an_independence_claim():
    args,rows,sources=setup();args,sources,_=covariance(args,rows,sources,[[.0081,.00135],[.00135,.000225]])
    _,s=calculate(args,rows,sources)
    assert s['cells']['activity_ratio']['value']==6
    assert s['cells']['activity_ratio_variance']['value']==0
    assert s['cells']['log_activity_ratio_variance']['value']==0
    assert s['cells']['activity_ratio_standard_uncertainty']['value']==0
    assert 'no_independence_from_distinct_refs' in s['cells']['activity_ratio']['limitations']


def test_zero_preferred_physical_point_over_a_positive_denominator_branch_is_zero():
    text='Synthetic preferred rate 0 per_s; alternative rate <30 ions/s.'
    args={**common(text),'route':'reported_threshold_pair','thresholds':{
        'preferred':source_quantity(text,'0','per_s',physical=True),
        'alternative':source_quantity(text,'30','ions/s',physical=True)}}
    _,s=calculate(args,[],{SOURCE:text.encode()});c=s['cells']['nominal_threshold_ratio']
    assert c['value']==0 and c['relation']=='point'
    assert c['nominal_domain']['lower']==c['nominal_domain']['upper']==0
    assert c['physical_domain']['lower']==c['physical_domain']['upper']==0
    assert c['zero_denominator_case']=='possible_in_source_domain'
    assert 'denominator_positive_condition' in c['limitations']


def test_nonnegative_physical_parameter_cannot_have_a_strict_upper_limit_zero():
    text='Synthetic preferred rate >10 per_s; alternative rate <0 ions/s.'
    args={**common(text),'route':'reported_threshold_pair','thresholds':{
        'preferred':source_quantity(text,'10','per_s',physical=True),
        'alternative':source_quantity(text,'0','ions/s',physical=True,at=text.index('<0')+1)}}
    _,s=calculate(args,[],{SOURCE:text.encode()})
    assert s['cells']['alternative_activity']['threshold']==0
    assert s['cells']['alternative_activity']['physical_domain'] is None
    assert 'physical_domain_inconsistent' in s['cells']['alternative_activity']['unavailable_reasons']


def test_reported_spread_is_retained_as_unimplemented_not_an_exact_physical_bound():
    text='A selectivity lower limit of 100 ±3-fold.'
    args={**common(text),'route':'reported_ratio','reported_ratio':source_quantity(text,'100',None,meaning='reported_transport_selectivity_ratio',physical=True)}
    _,s=calculate(args,[],{SOURCE:text.encode()});c=s['cells']['reported_selectivity']
    assert c['threshold']==100 and c['physical_domain'] is None
    assert 'reported_uncertainty_reading_unimplemented' in c['unavailable_reasons']


def test_pure_calculator_rejects_changed_mean_owner_and_invalid_covariance_after_read():
    args,rows,sources=setup();e=read(args,rows,sources)
    bad=deepcopy(e);bad['operands']['preferred']['activity_key']='changed'
    with pytest.raises(ExperimentalContractError,match='ion_extraction_selection_mismatch'):populate_ion_discrimination(bad)
    args,sources,_=covariance(args,rows,sources,[[.01,0],[0,.01]]);e=read(args,rows,sources)
    e['covariance']['data']['matrix']=[[-1,0],[0,.01]]
    with pytest.raises(ExperimentalContractError,match='covariance_invalid'):populate_ion_discrimination(e)


@pytest.mark.parametrize('meaning',['charge_equivalent_rate','signed_reporter_estimator','unknown','conflicting'])
def test_native_nonion_meaning_and_unknown_derivation_are_never_relabeled(meaning):
    text='Preferred quantity >30 per_s; alternative <3 ions/s. One account calls this an ion-specific rate. Another account calls this charge equivalents.'
    preferred=source_quantity(text,'30','per_s',meaning=meaning)
    preferred['derivation']={'value':'unknown','witnesses':[]}
    if meaning=='conflicting':preferred['meaning']['witnesses']=[w(text,'One account calls this an ion-specific rate.'),w(text,'Another account calls this charge equivalents.')]
    args={**common(text),'source_kind':'primary_source','route':'reported_threshold_pair','thresholds':{
        'preferred':preferred,'alternative':source_quantity(text,'3','ions/s',at=text.index('<3')+1)}}
    _,s=calculate(args,[],{SOURCE:text.encode()});c=s['cells']['preferred_activity']
    assert c['threshold']==30 and c['quantity_kind']==meaning and c['origin']=='reported' and c['derivation']=='unknown'
    assert c['physical_domain'] is None and s['cells']['nominal_threshold_ratio']['threshold'] is None


def test_conflicting_qualification_retains_known_adjacent_approximation():
    text='A reported permeability lower limit of ∼100-fold. One description calls the estimate approximate. Another calls it exact.'
    q=source_quantity(text,'100',None,meaning='reported_permeability_ratio')
    q['qualification']={'value':'conflicting','witnesses':[w(text,'One description calls the estimate approximate.'),w(text,'Another calls it exact.')]} 
    args={**common(text),'route':'reported_ratio','reported_ratio':q}
    _,s=calculate(args,[],{SOURCE:text.encode()});c=s['cells']['reported_selectivity']
    assert c['approximation']=='conflicting' and c['threshold']==100
    assert set(c['source_qualifications'])=={'adjacent_approximate','selected_qualification_conflicting'}
    assert c['physical_domain'] is None


def test_known_strict_denominator_preserves_strictness_with_unknown_numerator_inclusivity():
    text='Preferred lower limit of 30 per_s; alternative <3 ions/s.'
    args={**common(text),'route':'reported_threshold_pair','thresholds':{
        'preferred':source_quantity(text,'30','per_s',physical=True),
        'alternative':source_quantity(text,'3','ions/s',physical=True,at=text.index('<3')+1)}}
    _,s=calculate(args,[],{SOURCE:text.encode()});c=s['cells']['nominal_threshold_ratio']
    assert c['nominal_domain']['lower']==10 and c['nominal_domain']['lower_inclusive'] is False
    assert c['physical_domain']['lower_inclusive'] is False


def test_synthetic_activity_means_remain_fixture_partials_in_a_nonsynthetic_request():
    args,rows,sources=setup();args['source_kind']='primary_source'
    _,s=calculate(args,rows,sources)
    assert s['cells']['preferred_activity']['value']==.9 and s['cells']['preferred_activity']['origin']=='synthetic'
    assert s['cells']['activity_ratio']['value'] is None
    assert s['cells']['activity_ratio']['origin']=='synthetic'
    assert 'synthetic_activity_for_nonsynthetic_selection' in s['cells']['activity_ratio']['unavailable_reasons']


def test_whole_physical_activity_aliases_across_distinct_sheets_are_not_two_ions():
    args,rows,sources=setup(.9,.9)
    rows[1]['dependencies']=deepcopy(rows[0]['dependencies'])
    args,sources,_=covariance(args,rows,sources,[[.01,0],[0,.01]])
    e,s=calculate(args,rows,sources)
    assert s['cells']['activity_ratio']['value'] is None
    assert 'reused_activity_not_ion_discrimination' in s['cells']['activity_ratio']['unavailable_reasons']
    assert e['covariance']['status']=='shared_activity_covariance_inconsistent'
    rows[1]['value']=.15
    _,s=calculate(args,rows,sources)
    assert 'shared_activity_estimator_inconsistent' in s['cells']['activity_ratio']['unavailable_reasons']
    assert s['cells']['alternative_activity']['value']==.15


def test_shared_normalizer_subset_does_not_make_distinct_ion_activities_aliases():
    args,rows,sources=setup()
    rows[1]['dependencies'][3]=deepcopy(rows[0]['dependencies'][3])
    _,s=calculate(args,rows,sources)
    assert s['cells']['activity_ratio']['value']==6
    assert s['cells']['activity_ratio_variance']['value'] is None
    assert s['cells']['activity_ratio']['origin']=='synthetic'
    assert all(d['origin']=='synthetic' for d in s['cells']['activity_ratio']['dependencies'])
