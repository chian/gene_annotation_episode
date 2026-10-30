"""Check this paper packet's counts/ratios only; no alignment or reader implementation."""

import json
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parent
record = json.loads((ROOT / "cells_001.json").read_text())
cells = record["cells"]
checks = []


def checked(name, condition):
    assert condition, name
    checks.append(name)


def v(name):
    return cells[name]["value"]


expected_positions = [84, 92, 125, 217, 219, 253, 255, 328, 331]
differences = record["differences"]
checked("Nine unique source-displayed positions", [d["target_position"] for d in differences] == expected_positions)
checked("One-to-one source-displayed coordinate mapping", all(d["target_position"] == d["reference_position"] for d in differences))
checked("All source-displayed substitutions differ", all(d["target_residue"] != d["reference_residue"] for d in differences))
checked("No causal residue roles inserted", all(d["functional_role"] is None for d in differences))
checked("Reported full protein count reconciles", v("aa_identity_count") + v("aa_mismatch_count") == v("aa_aligned_pairs") == 475)
checked("Displayed mismatches reconcile with paper count", len(differences) == v("aa_mismatch_count") == 9)
checked("Coverage uses whole published proteins", v("target_length") == v("reference_length") == v("aa_aligned_pairs"))

block_results = []
for start, end in [(i, min(i + 49, 475)) for i in range(1, 476, 50)]:
    n = end - start + 1
    m = sum(start <= d["target_position"] <= end for d in differences)
    i = n - m
    block_results.append({"start": start, "end": end, "compared_pairs": n, "mismatches": m, "identities": i, "identity_fraction_exact": str(Fraction(i, n))})

checked("Block pairs sum without overlap", sum(b["compared_pairs"] for b in block_results) == 475)
checked("Block identity count sum", sum(b["identities"] for b in block_results) == 466)
checked("Block mismatch count sum", sum(b["mismatches"] for b in block_results) == 9)
weighted_block_identity = sum((Fraction(b["compared_pairs"], 475) * Fraction(b["identities"], b["compared_pairs"]) for b in block_results), Fraction(0))
checked("Length-weighted block identity equals whole comparison", weighted_block_identity == Fraction(466, 475))

exact_results = {}
for key, numerator, denominator in [
    ("aa_identity_fraction", 466, 475),
    ("aa_mismatch_fraction", 9, 475),
    ("target_coverage", 475, 475),
    ("reference_coverage", 475, 475),
    ("nt_identity_fraction_conditional", 1416, 1425),
    ("nt_mismatch_fraction_conditional", 9, 1425),
    ("reported_nonsynonymous_difference_fraction", 9, 9),
    ("identical_target_fraction_proposed", 466, 475),
]:
    expected = Fraction(numerator, denominator)
    c = cells[key]
    checked(key + " operands", (c["numerator"], c["denominator"]) == (numerator, denominator))
    checked(key + " decimal", abs(c["value"] - float(expected)) < 1e-14)
    exact_results[key] = {"numerator": numerator, "denominator": denominator, "exact": str(expected), "decimal": float(expected)}

checked("Identity and mismatch partition the protein pairs", Fraction(466, 475) + Fraction(9, 475) == 1)
checked("Identity-times-extent transformation equals identical positions per target", Fraction(466, 475) * Fraction(475, 475) == Fraction(466, 475))
checked("Conditional sense-coding length arithmetic", 3 * 475 == v("nt_orf_length") == 1425)
checked("Conditional nucleotide count arithmetic", v("nt_identity_count_conditional") == 1425 - 9 == 1416)
checked("Source rounded percentages preserved independently", v("aa_identity_percent_reported") == 98 and v("nt_identity_percent_reported") == 99)
checked("Protein count rounds consistently to source percent", round(100 * Fraction(466, 475)) == 98)
checked("Conditional nucleotide count rounds consistently to source percent", round(100 * Fraction(1416, 1425)) == 99)

required_fields = {"value", "status", "unit", "numerator", "denominator", "formula_id", "input_cell_ids", "region_id", "source_ids", "uncertainty_status", "missing_reason"}
statuses = {"reported", "figure_read", "derived", "conditional_derived", "proposed_derived", "missing"}
for key, c in cells.items():
    checked(key + " cell fields", set(c) == required_fields)
    checked(key + " declared status", c["status"] in statuses)
    checked(key + " source location", len(c["source_ids"]) > 0 and all(s in record["source_locations"] for s in c["source_ids"]))
    checked(key + " references", all(x in cells for x in c["input_cell_ids"]))
    if c["status"] == "missing":
        checked(key + " stays missing", c["value"] is None and c["numerator"] is None and c["denominator"] is None and c["missing_reason"] is not None)
    else:
        checked(key + " numerical value", isinstance(c["value"], (int, float)) and not isinstance(c["value"], bool))
        checked(key + " no missing reason", c["missing_reason"] is None)
    if c["unit"] == "fraction" and c["value"] is not None:
        checked(key + " bounded ratio with positive denominator", 0 <= c["value"] <= 1 and c["denominator"] > 0)

checked("No native-score imputation", all(v(k) is None for k in ["alignment_score", "bitscore", "evalue", "profile_score"]))
checked("No domain/site denominator invented", all(v(k) is None for k in ["domain_identity_fraction", "domain_target_coverage", "required_site_count", "required_site_identity_fraction", "required_site_coverage"]))
checked("Single comparison dependence group", record["dependence_group"] == "PMC95154_TriA_AtzA_published_sequence_pair")
checked("No new scientific execution claimed", record["alignment_executed"] is False and record["scientific_episode_executed"] is False)

result = {
    "status": "passed",
    "scope": "Arithmetic and declared cell consistency only; no source-independent biological validation, alignment, production reader or annotation-credit test.",
    "checked_assertion_count": len(checks),
    "checks": checks,
    "exact_results": exact_results,
    "disjoint_display_blocks": block_results,
    "native_score_imputation": False,
    "overall_axis_aggregation": None,
}
output = ROOT / "arithmetic_checked_001.json"
if output.exists():
    raise FileExistsError("Preserve the original check receipt; use a new version for another run.")
output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": "passed", "checks": len(checks), "output": str(output)}))
