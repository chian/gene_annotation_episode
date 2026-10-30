"""Standalone research arithmetic, not a production reader or adopted policy.

Reported operands are manually transcribed from exact source selectors; source
values are rounded/approximate. Synthetic scenarios are explicitly segregated.
"""
from fractions import Fraction as F
import json
import math
from pathlib import Path

fd, nadh = F(23), F(8)
eps_fd, eps_h = F('8.6'), F('1.2')
spectral_multiplier = eps_fd / eps_h
shortfall = fd - nadh
needed_fd_accumulation = shortfall / spectral_multiplier
actual = {
    'origin': 'calculated_from_rounded_reported_values',
    'qualification': 'Descriptive reported-protocol comparison; not established common-condition discrepancy.',
    'Fd_endpoint_Vmax_umol_min_mg': float(fd),
    'NADH_endpoint_Vmax_umol_min_mg': float(nadh),
    'conditional_difference_NADH_minus_Fd': float(nadh-fd),
    'conditional_ratio_NADH_over_Fd': float(nadh/fd),
    'conditional_log_ratio': math.log(float(nadh/fd)),
    'spectral_interference_multiplier_380nm': float(spectral_multiplier),
    'conditional_Fd_accumulation_needed_to_explain_shortfall_umol_min_mg': float(needed_fd_accumulation),
    'conditional_required_accumulation_fraction_of_23': float(needed_fd_accumulation/fd),
    'measured_Fd_accumulation_in_380nm_assay': None,
    'corrected_NADH_rate': None,
    'discrepancy_variance': None,
    'standardized_discrepancy': None,
    'combined_activity_estimate': None,
    'Fig3A_H2_per_added_NAD_from_caption_slope': float(F(1)/F('1.1')),
    'Fig3B_H2_per_added_NADPH_from_caption_slope': float(F(1)/F('2.2')),
    'conditional_NADPH_per_NAD_from_ratio_of_slopes': float(F('2.2')/F('1.1')),
}

# Synthetic, known estimator covariance and common unbiased estimand stipulated.
# No paper value, replicate count, precision or validity claim is supplied here.
x1, x2 = F(20), F(22)
v1, v2, cov12 = F(4), F(9), F(1)
variance = v1+v2-2*cov12
w1, w2 = (v2-cov12)/variance, (v1-cov12)/variance
synthetic = {
    'origin': 'synthetic_illustration_only',
    'assumptions': ['same common-condition estimand', 'unbiased estimators', 'known joint estimator covariance [[4,1],[1,9]]', 'no unidentified differential systematic error'],
    'estimates': [float(x1), float(x2)],
    'difference': float(x1-x2),
    'difference_variance': float(variance),
    'standardized_difference': float((x1-x2)/math.sqrt(float(variance))),
    'squared_standardized_difference': float((x1-x2)**2/variance),
    'GLS_weights': [float(w1), float(w2)],
    'GLS_mean': float(w1*x1+w2*x2),
    'GLS_mean_variance': float((v1*v2-cov12**2)/variance),
    'p_value': None,
    'function_probability': None,
    'final_annotation_credit': None,
}
assert w1+w2 == 1
assert variance == 11
assert w1*x1+w2*x2 == F(226,11)
assert (v1*v2-cov12**2)/variance == F(35,11)
assert needed_fd_accumulation == F(90,43)
result = {'actual_source_partial': actual, 'synthetic_known_covariance': synthetic}
Path(__file__).with_name('ARITHMETIC_001.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
