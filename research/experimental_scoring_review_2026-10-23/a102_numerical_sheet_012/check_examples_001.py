"""Research-only arithmetic checks of the fixed A102 draft illustrations.

This is not a source reader, alignment program, production scorer, or runtime
component. All inputs below are explicit copies of the draft's declared example
numbers; synthetic inputs are labeled. It writes only new research check files.
"""
import json
import math
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
checks = []


def checked(name, condition):
    checks.append({"check": name, "passed": bool(condition)})
    assert condition, name


def near(a, b):
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def k(distance, scale):
    # A pure arithmetic expression over these fixed examples, not a reader.
    return 1 / (1 + (distance / scale) ** 2)


published = []
for name, n, lt, lr, rmsd, z, atom in [
    ("AF2372_MJ0109", 209, 252, 252, 1.5, None, None),
    ("MJ0226_1ADJ", 76, 193, 421, 2.7, 5.9, "C_alpha"),
    ("MJ0226_1ATI", 75, 193, 505, 3.1, 4.6, "C_alpha"),
]:
    coverage = 2 * n / (lt + lr)
    geometry = k(rmsd, 2.0)
    base = coverage * geometry
    row = {
        "example": name,
        "origin": "reported_primary_numbers_and_declared_metadata_denominators",
        "rmsd_angstrom": rmsd,
        "matched_residue_pairs": n,
        "target_scope_length": lt,
        "reference_scope_length": lr,
        "length_definition": "paper_reported_monomer" if name.startswith("AF") else "RCSB_deposited_polymer_entity_sequence",
        "native_reported_z": z,
        "point_atom_selection": atom,
        "actual_pair_map": None,
        "coordinate_model_uncertainty": None,
        "independent_replication_count": None,
        "target_coverage": n / lt,
        "reference_coverage": n / lr,
        "symmetric_coverage": coverage,
        "proposed_rmsd_kernel_2A": geometry,
        "proposed_B": base,
        "F": None,
        "E": None,
        "E_missingness_bounds_given_reported_numbers": [0.0, base],
        "A102_nominal": None,
        "A102_missingness_bounds_given_reported_numbers": [0.0, base],
        "A102_measurement_bounds": None,
        "derived_squared_distance_sum_from_rounded_rmsd_A2": n * rmsd**2 if atom == "C_alpha" else None,
    }
    published.append(row)
    checked(name + " valid count/length relationships", 0 <= n <= min(lt, lr))
    checked(name + " bounded coverage/kernel/product", all(0 <= x <= 1 for x in [coverage, geometry, base]))
    checked(name + " product cannot exceed extent", base <= coverage)
    checked(name + " raw and derived values distinguished", row["rmsd_angstrom"] == rmsd and row["F"] is None)
    checked(name + " no invented interval or replication", row["A102_measurement_bounds"] is None and row["independent_replication_count"] is None)

checked("AF fraction exactly agrees with 836/1575", near(published[0]["proposed_B"], float(Fraction(836, 1575))))
checked("AF unknown atom selection prevents squared-distance-sum claim", published[0]["derived_squared_distance_sum_from_rounded_rmsd_A2"] is None)
checked("MJ1 corrected decimal", round(published[1]["proposed_B"], 10) == 0.0877084157)
checked("MJ2 corrected decimal", round(published[2]["proposed_B"], 10) == 0.0631593574)
checked("MJ1 rounded C-alpha implied sum", near(published[1]["derived_squared_distance_sum_from_rounded_rmsd_A2"], 554.04))
checked("MJ2 rounded C-alpha implied sum", near(published[2]["derived_squared_distance_sum_from_rounded_rmsd_A2"], 720.75))
checked("Angstrom versus nm unit conversion leaves dimensionless kernel unchanged", near(k(1.5, 2.0), k(0.15, 0.2)))
checked("half-response scales have stated meanings", k(2, 2) == 0.5 and k(1, 1) == 0.5)

