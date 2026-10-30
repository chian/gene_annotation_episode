"""Estimator-specific conditional covariance from actual reported curve vectors.

Research arithmetic, not an installed grader or source-established population.
Uses full empirical cross-concentration covariance of reported columns. It does
not set off-diagonal elements to zero or infer physical pairing from labels.
"""
from pathlib import Path
import hashlib
import json
import math

HERE=Path(__file__).resolve().parent
packet=json.loads((HERE/'SOURCE_PACKET_001.json').read_text())
prior=json.loads((HERE/'NUMERICAL_COMPONENTS_001.json').read_text())
xs=[float(r['concentration']['raw_value']) for r in packet['selected_points']]
columns=[[float(r['rate_entries'][j]['raw_value']) for r in packet['selected_points']] for j in range(3)]
mean=[math.fsum(v)/3 for v in zip(*columns)]


def fit(ys):
    def evaluate(k):
        a=[x/(k+x) for x in xs]
        v=math.fsum(u*y for u,y in zip(a,ys))/math.fsum(u*u for u in a)
        d=math.fsum((y-v*x/(k+x))*x/(k+x)**2 for x,y in zip(xs,ys))
        return v,d
    lo,hi=1e-4,1e6
    assert evaluate(lo)[1]<0<evaluate(hi)[1]
    for _ in range(160):
        mid=(lo+hi)/2
        if evaluate(mid)[1]<0:lo=mid
        else:hi=mid
    k=(lo+hi)/2;v,_=evaluate(k)
    return [v,k]


theta=fit(mean);v,k=theta
assert math.isclose(k,prior['fit_to_point_means']['Km'],rel_tol=3e-6)
residual=[y-v*x/(k+x) for x,y in zip(xs,mean)]
jac=[[x/(k+x),-v*x/(k+x)**2] for x in xs]
second=[[[0,-x/(k+x)**2],[-x/(k+x)**2,2*v*x/(k+x)**3]] for x in xs]
hessian=[[math.fsum(j[i]*j[l]-r*second[q][i][l] for q,(j,r) in enumerate(zip(jac,residual)))
          for l in range(2)] for i in range(2)]
det=hessian[0][0]*hessian[1][1]-hessian[0][1]*hessian[1][0]
assert hessian[0][0]>0 and det>0
inverse=[[hessian[1][1]/det,-hessian[0][1]/det],[-hessian[1][0]/det,hessian[0][0]/det]]
sensitivity=[[math.fsum(inverse[a][b]*j[b] for b in range(2)) for j in jac] for a in range(2)]
point_cov=[[math.fsum((col[i]-mean[i])*(col[l]-mean[l]) for col in columns)/2
            for l in range(len(xs))] for i in range(len(xs))]
mean_cov=[[value/3 for value in row] for row in point_cov]
parameter_cov=[[math.fsum(sensitivity[a][i]*mean_cov[i][l]*sensitivity[b][l]
                 for i in range(len(xs)) for l in range(len(xs))) for b in range(2)] for a in range(2)]
g=[1/v,-1/k]
log_variance=math.fsum(g[a]*parameter_cov[a][b]*g[b] for a in range(2) for b in range(2))
# Independent directional re-fitting verifies the implicit derivative. Each
# mode is a centered observed column divided by sqrt((3-1)*3), so summing its
# squared directional log-response equals full covariance propagation.
directions=[[(y-m)/math.sqrt(6) for y,m in zip(col,mean)] for col in columns]
mode_variance=0;mode_checks=[];step=1e-3
for direction in directions:
    exact=[math.fsum(row[i]*direction[i] for i in range(len(xs))) for row in sensitivity]
    high=fit([m+step*d for m,d in zip(mean,direction)])
    low=fit([m-step*d for m,d in zip(mean,direction)])
    measured=[(a-b)/(2*step) for a,b in zip(high,low)]
    assert all(math.isclose(a,b,rel_tol=3e-6,abs_tol=1e-10) for a,b in zip(exact,measured)),(exact,measured)
    log_direction=(math.log(high[0]/high[1])-math.log(low[0]/low[1]))/(2*step)
    mode_variance+=log_direction**2
    mode_checks.append({'implicit_parameter_direction':exact,'refit_parameter_direction':measured,
                        'refit_log_efficiency_direction':log_direction})
assert math.isclose(mode_variance,log_variance,rel_tol=5e-6)
assert parameter_cov[0][0]*parameter_cov[1][1]>=parameter_cov[0][1]*parameter_cov[1][0]-1e-20
result={'scope':'Conditional statistical scenario derived from original WT-DHA39reported rate cells; not a source-established preparation covariance.',
    'estimator':'unweighted_fit_to_the_13_point_means',
    'parameter_order':['Vmax','Km'],'parameter_values':theta,'parameter_units':['umol/min','mM'],
    'model':'v=Vmax*S/(Km+S)',
    'source_reported_columns':['data-1','data-2','data-3'],
    'assumption':'three_reported_curve_vectors_are_IID_exchangeable_units',
    'assumption_source_established':False,'physical_population_identity':None,
    'reported_curve_covariance':point_cov,'conditional_covariance_of_mean_curve':mean_cov,
    'mean_curve_to_parameters_sensitivity':sensitivity,
    'sensitivity_definition':'A=(J^T J-sum_i residual_i Hessian(f_i))^-1 J^T',
    'conditional_selected_parameter_covariance':parameter_cov,
    'conditional_log_efficiency_variance':log_variance,
    'conditional_log_efficiency_standard_uncertainty':math.sqrt(log_variance),
    'independent_directional_refit_checks':mode_checks,
    'independent_directional_log_variance':mode_variance,
    'all_directional_checks_passed':True,
    'published_S5_parameter_covariance':None,
    'current_common_or_kinetic_model_export':None,
    'export_limits':['Vmax_is_not_kcat','physical_sampling_unit_ids_unknown',
        'reporter_direction_and_species_conflict','published_fit_estimator_basis_not_reported',
        'conditional_statistical_model_must_not_be_relabelled_source_established'],
    'source_packet_sha256':hashlib.sha256((HERE/'SOURCE_PACKET_001.json').read_bytes()).hexdigest()}
with (HERE/'POOLED_ESTIMATOR_COVARIANCE_002.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:result[k] for k in ('estimator','parameter_values','conditional_selected_parameter_covariance',
    'conditional_log_efficiency_variance','conditional_log_efficiency_standard_uncertainty',
    'independent_directional_log_variance','all_directional_checks_passed')},indent=2))
