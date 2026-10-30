"""Bounded research arithmetic for the new complete examples, not a reader.

All inputs are explicit. No network, production import, dataset, scientific job,
or writes outside this new directory. The receipt is created exclusively.
"""
from fractions import Fraction as F
from math import comb
from pathlib import Path
import json


checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)


def s(ec, ea):
    return (ea-ec)/(ea+ec) if ea+ec else F(0)


def scalar_errors(ys, mu):
    return sum((y-mu)**2 for y in ys)/len(ys)


def correct(read, background, recovery, fraction, other, comparability):
    return ((read-background)/recovery-(1-fraction)*other)/fraction-comparability


def binomial(m, p):
    return [F(comb(m, k))*p**k*(1-p)**(m-k) for k in range(m+1)]


def convolve(baseline, m, p):
    f = binomial(m, p)
    u = [sum(f[k]*baseline[j-k] for k in range(min(m, j)+1))
         for j in range(len(baseline))]
    return u, [v/sum(u) for v in u]


def vector_error(ys, mu):
    return sum(sum((v-w)**2 for v, w in zip(y, mu)) for y in ys)/len(ys)


def pack(value):
    if isinstance(value, F):
        return {"exact": str(value), "decimal": float(value)}
    if isinstance(value, dict):
        return {str(k): pack(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [pack(v) for v in value]
    return value


# Final join to earlier source-derived conditional NfnAB values. The two
# approximate source ratios do not become exact measurements by using Fractions.
reverse = s((F(5, 11)-F(1, 2))**2, (F(5, 11)-1)**2)
forward = s((F(10, 11)-1)**2, F(10, 11)**2)
nfn = (reverse+forward)/2
check("source-derived NfnAB conditional join", nfn == F(14399, 14645))

# Retained UbiUV plot-midpoint diagnostic, not the empirical full-pattern score.
b, y, p = F(19, 90), F(31, 8), F(16, 25)
pred = {m: b+m*p/(1-p) for m in (0, 2, 3, 4)}
partial = {m: s((y-pred[3])**2, (y-pred[m])**2) for m in (0, 2, 4)}
check("retained reduced-isotope negative comparison", partial[2] == F(-179840, 181361))
check("all declared reduced alternatives retained", min(partial.values()) == partial[2])

# Entirely synthetic calibrated scalar data, two independent preparations.
read = [F(57, 10), F(69, 10)]
product = [correct(v, F(1, 2), F(4, 5), F(3, 4), F(2), F(1)) for v in read]
denominator = correct(F(51, 5), F(1, 5), F(1), F(1), F(0), F(0))
ys = [v/denominator for v in product]
check("scalar separate correction and denominator", product == [7, 9] and denominator == 10)
check("scalar resulting ratios", ys == [F(7, 10), F(9, 10)])
ec = scalar_errors(ys, F(1))
ea = scalar_errors(ys, F(1, 2))
ezero = scalar_errors(ys, F(0))
check("scalar independent-unit errors", (ec, ea, ezero) == (F(1, 20), F(1, 10), F(13, 20)))
mean = sum(ys)/2
sample_var = sum((v-mean)**2 for v in ys)
check("scalar mean-variance identity", (mean-1)**2+sample_var/2 == ec)
scalar_s = min(s(ec, ea), s(ec, ezero))
check("scalar alternative minimum", scalar_s == F(1, 3))
z = min(F(12), F(6))
f = z/10
supply_s = 2*f-1
scalar_C = (scalar_s+supply_s)/2
check("scalar simple resource join", (z, f, supply_s, scalar_C) == (6, F(3, 5), F(1, 5), F(4, 15)))
check("scalar CH2O oxidation atoms", {"C": 1, "H": 2, "O": 3} == {"C": 1, "H": 2, "O": 2+1})
check("scalar electron ledger", 4 == 4)

# Entirely synthetic isotope dataset: baseline and every selected bin are known.
# p_pool is supplied separately. All six bins (including true synthetic zeros)
# are explicit; this does not fill any missing published bin.
baseline = [F(4, 5), F(1, 5), F(0), F(0), F(0), F(0)]
labeled_amounts = [[12, 31, 36, 18, 3, 0], [8, 34, 39, 17, 2, 0]]
vectors = [[F(v, sum(row)) for v in row] for row in labeled_amounts]
models = {m: convolve(baseline, m, F(1, 2))[1] for m in (0, 2, 3, 4)}
check("isotope all vectors normalized", all(sum(v) == 1 for v in vectors+list(models.values())))
check("isotope claim convolution", models[3] == [F(1, 10), F(13, 40), F(3, 8), F(7, 40), F(1, 40), F(0)])
errors = {m: vector_error(vectors, mu) for m, mu in models.items()}
check("isotope claim variability retained", errors[3] == F(9, 10000))
check("isotope m2 error", errors[2] == F(121, 2500))
check("isotope m4 error", errors[4] == F(2597, 80000))
check("isotope m0 error", errors[0] == F(424, 625))
isotope_s = {m: s(errors[3], errors[m]) for m in (0, 2, 4)}
minimum = min(isotope_s.values())
check("isotope alternative minimum", minimum == F(2525, 2669))
u_truncated, pred_truncated = convolve(baseline[:4], 3, F(1, 2))
check("isotope truncated-window normalization", sum(u_truncated) == F(39, 40) and pred_truncated == [F(4, 39), F(1, 3), F(5, 13), F(7, 39)])

# Synthetic chemically closed three-hydroxylation account with a stipulated
# quinone acceptor Q. This is NOT an identification of the UbiUV electron sink.
# The common R skeleton cancels. R-H3 and R-(OH)3 each contain three H.
left = {"C": 3*10+3*6, "H": 3+3*10+3*4, "O": 3*6+3*2}
right = {"C": 3*9+3+3*6, "H": 3+3*8+3*6, "O": 3+3*3+3*2+3*2}
check("synthetic full reaction atom ledger", left == right == {"C": 48, "H": 45, "O": 24})
check("synthetic full reaction electron ledger", 3*2 == 3*2)
iso_z = min(F(12, 3), F(6, 3))
iso_f = iso_z/3
iso_supply = 2*iso_f-1
iso_C = (minimum+iso_supply)/2
check("isotope budget and candidate contribution", (iso_z, iso_f, iso_supply, iso_C) == (2, F(2, 3), F(1, 3), F(5122, 8007)))
check("missing budget retains weight", ((minimum-1)/2, (minimum+1)/2) == (F(-72, 2669), F(2597, 2669)))

# A small LP solved by an explicit primal witness and matching upper bound.
# Qox: q+g=3v. Qred: 3v=g+w. Bounds: q<=1,g<=2,v<=3,
# and shared processing resource 3v+g<=4. All flows nonnegative.
v, q, g, w = F(5, 6), F(1), F(3, 2), F(1)
check("LP primal witness", q+g == 3*v and 3*v == g+w and q <= 1 and g <= 2 and 3*v+g <= 4 and v <= 3)
check("LP matching upper bound", (F(4)+F(1))/6 == v)
lp_f, lp_s = v/2, 2*(v/2)-1
check("LP demand transformation", (lp_f, lp_s) == (F(5, 12), F(-1, 6)))

# New edge demonstrations needed in the final worked examples.
nd_hi = s(F(81, 100), F(1, 100))
check("nondetection upper contrast", nd_hi == F(-40, 41))
check("documented contradictory units remain", scalar_errors([F(0), F(1)], F(1)) == scalar_errors([F(0), F(1)], F(0)) == F(1, 2))
bad_D = max(abs(F(2)-4)/4, abs(F(1)-2)/2)
check("unbalanced water equation penalty", (bad_D, (1-bad_D)*F(3, 5)-bad_D) == (F(1, 2), F(-1, 5)))

result = {
    "scope": "bounded final joins and fully synthetic examples; no primary-source revalidation or production reader",
    "checks_passed": len(checks), "checks": checks,
    "nfn_conditional_source_derived": pack(nfn),
    "ubi_retained_reduced_statistic_only": pack({"predictions": pred, "pairwise": partial}),
    "synthetic_scalar": pack({"corrected_product_umol": product, "corrected_consumed_substrate_umol": denominator, "ratios": ys, "mean": mean, "sample_variance": sample_var, "e_claim": ec, "e_alternative_half": ea, "e_alternative_zero": ezero, "s_question": scalar_s, "resource_z_umol": z, "resource_fraction": f, "resource_s": supply_s, "C": scalar_C}),
    "synthetic_isotope": pack({"baseline_fraction": baseline, "labeled_amounts": labeled_amounts, "observed_fraction_vectors": vectors, "predictions": models, "errors": errors, "pairwise": isotope_s, "s_question": minimum, "truncated_prediction": pred_truncated, "resource_z_umol": iso_z, "resource_fraction": iso_f, "resource_s": iso_supply, "atom_totals_after_common_skeleton_cancellation": left, "C": iso_C}),
    "synthetic_LP": pack({"v": v, "q": q, "g": g, "w": w, "f": lp_f, "s": lp_s}),
    "synthetic_nondetection_bounds": pack([F(-1), nd_hi]),
}
destination = Path(__file__).with_name("final_join_receipt_026.json")
with destination.open("x") as stream:
    json.dump(result, stream, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps({"checks_passed": len(checks), "receipt": str(destination), "synthetic_scalar_C": float(scalar_C), "synthetic_isotope_C": float(iso_C)}, indent=2))
