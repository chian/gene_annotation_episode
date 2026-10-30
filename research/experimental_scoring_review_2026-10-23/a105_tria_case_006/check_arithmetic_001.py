"""Check hand-entered paper arithmetic, without extracting or scoring evidence.

Run with Python's standard library. This is a research arithmetic checker, not
an A105 reader, likelihood model, production scorer, or scientific experiment.
Reported +/- quantities have unspecified meaning and are never treated as SE.
"""

import json
import math
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "paper_inputs_001.json").read_text())
rows = data["table_1"]["rows"]
assert len(rows) == 16
assert len({r["id"] for r in rows}) == 16
positive = [r for r in rows if r["relation"] == "equal"]
censored = [r for r in rows if r["relation"] == "less_than"]
assert len(positive) == 4 and len(censored) == 12
assert data["table_1"]["screen_detection_limit_pmol_per_min_per_mg"] / 1000 == 0.01
assert all(r["value"] > 0 for r in rows)
reference = rows[0]

def ratio_sensitivity(a, b):
    """Arithmetic at printed mean +/- endpoints, NOT a statistical interval."""
    x, ux = a["value"], a["reported_halfwidth"]
    y, uy = b["value"], b["reported_halfwidth"]
    assert min(x - ux, y - uy) > 0
    lo, hi = (x - ux) / (y + uy), (x + ux) / (y - uy)
    return {"ratio_endpoint_sensitivity": [lo, hi],
            "log_ratio_endpoint_sensitivity": [math.log(lo), math.log(hi)],
            "interpretation": "printed +/- endpoint sensitivity only; not CI, SE or bound on true value"}

table_calculations = []
for r in rows:
    q = r["value"] / reference["value"]
    item = {"row": r["id"], "substrate": r["substrate"],
            "numerator": r["value"], "denominator": reference["value"],
            "rate_ratio_to_melamine": q, "log_rate_ratio_to_melamine": math.log(q),
            "relation": r["relation"],
            "statistical_uncertainty": None}
    if r["reported_halfwidth"] is not None:
        item["relative_reported_halfwidth"] = r["reported_halfwidth"] / r["value"]
    if r["id"] == reference["id"]:
        item["self_ratio_identity"] = "1 by reusing the same observation; no independent confirmation"
    elif r["relation"] == "equal":
        item.update(ratio_sensitivity(r, reference))
    table_calculations.append(item)

positive_pair_contrasts = []
for a, b in combinations(positive, 2):
    ratio = a["value"] / b["value"]
    positive_pair_contrasts.append({"numerator_row": a["id"], "denominator_row": b["id"],
                                    "difference_nmol_per_min_per_mg": a["value"] - b["value"],
                                    "ratio": ratio, "log_ratio": math.log(ratio),
                                    **ratio_sensitivity(a, b)})

specific_alternative = {"numerator_row": "T04", "denominator_row": "T06",
                        "ratio_lower_boundary": 17 / 0.01,
                        "log_ratio_lower_boundary": math.log(17 / 0.01),
                        "relation": "greater_than_for_positive_undetected_rate",
                        "denominator_is_detection_limit_not_measured_zero_or_blank": True}

competition = []
for r in data["competition"]["rows"]:
    inhibition = r["inhibition_percent"] / 100
    residual = 1 - inhibition
    halfwidth = r["reported_halfwidth_percentage_points"] / 100
    competition.append({"row": r["id"], "inhibition_fraction": inhibition,
                        "residual_rate_fraction": residual,
                        "residual_reported_halfwidth": halfwidth,
                        "log_residual_rate_fraction": math.log(residual),
                        "statistical_uncertainty": None})

competition_contrasts = []
for a, b in [(data["competition"]["rows"][0], data["competition"]["rows"][1]),
             (data["competition"]["rows"][2], data["competition"]["rows"][3]),
             (data["competition"]["rows"][4], data["competition"]["rows"][0])]:
    ia, ib = a["inhibition_percent"], b["inhibition_percent"]
    fa, fb = 1 - ia / 100, 1 - ib / 100
    competition_contrasts.append({"numerator_row": a["id"], "denominator_row": b["id"],
                                 "inhibition_difference_percentage_points": ia - ib,
                                 "inhibition_ratio": ia / ib,
                                 "log_inhibition_ratio": math.log(ia / ib),
                                 "residual_rate_fraction_ratio": fa / fb,
                                 "log_residual_rate_fraction_ratio": math.log(fa / fb),
                                 "statistical_uncertainty": None,
                                 "cross_enzyme_comparability": "unresolved" if a["subject"] != b["subject"] else "within same subject; see methods limitations"})

s = data["sequence"]
assert len(s["positions_AtzA_TriA"]) == s["amino_acid_differences"] == 9
assert all(a != b for _, a, b in s["positions_AtzA_TriA"])
assert len({p for p, _, _ in s["positions_AtzA_TriA"]}) == 9
identity = (s["aligned_span_aa"] - s["amino_acid_differences"]) / max(s["source_span_aa"], s["target_span_aa"])
sequence = {"identical_residues": 466, "compared_span_aa": 475,
            "identity_correspondence": identity,
            "nonidentity_fraction": 9 / 475,
            "nucleotide_identity": (1425 - 9) / 1425,
            "coverage_of_each_protein": 475 / 475,
            "known_function_site_fraction": None,
            "R_available_if_only_sequence_observed": identity,
            "hypothetical_five_equal_relevant_families": {
                "observed_weight_fraction": 1 / 5,
                "R_full_identification_lower": identity / 5,
                "R_full_identification_upper": (identity + 4) / 5,
                "choice_of_all_five_families_is_not_established_by_paper": True},
            "B_source": None, "C_target_conventional": None}

assert math.isclose(math.exp(positive_pair_contrasts[0]["log_ratio"]), 245 / 135)
assert sequence["R_available_if_only_sequence_observed"] < 1
assert all(c["statistical_uncertainty"] is None for c in competition)
assert data["statistical_outputs_not_identified"]["source_log_likelihood_contrast_S"] is None
assert data["sequence"]["individually_engineered_mutant_assays_in_this_paper"] == 0

out = {
    "status": "arithmetic checked; no statistical error model or annotation score fitted",
    "table1_reference_comparisons": table_calculations,
    "all_six_positive_rate_pairs": positive_pair_contrasts,
    "matched_leaving_group_comparison": specific_alternative,
    "competition_residual_rates": competition,
    "selected_competition_comparisons": competition_contrasts,
    "sequence_correspondence": sequence,
    "ammelide_control_protein_concentration_ratio": 124 / 12.4,
    "not_validated": ["source truth beyond manual primary inspection", "biological independence of samples",
                      "likelihood", "confidence interval", "function probability", "A105 compilation policy"]
}
(HERE / "arithmetic_checked_001.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"status": out["status"], "table_rows": len(rows),
                  "positive_pairs": len(positive_pair_contrasts), "competition_rows": len(competition),
                  "identity": identity, "written": "arithmetic_checked_001.json"}, indent=2))
