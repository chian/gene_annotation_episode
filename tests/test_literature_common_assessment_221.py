"""Pure common A105 arithmetic with actual218/kinetic native-row custody.

Retained207 source examples are distinguished from synthetic model/covariance
experiments. No common selected-operation, provider/model or credit is run.
"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

import pytest

from gene_annotation_episode.domain import ContractError, identity, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_product_coupling_storage import LiteratureProductCouplingRepository
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository
from gene_annotation_episode.literature_kinetic_inputs import SUBJECT_FIELDS, CONTEXT_FIELDS
from gene_annotation_episode.literature_compiled_assay_inputs import (
    COMMON_CONTEXT, COMMON_ARM_CONTEXT, COMMON_ROLES, COMMON_GROUPS, COMMON_ASSUMPTIONS,
    COMMON_REQUEST, COMMON_POPULATION, COMMON_PARAMETER_KINDS, read_common_assessment_inputs,
    common_assessment_population_schema, common_assessment_inputs_schema,
)
from gene_annotation_episode.literature_compiled_assay_calculations import (
    COMMON_COMPONENTS, populate_common_assessment, common_assessment_sheet_schema,
)
import test_literature_product_coupling_212 as retained212
from test_literature_product_coupling_binding_218 import rebind

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_common_scientific_sheet_review_219/ROOT_NUMERICAL_ORACLES_001.json'


def original(index=1):
    """Relocate the immutable212 fixture's source to this frozen cohort.

    The original packet and source hashes remain checked by212. Only the exact
    historical absolute acquisition path is resolved to the byte-identical
    retained copy beside that packet; no published source file is modified.
    """
    packet=json.loads((retained212.CASE/'SOURCE_PACKET_001.json').read_text())
    original_path=retained212.Path
    def path(value,*args,**kwargs):
        if str(value)==packet['paper']['original_path']:
            return retained212.CASE/'acquisition_001.bin'
        return original_path(value,*args,**kwargs)
    retained212.Path=path
    try:return retained212.original(index)
    finally:retained212.Path=original_path


class Case:
    """Actual existing repositories supply received rows; callbacks deny others."""
    def __init__(self,path,index=1):
        source,_,_=original(index);self.raw=source.content;self.store=Store(path)
        self.store.create_problem(raw_sequence='ATGGCT',molecule='dna')
        self.refs={};self.extra={};self.calls=[];self.index=index
        self.source=self.publish(self.raw,'retained_primary_207')
        self.context=BindingContext('common221','reader221','literature',(('literature','reader221'),),
            self.store.validate_scope(),{'version':'literature_assignment_v1','source_refs':[self.source],
                'question_context_refs':[],'requested_product_coupling_components':['reported_product_activity','reported_cofactor_activity']}, {},(self.source,))
        self.product=LiteratureProductCouplingRepository(self.store,self.context.run_id)
        self.kinetic=LiteratureKineticRepository(self.store,self.context.run_id)
        self.rows={};self.tables=list(re.finditer(rb'<table\b[^>]*>.*?</table>',self.raw,re.S))
        for arm,i in [('reference',0),('test',index)]:
            s,args,_=original(i);args=rebind(args,{s.reference:self.source})
            args['context']['construct']=self.cell(2,i+3,0)
            out=self.product.populate(self.context,args,'product_'+arm)
            self.admit(out)
            for row in out['result']['cells']:
                self.rows[(row['sheet_ref'],row['component'])]=row
        self.product_refs={arm:self.store.db.execute('SELECT outcome FROM literature_product_coupling_operations WHERE operation_key=?',('product_'+arm,)).fetchone()[0] for arm in ('reference','test')}
        self.product_refs={arm:json.loads(v)['result']['sheet_ref'] for arm,v in self.product_refs.items()}
        self.kin_refs={}
        for kind,col in [('kcat',1),('Km',2)]:
            operands={}
            for side,i in [('numerator',index),('denominator',0)]:
                c=self.cell(1,i+1,col);token=None if i==3 else re.search(r'[0-9]+',c['quote'])
                n=None if token is None else {'witness':c,'number_start':token.start(),'number_end':token.end()}
                unit=self.find('min<sup>−1</sup>' if kind=='kcat' else 'µM',self.tables[1].start())
                sm=re.search(r'±\s*([0-9]+)',c['quote'])
                magnitude=None if sm is None else {'witness':c,'number_start':sm.start(1),'number_end':sm.end(1)}
                operands[side]={'parameter_kind':self.meaning(kind,self.cell(1,0,col)),
                    'subject':{k:self.cell(1,i+1,0) if k=='construct' else None for k in SUBJECT_FIELDS},
                    'context':{k:None for k in CONTEXT_FIELDS},'measurement_identity':None,
                    'measurement':None if n is None else {'number':n,'unit':unit},
                    'qualification':self.meaning('reported_point',c),
                    'uncertainty':{'statistic':self.meaning('unspecified'), 'magnitude':magnitude,'interval':None,'unit':None,
                        'unit_relationship':self.meaning('same_as_parameter',unit),'confidence_level':None,'count':None,
                        'repetition_basis':self.meaning('unspecified'),'estimate_basis':self.meaning('unknown')}}
            args={'version':'a105_kinetic_source_selection_v1','source_ref':self.source,'source_kind':'primary_source',**operands,
                'comparison':{name:self.meaning(value,self.find('T252N')) for name,value in {
                    'subject_relationship':'different','parameter_definition_relationship':'same','substrate_arrangement':'separate_assays',
                    'comparison_scope':'reported_protocols','nonintended_conditions_relationship':'unknown'}.items()}}
            out=self.kinetic.populate(self.context,args,'kinetic_'+kind);self.admit(out);ref=out['result']['sheet_ref'];self.kin_refs[kind]=ref
            for row in self.kinetic.fact_cells(self.context,[ref],components=['numerator_parameter','denominator_parameter']):
                self.rows[(ref,row['component'])]=row
        self.model_ref=self.publish(b'<p>shared free substrate 2000 uM</p><p>Model sensitivity stipulates one-site equilibrium and equal other responses.</p>', 'synthetic_model_scenario')
        self.context=replace(self.context,received_record_refs=(*self.context.received_record_refs,self.model_ref))

    def publish(self,raw,provider):
        artifact=self.store.artifact(raw,'application/xml');ref=self.store.put('source',{'provider':provider,'accession':None,'uri':None,
            'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None},origin='caller')['id']
        self.refs[ref]={'artifact_ref':artifact,'content':raw};return ref

    def admit(self,out):
        self.context=replace(self.context,received_record_refs=tuple(dict.fromkeys((*self.context.received_record_refs,*out['record_refs']))))

    def witness(self,a,b,ref=None):
        ref=ref or self.source;return dict(source_ref=ref,representation='original',start=a,end=b,quote=self.refs[ref]['content'][a:b].decode())

    def find(self,text,start=0,ref=None):
        raw=self.refs[ref or self.source]['content'];a=raw.index(text.encode(),start);return self.witness(a,a+len(text.encode()),ref)

    def cell(self,table,row,col):
        t=self.tables[table];rows=list(re.finditer(rb'<tr\b[^>]*>.*?</tr>',t.group(),re.S));r=rows[row]
        cells=list(re.finditer(rb'<(?:td|th)\b[^>]*>(.*?)</(?:td|th)>',r.group(),re.S));c=cells[col]
        a=t.start()+r.start()+c.start(1);return self.witness(a,a+len(c.group(1)))

    def meaning(self,value,witness=None):
        return {'value':value,'witnesses':[] if value in ('unknown','unspecified') else [witness or self.find('T252N')]}

    def source_parameter(self,role,arm='test'):
        base=role.rsplit('_',1)[0]
        if base=='Kd':
            index=self.index if arm=='test' else 0;c=self.cell(3,index+3,1);m=re.search(r'[0-9.]+',c['quote']);spread=re.search(r'±\s*([0-9.]+)',c['quote'])
            return {'kind':'source_parameter','source_kind':'primary_source','parameter_kind':self.meaning(COMMON_PARAMETER_KINDS[base],self.cell(3,0,1)),
                'layout':'table','record':None,'number':dict(witness=c,number_start=m.start(),number_end=m.end()),
                'row_label':self.cell(3,index+3,0),'quantity_label':self.cell(3,0,1),'unit':self.find('µM',self.tables[3].start()),
                'semantics':self.meaning('reported_point',c),'method':self.find('Spectral binding titrations'),
                'assay':None,'conditions':None,'normalization':None,'population':None,'physical_identity':None,
                'reported_spread':None if spread is None else {'witness':c,'number_start':spread.start(1),'number_end':spread.end(1)}}
        record=self.find('shared free substrate 2000 uM',ref=self.model_ref)
        return {'kind':'source_parameter','source_kind':'supplied_model','parameter_kind':self.meaning(COMMON_PARAMETER_KINDS[base],record),
            'layout':'single_record','record':record,'number':dict(witness=self.find('2000',ref=self.model_ref),number_start=0,number_end=4),
            'row_label':self.find('shared',ref=self.model_ref),'quantity_label':self.find('free substrate',ref=self.model_ref),
            'unit':self.find('uM',ref=self.model_ref),'semantics':self.meaning('reported_point',record),
            'method':None,'assay':None,'conditions':None,'normalization':None,'population':None,'physical_identity':None,'reported_spread':None}

    def args(self,requested=None):
        context={k:None for k in COMMON_CONTEXT};context.update(molecule=self.find('P450cam'),conditions=self.find('37 °C'))
        args={'version':COMMON_REQUEST,'population_version':COMMON_POPULATION,'source_ref':self.source,'source_kind':'primary_source',
            'assertion':{**context,'resolution':'binding_occupancy_alternative','question':'named_alternative'},
            'arms':{arm:{k:self.cell(2,(0 if arm=='reference' else self.index)+3,0) if k=='construct' else None for k in COMMON_ARM_CONTEXT} for arm in ('reference','test')},
            'subject_relationship':self.meaning('intended_variant'),
            'relationships':{group:{name:self.meaning('same_estimand' if name=='endpoint' else 'compatible_supported') if name in ('endpoint','normalization') else self.meaning('unknown') for name in ('endpoint','normalization','preparation','conditions')} for group in COMMON_GROUPS},
            'product_reporter_relationship':self.meaning('author_assigned_pair'),'sampling_relationship':self.meaning('unknown'),'estimates':{r:None for r in COMMON_ROLES},
            'model':{'kind':'one_site_equilibrium','scope':'conditional_sensitivity','substrate_ownership':'shared_owner',
                'substrate_uncertainty':'fixed_scenario','assumptions':{k:self.meaning('stipulated_sensitivity',self.find('Model sensitivity stipulates one-site equilibrium and equal other responses.',ref=self.model_ref)) for k in COMMON_ASSUMPTIONS}},
            'correction_factorization':self.meaning('unknown'),'covariance_source_refs':[],
            'requested_cells':list(COMMON_COMPONENTS if requested is None else requested)}
        for arm in ('reference','test'):
            for base,component in [('product','reported_product_activity'),('reporter','reported_cofactor_activity')]:
                args['estimates'][base+'_'+arm]={'kind':'received_component','namespace':'literature_product_coupling_cells','sheet_ref':self.product_refs[arm],'component':component}
            for kind in ('kcat','Km'):
                args['estimates'][kind+'_'+arm]={'kind':'received_component','namespace':'literature_kinetic_cells','sheet_ref':self.kin_refs[kind],
                    'component':'denominator_parameter' if arm=='reference' else 'numerator_parameter'}
            for base in ('Kd','free_substrate'):args['estimates'][base+'_'+arm]=self.source_parameter(base+'_'+arm,arm)
        return args

    def read_source(self,ref,representation):
        self.calls.append(('source',ref));assert representation=='original'
        if ref not in self.context.received_record_refs:raise ContractError('literature_source_not_received')
        return deepcopy(self.refs[ref])

    def read_component(self,s):
        self.calls.append(('component',s['sheet_ref'],s['component']))
        row=self.rows.get((s['sheet_ref'],s['component']))
        return [] if row is None else [deepcopy(row)]

    def read(self,args):
        return read_common_assessment_inputs(args,read_source=self.read_source,read_component=self.read_component,read_record=self.store.get)

    def covariance(self,data,roles,matrix,status='estimated'):
        payload={'version':'a105_common_assessment_covariance_v1','roles':roles,
            'owner_keys':[data['estimates'][r]['owner_key'] for r in roles], 'units':[data['estimates'][r]['unit'] for r in roles],
            'dependency_keys':[data['estimates'][r]['dependency_keys'] for r in roles], 'covariance':matrix,
            'basis':'joint_covariance_of_selected_estimates','variance_status':status,'origin':'synthetic'}
        ref=self.publish(json.dumps(payload).encode(),'synthetic_joint_covariance221')
        self.context=replace(self.context,received_record_refs=(*self.context.received_record_refs,ref));return ref


def cells(sheet):return {r['component']:r for r in sheet['cells']}
def exact(row,conditional=False):
    e=row['conditional_exact_value' if conditional else 'exact_value'];return None if e is None else Fraction(int(e['numerator']),int(e['denominator']))


@pytest.mark.parametrize('index,label',[(1,'T252N'),(2,'T252N/V253T')])
def test_primary207_native_rows_conditional_residual_and_root219_oracles(tmp_path,index,label):
    c=Case(tmp_path,index);args=c.args();before=deepcopy(args);data=c.read(args);sheet=populate_common_assessment(data);r=cells(sheet)
    oracle=json.loads(ORACLE.read_text())['results'][label]
    assert args==before
    assert exact(r['product_reference_contrast'])==Fraction(int(oracle['product_contrast']['numerator']),int(oracle['product_contrast']['denominator']))
    assert r['saturation_turnover_reference_contrast']['value']==pytest.approx(oracle['saturation_turnover_contrast']['display'])
    assert r['low_substrate_efficiency_reference_contrast']['value']==pytest.approx(oracle['low_substrate_efficiency_contrast']['display'])
    assert r['occupancy_reference_contrast']['value'] is None
    assert r['occupancy_reference_contrast']['conditional_value']==pytest.approx(oracle['conditional_occupancy_contrast']['display'])
    assert r['post_binding_residual_ratio']['conditional_value']==pytest.approx(oracle['conditional_residual_ratio']['display'])
    assert r['binding_only_log_residual']['conditional_value']==pytest.approx(float(oracle['conditional_log_residual']))
    assert r['binding_only_standardized_residual']['value'] is None and r['binding_only_standardized_residual']['conditional_value'] is None
    assert r['fully_corrected_activity_reference_contrast']['value'] is None
    assert data['estimates']['kcat_test']['numeric_origin']=='original_source_token'
    assert r['estimate_kcat_test']['reported_uncertainty']['statistic']=='unspecified'
    assert r['estimate_kcat_test']['reported_uncertainty']['exact_magnitude']=={'numerator':str(2 if index==1 else 7),'denominator':'1'}
    assert c.kinetic.read(c.kin_refs['kcat'])['cells']['parameter_ratio']['value'] is None
    assert all('private' not in str(call) for call in c.calls)
    validate_schema(data,common_assessment_inputs_schema());validate_schema(sheet,common_assessment_sheet_schema())
    assert sheet['annotation_credit'] is None


@pytest.mark.parametrize('change,reason',[
    ('wrong_row','row_mismatch'),('wrong_column','column_meaning_required'),('wrong_construct','construct_mismatch'),
    ('hill_kind','role_mismatch'),('borrowed_unit','column_mismatch'),('wrong_native_role','role_mismatch')])
def test_numeric_occurrence_alone_cannot_bind_wrong_scientific_operand(tmp_path,change,reason):
    c=Case(tmp_path);a=c.args();s=a['estimates']['Kd_test']
    if change=='wrong_row':s['number']=a['estimates']['Kd_reference']['number']
    if change=='wrong_column':s['quantity_label']=c.cell(2,0,1)
    if change=='wrong_construct':s['row_label']=c.cell(3,3,0)
    if change=='hill_kind':s['parameter_kind']['value']=COMMON_PARAMETER_KINDS['free_substrate']
    if change=='borrowed_unit':s['unit']=c.cell(3,1,0)
    if change=='wrong_native_role':a['estimates']['product_test']['component']='reported_cofactor_activity'
    with pytest.raises(ExperimentalContractError,match=reason):c.read(a)


def test_nd_native_zero_survives_but_no_physical_ratio_log_or_invented_limit(tmp_path):
    c=Case(tmp_path,3);r=cells(populate_common_assessment(c.read(c.args())))
    assert r['estimate_product_test']['value']==0 and r['estimate_product_test']['native_semantics']=='reported_nondetection'
    assert all(r[name]['value'] is None and r[name]['conditional_value'] is None for name in (
        'product_reference_contrast','post_binding_residual_ratio','binding_only_log_residual','binding_only_residual_variance'))
    assert 'native_nondetection_not_point' in r['product_reference_contrast']['source_missing_reasons']


def test_shared_s_requires_same_actual_owner_and_conditional_unknowns_are_local(tmp_path):
    c=Case(tmp_path);a=c.args();s=a['estimates']['free_substrate_test'];raw=b'<p>separate free substrate 2000 uM</p>'
    ref=c.publish(raw,'synthetic_distinct_S');c.context=replace(c.context,received_record_refs=(*c.context.received_record_refs,ref))
    record=c.witness(3,len(raw)-4,ref);s.update(record=record,row_label=c.find('separate',ref=ref),quantity_label=c.find('free substrate',ref=ref),unit=c.find('uM',ref=ref),
        number={'witness':c.find('2000',ref=ref),'number_start':0,'number_end':4})
    with pytest.raises(ExperimentalContractError,match='shared_substrate_owner'):c.read(a)
    a['model']['substrate_ownership']='separate_owners';data=c.read(a)
    assert cells(populate_common_assessment(data))['post_binding_residual_ratio']['conditional_value'] is not None
    a['model']['assumptions']['binding_catalysis_applicability']=c.meaning('unknown')
    r=cells(populate_common_assessment(c.read(a)))
    assert r['product_reference_contrast']['value'] is not None and r['occupancy_test']['conditional_value'] is not None
    assert r['post_binding_residual_ratio']['conditional_value'] is None


def test_joint_covariance_actual_owners_shared_S_and_signed_terms(tmp_path):
    c=Case(tmp_path);a=c.args();a['model']['substrate_uncertainty']='selected_estimate_covariance';d=c.read(a)
    roles=['product_test','product_reference','Kd_test','Kd_reference','free_substrate_test']
    vector=[2,1,3,1,4];matrix=[[x*y for y in vector] for x in vector]
    a['covariance_source_refs']=[c.covariance(d,roles,matrix)];r=cells(populate_common_assessment(c.read(a)))
    p,pr,k,kr,s=map(Fraction,[92,206,34,Fraction(18,10),2000])
    grad=[1/p,-1/pr,1/(s+k),-1/(s+kr),1/(s+k)-1/(s+kr)]
    expected=sum(x*y for x,y in zip(grad,vector))**2
    assert exact(r['binding_only_residual_variance'],True)==expected
    assert r['binding_only_standardized_residual']['uncertainty']['variance_status']=='estimated'
    assert r['binding_only_standardized_residual']['conditional_value']<0
    assert 'synthetic' in r['binding_only_residual_variance']['input_origins']
    # Marginal blocks do not manufacture cross-covariances.
    a['covariance_source_refs']=[c.covariance(d,['product_test'],[[4]])]
    r=cells(populate_common_assessment(c.read(a)))
    assert 'joint_covariance_incomplete' in r['binding_only_residual_variance']['implementation_reasons']
    assert r['binding_only_log_residual']['conditional_value'] is not None


@pytest.mark.parametrize('matrix,reason',[
    ([[10**18,10**17],[10**17+1,10**18]],'exact_symmetry'),
    ([[1,2],[2,1]],'psd_required'),([[1,'bad'],['bad',1]],'shape_numeric'),
])
def test_covariance_exact_symmetry_psd_and_invalid_numbers(tmp_path,matrix,reason):
    c=Case(tmp_path);a=c.args();d=c.read(a);a['covariance_source_refs']=[c.covariance(d,['product_test','product_reference'],matrix)]
    with pytest.raises(ExperimentalContractError,match=reason):c.read(a)


def test_broad_context_numeric_scope_and_requested_only_cells(tmp_path):
    c=Case(tmp_path);a=c.args(['product_reference_contrast'])
    broad=c.publish(b'<p>assay P 92; unrelated residual variance 0.001; temperature 37 C</p>','synthetic_scope_context')
    c.context=replace(c.context,received_record_refs=(*c.context.received_record_refs,broad))
    a['assertion']['conditions']=c.witness(3,len(c.refs[broad]['content'])-4,broad)
    d=c.read(a);s=populate_common_assessment(d)
    assert len(s['cells'])==1
    text=' '.join(r['display_text'] for r in s['context'])
    assert '0.001' not in text and '92;' not in text
    assert s['numerical_scope_implementation_status']=='partial_unresolved'
    assert '0.001' in d['request']['assertion']['conditions']['quote']
    a['assertion']['conditions']=c.find('37 °C');s=populate_common_assessment(c.read(a))
    assert any('37' in r['display_text'] for r in s['context'])


def test_pure_calculation_never_calls_source_component_or_store(tmp_path,monkeypatch):
    c=Case(tmp_path);d=c.read(c.args(['post_binding_residual_ratio']));before=deepcopy(d)
    def denied(*args,**kwargs):raise AssertionError('IO in pure calculator')
    monkeypatch.setattr(c,'read_source',denied);monkeypatch.setattr(c,'read_component',denied);monkeypatch.setattr(c.store,'get',denied)
    s=populate_common_assessment(d)
    assert d==before and len(s['cells'])==1


@pytest.mark.parametrize('index,label',[(1,'T252N'),(2,'T252N/V253T')])
def test_root219_two_joint_error_mode_variance_oracles(tmp_path,index,label):
    c=Case(tmp_path,index);a=c.args(['binding_only_residual_variance']);a['model']['substrate_uncertainty']='selected_estimate_covariance'
    d=c.read(a);roles=['product_test','product_reference','Kd_test','Kd_reference','free_substrate_test']
    modes=((Fraction(1),Fraction('0.5'),Fraction(2),Fraction('0.1'),Fraction(20)),
        (Fraction('-0.2'),Fraction('0.4'),Fraction(1),Fraction('0.3'),Fraction(-10)))
    matrix=[[float(sum(mode[i]*mode[j] for mode in modes)) for j in range(5)] for i in range(5)]
    a['covariance_source_refs']=[c.covariance(d,roles,matrix,'known')]
    row=populate_common_assessment(c.read(a))['cells'][0];o=json.loads(ORACLE.read_text())['results'][label]['synthetic_error_mode_variance_exact']
    assert exact(row,True)==Fraction(int(o['numerator']),int(o['denominator']))
    assert row['uncertainty']['variance_status']=='known' and 'synthetic' in row['input_origins']


def test_full_correction_uses_actual_synthetic_operands_and_explicit_factorization(tmp_path):
    c=Case(tmp_path);a=c.args(['fully_corrected_activity_reference_contrast','product_reference_contrast'])
    raw=(b'<table><tr><th>Construct</th><th>Background</th><th>Recovery</th><th>Active fraction</th><th>Nuisance response</th></tr>'
        b'<tr><th>name</th><th>per_min</th><th>fraction</th><th>fraction</th><th>fraction</th></tr>'
        b'<tr><td>Wild-type</td><td>2</td><td>0.8</td><td>0.5</td><td>1.2</td></tr>'
        b'<tr><td>T252N</td><td>1</td><td>0.9</td><td>0.4</td><td>1.1</td></tr></table>'
        b'<p>Nuisance controls exclude the intended mutation; recovery and active amounts apply to these assay preparations.</p>')
    ref=c.publish(raw,'synthetic_applicable_corrections221');c.context=replace(c.context,received_record_refs=(*c.context.received_record_refs,ref))
    rows=list(re.finditer(rb'<tr>(.*?)</tr>',raw,re.S))
    def cell(row,col):
        r=rows[row];x=list(re.finditer(rb'<(?:td|th)>(.*?)</(?:td|th)>',r.group(),re.S))[col]
        start=r.start()+x.start(1);return c.witness(start,start+len(x.group(1)),ref)
    for arm,i in [('reference',2),('test',3)]:
        for col,base in enumerate(('background','recovery','active_fraction','nuisance_response'),1):
            w=cell(i,col)
            a['estimates'][base+'_'+arm]={'kind':'source_parameter','source_kind':'synthetic_fixture',
                'parameter_kind':c.meaning(COMMON_PARAMETER_KINDS[base],cell(0,col)), 'layout':'table','record':None,
                'number':dict(witness=w,number_start=0,number_end=len(w['quote'])),
                'row_label':cell(i,0),'quantity_label':cell(0,col),'unit':cell(1,col),'semantics':c.meaning('reported_point',w),
                'method':c.find('Nuisance controls exclude the intended mutation; recovery and active amounts apply to these assay preparations.',ref=ref),
                'assay':cell(i,0),'conditions':None,'normalization':None,'population':None,'physical_identity':None,'reported_spread':None}
    a['correction_factorization']=c.meaning('supported',c.find('Nuisance controls exclude the intended mutation; recovery and active amounts apply to these assay preparations.',ref=ref))
    for name in a['relationships']['correction']:a['relationships']['correction'][name]=c.meaning('compatible_supported',cell(3,0))
    d=c.read(a);r=populate_common_assessment(d)['cells'][0]
    rt=Fraction(10009,10170);expected=Fraction(91,204)*Fraction(8,9)*Fraction(5,4)*Fraction(12,11)/rt
    assert exact(r,True)==expected and r['value'] is None and 'synthetic' in r['input_origins']
    for field in ('endpoint','normalization'):
        for status in ('incompatible','conflicting'):
            bad=deepcopy(a)
            bad['relationships']['binding'][field]={'value':status,'witnesses':
                [c.cell(3,3,0),c.cell(3,4,0)] if status=='conflicting' else [c.cell(3,4,0)]}
            tested=cells(populate_common_assessment(c.read(bad)))
            full=tested['fully_corrected_activity_reference_contrast']
            assert full['conditional_value'] is None
            assert ('relationship_'+status) in full['relationship_reasons']
            assert tested['product_reference_contrast']['value'] is not None
    a['estimates']['background_test']=None;r=populate_common_assessment(c.read(a))['cells'][0]
    assert r['conditional_value'] is None and 'estimate_not_selected' in r['source_missing_reasons']
    a['estimates']['background_test']=d['request']['estimates']['background_test'];a['correction_factorization']=c.meaning('unknown')
    assert 'correction_factorization_unresolved' in populate_common_assessment(c.read(a))['cells'][0]['relationship_reasons']


def test_parameter_units_full_tokens_reported_spread_and_scope_bound_names(tmp_path):
    c=Case(tmp_path);a=c.args(['estimate_Kd_test','post_binding_residual_ratio'])
    selected=a['estimates']['Kd_test'];w=selected['number']['witness'];start=w['quote'].index('2',w['quote'].index('±'))
    selected['reported_spread']={'witness':w,'number_start':start,'number_end':start+1}
    d=c.read(a);assert d['estimates']['Kd_test']['reported_spread']['statistic']=='unspecified'
    assert d['estimates']['Kd_test']['reported_spread']['exact_value']=={'numerator':'2','denominator':'1'}
    unit=selected['unit'];selected['unit']={**unit,'start':unit['end']-1,'quote':'M'}
    with pytest.raises(ExperimentalContractError,match='partial_common_source_unit'):c.read(a)
    selected['unit']=unit
    extra=c.publish(b'<p>5-methyl-uridine</p><p>mean5mM SEM3uM</p>','synthetic_name_scope221')
    c.context=replace(c.context,received_record_refs=(*c.context.received_record_refs,extra))
    a['assertion']['product_or_ligand']=c.find('5-methyl-uridine',ref=extra)
    a['assertion']['conditions']=c.find('mean5mM SEM3uM',ref=extra)
    s=populate_common_assessment(c.read(a));text=' '.join(r['display_text'] for r in s['context'])
    assert '5-methyl-uridine' in text and 'mean5mM' not in text and 'SEM3uM' not in text


def test_missing_received_component_and_wrong_source_are_access_failures(tmp_path):
    c=Case(tmp_path);a=c.args(['product_reference_contrast']);s=a['estimates']['product_test']
    c.rows.pop((s['sheet_ref'],s['component']))
    with pytest.raises(ExperimentalContractError,match='selected_component_not_received'):c.read(a)
    a=c.args();a['estimates']['Kd_test']['number']['witness']['source_ref']='source_'+'f'*24
    with pytest.raises(ContractError,match='not_received'):c.read(a)


def test_received_recovery_conversion_is_explicitly_unimplemented_not_source_absent(tmp_path):
    from test_literature_calibration_recovery_169 import Source as RecoverySource
    from gene_annotation_episode.literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
    c=Case(tmp_path);s=RecoverySource();ref=c.publish(s.content,'synthetic_recovery_control221')
    c.context=replace(c.context,received_record_refs=(*c.context.received_record_refs,ref),
        assignment={**c.context.assignment,'requested_calibration_recovery_components':['recovery']})
    args=rebind(s.args(),{s.reference:ref});repo=LiteratureCalibrationRecoveryRepository(c.store,c.context.run_id)
    out=repo.populate(c.context,args,'existing_recovery');c.admit(out);row=out['result']['cells'][0]
    c.rows[(row['sheet_ref'],row['component'])]=row
    a=c.args(['estimate_recovery_test','fully_corrected_activity_reference_contrast'])
    a['estimates']['recovery_test']={'kind':'received_component','namespace':'literature_calibration_recovery_cells',
        'sheet_ref':row['sheet_ref'],'component':'recovery'}
    d=c.read(a);r=cells(populate_common_assessment(d))
    assert r['estimate_recovery_test']['value']==.98
    assert 'correction_conversion_unimplemented' in r['fully_corrected_activity_reference_contrast']['implementation_reasons']
    assert d['estimates']['recovery_test']['source_missing_reasons']==[]


def test_broad_actual218_construct_keeps_native_partial_and_reports_scope_gap(tmp_path):
    c=Case(tmp_path);source,a,_=original(1);a=rebind(a,{source.reference:c.source})
    out=c.product.populate(c.context,a,'actual_broad_construct');c.admit(out)
    for row in out['result']['cells']:c.rows[(row['sheet_ref'],row['component'])]=row
    args=c.args(['estimate_product_test','product_reference_contrast'])
    args['estimates']['product_test']['sheet_ref']=out['result']['sheet_ref']
    r=cells(populate_common_assessment(c.read(args)))
    assert r['estimate_product_test']['value']==92 and r['product_reference_contrast']['value'] is None
    assert 'unrequested_numerical_scope_unresolved' in r['product_reference_contrast']['implementation_reasons']
    assert 'received_construct_unresolved' not in r['product_reference_contrast']['source_missing_reasons']


def test_separate_substrate_uncertainty_matches_independent_directional_oracle(tmp_path):
    from decimal import Decimal, localcontext
    c=Case(tmp_path);a=c.args(['binding_only_residual_variance','binding_only_standardized_residual','binding_only_log_residual'])
    raw=b'<p>test free substrate 1600 uM</p>';ref=c.publish(raw,'synthetic_separate_substrate221')
    c.context=replace(c.context,received_record_refs=(*c.context.received_record_refs,ref))
    s=a['estimates']['free_substrate_test'];s.update(record=c.witness(3,len(raw)-4,ref),
        row_label=c.find('test',ref=ref),quantity_label=c.find('free substrate',ref=ref),unit=c.find('uM',ref=ref),
        number={'witness':c.find('1600',ref=ref),'number_start':0,'number_end':4})
    a['model'].update(substrate_ownership='separate_owners',substrate_uncertainty='selected_estimate_covariance')
    d=c.read(a);roles=['product_test','product_reference','Kd_test','Kd_reference','free_substrate_test','free_substrate_reference']
    modes=((Fraction(2),Fraction(1),Fraction(3),Fraction(1),Fraction(20),Fraction(-10)),
        (Fraction(-1),Fraction('.4'),Fraction('-.5'),Fraction('.3'),Fraction(-15),Fraction(25)))
    matrix=[[float(sum(mode[i]*mode[j] for mode in modes)) for j in range(6)] for i in range(6)]
    a['covariance_source_refs']=[c.covariance(d,roles,matrix,'known')]
    r=cells(populate_common_assessment(c.read(a)))
    with localcontext() as ctx:
        ctx.prec=65;values=list(map(Decimal,['92','206','34','1.8','1600','2000']));h=Decimal('1e-10')
        def f(v):
            pt,pr,kt,kr,st,sr=v
            return (pt/pr).ln()-(st/(st+kt)).ln()+(sr/(sr+kr)).ln()
        oracle=Decimal(0)
        for mode in modes:
            direction=[Decimal(x.numerator)/Decimal(x.denominator) for x in mode]
            hi=[x+h*v for x,v in zip(values,direction)];lo=[x-h*v for x,v in zip(values,direction)]
            oracle+=((f(hi)-f(lo))/(2*h))**2
    assert r['binding_only_residual_variance']['conditional_value']==pytest.approx(float(oracle),rel=1e-13)
    assert r['binding_only_standardized_residual']['conditional_value']<0
    # Unknown covariance preserves the measured/model discrepancy without z.
    a['covariance_source_refs']=[c.covariance(d,roles,None,'unknown')]
    r=cells(populate_common_assessment(c.read(a)))
    assert r['binding_only_log_residual']['conditional_value'] is not None
    assert r['binding_only_standardized_residual']['conditional_value'] is None
    assert 'covariance_status_unknown' in r['binding_only_residual_variance']['implementation_reasons']
    # S held fixed is an explicit conditional uncertainty term even when the
    # synthetic caller supplies supported mean-model interpretations.
    a['model'].update(substrate_uncertainty='fixed_scenario',scope='supported_physical')
    a['model']['assumptions']={k:c.meaning('supported') for k in COMMON_ASSUMPTIONS}
    for arm in ('reference','test'):a['estimates']['free_substrate_'+arm]['source_kind']='synthetic_fixture'
    a['covariance_source_refs']=[c.covariance(c.read({**a,'covariance_source_refs':[]}),roles,matrix,'known')]
    r=cells(populate_common_assessment(c.read(a)))
    assert r['binding_only_log_residual']['value'] is not None
    assert r['binding_only_residual_variance']['value'] is None
    assert r['binding_only_residual_variance']['conditional_value'] is not None


def test_pure_operation_factory_retains_only_its_original_two_branches():
    from gene_annotation_episode.literature_compiled_assay_inputs import compiled_assay_operation_schema
    assert len(compiled_assay_operation_schema()['anyOf'])==2
    assert COMMON_REQUEST not in json.dumps(compiled_assay_operation_schema())


def test_root224_model_domain_causes_reach_all_affected_composites(tmp_path):
    c=Case(tmp_path)
    requested=['estimate_product_test','estimate_Kd_test','product_reference_contrast','occupancy_reference_contrast',
        'post_binding_residual_ratio','binding_only_log_residual','binding_only_residual_variance','fully_corrected_activity_reference_contrast']
    for bad in ('0','-1'):
        a=c.args(requested)
        raw=('<table><tr><th>Construct</th><th>Kd(uM)</th></tr><tr><td>T252N</td><td>'+bad+'</td></tr></table><p>Spectral titration.</p>').encode()
        ref=c.publish(raw,'synthetic_domain_Kd221');c.context=replace(c.context,received_record_refs=(*c.context.received_record_refs,ref))
        s=a['estimates']['Kd_test'];s.update(source_kind='synthetic_fixture',row_label=c.find('T252N',ref=ref),
            quantity_label=c.find('Kd(uM)',ref=ref),unit=c.find('uM',ref=ref),method=c.find('Spectral titration.',ref=ref),
            number={'witness':c.find(bad,raw.index(b'<td>'+bad.encode()),ref),'number_start':0,'number_end':len(bad)},reported_spread=None)
        r=cells(populate_common_assessment(c.read(a)))
        assert r['estimate_Kd_test']['value']==float(bad) and r['estimate_product_test']['value']==92
        assert r['product_reference_contrast']['value'] is not None
        for name in requested[3:]:
            assert r[name]['value'] is None and r[name]['conditional_value'] is None
            assert 'positive_operand_required' in r[name]['implementation_reasons'],(name,r[name])
            assert 'source_number_unavailable' not in r[name]['source_missing_reasons']
    a=c.args(requested);raw=b'<p>shared free substrate 0 uM</p>'
    ref=c.publish(raw,'synthetic_domain_S221');c.context=replace(c.context,received_record_refs=(*c.context.received_record_refs,ref))
    for arm in ('reference','test'):
        a['estimates']['free_substrate_'+arm].update(source_kind='synthetic_fixture',record=c.witness(3,len(raw)-4,ref),
            row_label=c.find('shared',ref=ref),quantity_label=c.find('free substrate',ref=ref),unit=c.find('uM',ref=ref),
            number={'witness':c.find('0',ref=ref),'number_start':0,'number_end':1})
    r=cells(populate_common_assessment(c.read(a)))
    for name in requested[3:]:assert 'positive_operand_required' in r[name]['implementation_reasons']


def test_root224_complete_reader_name_scope_regressions_preserve_source_and_true_names(tmp_path):
    c=Case(tmp_path)
    for token,field,safe in [('5-fold','product_or_ligand',False),('Kd34uM','construct',False),
        ('IC50_5uM','construct',False),('5-methyl-uridine','product_or_ligand',True),
        ('5-exo-hydroxycamphor','product_or_ligand',True),('P450cam','molecule',True),('T252N/V253T','construct',True)]:
        raw=('<p>'+token+'</p>').encode();ref=c.publish(raw,'synthetic_root224_name_scope')
        c.context=replace(c.context,received_record_refs=(*c.context.received_record_refs,ref))
        a=c.args(['product_reference_contrast']);w=c.witness(3,len(raw)-4,ref);a['assertion'][field]=w
        d=c.read(a);r=populate_common_assessment(d)
        shown=next(x for x in r['context'] if x['field']=='assessment.assertion.'+field)
        assert d['request']['assertion'][field]['quote']==token
        assert (token in shown['display_text']) is safe
        assert (shown['implementation_status']=='numerical_scope_unresolved') is not safe
