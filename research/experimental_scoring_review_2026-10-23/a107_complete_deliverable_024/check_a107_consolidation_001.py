"""Bounded A107 research joins, not a production reader or source reanalysis.

Reads the parent's verified numerical receipt and the existing 20-row synthetic
matrix. Does not reopen papers, rehash/reparse the large public dataset, invoke
an aligner, or overwrite a prior record. Outputs are created exclusively.
"""
from pathlib import Path
from statistics import NormalDist
import csv
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OLD = ROOT / "a107_partner_sheet_014"
PARENT = ROOT / "a107_sheet_construction_001"
checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def close(name, actual, expected, tolerance=1e-11):
    if isinstance(actual, (list, tuple)):
        condition = len(actual) == len(expected) and all(
            math.isclose(a, b, abs_tol=tolerance, rel_tol=tolerance)
            for a, b in zip(actual, expected)
        )
    else:
        condition = math.isclose(actual, expected, abs_tol=tolerance, rel_tol=tolerance)
    check(name, condition)


def positive_square(r):
    return max(0.0, r) ** 2


def residual(values, growth):
    count = len(values)
    xm, gm = sum(values) / count, sum(growth) / count
    centered_g = [g - gm for g in growth]
    gg = sum(g * g for g in centered_g)
    beta = sum(g * (x - xm) for g, x in zip(centered_g, values)) / gg if gg else 0.0
    return [x - xm - beta * g for x, g in zip(values, centered_g)]


def correlation(x, y, growth):
    ex, ey = residual(x, growth), residual(y, growth)
    return sum(a * b for a, b in zip(ex, ey)) / math.sqrt(
        sum(a * a for a in ex) * sum(b * b for b in ey)
    )


def norm_score(pair, self_q, self_r):
    assert self_q > 0 and self_r > 0
    return min(1.0, max(0.0, pair / math.sqrt(self_q * self_r)))


def edge(G, H0, D, r):
    E = H0 * D * positive_square(r)
    return {"G": G, "H0": H0, "D_full": D, "r_full": r,
            "R_full": positive_square(r), "E_full": E,
            "s": G * (0.5 + 0.5 * E)}


def candidate(edges, clauses):
    return max(min(edges[j] for j in clause) for clause in clauses)


def outer_missing(G, H0, observed_count, q_pair, m):
    assert all(isinstance(i, int) for i in (observed_count, q_pair, m))
    assert m > 0 and 0 <= observed_count <= q_pair <= m
    d = [observed_count / m, (observed_count + m - q_pair) / m]
    e = [0.0, H0 * d[1]]
    s = [G * (0.5 + 0.5 * v) for v in e]
    return {"D_full": {"point": d[0] if d[0] == d[1] else None, "range": d},
            "r_full": {"point": None, "range": [-1.0, 1.0]},
            "E_full": {"point": 0.0 if e[1] == 0 else None, "range": e},
            "s": {"point": s[0] if s[0] == s[1] else None, "range": s}}


parent = json.loads((PARENT / "parent_arithmetic_001.json").read_text())
old = json.loads((OLD / "CHECKED_NUMERICAL_CELLS_001.json").read_text())
check("retained parent receipt describes 28 samples and 12 conditions",
      len(parent["sample_ids"]) == 28 and len(parent["condition_ids"]) == 12)
check("ten retained relation rows", len(parent["native_relations"]) == 10)
native = {}
for row in parent["native_relations"]:
    key = row["target"] + ":" + row["partner"]
    close(key + " residual numerator/denominator join", row["residual_dot_product"] /
          math.sqrt(row["residual_ss_target"] * row["residual_ss_partner"]), row["partial_r"])
    count = row["codetection_by_TPM_threshold"]["1"]
    check(key + " realizable complete count", isinstance(count, int) and 0 <= count <= 12)
    result = edge(1.0, 1.0, count / 12, row["partial_r"])
    result["family_s_interval"] = [0.5 + 0.5 * count / 12 * positive_square(r)
                                   for r in row["family_r_ci95"]]
    close(key + " component join", result["s"], row["partner_point"])
    close(key + " family join", result["family_s_interval"], row["partner_family_interval"])
    native[key] = result

