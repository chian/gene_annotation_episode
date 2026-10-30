"""Independent exact arithmetic; source reports and synthetic models separated."""
from fractions import Fraction as Q
from hashlib import sha256
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
CASE=HERE.parents[2]/'research/experimental_scoring_review_2026-10-23/a105_matched_assay_consistency_case_255'
for item in json.loads((CASE/'SOURCE_SELECTORS_001.json').read_text()):
    raw=Path(item['path']).read_bytes()
    assert sha256(raw).hexdigest()==item['source_sha256']
    assert raw[item['start']:item['end']].decode()==item['quote']
fd,nadh=Q(23),Q(8)
alpha=Q('8.6')/Q('1.2')
required=(fd-nadh)/alpha
assert alpha==Q(43,6) and required==Q(90,43)

def inv(matrix):
    n=len(matrix)
    rows=[[Q(x) for x in row]+[Q(int(i==j)) for j in range(n)] for i,row in enumerate(matrix)]
    for k in range(n):
        pivot=next(i for i in range(k,n) if rows[i][k])
        rows[k],rows[pivot]=rows[pivot],rows[k]
        divisor=rows[k][k];rows[k]=[v/divisor for v in rows[k]]
        for i in range(n):
            if i!=k:
                factor=rows[i][k];rows[i]=[a-factor*b for a,b in zip(rows[i],rows[k])]
    return [r[n:] for r in rows]

def gls(matrix,x):
    precision=inv(matrix)
    ones_p=[sum(row) for row in precision]
    denominator=sum(ones_p)
    weights=[v/denominator for v in ones_p]
    return weights,sum(a*b for a,b in zip(weights,x)),1/denominator

def exact(value):return {'numerator':str(value.numerator),'denominator':str(value.denominator)}

cov=[[Q(4),Q(1)],[Q(1),Q(9)]];x=[Q(20),Q(22)]
weights,mean,variance=gls(cov,x)
discrepancy=x[0]-x[1];dvariance=cov[0][0]+cov[1][1]-2*cov[0][1]
assert weights==[Q(8,11),Q(3,11)] and mean==Q(226,11) and variance==Q(35,11)
shared=Q(16)
cov_with_shared=[[entry+shared for entry in row] for row in cov]
shared_weights,shared_mean,shared_variance=gls(cov_with_shared,x)
assert shared_weights==weights and shared_mean==mean and shared_variance==variance+shared
assert cov_with_shared[0][0]+cov_with_shared[1][1]-2*cov_with_shared[0][1]==dvariance==11
result={
 'source_report_arithmetic':{'scope':'approximate reported-protocol comparison; not common-condition physical flux agreement',
    'ratio_NADH_over_Fd':float(nadh/fd),'nominal_difference':float(nadh-fd),
    'spectral_multiplier':float(alpha),'spectral_multiplier_exact_decimal_arithmetic':exact(alpha),
    'measured_nuisance_rate':None,'corrected_NADH_activity':None,'standardized_common_condition_discrepancy':None},
 'explicit_conditional_explanation':{'assumption':'true rate in the380nm protocol equals23 reported in the430nm protocol',
    'required_Fd_accumulation_rate':float(required),'required_rate_exact_decimal_arithmetic':exact(required),
    'is_observed_nuisance_rate':False,'required_fraction_of23':float(required/fd)},
 'source_stoichiometry_caption_arithmetic':{'H2_per_NAD':float(1/Q('1.1')),'H2_per_NADPH':float(1/Q('2.2')),
    'NADPH_per_NAD_under_coupling_model':float(Q('2.2')/Q('1.1')),'source_values_approximate':True},
 'synthetic_common_unbiased_estimates_only':{'input':[20,22],'known_joint_covariance':[[4,1],[1,9]],
    'weights':[exact(v) for v in weights],'combined_mean':exact(mean),'combined_variance':exact(variance),
    'difference':float(discrepancy),'difference_variance':float(dvariance),
    'standardized_difference':float(discrepancy)/math.sqrt(float(dvariance)),
    'squared_standardized_difference':float(discrepancy*discrepancy/dvariance),
    'known_shared_variance_added':16,'combined_variance_with_shared':exact(shared_variance),
    'discrepancy_variance_unchanged':True,'shared_bias_detected_by_agreement':False},
 'source_selectors_verified':9,'no_source_script_or_original_modified':True,
 'production_grader_or_selected_episode_executed':False,'goal_changed':False,'A105_complete':False}
with (HERE/'ROOT_INDEPENDENT_ARITHMETIC_001.json').open('x') as output:json.dump(result,output,indent=2);output.write('\n')
print(json.dumps(result,indent=2))
