"""Independent research arithmetic; no production imports or modifications."""
from pathlib import Path
import csv
import hashlib
import json
import math
from collections import defaultdict

import numpy as np
from scipy.stats import norm, t as student_t

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "a107_partner_sheet_014"
checks = []


def check(name, condition):
    if not bool(condition):
        raise AssertionError(name)
    checks.append(name)


def close(name, actual, expected, tolerance=1e-11):
    check(name, np.allclose(actual, expected, rtol=tolerance, atol=tolerance))


def read_csv(name):
    with (SOURCE / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


def residuals(values, growth):
    design = np.column_stack([np.ones(len(growth)), growth])
    return values - design @ np.linalg.lstsq(design, values, rcond=None)[0]


def adjusted_r(x, y, growth):
    ex, ey = residuals(x, growth), residuals(y, growth)
    return float(ex @ ey / math.sqrt(float(ex @ ex) * float(ey @ ey)))


retrieval = json.loads((SOURCE / "PRECISE_RETRIEVAL.json").read_text())
input_hashes = {}
for record in retrieval["files"]:
    path = SOURCE / Path(record["path"]).name
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    check(f"retained input hash: {path.name}", digest == record["sha256"])
    check(f"retained input bytes: {path.name}", len(payload) == record["bytes"])
    input_hashes[path.name] = digest

selection = {
    "Project ID": "ica",
    "Strain Description": "Escherichia coli K-12 MG1655",
    "Evolved Sample": "No",
    "Base Media": "M9",
    "Temperature (C)": "37",
    "pH": "7",
    "Culture Type": "Batch",
}
metadata = read_csv("precise_data_metadata.csv")
selected = [row for row in metadata if all(row[k] == v for k, v in selection.items())]
check("28 selected sample records", len(selected) == 28)
sample_ids = [row["Sample ID"] for row in selected]
check("sample IDs are unique", len(sample_ids) == len(set(sample_ids)))
check("selected rows use GSE122295", {row["GEO"] for row in selected} == {"GSE122295"})
groups = defaultdict(list)
for row in selected:
    groups[row["Condition ID"]].append(row)
check("12 condition units", len(groups) == 12)
check("glucose has six samples; all other conditions two", sorted(map(len, groups.values())) == [2] * 11 + [6])

genes = {"yfgM": "b2513", "ppiD": "b0441", "secY": "b3300", "secE": "b3981", "secG": "b3175", "nlpI": "b3163", "mepS": "b2175", "mepM": "b1856", "dacB": "b3182", "pbpG": "b2134", "mrcA": "b3396", "lpoA": "b3147"}
features = {row[""]: row for row in read_csv("precise_data_gene_info.csv")}
for gene, locus in genes.items():
    check(f"feature identity: {gene}", features[locus]["gene_name"] == gene)
    check(f"feature coordinates: {gene}", int(features[locus]["stop"]) > int(features[locus]["start"]) >= 0)

matrix = {}
with (SOURCE / "precise_data_log_tpm_full.csv").open(newline="") as stream:
    for row in csv.DictReader(stream):
        if row[""] in genes.values():
            matrix[row[""]] = {sample: float(row[sample]) for sample in sample_ids}
check("all requested gene rows retained", set(matrix) == set(genes.values()))

condition_ids = sorted(groups)
growth = np.array([np.mean([float(row["Growth Rate (1/hr)"]) for row in groups[c]]) for c in condition_ids])
means = {gene: np.array([np.mean([matrix[locus][row["Sample ID"]] for row in groups[c]]) for c in condition_ids]) for gene, locus in genes.items()}
prior_conditions = {row["condition_id"]: row for row in read_csv("PRECISE_CONDITION_INPUTS_001.csv")}
for i, condition in enumerate(condition_ids):
    previous = prior_conditions[condition]
    check(f"condition membership: {condition}", set(previous["sample_ids"].split("|")) == {row["Sample ID"] for row in groups[condition]})
    close(f"condition growth mean: {condition}", growth[i], float(previous["growth_rate_per_hr"]))
    for gene in genes:
        close(f"condition expression mean: {condition}/{gene}", means[gene][i], float(previous[gene]))

worker = json.loads((SOURCE / "CHECKED_NUMERICAL_CELLS_001.json").read_text())
previous_relations = {(row["target"], row["partner"]): row for row in worker["relations"]}
relations = [("yfgM", gene) for gene in ("ppiD", "secY", "secE", "secG")] + [("nlpI", gene) for gene in ("mepS", "mepM", "dacB", "pbpG", "mrcA", "lpoA")]
results = {}
critical = float(norm.ppf(1 - .05 / (2 * len(relations))))
for target, partner in relations:
    x, y = means[target], means[partner]
    ex, ey = residuals(x, growth), residuals(y, growth)
    coefficient = adjusted_r(x, y, growth)
    raw_r = float(np.corrcoef(x, y)[0, 1])
    df = len(x) - 1 - 2
    statistic = coefficient * math.sqrt(df / (1 - coefficient**2))
    probability = float(2 * student_t.sf(abs(statistic), df))
    se = 1 / math.sqrt(len(x) - 1 - 3)
    family = np.tanh(np.arctanh(coefficient) + np.array([-1, 1]) * critical * se)
    ordinary = np.tanh(np.arctanh(coefficient) + np.array([-1, 1]) * norm.ppf(.975) * se)
    counts = {str(threshold): int(np.sum((x >= math.log2(threshold + 1)) & (y >= math.log2(threshold + 1)))) for threshold in (1, 5, 10)}
    fraction = counts["1"] / len(x)
    expression = fraction * max(0., coefficient)**2
    point = .5 + .5 * expression
    edge_interval = [.5 + .5 * fraction * max(0., float(end))**2 for end in family]
    leave_out = [adjusted_r(np.delete(x, i), np.delete(y, i), np.delete(growth, i)) for i in range(len(x))]
    row = {
        "target": target, "partner": partner,
        "raw_pearson_r": raw_r, "partial_r": coefficient,
        "residual_dot_product": float(ex @ ey), "residual_ss_target": float(ex @ ex), "residual_ss_partner": float(ey @ ey),
        "n_conditions": len(x), "n_sample_records": len(selected), "df": df,
        "p_two_sided": probability, "ordinary_r_ci95": ordinary.tolist(), "family_r_ci95": family.tolist(),
        "codetection_by_TPM_threshold": counts,
        "expression_component": expression, "partner_point": point, "partner_family_interval": edge_interval,
        "leave_one_condition_out_r_range": [min(leave_out), max(leave_out)],
    }
    old = previous_relations[(target, partner)]
    for new_key, old_key in [("raw_pearson_r", "raw_pearson_r"), ("partial_r", "partial_r"), ("p_two_sided", "p_two_sided"), ("residual_dot_product", "residual_dot_product"), ("residual_ss_target", "residual_ss_target"), ("residual_ss_partner", "residual_ss_partner"), ("ordinary_r_ci95", "fisher_ci95"), ("family_r_ci95", "fisher_family_ci95"), ("partner_point", "edge_point"), ("partner_family_interval", "edge_family_interval"), ("leave_one_condition_out_r_range", "leave_one_condition_out_partial_r_range")]:
        close(f"independent relation calculation: {target}/{partner}/{new_key}", row[new_key], old[old_key])
    check(f"co-detection thresholds: {target}/{partner}", counts == old["codetection_count_by_tpm_threshold"])
    results[f"{target}:{partner}"] = row

candidate_definitions = {
    "yfgM_ppiD_secYEG_hypothesis": ("yfgM", [["ppiD", "secY", "secE", "secG"]]),
    "nlpI_mepS_pbp4_or_pbp7_hypothesis": ("nlpI", [["mepS", "dacB"], ["mepS", "pbpG"]]),
    "nlpI_pbp1a_lpoa_pbp4_hypothesis": ("nlpI", [["mrcA", "lpoA", "dacB"]]),
}
candidates = {}
for name, (target, clauses) in candidate_definitions.items():
    point = max(min(results[f"{target}:{partner}"]["partner_point"] for partner in clause) for clause in clauses)
    interval = [max(min(results[f"{target}:{partner}"]["partner_family_interval"][end] for partner in clause) for clause in clauses) for end in (0, 1)]
    close(f"candidate point: {name}", point, worker["candidate_coordinates"][name]["point"])
    close(f"candidate interval: {name}", interval, worker["candidate_coordinates"][name]["family_interval"])
    candidates[name] = {"point": point, "conditional_family_interval": interval}

# Counterexample: the observed correlation cannot be linearly blended by coverage.
observed_n, total_n = 16, 20
observed_g = np.arange(1, observed_n + 1, dtype=float) / 10
angles = np.arange(observed_n, dtype=float) * (2 * np.pi / observed_n)
x = residuals(np.sin(angles), observed_g)
x *= 4 / np.linalg.norm(x)
v = residuals(np.cos(angles), observed_g)
v -= x * (x @ v) / (x @ x)
v *= 4 / np.linalg.norm(v)
y = .6 * x + .8 * v
observed_x, observed_y = 10 + x, 10 + y
missing_offsets = np.array([7., -7., -7., 7.])
full_x = np.r_[observed_x, 10 + missing_offsets]
full_y = np.r_[observed_y, 10 - missing_offsets]
full_g = np.arange(1, total_n + 1, dtype=float) / 10
observed_r = adjusted_r(observed_x, observed_y, observed_g)
full_r = adjusted_r(full_x, full_y, full_g)
close("counterexample observed r", observed_r, .6)
close("counterexample completed r", full_r, -186.4 / 212)
check("counterexample values are valid nonnegative log-expression and co-detected", min(full_x.min(), full_y.min()) >= 1)
H0, G, coverage = .9, .75, observed_n / total_n
old_expression = [H0 * (coverage * observed_r**2 + (1 - coverage) * endpoint) for endpoint in (0, 1)]
old_partner = [G * (.5 + .5 * endpoint) for endpoint in old_expression]
full_expression = H0 * max(0., full_r)**2
full_partner = G * (.5 + .5 * full_expression)
corrected_expression = [0., H0 * 1.]
corrected_partner = [G * (.5 + .5 * endpoint) for endpoint in corrected_expression]
close("counterexample old bounds", old_partner, [.4722, .5397])
close("counterexample completed partner", full_partner, .375)
close("counterexample corrected outer bounds", corrected_partner, [.375, .7125])
check("old missing-input interval is invalid", full_partner < old_partner[0])
check("corrected interval includes completion", corrected_partner[0] <= full_partner <= corrected_partner[1])
check("draft D=.8 cannot be a count fraction with 16 conditions", not float(.8 * 16).is_integer())

counterexample = {
    "origin": "synthetic_counterexample_not_biological_measurement",
    "growth": full_g.tolist(), "target_log2_TPM_plus_1": full_x.tolist(), "partner_log2_TPM_plus_1": full_y.tolist(),
    "observed_indices": list(range(observed_n)), "unobserved_indices": list(range(observed_n, total_n)),
    "observed_partial_r": observed_r, "completed_partial_r": full_r,
    "old_invalid_partner_interval": old_partner, "completed_partner_point": full_partner,
    "corrected_outer_partner_interval": corrected_partner,
}
output = {
    "scope": "independent arithmetic on retained processed public data and an explicitly synthetic missing-condition counterexample",
    "no_new_primary_paper_inspection": True,
    "source_commit": retrieval["commit"], "input_hashes": input_hashes,
    "selection": selection, "sample_ids": sample_ids, "condition_ids": condition_ids,
    "native_relations": list(results.values()), "native_candidates": candidates,
    "missing_condition_counterexample": counterexample,
    "assertions_passed": len(checks), "checks": checks,
}
with (HERE / "parent_arithmetic_001.json").open("x") as stream:
    json.dump(output, stream, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps({"assertions_passed": len(checks), "native_candidates": candidates, "missing_condition_counterexample": {k: v for k, v in counterexample.items() if not isinstance(v, list) or "interval" in k}}, indent=2))
