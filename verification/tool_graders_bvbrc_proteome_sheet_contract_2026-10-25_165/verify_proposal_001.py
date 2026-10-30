"""Independent contract-shape and literal arithmetic checks; no production code.

No GenomeComparison native output or BLAST report is invented here. One filled
sheet reuses A's existing, explicitly synthetic projection unchanged. Remaining
cases are mathematical examples, not acquired scientific measurements.
"""
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator, validators

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SCHEMA = json.loads((HERE / "DATA_SHAPES_PROPOSAL_001.json").read_text())
NATIVE_PATH = ROOT / "gene_annotation_episode/bvbrc_proteome_native_schemas.json"
NATIVE = json.loads(NATIVE_PATH.read_text())
CHECKS = []

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)

def emit(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()

def sha(data): return hashlib.sha256(data).hexdigest()
def cell(value=None, state="value", reasons=(), fields=()):
    return {"state": state, "value": value, "reason_codes": list(reasons), "source_fields": deepcopy(list(fields))}

def missing(reason="denominator_unavailable"):
    return cell(None, "missing_input", [reason])

def ratio(n, d, value=None, state="value", reasons=()):
    return {"numerator": deepcopy(n), "denominator": deepcopy(d), "fraction": cell(value, state, reasons)}

def scope(**kwargs):
    keys = ("track_key", "reference_row_ordinal", "association_key", "protein_key", "report_key", "query_ordinal", "hit_ordinal", "hsp_ordinal")
    return {k: kwargs.get(k) for k in keys}

def requirement(code, kind, **kwargs):
    return {"code": code, "scope": scope(**kwargs), "required_input": kind, "source_fields": []}

def diagnostic(code, **kwargs):
    return {"code": code, "severity": "qualification", "path": "", "scope": scope(**kwargs), "source_fields": []}

TYPES = Draft202012Validator.TYPE_CHECKER.redefine_many({
    "integer": lambda checker, value: type(value) is int,
    "number": lambda checker, value: type(value) in (int, float) and (type(value) is int or math.isfinite(value)),
})
VALIDATOR = validators.extend(Draft202012Validator, type_checker=TYPES)

def validate(name, value):
    VALIDATOR({"$schema": SCHEMA["$schema"], "$ref": "#/$defs/" + name, "$defs": SCHEMA["$defs"]}).validate(value)
    CHECKS.append("shape:" + name)

def rejects(name, value):
    v = VALIDATOR({"$schema": SCHEMA["$schema"], "$ref": "#/$defs/" + name, "$defs": SCHEMA["$defs"]})
    check("reject:" + name + ":" + str(len(CHECKS)), bool(list(v.iter_errors(value))))

Draft202012Validator.check_schema(SCHEMA)
check("draft2020_12_schema_valid", True)
check("accepted_native_schema_hash", sha(NATIVE_PATH.read_bytes()) == "c84fecffe0170b7c77948f411593a55ae63e902f976e8a42463a0053c1a1f01d")
check("all_native_definitions_unchanged", all(SCHEMA["$defs"][k] == v for k, v in NATIVE["$defs"].items()))
references = []
open_objects = []
def inspect(node, path=""):
    if isinstance(node, dict):
        if "$ref" in node:
            references.append(node["$ref"])
        if node.get("type") == "object" and node.get("additionalProperties") is not False:
            open_objects.append(path)
        for key, value in node.items(): inspect(value, path + "/" + key)
    elif isinstance(node, list):
        for i, value in enumerate(node): inspect(value, path + "/" + str(i))
inspect(SCHEMA)
check("all_object_shapes_closed", not open_objects)
check("all_references_local_and_resolved", all(r.startswith("#/$defs/") and r[8:] in SCHEMA["$defs"] for r in references))

# Literal rational arithmetic: independent of any proposed production function.
identities = [Q(7, 8), Q(0), Q(5, 8)]
endpoint_differences = [Q(99, 100), Q(1, 2), Q(3, 4)]
check("native_identity_mean_one_half", sum(identities) / 3 == Q(1, 2))
check("native_endpoint_mean_56_over_75", sum(endpoint_differences) / 3 == Q(56, 75))
check("display_percent_zero_is_zero", [100 * v for v in identities] == [Q(175, 2), Q(0), Q(125, 2)])
passing = [i for i, (a, b) in enumerate(zip(identities, endpoint_differences)) if a >= Q(3, 5) and b >= Q(7, 10)]
check("explicit_postfilter_two_of_four", passing == [0, 2] and Q(len(passing), 4) == Q(1, 2))
check("strict_postfilter_true_zero", sum(v >= Q(9, 10) for v in identities) == 0)
check("missing_identity_summary_not_zero", (identities[0] + identities[2]) / 2 == Q(3, 4))
check("native_fraction_is_not_percent", 100 * Q("0.875") == Q("87.5"))
check("alternate_decimal_lexemes_equal", Q(".875") == Q("8.750E-1"))
check("rounded_native_not_corrected_coverage", Q(".99") != Q(1))
check("bound_distinct_pairs_many_to_one", len({("R0", "S0"), ("R1", "S0"), ("R2", "S1")}) - len({"S0", "S1"}) == 1)
check("original_track_order_skips_keep_identity", ["F1", "G1", "G2", "FG1"][2] == "G2")

# Explicit residue correspondences for two hypothetical HSPs; no text report.
pairs_h1 = {(1, 1, True), (2, 2, True), (3, 3, False), (4, 4, True)}
pairs_h2 = {(3, 3, False), (4, 4, True), (5, 5, True), (6, 6, True)}
union = pairs_h1 | pairs_h2
check("overlap_eight_representations_six_pairs", len(pairs_h1) + len(pairs_h2) == 8 and len(union) == 6)
check("union_identity_five_over_six", Q(sum(v[2] for v in union), len(union)) == Q(5, 6))
check("union_query_and_subject_coverage", Q(len({v[0] for v in union}), 8) == Q(3, 4) and Q(len({v[1] for v in union}), 10) == Q(3, 5))
conflicted = union | {(3, 7, True), (4, 8, True)}
conflict_q = sorted(q for q in {v[0] for v in conflicted} if len({s for x, s, _ in conflicted if x == q}) > 1)
check("alternative_mapping_positions_explicit", conflict_q == [3, 4])
check("conflicted_union_positions_retained", Q(len({v[0] for v in conflicted}), 8) == Q(3, 4) and Q(len({v[1] for v in conflicted}), 10) == Q(4, 5))

examples = {
    "origin": "invented_mathematical_contract_examples_not_native_results",
    "scientific_program_executed": False,
    "cases": [
        {"case": "four_record_reference", "reference_occurrences": 4, "subject_occurrences": 2,
         "rows": [{"reference": "R0", "subject": "S0", "identity": .875, "subject_endpoint_difference": .990, "category": "bi (<->)"},
                  {"reference": "R1", "subject": "S0", "identity": 0, "subject_endpoint_difference": .500, "category": "uni (->)"},
                  {"reference": "R2", "subject": "S1", "identity": .625, "subject_endpoint_difference": .750, "category": "bi (<->)"}],
         "expected": {"published_count": 3, "native_bi": 2, "native_uni": 1, "identity_mean": .5,
            "endpoint_difference_mean": float(Q(56, 75)), "endpoint_difference_mean_exact": "56/75",
            "published_reference_fraction": .75, "no_published_reference_count": 1,
            "multiple_reference_subject_count": 1, "excess_bound_pair_count": 1,
            "subject_feature_occurrence_count": 2, "subject_sequence_groups_if_equal_full_sequence": 1}},
        {"case": "recalculation", "first_parameters": {"minimum_identity_fraction": .6, "minimum_subject_endpoint_difference_fraction": .7},
         "first_expected": {"pass": 2, "fail": 1, "unknown": 0, "fraction": .5},
         "second_parameters": {"minimum_identity_fraction": .9, "minimum_subject_endpoint_difference_fraction": None},
         "second_expected": {"pass": 0, "fail": 3, "unknown": 0, "fraction": 0}},
        {"case": "missing_vs_zero", "identity": None, "presence": "explicit_null", "expected_identity_percent": None,
         "expected_identity_value_count": 2, "expected_identity_mean": .75,
         "identity_minimum": .6, "endpoint_difference": .5,
         "decision_with_endpoint_minimum_point5": "unknown", "decision_with_endpoint_minimum_point7": "fail"},
        {"case": "unknown_input_completeness", "visible_reference_records": 4, "membership_complete": "unknown",
         "expected_native_mean": .5, "expected_observed_bound_reference_count": 3,
         "expected_denominator": missing("input_membership_unknown"), "expected_population_fraction": missing("denominator_unavailable"),
         "expected_no_published_count": missing("reference_membership_unresolved")},
        {"case": "skipped_tracks", "ordered_inputs": ["G1", "G2", "F1", "FG1"], "reference_index": 3,
         "expected_tracks": {"ref_genome": "F1", "comp_genome_1": "G1", "comp_genome_2": "G2", "comp_genome_3": "FG1"},
         "skipped_track": "comp_genome_1", "materialized_track": "comp_genome_2", "materialized_input": "G2"},
        {"case": "name_only_vs_blank_materialized", "name_only_observed_source_count": 0,
         "name_only_no_published": missing("track_materialization_unknown"), "name_only_fraction": missing("track_materialization_unknown"),
         "materialized_blank_count": 0, "materialized_blank_reference_denominator": 4,
         "materialized_blank_fraction": 0, "materialized_blank_no_published": 4},
        {"case": "empty_exact_input", "ratio": ratio(cell(0), cell(0), None, "zero_denominator", ["denominator_zero"])},
        {"case": "duplicate_identifiers", "supplied_fasta": ">dup\nAAAA\n>dup\nAAAA\n>u\nCCCC\n",
         "expected_occurrence_count": 3, "expected_unique_identifier_count": 2, "expected_sequence_group_count": 2,
         "native_dup_candidates": [{"inventory_key": "synthetic-reference", "record_ordinal": 0}, {"inventory_key": "synthetic-reference", "record_ordinal": 1}],
         "expected_join_state": "ambiguous", "retained_native_identity": .875, "expected_no_published": missing("row_join_ambiguous")},
        {"case": "malformed_neighbors", "native_identity_values": [.875, None, .625], "middle_presence": "invalid",
         "expected_value_count": 2, "expected_invalid_count": 1, "expected_mean": .75,
         "wrong_width_tsv_middle_state": "uncertain_table_layout", "invalid_json_length_does_not_erase_identity": True},
        {"case": "alternate_representations", "primary_association_count": 3, "alternate_association_count": 3,
         "expected_scientific_observation_count": 3, "primary_identity": .875, "equal_alternate_lexeme": "8.750E-1",
         "conflicting_alternate_identity": .9, "expected_conflict_state": "conflicting", "selected_primary_value_after_conflict": .875},
        {"case": "overlap_and_conflict_not_native_report", "hsp1": {"qseq": "ACDE", "sseq": "ACNE", "q": [1,4], "s": [1,4]},
         "hsp2": {"qseq": "DEFG", "sseq": "NEFG", "q": [3,6], "s": [3,6]},
         "query_length": 8, "subject_length": 10, "paired_representations": 8, "distinct_pairs": 6,
         "identical_distinct_pairs": 5, "query_coverage": .75, "subject_coverage": .6, "identity_exact": "5/6",
         "conflicting_hsp3": {"qseq": "DE", "sseq": "DE", "q": [3,4], "s": [7,8]},
         "conflicting_query_positions": conflict_q, "after_conflict_query_coverage": .75,
         "after_conflict_subject_coverage": .8, "after_conflict_aggregate_identity": None},
    ],
}
emit("NUMERICAL_EXAMPLES_001.json", examples)

# A fully shaped measurement sheet from A's existing synthetic JSON projection.
saved = json.loads((ROOT / "verification/tool_graders_bvbrc_proteome_native_2026-10-25/SYNTHETIC_PROJECTIONS_001.json").read_text())
a_result = deepcopy(saved[0]["result"])
native = a_result["value"]
validate("NativeProjectionResult", a_result)
primary_ref = native["source"]["content"]["source_ref"]
requirements = [requirement("exact_executed_input_missing", "execution_input_witness"),
    requirement("full_reports_not_retained", "directional_report")]
attachment = {"version": "bvbrc_proteome_directional_attachment_proposal_v1", "state": "unavailable",
    "expected_scopes": [{"comparison_track_key": t["track_key"], "direction": direction}
        for t in native["tracks"] if t["track_key"] != "ref_genome"
        for direction in ("reference_to_comparison", "comparison_to_reference")],
    "reports": [], "operand_links": [], "requirements": [requirements[1]], "diagnostics": []}
sheet = {"version": "bvbrc_proteome_native_sheet_proposal_v1", "scientific_mode": "proteome_comparison",
    "primary_source_ref": primary_ref, "native_results": [a_result], "input_index": None,
    "inventories": [], "feature_snapshots": [], "genome_snapshots": [], "sequence_snapshots": [],
    "joins": None, "representation_comparisons": [], "tracks": [], "reference_rows": [], "association_rows": [],
    "directional_attachment": attachment, "requirements": requirements,
    "diagnostics": [diagnostic("exact_executed_input_missing"), diagnostic("full_reports_not_retained")]}
for track in native["tracks"]:
    sheet["tracks"].append({"track_key": track["track_key"], "comparison_ordinal": track["comparison_ordinal"],
        "original_input_key": None, "native_materialization": track["materialization"], "native_source_fields": deepcopy(track["source_fields"]),
        "inventory_key": None, "input_record_count": missing("exact_executed_input_missing"),
        "complete_reference_row_membership": "unknown", "complete_published_association_membership": "unknown", "diagnostics": []})
for row in native["reference_rows"]:
    sheet["reference_rows"].append({"reference_row_ordinal": row["row_ordinal"], "reference_row_key": row["reference_row_key"],
        "protein": None, "join_state": "not_supplied", "native_aa_length": deepcopy(row["aa_length"]),
        "inventory_sequence_symbol_count": missing("exact_executed_input_missing"),
        "native_start": deepcopy(row["start"]), "native_end": deepcopy(row["end"]), "native_strand": deepcopy(row["strand"]),
        "coordinate_kind": "unknown", "metadata_links": [], "diagnostics": []})
for row in native["associations"]:
    sheet["association_rows"].append({"association_key": row["association_key"], "reference_row_ordinal": row["reference_row_ordinal"],
        "track_key": row["track_key"], "reference_protein": None, "subject_protein": None,
        "reference_join_state": "not_supplied", "subject_join_state": "not_supplied",
        "native_hit_category": deepcopy(row["hit"]), "native_subject_length_aa": deepcopy(row["aa_length"]),
        "inventory_subject_sequence_symbol_count": missing("exact_executed_input_missing"),
        "native_first_hsp_alignment_identity_fraction": deepcopy(row["percent_identity"]),
        "native_subject_endpoint_difference_fraction": deepcopy(row["seq_coverage"]),
        "layout_state": "source_field_located", "native_subject_identifier_present": True,
        "metadata_links": [], "diagnostics": []})
validate("NativeSheet", sheet)
validate("NativeSheetResult", {"status": "partial", "value": sheet, "requirements": requirements, "diagnostics": sheet["diagnostics"]})
check("synthetic_A_envelope_reused_unchanged", sheet["native_results"][0] == saved[0]["result"])
check("saved_native_cells_reused_unchanged", all(
    row["native_first_hsp_alignment_identity_fraction"] == original["percent_identity"] and
    row["native_subject_endpoint_difference_fraction"] == original["seq_coverage"]
    for row, original in zip(sheet["association_rows"], native["associations"])))
emit("FILLED_NATIVE_SHEET_001.json", {"origin": "schema_example_from_existing_A_synthetic_projection_not_a_production_builder_result", "value": sheet})

# Expected component shape for that exact unbound sheet. Literal native rows
# supply the arithmetic, with no asserted original inputs or biological counts.
parameters = {"version": "bvbrc_proteome_native_parameters_proposal_v1", "track_keys": ["comp_genome_2", "comp_genome_4"],
    "minimum_identity_fraction": .6, "minimum_subject_endpoint_difference_fraction": .7, "allowed_hit_categories": None}
component = {"version": "bvbrc_proteome_native_components_proposal_v1", "formula_version": "native_descriptive_components_v1",
    "sheet_sha256": sha(canonical(sheet)), "parameters": parameters, "associations": [], "tracks": [],
    "used_component_families": ["legacy_identity", "legacy_subject_endpoint_difference", "native_category", "explicit_occurrence_membership", "full_sequence_identity"],
    "retained_unused_component_families": ["feature_function_assignments", "feature_taxonomy", "feature_families", "genomic_or_layout_coordinates", "directional_hsps"],
    "requirements": requirements, "diagnostics": []}
for row in sheet["association_rows"]:
    i = Q(row["native_first_hsp_alignment_identity_fraction"]["lexeme"])
    c = Q(row["native_subject_endpoint_difference_fraction"]["lexeme"])
    failed = ([] if i >= Q(3,5) else ["identity"]) + ([] if c >= Q(7,10) else ["subject_endpoint_difference"])
    component["associations"].append({"association_key": row["association_key"], "track_key": row["track_key"],
        "first_hsp_alignment_identity_percent": cell(float(100 * i), fields=[row["native_first_hsp_alignment_identity_fraction"]["source_field"]]),
        "subject_endpoint_difference_percent": cell(float(100 * c), fields=[row["native_subject_endpoint_difference_fraction"]["source_field"]]),
        "selection": "fail" if failed else "pass", "failed_conditions": failed, "unknown_conditions": [], "diagnostics": []})
for track_key in parameters["track_keys"]:
    rows = [r for r in sheet["association_rows"] if r["track_key"] == track_key]
    n = len(rows)
    def summary(field):
        values = [Q(r[field]["lexeme"]) for r in rows]
        fields = [r[field]["source_field"] for r in rows]
        return {"used_association_keys": [r["association_key"] for r in rows], "value_count": cell(n, fields=fields),
            **{key: cell(0) for key in ("omitted_count", "null_count", "blank_count", "invalid_count", "layout_uncertain_count")},
            "sum": cell(float(sum(values)), fields=fields), "mean": cell(float(sum(values)/n), fields=fields),
            "minimum": cell(float(min(values)), fields=fields), "maximum": cell(float(max(values)), fields=fields),
            "unit": "fraction", "native_rounding_quantum": .001}
    counts = {key: cell(0) for key in ("observed_bound_reference_count", "observed_bound_subject_count", "multiple_reference_subject_count",
        "excess_bound_pair_count", "observed_selected_reference_count", "demonstrated_subject_sequence_group_count", "unresolved_subject_sequence_count")}
    counts.update({"source_association_record_count": cell(n), "published_association_record_count": cell(n),
        "native_bi_count": cell(sum(r["native_hit_category"]["value"] == "bi (<->)" for r in rows)),
        "native_uni_count": cell(sum(r["native_hit_category"]["value"] == "uni (->)" for r in rows)),
        "native_other_category_count": cell(0), "native_missing_category_count": cell(0),
        "unresolved_reference_association_count": cell(n), "unresolved_subject_association_count": cell(n),
        "reference_input_record_count": missing("exact_executed_input_missing"), "comparison_input_record_count": missing("exact_executed_input_missing"),
        "no_published_reference_count": missing("reference_membership_unresolved")})
    statuses = [r["selection"] for r in component["associations"] if r["track_key"] == track_key]
    rr = ratio(cell(0), missing("exact_executed_input_missing"), None, "missing_input", ["denominator_unavailable"])
    component["tracks"].append({"track_key": track_key, "materialization": "published_association", "source_scope": "complete_document",
        **counts, "first_hsp_identity_summary": summary("native_first_hsp_alignment_identity_fraction"),
        "subject_endpoint_difference_summary": summary("native_subject_endpoint_difference_fraction"),
        "observed_reference_fraction": deepcopy(rr), "complete_published_reference_fraction": deepcopy(rr),
        "selection_counts": {k: cell(statuses.count(k)) for k in ("pass", "fail", "unknown")},
        "observed_selected_reference_fraction": deepcopy(rr), "complete_selected_reference_fraction": deepcopy(rr),
        "qualifications": ["legacy_first_hsp_only", "legacy_rounded_fraction", "legacy_subject_endpoint_difference",
            "native_category_not_orthology_probability", "exact_executed_input_missing", "row_join_missing", "observed_subset_not_total", "full_reports_not_retained"]})
validate("NativeComponents", component)
check("filled_comp2_mean_identity", component["tracks"][0]["first_hsp_identity_summary"]["mean"]["value"] == .875)
check("filled_comp4_mean_identity", component["tracks"][1]["first_hsp_identity_summary"]["mean"]["value"] == .4375)
check("filled_missing_denominator_not_source_row_count", all(t["reference_input_record_count"]["value"] is None for t in component["tracks"]))
check("filled_measured_zero_retained", component["associations"][1]["first_hsp_alignment_identity_percent"]["value"] == 0)
emit("FILLED_NATIVE_COMPONENTS_001.json", {"origin": "independently_calculated_expected_shape_not_a_production_calculator_result", "value": component})

validate("CountCell", cell(0))
validate("FractionCell", missing())
validate("Ratio", examples["cases"][6]["ratio"])
validate("DirectionalAttachment", attachment)
rejects("CountCell", {**cell(0), "extra": True})
rejects("CountCell", cell(-1))
rejects("CountCell", cell(True))
rejects("FractionCell", cell(1.01))
rejects("FractionCell", cell(float("nan")))
rejects("FractionCell", cell(0, "missing_input"))
rejects("NativeSheetResult", {"status": "invalid", "value": sheet, "requirements": [], "diagnostics": []})
rejects("NativeSheetResult", {"status": "ok", "value": None, "requirements": [], "diagnostics": []})

emit("VERIFICATION_001.json", {"recorded_at": datetime.now(timezone.utc).isoformat(),
    "scope": "contract_data_shapes_and_independent_literal_arithmetic_only", "check_count": len(CHECKS), "checks": CHECKS,
    "definitions": len(SCHEMA["$defs"]), "native_definitions_unchanged": len(NATIVE["$defs"]),
    "all_object_shapes_closed": not open_objects, "failed_checks": 0,
    "production_parsers_or_calculators_executed": False, "native_program_executed": False,
    "new_service_or_hpc_job": False, "new_native_output_fixture_generated": False,
    "real_GenomeComparison_output_verified": False, "episode_integration_verified": False,
    "native_synthetic_source": "verification/tool_graders_bvbrc_proteome_native_2026-10-25/SYNTHETIC_PROJECTIONS_001.json",
    "limits": ["Schema validation is not source custody or scientific truth validation.",
        "Expected sheet/components are manually constructed contract examples, not working production modules.",
        "Exact execution witness and full directional native report format evidence remain unresolved."]})
print(json.dumps({"checks_passed": len(CHECKS), "schema_definitions": len(SCHEMA["$defs"]), "failed": 0}))
