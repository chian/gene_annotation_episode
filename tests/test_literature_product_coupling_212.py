"""Pure source-grounded endpoint comparisons and explicit synthetic contrasts.

No Store, selected episode, provider/model, controller or credit path is run.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.domain import ContractError, identity, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_product_coupling_inputs import (
    CONTEXT_FIELDS, QUANTITY_MEANINGS, RELATIONSHIPS, _exact,
    read_product_coupling_inputs, product_coupling_population_schema,
    product_coupling_extraction_schema,
)
from gene_annotation_episode.literature_product_coupling_calculations import (
    populate_product_coupling, product_coupling_sheet_schema, COMPONENTS,
)
from gene_annotation_episode.literature_product_coupling_prompt import PRODUCT_COUPLING_TASK

ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_identified_product_scoring_case_207'
TASK=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_identified_product_review_211/TASK_PROPOSAL_001.txt'


class Source:
    def __init__(self,product='2',cofactor='4',reported='50',rate_unit='min<sup>−1</sup>',content=None,kind='synthetic_fixture'):
        self.values=dict(product=product,cofactor=cofactor,reported_coupling=reported)
        self.rate_unit=rate_unit;self.kind=kind
        text=('<article><p>Reference protein Q in buffer pH7.4 at37C. Same molecule and preparation; '
            'matched conditions; compatible normalization. Product chemically identified by standard. '
            'Author assigns endpoints. Reported point estimates. Per assayed molecule. '
            'Fixed one cofactor per product. Uncertain stoichiometry estimate. '
            'Negligible product; not detected. Different preparation. Alternate identity.</p>'
            '<table><thead><tr><th>Product formation</th><th>Cofactor consumption</th><th>Coupling</th></tr>'
            '<tr><th>'+rate_unit+'</th><th>'+rate_unit+'</th><th>%</th></tr></thead>'
            '<tbody><tr><td id="p">'+product+'</td><td id="h">'+cofactor+'</td><td id="r">'+reported+'</td>'
            '</tr></tbody></table></article>')
        self.content=text.encode() if content is None else content
        self.reference=identity('source',{'fixture':'coupling212','hash':hashlib.sha256(self.content).hexdigest()})
        self.artifact='artifact_'+hashlib.sha256(self.content).hexdigest()
        self.extra={};self.aliases=set();self.calls=[]

    def span(self,start,end):
        return {'source_ref':self.reference,'representation':'original','start':start,'end':end,
            'quote':self.content[start:end].decode()}

    def witness(self,text,after=0):
        start=self.content.index(text.encode(),after);return self.span(start,start+len(text.encode()))

    def selector(self,text,after=0):
        return {'witness':self.witness(text,after),'number_start':0,'number_end':len(text)}

    def interpretation(self,value,text=None):
        return {'value':value,'witnesses':[] if text is None else [self.witness(text)]}

    def quantity(self,role):
        index={'product':0,'cofactor':1,'reported_coupling':2}[role]
        tag=('p','h','r')[index]
        label=('Product formation','Cofactor consumption','Coupling')[index]
        header_start=self.content.index(b'<thead>')
        unit_after=self.content.index(b'<tr><th>'+self.rate_unit.encode())
        if role=='cofactor':unit_after=self.content.index(self.rate_unit.encode(),unit_after)+len(self.rate_unit.encode())
        unit=self.witness('%',header_start) if role=='reported_coupling' else self.witness(self.rate_unit,unit_after)
        return {'number':self.selector(self.values[role],self.content.index(('<td id="'+tag+'">').encode())),
            'quantity_label':self.witness(label),'unit':unit,
            'endpoint_role':self.interpretation(('product_formation','cofactor_consumption','coupling_fraction')[index],label),
            'measurement_semantics':self.interpretation('reported_point','Reported point estimates'),
            'normalization':self.interpretation('per_assayed_molecule','Per assayed molecule'),
            'physical_identity':None,'dependency_witnesses':[]}

    def args(self):
        return {'source_ref':self.reference,'source_kind':self.kind,
            'context':{name:None for name in CONTEXT_FIELDS},
            'quantities':{role:self.quantity(role) for role in self.values},
            'relationships':{
                'source_pairing':self.interpretation('author_assigned','Author assigns endpoints'),
                'same_molecule':self.interpretation('same','Same molecule and preparation'),
                'same_preparation':self.interpretation('same','Same molecule and preparation'),
                'normalization':self.interpretation('compatible','compatible normalization'),
                'conditions':self.interpretation('matched','matched conditions'),
                'product_identity':self.interpretation('chemically_identified','Product chemically identified by standard'),
                'molecular_attribution':self.interpretation('unknown')},
            'nu_cofactor_per_product':{'kind':'interpreted_reaction_account','direction':'cofactor_per_product',
                'status':'fixed_model','exact_value':{'numerator':'1','denominator':'1'},
                'witnesses':[self.witness('Fixed one cofactor per product')]},
            'covariance_source_ref':None}

    def read(self,reference,representation):
        assert representation=='original'
        self.calls.append((reference,representation))
        if reference in self.extra:return deepcopy(self.extra[reference])
        assert reference==self.reference or reference in self.aliases
        return {'artifact_ref':self.artifact,'content':self.content}

    def covariance(self,args,matrix=((.05,.05),(.05,.1)),**changes):
        data=read_product_coupling_inputs(args,read_source=self.read)
        record={'version':'a105_product_coupling_covariance_v1','order':['product','cofactor'],
            'measurement_keys':[data['quantities'][r]['number']['measurement_key'] for r in ('product','cofactor')],
            'units':['per_min','per_min'],'basis':'joint_covariance_of_selected_rate_estimates',
            'variance_status':'estimated','origin':'synthetic','covariance':[list(row) for row in matrix]}
        record.update(changes)
        content=json.dumps(record).encode();reference=identity('source',{'covariance':record})
        self.extra[reference]={'artifact_ref':'artifact_'+hashlib.sha256(content).hexdigest(),'content':content}
        args['covariance_source_ref']=reference
        return record


def run(source,args=None):
    data=read_product_coupling_inputs(source.args() if args is None else args,read_source=source.read)
    return data,populate_product_coupling(data)


def test_conflicting_quantity_normalization_blocks_physical_fraction_only():
    s=Source();a=s.args()
    a['quantities']['product']['normalization']={'value':'conflicting','witnesses':[
        s.witness('Per assayed molecule'),s.witness('Different preparation')]}
    data,sheet=run(s,a)
    assert sheet['cells']['product_per_cofactor']['value']==.5
    eta=sheet['cells']['productive_fraction']
    assert eta['value'] is None and eta['conditional_value'] is None
    assert 'product_normalization_conflicting' in eta['unavailable_reasons']


def test_uncertain_nu_does_not_invent_unknown_assay_relationships():
    s=Source();a=s.args();a['nu_cofactor_per_product']['status']='uncertain_model'
    data,sheet=run(s,a)
    eta=sheet['cells']['productive_fraction']
    assert eta['conditional_value']==.5
    assert 'unknown_scientific_relationships_assumed_compatible_only_for_conditional_arithmetic' not in eta['assumptions']


def exact(cell,field='exact_value'):
    value=cell[field]
    return None if value is None else Fraction(int(value['numerator']),int(value['denominator']))


def original(index=1):
    packet=json.loads((CASE/'SOURCE_PACKET_001.json').read_text())
    assert hashlib.sha256((CASE/'SOURCE_PACKET_001.json').read_bytes()).hexdigest()=='7ca8c54df69f5591d410869e658ff47e31d34028088fec99a9a04829a979d8fb'
    content=Path(packet['paper']['original_path']).read_bytes()
    assert hashlib.sha256(content).hexdigest()==packet['paper']['sha256']
    s=Source(content=content,kind='primary_source')
    def sw(w):
        assert content[w['start']:w['end']]==w['quote'].encode()
        return s.span(w['start'],w['end'])
    row=packet['table3_source_rows'][index];table=packet['tables']['T3']
    quantities={}
    for role,column,field,endpoint in [('product',1,'product_activity','product_formation'),
            ('cofactor',2,'nadh_consumption_activity','cofactor_consumption'),
            ('reported_coupling',5,'reported_coupling_percent','coupling_fraction')]:
        numeric=sw(row['quantities'][field]['witness']);label=sw(table['rows'][0]['cells'][column]['witness'])
        semantics='reported_nondetection' if index==3 and role in ('product','reported_coupling') else 'reported_point'
        quantities[role]={'number':{'witness':numeric,'number_start':0,'number_end':len(numeric['quote'])},
            'quantity_label':label,'unit':sw(table['rows'][2]['cells'][column]['witness']),
            'endpoint_role':{'value':endpoint,'witnesses':[label]},
            'measurement_semantics':{'value':semantics,'witnesses':[sw(packet['paragraphs']['P17']['witness'])] if semantics!='reported_point' else [sw(row['witness'])]},
            'normalization':s.interpretation('unknown'),'physical_identity':None,'dependency_witnesses':[]}
    pairing=sw(packet['paragraphs']['P19']['witness'])
    args={'source_ref':s.reference,'source_kind':'primary_source','context':{name:None for name in CONTEXT_FIELDS},
        'quantities':quantities,'relationships':{name:s.interpretation('unknown') for name in RELATIONSHIPS},
        'nu_cofactor_per_product':{'kind':'interpreted_reaction_account','direction':'cofactor_per_product',
            'status':'fixed_model','exact_value':{'numerator':'1','denominator':'1'},
            'witnesses':[sw(packet['paragraphs']['P4']['witness']),sw(table['witness'])]},
        'covariance_source_ref':None}
    args['relationships']['source_pairing']={'value':'author_assigned','witnesses':[pairing]}
    args['relationships']['same_molecule']={'value':'same','witnesses':[sw(row['witness'])]}
    args['relationships']['product_identity']={'value':'chemically_identified','witnesses':[sw(packet['paragraphs']['P11']['witness']),sw(packet['paragraphs']['P17']['witness'])]}
    for field,paragraph in [('experiment','P19'),('molecule','P4'),('construct','P8'),('preparation','P9'),
            ('partners','P10'),('product_identity_method','P11'),('product_conditions','P10'),('cofactor_conditions','P12')]:
        args['context'][field]=sw(packet['paragraphs'][paragraph]['witness'])
    return s,args,row


@pytest.mark.parametrize('index',range(3))
def test_original_positive_source_rows_have_native_descriptive_and_conditional_physical_cells(index):
    source,args,row=original(index);data,sheet=run(source,args);cells=sheet['cells']
    p=Fraction(row['quantities']['product_activity']['raw_number']);h=Fraction(row['quantities']['nadh_consumption_activity']['raw_number'])
    report=Fraction(row['quantities']['reported_coupling_percent']['raw_number'])
    assert exact(cells['product_per_cofactor'])==p/h
    assert cells['productive_fraction']['value'] is None
    assert exact(cells['productive_fraction'],'conditional_exact_value')==p/h
    assert cells['productive_fraction']['status']=='conditional'
    assert cells['productive_fraction']['origin']=='proposed'
    assert cells['productive_fraction']['input_model_keys']==[data['nu_cofactor_per_product']['model_key']]
    assert exact(cells['displayed_coupling_difference_pp'],'conditional_exact_value')==100*p/h-report
    assert cells['reported_coupling_percent']['value']==float(report)
    assert cells['reported_product_activity']['origin']=='reported'
    assert cells['reconstructed_product_activity']['value']==float(p)
    assert cells['reconstructed_product_activity']['contribution_key']==cells['reported_product_activity']['contribution_key']
    assert cells['product_per_cofactor_variance']['value'] is None
    assert cells['product_per_cofactor_variance']['unavailable_reasons']==['covariance_not_supplied']
    assert data['relationships']['same_preparation']['value']=='unknown'
    with localcontext() as context:
        context.prec=65
        oracle=Decimal(str(p.numerator))/Decimal(str(p.denominator))/Decimal(str(h.numerator))*Decimal(str(h.denominator))
        result=exact(cells['product_per_cofactor'])
        assert abs(Decimal(result.numerator)/Decimal(result.denominator)-oracle)<Decimal('1e-62')
    validate_schema(data,product_coupling_extraction_schema());validate_schema(sheet,product_coupling_sheet_schema())
    assert sheet['annotation_credit'] is None


def test_original_nondetection_zero_is_native_report_not_physical_ratio_or_function_absence():
    source,args,_=original(3);data,sheet=run(source,args);cells=sheet['cells']
    assert cells['reported_product_activity']['value']==0
    assert cells['reported_product_activity']['native_measurement_semantics']=='reported_nondetection'
    assert cells['reported_cofactor_activity']['value']==427
    assert cells['reported_coupling_percent']['value']==0
    for name in ('product_per_cofactor','productive_fraction','reconstructed_product_activity'):
        assert cells[name]['value'] is None and cells[name]['conditional_value'] is None
        assert 'product_measurement_semantics_reported_nondetection' in cells[name]['unavailable_reasons']
    assert 'negligible' in data['quantities']['product']['measurement_semantics']['witnesses'][0]['quote']


def test_original_mutant_reference_factorization_reuses_same_product_and_cofactor_measurements():
    s,a,_=original(0);_,wt=run(s,a)
    s,a,_=original(1);_,mutant=run(s,a)
    p=exact(mutant['cells']['reported_product_activity'])/exact(wt['cells']['reported_product_activity'])
    h=exact(mutant['cells']['reported_cofactor_activity'])/exact(wt['cells']['reported_cofactor_activity'])
    ratio=exact(mutant['cells']['product_per_cofactor'])/exact(wt['cells']['product_per_cofactor'])
    assert h*ratio==p==Fraction(46,103)
    assert set(mutant['cells']['product_per_cofactor']['input_measurement_keys'])==set(mutant['cells']['reconstructed_product_activity']['input_measurement_keys'])


def test_supported_synthetic_pair_and_exact_nu_direction_and_unit_conversion():
    s=Source();a=s.args();a['nu_cofactor_per_product']['exact_value']={'numerator':'2','denominator':'1'}
    data,sheet=run(s,a);c=sheet['cells']
    assert exact(c['product_per_cofactor'])==Fraction(1,2)
    assert exact(c['productive_fraction'])==1
    assert c['calculated_coupling_percent']['value']==100
    assert c['displayed_coupling_difference_pp']['value']==50
    assert c['productive_fraction']['conditional_value'] is None
    assert c['productive_fraction']['physical_fraction_status']=='within_reported_model_domain'
    before=deepcopy(data);calls=list(s.calls)
    assert populate_product_coupling(data)==sheet and data==before and s.calls==calls


@pytest.mark.parametrize('field,value,witness',[
    ('same_preparation','unknown',None),('conditions','unknown',None),('normalization','unknown',None),
    ('product_identity','unknown',None),('source_pairing','unknown',None)])
def test_unknown_physical_link_preserves_descriptive_ratio_and_conditional_eta(field,value,witness):
    s=Source();a=s.args();a['relationships'][field]=s.interpretation(value,witness)
    _,sheet=run(s,a);c=sheet['cells']
    assert c['product_per_cofactor']['value']==.5
    assert c['productive_fraction']['value'] is None and c['productive_fraction']['conditional_value']==.5
    assert 'eta_relationship_'+field+'_unknown' in c['productive_fraction']['unavailable_reasons']


@pytest.mark.parametrize('field,value,witness',[
    ('same_preparation','different','Different preparation'),('conditions','different','Different preparation'),
    ('normalization','incompatible','Different preparation'),('product_identity','other_product','Alternate identity'),
    ('product_identity','reporter_only','Alternate identity'),('same_molecule','different','Different preparation'),
    ('source_pairing','not_assigned','Different preparation')])
def test_known_incompatible_pair_preserves_source_ratio_but_supplies_no_physical_eta(field,value,witness):
    s=Source();a=s.args();a['relationships'][field]=s.interpretation(value,witness)
    _,sheet=run(s,a);c=sheet['cells']
    assert c['product_per_cofactor']['value']==.5
    assert c['productive_fraction']['value'] is None and c['productive_fraction']['conditional_value'] is None
    assert c['reported_product_activity']['value']==2


def test_conflicting_product_identity_retained_without_counterfeit_physical_efficiency():
    s=Source();a=s.args();a['relationships']['product_identity']={'value':'conflicting','witnesses':[
        s.witness('Product chemically identified by standard'),s.witness('Alternate identity')]}
    _,sheet=run(s,a)
    assert sheet['cells']['product_per_cofactor']['value']==.5
    assert sheet['cells']['productive_fraction']['conditional_value'] is None


def test_unknown_stoichiometry_keeps_rho_without_default_one():
    s=Source();a=s.args();a['nu_cofactor_per_product'].update(status='unknown',exact_value=None,witnesses=[])
    _,sheet=run(s,a);c=sheet['cells']
    assert c['product_per_cofactor']['value']==.5
    assert c['productive_fraction']['value'] is None and c['productive_fraction']['conditional_value'] is None
    assert c['productive_fraction']['input_model_keys']==[]
    assert 'nu_model_not_supplied' in c['productive_fraction']['unavailable_reasons']


def test_uncertain_supplied_nu_preserves_conditional_value_and_fixed_substitution_variance_only():
    s=Source();a=s.args();a['nu_cofactor_per_product'].update(status='uncertain_model',exact_value={'numerator':'2','denominator':'1'},
        witnesses=[s.witness('Uncertain stoichiometry estimate')])
    s.covariance(a);_,sheet=run(s,a);c=sheet['cells']
    assert c['productive_fraction']['value'] is None and c['productive_fraction']['conditional_value']==1
    assert c['product_per_cofactor_variance']['value'] is not None
    v=c['productive_fraction_variance']
    assert v['value'] is None and exact(v,'conditional_exact_value')==4*exact(c['product_per_cofactor_variance'])
    assert 'uncertain_nu_uncertainty_propagation_unimplemented' in v['unavailable_reasons']
    assert 'conditional_variance_term_excludes_nu_variance_and_covariance' in v['assumptions']
    assert c['productive_fraction_standard_uncertainty']['value'] is None


@pytest.mark.parametrize('value',[0,-1])
def test_nonpositive_stoichiometry_is_not_a_physical_fraction_multiplier(value):
    s=Source();a=s.args();a['nu_cofactor_per_product']['exact_value']={'numerator':str(value),'denominator':'1'}
    _,sheet=run(s,a)
    assert sheet['cells']['product_per_cofactor']['value']==.5
    assert 'nonpositive_stoichiometric_model' in sheet['cells']['productive_fraction']['unavailable_reasons']


def test_full_covariance_matches_independent_directional_finite_difference_oracle():
    s=Source();a=s.args();s.covariance(a);_,sheet=run(s,a);c=sheet['cells']
    # The synthetic covariance is generated by two unit-variance error modes:
    # (deltaP,deltaH)=(.2,.1),(.1,.3). Numerically differentiate the actual ratio
    # along each mode and add squared responses, rather than reusing JΣJ.
    epsilon=Fraction(1,10**10);p,h=Fraction(2),Fraction(4)
    oracle=Fraction(0)
    for dp,dh in ((Fraction(1,5),Fraction(1,10)),(Fraction(1,10),Fraction(3,10))):
        response=((p+epsilon*dp)/(h+epsilon*dh)-(p-epsilon*dp)/(h-epsilon*dh))/(2*epsilon)
        oracle+=response**2
    variance=exact(c['product_per_cofactor_variance'])
    assert variance==Fraction(1,640)
    assert abs(variance-oracle)<Fraction(1,10**22)
    assert exact(c['productive_fraction_variance'])==variance
    assert c['productive_fraction_variance']['contribution_key']==c['productive_fraction_standard_uncertainty']['contribution_key']
    assert c['product_per_cofactor_variance']['origin']=='proposed'
    assert c['product_per_cofactor_variance']['input_origins']==['synthetic']


def test_offdiagonal_is_used_and_not_replaced_by_independence():
    s=Source();a=s.args();s.covariance(a);_,shared=run(s,a)
    a=s.args();s.covariance(a,((.05,0),(0,.1)));_,independent=run(s,a)
    assert shared['cells']['product_per_cofactor_variance']['value']!=independent['cells']['product_per_cofactor_variance']['value']
    assert exact(shared['cells']['product_per_cofactor_variance'])==Fraction(1,640)
    assert exact(independent['cells']['product_per_cofactor_variance'])==Fraction(3,640)


@pytest.mark.parametrize('changes,reason',[
    ({'measurement_keys':['wrong','owners']},'covariance_owner_mismatch'),
    ({'units':['per_s','per_s']},'covariance_units_mismatch'),
    ({'basis':'raw_population_variability'},'covariance_basis_mismatch'),
    ({'variance_status':'unknown'},'covariance_status_unknown'),
    ({'covariance':[[1,2],[0,1]]},'covariance_not_symmetric'),
    ({'covariance':[[1,2],[2,1]]},'covariance_not_positive_semidefinite'),
    ({'covariance':[[-1,0],[0,1]]},'covariance_not_positive_semidefinite'),
    ({'covariance':[[1]]},'covariance_shape_invalid'),
    ({'origin':'made_up'},'covariance_contract_mismatch'),
])
def test_unavailable_covariance_preserves_all_source_point_components(changes,reason):
    s=Source();a=s.args();s.covariance(a,**changes);data,sheet=run(s,a)
    assert data['covariance']['unavailable_reason']==reason
    assert sheet['cells']['reported_product_activity']['value']==2
    assert sheet['cells']['product_per_cofactor']['value']==.5
    assert sheet['cells']['productive_fraction']['value']==.5
    assert sheet['cells']['product_per_cofactor_variance']['value'] is None
    assert reason in sheet['cells']['product_per_cofactor_variance']['unavailable_reasons']


def test_synthetic_covariance_on_original_rates_never_becomes_reported_primary_uncertainty():
    s,a,_=original();s.covariance(a);_,sheet=run(s,a)
    c=sheet['cells']['product_per_cofactor_variance']
    assert c['input_origins']==['reported','synthetic'] and c['origin']=='proposed'
    assert 'known_normal' not in json.dumps(sheet)


@pytest.mark.parametrize('scale',['1e400','1e-400'])
def test_exact_operands_survive_float_range_when_their_ratio_remains_finite(scale):
    s=Source(product=scale,cofactor=scale);_,sheet=run(s);c=sheet['cells']
    for name in ('reported_product_activity','reported_cofactor_activity'):
        assert c[name]['value'] is None and exact(c[name])==Fraction(scale)
        assert 'numerical_model_range' in c[name]['unavailable_reasons']
    assert c['product_per_cofactor']['value']==1 and exact(c['product_per_cofactor'])==1
    assert c['productive_fraction']['value']==1
    assert c['reconstructed_product_activity']['contribution_key']==c['reported_product_activity']['contribution_key']


@pytest.mark.parametrize('p,h',[('0','4'),('-2','4'),('2','-4'),('2','0'),('8','4')])
def test_signed_zero_and_outside_fraction_domain_do_not_clamp_or_invent_physics(p,h):
    s=Source(product=p,cofactor=h);_,sheet=run(s);c=sheet['cells']
    assert c['reported_product_activity']['source_value']==float(p)
    if h=='0':
        assert c['product_per_cofactor']['value'] is None
        assert 'zero_cofactor_denominator' in c['product_per_cofactor']['unavailable_reasons']
    else:
        assert exact(c['product_per_cofactor'])==Fraction(p)/Fraction(h)
        if Fraction(h)<=0:
            assert c['productive_fraction']['conditional_value'] is None
        elif Fraction(p)<0 or Fraction(p)>Fraction(h):
            assert c['productive_fraction']['value'] is None
            assert exact(c['productive_fraction'],'conditional_exact_value')==Fraction(p)/Fraction(h)
            assert c['productive_fraction']['physical_fraction_status']=='outside_reported_model_domain'


@pytest.mark.parametrize('printed,token,reason',[
    ('<2','2','bounded_ratio_calculation_unimplemented'),('>2','2','bounded_ratio_calculation_unimplemented'),
    ('approximately 2','2','source_approximation_unimplemented'),('1–2','1–2','source_range_unimplemented'),
    ('NaN','NaN','nonfinite_source_statistic_unavailable'),('not greater than 2','2','source_negated_comparison_unimplemented'),
    ('ND','ND','nondetection_source_text')])
def test_source_limits_and_capability_gaps_preserve_other_native_quantities(printed,token,reason):
    s=Source(product=printed);a=s.args();a['quantities']['product']['number']=s.selector(token,s.content.index(b'<td id="p">'))
    data,sheet=run(s,a)
    assert data['quantities']['product']['number']['representation_witness']['quote']==printed
    assert reason in sheet['cells']['product_per_cofactor']['unavailable_reasons']
    assert sheet['cells']['reported_cofactor_activity']['value']==4
    assert sheet['cells']['reported_coupling_percent']['value']==50


def test_numeric_column_unit_and_markup_selection_guards():
    s=Source();a=s.args();a['quantities']['product']['number']=s.quantity('cofactor')['number']
    with pytest.raises(ExperimentalContractError,match='source_quantity_column_mismatch'):run(s,a)
    a=s.args();a['quantities']['product']['unit']=s.quantity('reported_coupling')['unit']
    with pytest.raises(ExperimentalContractError,match='source_quantity_column_mismatch'):run(s,a)
    a=s.args();start=s.content.index(b'id="p"')
    a['quantities']['product']['quantity_label']=s.span(start+4,start+5)
    with pytest.raises(ExperimentalContractError,match='source_markup_is_not_statistic'):run(s,a)


@pytest.mark.parametrize('printed',['2 nmol','2 ± 1 %','2 ± 1 s<sup>−1</sup>'])
def test_header_cannot_erase_an_explicit_incompatible_unit_after_selected_number(printed):
    s=Source(product=printed);a=s.args();a['quantities']['product']['number']=s.selector('2',s.content.index(b'<td id="p">'))
    with pytest.raises(ExperimentalContractError,match='explicit_source_rate_unit_mismatch'):run(s,a)


def test_rate_unit_conversion_preserves_native_scale_and_ratio():
    s=Source(product='2',cofactor='4',rate_unit='s<sup>−1</sup>');data,sheet=run(s);c=sheet['cells']
    assert c['reported_product_activity']['value']==120 and c['reported_product_activity']['source_value']==2
    assert c['reported_product_activity']['source_unit']=='s<sup>−1</sup>'
    assert c['product_per_cofactor']['value']==.5
    assert data['quantities']['product']['canonical_unit']=='per_min'


@pytest.mark.parametrize('unit',['nmol/min/mg','unsupported_unit'])
def test_genuine_other_or_unsupported_unit_keeps_native_reports_without_physical_ratio(unit):
    s=Source(rate_unit=unit);data,sheet=run(s)
    assert sheet['cells']['reported_product_activity']['source_value']==2
    assert sheet['cells']['reported_cofactor_activity']['source_value']==4
    assert sheet['cells']['reported_coupling_percent']['value']==50
    assert sheet['cells']['product_per_cofactor']['value'] is None
    assert sheet['cells']['productive_fraction']['conditional_value'] is None


@pytest.mark.parametrize('payload',[b'{',b'{"a":1,"a":2}',b'{"a":NaN}'])
def test_malformed_received_covariance_is_specific_unavailable_partial(payload):
    s=Source();a=s.args();reference=identity('source',{'malformed_covariance':payload.hex()})
    s.extra[reference]={'artifact_ref':'artifact_'+hashlib.sha256(payload).hexdigest(),'content':payload}
    a['covariance_source_ref']=reference;data,sheet=run(s,a)
    assert data['covariance']['unavailable_reason']=='covariance_json_invalid'
    assert sheet['cells']['product_per_cofactor']['value']==.5
    assert sheet['cells']['product_per_cofactor_variance']['value'] is None


def test_missing_rate_cannot_retain_valid_owned_covariance_record():
    s=Source();a=s.args();s.covariance(a);data,_=run(s,a)
    data['quantities']['product']=None
    with pytest.raises(ExperimentalContractError,match='covariance_binding_mismatch'):
        populate_product_coupling(data)


def test_clipped_digits_and_source_quote_mismatch_fail_as_repairable_selection_errors():
    s=Source(product='12');a=s.args();a['quantities']['product']['number']['number_start']=1
    with pytest.raises(ExperimentalContractError,match='partial_source_numeric_token'):run(s,a)
    a=s.args();a['quantities']['product']['number']['witness']['quote']='13'
    with pytest.raises(ExperimentalContractError,match='source_quote_mismatch'):run(s,a)


def test_physical_source_aliases_do_not_manufacture_two_endpoint_measurements():
    s=Source();a=s.args();a['quantities']['cofactor']['number']=deepcopy(a['quantities']['product']['number'])
    a['quantities']['cofactor']['quantity_label']=deepcopy(a['quantities']['product']['quantity_label'])
    a['quantities']['cofactor']['unit']=deepcopy(a['quantities']['product']['unit'])
    alias='source_'+'9'*24;s.aliases.add(alias)
    a['quantities']['cofactor']['number']['witness']['source_ref']=alias
    data,sheet=run(s,a)
    assert data['quantities']['product']['number']['measurement_key']==data['quantities']['cofactor']['number']['measurement_key']
    assert 'reused_source_observation' in sheet['cells']['product_per_cofactor']['unavailable_reasons']


def test_equal_values_in_different_cells_are_not_declared_independent_or_deduplicated():
    s=Source(product='4');data,sheet=run(s)
    assert data['quantities']['product']['number']['measurement_key']!=data['quantities']['cofactor']['number']['measurement_key']
    assert sheet['cells']['product_per_cofactor']['value']==1
    assert sheet['cells']['product_per_cofactor_variance']['value'] is None


def test_exact_representation_aliases_do_not_supply_distinct_conflicting_witnesses_or_physical_identity():
    s=Source();a=s.args();w=s.witness('Same molecule and preparation');alias={**w,'representation':'text'}
    def read(reference,representation):
        return s.read(reference,'original')
    a['relationships']['same_preparation']={'value':'conflicting','witnesses':[w,alias]}
    with pytest.raises(ExperimentalContractError,match='interpretation_witness_required'):
        read_product_coupling_inputs(a,read_source=read)
    a=s.args();a['quantities']['product']['physical_identity']=w
    a['quantities']['cofactor']['physical_identity']=alias
    data=read_product_coupling_inputs(a,read_source=read)
    assert data['quantities']['product']['physical_identity_key']==data['quantities']['cofactor']['physical_identity_key']
    assert 'reused_source_observation' in populate_product_coupling(data)['cells']['product_per_cofactor']['unavailable_reasons']
    # Different coordinates remain separate witnesses; source aliases do not
    # erase a genuine alternative source statement.
    a=s.args();a['relationships']['same_preparation']={'value':'conflicting',
        'witnesses':[w,s.witness('Different preparation')]}
    data=read_product_coupling_inputs(a,read_source=read)
    assert data['relationships']['same_preparation']['value']=='conflicting'
    a=s.args();model=read_product_coupling_inputs(a,read_source=read)['nu_cofactor_per_product']['model_key']
    a['nu_cofactor_per_product']['witnesses'][0]['representation']='text'
    assert read_product_coupling_inputs(a,read_source=read)['nu_cofactor_per_product']['model_key']==model
    a['nu_cofactor_per_product']['witnesses'].append({**a['nu_cofactor_per_product']['witnesses'][0],'representation':'original'})
    assert read_product_coupling_inputs(a,read_source=read)['nu_cofactor_per_product']['model_key']==model
    a['nu_cofactor_per_product']['status']='conflicting'
    with pytest.raises(ExperimentalContractError,match='interpretation_witness_required'):
        read_product_coupling_inputs(a,read_source=read)


def test_different_artifacts_at_equal_coordinates_remain_distinct_source_spans():
    s=Source();a=s.args();w=s.witness('Same molecule and preparation')
    other=s.content+b' Additional retained source statement.'
    reference=identity('source',{'other_source':hashlib.sha256(other).hexdigest()})
    s.extra[reference]={'artifact_ref':'artifact_'+hashlib.sha256(other).hexdigest(),'content':other}
    second={**w,'source_ref':reference}
    a['relationships']['same_preparation']={'value':'conflicting','witnesses':[w,second]}
    a['quantities']['product']['physical_identity']=w
    a['quantities']['cofactor']['physical_identity']=second
    data,sheet=run(s,a)
    assert data['quantities']['product']['physical_identity_key']!=data['quantities']['cofactor']['physical_identity_key']
    assert sheet['cells']['product_per_cofactor']['value']==.5
    assert sheet['cells']['productive_fraction']['conditional_value'] is None


def test_unknown_roles_and_known_wrong_endpoint_do_not_become_verified_product_coupling():
    s=Source();a=s.args();a['quantities']['product']['endpoint_role']=s.interpretation('unknown')
    _,sheet=run(s,a)
    assert sheet['cells']['product_per_cofactor']['value'] is None and sheet['cells']['product_per_cofactor']['conditional_value']==.5
    a=s.args();a['quantities']['product']['endpoint_role']=s.interpretation('cofactor_consumption','Cofactor consumption')
    _,sheet=run(s,a)
    assert sheet['cells']['reported_product_activity']['value']==2
    assert sheet['cells']['product_per_cofactor']['value'] is None and sheet['cells']['product_per_cofactor']['conditional_value'] is None


def test_missing_product_does_not_discard_received_cofactor_and_coupling_reports():
    s=Source();a=s.args();a['quantities']['product']=None
    _,sheet=run(s,a)
    assert sheet['cells']['reported_product_activity']['value'] is None
    assert sheet['cells']['reported_cofactor_activity']['value']==4
    assert sheet['cells']['reported_coupling_percent']['value']==50


def test_closed_input_and_mutated_numeric_model_unit_and_dependency_bindings_fail():
    s=Source();a=s.args();a['quantities']['product']['number']['value']=2
    with pytest.raises(ContractError):validate_schema(a,product_coupling_population_schema())
    data,_=run(s)
    wrong=deepcopy(data);wrong['quantities']['product']['number']['native_exact_value']['numerator']='999'
    with pytest.raises(ExperimentalContractError,match='number_record_mismatch'):populate_product_coupling(wrong)
    wrong=deepcopy(data);wrong['nu_cofactor_per_product']['exact_value']['numerator']='2'
    with pytest.raises(ExperimentalContractError,match='nu_binding_mismatch'):populate_product_coupling(wrong)
    wrong=deepcopy(data);wrong['quantities']['product']['unit']['multiplier_exact']={'numerator':'2','denominator':'1'}
    with pytest.raises(ExperimentalContractError,match='unit_record_mismatch'):populate_product_coupling(wrong)
    wrong=deepcopy(data);wrong['quantities']['product']['dependency_keys']=[]
    with pytest.raises(ExperimentalContractError,match='dependency_record_mismatch'):populate_product_coupling(wrong)


def test_full_exact_task_remains_separate_from_numerical_sheet_and_interpretation_codes():
    assert PRODUCT_COUPLING_TASK==TASK.read_text().rstrip('\n')
    assert len(PRODUCT_COUPLING_TASK.split('\n\n'))==6
    assert 'an initial annotation or public searchable name is not required' in PRODUCT_COUPLING_TASK
    assert 'source_ref' not in PRODUCT_COUPLING_TASK and 'J*Sigma' not in PRODUCT_COUPLING_TASK
    assert len(COMPONENTS)==11 # the reviewed cell plan, never a grader/assay count
