"""Research-only numerical proposal; no native search or production scorer."""
from pathlib import Path
import json
import math

HERE = Path(__file__).resolve().parent
prior = json.loads((HERE.parent / "a101_native_score_contract_010/synthetic_joint_alternative_results.json").read_text())
f = prior["feature_values_excluding_site"]
inputs = {
    "b_f": f["blast_bits"], "b_g": prior["alternative_function_comparisons"]["blast_bits"],
    "h_f": f["hmmer_domain_bits"], "h_g": 64.0,
    "query_span": f["blast_query_span_fraction"],
    "reference_span": f["blast_reference_span_fraction"],
    "profile_span": f["hmmer_profile_span_fraction"],
    "identity": f["blast_identity_fraction"], "site_fraction": .6,
}

def sigmoid(z):
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    t = math.exp(z)
    return t / (1 + t)

def calculate(x, score_unit_scale=1.0):
    # score_unit_scale multiplies all bit operands; inverse-unit coefficients compensate.
    b_f, b_g, h_f, h_g = [x[k] * score_unit_scale for k in ("b_f", "b_g", "h_f", "h_g")]
    blast = (.025*b_f + .040*(b_f-b_g)) / score_unit_scale
    hmmer = (.020*h_f + .050*(h_f-h_g)) / score_unit_scale
    fraction_sum = sum(x[k] for k in ("query_span", "reference_span", "profile_span", "identity", "site_fraction"))
    z = -3 + .5*blast + .5*hmmer + .5*fraction_sum
    return {"blast_index": blast, "hmmer_index": hmmer,
            "pooled_algorithm_index": .5*(blast+hmmer),
            "fraction_sum": fraction_sum, "z": z, "bounded_component": sigmoid(z)}

base = calculate(inputs)
assert math.isclose(base["bounded_component"], .6297865655757878, rel_tol=1e-13)
assert math.isclose(calculate(inputs, math.log(2))["z"], base["z"], rel_tol=1e-13)
upper = calculate({**inputs, "site_fraction": .8})
assert base["bounded_component"] < upper["bounded_component"]
# Fixed alternative/coverage/site inputs: no adverse cross-score derivative.
for b in (0, 50, 325, 350, 400, 1000):
    for h in (0, 50, 325, 350, 400, 1000):
        x = {**inputs, "b_f": b, "h_f": h}
        z = calculate(x)["z"]
        assert math.isclose(calculate({**x, "b_f": b+1})["z"]-z, .0325, rel_tol=1e-10)
        assert math.isclose(calculate({**x, "h_f": h+1})["z"]-z, .035, rel_tol=1e-10)
        assert math.isclose(calculate({**x, "b_g": x["b_g"]+1})["z"]-z, -.020, rel_tol=1e-10)
        assert math.isclose(calculate({**x, "h_g": x["h_g"]+1})["z"]-z, -.025, rel_tol=1e-10)

receipt = {
    "status": "research_proposal_not_adopted_or_calibrated",
    "all_measurements_and_coefficients_are_synthetic": True,
    "inputs": inputs, "complete_example": base,
    "unknown_fifth_site": {"site_fraction_bounds": [.6, .8], "point": None,
                           "bounded_component_bounds": [base["bounded_component"], upper["bounded_component"]]},
    "partial_derivatives_of_z": {"b_f": .0325, "h_f": .035, "b_g": -.020, "h_g": -.025},
    "prior_polynomial_defect": {"partial_b_at_h400": -.015, "partial_h_at_b400": -.010},
    "checked": ["filled arithmetic", "native score-unit conversion", "missing-site bounds",
                "positive own-score and negative alternative-score partial derivatives on 36 paired score settings"],
    "whole_axis_aggregation": None,
    "production_or_scientific_jobs_executed": False,
}
output = HERE / "monotone_native_parent_arithmetic_004.json"
payload = json.dumps(receipt, indent=2) + "\n"
if output.exists():
    assert output.read_text() == payload, "Preserve prior receipt; use additive correction"
else:
    output.write_text(payload)
print(json.dumps({"status": "passed", "complete_example": base,
                  "missing_site_interval": receipt["unknown_fifth_site"]["bounded_component_bounds"],
                  "receipt": str(output)}))
