"""Authenticated synthetic sources and bounded parent-converted original binding.

These cases exercise implemented readers/calculators, not the plan illustrations.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_measurement_comparison_inputs import (
    read_measurement_comparison_inputs, compile_measurement_comparison_inputs,
    validate_measurement_comparison_extraction, validate_measurement_comparison_calculation_inputs,
    measurement_comparison_selection_schema, measurement_comparison_extraction_schema,
    measurement_comparison_calculation_inputs_schema, measurement_comparison_covariance_schema,
)
from gene_annotation_episode.literature_measurement_comparison_calculations import (
    populate_measurement_comparison, validate_measurement_comparison_sheet,
    measurement_comparison_sheet_schema,
)
from gene_annotation_episode.literature_measurement_comparison_prompt import MEASUREMENT_COMPARISON_TASK
from gene_annotation_episode.domain import validate_schema

ROOT=Path(__file__).resolve().parents[1]
PACKET=ROOT/'verification/a105_measurement_comparison_components_258'
ROLES=('left','right','epsilon_signal','epsilon_nuisance','nuisance')


def exact(x):
    x=Fraction(x);return {'numerator':str(x.numerator),'denominator':str(x.denominator)}


def source_fixture(values=None, *, approximate=False, table=False, optical=False, defined=False):
    values={'left':'20','right':'22'} if values is None else values
    parts=[]
    def span(text):
        start=len(''.join(parts).encode());parts.append(text)
        return dict(start=start,end=start+len(text.encode()),quote=text)
    context=span('<p>Declared synthetic source: same construct and denominator; common unbiased estimate model is supported only inside this synthetic example. Three preparations.</p>')
    records={};units={};row={};label={};endpoints={};definitions={}
    def inside(w,text):
        a=w['quote'].index(text);return dict(start=w['start']+len(w['quote'][:a].encode()),end=w['start']+len(w['quote'][:a+len(text)].encode()),quote=text)
    if table:
        span('<table><tr><th>construct</th><th>')
        heading=span('rate (umol/min/mg)');span('</th></tr>')
    for role,val in values.items():
        endpoint='NADH' if role in ('left','epsilon_signal') else 'ferredoxin' if role in ('right','epsilon_nuisance','nuisance') else role
        if table:
            span('<tr><td>');row[role]=span(role);span('</td><td>');records[role]=span(str(val));span('</td></tr>')
            label[role]=inside(heading,'rate');units[role]=inside(heading,'umol/min/mg');endpoints[role]=context
        else:
            unit='mM^-1cm^-1' if role.startswith('epsilon') else 'U/mg' if defined else 'umol/min/mg'
            text=role+' '+endpoint+' rate '+('approximately ' if approximate else '')+str(val)+' '+unit+'.'
            span('<p>');records[role]=span(text);span('</p>')
            row[role]=inside(records[role],role);label[role]=inside(records[role],'rate');units[role]=inside(records[role],unit);endpoints[role]=inside(records[role],endpoint)
        if defined and not role.startswith('epsilon'):
            span('<p>');definitions[role]=span('One unit was equivalent to 1 umol of '+endpoint+' per min.');span('</p>')
    if table:span('</table>')
    content=''.join(parts).encode();digest=hashlib.sha256(content).hexdigest();ref='source_'+digest;artifact='artifact_'+digest
    def w(x):return dict(source_ref=ref,representation='original',**x)
    def M(value):return dict(value=value,witnesses=[] if value in ('unknown','unreported') else [w(context)])
    def number(role):
        val=str(values[role]);text=records[role]['quote'];a=text.index(val)
        if val.startswith(('< ','> ')): a+=2;val=val[2:]
        return dict(witness=w(records[role]),number_start=a,number_end=a+len(val))
    original=json.loads((PACKET/'NFN_PARENT_CONVERSION_SELECTION_ILLUSTRATION_001.json').read_text())
    selection=deepcopy(original);selection.update(source_ref=ref,source_kind='synthetic_fixture',optical=None,common_model=None,covariance_source_refs=[])
    selection['assertion']=dict(question='quantitative_activity',molecule=w(context),functional_assertion=w(context))
    for role in ROLES:
        if role not in values:selection['quantities'][role]=None;continue
        q=deepcopy(original['quantities']['left'])
        q.update(layout='table' if table else 'labelled_record',record=None if table else w(records[role]),number=number(role),row_label=w(row[role]),quantity_label=w(label[role]),unit=w(units[role]),
            quantity_kind=M('extinction_coefficient' if role.startswith('epsilon') else 'specific_activity'),estimator_scale=M('parameter_estimate' if role.startswith('epsilon') else 'reported_mean'),semantics=M('reported_nondetection' if str(values[role])=='ND' else 'reported_point_estimate'),qualification=M('source_qualified_approximate' if approximate else 'reported_point'),normalization=M('extinction_unit' if role.startswith('epsilon') else 'protein_mass'),physical_identity=None,dependency_witnesses=[])
        q['subject']={k:w(context) if k in ('construct','molecule') else None for k in q['subject']}
        q['assay']={k:w(context) if k in ('conditions','assay','fit_basis','preparation','denominator') else None for k in q['assay']};q['assay']['direct_endpoint']=w(endpoints[role])
        q['uncertainty']=dict(statistic=M('unreported'),magnitude=None,interval=None,confidence_level=None,unit=None,unit_relationship=M('unknown'),count=None,repetition_basis=M('unknown'),estimate_basis=M('unknown'))
        if defined and not role.startswith('epsilon'):
            dw=definitions[role];entity=endpoints[role]['quote'];a=dw['quote'].index('1')
            q['unit']=dict(kind='source_defined_rate_unit',witness=w(units[role]),definition=dict(bridge=w(dw),clause=w(inside(dw,'1 umol of '+entity+' per min')),amount=dict(witness=w(dw),number_start=a,number_end=a+1),amount_unit=w(inside(dw,'umol')),time_unit=w(inside(dw,'min')),endpoint=w(endpoints[role]),endpoint_entity=w(endpoints[role]),definition_entity=w(inside(dw,entity))))
        selection['quantities'][role]=q
    rel={'construct':'same_construct_supported','preparation':'same_preparation_supported','preparation_target':'same_population_estimand_supported','protocol':'matched_except_intended_change','endpoint':'same_quantity','denominator':'same_basis_supported','functional_bearing':'same_quantitative_assertion','attribution':'unknown','sampling':'independence_not_established','systematic_coverage':'not_established','left_validity':'endpoint_quantification_supported','right_validity':'endpoint_quantification_supported','left_readout_isolation':'isolated_signal_supported','right_readout_isolation':'isolated_signal_supported'}
    selection['relationships']={k:M(v) for k,v in rel.items()}
    selection['common_quantity']=dict(label=w(context),unit='umol/min/mg')
    for r in ('left','right'):
        selection['common_quantity'][r+'_conversion']=dict(kind='identity',direction=M('same_direction_supported'),support_status=M('supported'),reaction=None,endpoint_species=w(context),common_species=w(context),endpoint_coefficient=None,common_coefficient=None)
    selection['common_model']=dict(kind='common_unbiased_quantity',applicability=M('supported'),variance_interpretation='known_joint_estimator_covariance',combination='generalized_least_squares')
    if optical:
        selection['optical']=dict(signal_role='left',observation_equation='y=h+s*alpha*f',nuisance_sign=-1,sign_support=[w(context)],raw_optical_relation=M('supported'),coefficient_applicability=M('supported'),estimate_scale_applicability=M('supported'),nuisance_quantity_linkage=M('supported'),scenario=dict(kind='required_interference_on_selected_report_scale',anchor_role='right',common_rate_equality=M('stipulated_sensitivity'),linear_mixture_on_estimate_scale=M('stipulated_sensitivity')))
    sources={(ref,'original'):dict(artifact_ref=artifact,content=content)}
    def read(reference,representation):return deepcopy(sources[(reference,representation)])
    return selection,sources,read


def bind_covariance(selection,sources,read,matrix,*,roles=('left','right'),status='known',derivation='synthetic_model'):
    base=deepcopy(selection);base['covariance_source_refs']=[]
    data=read_measurement_comparison_inputs(base,read_source=read)
    q={r:data['quantities'][r]['value'] for r in roles}
    document=dict(version='a105_measurement_comparison_covariance_v1',roles=list(roles),owner_keys=[q[r]['owner_key'] for r in roles],units=[q[r]['canonical_unit'] for r in roles],dependency_keys=[q[r]['dependency_keys'] for r in roles],covariance=matrix,basis='joint_covariance_of_selected_estimates',variance_status=status,origin='synthetic',systematic_coverage='included_as_declared',derivation=derivation)
    content=(json.dumps(document,separators=(',',':'))+'\n').encode();h=hashlib.sha256(content).hexdigest();ref='source_'+h
    sources[(ref,'original')]=dict(artifact_ref='artifact_'+h,content=content)
    selection['covariance_source_refs'].append(ref)
    if selection['common_model'] is not None:selection['common_model']['variance_interpretation']=status+'_joint_estimator_covariance' if status!='unknown' else 'unknown'
    return document,ref


def execute(selection,read):
    extraction=read_measurement_comparison_inputs(selection,read_source=read)
    inputs=compile_measurement_comparison_inputs(extraction)
    sheet=populate_measurement_comparison(inputs)
    validate_measurement_comparison_sheet(sheet,inputs=inputs)
    return extraction,inputs,{c['component']:c for c in sheet['cells']},sheet


def test_exact_reviewed_schema_resources_and_task():
    for name,factory in [('SELECTION',measurement_comparison_selection_schema),('EXTRACTION',measurement_comparison_extraction_schema),('CALCULATION_INPUTS',measurement_comparison_calculation_inputs_schema),('SHEET',measurement_comparison_sheet_schema),('COVARIANCE_DOCUMENT',measurement_comparison_covariance_schema)]:
        assert factory()==json.loads((PACKET/(name+'_SCHEMA_003.json')).read_text())
    assert hashlib.sha256(MEASUREMENT_COMPARISON_TASK.encode()).hexdigest()=='cd98aa8e5208a0b1c7f2d0b67c3e522589313474a52f613be157f8985577382e'


def test_authenticated_reader_detachment_common_covariance():
    s,docs,read=source_fixture();bind_covariance(s,docs,read,[[4,1],[1,9]])
    e,i,c,sheet=execute(s,read)
    assert c['protocol_difference']['exact_value']==exact(-2)
    for name,value in [('difference_variance',11),('weight_left',Fraction(8,11)),('weight_right',Fraction(3,11)),('combined_estimate',Fraction(226,11)),('combined_variance',Fraction(35,11)),('squared_standardized_difference',Fraction(4,11))]:assert c[name]['exact_value']==exact(value)
    assert c['standardized_difference']['value']==pytest.approx(-2/math.sqrt(11))
    assert sheet['relationship_meanings']['attribution']=='unknown'
    # Compilation/calculation after source access is removed is fully detached.
    docs.clear();assert populate_measurement_comparison(compile_measurement_comparison_inputs(e))==sheet
    s['requested_cells'].clear();assert len(i['selection']['requested_cells'])>0


@pytest.mark.parametrize('status',('known','estimated'))
@pytest.mark.parametrize('v',(0,4))
@pytest.mark.parametrize('right',(20,22))
def test_singular_partials_known_versus_plugin(status,v,right):
    s,docs,read=source_fixture({'left':'20','right':str(right)});bind_covariance(s,docs,read,[[v,v],[v,v]],status=status)
    _,_,c,_=execute(s,read)
    assert c['difference_variance']['exact_value']==exact(0)
    assert c['difference_standard_uncertainty']['value']==0
    assert c['weight_left']['value'] is None and c['standardized_difference']['value'] is None
    if right==20:
        assert c['combined_estimate']['value']==20
        assert c['combined_variance']['value']==v
        assert c['combined_standard_uncertainty']['value']==math.sqrt(v)
        assert c['weight_left']['reasons']['domain']==['nonunique_gls_weights']
    elif status=='known':assert 'inconsistent_deterministic_constraint' in c['combined_estimate']['reasons']['domain']
    else:
        assert c['standardized_difference']['reasons']['domain']==['zero_plugin_difference_variance']
        assert c['combined_estimate']['reasons']['domain']==['combined_estimate_not_identified_by_plugin_covariance']
        assert all('inconsistent_deterministic_constraint' not in x['reasons']['domain'] for x in c.values())


def test_descriptive_variance_does_not_need_common_mean():
    s,docs,read=source_fixture();s['common_model']=None;s['relationships']['protocol']['value']='additional_differences'
    bind_covariance(s,docs,read,[[4,1],[1,9]])
    _,_,c,_=execute(s,read)
    assert c['difference_variance']['value']==11
    assert c['difference_standard_uncertainty']['value']==pytest.approx(math.sqrt(11))
    assert c['standardized_difference']['value'] is None and c['combined_estimate']['value'] is None


def test_signed_optical_correction_full_joint_covariance():
    s,docs,read=source_fixture({'left':'8','right':'23','epsilon_signal':'1.2','epsilon_nuisance':'8.6','nuisance':'2'},optical=True)
    roles=('left','epsilon_nuisance','epsilon_signal','nuisance')
    C=[[4,0,0,-1],[0,1,0,0],[0,0,1,0],[-1,0,0,1]]
    bind_covariance(s,docs,read,C,roles=roles)
    _,_,c,sheet=execute(s,read)
    alpha=Fraction(43,6);assert c['spectral_multiplier']['exact_value']==exact(alpha)
    assert c['corrected_estimate']['exact_value']==exact(8+alpha*2)
    J=[Fraction(1),Fraction(5,3),-Fraction(215,18),alpha]
    expected=sum(J[a]*C[a][b]*J[b] for a in range(4) for b in range(4))
    assert c['corrected_estimate_variance']['exact_value']==exact(expected)
    assert sheet['relationship_meanings']['attribution']=='unknown'
    assert c['required_nuisance_equivalent_scenario']['conditional_exact_value']==exact(Fraction(90,43))


def test_missing_nuisance_and_fitted_scale_need_both_stipulations():
    s,docs,read=source_fixture({'left':'8','right':'23','epsilon_signal':'1.2','epsilon_nuisance':'8.6'},optical=True,approximate=True,defined=True)
    s['optical']['estimate_scale_applicability']={'value':'unknown','witnesses':[]}
    s['optical']['nuisance_quantity_linkage']={'value':'unknown','witnesses':[]}
    for r in ('left','right'):s['quantities'][r]['estimator_scale']['value']='fitted_asymptote';s['quantities'][r]['quantity_kind']['value']='apparent_specific_activity'
    _,_,c,_=execute(s,read)
    assert c['protocol_ratio']['exact_value']==exact(Fraction(8,23))
    assert c['spectral_multiplier']['exact_value']==exact(Fraction(43,6))
    assert c['corrected_estimate']['value'] is None
    assert c['required_nuisance_equivalent_scenario']['conditional_exact_value']==exact(Fraction(90,43))
    for name in ('common_rate_equality','linear_mixture_on_estimate_scale'):
        bad=deepcopy(s);bad['optical']['scenario'][name]={'value':'unknown','witnesses':[]}
        _,_,cc,_=execute(bad,read)
        assert cc['required_nuisance_equivalent_scenario']['conditional_value'] is None


@pytest.mark.parametrize('token,expected', [('ND','native_nondetection_not_point'),('< 3','bounded_arithmetic_unimplemented'),('3 to 5','range_arithmetic_unimplemented')])
def test_native_limits_and_missing_parts(token,expected):
    s,docs,read=source_fixture({'left':token})
    _,_,c,_=execute(s,read)
    assert expected in sum((v for v in c['converted_left']['reasons'].values()),[])
    assert c['native_right']['value'] is None
    assert c['protocol_ratio']['value'] is None


def test_table_row_and_source_association():
    s,docs,read=source_fixture(table=True)
    execute(s,read)
    bad=deepcopy(s);bad['quantities']['left']['row_label']=bad['quantities']['right']['row_label']
    with pytest.raises(ExperimentalContractError,match='comparison_source_row_mismatch'):execute(bad,read)


@pytest.mark.parametrize('C,reason', [([[1,2],[2,1]],'covariance_not_positive_semidefinite'),([[4,1],[2,9]],'covariance_not_symmetric'),([[4,1],[1]],'covariance_invalid_shape')])
def test_invalid_covariance_keeps_native_and_descriptive(C,reason):
    s,docs,read=source_fixture();bind_covariance(s,docs,read,C)
    _,_,c,_=execute(s,read)
    assert c['native_left']['value']==20 and c['protocol_difference']['value']==-2
    assert reason in c['difference_variance']['reasons']['domain']


def test_negative_covariance_and_valid_negative_weights():
    for C in ([[4,-1],[-1,9]],[[1,1.5],[1.5,4]]):
        s,docs,read=source_fixture();bind_covariance(s,docs,read,C)
        _,_,c,_=execute(s,read)
        assert c['combined_estimate']['value'] is not None
    assert c['weight_right']['value']==-.25


def test_shared_random_variance_is_retained():
    s,docs,read=source_fixture();bind_covariance(s,docs,read,[[20,17],[17,25]])
    _,_,c,_=execute(s,read)
    assert c['difference_variance']['value']==11
    assert c['combined_estimate']['exact_value']==exact(Fraction(226,11))
    assert c['combined_variance']['exact_value']==exact(Fraction(211,11))


def original_nfn_fixture():
    """Mechanical binding of root257's assigned meanings; no new interpretation.

    The nine existing selectors and root conversion supply the identities. Same
    row condition labels are kept distinct from separate assay/construct context.
    """
    base=ROOT/'research/experimental_scoring_review_2026-10-23/a110_chemical_sheet_016/sources'
    html_bytes=(base/'PMC2944534.html').read_bytes();text_bytes=(base/'PMC2944534.txt').read_bytes()
    assert hashlib.sha256(html_bytes).hexdigest()=='056f3c93bce434f3d45a21185d8c7b36a13664778f9a8f537b3024fedaa409fa'
    assert hashlib.sha256(text_bytes).hexdigest()=='32477da75c460b593002d2216243789594d2dff0ad1cc87d75801ae84d88814d'
    review=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_matched_assay_consistency_review_257'
    review_bytes=(review/'ROOT_SCIENTIFIC_REVIEW_001.md').read_bytes()
    clarification=(review/'ROOT_SCIENTIFIC_CLARIFICATION_002.md').read_bytes()
    docs={}
    def add(raw):
        h=hashlib.sha256(raw).hexdigest();ref='source_'+h
        docs[(ref,'original')]=dict(artifact_ref='artifact_'+h,content=raw);return ref
    href,tref,rref,cref=map(add,(html_bytes,text_bytes,review_bytes,clarification))
    def w(ref,a,z):return dict(source_ref=ref,representation='original',start=a,end=z,quote=docs[(ref,'original')]['content'][a:z].decode())
    def find(ref,text,*,start=0,end=None):
        raw=docs[(ref,'original')]['content'];token=text.encode();a=raw.index(token,start,len(raw) if end is None else end);return w(ref,a,a+len(token))
    def inside(record,text):return find(record['source_ref'],text,start=record['start'],end=record['end'])
    selectors=json.loads((ROOT/'research/experimental_scoring_review_2026-10-23/a105_matched_assay_consistency_case_255/SOURCE_SELECTORS_001.json').read_text())
    selected={s['id']:s for s in selectors}
    for s in selectors:
        raw=(ROOT/s['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==s['source_sha256'];assert raw[s['start']:s['end']].decode()==s['quote']
    method=selected['assay_methods'];methods=w(tref,method['start'],method['end'])
    source_validity=selected['source_results_and_validity'];validity=w(tref,source_validity['start'],source_validity['end'])
    construct_section=selected['construct_and_preparation'];construct_context=w(tref,construct_section['start'],construct_section['end'])
    organism=inside(construct_context,'C. kluyveri\nDSM 555')
    ca=text_bytes.index(b'nfnAB\nwith both an',construct_context['start']);cz=text_bytes.index(b'.',ca)+1
    construct=w(tref,ca,cz)
    molecule=inside(construct_context,'NfnAB')
    fit=find(href,'Extrapolated from Lineweaver-Burk plots and rounded.')
    hhead=find(href,'Apparent <em>V</em><sub>max</sub> (U/mg)',start=84000,end=85000)
    unit=inside(hhead,'U/mg')
    parent_reaction=find(rref,'Reaction5 links one two-electron ferredoxin and one NADH per two NADPH in its\nbackward direction.')
    stip_start=clarification.index(b'Consequently');stip_end=clarification.index(b'Actual f',stip_start)
    stip=w(cref,stip_start,stip_end)
    parent_context=w(rref,0,len(review_bytes))
    def M(value,spans=None):return dict(value=value,witnesses=[] if value=='unknown' else [parent_reaction] if spans is None else spans)
    s=deepcopy(json.loads((PACKET/'NFN_PARENT_CONVERSION_SELECTION_ILLUSTRATION_001.json').read_text()))
    s.update(source_ref=href,source_kind='primary_source',covariance_source_refs=[],common_model=None)
    s['assertion']=dict(question='quantitative_activity',molecule=molecule,functional_assertion=parent_reaction)
    s['quantities']={r:None for r in ROLES}
    for role,sid,entity in (('left','NADH_Vmax_with_Fdox','NADH'),('right','Fd_Vmax_with_NAD','ferredoxin')):
        selector=selected[sid];a,z=selector['start'],selector['end'];number=dict(witness=w(href,a,z),number_start=0,number_end=z-a)
        rowstart=html_bytes.rfind(b'<tr>',0,a);rowend=html_bytes.index(b'</tr>',a)+5
        import re
        cells=list(re.finditer(rb'<td\b[^>]*>(.*?)</td>',html_bytes[rowstart:rowend],re.S))
        rowlabel=w(href,rowstart+cells[1].start(1),rowstart+cells[1].end(1))
        prefix='Formation of 1 μmol of NADH per min was defined as representing 1 unit.' if role=='left' else 'Reduction of 1 μmol of ferredoxin per min was defined as representing 1 unit.'
        bridge=inside(methods,prefix);clause=inside(bridge,'1 μmol of '+entity+' per min');amount=inside(clause,'1')
        endpoint=inside(clause,entity)
        proto_start=text_bytes.rfind(b'\n',methods['start'],bridge['start'])
        # The assigned assay definition and endpoint come from the exact bridge;
        # broader source method custody is kept separately, without fitted raw data.
        q=deepcopy(json.loads((PACKET/'NFN_PARENT_CONVERSION_SELECTION_ILLUSTRATION_001.json').read_text())['quantities'][role])
        q.update(layout='table',record=None,number=number,row_label=rowlabel,quantity_label=hhead,
            unit=dict(kind='source_defined_rate_unit',witness=unit,definition=dict(bridge=bridge,clause=clause,amount=dict(witness=amount,number_start=0,number_end=1),amount_unit=inside(clause,'μmol'),time_unit=inside(clause,'min'),endpoint=endpoint,endpoint_entity=endpoint,definition_entity=endpoint)),
            quantity_kind=M('apparent_specific_activity',[hhead]),estimator_scale=M('fitted_asymptote',[fit]),semantics=M('reported_point_estimate',[number['witness']]),qualification=M('rounded_after_fit',[fit]),normalization=M('protein_mass',[unit]),physical_identity=None,dependency_witnesses=[])
        q['subject']={k:None for k in q['subject']};q['subject'].update(organism=organism,molecule=molecule,construct=construct,expression_host=inside(construct_context,'E. coli'))
        q['assay']={k:None for k in q['assay']};q['assay'].update(assay=bridge,conditions=methods,direct_endpoint=endpoint,inferred_quantity=hhead,denominator=unit,fit_basis=fit)
        q['uncertainty']=dict(statistic=M('unreported',[]),magnitude=None,interval=None,confidence_level=None,unit=None,unit_relationship=M('unknown'),count=None,repetition_basis=M('unknown'),estimate_basis=M('unknown'))
        s['quantities'][role]=q
    for role,token in (('epsilon_signal','1.2'),('epsilon_nuisance','8.6')):
        n=inside(validity,token);a=n['start'];raw=text_bytes
        if role=='epsilon_signal':
            start=raw.rfind(b'380 nm',validity['start'],a);end=raw.index(b')',a)+1;record=w(tref,start,end);rowlabel=inside(record,'380 nm');label=inside(record,'ɛ')
        else:
            start=raw.rfind(b'ferredoxin reduction',validity['start'],a);end=raw.index(b')',a)+1;record=w(tref,start,end);rowlabel=inside(record,'ferredoxin reduction');label=inside(record,'Δɛ\nox-red')
        u=inside(record,'mM\n−1\ncm\n−1')
        q=deepcopy(s['quantities']['left']);q.update(layout='labelled_record',record=record,number=dict(witness=n,number_start=0,number_end=len(token)),row_label=rowlabel,quantity_label=label,unit=u,
            quantity_kind=M('extinction_coefficient',[record]),estimator_scale=M('parameter_estimate',[record]),semantics=M('reported_point_estimate',[record]),qualification=M('source_qualified_approximate',[record]),normalization=M('extinction_unit',[u]))
        q['assay']={k:None for k in q['assay']};q['assay'].update(assay=validity,conditions=record,direct_endpoint=rowlabel,inferred_quantity=label)
        s['quantities'][role]=q
    rel=dict(construct='same_construct_supported',preparation='unknown',preparation_target='unknown',protocol='additional_differences',endpoint='fixed_reaction_conversion',denominator='same_basis_supported',functional_bearing='existence_only',attribution='unknown',sampling='independence_not_established',systematic_coverage='identified_unresolved',left_validity='identified_unresolved_interference',right_validity='endpoint_quantification_supported',left_readout_isolation='mixed_optical_contributions',right_readout_isolation='isolated_signal_supported')
    s['relationships']={k:M(v,[validity] if k in ('functional_bearing','systematic_coverage','left_validity','left_readout_isolation') else [methods] if k=='protocol' else [construct] if k=='construct' else None) for k,v in rel.items()}
    s['common_quantity']=dict(label=parent_reaction,unit='umol/min/mg')
    for role in ('left','right'):
        coefficient=dict(origin='implicit_unit_coefficient',number=None,implicit_value=exact(1),support=[parent_reaction])
        s['common_quantity'][role+'_conversion']=dict(kind='fixed_reaction_scale',direction=M('same_direction_supported'),support_status=M('supported'),reaction=parent_reaction,endpoint_species=s['quantities'][role]['assay']['direct_endpoint'],common_species=parent_reaction,endpoint_coefficient=deepcopy(coefficient),common_coefficient=deepcopy(coefficient))
    s['optical']=dict(signal_role='left',observation_equation='y=h+s*alpha*f',nuisance_sign=-1,sign_support=[validity],raw_optical_relation=M('supported',[validity]),coefficient_applicability=M('supported',[validity]),estimate_scale_applicability=M('unknown'),nuisance_quantity_linkage=M('unknown'),scenario=dict(kind='required_interference_on_selected_report_scale',anchor_role='right',common_rate_equality=M('stipulated_sensitivity',[stip]),linear_mixture_on_estimate_scale=M('stipulated_sensitivity',[stip])))
    def read(reference,representation):return deepcopy(docs[(reference,representation)])
    return s,docs,read


def test_actual_original_nfn_mechanical_binding():
    s,docs,read=original_nfn_fixture();e,i,c,sheet=execute(s,read)
    assert c['native_left']['value']==8 and c['native_right']['value']==23
    assert c['native_left']['origin']=='reported'
    assert c['protocol_ratio']['exact_value']==exact(Fraction(8,23))
    assert c['protocol_difference']['value']==-15
    assert c['spectral_multiplier']['exact_value']==exact(Fraction(43,6))
    assert c['spectral_multiplier']['origin']=='derived'
    assert c['corrected_estimate']['value'] is None
    assert c['difference_variance']['value'] is None
    assert c['standardized_difference']['value'] is None
    assert c['required_nuisance_equivalent_scenario']['conditional_exact_value']==exact(Fraction(90,43))
    assert c['required_nuisance_equivalent_scenario']['approximate']
    assert e['quantities']['left']['selection']['row_label']['start'] < 86458
    assert e['quantities']['left']['value']['estimator_scale']=='fitted_asymptote'
    docs.clear();assert populate_measurement_comparison(i)==sheet


def test_detached_records_reject_meaning_unit_owner_and_covariance_tampering():
    s,docs,read=source_fixture();bind_covariance(s,docs,read,[[4,1],[1,9]])
    e,i,c,sheet=execute(s,read)
    mutations=[lambda x:x['quantities']['left'].update(canonical_value=21,canonical_exact=exact(21)),
        lambda x:x['quantities']['left'].update(physical_owner_key='invented'),
        lambda x:x['relationships']['protocol'].update(value='additional_differences'),
        lambda x:x['conversions']['left'].update(multiplier_exact=exact(2)),
        lambda x:x['covariance_blocks'][0]['matrix_exact'][0].__setitem__(0,exact(5))]
    for mutate in mutations:
        bad=deepcopy(i);mutate(bad)
        with pytest.raises(ExperimentalContractError):validate_measurement_comparison_calculation_inputs(bad)
    bad=deepcopy(e);bad['quantities']['left']['value']['canonical_value']=21;bad['quantities']['left']['value']['canonical_exact']=exact(21)
    with pytest.raises(ExperimentalContractError):validate_measurement_comparison_extraction(bad)
    bad=deepcopy(sheet);next(c for c in bad['cells'] if c['component']=='combined_estimate')['value']=999
    with pytest.raises(ExperimentalContractError):validate_measurement_comparison_sheet(bad,inputs=i)


def test_original_source_rejects_wrong_endpoint_unit_and_continuation_row():
    s,docs,read=original_nfn_fixture()
    bad=deepcopy(s);bad['quantities']['left']['unit']['definition']['endpoint']=s['quantities']['right']['assay']['direct_endpoint']
    with pytest.raises(ExperimentalContractError,match='endpoint_mismatch'):execute(bad,read)
    bad=deepcopy(s);bad['quantities']['left']['unit']['definition']['definition_entity']=s['quantities']['right']['unit']['definition']['definition_entity']
    with pytest.raises(ExperimentalContractError,match='defined_unit_'):execute(bad,read)
    bad=deepcopy(s);bad['quantities']['left']['unit']['witness']=s['quantities']['epsilon_signal']['unit']
    with pytest.raises(ExperimentalContractError):execute(bad,read)
    bad=deepcopy(s);bad['quantities']['left']['row_label']=s['quantities']['right']['row_label']
    with pytest.raises(ExperimentalContractError,match='comparison_source_row_mismatch'):execute(bad,read)


def test_signed_coefficient_and_estimated_optical_uncertainty():
    s,docs,read=source_fixture({'left':'8','right':'23','epsilon_signal':'1.2','epsilon_nuisance':'-8.6','nuisance':'2'},optical=True)
    roles=('left','epsilon_nuisance','epsilon_signal','nuisance');bind_covariance(s,docs,read,[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],roles=roles,status='estimated')
    _,_,c,_=execute(s,read)
    assert c['spectral_multiplier']['exact_value']==exact(Fraction(-43,6))
    assert c['corrected_estimate']['exact_value']==exact(Fraction(-19,3))
    assert c['corrected_estimate_variance']['interpretation']=='first_order_estimated_input_covariance'
    assert c['corrected_estimate_variance']['uncertainty']['variance_status']=='estimated'


def test_nuisance_normalization_and_fitted_applicability_are_specific_failures():
    s,docs,read=source_fixture({'left':'8','right':'23','epsilon_signal':'1.2','epsilon_nuisance':'8.6','nuisance':'2'},optical=True)
    s['optical']['estimate_scale_applicability']={'value':'unknown','witnesses':[]}
    _,_,c,_=execute(s,read)
    assert c['corrected_estimate']['value'] is None
    assert 'estimate_scale_model_unknown' in c['corrected_estimate']['reasons']['relationship']
    assert c['spectral_multiplier']['value'] is not None and c['protocol_ratio']['value'] is not None
    s['quantities']['nuisance']['normalization']['value']='active_molecule_amount'
    _,_,c,_=execute(s,read)
    assert 'denominator_not_common' in c['corrected_estimate']['reasons']['relationship']


def test_exact_large_integer_covariance_symmetry_before_float_rounding():
    s,docs,read=source_fixture()
    huge=2**60
    bind_covariance(s,docs,read,[[huge*2,huge],[huge+1,huge*2]])
    _,_,c,_=execute(s,read)
    assert c['protocol_difference']['value']==-2
    assert 'covariance_not_symmetric' in c['difference_variance']['reasons']['domain']


def test_unknown_covariance_and_marginals_do_not_create_cross_terms():
    s,docs,read=source_fixture();bind_covariance(s,docs,read,[[4,1],[1,9]],status='unknown')
    _,_,c,_=execute(s,read)
    assert 'covariance_status_unknown' in c['difference_variance']['reasons']['source']
    s['covariance_source_refs']=[];s['common_model']['variance_interpretation']='known_joint_estimator_covariance'
    bind_covariance(s,docs,read,[[4]],roles=('left',));bind_covariance(s,docs,read,[[9]],roles=('right',))
    _,_,c,_=execute(s,read)
    assert 'joint_covariance_incomplete' in c['difference_variance']['reasons']['source']


def test_conflicting_covariance_blocks_preserve_points_and_discrepancy():
    s,docs,read=source_fixture();bind_covariance(s,docs,read,[[4,1],[1,9]]);bind_covariance(s,docs,read,[[5,1],[1,9]])
    _,_,c,_=execute(s,read)
    assert c['protocol_difference']['value']==-2
    assert 'covariance_overlap_conflict' in c['difference_variance']['reasons']['domain']


def test_invalid_covariance_json_shape_and_owner_units_are_partial():
    for mutation in (lambda d:d.update(owner_keys=3),lambda d:d.update(units=['per_min','per_min']),lambda d:d.update(covariance=[[True,0],[0,1]])):
        s,docs,read=source_fixture();doc,ref=bind_covariance(s,docs,read,[[4,1],[1,9]])
        mutation(doc);raw=json.dumps(doc).encode();h=hashlib.sha256(raw).hexdigest();newref='source_'+h;docs[(newref,'original')]=dict(artifact_ref='artifact_'+h,content=raw);s['covariance_source_refs']=[newref]
        _,_,c,_=execute(s,read)
        assert c['native_left']['value']==20 and c['difference_variance']['value'] is None
    s,docs,read=source_fixture();raw=b'{"version":1,"version":2}';h=hashlib.sha256(raw).hexdigest();ref='source_'+h;docs[(ref,'original')]=dict(artifact_ref='artifact_'+h,content=raw);s['covariance_source_refs']=[ref]
    _,_,c,_=execute(s,read);assert c['difference_variance']['reasons']['domain']==['covariance_json_invalid']


def test_shared_measurement_aliases_do_not_gain_independence():
    s,docs,read=source_fixture({'left':'20','right':'20'})
    s['quantities']['right']=deepcopy(s['quantities']['left'])
    s['relationships']['sampling']['value']='shared_physical_estimate'
    bind_covariance(s,docs,read,[[4,4],[4,4]])
    _,_,c,sheet=execute(s,read)
    assert c['combined_variance']['value']==4
    assert c['combined_estimate']['value']==20
    assert c['weight_left']['value'] is None
    assert any(d['relation']=='shared_primitive' for d in sheet['dependence'])
    assert c['protocol_ratio']['contribution_key']==c['protocol_log_ratio']['contribution_key']==c['combined_estimate']['contribution_key']


def test_extreme_ratio_keeps_log_and_individual_finite_results():
    s,docs,read=source_fixture({'left':'1e300','right':'1e-300'})
    _,_,c,_=execute(s,read)
    assert c['native_left']['value']==1e300 and c['native_right']['value']==1e-300
    assert c['protocol_ratio']['value'] is None
    assert c['protocol_ratio']['reasons']['implementation']==['numerical_model_range']
    assert c['protocol_log_ratio']['value']==pytest.approx(600*math.log(10))


def test_supported_count_is_retained_but_does_not_supply_covariance():
    s,docs,read=source_fixture()
    w=s['quantities']['left']['subject']['construct'];a=w['quote'].index('Three')
    s['quantities']['left']['uncertainty'].update(count=dict(witness=w,number_start=a,number_end=a+5),repetition_basis=dict(value='independent_preparations',witnesses=[w]))
    e,_,c,_=execute(s,read)
    assert e['quantities']['left']['count_reading']['exact_count']==3
    assert c['difference_variance']['value'] is None
    assert 'covariance_not_supplied' in c['difference_variance']['reasons']['source']


def test_source_authentication_and_clipped_numeric_token_rejected():
    s,docs,read=source_fixture();ref=s['source_ref'];docs[(ref,'original')]['content']+=b' changed'
    with pytest.raises(ExperimentalContractError,match='comparison_source_artifact_mismatch'):execute(s,read)
    s,docs,read=source_fixture();s['quantities']['left']['number']['number_end']-=1
    with pytest.raises(ExperimentalContractError,match='partial_source_numeric_token'):execute(s,read)


def test_native_nondetection_zero_cannot_be_promoted_by_clearing_reasons():
    s,docs,read=source_fixture({'left':'0','right':'22'})
    s['quantities']['left']['semantics']['value']='reported_nondetection'
    e,i,c,_=execute(s,read)
    assert c['native_left']['value']==0 and c['converted_left']['value'] is None
    i['quantities']['left']['reasons']['source']=[]
    with pytest.raises(ExperimentalContractError,match='comparison_semantic_reason_mismatch'):populate_measurement_comparison(i)


def test_required_signed_interference_does_not_need_spectral_ratio():
    s,docs,read=source_fixture({'left':'8','right':'23'},optical=True)
    _,_,c,_=execute(s,read)
    assert c['required_interference_scenario']['conditional_value']==-15
    assert c['required_nuisance_equivalent_scenario']['conditional_value'] is None


@pytest.mark.parametrize('zero_role',('right','epsilon_signal','epsilon_nuisance'))
def test_zero_domains_preserve_eligible_partials(zero_role):
    values={'left':'8','right':'23','epsilon_signal':'1.2','epsilon_nuisance':'8.6','nuisance':'2'};values[zero_role]='0'
    s,docs,read=source_fixture(values,optical=True)
    _,_,c,_=execute(s,read)
    assert c['native_left']['value']==8
    if zero_role=='right':
        assert c['protocol_difference']['value']==8
        assert c['protocol_ratio']['value'] is None
    elif zero_role=='epsilon_signal':
        assert c['spectral_multiplier']['value'] is None
        assert c['required_interference_scenario']['conditional_value']==-15
    else:
        assert c['spectral_multiplier']['value']==0
        assert c['corrected_estimate']['value']==8
        assert c['required_interference_scenario']['conditional_value']==-15
        assert c['required_nuisance_equivalent_scenario']['conditional_value'] is None