# All following molecular objects, coordinates, relationships and scores are
# synthetic arithmetic inputs. They are not physical structural models.
target_anchors = [[10.0, 0, 0], [20.0, 0, 0], [30.0, 0, 0], [40.0, 0, 0]]
support_anchors = [[10.0, 0, 0], [20.0, -1, 0], [30.0, -1, 0], [40.0, -2, 0]]
opponent_anchors = [[10.0, -1, 0], [20.0, -2, 0], [30.0, -2, 0], [40.0, -3, 0]]
support_distances = [math.dist(x, y) for x, y in zip(target_anchors, support_anchors)]
opponent_distances = [math.dist(x, y) for x, y in zip(target_anchors, opponent_anchors)]
checked("declared synthetic anchor coordinates reproduce support distances", support_distances == [0, 1, 1, 2])
checked("declared synthetic anchor coordinates reproduce opponent distances", opponent_distances == [1, 2, 2, 3])
support_map = [[i, i] for i in range(1, 91)]
opponent_map = [[i, i] for i in range(1, 81)]
checked("synthetic maps have unique expected pairs", len(support_map) == len(set(map(tuple, support_map))) == 90 and len(opponent_map) == len(set(map(tuple, opponent_map))) == 80)

B_s = float(Fraction(9, 10) * Fraction(4, 5))
B_o = float(Fraction(4, 5) * Fraction(1, 2))
F_s = sum(k(d, 1) for d in support_distances) / 4
F_o = sum(k(d, 1) for d in opponent_distances) / 4
E_s, E_o = B_s * F_s, B_o * F_o
margin = max(0, E_s - E_o)
checked("synthetic global products", near(B_s, .72) and near(B_o, .4))
checked("synthetic feature means", near(F_s, .55) and near(F_o, .25))
checked("synthetic constrained products", near(E_s, .396) and near(E_o, .1))
checked("synthetic exact margin 37/125", near(margin, float(Fraction(37, 125))))
checked("duplicate reference representation gives no gain", near(max(E_s, E_s) - E_o, margin))
checked("weaker additional supporting reference gives no count bonus", near(max(E_s, .3) - E_o, margin))
checked("stronger incompatible comparison gives zero margin while retaining evidence", max(0, E_s - .5) == 0 and E_s > 0)
checked("same-comparison variants retained as range not optimistic max", [min(E_s, .3), max(E_s, .3)] == [.3, E_s])

F_missing = [2 / 4, 3 / 4]
E_missing = [B_s * x for x in F_missing]
A_missing = [max(0, x - E_o) for x in E_missing]
checked("unresolved feature interval", all(near(a, b) for a, b in zip(A_missing, [.26, .44])))
A_absent = max(0, B_s * (2 / 4) - E_o)
checked("established absent feature differs from missing feature", near(A_absent, .26) and A_missing[1] > A_absent)
checked("original complete example lies inside missingness bounds", A_missing[0] <= margin <= A_missing[1])

u = .2  # Synthetic HARD bound on the RMSD and each feature distance.
B_s_bounds = [.9 * k(1 + u, 2), .9 * k(max(0, 1 - u), 2)]
B_o_bounds = [.8 * k(2 + u, 2), .8 * k(max(0, 2 - u), 2)]
F_s_bounds = [sum(k(d + u, 1) for d in support_distances) / 4,
              sum(k(max(0, d - u), 1) for d in support_distances) / 4]
F_o_bounds = [sum(k(d + u, 1) for d in opponent_distances) / 4,
              sum(k(max(0, d - u), 1) for d in opponent_distances) / 4]
E_s_bounds = [B_s_bounds[j] * F_s_bounds[j] for j in (0, 1)]
E_o_bounds = [B_o_bounds[j] * F_o_bounds[j] for j in (0, 1)]
A_bounds = [max(0, E_s_bounds[0] - E_o_bounds[1]),
            max(0, E_s_bounds[1] - E_o_bounds[0])]
checked("synthetic uncertainty contains nominal margin", 0 <= A_bounds[0] <= margin <= A_bounds[1] <= 1)
checked("global and site hard bounds contain nominal values", all(low <= val <= high for (low, high), val in [(B_s_bounds,B_s),(B_o_bounds,B_o),(F_s_bounds,F_s),(F_o_bounds,F_o),(E_s_bounds,E_s),(E_o_bounds,E_o)]))

