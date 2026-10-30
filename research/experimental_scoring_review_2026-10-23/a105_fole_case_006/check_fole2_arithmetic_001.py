#!/usr/bin/env python3
"""Research arithmetic checks only; not a paper reader or annotation scorer."""

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "fole2_numerical_cells_001.json").read_text())
groups = []


def near(actual, expected, *, rel=1e-11, abs_tol=1e-13):
    assert math.isclose(actual, expected, rel_tol=rel, abs_tol=abs_tol), (
        actual, expected
    )


rows = {r["metal"]: r for r in data["metal_assay"]["rows"]}
reference = rows["Mn(II)"]["relative_activity_percent"]
for row in rows.values():
    near(row["response_relative_to_Mn500"], row["relative_activity_percent"] / reference)
    if row["printed_spread_percent_points"] is None:
        assert row["converted_printed_spread"] is None
    else:
        near(row["converted_printed_spread"], row["printed_spread_percent_points"] / 100)
    assert row["shared_reference"] == "Mn500_same_normalization"
groups.append("reported-relative-unit conversions with unknown reference spread")

r = data["metal_response_calculations"]
zn = rows["Zn(II)"]["relative_activity_percent"]
fe = rows["Fe(II)"]["relative_activity_percent"]
near(r["Zn50_over_Mn500"], zn / reference)
near(r["Mn500_over_Zn50"], reference / zn)
near(r["Zn50_over_Mn500"] * r["Mn500_over_Zn50"], 1)
near(r["log_Zn50_over_Mn500"], math.log(zn / reference))
near(r["Zn_printed_spread_over_mean"], rows["Zn(II)"]["printed_spread_percent_points"] / zn)
near(r["source_relative_units"] * r["same_molecule_identity_factor"]
     * r["Zn50_over_Mn500"], r["target_relative_units"])
assert r["target_absolute_rate"] is None
assert r["score_relevance_multiplier"] is None
assert r["uncertainty_variance"] is None
groups.append("condition response, reciprocal, log shift and same-molecule reconstruction")

near(r["Zn50_over_Fe1000"], (zn / reference) / (fe / reference))
near(r["Zn50_over_Fe1000"], zn / fe)
# Gradients in coordinates (log Zn, log Fe, log Mn). The shared Mn term cancels.
g_zn_mn = (1, 0, -1)
g_fe_mn = (0, 1, -1)
assert tuple(a-b for a, b in zip(g_zn_mn, g_fe_mn)) == (1, -1, 0)
# Multiplying source Mn by Zn/Mn reconstructs Zn; source error is not added again.
g_source_mn = (0, 0, 1)
assert tuple(a+b for a, b in zip(g_source_mn, g_zn_mn)) == (1, 0, 0)
groups.append("common normalization and reconstructed-source covariance cancellation")

kin = data["kinetics"]
E, k, K = kin["enzyme_uM"], kin["kcat_s_inv"], kin["Km_uM"]
near(kin["Vmax_uM_per_s"], E * k)
near(kin["catalytic_efficiency_M_inv_s_inv"], k / (K * 1e-6))
evaluations = {row["GTP_uM"]: row for row in kin["evaluations"]}
for S, row in evaluations.items():
    assert kin["GTP_range_uM"][0] <= S <= kin["GTP_range_uM"][1]
    near(row["fraction_of_maximum"], S/(K+S))
    near(row["rate_uM_per_s"], E*k*S/(K+S))
    near(row["rate_uM_per_min"], 60*row["rate_uM_per_s"])
    assert row["status"] == "model_derived_not_raw_data"
assert kin["model_evaluation_is_raw_observation"] is False
groups.append("kinetic model evaluation, range and micromolar/second/minute conversions")

rate3, rate50 = evaluations[3]["rate_uM_per_s"], evaluations[50]["rate_uM_per_s"]
near(kin["response_3_over_50"], rate3/rate50)
near(kin["response_3_over_50"], (3/(K+3))/(50/(K+50)))
near(kin["response_50_over_3"], rate50/rate3)
near(kin["response_3_over_50"]*kin["response_50_over_3"], 1)
near(evaluations[50]["rate_uM_per_min"] * kin["response_3_over_50"],
     evaluations[3]["rate_uM_per_min"])
# The ratio expression has no E or kcat term; do not add their errors twice.
derivative = 1/(K+50)-1/(K+3)
near(kin["log_response_Km_derivative_uM_inv"], derivative)
step = 1e-4  # numerical differentiation step, not an experimental uncertainty
log_ratio = lambda km: math.log((3/(km+3))/(50/(km+50)))
near((log_ratio(K+step)-log_ratio(K-step))/(2*step), derivative, rel=1e-8)
near(-1/(K+50) + derivative, -1/(K+3))
assert kin["parameter_covariance"] is None
assert kin["kinetic_x_metal_factorization_supported"] is False
groups.append("substrate mapping and shared-parameter Jacobian cancellation")

for row in data["metal_assay"]["nondetections"] + [data["metal_assay"]["no_added_metal"]]:
    assert row["reported_relative_activity_percent"] == 0
    assert row["observation_kind"] == "nondetected"
    assert row["latent_activity"] is None
    assert row["detection_limit"] is None
assert data["metal_assay"]["covariance"] is None
assert data["metal_assay"]["independent_preparation_count"] is None
assert data["metal_assay"]["figure_3_assay_sets"] == 4
assert data["metal_assay"]["figure_3_replicates_per_set"] == 3
assert data["metal_assay"]["figure_3_SD_sampling_unit"] is None
assert data["metal_assay"]["table_2_spread_kind"] is None
groups.append("nondetection, sampling units and missing uncertainty remain unresolved")

c = data["correspondence"]
for row in c["structural_comparisons"]:
    near(row["source_full_span_coverage"], row["aligned_Ca"] / c["source_full_monomer_residues"])
    assert row["target_full_span_coverage"] is None
    assert row["calibrated_activity_factor"] is None
assert c["B_subtilis_N_gonorrhoeae"]["calibrated_activity_factor"] is None
assert c["B_subtilis_N_gonorrhoeae"]["alignment_denominator"] is None
assert all(v is None for v in data["source_isolation"].values())
assert data["metal_content"]["occupancy_correction_allowed"] is False
assert data["metal_content"]["assay_active_site_occupancy"] is None
assert data["primary_source"]["primary_papers_inspected"] == 1
groups.append("one-sided correspondence cannot manufacture activity or occupancy calibration")

print(f"PASS: {len(groups)} arithmetic and missing-data groups")
for group in groups:
    print(f"- {group}")
