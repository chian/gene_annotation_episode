"""Research-only arithmetic and source custody; imports no production module.

Reads one previously examined retained original paper. This is not an episode,
reader integration, experimental rerun or configured-model execution.
"""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal as D, localcontext
import hashlib
import json
import re
import struct
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CASE = ROOT / 'research/experimental_scoring_review_2026-10-23/a105_calibration_primary_case_167'
XML = CASE / 'source/PMC6454709.xml'
raw = XML.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '86896c47556f7eeef975856dbbe2d3bab3b6143b91d1f826078e29771761b698'

def witness(start, end):
    return dict(path=str(XML), sha256=hashlib.sha256(raw).hexdigest(),
                start_byte=start, end_byte=end, quote=raw[start:end].decode())

paragraphs = {}
for number in [28,29,31,32,33,35,36,37,38,39,43,47,49,50,55,58]:
    pattern = rb'<p\b[^>]*\bid="Par' + str(number).encode() + rb'"[^>]*>.*?</p>'
    found = re.search(pattern, raw, re.S)
    assert found is not None
    paragraphs['Par'+str(number)] = witness(found.start(), found.end())

table = re.search(rb'<table-wrap\b[^>]*\bid="Tab2"[^>]*>.*?</table-wrap>', raw, re.S)
assert table is not None
rows = []
for match in re.finditer(rb'<tr>.*?</tr>', table.group(), re.S):
    node = ET.fromstring(match.group())
    cells = node.findall('td')
    if cells:
        rows.append((match, cells))

def txt(e):
    return ''.join(e.itertext()).strip()

selected = []
for index, expected in [(3,['4.3','4.39','2.1','2.2','4.5','0.90']),
                        (4,['8.6','8.72','1.4','0.8','1.7','0.99']),
                        (5,['12.9','12.98','0.6','1.5','2.1','0.98'])]:
    match,cells = rows[index]
    values = [txt(c) for c in cells]
    assert values[-6:] == expected, values
    start = table.start()+match.start()
    fields = ('nominal','measured','reported_RE_percent','within_run_CV_percent',
              'between_run_CV_percent','reported_Zprime')
    raw_cells=list(re.finditer(rb'<td\b[^>]*>.*?</td>',match.group(),re.S))[-6:]
    field_witnesses={}
    for name,token,cell in zip(fields,expected,raw_cells):
        cs=start+cell.start();ce=start+cell.end()
        located=raw.find(token.encode(),cs,ce)
        assert located>=cs and raw[located:located+len(token.encode())].decode()==token
        field_witnesses[name]=dict(cell=witness(cs,ce),number=witness(located,located+len(token.encode())))
    selected.append(dict(subject='prepared NADPH standard', method='WST8 450nm',
        unit='nmol', source_row_index_in_body=index,
        fields=dict(zip(fields,expected)),field_witnesses=field_witnesses,
        witness=witness(start,start+len(match.group())),
        precision_basis='source within-run and between-run; pooling and SD denominator not specified',
        independence='validation independence from fitted standard data/stocks unknown'))

fig = CASE/'source/Fig3.png'
png=fig.read_bytes()
assert png[:8] == b'\x89PNG\r\n\x1a\n'
width,height=struct.unpack('>II',png[16:24])
visual=dict(path=str(fig),sha256=hashlib.sha256(png).hexdigest(),width=width,height=height,
    panel='B inset',origin='printed_fit_read_from_actual_native_image_in_this_review',
    slope='0.0999',slope_unit='absorbance/nmol',intercept='0.0166',intercept_unit='absorbance',
    r_squared='0.9994',source_range_nmol=['0','19'],
    note='No sample/blank absorbance is reported by these fit coefficients; predictions are not observations.')

def exact(v):
    return dict(numerator=str(v.numerator),denominator=str(v.denominator))