definitions = {
    "yfgM_ppiD_secYEG_hypothesis": [["yfgM:ppiD", "yfgM:secY", "yfgM:secE", "yfgM:secG"]],
    "nlpI_mepS_pbp4_or_pbp7_hypothesis": [["nlpI:mepS", "nlpI:dacB"], ["nlpI:mepS", "nlpI:pbpG"]],
    "nlpI_pbp1a_lpoa_pbp4_hypothesis": [["nlpI:mrcA", "nlpI:lpoA", "nlpI:dacB"]],
}
native_candidates = {}
for name, clauses in definitions.items():
    point = candidate({k: v["s"] for k, v in native.items()}, clauses)
    interval = [candidate({k: v["family_s_interval"][i] for k, v in native.items()}, clauses)
                for i in (0, 1)]
    close(name + " complete candidate join", point, parent["native_candidates"][name]["point"])
    close(name + " complete interval join", interval,
          parent["native_candidates"][name]["conditional_family_interval"])
    native_candidates[name] = {"clauses": clauses, "point": point, "conditional_family_interval": interval}

with (OLD / "SYNTHETIC_EXPRESSION_INPUTS_001.csv").open(newline="") as stream:
    samples = list(csv.DictReader(stream))
check("synthetic complete fixed roster has 20 unique conditions",
      len(samples) == len({s["condition_id"] for s in samples}) == 20)
x = [float(s["target"]) for s in samples]
growth = [float(s["growth_rate_per_hr"]) for s in samples]
H0 = norm_score(180, 200, 200)
synthetic = {}
critical = NormalDist().inv_cdf(1 - 0.05 / 6)
for partner, scores, expected_r, expected_count in [
    ("P", [160, 200, 200], .8, 18), ("Q", [135, 180, 180], .6, 16),
    ("R", [180, 200, 200], -.4, 20), ("O_optional", [190, 200, 200], .95, 20)
]:
    y = [float(s[partner]) for s in samples]
    r = correlation(x, y, growth)
    count = sum(a >= 1 and b >= 1 for a, b in zip(x, y))
    close(partner + " synthetic vector r", r, expected_r)
    check(partner + " synthetic integer co-detection", count == expected_count)
    check(partner + " nonnegative synthetic log expression", min(x + y) >= 0)
    row = edge(norm_score(*scores), H0, count / 20, r)
    row["raw_pair_self_self"] = scores
    row["codetection_count"] = count
    if partner != "O_optional":
        r_interval = [math.tanh(math.atanh(r) + sign * critical / 4) for sign in (-1, 1)]
        row["family_r_interval"] = r_interval
        row["family_s_interval"] = [edge(row["G"], H0, count / 20, a)["s"] for a in r_interval]
    synthetic[partner] = row
clauses = [["P", "Q"], ["P", "R"]]
points = {k: v["s"] for k, v in synthetic.items()}
synthetic_candidate = candidate(points, clauses)
synthetic_interval = [candidate({k: v["family_s_interval"][i] for k, v in synthetic.items()
                                if k != "O_optional"}, clauses) for i in (0, 1)]
close("synthetic candidate join", synthetic_candidate, .4722)
close("synthetic conditional interval join", synthetic_interval, [.45, .5744858635848281])
close("optional relation excluded", candidate({k: v for k, v in points.items() if k != "O_optional"}, clauses), synthetic_candidate)

counter = parent["missing_condition_counterexample"]
cx, cy, cg = counter["target_log2_TPM_plus_1"], counter["partner_log2_TPM_plus_1"], counter["growth"]
observed_r = correlation(cx[:16], cy[:16], cg[:16])
complete_r = correlation(cx, cy, cg)
close("counterexample observed r", observed_r, .6)
close("counterexample completed r", complete_r, -186.4 / 212)
check("counterexample realizable observed count", sum(a >= 1 and b >= 1 for a, b in zip(cx[:16], cy[:16])) == 16)
corrected = outer_missing(.75, .9, 16, 16, 20)
close("corrected missing-panel interval", corrected["s"]["range"], [.375, .7125])
check("incomplete panel retains null full-panel point", corrected["s"]["point"] is None)
actual_s = edge(.75, .9, 1.0, complete_r)["s"]
close("actual completion preserved", actual_s, .375)
invalid_old = [.75 * (.5 + .5 * .9 * (.8 * observed_r**2 + .2 * u)) for u in (0, 1)]
close("historical invalid bounds identified", invalid_old, [.4722, .5397])
check("old interval excludes completion", actual_s < invalid_old[0])
check("corrected interval includes completion", corrected["s"]["range"][0] <= actual_s <= corrected["s"]["range"][1])
check("old 0.8 of 16 is not an integer count", not float(.8 * 16).is_integer())

