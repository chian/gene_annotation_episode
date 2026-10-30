"""Generate explicitly synthetic expression inputs and audit the worked example.
This is an isolated research calculation, not a production reader or scorer.
"""
from pathlib import Path
import csv,json,math,statistics as st
from scipy import stats
P=Path(__file__).resolve().parent
n=20
dot=lambda a,b:math.fsum(x*y for x,y in zip(a,b))
unit=lambda a:[x/math.sqrt(dot(a,a)) for x in a]
growth=[(i+1)/10 for i in range(n)]
base=[unit([1.]*n),unit([g-st.mean(growth) for g in growth])]
vectors=[]
for frequency in range(1,6):
    v=[math.cos(2*math.pi*frequency*(i+.5)/n) for i in range(n)]
    for u in base+vectors:
        projection=dot(v,u)
        v=[x-projection*y for x,y in zip(v,u)]
    vectors.append(unit(v))
target=[2+.5*v+.01*g for v,g in zip(vectors[0],growth)]
data={};checks=[]
for name,r,needed,i in [('P',.8,18,1),('Q',.6,16,2),('R',-.4,20,3),('O_optional',.95,20,4)]:
    residual=[.5*(r*x+math.sqrt(1-r*r)*y) for x,y in zip(vectors[0],vectors[i])]
    raw=[x+.01*g for x,g in zip(residual,growth)]
    ordered=sorted(raw)
    missing=n-needed
    intercept=2 if missing==0 else 1-(ordered[missing-1]+ordered[missing])/2
    values=[intercept+x for x in raw]
    data[name]=values
    residualize=lambda a:[a[j]-st.mean(a)-dot([x-st.mean(a) for x in a],base[1])*base[1][j] for j in range(n)]
    observed=stats.pearsonr(residualize(target),residualize(values)).statistic
    observed_d=sum(a>=1 and b>=1 for a,b in zip(target,values))
    assert abs(observed-r)<1e-12 and observed_d==needed
    assert min(values)>=0
    checks.append({'partner':name,'partial_r':float(observed),'expected_r':r,
                   'co_detected_conditions':observed_d,'denominator':n,'log2_values_nonnegative':True})
with (P/'SYNTHETIC_EXPRESSION_INPUTS_001.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=['condition_id','growth_rate_per_hr','target']+list(data));w.writeheader()
    for i in range(n):w.writerow({'condition_id':f'synthetic_{i+1:02d}','growth_rate_per_hr':growth[i],
                                 'target':target[i],**{g:v[i] for g,v in data.items()}})
(P/'SYNTHETIC_VECTOR_CHECKS_001.json').write_text(json.dumps({'kind':'entirely synthetic',
  'n_conditions':n,'n_independent_cultures_assumed':n,'within_condition_replicates':1,
  'expression_unit':'log2(TPM+1)','codetection_threshold_TPM':1,'checks':checks},indent=2)+'\n')
print(json.dumps(checks,indent=2))
