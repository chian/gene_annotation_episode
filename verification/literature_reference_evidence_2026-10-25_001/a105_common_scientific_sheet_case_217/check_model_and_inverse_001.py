"""Independent model sensitivity checks; standalone design verification only."""
from pathlib import Path
from fractions import Fraction as F
from math import log,isclose
import json
B=Path(__file__).resolve().parent
rows={}
for arm,ptest,kdtest in [('T252N',92,34),('T252N/V253T',132,12)]:
    # Inverse algebra and independent forward substitution, no fitted source S.
    R=F(ptest,206);Kdi=F(kdtest);Kd0=F('1.8')
    required=(R*Kdi-Kd0)/(1-R)
    assert required>0 and (required+Kd0)/(required+Kdi)==R
    x=[float(ptest),206.,float(kdtest),1.8,2000.]
    def residual(t):
        P,P0,k,k0,s=t
        return log(P/P0)-log((s+k0)/(s+k))
    P,P0,k,k0,s=x
    analytic=[1/P,-1/P0,1/(s+k),-1/(s+k0),1/(s+k)-1/(s+k0)]
    numeric=[]
    for i,v in enumerate(x):
        step=max(abs(v),1)*1e-4
        xa=x[:];xb=x[:];xa[i]+=step;xb[i]-=step
        numeric.append((residual(xa)-residual(xb))/(2*step))
    for a,n in zip(analytic,numeric):
        assert isclose(a,n,rel_tol=2e-7,abs_tol=1e-12),(arm,a,n)
    # Direct occupancy computes the same residual without the simplified ratio.
    ti=s/(s+k);tr=s/(s+k0)
    assert isclose(residual(x),log(P/P0)-log(ti/tr),abs_tol=1e-14)
    rows[arm]={'required_free_substrate_uM_exact':str(required),'required_free_substrate_uM':float(required),
      'forward_substitution_product_ratio_exact':str((required+Kd0)/(required+Kdi)),
      'reported_product_ratio_exact':str(R),'interpretation':'Inverse conditional binding-only model; NOT measured or inferred actual assay substrate.',
      'analytic_D_gradient_order':['P_test','P_reference','Kd_test','Kd_reference','shared_S'],
      'analytic_D_gradient':analytic,'central_difference_gradient':numeric,
      'gradient_status':'passed independent finite-difference checks'}
result={'status':'passed','model':'single_site_equilibrium_binding_only_sensitivity','rows':rows,
        'source_scope':'Same retained207 paper only; paper quantities already frozen in NUMERICAL_ORACLES_001.json.',
        'limits':['Product-assay S unreported in inspected article; no actual concentration estimate follows.',
                  'Differences in inverse S across mutants do not establish statistical contradiction without compatible assays/model/uncertainty.',
                  'No covariance, probability, active fraction or causal attribution invented.']}
(B/'MODEL_CHECKS_AND_INVERSE_001.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'passed','required_free_substrate_uM':{a:v['required_free_substrate_uM'] for a,v in rows.items()},'gradient_check_count':10}))
