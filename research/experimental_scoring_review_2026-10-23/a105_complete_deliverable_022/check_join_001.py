"""Bounded, source-free A105 consolidation arithmetic; not a production reader.

Run from anywhere with python3. Writes only this workload's arithmetic receipt.
Checks the populated join once, not historical sensitivity grids.
"""
from fractions import Fraction as F
from math import atanh, exp, isclose, log, sqrt, tanh
from pathlib import Path
import json

checks = []


def check(name, actual, expected, tol=3e-12):
    if isinstance(expected, F):
        assert actual == expected, (name, actual, expected)
    else:
        assert isclose(float(actual), float(expected), rel_tol=tol, abs_tol=tol), (name, actual, expected)
    checks.append(name)


def transpose(a):
    return list(map(list, zip(*a)))


def multiply(a, b):
    return [[sum(x * y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def inverse(a):
    n = len(a)
    aug = [list(row) + [F(i == j) for j in range(n)] for i, row in enumerate(a)]
    for i in range(n):
        pivot = next(j for j in range(i, n) if aug[j][i])
        aug[i], aug[pivot] = aug[pivot], aug[i]
        p = aug[i][i]
        aug[i] = [v / p for v in aug[i]]
        for j in range(n):
            if j != i:
                p = aug[j][i]
                aug[j] = [v - p * w for v, w in zip(aug[j], aug[i])]
    return [row[n:] for row in aug]


def numeric(value):
    if isinstance(value, F):
        return {"exact": str(value), "decimal": float(value)}
    if isinstance(value, list):
        return [numeric(x) for x in value]
    if isinstance(value, dict):
        return {k: numeric(v) for k, v in value.items()}
    return value


q, g, k, amount, u, v = map(F, ["1", ".15", "1", "1", "2", "1.6"])
a = (q - g) * v / (k * amount * u)
j = [v/(k*amount*u), -v/(k*amount*u), -a/k, -a/amount, -a/u, a/v]
primitive_variance = list(map(F, [".04", ".0225", ".0025", ".01", ".01", ".01"]))
terms = [x*x*y for x, y in zip(j, primitive_variance)]
residual = F(".09") - F(".0275")
V = sum(terms) + residual
check("full activity equation", a, F(17, 25))
check("condition propagation joins both independent controls", terms[4]+terms[5], F(".00296225"))
check("six named contributions plus distinct residual exactly once", V, F(".11124225"))
S = a*a/(2*V)
check("source separation", S, F(924800, 444969))
B = tanh(float(S)/2)
r = [float(F(24,31)), .85, .8, .85, exp(-.37)]
R = sum(r)/5
D = B*R
check("source bounded contrast", B, .777561486079)
check("five measured correspondence components", R, .792985575805)
check("joined target activity", D, .616595042762)

# Reconstruct the calibrated companion from its actual retained primitives.
prior = Path(__file__).resolve().parent.parent / "a105_calibrated_contract_007/SYNTHETIC_RECORD_001.json"
cal = json.loads(prior.read_text(), parse_float=F, parse_int=F)
primitive = cal["input"]["primitive"]
J = primitive["jacobian_J"]
Sigma = primitive["covariance_matrix"]
C = multiply(multiply(J, Sigma), transpose(J))
z = [row[0] for row in multiply(J, [[x] for x in primitive["values"]])]
assert C == [[F(".230"), F(".115"), F(".060")], [F(".115"), F(".300"), F(".085")], [F(".060"), F(".085"), F(".400")]]
checks.append("all calibrated primitive covariance terms reproduce C")
assert z == [F(".8"), F(".6"), F(".9")]
checks.append("all calibrated primitive means reproduce z")
Cinv = inverse(C)
P = sum(sum(row) for row in Cinv)
weights = [sum(row)/P for row in Cinv]
theta = sum(w*x for w, x in zip(weights, z))
Vt = 1/P
Q = sum((z[i]-theta)*Cinv[i][j]*(z[j]-theta) for i in range(3) for j in range(3))
St = theta*abs(theta)/(2*Vt)
Bt = tanh(float(St)/2)
check("calibrated target mean", theta, F(89,115))
check("calibrated target variance", Vt, .15548163418290856)
check("calibrated disagreement diagnostic", Q, F(5,23))
check("calibrated target bounded contrast", Bt, .7456307045069301)
candidate = max(0, min(D, Bt))
check("one candidate requiring activity and specificity", candidate, D)


def strongest(indexes):
    if not indexes:
        return None
    return max(0, max(indexes)) - max(0, max(-x for x in indexes))


dp = .8*tanh(2)
dw = .4*tanh(1)
pool_examples = {}
for name, indexes in [
    ("one_positive", [dp]),
    ("weaker_agreement", [dp, dw]),
    ("opposition", [dp, -dw]),
    ("ten_equal_positive_plus_opposition", [dp]*10+[-dw]),
    ("equal_opposition", [dp, -dp]),
    ("irrelevant_append", [dp, 0]),
]:
    pool_examples[name] = {"source_indexes": indexes, "recommended_current_proposal": strongest(indexes), "unit_allocation_alternative": tanh(sum(atanh(x) for x in indexes))}
check("pooling opposition", strongest([dp, -dw]), .4665844016783476)
check("unit accumulation alternative", pool_examples["opposition"]["unit_allocation_alternative"], .609869037957144)
check("irrelevant source neutral under current proposal", strongest([dp, 0]), dp)
check("duplicate source representation no gain under current proposal", strongest([dp, dp]), dp)
check("current corrected source fit replaces stronger history", strongest([.2, -dw]), .2-dw)

# New joined missingness checks carry bounds through the current pool and candidate.
known_sum = sum(r) - r[3]
R_bounds = [known_sum/5, (known_sum+1)/5]
D_bounds = [B*x for x in R_bounds]
candidate_bounds = [max(0, min(x, Bt)) for x in D_bounds]
check("missing family lower join", candidate_bounds[0], .4844095901289222)
check("missing family upper join", candidate_bounds[1], .6399218873447938)
missing_pool_bounds = [strongest([dp, -1]), strongest([dp, 1])]
check("unresolved roster member lower", missing_pool_bounds[0], dp-1)
check("unresolved roster member upper", missing_pool_bounds[1], 1)
negative_candidate_bounds = [max(0,min(-.2, -1)), max(0,min(-.2, 1))]
assert negative_candidate_bounds == [0,0]
checks.append("opposed requirement identifies zero projection with unknown other requirement")

# Arithmetic on received cross-case numbers only; no new paper inspection.
published = {
    "CsiD_rounded_graph_rate_difference_umol_per_min": F(".16062")-F(".10484"),
    "BtsT_saturation_10": F(10)/(F("16.5")+10),
    "BtsT_saturation_40": F(40)/(F("16.5")+40),
    "BtsT_declared_10_to_40_response": (F(10)/(F("16.5")+10))/(F(40)/(F("16.5")+40)),
    "IscR_2013_IC50_ratio_strict_lower": F(510,32),
    "IscR_2013_log_ratio_strict_lower": log(510/32),
    "IscR_2025_apparent_Kd_ratio_strict_lower": F(1000,22),
    "IscR_2025_state_comparison_ratio": F(26,22),
    "TriA_identity_fraction": F(466,475),
    "TriA_activity_ratio_strict_lower": F(17)/F(".01"),
}
check("CsiD rounded supplied contrast", published["CsiD_rounded_graph_rate_difference_umol_per_min"], F(".05578"))
check("BtsT shared-Km response", published["BtsT_declared_10_to_40_response"], F(113,212))
check("IscR point-limit ratio", published["IscR_2013_IC50_ratio_strict_lower"], F(255,16))
check("TriA point-limit ratio", published["TriA_activity_ratio_strict_lower"], F(1700))

receipt = {
    "status": "research_arithmetic_only; no policy adopted; no axis completed",
    "checks_passed": len(checks), "checks": checks,
    "activity": {"primitive_order": ["net_rate", "contaminant_rate", "recovery", "protein_amount", "condition_test_rate", "condition_reference_rate"], "primitive_values": [q,g,k,amount,u,v], "primitive_variance": primitive_variance, "jacobian": j, "propagated_terms": terms, "distinct_residual": residual, "effect": a, "variance": V, "standard_uncertainty": sqrt(float(V)), "precision": 1/V, "S": S, "B": B, "correspondence_components": r, "R": R, "D": D},
    "specificity": {"primitive_record": str(prior), "z": z, "C": C, "precision": P, "weights": weights, "theta": theta, "variance": Vt, "standard_uncertainty": sqrt(float(Vt)), "Q": Q, "Q_plus": Q, "Q_minus": Q+2*St, "S": St, "B": Bt},
    "candidate": {"meaning": "activity AND specificity at the declared target scope", "signed_index": min(D,Bt), "coordinate": candidate, "profile_log_ratio": None, "route": "conventional_minimum_of_current_statement_indexes"},
    "pooling_examples": pool_examples,
    "missingness": {"R_full_bounds": R_bounds, "activity_D_bounds": D_bounds, "candidate_bounds": candidate_bounds, "unknown_source_pool_bounds": missing_pool_bounds, "negative_required_projection_bounds": negative_candidate_bounds},
    "published_values_received_in_cross_case_documents": published,
    "inspection": {"new_primary_papers": 0, "new_paper_specific_packets": 0, "production_tests": 0, "target_annotations": 0, "native_or_HPC_jobs": 0},
}
out = Path(__file__).with_name("ARITHMETIC_RESULTS_001.json")
out.write_text(json.dumps(numeric(receipt), indent=2)+"\n")
print(f"{len(checks)} bounded arithmetic checks passed; wrote {out}")
