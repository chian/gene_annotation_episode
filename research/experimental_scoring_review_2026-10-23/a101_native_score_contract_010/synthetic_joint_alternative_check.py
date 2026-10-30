"""Additive SYNTHETIC arithmetic check including explicit functional alternatives.

No scoring coefficients are fitted or adopted. No search/alignment is executed.
This also adds strict relative checks for the very small E-value calculations
in the first arithmetic artifact; its original generous absolute tolerance is
not relied on for those comparisons.
"""

import json
import math
from pathlib import Path


root = Path(__file__).resolve().parent
data = json.loads((root / "synthetic_arithmetic_results.json").read_text())
assert data["all_values_are_synthetic"] is True
b = data["blast"]
h = data["hmmer"]
sites = data["site_correspondence"]
assert math.isclose(b["E_from_raw"], b["E_from_bits"], rel_tol=1e-12, abs_tol=0)
assert math.isclose(h["domain_tail_P"], 2 ** -55, rel_tol=1e-12, abs_tol=0)
assert math.isclose(h["sequence_tail_P"], 2 ** -57, rel_tol=1e-12, abs_tol=0)

# These are invented alternative-function comparison operands, not discovered hits.
alternative = {
    "function_label": "synthetic_alternative_G",
    "blast_raw_score_points": 195,
    "blast_lambda_inverse_raw_points": 0.267,
    "blast_K": 0.041,
    "hmmer_domain_bits": 64.0,
    "grounding_status": "stipulated_synthetic_separately_characterized_endpoint",
    "scope_status": "stipulated_same_target_focal_family_region",
}
alternative["blast_bits"] = (
    alternative["blast_lambda_inverse_raw_points"] * alternative["blast_raw_score_points"]
    - math.log(alternative["blast_K"])
) / math.log(2)
features = {
    "blast_bits": b["bit_score"],
    "hmmer_domain_bits": h["domain_bit_score"],
    "blast_x_hmmer_bits_squared": b["bit_score"] * h["domain_bit_score"],
    "blast_contrast_bits": b["bit_score"] - alternative["blast_bits"],
    "hmmer_contrast_bits": h["domain_bit_score"] - alternative["hmmer_domain_bits"],
    "blast_query_span_fraction": b["query_span_coverage"],
    "blast_reference_span_fraction": b["reference_span_coverage"],
    "hmmer_profile_span_fraction": h["profile_span_coverage"],
    "blast_identity_fraction": b["identity_fraction_all_columns"],
}
coefficients = dict(data["unadopted_joint_combination_arithmetic"]["coefficients"])
coefficients.update({"blast_contrast_bits": 0.04, "hmmer_contrast_bits": 0.05})
terms = {name: coefficients[name] * value for name, value in features.items()}
terms["intercept"] = coefficients["intercept"]
base = math.fsum(terms.values())
site_bounds = [sites["compatible_fraction_lower"], sites["compatible_fraction_upper"]]
z_bounds = sorted(base + coefficients["site_compatible_fraction"] * value for value in site_bounds)
c_bounds = [1 / (1 + math.exp(-z)) for z in z_bounds]

# The point fixture explicitly supplies the fifth site's incompatible status.
# The original missing-site fixture remains unchanged and retains its bounds.
complete_sites = {"declared_sites": 5, "assessable_sites": 5, "compatible_sites": 3, "unknown_sites": 0}
complete_site_fraction = complete_sites["compatible_sites"] / complete_sites["declared_sites"]
complete_site_term = coefficients["site_compatible_fraction"] * complete_site_fraction
complete_z = base + complete_site_term
complete_c = 1 / (1 + math.exp(-complete_z))
assert math.isclose(complete_z, z_bounds[0], rel_tol=1e-12, abs_tol=0)

# Re-delivery of the same comparison group must not create another group value.
group_values = {"synthetic_shared_family_region": complete_c}
group_values["synthetic_shared_family_region"] = complete_c
assert len(group_values) == 1
assert 0 < complete_c < 1
assert 0 <= c_bounds[0] <= c_bounds[1] <= 1
assert math.isclose(features["blast_contrast_bits"], 0.267 * 5 / math.log(2), rel_tol=1e-12, abs_tol=0)

# A tenfold database multiplier changes E, not this fixed-feature bit-based index.
assert data["blast"]["E_after_tenfold_effective_search_space"] / b["E_from_raw"] == 10.0

result = {
    "all_values_are_synthetic": True,
    "coefficient_status": "invented_arithmetic_convention_not_fitted_not_adopted",
    "interpretation": "bounded_proposed_A101_group_component_not_a_function_probability",
    "source_fixture": "synthetic_arithmetic_results.json",
    "alternative_function_comparisons": alternative,
    "feature_values_excluding_site": features,
    "coefficients": coefficients,
    "summands_excluding_site": terms,
    "complete_site_fixture": complete_sites,
    "complete_site_fraction": complete_site_fraction,
    "complete_site_summand": complete_site_term,
    "complete_linear_index": complete_z,
    "complete_bounded_component": complete_c,
    "missing_site_fixture_preserved": sites,
    "missing_site_linear_index_bounds": z_bounds,
    "missing_site_bounded_component_bounds": c_bounds,
    "actual_real_case_A101_contribution": None,
    "actual_real_case_status": "policy_or_calibration_absent",
    "strict_relative_small_number_checks": "passed",
    "scientific_programs_executed": [],
    "arithmetic_assertions": "passed",
}
print(json.dumps(result, indent=2, allow_nan=False))
