"""Independent original-cell audit and high-precision numerical research checks.

No production grader/model/episode/annotation credit. Statistical covariance of
an estimator remains conditional on the explicitly unproven IID-curve model.
"""
from pathlib import Path
from zipfile import ZipFile
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
import hashlib
import json
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CASE=ROOT/'research/experimental_scoring_review_2026-10-23/a105_precision_population_case_225'
getcontext().prec=65
sha=lambda raw:hashlib.sha256(raw).hexdigest()
packet=json.loads((CASE/'SOURCE_PACKET_001.json').read_text())
expected=json.loads((CASE/'NUMERICAL_COMPONENTS_001.json').read_text())
pooled=json.loads((CASE/'POOLED_ESTIMATOR_COVARIANCE_002.json').read_text())
for value in packet['sources'].values():
    raw=Path(value['path']).read_bytes()
    assert sha(raw)==value['sha256'] and len(raw)==value['bytes']
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with ZipFile(CASE/'originals/S1Data.xlsx') as book:
    raw=book.read('xl/worksheets/sheet1.xml')
    shared=ET.fromstring(book.read('xl/sharedStrings.xml'))
    strings=[''.join(t.text or '' for t in node.findall('.//s:t',ns)) for node in shared.findall('s:si',ns)]
    actual={c.attrib['r']:c for c in ET.fromstring(raw).findall('s:sheetData/s:row/s:c',ns)}
    for name, receipt in packet['xlsx_members'].items():
        content=book.read(name)
        assert sha(content)==receipt['sha256'] and len(content)==receipt['bytes']
    for w in [*packet['selected_headers'].values(),
              *(x for point in packet['selected_points'] for x in (point['concentration'],*point['rate_entries']))]:
        cell=actual[w['cell']]
        token=cell.find('s:v',ns).text
        value=strings[int(token)] if cell.attrib.get('t')=='s' else token
        assert token==w['raw_value'] and value==w['value']
        assert raw[w['member_start']:w['member_end']].decode()==w['cell_xml']
        assert cell.find('s:f',ns) is None
text=(CASE/'originals/article_text.txt').read_bytes()
for w in packet['article_witnesses'].values():
    assert sha(text)==w['artifact_sha256']
    assert text[w['start']:w['end']].decode()==w['quote']

xs=[D(point['concentration']['raw_value']) for point in packet['selected_points']]
columns=[[D(point['rate_entries'][j]['raw_value']) for point in packet['selected_points']] for j in range(3)]
n=D(len(columns));means=[sum(values)/n for values in zip(*columns)]
def close(actual,expected,rtol=D('0.000003'),atol=D('1e-25')):
    assert abs(actual-D(str(expected)))<=atol+rtol*abs(actual),(str(actual),expected)
for point, summary in zip(packet['selected_points'],expected['point_summaries']):
    values=[F(v['raw_value']) for v in point['rate_entries']]
    mean=sum(values)/len(values)
    variance=sum((v-mean)**2 for v in values)/(len(values)-1)
    for name,v in [('mean_exact',mean),('sample_variance_exact',variance)]:
        assert summary[name]=={'numerator':str(v.numerator),'denominator':str(v.denominator)}


def fit(ys):
    """Decimal Newton root with explicit bracket; no copied fit parameters."""
    def evaluate(k):
        a=[x/(k+x) for x in xs]
        b=[x/(k+x)**2 for x in xs]
        c=[x/(k+x)**3 for x in xs]
        numerator=sum(t*y for t,y in zip(a,ys));denominator=sum(t*t for t in a)
        v=numerator/denominator
        vp=(-sum(t*y for t,y in zip(b,ys))*denominator+
            2*numerator*sum(t*u for t,u in zip(a,b)))/denominator**2
        residual=[y-v*t for y,t in zip(ys,a)]
        value=sum(r*t for r,t in zip(residual,b))
        derivative=sum((-vp*t+v*u)*u-2*r*w for t,u,r,w in zip(a,b,residual,c))
        return v,value,derivative
    lo,hi=D('1e-8'),D('1e8')
    assert evaluate(lo)[1]<0<evaluate(hi)[1]
    k=(min(xs)*max(xs)).sqrt()
    for iteration in range(400):
        v,value,derivative=evaluate(k)
        if value<0:lo=k
        else:hi=k
        candidate=k-value/derivative if derivative else (lo+hi)/2
        if not lo<candidate<hi:candidate=(lo+hi)/2
        if abs(candidate-k)<D('1e-48'):
            k=candidate;break
        k=candidate
    else:raise AssertionError('Numerical oracle did not converge')
    return [evaluate(k)[0],k]


