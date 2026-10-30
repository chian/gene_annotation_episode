"""Research arithmetic fixture only: synthetic trees; no biological analysis.

No production reader is implemented here. Published figure counts are manually
entered observations; only their arithmetic is checked. Synthetic tree geometry
is calculated from the fully specified toy trees to avoid impossible cell totals.
Run with python3; emits JSON to stdout and writes no files.
"""
from fractions import Fraction as Q
from itertools import combinations, product
from statistics import median
import json
import math


def leaf(name, length):
    return (name, Q(length), ())


def node(name, length, *children):
    return (name, Q(length), children)


plus = node("root", "0",
    node("F", ".2", node("QF1", ".1", leaf("q", ".6"), leaf("f1", ".2")), leaf("f2", ".3")),
    node("G", ".2", leaf("g1", ".2"), leaf("g2", ".2")))
minus = node("root", "0",
    node("F", ".2", leaf("f1", ".2"), leaf("f2", ".2")),
    node("G", ".2", node("QG1", ".1", leaf("q", ".6"), leaf("g1", ".2")), leaf("g2", ".1")))


def paths(tree):
    output = {}
    def walk(item, path, depth):
        name, edge, children = item
        path = path + ((name, depth + edge),)
        if children:
            for child in children:
                walk(child, path, depth + edge)
        else:
            output[name] = path
    walk(tree, (), Q(0))
    return output


def common(a, b):
    shared = []
    for x, y in zip(a, b):
        if x[0] != y[0]:
            break
        shared.append(x)
    return shared


def pair_topology(tree_paths, a, b, c):
    pairs = [(a, b), (a, c), (b, c)]
    depths = [len(common(tree_paths[x], tree_paths[y])) for x, y in pairs]
    best = max(depths)
    winners = [pairs[i] for i, d in enumerate(depths) if d == best]
    return tuple(sorted(winners[0])) if len(winners) == 1 else None


def distance(tree_paths, a, b):
    ancestor = common(tree_paths[a], tree_paths[b])[-1][1]
    return tree_paths[a][-1][1] + tree_paths[b][-1][1] - 2 * ancestor


def outlier(tree_paths, refs):
    spacing = median([min(distance(tree_paths, x, y) for y in refs if x != y) for x in refs])
    nearest = min(distance(tree_paths, "q", x) for x in refs)
    assert spacing > 0
    factor = Q(1) if nearest == 0 else min(Q(1), spacing / nearest)
    return {"reference_spacing":spacing, "query_nearest":nearest, "factor":factor}


def values(tree, organism):
    t, u = paths(tree), paths(organism)
    f, g = ["f1", "f2"], ["g1", "g2"]
    counts = {"candidate":0, "alternative":0, "outside":0, "unresolved":0}
    detailed = []
    for x, y in product(f, g):
        pair = pair_topology(t, "q", x, y)
        kind = "unresolved" if pair is None else "candidate" if pair == tuple(sorted(("q", x))) else "alternative" if pair == tuple(sorted(("q", y))) else "outside"
        counts[kind] += 1
        detailed.append({"candidate_reference":x, "alternative_reference":y, "topology":kind})
    placement = Q(counts["candidate"] - counts["alternative"], 4)
    histories = []
    for x, y in combinations(f + g, 2):
        a, b = pair_topology(t, "q", x, y), pair_topology(u, "q", x, y)
        status = "unresolved" if a is None or b is None else "concordant" if a == b else "discordant"
        histories.append({"other_taxa":[x,y], "gene_pair":a, "organism_pair":b, "status":status})
    nc = sum(x["status"] == "concordant" for x in histories)
    nd = sum(x["status"] == "discordant" for x in histories)
    nu = sum(x["status"] == "unresolved" for x in histories)
    contact = Q(8, 10)
    rate_dr, rate_bg, rate_ref = Q(32,100000), Q(2,100000), Q(52,100000)
    compatibility = max(Q(0), min(Q(1), (rate_dr-rate_bg)/(rate_ref-rate_bg)))
    explanation = (contact + compatibility) / 2
    assert nu == 0
    history = (nc + nd * explanation) / 6
    of, og = outlier(t, f), outlier(t, g)
    support = max(Q(0), placement) * of["factor"] * history
    opposition = max(Q(0), -placement) * og["factor"]
    return {"placement_counts":counts,"placement_triplets":detailed,"P":placement,
            "outlier_F":of,"outlier_G":og,"history_triplets":histories,
            "history_counts":{"concordant":nc,"discordant":nd,"unresolved":nu,"denominator":6},
            "contact":contact,"transfer_compatibility":compatibility,"explanation":explanation,
            "H":history,"support":support,"opposition":opposition,"signed":support-opposition}