results=[]
checks=0
with localcontext() as ctx:
    ctx.prec=65
    for row in selected:
        x=row['fields'];n,m=F(x['nominal']),F(x['measured']);ratio=m/n;bias=ratio-1
        loss={}
        for basis in ('within_run','between_run'):
            cv=F(x[basis+'_CV_percent'])/100
            variance=(ratio*cv)**2
            mse=bias*bias+variance
            nd,md,cd=D(x['nominal']),D(x['measured']),D(x[basis+'_CV_percent'])/100
            independent=((md-nd)**2+(cd*md)**2)/(nd*nd)
            assert abs(D(mse.numerator)/D(mse.denominator)-independent) < D('1e-60')
            checks+=1
            loss[basis]=dict(relative_bias_squared=exact(bias*bias),
                relative_variance_plugin=exact(variance),relative_MSE_plugin=exact(mse),
                relative_MSE_decimal=str(independent),relative_RMSE_percent=str(100*independent.sqrt()),
                status='proposal_conditional_plugin_not_source_reported_MSE',
                assumption='reported measured amount represents mean and reported CV is SD/that mean for this precision basis')
        z=F(x['reported_Zprime']);band=(1-z)/3
        checks+=1;assert D(band.numerator)/D(band.denominator) == (1-D(x['reported_Zprime']))/3
        results.append(dict(nominal_nmol=x['nominal'],measured_nmol=x['measured'],
            measured_over_nominal=exact(ratio),relative_bias=exact(bias),
            precision_bases=loss,reported_Zprime=x['reported_Zprime'],
            implied_sd_sum_over_mean_separation=exact(band),
            Zprime_recalculation=None,Zprime_missing='positive/negative means and SDs and control identities not supplied'))
    slope,intercept=F('0.0999'),F('0.0166');offset=intercept/slope
    offset_d=D('0.0166')/D('0.0999')
    assert abs(D(offset.numerator)/D(offset.denominator)-offset_d)<D('1e-60');checks+=1
    fit=dict(intercept_equivalent_nmol=exact(offset),
        intercept_equivalent_nmol_decimal=str(offset_d),
        subtraction_error_after_matched_blank_nmol=exact(-offset),
        relative_error_at_nominal_8_6=exact(-offset/F('8.6')),
        relative_error_at_LLOQ_0_4=exact(-offset/F('0.4')),
        origin='algebraic_consequence_of_source_fit_not_observed_sample_absorbance')
    comparison=dict(WST_specific_activity='12.51',UV_specific_activity='14.88',
        unit='nmol/min/ug',difference=exact(F('12.51')-F('14.88')),
        WST_over_UV=exact(F('12.51')/F('14.88')),
        enzyme_concentration_WST_over_UV=exact((F('0.1')/F('0.150'))/(F('0.5')/F('1'))),
        variance_of_difference=None,limitation='nominal concentrations differ; sampling-unit identity, pairing, covariance unknown')

packet=dict(source=dict(path=str(XML),sha256=hashlib.sha256(raw).hexdigest(),
    doi='10.1186/s12858-019-0108-1',original_url='https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6454709/fullTextXML'),
    paragraphs=paragraphs,standard_rows=selected,visual_fit=visual,
    table_witnesses={key:witness(found.start(),found.end()) for key in ('Tab1','Tab2','Tab3','Tab4')
        for found in [re.search(rb'<table-wrap\b[^>]*\bid="'+key.encode()+rb'"[^>]*>.*?</table-wrap>',raw,re.S)]
        if found is not None},
    scientific_scope='detector NADPH quantification; not chemical product identification',
    reset_receipt=str(HERE/'POST_WST8_RESET_002.json'))
(HERE/'SOURCE_PACKET_001.json').write_text(json.dumps(packet,indent=2,ensure_ascii=False)+'\n')
(HERE/'NUMERICAL_ORACLE_001.json').write_text(json.dumps(dict(
    source_standard_examples=results,fit_blank_algebra=fit,method_comparison=comparison,
    arithmetic_checks=checks,precision=65,
    methods='exact Fraction algebra cross-checked independently with Decimal squared-error form',
    missing_source_vs_implementation=dict(
        source_missing=['raw positive/negative control distributions','per-day raw standards and pooling',
            'nominal stock uncertainty','calibration covariance','sample and blank raw absorbances',
            'chemical product rate and productive coupling'],
        implementation_missing=['reported basis-specific CV/Zprime reader','conditional relative MSE compilation',
            'source linear fit/blank conversion','typed endpoint-to-functional-product relationship']),
    no_production_imports=True,no_model_execution=True),indent=2)+'\n')
print(json.dumps(dict(arithmetic_checks=checks,examples=[dict(nominal=x['nominal_nmol'],
    within_RMSE_percent=x['precision_bases']['within_run']['relative_RMSE_percent'],
    between_RMSE_percent=x['precision_bases']['between_run']['relative_RMSE_percent']) for x in results],
    intercept_equivalent_nmol=str(offset_d)),indent=2))