# Native-TM-formula illustration at zero matched distances. No alignment run.
tm_t, tm_r = 100 / 100, 100 / 200
tm_base = min(tm_t, tm_r)
incorrect_double_normalization = tm_base * (2 * 100 / (100 + 200))
checked("two-length TM illustration", tm_base == .5 and near(incorrect_double_normalization, 1/3))
checked("one missing reverse TM gives descriptor bound [0, known TM]", min(.7, 0) == 0 and min(.7, 1) == .7)

distance_a, distance_b = [2, 2], [0, math.sqrt(8)]
r_a = math.sqrt(sum(x*x for x in distance_a)/2)
r_b = math.sqrt(sum(x*x for x in distance_b)/2)
kernel_a = sum(k(x,2) for x in distance_a)/2
kernel_b = sum(k(x,2) for x in distance_b)/2
checked("same aggregate RMSD for different distance distributions", near(r_a,2) and near(r_b,2))
checked("same RMSD does not fix mean kernel", near(kernel_a,.5) and near(kernel_b,2/3) and not near(kernel_a,kernel_b))

examples = {
    "status":"fixed_example_arithmetic_not_a_production_reader_or_scorer",
    "published_rows":published,
    "synthetic_complete":{
        "origin":"synthetic_not_a_real_protein_or_run",
        "scopes":{"target_length":100,"support_reference_length":100,"opposing_reference_length":100},
        "profile":"RMSD_2A_with_feature_1A",
        "native_style_reported_inputs":{"support":{"n_pairs":90,"rmsd_A":1},"opponent":{"n_pairs":80,"rmsd_A":2}},
        "native_style_report_qualification":"RMSDs are supplied synthetic summary inputs, not recomputed from the landmark-only coordinates; no full protein coordinates or optimized alignment are claimed.",
        "synthetic_residue_pair_maps":{"support":support_map,"opponent":opponent_map},
        "feature_map":[{"key":f"feature_{i+1}","target_landmark":i+1,"support_landmark":i+1,"opponent_landmark":i+1,"physical_feature_group":f"unique_anchor_{i+1}"} for i in range(4)],
        "feature_coordinate_definition":"four declared distinct hypothetical structural landmarks, in Angstrom; these are raw arithmetic inputs, not chemically validated atoms or an actual molecular model",
        "transform":{"R":[[1,0,0],[0,1,0],[0,0,1]],"t":[0,0,0]},
        "target_anchors_A":target_anchors,"support_anchors_A":support_anchors,"opponent_anchors_A":opponent_anchors,
        "support_distances_A":support_distances,"opponent_distances_A":opponent_distances,
        "K":4,"support":{"B":B_s,"F":F_s,"E":E_s},"opponent":{"B":B_o,"F":F_o,"E":E_o},
        "S":E_s,"O":E_o,"A102":margin,"A102_exact_fraction":"37/125",
        "one_support_feature_unresolved":{"F_bounds":F_missing,"E_bounds":E_missing,"A_bounds":A_missing,"A_point":None},
        "one_support_feature_established_absent":{"A":A_absent},
        "synthetic_hard_bound_0_2A":{"B_support":B_s_bounds,"B_opponent":B_o_bounds,"F_support":F_s_bounds,"F_opponent":F_o_bounds,"E_support":E_s_bounds,"E_opponent":E_o_bounds,"A102":A_bounds,"confidence_level":None},
        "TM_length_illustration":{"TM_target":tm_t,"TM_reference":tm_r,"B":tm_base,"incorrect_double_normalization":incorrect_double_normalization},
        "same_rmsd_illustration":{"rmsd_A":[r_a,r_b],"mean_kernel_at_2A":[kernel_a,kernel_b]},
    },
}
for filename, obj in [("checked_examples_001.json",examples), ("arithmetic_checks_001.json",{"passed":True,"check_count":len(checks),"checks":checks,"not_verified":["primary coordinate maps and state joins","native score recomputation","functional-feature assignment in published cases","physical realism of synthetic landmarks","probability calibration","reader/runtime implementation","user adoption or axis completion"]})]:
    with (HERE/filename).open('x') as f:
        json.dump(obj,f,indent=2)
        f.write('\n')
print(json.dumps({"passed":True,"check_count":len(checks),"synthetic_hard_bound_A102":A_bounds}))