fits=[fit(col) for col in columns]
theta_mean=[sum(row[a] for row in fits)/n for a in range(2)]
theta_fit=fit(means)
for result,reference in zip(fits,expected['reporting_column_fits']):
    close(result[0],reference['Vmax']);close(result[1],reference['Km'])
close(theta_fit[0],pooled['parameter_values'][0]);close(theta_fit[1],pooled['parameter_values'][1])
column_cov=[[sum((t[a]-theta_mean[a])*(t[b]-theta_mean[b]) for t in fits)/(n-1)
             for b in range(2)] for a in range(2)]
g=[1/theta_mean[0],-1/theta_mean[1]]
mean_parameter_logvar=sum(g[a]*column_cov[a][b]*g[b]/n for a in range(2) for b in range(2))
close(mean_parameter_logvar,expected['conditional_scenario']['first_order_log_efficiency_variance'])

# Independent finite differences in all13 observed-mean directions, rather
# than using the research report's analytical Hessian/sensitivity formula.
step=D('1e-14');sensitivity=[[],[]]
for index in range(len(xs)):
    high=means.copy();low=means.copy();high[index]+=step;low[index]-=step
    a,b=fit(high),fit(low)
    for j in range(2):sensitivity[j].append((a[j]-b[j])/(2*step))
source_cov=[[sum((col[i]-means[i])*(col[j]-means[j]) for col in columns)/(n-1)
             for j in range(len(xs))] for i in range(len(xs))]
fit_cov=[[sum(sensitivity[a][i]*source_cov[i][j]*sensitivity[b][j]/n
              for i in range(len(xs)) for j in range(len(xs))) for b in range(2)] for a in range(2)]
for a in range(2):
    for b in range(2):close(fit_cov[a][b],pooled['conditional_selected_parameter_covariance'][a][b])
g=[1/theta_fit[0],-1/theta_fit[1]]
fit_logvar=sum(g[a]*fit_cov[a][b]*g[b] for a in range(2) for b in range(2))
close(fit_logvar,pooled['conditional_log_efficiency_variance'])
assert abs(theta_mean[1]-theta_fit[1])>D('.5')
assert abs(mean_parameter_logvar-fit_logvar)>D('.0004')
within=sum((y-m)**2 for m,values in zip(means,zip(*columns)) for y in values)
between=n*sum((m-theta_fit[0]*x/(theta_fit[1]+x))**2 for m,x in zip(means,xs))
total=sum((y-theta_fit[0]*x/(theta_fit[1]+x))**2 for col in columns for x,y in zip(xs,col))
assert abs(total-within-between)<D('1e-60')

result={'scope':'Independent original-source custody/exact statistics/Decimal Newton and13finite-difference checks; research only.',
    'selected_rate_cells_verified':39,'concentration_cells_verified':13,'header_cells_verified':6,
    'exact_point_means_and_variances_verified':13,'article_witnesses_verified':len(packet['article_witnesses']),
    'per_column_fits':fits,'mean_of_fitted_parameter_vectors':theta_mean,'fit_to_point_means':theta_fit,
    'conditional_log_variance_mean_parameters':mean_parameter_logvar,
    'conditional_fit_to_means_parameter_covariance':fit_cov,'conditional_log_variance_fit_to_means':fit_logvar,
    'independent_mean_direction_refits':13,'residual_sum_decomposition':{'total':total,'within':within,'model':between},
    'published_parameter_covariance':None,'independent_preparation_count':None,
    'statistical_IID_curve_model_source_established':False,'source_endpoint_conflict_retained':True,
    'measurements_synthetic':False,'new_complex_software':0,'production_changes':False}
with (HERE/'ROOT_NUMERICAL_ORACLES_001.json').open('x') as handle:
    json.dump(result,handle,indent=2,default=str);handle.write('\n')
print(json.dumps(result,indent=2,default=str))
