"""Research arithmetic: reported FolE2 operands plus marked synthetic checks."""
from pathlib import Path
import json
import math

km, kcat, enzyme = 9.87, 0.0011, 0.5
def rate(substrate, km_value=km):
    return enzyme * kcat * substrate / (km_value + substrate) * 60
def response(km_value):
    return (3 / (km_value + 3)) / (50 / (km_value + 50))
r = response(km)
derivative = 1 / (km + 50) - 1 / (km + 3)
h = 1e-4  # Numerical derivative step, not an experimental uncertainty.
finite_difference = (math.log(response(km+h)) - math.log(response(km-h))) / (2*h)
assert math.isclose(derivative, finite_difference, rel_tol=1e-8)
assert math.isclose(rate(50)*r, rate(3), rel_tol=1e-13)
assert math.isclose((14/100)/(75/100), 14/75, rel_tol=1e-13)

# Synthetic covariance example, not FolE2 uncertainty estimates.
v_m, v_z, cov_m_z = .04, .09, .01
v_difference = v_m + v_z - 2*cov_m_z
cov_m_difference = cov_m_z - v_m
v_reconstructed_z = v_m + v_difference + 2*cov_m_difference
assert math.isclose(v_reconstructed_z, v_z, rel_tol=1e-13)

# Exact response scaling under the stated synthetic zero-boundary model.
a, variance, exact_multiplier = .68, .11124225, .14
s_original = a*a/(2*variance)
s_scaled = (a*exact_multiplier)**2/(2*variance*exact_multiplier**2)
assert math.isclose(s_original, s_scaled, rel_tol=1e-13)
out = {
    "source": "10.1128/JB.00287-09",
    "reported_inputs": {"Km_uM":km,"kcat_s_inverse":kcat,"enzyme_uM":enzyme},
    "derived_from_reported_points": {
        "Zn50_to_Mn500":.14,"reverse":100/14,"log_ratio":math.log(.14),
        "Zn50_to_Fe1000":14/75,
        "efficiency_M_inverse_s_inverse":kcat/(km*1e-6),
        "model_rate_at_3_uM_per_min":rate(3),
        "model_rate_at_50_uM_per_min":rate(50),
        "model_50_to_3_response":r,
        "log_response_derivative_per_uM_Km":derivative,
        "Km_variance":None,"Table_2_spread_kind":None,
        "isolated_source_B":None,
    },
    "synthetic_only_checks": {
        "log_M_variance":v_m,"log_Z_variance":v_z,"covariance":cov_m_z,
        "reconstructed_log_Z_variance":v_reconstructed_z,
        "original_S":s_original,"exact_positive_rescaling_S":s_scaled,
    },
    "checks":"native-unit arithmetic, numerical gradient, shared-reference cancellation, exact scale invariance passed",
}
path = Path(__file__).with_name("fole2_parent_arithmetic_004.json")
if path.exists():
    assert json.loads(path.read_text()) == out, "Preserve recorded output; use an additive revision."
else:
    path.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