a, b = values(plus, minus), values(minus, minus)
assert a["P"] == 1 and b["P"] == -1
assert a["outlier_F"]["reference_spacing"] == Q(3,5)
assert a["outlier_F"]["query_nearest"] == Q(4,5)
assert a["outlier_F"]["factor"] == Q(3,4)
assert b["outlier_G"]["reference_spacing"] == Q(2,5)
assert b["outlier_G"]["query_nearest"] == Q(4,5)
assert b["outlier_G"]["factor"] == Q(1,2)
assert a["history_counts"]["concordant"] == 0
assert b["history_counts"]["concordant"] == 6
assert a["explanation"] == Q(7,10)
assert a["H"] == Q(7,10) and b["H"] == 1
assert a["support"] == Q(21,40) and a["opposition"] == 0
assert b["support"] == 0 and b["opposition"] == Q(1,2)

mean_support = (8 * a["support"] + 2 * b["support"]) / 10
mean_opposition = (8 * a["opposition"] + 2 * b["opposition"]) / 10
signed = mean_support - mean_opposition
assert mean_support == Q(21,50) and mean_opposition == Q(1,10) and signed == Q(8,25)
scores = sorted([a["signed"]] * 8 + [b["signed"]] * 2)
quantile = lambda p: scores[max(0, math.ceil(p * len(scores)) - 1)]
assert quantile(.025) == Q(-1,2) and quantile(.975) == Q(21,40)

published = {"Bp1689_P":Q(4-0,4),"Bp1670_P":Q(0-4,4),
             "Bp1689_PorE_resampling_fraction":Q(99,100),
             "porphyranase_clade_resampling_fraction":Q(55,100)}
assert published["Bp1689_P"] == 1 and published["Bp1670_P"] == -1

# Interval checks preserve unknown cells; no missing value is imputed to zero.
missing_explanation_point = [Q(0), Q(3,4)]
contact_only_explanation = [Q(2,5), Q(9,10)]
contact_only_support = [Q(3,4) * x for x in contact_only_explanation]
assert contact_only_support == [Q(3,10), Q(27,40)]
missing_explanation_ensemble = [-mean_opposition, Q(8,10)*Q(3,4)-mean_opposition]
assert missing_explanation_ensemble == [Q(-1,10), Q(1,2)]
unresolved_P_counts = {"candidate":2,"alternative":1,"outside":0,"unresolved":1,"denominator":4}
unresolved_P_bounds = [Q(2-1-1,4), Q(2-1+1,4)]
assert unresolved_P_bounds == [Q(0),Q(1,2)]

# Complete Cartesian endpoint check for bounded score range under this formula.
grid = [Q(0),Q(1,5),Q(1,2),Q(1)]
grid_checks = 0
for p, of, og, h in product([-1,Q(-1,2),Q(0),Q(1,2),1],grid,grid,grid):
    s=max(Q(0),p)*of*h
    c=max(Q(0),-p)*og
    assert 0<=s<=1 and 0<=c<=1 and -1<=s-c<=1
    grid_checks += 1


def export(obj):
    if isinstance(obj, Q):
        return {"exact":str(obj),"decimal":float(obj)}
    if isinstance(obj, dict):
        return {k:export(v) for k,v in obj.items()}
    if isinstance(obj, (list,tuple)):
        return [export(v) for v in obj]
    return obj


result={"status":"all assertions passed; research fixture only",
        "published_arithmetic_only":published,
        "synthetic_plus":a,"synthetic_minus":b,
        "synthetic_ensemble":{"replicates":10,"plus_multiplicity":8,"minus_multiplicity":2,
                              "positive":mean_support,"opposing":mean_opposition,"signed":signed,
                              "empirical_025":quantile(.025),"empirical_975":quantile(.975),
                              "positive_score_fraction":Q(8,10),"opposing_score_fraction":Q(2,10)},
        "missingness":{"unobserved_explanation_point_support_bounds":missing_explanation_point,
                       "contact_only_explanation_bounds":contact_only_explanation,
                       "contact_only_point_support_bounds":contact_only_support,
                       "unobserved_explanation_ensemble_signed_bounds":missing_explanation_ensemble,
                       "unresolved_triplet_counts":unresolved_P_counts,
                       "unresolved_placement_bounds":unresolved_P_bounds},
        "bounded_range_grid_checks":grid_checks,
        "limitations":["Synthetic tree calculations are not analysis of biological data.",
                       "Published topology was manually read from the source figure, not reconstructed by this script.",
                       "No production reader, scoring policy, uncertainty calibration, or axis completion is established."]}
print(json.dumps(export(result),indent=2))
