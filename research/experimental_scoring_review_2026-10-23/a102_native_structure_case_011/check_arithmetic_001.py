"""Research arithmetic/field checks only; no scientific computation or scorer."""
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
PACKET = BASE / "af2372_components_001.json"
p = json.loads(PACKET.read_text())
checks = []


def check(name, condition):
    checks.append({"check": name, "passed": bool(condition)})


def near(number, expected, tolerance=1e-12):
    return abs(number - float(expected)) <= tolerance


native = p["native_comparisons"][0]
components = p["derived_components"]
check("native reported pair retained", native["value_angstrom"] == 1.5 and native["superposed_residue_pairs"] == 209)
for side in ("target", "reference"):
    length = p["comparison_subjects"][side]["paper_reported_monomer_length_residues"]
    check(f"{side} explicit reported denominator retained", length == 252)
    row = components[f"{side}_reported_length_coverage"]
    check(f"{side} fraction arithmetic", near(row["value"], Fraction(row["numerator"], row["denominator"])))
    check(f"{side} coverage operands match native pair", row["numerator"] == 209 and row["denominator"] == length)
    check(f"{side} residue count relationship", 0 <= native["superposed_residue_pairs"] <= length)
symmetric = components["symmetric_reported_length_coverage"]
check("symmetric coverage numerator and denominator", symmetric["numerator"] == 418 and symmetric["denominator"] == 504)
check("symmetric coverage arithmetic", near(symmetric["value"], Fraction(418, 504)))
check("unmatched count arithmetic", components["residues_outside_reported_superposition_per_protein"]["value"] == 252 - 209)

helix = p["local_architecture"]["second_n_terminal_helix"]
for side in ("target", "reference"):
    first, last = helix[f"{side}_residue_interval_inclusive"]
    check(f"{side} inclusive helix span", helix[f"{side}_span_residues"] == last - first + 1)
check("helix span difference", helix["length_difference_residues"] == 15 - 10)
check("helix length ratio", near(helix["shorter_to_longer_length_ratio"], Fraction(2, 3)))
loop = p["local_architecture"]["AF2372_mobile_catalytic_loop"]
check("mobile loop inclusive span", loop["span_residues"] == 43 - 32 + 1)

for row in p["structure_quality"]["rows"]:
    gap = Decimal(str(row["r_free_all_reflections"])) - Decimal(str(row["r_work_all_reflections"]))
    check(f"{row['structure_label']} all-reflection R gap", gap == Decimal(str(row["derived_r_free_minus_r_work"])))
    check(f"{row['structure_label']} quality is not assigned to unknown pair", row["selected_for_interprotein_comparison"] is None)

proposed = p["proposed_component_combination"]
expected_products = {1: Fraction(209, 819), 2: Fraction(836, 1575), 3: Fraction(209, 315)}
for row in proposed["sensitivity_examples"]:
    d = row["distance_scale_angstrom"]
    kernel = Fraction(1) / (1 + (Fraction(3, 2) / d) ** 2)
    product = Fraction(209, 252) * kernel
    check(f"illustrative scale {d} kernel", near(row["rmsd_kernel"], kernel) and Fraction(row["rmsd_kernel_exact"]) == kernel)
    check(f"illustrative scale {d} product", near(row["coverage_times_kernel"], product) and Fraction(row["coverage_times_kernel_exact"]) == product == expected_products[d])
    check(f"illustrative scale {d} labelled", row["scale_status"] == "illustrative_not_paper_measurement_or_adopted_parameter")
check("no adopted scale", proposed["adopted_distance_scale_angstrom"] is None)
check("no TM-score substitution", proposed["not_a_TM_score"] and components["native_tm_score"] is None)
check("no overall adopted A102 score", not p["overall_axis_aggregation_adopted"] and proposed["not_an_adopted_A102_score"] and not p["axis_sheet_complete"])
check("no active target credit implied", p["current_target_credit"] is None)
check("no fabricated pair uncertainty", native["uncertainty"]["standard_error_angstrom"] is None and native["uncertainty"]["confidence_interval_angstrom"] is None)
check("unknown atomic denominator retained", native["number_of_atomic_points_in_rmsd_denominator"] is None and native["point_atom_selection"] is None and components["summed_squared_point_distances_angstrom_squared"] is None)
check("no global-to-local substitution", components["local_functional_site_rmsd_angstrom"] is None and components["local_functional_site_coverage_fraction"] is None)
check("no matched-count independence claim", p["dependence_policy"]["independent_replication_count"] is None)
check("no unrecovered image inspection claimed", not p["source"]["table_v_image_visually_inspected"])

source_ids = {row["id"] for row in p["source_trace"]}


def inspect_refs(obj):
    if isinstance(obj, dict):
        if "source_refs" in obj:
            check("declared source references resolve", all(ref in source_ids for ref in obj["source_refs"]))
        for value in obj.values():
            inspect_refs(value)
    elif isinstance(obj, list):
        for value in obj:
            inspect_refs(value)


inspect_refs(p)
coverage = json.loads((BASE / "inspection_coverage_001.json").read_text())
check("retained extract-line coverage", coverage["all_primary_text_lines_covered"] and not coverage["missing_line_ids"])
reset = json.loads((BASE / "authority_reset_001.json").read_text())
check("post-paper reset is recorded", reset["occurred_after_primary_and_before_scoring_conversion"] and all(doc["coverage"] == "complete" for doc in reset["documents"]))

result = {
    "check_scope": "Arithmetic and declared numerical/unknown-field relationships only; no reread of paper evidence during this check",
    "packet_sha256": hashlib.sha256(PACKET.read_bytes()).hexdigest(),
    "passed": all(row["passed"] for row in checks),
    "checks": checks,
    "not_verified": ["Table V image", "exact structure and chain operands", "coordinate or residue mappings", "native RMSD recomputation", "functional transfer", "calibrated reliability or overall A102 policy"],
}
with (BASE / "arithmetic_check_001.json").open("x") as handle:
    json.dump(result, handle, indent=2)
    handle.write("\n")
print("Arithmetic and field relationship checks: " + ("PASS" if result["passed"] else "FAIL"))
if not result["passed"]:
    print("Failed checks:", [row["check"] for row in checks if not row["passed"]])
    raise SystemExit(1)