growth_missing = outer_missing(.75, .9, 16, 20, 20)
close("missing growth preserves paired-expression D", growth_missing["D_full"]["range"], [.8, .8])
close("missing growth partner range", growth_missing["s"]["range"], [.375, .645])
missing_growth_candidate = [candidate({**points, "Q": growth_missing["s"]["range"][i]}, clauses) for i in (0, 1)]
close("missing-growth candidate range", missing_growth_candidate, [.45, .60736])
zero_detection = outer_missing(.75, .9, 0, 20, 20)
close("known zero detection fixes expression", zero_detection["E_full"]["point"], 0.0)
close("known zero detection fixes partner despite undefined r", zero_detection["s"]["point"], .375)

genome_missing = [candidate({**points, "Q": v}, clauses) for v in (0.0, points["Q"])]
close("unknown genomic presence range", genome_missing, [.45, .4722])
close("resolved absent alternative is zero", candidate({**points, "R": 0.0}, clauses), .4722)
close("duplicate relation is idempotent", candidate(points, [["P", "P", "Q"], ["P", "R"]]), synthetic_candidate)
replication = {}
for name, r2, expected in [("weaker_positive", .4, .45184), ("contrary", -.4, .4)]:
    e2 = H0 * .9 * positive_square(r2)
    combined = min(synthetic["P"]["E_full"], e2)
    partner = .8 * (.5 + .5 * combined)
    answer = candidate({**points, "P": partner}, clauses)
    close(name + " repeated block combination", answer, expected)
    replication[name] = {"second_block_r": r2, "second_block_E": e2,
                         "combined_P_E": combined, "P_s": partner, "candidate": answer}
overlap_range = [candidate({**points, "P": v}, clauses) for v in (.45184, .60736)]
close("unresolved overlap is a range, not a new replicate", overlap_range, [.45184, .4722])

publication_arithmetic = {
    "YfgM_PpiD_reported_ratio": 99 / 100,
    "YfgM_PpiD_conditional_loading_ratio": 99 / 112,
    "YfgM_Skp_conditional_loading_ratio": 131 / 112,
    "YfgM_SurA_conditional_loading_ratio": 95 / 112,
    "YfgM_Skp_conditional_amount_similarity": 112 / 131,
    "NlpI_PBP4_synthesis_ratio": 441 / 389,
    "NlpI_MepM_synthesis_ratio": 341 / 389,
    "NlpI_MepS_synthesis_ratio": 3931 / 389,
    "NlpI_conditional_micromolar": 389 * .005,
    "PBP4_conditional_micromolar": 441 * .005,
    "MepM_conditional_micromolar": 341 * .005,
    "MepS_conditional_micromolar": 3931 * .005,
}
close("published contrast PpiD conditional arithmetic", publication_arithmetic["YfgM_PpiD_conditional_loading_ratio"], old["publication_arithmetic"]["yfgm_ppid_conditional_loading_ratio"])
close("published contrast MepM synthesis arithmetic", publication_arithmetic["NlpI_MepM_synthesis_ratio"], old["publication_arithmetic"]["nlpi_mepm_supply_assuming_one_to_one"])

output = {
    "scope": "final numerical joins and missing-condition correction only",
    "new_primary_or_paper_packet_inspection": False,
    "new_full_public_dataset_reconstruction": False,
    "source_receipt": "../a107_sheet_construction_001/parent_arithmetic_001.json",
    "native_relations": native,
    "native_candidates": native_candidates,
    "synthetic_relations": synthetic,
    "synthetic_candidate": {"clauses": clauses, "point": synthetic_candidate,
                            "conditional_family_interval": synthetic_interval},
    "corrected_missing_conditions": corrected,
    "counterexample_actual_completion": actual_s,
    "historical_invalid_bounds": invalid_old,
    "missing_growth": growth_missing,
    "missing_growth_candidate_range": missing_growth_candidate,
    "missing_genome_candidate_range": genome_missing,
    "replication_examples": replication,
    "overlap_candidate_range": overlap_range,
    "publication_arithmetic": publication_arithmetic,
    "assertions_passed": len(checks), "checks": checks,
}
with (HERE / "A107_FINAL_ARITHMETIC_001.json").open("x") as stream:
    json.dump(output, stream, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps({"assertions_passed": len(checks), "native_candidates": native_candidates,
                  "synthetic_candidate": output["synthetic_candidate"],
                  "corrected_missing_conditions": corrected,
                  "replication_examples": replication}, indent=2))
