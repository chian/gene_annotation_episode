"""Original XLSX/source-oracle checks and explicitly synthetic edge arrangements."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_rate_observation_inputs import (
    GRID_INPUT_VERSION, read_reported_rate_grid, validate_reported_rate_grid_extraction,
    reported_rate_grid_population_schema)
from gene_annotation_episode.literature_rate_observation_calculations import (
    _grid_fit, populate_reported_curve_precision, reported_curve_precision_sheet_schema)

ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT/'research/experimental_scoring_review_2026-10-23/a105_precision_population_case_225'
ART=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_reported_curve_precision_228'
ORACLE=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_precision_population_review_227/ROOT_NUMERICAL_ORACLES_001.json'
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def artifact(raw):return 'artifact_'+hashlib.sha256(raw).hexdigest()
def label(address,text):return {'cell':address,'expected_text':text}
def xlabel(address,text):return {'kind':'xlsx_label',**label(address,text)}


def source_setup():
    # Retained source witnesses supply locations/meanings only, never numeric
    # arguments to the reader. Every operand is reread from the original XLSX.
    packet=json.loads((CASE/'SOURCE_PACKET_001.json').read_text())
    raw=(CASE/'originals/S1Data.xlsx').read_bytes()
    context=(CASE/'originals/article_text.txt').read_bytes(); ar=artifact(context)
    def span(name):
        w=packet['article_witnesses'][name]
        return {'kind':'context_span','source_ref':'source_'+'2'*24,'artifact_ref':ar,
                'start':w['start'],'end':w['end'],'quote':w['quote']}
    caption=span('S17_caption'); methods=span('main_mutant_kinetic_method')
    args={'version':GRID_INPUT_VERSION,'source_ref':'source_'+'1'*24,
        'source_kind':'primary_source','worksheet':'Sheet1',
        'panel':label('A189',packet['selected_headers']['A189']['value']),
        'subject':label('Q191','PK_WT-DHA'),
        'native_rate_label':label('B190','NADH consumption rate µmol min-1'),
        'curves':[{'header':label(c+'192','data-'+str(j+1))} for j,c in enumerate('RST')],
        'points':[{'concentration_cell':'Q'+str(i),'rate_cells':[c+str(i) for c in 'RST']} for i in range(193,206)],
        'rate_unit':{'code':'umol/min','witness':xlabel('B190','NADH consumption rate µmol min-1')},
        'concentration_unit':{'code':'mM','witness':caption},
        'endpoint_relationship':{'status':'conflicting','witnesses':[xlabel('B190','NADH consumption rate µmol min-1'),methods]},
        'curve_sampling':{'status':'stipulated_sensitivity','assumption':'iid_reported_curve_vectors',
            'source_claim':'not_established','witnesses':[caption]}}
    docs=[{'source_ref':'source_'+'2'*24,'artifact_ref':ar,'content':context}]
    return raw,args,docs,packet


def extract(raw=None,args=None,docs=None):
    native,a,d,_=source_setup()
    return read_reported_rate_grid(native if raw is None else raw,a if args is None else args,
        artifact_ref=artifact(native if raw is None else raw),context_documents=d if docs is None else docs)


def select(scope,component,**kw):return {'scope':scope,'component':component,**kw}
def run(data,selectors,model='unweighted_positive_km_mm'):
    return populate_reported_curve_precision(data,{'version':'a105_reported_curve_precision_request_v1',
        'fit_model':model,'requested_components':selectors})
def values(sheet):return [r['conditional_value'] if r['status']=='conditional_scenario' else r['value'] for r in sheet['cells']]


def edit_workbook(mutator):
    raw,_,_,_=source_setup(); out=io.BytesIO()
    with ZipFile(io.BytesIO(raw)) as original,ZipFile(out,'w',ZIP_DEFLATED) as target:
        for name in original.namelist():
            content=original.read(name)
            if name=='xl/worksheets/sheet1.xml':
                sheet=ET.fromstring(content); cells={c.get('r'):c for c in sheet.findall('m:sheetData/m:row/m:c',NS)}
                mutator(sheet,cells); content=ET.tostring(sheet,encoding='utf-8')
            target.writestr(name,content)
    return out.getvalue()


def test_original_cells_custody_and_exact_statistics():
    raw,args,docs,packet=source_setup();data=extract(raw,args,docs)
    assert len(data['curves'])==3 and len(data['points'])==13
    assert data['custody']['workbook_sha256']==hashlib.sha256(raw).hexdigest()
    assert data['custody']['member_sha256']==packet['xlsx_members']['xl/worksheets/sheet1.xml']['sha256']
    for source,point in zip(packet['selected_points'],data['points']):
        assert point['concentration']['witness']['raw_value']==source['concentration']['raw_value']
        for a,b in zip(source['rate_entries'],point['entries']):
            assert b['quantity']['witness']['raw_value']==a['raw_value']
    selectors=[select('point',component,concentration_cell='Q'+str(i)) for i in range(193,206) for component in ('mean','sample_variance','sample_sd','cv')]
    sheet=run(data,selectors);validate_schema(sheet,reported_curve_precision_sheet_schema())
    for i,point in enumerate(data['points']):
        ys=[Fraction(q['quantity']['witness']['raw_value']) for q in point['entries']]
        mean=sum(ys)/3;var=sum((y-mean)**2 for y in ys)/2
        a,b,sd,cv=sheet['cells'][i*4:i*4+4]
        assert Fraction(**{k:int(v) for k,v in a['exact_value'].items()})==mean
        assert Fraction(**{k:int(v) for k,v in b['exact_value'].items()})==var
        assert sd['value']==pytest.approx(math.sqrt(float(var)),rel=1e-14)
        assert cv['value']==pytest.approx(math.sqrt(float(var))/float(mean),rel=1e-14)
    assert values(sheet)[15]==pytest.approx(.03488479236954927)
    assert values(sheet)[-1]==pytest.approx(.18961065720324072)


def test_independent_root227_estimators_full_covariance_and_signed_terms():
    oracle=json.loads(ORACLE.read_text());data=extract(); selectors=[]
    for c in 'RST':
        selectors += [select('curve',p,curve_header_cell=c+'192') for p in ('Vmax','Km')]
    for estimator in ('mean_of_reported_curve_fits','fit_of_point_means'):
        selectors += [select('estimator',p,estimator=estimator) for p in ('Vmax','Km','log_efficiency_variance')]
        selectors += [select('variance_term','signed_log_efficiency_variance_term',estimator=estimator,left_parameter=a,right_parameter=b) for a in ('Vmax','Km') for b in ('Vmax','Km')]
    selectors += [select('parameter_covariance','covariance',estimator='fit_of_point_means',left_parameter=a,right_parameter=b) for a in ('Vmax','Km') for b in ('Vmax','Km')]
    sheet=run(data,selectors); result=values(sheet)
    for j,theta in enumerate(oracle['per_column_fits']):
        assert result[2*j:2*j+2]==pytest.approx([float(v) for v in theta],rel=2e-10)
    assert result[6:8]==pytest.approx([float(v) for v in oracle['mean_of_fitted_parameter_vectors']],rel=2e-10)
    assert result[13:15]==pytest.approx([float(v) for v in oracle['fit_to_point_means']],rel=2e-10)
    assert result[8]==pytest.approx(float(oracle['conditional_log_variance_mean_parameters']),rel=2e-9)
    assert result[15]==pytest.approx(float(oracle['conditional_log_variance_fit_to_means']),rel=2e-9)
    assert result[8]!=pytest.approx(result[15],rel=1e-2)
    assert math.fsum(result[9:13])==pytest.approx(result[8],rel=1e-13)
    assert math.fsum(result[16:20])==pytest.approx(result[15],rel=1e-13)
    assert result[10]<0 and result[11]<0
    target=[float(v) for row in oracle['conditional_fit_to_means_parameter_covariance'] for v in row]
    assert result[-4:]==pytest.approx(target,rel=2e-9)
    assert all(row['value'] is None for row in sheet['cells'] if row['status']=='conditional_scenario')
    assert len({sheet['cells'][6]['estimator_key'],sheet['cells'][13]['estimator_key']})==2


def test_all13_independent_finite_difference_refits():
    data=extract(); xs=[Fraction(p['concentration']['witness']['raw_value']) for p in data['points']]
    ys=[sum(Fraction(e['quantity']['witness']['raw_value']) for e in p['entries'])/3 for p in data['points']]
    rows=run(data,[select('sensitivity','d_parameter_d_point_mean',estimator='fit_of_point_means',parameter=a,concentration_cell='Q'+str(193+i)) for a in ('Vmax','Km') for i in range(13)])['cells']
    # Finite-difference estimator refits rather than repeating analytic Hessian.
    for i in range(13):
        h=Fraction(1,10**8);high=list(ys);low=list(ys);high[i]+=h;low[i]-=h
        a=_grid_fit(xs,high);b=_grid_fit(xs,low)
        assert a['reason'] is None and b['reason'] is None
        for j in range(2):
            observed=(a['theta'][j]-b['theta'][j])/(2*float(h))
            assert rows[j*13+i]['value']==pytest.approx(observed,rel=3e-6,abs=2e-8)


def test_residual_identity_full_cross_covariance_and_rank_two():
    data=extract();sels=[select('grid',c) for c in ('all_reported_residual_SS','within_concentration_reported_entry_SS','mean_curve_fit_residual_SS_times_curve_count')]
    sels += [select('reported_curve_covariance','sample_covariance',left_concentration_cell='Q'+str(193+i),right_concentration_cell='Q'+str(193+j)) for i in range(13) for j in range(13)]
    vals=values(run(data,sels));assert vals[0]==pytest.approx(vals[1]+vals[2],rel=1e-13)
    assert vals[4]!=0  # explicit off-diagonal covariance retained
    # Exact3x3 determinant vanishes for3 centered reporting vectors (rank<=2).
    matrix=[[Fraction(**{k:int(v) for k,v in run(data,[sels[3+i*13+j]],model='none')['cells'][0]['exact_value'].items()}) for j in range(3)] for i in range(3)]
    det=sum(matrix[0][i]*(matrix[1][(i+1)%3]*matrix[2][(i+2)%3]-matrix[1][(i+2)%3]*matrix[2][(i+1)%3]) for i in range(3))
    assert det==0


def test_complete_aliases_and_equal_values_distinct_cells():
    _,args,docs,_=source_setup();args['points'].append(deepcopy(args['points'][0]));args['curves'].append(deepcopy(args['curves'][0]))
    for point in args['points']:point['rate_cells'].append(point['rate_cells'][0])
    data=extract(args=args,docs=docs);assert len(data['points'])==13 and len(data['curves'])==3
    assert data['points'][0]['selection_indices']==[0,13]
    assert data['curves'][0]['selection_indices']==[0,3]
    raw=edit_workbook(lambda _,cells: setattr(cells['S193'].find('m:v',NS),'text',cells['R193'].find('m:v',NS).text))
    _,a,_,_=source_setup();a['source_kind']='synthetic_fixture';d=extract(raw,a)
    q=[e['quantity'] for e in d['points'][0]['entries']]
    assert q[0]['exact_value']==q[1]['exact_value'] and q[0]['measurement_key']!=q[1]['measurement_key']
    assert values(run(d,[select('point','selected_entry_count',concentration_cell='Q193')]))==[3]


@pytest.mark.parametrize('kind,status,reason',[('absent','missing','source_measurement_unavailable'),('ND','not_detected','nondetection_without_point'),('<0.1','censored','censored_measurement'),('formula','unsupported_cell','formula_measurement_unsupported'),('error','unsupported_cell','source_error_cell')])
def test_nonpoints_preserve_roster_unaffected_partials(kind,status,reason):
    def mutate(sheet,cells):
        cell=cells['R193']
        if kind=='absent':
            next(r for r in sheet.findall('m:sheetData/m:row',NS) if r.get('r')=='193').remove(cell)
        elif kind=='formula':ET.SubElement(cell,'{'+NS['m']+'}f').text='1+1'
        else:
            for child in list(cell):cell.remove(child)
            if kind=='error':cell.set('t','e');ET.SubElement(cell,'{'+NS['m']+'}v').text='#VALUE!'
            else:
                cell.set('t','inlineStr');ET.SubElement(ET.SubElement(cell,'{'+NS['m']+'}is'),'{'+NS['m']+'}t').text=kind
    raw=edit_workbook(mutate);_,args,_,_=source_setup();args['source_kind']='synthetic_fixture';data=extract(raw,args)
    q=data['points'][0]['entries'][0]['quantity'];assert q['status']==status and q['unavailable_reason']==reason
    assert len(data['points'])==13 and len(data['points'][0]['entries'])==3
    if kind.startswith('<'):assert q['exact_limit']=={'numerator':'1','denominator':'10'}
    sels=[select('point',c,concentration_cell='Q193') for c in ('mean','available_point_mean','selected_entry_count','available_point_count')]
    sels += [select('curve','Vmax',curve_header_cell=c+'192') for c in 'RS']
    sels += [select('estimator','log_efficiency_variance',estimator='fit_of_point_means')]
    sheet=run(data,sels);vals=values(sheet)
    assert vals[0] is None and vals[1] is not None and vals[2:4]==[3,2]
    assert vals[4] is None and vals[5]>0 and vals[6] is None


@pytest.mark.parametrize('status',['unknown','conflicting','supported','stipulated_sensitivity'])
def test_sampling_semantics_and_native_partial(status):
    _,args,docs,_=source_setup();s=args['curve_sampling'];s['status']=status
    if status=='supported':s['source_claim']='iid_reporting_vectors_supported'
    if status=='unknown':s.update(assumption='none',source_claim='unknown',witnesses=[])
    if status=='conflicting':s['source_claim']='conflicting'
    data=extract(args=args,docs=docs)
    sheet=run(data,[select('estimator','Vmax',estimator='fit_of_point_means'),select('estimator','log_efficiency_variance',estimator='fit_of_point_means')])
    assert sheet['cells'][0]['value']>0
    if status in ('unknown','conflicting'):
        assert sheet['cells'][1]['status']=='unavailable'
        assert sheet['cells'][1]['relationship_reasons']==['sampling_model_'+status]
    else:
        assert sheet['cells'][1]['status']=='conditional_scenario'
        assert sheet['cells'][1]['variance_status']=='estimated'
    assert sheet['calculation_metadata']['physical_preparation_count'] is None


def test_unit_rate_scaling_invariance():
    original=extract();selectors=[select('estimator',c,estimator='fit_of_point_means') for c in ('Vmax','Km','log_efficiency_variance')]
    base=values(run(original,selectors))
    def mutate(_,cells):
        for i in range(193,206):
            for col,factor in [('Q',Fraction(1000)),*[(c,Fraction(1000)) for c in 'RST']]:
                node=cells[col+str(i)].find('m:v',NS);node.text=str(float(Fraction(node.text)*factor))
    raw=edit_workbook(mutate);_,args,_,_=source_setup();args['source_kind']='synthetic_fixture'
    # These are explicitly synthetic unit conversions of the workbook itself.
    new_label='NADH consumption rate nmol min-1'
    def relabel(content):
        output=io.BytesIO()
        with ZipFile(io.BytesIO(content)) as z,ZipFile(output,'w',ZIP_DEFLATED) as target:
            for name in z.namelist():
                body=z.read(name)
                if name=='xl/worksheets/sheet1.xml':
                    sheet=ET.fromstring(body);cell=next(c for c in sheet.findall('m:sheetData/m:row/m:c',NS) if c.get('r')=='B190')
                    for child in list(cell):cell.remove(child)
                    cell.set('t','inlineStr');ET.SubElement(ET.SubElement(cell,'{'+NS['m']+'}is'),'{'+NS['m']+'}t').text=new_label
                    body=ET.tostring(sheet,encoding='utf-8')
                target.writestr(name,body)
        return output.getvalue()
    raw=relabel(raw)
    args['native_rate_label']=label('B190',new_label)
    args['rate_unit']={'code':'nmol/min','witness':xlabel('B190',new_label)}
    args['endpoint_relationship']['witnesses'][0]=xlabel('B190',new_label)
    context=b'Synthetic converted concentration unit: uM.'
    witness={'kind':'context_span','source_ref':'source_'+'3'*24,'artifact_ref':artifact(context),
             'start':0,'end':len(context),'quote':context.decode()}
    args['concentration_unit']={'code':'uM','witness':witness}
    _,_,docs,_=source_setup();docs.append({'source_ref':witness['source_ref'],'artifact_ref':artifact(context),'content':context})
    scaled=values(run(extract(raw,args,docs),selectors))
    assert scaled[:2]==pytest.approx([v*1000 for v in base[:2]],rel=1e-10)
    assert scaled[2]==pytest.approx(base[2],rel=1e-10)


def test_authentication_layout_closed_schema_and_detached_rejections():
    raw,args,docs,_=source_setup()
    with pytest.raises(ExperimentalContractError,match='source_artifact_hash_mismatch'):
        read_reported_rate_grid(raw,args,artifact_ref='artifact_'+'0'*64,context_documents=docs)
    broken=deepcopy(docs);broken[0]['content']+=b'x'
    with pytest.raises(ExperimentalContractError,match='context_artifact_hash_mismatch'):extract(args=args,docs=broken)
    broken=deepcopy(args);broken['concentration_unit']['witness']['quote']+='x'
    with pytest.raises(ExperimentalContractError,match='context_span_mismatch'):extract(args=broken)
    broken=deepcopy(args);broken['points'][0]['rate_cells'][0]='S193'
    with pytest.raises(ExperimentalContractError,match='association_mismatch'):extract(args=broken)
    broken=deepcopy(args);broken['measured_value']=4
    with pytest.raises(ContractError):validate_schema(broken,reported_rate_grid_population_schema())
    data=extract();data['points'][0]['entries'][0]['quantity']['exact_value']['numerator']='1'
    with pytest.raises(ExperimentalContractError,match='detached_quantity_mismatch'):validate_reported_rate_grid_extraction(data)
    with pytest.raises(ExperimentalContractError,match='selected_point_required'):run(extract(),[select('point','mean',concentration_cell='A1')])


def test_solver_limits_no_model_and_legacy_prefix_preservation():
    for name,original in [('literature_rate_observation_inputs.py','ORIGINAL_INPUTS_001.py'),('literature_rate_observation_calculations.py','ORIGINAL_CALCULATIONS_001.py')]:
        assert (ROOT/'gene_annotation_episode'/name).read_bytes().startswith((ART/original).read_bytes())
    data=extract();sheet=run(data,[select('point','mean',concentration_cell='Q193'),select('curve','Vmax',curve_header_cell='R192')],model='none')
    assert sheet['cells'][0]['value']>0 and sheet['cells'][1]['relationship_reasons']==['model_not_selected']
    assert _grid_fit([Fraction(1),Fraction(2),Fraction(3)],[Fraction(-1)]*3)['reason']=='fit_nonpositive_response'
    assert _grid_fit([Fraction(0),Fraction(2),Fraction(3)],[Fraction(1)]*3)['reason']=='positive_concentrations_required'
    assert _grid_fit([Fraction(1)]*3,[Fraction(1)]*3)['reason']=='insufficient_distinct_concentrations'
    assert _grid_fit([Fraction(1),Fraction(2),Fraction(3)],[Fraction(1),Fraction(2),Fraction(3)])['reason']=='fit_domain_exhausted'


def scaled_source(xexponent=0,yexponent=0):
    from decimal import Decimal, localcontext
    def mutate(_,cells):
        with localcontext() as ctx:
            ctx.prec=60
            for i in range(193,206):
                for c in 'QRST':
                    node=cells[c+str(i)].find('m:v',NS)
                    node.text=str(Decimal(node.text)*(Decimal(10)**(xexponent if c=='Q' else yexponent)))
    raw=edit_workbook(mutate);_,args,_,_=source_setup();args['source_kind']='synthetic_fixture'
    return extract(raw,args)


@pytest.mark.parametrize('exponent',[-150,150])
def test_cross_stage_extreme_scale_correlation_and_logvariance(exponent):
    selectors=[select('parameter_covariance','correlation',estimator=e,left_parameter='Vmax',right_parameter='Km') for e in ('reported_curve_fit_distribution','mean_of_reported_curve_fits','fit_of_point_means')]
    selectors += [select('estimator',c,estimator='fit_of_point_means') for c in ('native_efficiency','log_efficiency_variance','log_efficiency_standard_uncertainty')]
    base=values(run(extract(),selectors));scaled=values(run(scaled_source(exponent,exponent),selectors))
    assert all(v is not None and math.isfinite(v) for v in scaled)
    assert scaled==pytest.approx(base,rel=2e-8)
    assert scaled[0]!=0


@pytest.mark.parametrize('exponent',[-400,400])
def test_range_failure_keeps_dimensionless_native_partial(exponent):
    data=scaled_source(0,exponent)
    selectors=[select('point',c,concentration_cell='Q196') for c in ('mean','sample_sd','cv')]
    selectors += [select('estimator',c,estimator='fit_of_point_means') for c in ('Vmax','native_efficiency','log_efficiency_variance')]
    sheet=run(data,selectors);rows=sheet['cells']
    assert rows[0]['value'] is None and rows[1]['value'] is None
    assert rows[2]['value']==pytest.approx(.03488479236954927)
    assert rows[2]['model_keys']==[]
    assert rows[0]['implementation_reasons']==['numerical_model_range']
    assert rows[0]['source_missing_reasons']==[]
    assert all(row['status']=='unavailable' for row in rows[3:])


def test_selected_meaning_validation_and_ambiguous_units():
    _,args,docs,_=source_setup();wrong=deepcopy(args);wrong['rate_unit']['code']='nmol/min'
    with pytest.raises(ExperimentalContractError,match='grid_unit_code_witness_mismatch'):extract(args=wrong)
    wrong=deepcopy(args);wrong['concentration_unit']['code']='uM'
    with pytest.raises(ExperimentalContractError,match='grid_unit_code_witness_mismatch'):extract(args=wrong)
    text=b'Two assay units: mM and uM.';new={'kind':'context_span','source_ref':'source_'+'4'*24,
        'artifact_ref':artifact(text),'start':0,'end':len(text),'quote':text.decode()}
    wrong=deepcopy(args);wrong['concentration_unit']['witness']=new
    with pytest.raises(ExperimentalContractError,match='grid_unit_meaning_ambiguous'):
        extract(args=wrong,docs=docs+[{'source_ref':new['source_ref'],'artifact_ref':artifact(text),'content':text}])
    wrong=deepcopy(args);wrong['curve_sampling']['status']='supported'
    with pytest.raises(ExperimentalContractError,match='grid_supported_sampling_claim_required'):extract(args=wrong)
    wrong=deepcopy(args);wrong['curve_sampling']['witnesses']=[]
    with pytest.raises(ExperimentalContractError,match='grid_explicit_iid_model_provenance_required'):extract(args=wrong)
    unknown=deepcopy(args);unknown['concentration_unit']={'code':'unknown','witness':None}
    rows=run(extract(args=unknown),[select('point','mean',concentration_cell='Q193'),select('curve','Km',curve_header_cell='R192')])['cells']
    assert rows[0]['value']>0 and rows[1]['relationship_reasons']==['concentration_unit_unknown']
    assert rows[1]['implementation_reasons']==[]
    detached=extract();detached['context_witnesses']=[]
    with pytest.raises(ExperimentalContractError,match='grid_detached_context_mismatch'):validate_reported_rate_grid_extraction(detached)


def test_defined_zero_variance_and_nonpositive_cv_are_not_software_failures():
    def mutate(_,cells):
        for i in range(193,206):
            for c in 'ST':cells[c+str(i)].find('m:v',NS).text=cells['R'+str(i)].find('m:v',NS).text
    raw=edit_workbook(mutate);_,args,_,_=source_setup();args['source_kind']='synthetic_fixture'
    selectors=[select('estimator',c,estimator='fit_of_point_means') for c in ('log_efficiency_variance','log_efficiency_standard_uncertainty')]
    selectors += [select('parameter_covariance','correlation',estimator='reported_curve_fit_distribution',left_parameter='Vmax',right_parameter='Km')]
    rows=run(extract(raw,args),selectors)['cells'];assert values({'cells':rows})[:2]==[0,0]
    assert rows[2]['relationship_reasons']==['zero_covariance_variance'] and rows[2]['implementation_reasons']==[]
    def negative(_,cells):
        for c in 'RST':cells[c+'193'].find('m:v',NS).text='-1'
    rows=run(extract(edit_workbook(negative),args),[select('point',c,concentration_cell='Q193') for c in ('mean','cv')])['cells']
    assert rows[0]['value']==-1 and rows[1]['relationship_reasons']==['nonpositive_mean']
    assert rows[1]['unit']=='dimensionless' and rows[1]['implementation_reasons']==[]


def test_incomplete_source_reasons_distinguish_present_bounds_from_reader_limits():
    for text,expected,bucket in [('ND','nondetection_without_point','source_missing_reasons'),('<1','censored_measurement','source_missing_reasons'),('12.3','numeric_cell_type_required','implementation_reasons')]:
        def mutate(_,cells):
            c=cells['R193']
            for q in list(c):c.remove(q)
            c.set('t','inlineStr');ET.SubElement(ET.SubElement(c,'{'+NS['m']+'}is'),'{'+NS['m']+'}t').text=text
        _,args,_,_=source_setup();args['source_kind']='synthetic_fixture'
        row=run(extract(edit_workbook(mutate),args),[select('point','mean',concentration_cell='Q193')])['cells'][0]
        assert expected in row[bucket]
        assert 'source_measurement_unavailable' not in row['source_missing_reasons']


def test_two_distinct_concentrations_can_identify_two_fit_parameters():
    # No arbitrary third-point quota: two parameters can have a full-rank
    # sensitivity at two distinct positive concentrations, without residual df.
    fit=_grid_fit([Fraction(1),Fraction(2)],[Fraction(1),Fraction(3,2)])
    assert fit['reason'] is None
    assert fit['theta']==pytest.approx([3,2],rel=1e-12)


def test_unit_denominators_are_not_silently_truncated():
    _,args,docs,_=source_setup()
    for code,text,field in [('umol/min','umol/min/mg','rate_unit'),('mM','mM/min','concentration_unit')]:
        raw=text.encode();w={'kind':'context_span','source_ref':'source_'+'5'*24,
            'artifact_ref':artifact(raw),'start':0,'end':len(raw),'quote':text}
        wrong=deepcopy(args);wrong[field]={'code':code,'witness':w}
        with pytest.raises(ExperimentalContractError,match='grid_unit_spelling_unsupported'):
            extract(args=wrong,docs=docs+[{'source_ref':w['source_ref'],'artifact_ref':artifact(raw),'content':raw}])


def test_unaffected_covariance_pair_survives_other_missing_row():
    def mutate(sheet,cells):
        next(r for r in sheet.findall('m:sheetData/m:row',NS) if r.get('r')=='193').remove(cells['R193'])
    _,args,_,_=source_setup();args['source_kind']='synthetic_fixture';data=extract(edit_workbook(mutate),args)
    row=run(data,[select('reported_curve_covariance','sample_covariance',left_concentration_cell='Q194',right_concentration_cell='Q195')])['cells'][0]
    assert row['value'] is not None and row['source_missing_reasons']==[]
    assert row['model_keys']==[]
