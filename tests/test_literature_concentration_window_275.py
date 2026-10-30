"""Bounded actual-reader/calculator checks for the released concentration window.

Retained original paper bytes are used only for the already reviewed case.
Text/covariance contrasts are explicitly synthetic engineering fixtures.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from gene_annotation_episode import literature_concentration_window_inputs as I
from gene_annotation_episode import literature_concentration_window_calculations as C
from gene_annotation_episode.literature_concentration_window_prompt import CONCENTRATION_WINDOW_TASK
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError

ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'verification/a105_concentration_window_275'
CASE=ROOT/'research/experimental_scoring_review_2026-10-23/a105_matched_estimator_source_260/originals'


def load(name):return json.loads((V/name).read_text())
def callback(sources):
    def read(ref,rep):
        assert rep=='original'
        data=sources[ref]
        return dict(artifact_ref='artifact:'+hashlib.sha256(data).hexdigest(),content=data)
    return read


@pytest.fixture
def original():
    selection=load('SOURCE_SELECTION_PROPOSAL_002.json')
    return selection,{
        'source:elife65773_original_fig6_xlsx':(CASE/'elife65773_fig6.xlsx').read_bytes(),
        'source:elife65773_original_html':(CASE/'elife65773.html').read_bytes()}


def run(selection,sources):
    extraction=I.read_concentration_window_inputs(selection,read_source=callback(sources))
    inputs=I.compile_concentration_window_inputs(extraction)
    sheet=C.populate_concentration_window(inputs)
    I.validate_concentration_window_extraction(extraction,selection=selection,read_source=callback(sources))
    I.validate_concentration_window_calculation_inputs(inputs,extraction=extraction)
    C.validate_concentration_window_sheet(sheet,inputs=inputs)
    return extraction,inputs,sheet


def cells(sheet):return {r['component']:r for r in sheet['cells']}
def qcell(sheet,name):return I._q(cells(sheet)[name]['exact_value'])


def synthetic(values=(120,60,4,61,2,14,3,33),unit='uM',time_unit='s'):
    """One finite text-table fixture, not another experimental paper."""
    template=load('SOURCE_SELECTION_PROPOSAL_002.json')
    numbers=[str(v) for v in values]
    header='<tr><th>time ('+time_unit+')</th><th>S ('+unit+')</th><th>T ('+unit+')</th><th>F ('+unit+')</th></tr>'
    rows=''.join('<tr>'+''.join('<td>'+numbers[i]+'</td>' for i in order)+'</tr>' for order in ((6,0,2,4),(7,1,3,5)))
    text='<p>synthetic enzyme assay; S to T; F fate</p><table>'+header+rows+'</table>'
    data=text.encode();reference='synthetic:window'
    def field(start,end):return dict(kind='text',source_ref=reference,representation='original',
        start=len(text[:start].encode()),end=len(text[:end].encode()),quote=text[start:end])
    context=field(3,text.index('</p>'))
    table=field(text.index('<table>'),len(text))
    def m(value):return dict(value=value,witnesses=[] if value=='unknown' else [deepcopy(context)])
    selection=deepcopy(template);selection.update(source_ref=reference,source_kind='synthetic_fixture',grid=None,
        covariance_source_ref=None,covariance_material='not_selected',evidence=[])
    for k in selection['assay']:
        if k not in ('arrangement','participants'):selection['assay'][k]=deepcopy(context) if k in ('molecule','construct','conditions','endpoint','calibration','normalization') else None
    selection['assay'].update(arrangement=m('single_preparation'),participants=[dict(identity=deepcopy(context),role='assayed_molecule',presence='present')])
    for model in selection['stoichiometry'].values():model.update(reaction=deepcopy(context),relationship=m('supported'))
    for p in selection['pair_relationships'].values():
        for k in p:p[k]['witnesses']=[deepcopy(context)]
    for p in selection['cross_relationships'].values():
        for k in p:p[k]['witnesses']=[deepcopy(context)]
    selection['timing']=dict(source_meaning=m('actual_sampling_time'),scenario=None)
    import re
    numeric=list(re.finditer(r'<td>(.*?)</td>',text))
    order=(1,5,2,6,3,7,0,4)
    headers=list(re.finditer(r'<th>(.*?)</th>',text))
    for index,role in enumerate(I.ROLES):
        match=numeric[order[index]];raw=match.group(1);f=field(match.start(1),match.end(1))
        raw_numeric=re.search(r'[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?',raw)
        ns=raw_numeric.start() if raw_numeric else 0;ne=raw_numeric.end() if raw_numeric else 0
        column=(1 if role.startswith('substrate') else 2 if role.startswith('total_product') else 3 if role.startswith('fate_product') else 0)
        h=headers[column]
        analyte=field(h.start(1),h.end(1))
        u=time_unit if column==0 else unit;us=text.index(u,h.start(1),h.end(1))
        coord_match=numeric[0 if role.endswith('start') else 4]
        selection['quantities'][role]=dict(number=None if raw_numeric is None else dict(field=f,number_start=ns,number_end=ne),
            unit=field(us,us+len(u)),record=deepcopy(table),analyte=analyte,
            coordinate=field(coord_match.start(1),coord_match.end(1)),measurement_identity=None,
            unit_association=m('source_header'),reading_meaning=m('reported_nondetection' if raw=='ND' else 'reported_point'),
            concentration_basis=m('coordinate' if column==0 else 'native_reaction_concentration'),uncertainty=[])
    return selection,{reference:data}


def covariance(selection,sources):
    e=I.read_concentration_window_inputs(selection,read_source=callback(sources))
    doc=load('SYNTHETIC_COVARIANCE_DOCUMENT_001.json')
    doc['owner_keys']=[e['quantities'][r]['owner_key'] for r in doc['roles']]
    doc['dependency_keys']=[e['quantities'][r]['dependency_keys'] for r in doc['roles']]
    selection['covariance_source_ref']='synthetic:joint_covariance'
    selection['covariance_material']='closed_joint_estimator_covariance_document'
    sources['synthetic:joint_covariance']=json.dumps(doc).encode()
    return doc


def test_exact_released_schemas_and_task():
    schemas=load('SCHEMAS_003.json')
    for name,factory in [('SELECTION',I.concentration_window_selection_schema),('EXTRACTION',I.concentration_window_extraction_schema),
        ('CALCULATION_INPUTS',I.concentration_window_calculation_inputs_schema),('SHEET',I.concentration_window_sheet_schema),
        ('COVARIANCE_DOCUMENT',I.concentration_window_covariance_schema)]:assert factory()==schemas[name]
    assert CONCENTRATION_WINDOW_TASK==(V/'TASK_PROPOSAL_001.txt').read_text().rstrip()
    assert len(CONCENTRATION_WINDOW_TASK.split('\n\n'))==3


def test_original_workbook_exact_numerics_and_meanings(original,tmp_path):
    selection,sources=original;e,i,s=run(selection,sources)
    expected={'substrate_loss':Fraction(100),'total_product_gain':Fraction(189,2),'fate_product_gain':Fraction(52,5),
        'chemical_discrepancy':Fraction(11,2),'chemical_ratio':Fraction(200,189),
        'chemical_relative_discrepancy':Fraction(11,189),'fate_fraction':Fraction(104,945),
        'coordinate_span':Fraction(49),'substrate_depletion_fraction':Fraction(1,2)}
    assert {n:qcell(s,n) for n in expected}==expected
    assert all(cells(s)[n]['origin']=='calculated' for n in expected)
    assert cells(s)['source_interval_average_substrate']['value'] is None
    assert I._q(cells(s)['scenario_interval_average_total_product']['conditional_exact_value'])==Fraction(810,7)
    assert s['scientific_context']==e['scientific_context']==i['scientific_context']
    assert s['scientific_context']['quantities']['substrate_start']['analyte']['scientific_text']=='NAD+'
    assert s['scientific_context']['assay']['molecule']['scientific_text']=='Wild-type PARP1'
    assert s['scientific_context']['stoichiometry']['total_product']['value']==1
    assert s['scientific_context']['stoichiometry']['total_product']['analyte']['scientific_text']=='nicotinamide (µM)'
    assert s['annotation_credit'] is None
    (tmp_path/'production_sheet.json').write_text(json.dumps(s))


def test_partial_survival_and_requested_scope(original):
    _,sources=original;selection=load('PARTIAL_CONTRAST_SELECTION_PROPOSAL_002.json')
    e,i,s=run(selection,sources);out=cells(s)
    assert qcell(s,'substrate_loss')==100 and qcell(s,'fate_product_gain')==Fraction(52,5)
    assert all(out[n]['status']=='unavailable' and out[n]['reasons']['relationship']==['pair_endpoint_comparability_unknown']
        for n in ('total_product_gain','chemical_ratio','fate_fraction'))
    assert list(out)==selection['requested_cells']
    assert not any(r in out for r in I.ROLES)
    for q in s['scientific_context']['quantities'].values():
        assert q['coordinate']['scientific_text'] is None
        assert all(w['scientific_text'] is None for w in q['reading_meaning']['witnesses'])


@pytest.mark.parametrize('part',('number_quote','method_quote','member','column','time_row','header','shared_header_row'))
def test_original_binding_negatives(original,part):
    selection,sources=original;q=selection['quantities']['substrate_start']
    if part=='number_quote':q['number']['field']['quote']='201'
    elif part=='method_quote':selection['assay']['conditions']['quote']='wrong'
    elif part=='member':q['number']['field']['worksheet_part']='xl/worksheets/sheet1.xml'
    elif part=='column':q['number']['field'].update(cell='B2',quote='2.8',decoded_end=3);q['number']['number_end']=3
    elif part=='time_row':q['coordinate'].update(cell='A5',quote='50',decoded_end=2)
    elif part=='header':q['analyte'].update(cell='B1',quote='ADPR',decoded_end=4)
    else:q['unit'].update(cell='D11')
    with pytest.raises(ValueError):I.read_concentration_window_inputs(selection,read_source=callback(sources))


def test_original_entire_byte_digest_reauthentication(original):
    selection,sources=original;e=I.read_concentration_window_inputs(selection,read_source=callback(sources))
    sources['source:elife65773_original_html']+=b'<!-- changed outside selected witnesses -->'
    with pytest.raises(ExperimentalContractError):I.validate_concentration_window_extraction(e,selection=selection,read_source=callback(sources))


def test_actual_original_html_number_binding(original):
    selection,sources=original
    raw=sources['source:elife65773_original_html'];a,b=222847,224328
    snippet=raw[a:b].decode();local=snippet.index('200 µM');start=a+len(snippet[:local].encode())
    field=dict(kind='text',source_ref='source:elife65773_original_html',representation='original',start=start,end=start+3,quote='200')
    # A mechanical read of the already reviewed shared HPLC protocol's NAD+ input;
    # no new trajectory or biological conclusion is inferred from this test.
    q=selection['quantities']['substrate_start']
    unit_pos=raw.index('µM'.encode(),start,b);label_pos=raw.rfind(b'NAD',a,start)
    def f(x,y):return dict(kind='text',source_ref=field['source_ref'],representation='original',start=x,end=y,quote=raw[x:y].decode())
    q.update(number=dict(field=field,number_start=0,number_end=3),unit=f(unit_pos,unit_pos+len('µM'.encode())),
        record=f(a,b),analyte=f(label_pos,label_pos+3),coordinate=None,
        unit_association=dict(value='same_record',witnesses=[f(a,b)]))
    selection['requested_cells']=['substrate_start']
    e,i,s=run(selection,sources)
    assert qcell(s,'substrate_start')==200
    assert e['quantities']['substrate_start']['locations'][0]['kind']=='text'


@pytest.mark.parametrize('unit,expected', [('M',1000000),('mM',1000),('uM',1),('µM',1),('μM',1),('nM',Fraction(1,1000)),('pM',Fraction(1,1000000)),('mol/L',1000000)])
def test_units_exact(unit,expected):
    selection,sources=synthetic(unit=unit)
    _,_,s=run(selection,sources)
    assert qcell(s,'substrate_loss')==60*expected


@pytest.mark.parametrize('unit',('uM/min','mg/mL','percent','m'))
def test_unsupported_dimensions_remain_unknown(unit):
    selection,sources=synthetic(unit=unit);e,i,s=run(selection,sources)
    assert e['quantities']['substrate_start']['value'] is None
    assert 'source_unit_unsupported' in cells(s)['substrate_loss']['reasons']['implementation']
    assert cells(s)['substrate_loss']['value'] is None


@pytest.mark.parametrize('raw,status,reason',[('&lt;60','bounded','bounded_arithmetic_unimplemented'),('~60','point','approximate_arithmetic_unimplemented'),('ND','nondetection',None)])
def test_qualified_and_nd(raw,status,reason):
    selection,sources=synthetic(values=(120,raw,4,61,2,14,3,33))
    e,i,s=run(selection,sources);assert e['quantities']['substrate_end']['status']==status
    assert cells(s)['substrate_loss']['value'] is None
    if reason:assert reason in cells(s)['substrate_loss']['reasons']['implementation']
    if raw=='ND':assert e['quantities']['substrate_end']['value'] is None


@pytest.mark.parametrize('raw,start,end',[('160',1,3),('6e2',0,1),('-60',1,3)])
def test_clipped_numeric_tokens(raw,start,end):
    selection,sources=synthetic(values=(120,raw,4,61,2,14,3,33));selection['quantities']['substrate_end']['number'].update(number_start=start,number_end=end)
    with pytest.raises(ExperimentalContractError,match='partial_source_numeric_token'):I.read_concentration_window_inputs(selection,read_source=callback(sources))


def test_unit_cannot_be_clipped_from_rate():
    selection,sources=synthetic(unit='uM/min')
    for q in selection['quantities'].values():
        if q['unit']['quote']=='uM/min':q['unit'].update(end=q['unit']['start']+2,quote='uM')
    with pytest.raises(ExperimentalContractError,match='source_unit_mismatch'):I.read_concentration_window_inputs(selection,read_source=callback(sources))


@pytest.mark.parametrize('literal',('120mg/mL','120%'))
def test_inline_incompatible_unit_cannot_be_overridden_by_header(literal):
    selection,sources=synthetic(values=(literal,60,4,61,2,14,3,33))
    with pytest.raises(ExperimentalContractError) as caught:
        I.read_concentration_window_inputs(selection,read_source=callback(sources))
    assert caught.value.code=='source_unit_mismatch'


def test_text_column_borrowing_fails():
    selection,sources=synthetic()
    selection['quantities']['substrate_start']['analyte']=deepcopy(selection['quantities']['total_product_start']['analyte'])
    with pytest.raises(ExperimentalContractError,match='source_quantity_column_mismatch'):I.read_concentration_window_inputs(selection,read_source=callback(sources))


def test_missing_unselected_and_unimplemented_are_distinct():
    selection,sources=synthetic();selection['quantities']['substrate_start']=None
    selection['quantities']['total_product_start']['number']=None
    selection.update(covariance_material='unsupported_observation_table',covariance_source_ref='synthetic:uncertainty_table')
    sources['synthetic:uncertainty_table']=b'raw observation table not a covariance document'
    _,_,s=run(selection,sources);out=cells(s)
    assert 'operand_not_selected' in out['substrate_loss']['reasons']['selection']
    assert 'number_unavailable' in out['total_product_gain']['reasons']['source']
    assert 'covariance_estimation_from_table_unimplemented' in out['fate_product_gain_variance']['reasons']['implementation']
    assert s['covariance_context']['source_ref']=='synthetic:uncertainty_table'
    assert s['covariance_context']['selection_status']=='selected'
    assert s['covariance_context']['variance_status'] is None
    assert s['covariance_context']['roles']==[]


@pytest.mark.parametrize('timing,scenario,source_ok,conditional_ok',[('actual_sampling_time',False,True,False),('unknown',False,False,False),('unknown',True,False,True),('plot_coordinate_only',True,False,False),('conflicting',True,False,False)])
def test_timing_populations(timing,scenario,source_ok,conditional_ok):
    selection,sources=synthetic();m=selection['timing']['source_meaning'];m['value']=timing
    if timing=='conflicting':m['witnesses'].append(deepcopy(selection['quantities']['coordinate_start']['coordinate']))
    selection['timing']['scenario']=dict(kind='coordinates_are_elapsed_sampling_times',status='stipulated_sensitivity') if scenario else None
    _,_,s=run(selection,sources);out=cells(s)
    assert (out['source_interval_average_substrate']['value'] is not None)==source_ok
    assert (out['scenario_interval_average_substrate']['conditional_value'] is not None)==conditional_ok
    assert out['scenario_interval_average_substrate']['value'] is None
    assert qcell(s,'substrate_loss')==60


@pytest.mark.parametrize('values',[(10,20,0,10,0,20,3,33),(0,0,4,4,2,14,3,33),(120,60,4,61,2,14,33,3)])
def test_signed_and_domain_results(values):
    selection,sources=synthetic(values=values);_,_,s=run(selection,sources);out=cells(s)
    assert qcell(s,'substrate_loss')==Fraction(values[0])-Fraction(values[1])
    if values[0]==10:
        assert out['substrate_loss']['negative_observed_change'];assert qcell(s,'fate_fraction')==2
        assert out['fate_fraction']['outside_physical_fraction_range']
    if values[2]==values[3]:assert 'zero_denominator' in out['chemical_ratio']['reasons']['domain']
    if values[6]>values[7]:assert 'positive_time_span_required' in out['source_interval_average_substrate']['reasons']['domain']


def test_positive_covariance_and_descriptive_uncertainty():
    selection,sources=synthetic();covariance(selection,sources)
    selection['pair_relationships']['substrate']['endpoint_comparability']['value']='separately_measured_compatible'
    selection['pair_relationships']['substrate']['physical_pairing']=dict(value='unknown',witnesses=[])
    e,i,s=run(selection,sources);out=cells(s);oracle=load('SYNTHETIC_COVARIANCE_ORACLE_001.json')['expected']
    assert out['substrate_loss']['interpretation_scope']=='descriptive_change'
    assert out['chemical_ratio']['interpretation_scope']=='descriptive_cross_readout_comparison'
    for name in ('chemical_discrepancy','chemical_discrepancy_variance','chemical_ratio','chemical_ratio_variance','fate_fraction','fate_fraction_variance'):
        assert out[name]['exact_value']==oracle[name]
    assert out['substrate_loss_variance']['value'] is not None
    assert out['chemical_standardized_discrepancy']['value'] is not None
    assert s['derived_covariance']['method']=='G*C*G_transpose'


@pytest.mark.parametrize('status',('known','estimated','unknown'))
def test_covariance_metadata_retained_without_matrix_display(status):
    selection,sources=synthetic();doc=covariance(selection,sources)
    doc.update(variance_status=status,origin='derived',derivation='estimated_from_observations',systematic_coverage='identified_unresolved')
    if status=='unknown':doc['covariance']=None
    sources['synthetic:joint_covariance']=json.dumps(doc).encode()
    e,i,s=run(selection,sources);context=s['covariance_context']
    assert context==i['covariance_context']
    assert context['selection_status']=='selected'
    for key in ('roles','owner_keys','units','dependency_keys','basis','variance_status','origin','derivation','systematic_coverage'):
        assert context[key]==doc[key]
    assert not ({'matrix','covariance','value','exact_value'}&set(context))
    if status=='unknown':assert 'joint_covariance_unknown' in cells(s)['chemical_discrepancy_variance']['reasons']['source']
    changed=deepcopy(i);changed['covariance_context']['systematic_coverage']='not_established'
    with pytest.raises(ValueError):I.validate_concentration_window_calculation_inputs(changed,extraction=e)
    changed=deepcopy(s);changed['covariance_context']['variance_status']='estimated' if status!='estimated' else 'known'
    with pytest.raises(ValueError):C.validate_concentration_window_sheet(changed,inputs=i)
    replay=json.loads(json.dumps(i,sort_keys=True))
    assert C.populate_concentration_window(replay)==s


def test_retained_report_origin_and_source_free_replay():
    selection,sources=synthetic()
    selection['source_kind']='retained_extraction'
    e,i,s=run(selection,sources)
    assert i['source_kind']=='retained_extraction'
    assert all(row['origin']=='reported' for row in e['quantities'].values())
    assert all(cells(s)[role]['origin']=='reported' for role in I.ROLES)
    assert cells(s)['substrate_loss']['origin']=='calculated'
    retained=json.loads(json.dumps(e,sort_keys=True));sources.clear()
    I.validate_concentration_window_extraction(retained,selection=selection)
    replay=I.compile_concentration_window_inputs(retained)
    assert replay==i and C.populate_concentration_window(replay)==s


@pytest.mark.parametrize('malformed',('top_level_array','scalar_matrix_rows'))
def test_malformed_covariance_source_has_structured_failure(malformed):
    selection,sources=synthetic();doc=covariance(selection,sources)
    if malformed=='top_level_array':sources['synthetic:joint_covariance']=b'[]'
    else:
        doc['covariance']=[1,2]
        sources['synthetic:joint_covariance']=json.dumps(doc).encode()
    with pytest.raises(ExperimentalContractError) as caught:
        I.read_concentration_window_inputs(selection,read_source=callback(sources))
    assert caught.value.code=='concentration_window_covariance_matrix_invalid'


def test_selected_covariance_cannot_be_dropped_from_retained_extraction():
    selection,sources=synthetic();covariance(selection,sources)
    extraction=I.read_concentration_window_inputs(selection,read_source=callback(sources))
    dropped=deepcopy(extraction);dropped['covariance']=None
    with pytest.raises(ExperimentalContractError,match='source_artifact_mismatch'):
        I.validate_concentration_window_extraction(dropped,selection=selection)
    with pytest.raises(ExperimentalContractError,match='source_artifact_mismatch'):
        I.compile_concentration_window_inputs(dropped)


def test_ratio_variance_display_underflow_has_explicit_domain_reason():
    selection,sources=synthetic(values=('2e150','1e150',0,'1e150',0,'1e149',0,10))
    doc=covariance(selection,sources)
    doc['covariance']=[[1e-100 if i==j else 0 for j in range(8)] for i in range(8)]
    sources['synthetic:joint_covariance']=json.dumps(doc).encode()
    e,i,s=run(selection,sources);out=cells(s)
    assert qcell(s,'chemical_ratio')==1
    assert I._q(i['covariance']['matrix_exact'][0][0])==Fraction(1,10**100)
    # The exact gradient calculation gives4e-400; it must not become a displayed0.
    assert Fraction(4,10**400)>0 and I._float(Fraction(4,10**400)) is None
    assert out['chemical_ratio_variance']['value'] is None
    assert out['chemical_ratio_variance']['status']=='unavailable'
    assert out['chemical_ratio_variance']['reasons']['domain']==['numerical_model_range']


@pytest.mark.parametrize('mutation',('owner','unit','dependency','duplicate','asymmetric','indefinite','shape','zero_variance','partial'))
def test_covariance_negatives_and_partial(mutation):
    selection,sources=synthetic();doc=covariance(selection,sources)
    if mutation=='owner':doc['owner_keys'][0]='wrong'
    elif mutation=='unit':doc['units'][0]='s'
    elif mutation=='dependency':doc['dependency_keys'][0]=['wrong']
    elif mutation=='duplicate':doc['roles'][1]=doc['roles'][0]
    elif mutation=='asymmetric':doc['covariance'][0][1]+=1
    elif mutation=='indefinite':doc['covariance'][0][0]=-1
    elif mutation=='shape':doc['covariance'][0].pop()
    elif mutation=='zero_variance':doc['covariance']=[[0]*8 for _ in range(8)]
    else:
        doc['roles']=doc['roles'][:2];doc['owner_keys']=doc['owner_keys'][:2];doc['units']=doc['units'][:2];doc['dependency_keys']=doc['dependency_keys'][:2]
        doc['covariance']=[row[:2] for row in doc['covariance'][:2]]
    sources['synthetic:joint_covariance']=json.dumps(doc).encode()
    if mutation not in ('zero_variance','partial'):
        with pytest.raises(ValueError):I.read_concentration_window_inputs(selection,read_source=callback(sources))
    else:
        _,_,s=run(selection,sources);out=cells(s)
        if mutation=='zero_variance':assert 'positive_variance_required' in out['chemical_standardized_discrepancy']['reasons']['domain']
        else:
            assert out['substrate_loss_variance']['value'] is not None
            assert 'joint_covariance_incomplete' in out['total_product_gain_variance']['reasons']['source']


def test_authoritative_predecessor_mutations(original):
    selection,sources=original;e,i,s=run(selection,sources)
    for field in ('subject','basis','source','coefficient','selection'):
        changed=deepcopy(e)
        if field=='subject':changed['scientific_context']['assay']['molecule']['scientific_text']='wrong subject'
        elif field=='basis':changed['scientific_context']['quantities']['substrate_start']['concentration_basis']['value']='quenched_sample_concentration'
        elif field=='source':changed['quantities']['substrate_start']['locations'][0]['cell']='B2'
        elif field=='coefficient':changed['coefficients']['total_product']['value']=2
        else:changed['selection']['pair_relationships']['substrate']['endpoint_comparability']['value']='unknown'
        with pytest.raises(ValueError):I.validate_concentration_window_extraction(changed,selection=selection)
    changed=deepcopy(i);changed['scientific_context']['quantities']['substrate_start']['analyte']['scientific_text']='wrong analyte'
    with pytest.raises(ValueError):I.validate_concentration_window_calculation_inputs(changed,extraction=e)
    changed=deepcopy(s);changed['scientific_context']['assay']['conditions']['scientific_text']='wrong conditions'
    with pytest.raises(ValueError):C.validate_concentration_window_sheet(changed,inputs=i)


def test_source_free_json_replay_and_scope(original):
    selection,sources=original;e,i,s=run(selection,sources)
    retained=json.loads(json.dumps(e,sort_keys=True));sources.clear()
    I.validate_concentration_window_extraction(retained,selection=selection)
    assert I.compile_concentration_window_inputs(retained)==i
    assert C.populate_concentration_window(json.loads(json.dumps(i,sort_keys=True)))==s
    selection,sources=synthetic();selection['requested_cells']=['fate_fraction']
    _,_,one=run(selection,sources);assert list(cells(one))==['fate_fraction'];assert one['derived_covariance'] is None
    selection['requested_cells']=[];_,_,empty=run(selection,sources);assert empty['cells']==[]


def test_formula_cache_and_duplicate_parts(original):
    selection,sources=original;ref=selection['source_ref']
    def rewrite(formula=False,duplicate=False):
        output=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(sources[ref])) as src,zipfile.ZipFile(output,'w') as dst:
            for row in src.infolist():
                raw=src.read(row)
                if formula and row.filename=='xl/worksheets/sheet2.xml':raw=raw.replace(b'<c r="C2" s="1"><v>200</v></c>',b'<c r="C2" s="1"><f>100+100</f><v>200</v></c>')
                dst.writestr(row,raw)
                if duplicate and row.filename=='xl/worksheets/sheet2.xml':dst.writestr(row,raw)
        return output.getvalue()
    original_bytes=sources[ref];sources[ref]=rewrite(formula=True)
    e,i,s=run(selection,sources)
    assert 'formula_cache_point_unimplemented' in cells(s)['substrate_loss']['reasons']['implementation']
    sources[ref]=original_bytes
    with pytest.warns(UserWarning):changed=rewrite(duplicate=True)
    sources[ref]=changed
    with pytest.raises(ValueError):I.read_concentration_window_inputs(selection,read_source=callback(sources))
