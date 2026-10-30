"""Fixed research arithmetic fixture. Not a reader, library scorer or credit binding."""
import json
import math
from fractions import Fraction as F
from pathlib import Path

# Entire fixture is synthetic; source comparisons below retain their origin labels.
rows = [
    (1, 1, 5, .5), (2, 1, 4, .3), (3, 1, 2, .4),
    (4, 1, 5, 5), (5, 1, 3, .5), (6, 1, 1, .5),
    (7, 1, 6, .6), (8, 1, 9, .9), (9, 0, 5, .5), (10, 0, 4, .4),
]
assert len({r[0] for r in rows}) == len(rows) == 10
access = sum(a for _, a, c, o in rows)
ae = sum(a and 2.5 <= c <= 10 for _, a, c, o in rows)
aeo = sum(a and 2.5 <= c <= 10 and 0 <= o <= 1 for _, a, c, o in rows)
assert (access, ae, aeo) == (8, 6, 5)
qa, qe, qo = F(access, 10), F(ae, access), F(aeo, ae)
assert qa * qe * qo == F(aeo, 10) == F(1, 2)

# Display order cannot change the fully observed joint answer.
oa = sum(a and 0 <= o <= 1 for _, a, c, o in rows)
assert F(access, 10) * F(oa, access) * F(aeo, oa) == F(1, 2)

# Unpaired marginal multiplication would give a different and unjustified result.
e = sum(2.5 <= c <= 10 for _, a, c, o in rows)
o = sum(0 <= ox <= 1 for _, a, c, ox in rows)
marginal_product = F(access, 10) * F(e, 10) * F(o, 10)
assert marginal_product == F(72, 125) and marginal_product != F(1, 2)
marginal_lower = max(F(0), F(access+e+o, 10)-2)
marginal_upper = min(F(access, 10), F(e, 10), F(o, 10))
assert (marginal_lower, marginal_upper) == (F(1, 2), F(4, 5))

x = (F(42, 10)-F(2, 10))/F(8, 10)
xlo = (F(41, 10)-F(21, 100))/F(82, 100)
xhi = (F(43, 10)-F(19, 100))/F(78, 100)
assert x == 5 and F(25, 10) < xlo <= xhi < 10
assert x / F(8, 10) != x  # a second recovery correction would change the value

epsilon = math.sqrt(math.log(2/.05)/(2*10))
sampling_interval = [max(0, .5-epsilon), min(1, .5+epsilon)]
assert abs(epsilon - .4294694083467376) < 1e-14

# Research scenarios are explicit membership bounds on the same fixed denominator.
base = [(1,1),(1,1),(0,0),(0,0),(1,1),(0,0),(1,1),(1,1),(0,0),(0,0)]
variants = {"base": base}
v = base.copy(); v[2] = (0,1); variants["unit3_boundary_uncertainty"] = v
v = base.copy(); v[5] = (0,0); variants["unit6_nondetect_below_requirement"] = v
v = base.copy(); v[5] = (0,1); variants["unit6_high_detection_limit"] = v
v = base.copy(); v[1] = (0,1); variants["unit2_conflicting_oxygen"] = v
variants["all_missing"] = [(0,1)] * 10
answers = {}
for name, v in variants.items():
    lo, hi = sum(t[0] for t in v)/10, sum(t[1] for t in v)/10
    assert 0 <= lo <= hi <= 1
    masses = [lo, hi-lo, 1-hi]
    assert abs(sum(masses)-1) < 1e-14
    answers[name] = {"lower":lo, "upper":hi, "point":lo if lo==hi else None,
                     "supported_unresolved_contradicted":masses}
assert answers["unit3_boundary_uncertainty"]["upper"] == .6
assert answers["unit2_conflicting_oxygen"]["lower"] == .4
assert answers["all_missing"]["point"] is None

# Duplicate source representations retain one unique sampling unit.
deduped = {row[0]: row for row in rows + [rows[0], rows[0]]}
assert len(deduped) == 10
assert sum(a and 2.5<=c<=10 and 0<=o<=1 for _,a,c,o in deduped.values()) == 5

source_comparisons = {
    "huc_margin_lower_approx": {"value": float(F(530,40)), "relation":">approximately",
        "origin":"derived_from_reported_benchmark_and_censored_residual"},
    "hyd1_conditional_margin_approx": {"value":float(F(530,4000)),
        "origin":"derived_diagnostic_only_unmatched_air_context"},
    "ttr_visual_margin_approx": {"value":float(F(33,10)/F(25,10)),
        "range":[float(F(32,10)/F(25,10)),float(F(34,10)/F(25,10))],
        "origin":"derived_from_visual_plot_reading_not_raw_data"},
}
assert source_comparisons["huc_margin_lower_approx"]["value"] == 13.25
assert source_comparisons["hyd1_conditional_margin_approx"]["value"] == .1325
assert source_comparisons["ttr_visual_margin_approx"]["value"] == 1.32

result = {
    "status":"passed", "scope":"fixed research arithmetic only; no scientific or production run",
    "synthetic_counts":{"n":10,"access":access,"access_exposure":ae,"joint":aeo},
    "synthetic_components":[float(qa),float(qe),float(qo)],
    "synthetic_joint":.5, "synthetic_display":50,
    "unpaired_marginal_product_not_used":float(marginal_product),
    "marginal_joint_bounds":[float(marginal_lower),float(marginal_upper)],
    "calibration_corrected":float(x),"calibration_bounds":[float(xlo),float(xhi)],
    "sampling_epsilon":epsilon,"synthetic_sampling_interval":sampling_interval,
    "scenarios":answers,"source_comparisons":source_comparisons,
    "checked_invariants":["conditional_product_equals_joint_fraction","display_order_invariance",
        "no_marginal_independence_assumption","correction_once","bounded_missingness",
        "mass_conservation","duplicate_invariance","reported_vs_synthetic_origin_labels"],
}
out = Path(__file__).with_name("ARITHMETIC_RESULTS_001.json")
assert not out.exists(), "Preserve existing results; write an additive revision instead."
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"status":result["status"],"results_path":str(out),
                  "checked_invariants":result["checked_invariants"]},indent=2))
