"""Read retained primary bytes and compute explicitly scoped source descriptors.

Research artifact only. No production publisher, model, episode or credit run.
No synthetic measurements or covariance matrices are used.
"""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import html
import json
import math
import re
import shutil
import statistics
import xml.etree.ElementTree as ET
from fractions import Fraction

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CASE=HERE.parent/'a105_raw_rate_primary_case_164'
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def exact(value):return {'numerator':str(value.numerator),'denominator':str(value.denominator)}
def dump(name,value):
    with (HERE/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')


originals=HERE/'originals';originals.mkdir(exist_ok=True)
copy_names={'article.html':CASE/'originals/article.html','article_text.txt':CASE/'article_text.txt',
            'S1Data.xlsx':CASE/'originals/S1Data.xlsx','S5Table.docx':CASE/'originals/S5Table.docx',
            'S5Table.visible.txt':CASE/'S5Table.visible.txt'}
sources={}
for name,source in copy_names.items():
    raw=source.read_bytes();target=originals/name
    assert not target.exists(),target
    shutil.copy2(source,target)
    assert target.read_bytes()==raw
    sources[name]={'path':str(target),'retained_from':str(source),'sha256':sha(raw),'bytes':len(raw)}

with ZipFile(originals/'S1Data.xlsx') as z:
    members={name:z.read(name) for name in ('xl/workbook.xml','xl/_rels/workbook.xml.rels',
        'xl/sharedStrings.xml','xl/worksheets/sheet1.xml')}
for name,raw in members.items():
    path=HERE/'xlsx_members'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
strings=[''.join(node.itertext()) for node in ET.fromstring(members['xl/sharedStrings.xml']).findall('m:si',NS)]
sheet=ET.fromstring(members['xl/worksheets/sheet1.xml'])
cells={cell.get('r'):cell for cell in sheet.findall('m:sheetData/m:row/m:c',NS)}
member_raw=members['xl/worksheets/sheet1.xml']


def cell_witness(address):
    cell=cells.get(address)
    if cell is None:return {'cell':address,'status':'absent','value':None}
    value=cell.find('m:v',NS);formula=cell.find('m:f',NS)
    token=None if value is None else value.text
    kind=cell.get('t','n')
    decoded=strings[int(token)] if token is not None and kind=='s' else token
    occurrence=re.search(rb'<c\b[^>]*\br="'+address.encode()+rb'"[^>]*>.*?</c>',member_raw,re.S)
    assert occurrence is not None
    return {'workbook_sha256':sources['S1Data.xlsx']['sha256'],'worksheet':'Sheet1',
        'member':'xl/worksheets/sheet1.xml','member_sha256':sha(member_raw),'cell':address,
        'cell_type':kind,'raw_value':token,'value':decoded,'formula':None if formula is None else formula.text,
        'value_is_formula_cache':formula is not None,'member_start':occurrence.start(),'member_end':occurrence.end(),
        'cell_xml':occurrence.group().decode(),
        'shared_string_index':int(token) if kind=='s' and token is not None else None}


headers={a:cell_witness(a) for a in ('A189','B190','Q191','R192','S192','T192')}
assert headers['Q191']['value']=='PK_WT-DHA'
assert [headers[a]['value'] for a in ('R192','S192','T192')]==['data-1','data-2','data-3']
assert headers['B190']['value']=='NADH consumption rate µmol min-1'
records=[]
for row in range(193,206):
    x=cell_witness('Q'+str(row));ys=[cell_witness(col+str(row)) for col in ('R','S','T')]
    assert all(c['cell_type']=='n' and c['formula'] is None and c['raw_value'] is not None for c in (x,*ys))
    records.append({'concentration':x,'rate_entries':ys})
assert len(records)==13 and sum(len(r['rate_entries']) for r in records)==39
text=(originals/'article_text.txt').read_bytes()


def text_witness(start,end,*,after=0):
    a=text.index(start.encode(),after);b=text.index(end.encode(),a)+len(end.encode())
    return {'representation':'retained_text','artifact_sha256':sha(text),'start':a,'end':b,
            'quote':text[a:b].decode(),'source_original_sha256':sources['article.html']['sha256']}


witnesses={
    'main_mutant_kinetic_method':text_witness('Activity assay and kinetic properties of PK and mutants',
        'using GraphPad Prism 5 software.'),
    'multispecies_short_chain_method':text_witness('Expression, purification, and enzyme kinetics of PKs from different species',
        'triplicate experiments using GraphPad Prism 5 (GraphPad Software, USA).'),
    'S17_caption':text_witness('S17 Fig.','https://doi.org/10.1371/journal.pbio.3002285.s017'),
    'purification_and_BCA':text_witness('Enzyme activity of BbPK for DHA, L-EUS, and D-EUS',
        'BCA Protein Assay Reagent Kit (Pierce, USA) with BSA as the standard.'),
    'S3_control':text_witness('S3 Fig.','https://doi.org/10.1371/journal.pbio.3002285.s003'),
    'S5_coproduct_identity':text_witness('S5 Fig.','https://doi.org/10.1371/journal.pbio.3002285.s005')}
# The retained text is a separate representation, not an original HTML span.
# Cross-check each selected scientific text against normalized original HTML.
visible=html.unescape(re.sub(r'<[^>]+>',' ',(originals/'article.html').read_text()))
collapse=lambda s:re.sub(r'\s+',' ',s).strip()
for name,w in witnesses.items():
    # Source whitespace/line breaks differ. Full exact token sequences must
    # nevertheless be represented in the retained original page.
    assert collapse(w['quote']) in collapse(visible),name

packet={'paper':{'title':'Construction of an artificial phosphoketolase pathway that efficiently catabolizes multiple carbon sources to acetyl-CoA',
    'doi':'10.1371/journal.pbio.3002285','url':'https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3002285',
    'data_url':'https://journals.plos.org/plosbiology/article/file?type=supplementary&id=10.1371/journal.pbio.3002285.s034'},
    'sources':sources,'xlsx_members':{name:{'sha256':sha(raw),'bytes':len(raw)} for name,raw in members.items()},
    'selected_headers':headers,'selected_points':records,'article_witnesses':witnesses,
    'selected_report':'WT-DHA rate-versus-concentration block only',
    'physical_preparation_ids':None,'biological_replication_count':None,
    'reporting_columns_are_not_proven_physical_units':True,
    'endpoint_conflict':{'workbook':'NADH consumption','methods':'NADPH production',
        'status':'unresolved_do_not_convert_to_product_rate'},
    'source_origin':'reported','new_experiment_run':False}
dump('SOURCE_PACKET_001.json',packet)

xs=[Fraction(r['concentration']['raw_value']) for r in records]
columns=[[Fraction(r['rate_entries'][j]['raw_value']) for r in records] for j in range(3)]


def profiled(k,ys):
    terms=[float(x)/(k+float(x)) for x in xs]
    v=math.fsum(a*float(y) for a,y in zip(terms,ys))/math.fsum(a*a for a in terms)
    residual=[float(y)-v*a for a,y in zip(terms,ys)]
    return v,math.fsum(r*r for r in residual)


def golden_fit(ys):
    # One-dimensional positive-K profile least squares. Grid identifies the
    # interior bracket; no a priori biological Km bound or reported fit copied.
    grid=[-12+i*.1 for i in range(361)]
    scores=[profiled(math.exp(t),ys)[1] for t in grid]
    best=min(range(len(grid)),key=scores.__getitem__)
    assert 0<best<len(grid)-1,'No interior fit in numerical search domain.'
    a,b=grid[best-1],grid[best+1];g=(math.sqrt(5)-1)/2
    c=b-g*(b-a);d=a+g*(b-a)
    for _ in range(120):
        if profiled(math.exp(c),ys)[1]<profiled(math.exp(d),ys)[1]:b,d=d,c;c=b-g*(b-a)
        else:a,c=c,d;d=a+g*(b-a)
    k=math.exp((a+b)/2);v,sse=profiled(k,ys)
    return {'Vmax':v,'Km':k,'SSE':sse}


def derivative_fit(ys):
    # Independent stationarity-root algorithm, not the golden-section search.
    def derivative(k):
        v,_=profiled(k,ys)
        return math.fsum((float(y)-v*float(x)/(k+float(x)))*float(x)/(k+float(x))**2
            for x,y in zip(xs,ys))
    lo,hi=1e-4,1e6
    assert derivative(lo)<0<derivative(hi)
    for _ in range(160):
        mid=(lo+hi)/2
        if derivative(mid)<0:lo=mid
        else:hi=mid
    k=(lo+hi)/2;v,sse=profiled(k,ys)
    return {'Vmax':v,'Km':k,'SSE':sse}


fits=[golden_fit(ys) for ys in columns]
checks=[derivative_fit(ys) for ys in columns]
for a,b in zip(fits,checks):
    for key in ('Vmax','Km','SSE'):assert math.isclose(a[key],b[key],rel_tol=3e-6,abs_tol=1e-18),(a,b)
parameters=[[f['Vmax'],f['Km']] for f in fits]
theta=[statistics.mean(row[j] for row in parameters) for j in range(2)]
cov=[[math.fsum((p[i]-theta[i])*(p[j]-theta[j]) for p in parameters)/2 for j in range(2)] for i in range(2)]
mean_cov=[[v/3 for v in row] for row in cov]
grad=[1/theta[0],-1/theta[1]]
signed_terms=[[grad[i]*mean_cov[i][j]*grad[j] for j in range(2)] for i in range(2)]
log_eff_var=math.fsum(v for row in signed_terms for v in row)
diagonal_only=math.fsum(signed_terms[i][i] for i in range(2))
assert cov[0][0]>=0 and cov[1][1]>=0 and cov[0][0]*cov[1][1]-cov[0][1]**2>=-1e-20
raw_summaries=[]
for point in records:
    values=[Fraction(v['raw_value']) for v in point['rate_entries']]
    mean=sum(values,Fraction())/3;var=sum((v-mean)**2 for v in values)/2
    raw_summaries.append({'concentration':point['concentration']['value'],
        'mean_exact':exact(mean),'sample_variance_exact':exact(var),'mean':float(mean),
        'sample_sd':math.sqrt(float(var)),'cv':math.sqrt(float(var))/float(mean),
        'count_basis':'three_reported_numeric_columns_not_independent_preparation_count'})
mean_curve=[sum(v,Fraction())/3 for v in zip(*columns)]
pooled=golden_fit(mean_curve)
within=sum(sum((v-m)**2 for v in point) for point,m in zip(zip(*columns),mean_curve))
pooled_sse=sum(profiled(pooled['Km'],ys)[1] for ys in columns) # diagnostic only: each own V differs
actual_pooled_sse=sum((float(y)-pooled['Vmax']*float(x)/(pooled['Km']+float(x)))**2
    for ys in columns for x,y in zip(xs,ys))
assert math.isclose(actual_pooled_sse,float(within)+3*pooled['SSE'],rel_tol=1e-12)
result={'scope':'Derived research descriptors from original WT-DHA S17 reported rates; no published fit or physical population is substituted.',
    'measurements_synthetic':False,'native_rate_unit':'umol/min; source header endpoint conflict retained',
    'concentration_unit':'mM_by_article_S17_caption_and_method; workbook_concentration_column_unit_not_explicit',
    'point_summaries':raw_summaries,'reporting_column_fits':fits,
    'independent_stationarity_fits':checks,'fit_definition':'unweighted_positive_K_profile_least_squares_v=Vmax*S/(Km+S)',
    'mean_of_column_fit_parameters':dict(zip(('Vmax','Km'),theta)),
    'fit_to_point_means':pooled,'parameter_order':['Vmax','Km'],
    'descriptive_between_reporting_column_fit_covariance':cov,
    'covariance_units':[['(umol/min)^2','(umol/min)*mM'],['(umol/min)*mM','mM^2']],
    'descriptive_parameter_correlation':cov[0][1]/math.sqrt(cov[0][0]*cov[1][1]),
    'unconditional_covariance_of_published_estimates':None,
    'physical_preparation_population_covariance':None,
    'conditional_scenario':{'assumption':'three_reporting_column_fit_vectors_are_IID_exchangeable_units',
        'source_established':False,'estimator':'mean_of_three_column_fit_parameter_vectors_not_fit_to_point_means',
        'covariance_of_mean_parameter_vector':mean_cov,
        'mean_parameter_native_efficiency':theta[0]/theta[1],
        'first_order_log_efficiency_variance':log_eff_var,
        'first_order_log_efficiency_standard_uncertainty':math.sqrt(log_eff_var),
        'signed_variance_contributions':signed_terms,'diagonal_only_variance_for_comparison':diagonal_only,
        'not_a_probability_or_significance_test':True},
    'pooled_fit_residual_decomposition':{'all39_residual_SS':actual_pooled_sse,
        'within_concentration_reported_entry_SS':float(within),
        'between_mean_curve_fit_residual_SS_times3':3*pooled['SSE'],
        'identity_checked':True,'no_lack_of_fit_pvalue_or_threshold':True},
    'implementation_status':'research_calculation_only_not_installed_or_bound',
    'independent_solver_agreement':True}
dump('NUMERICAL_COMPONENTS_001.json',result)
print(json.dumps({k:result[k] for k in ('reporting_column_fits','mean_of_column_fit_parameters',
    'fit_to_point_means','descriptive_between_reporting_column_fit_covariance',
    'descriptive_parameter_correlation','conditional_scenario','pooled_fit_residual_decomposition')},indent=2))
