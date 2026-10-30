"""Pure operand checks for the frozen shared phylogeny calculators.

These checks establish supplied relationships, not source authentication. C4
custody and provider extraction remain responsible for evidence truth. No files,
schemas, network connections or native programs are opened by this module.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re

COMPLETENESS = ("complete", "partial", "truncated", "unknown")
STATES = ("available", "missing", "not_measured", "failed", "truncated", "incompatible")
BRANCH_UNITS = ("expected_substitutions_per_model_site", "joint_mixed_partition_model_site", "native_unknown")
SUPPORT_METHODS = ("rapid_bootstrap", "rell_bootstrap", "phyml_abayes", "phyml_alrt_statistic",
                   "phyml_chi2", "phyml_sh_like", "fasttree_sh_like", "native_unknown")
SUPPORT_SCALES = ("percent", "fraction", "statistic", "native_unknown")
NATIVE_FIELDS = ("branch_length", "branch_support_native", "log_likelihood",
    "distinct_alignment_patterns", "gap_undetermined_percent_native", "family_native_length",
    "family_native_sequences", "family_native_gaps", "family_native_sum_squared_freq",
    "family_native_mean_squared_freq", "family_native_ranking_score", "family_native_worst_sequence_ratio",
    "sequence_native_mean_log2_frequency", "genome_native_all_families", "genome_native_single_copy_families",
    "genome_native_filtered_single_copy_families", "analysis_native_reported_counts")
NATIVE_UNITS = BRANCH_UNITS + ("percent", "fraction", "native_statistic", "natural_log_likelihood",
    "patterns", "columns", "sequences", "characters", "column_summed_squared_fraction",
    "mean_squared_fraction", "square_root_columns", "ratio", "bits_per_column", "families", "reported_count")

# Ordinary missing-input vocabulary; it does not select or execute work.
REQUIREMENT_REASONS = {
    "alignment_population_incomplete": ("output_bytes", "alignment"),
    "alphabet_required": ("scientific_metadata", "alignment_alphabet"),
    "original_member_length_required": ("input_metadata", "original_member_length"),
    "original_residue_map_required": ("scientific_metadata", "original_residue_map"),
    "branch_lengths_required": ("output_bytes", "native_tree"),
    "support_method_unresolved": ("scientific_metadata", "support_method"),
    "support_scale_unresolved": ("scientific_metadata", "support_scale"),
    "support_observations_conflict": ("scientific_metadata", "branch_support_resolution"),
    "bootstrap_expected_count_required": ("scientific_metadata", "bootstrap_population"),
    "bootstrap_replicates_not_retained": ("output_bytes", "bootstrap_replicates"),
    "composition_population_required": ("input_metadata", "composition_population"),
    "taxon_associations_required": ("scientific_metadata", "taxon_associations"),
}


def scope(*segments):
    """Escape each operand separately; slashes/percent signs cannot alias IDs."""
    for segment in segments:
        text(segment)
    return "phylogeny/" + "/".join(x.replace("%", "%25").replace("/", "%2F") for x in segments)


def fail(code):
    raise ValueError("phylogeny_" + code)


def require(condition, code):
    if not condition:
        fail(code)


def shape(value, keys, code="operand_shape_invalid"):
    require(type(value) is dict and set(value) == set(keys), code)


def text(value, *, nullable=False, empty=False):
    require(nullable and value is None or type(value) is str and (empty or bool(value)), "text_invalid")


def integer(value, *, nullable=False, minimum=0):
    require(nullable and value is None or type(value) is int and value >= minimum, "integer_invalid")


def number(value, *, nullable=False):
    require(nullable and value is None or type(value) is int or type(value) is float and math.isfinite(value),
            "number_invalid")


def sequence(value, *, stored=False):
    require(type(value) is list if stored else type(value) in (list, tuple), "array_invalid")


def unique_indices(value, *, stored=True):
    sequence(value, stored=stored)
    for i in value:
        integer(i)
    require(len(value) == len(set(value)), "duplicate_index")


def strings(value):
    sequence(value, stored=True)
    for s in value:
        text(s)
    require(len(value) == len(set(value)), "duplicate_identifier")


def digest(value, *, nullable=False):
    require(nullable and value is None or type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            "digest_invalid")


def evidence(value):
    sequence(value, stored=True)
    for item in value:
        shape(item, {"content", "pointer"}, "evidence_shape_invalid")
        content = item["content"]
        shape(content, {"source_ref", "artifact_field", "artifact_ref", "sha256", "byte_count"}, "evidence_shape_invalid")
        text(content["source_ref"])
        text(content["artifact_ref"])
        require(content["artifact_field"] in ("artifact_ref", "text_ref", "stdout_ref", "stderr_ref"), "evidence_invalid")
        digest(content["sha256"])
        integer(content["byte_count"])
        text(item["pointer"], empty=True)
        require((item["pointer"] == "" or item["pointer"].startswith("/")) and
                re.search(r"~(?![01])", item["pointer"]) is None, "evidence_pointer_invalid")


def location(value):
    shape(value, {"artifact", "byte_start_0based", "byte_end_0based_exclusive", "line_start_1based",
                  "line_end_1based_inclusive", "xml_path"}, "source_location_invalid")
    artifact = value["artifact"]
    shape(artifact, {"raw_artifact_ref", "source_ref", "sha256"}, "source_location_invalid")
    text(artifact["raw_artifact_ref"])
    text(artifact["source_ref"])
    digest(artifact["sha256"])
    present = False
    for start, end, minimum in (("byte_start_0based", "byte_end_0based_exclusive", 0),
                                ("line_start_1based", "line_end_1based_inclusive", 1)):
        a, b = value[start], value[end]
        if a is None and b is None:
            continue
        integer(a, minimum=minimum)
        integer(b, minimum=minimum)
        require(b >= a, "source_location_invalid")
        present = True
    if value["xml_path"] is not None:
        text(value["xml_path"])
        require(value["xml_path"].startswith("/"), "source_location_invalid")
        present = True
    require(present, "source_location_missing")


def subject(value):
    shape(value, {"kind", "id", "source_record_id"}, "subject_shape_invalid")
    require(value["kind"] in ("input_member", "feature", "genome"), "subject_kind_invalid")
    text(value["id"])
    text(value["source_record_id"])
    return value["kind"], value["id"], value["source_record_id"]


def member(value):
    shape(value, {"input_binding_id", "member_id"}, "member_shape_invalid")
    text(value["input_binding_id"])
    text(value["member_id"])
    return value["input_binding_id"], value["member_id"]


def alignment_population(value, alignment):
    shape(value, {"population_id", "alignment_id", "row_indices", "columns_0based", "completeness", "evidence"},
          "alignment_population_shape_invalid")
    text(value["population_id"])
    require(value["alignment_id"] == alignment["alignment_id"], "alignment_population_identity_conflict")
    require(value["completeness"] in COMPLETENESS, "population_completeness_invalid")
    evidence(value["evidence"])
    unique_indices(value["row_indices"])
    unique_indices(value["columns_0based"])
    require(all(i < len(alignment["rows"]) for i in value["row_indices"]), "population_row_outside_alignment")
    bound = alignment["observed_column_count"]
    if bound is None:
        bound = alignment["declared_column_count"]
    if bound is None:
        bound = max((len(row["sequence"]) for row in alignment["rows"]), default=0)
    require(all(j < bound for j in value["columns_0based"]), "population_column_outside_alignment")


def _member_population(value, *, taxonomy=False):
    shape(value, {"population_id", "unit", "member_subjects", "assignment_completeness",
                  "membership_completeness", "evidence"}, "composition_population_shape_invalid")
    text(value["population_id"])
    kinds = {"sequence_member": "input_member", "feature": "feature"}
    if taxonomy:
        kinds["genome"] = "genome"
    require(value["unit"] in tuple(kinds), "taxon_unit_invalid" if taxonomy else "composition_unit_invalid")
    require(value["assignment_completeness"] in COMPLETENESS and value["membership_completeness"] in COMPLETENESS,
            "population_completeness_invalid")
    sequence(value["member_subjects"], stored=True)
    evidence(value["evidence"])
    keys = [subject(row) for row in value["member_subjects"]]
    require(len(keys) == len(set(keys)), "duplicate_subject")
    expected_kind = kinds[value["unit"]]
    require(all(k[0] == expected_kind for k in keys),
            "taxon_subject_unit_conflict" if taxonomy else "composition_subject_unit_conflict")
    # Two source records may record the same member, but may not create two
    # population members and two votes for it.
    require(len({k[:2] for k in keys}) == len(keys), "duplicate_member_identity")
    return keys


def composition_population(value):
    return _member_population(value)


def taxon_population(value):
    return _member_population(value, taxonomy=True)


def native_observation(value):
    shape(value, {"observation_id", "field", "value", "raw_token", "state", "unit", "population_id", "subject_id",
                  "method", "location", "evidence", "uncertainty", "requirement_ids"}, "native_observation_shape_invalid")
    for key in ("observation_id", "population_id", "method"):
        text(value[key])
    text(value["subject_id"], nullable=True)
    text(value["raw_token"], nullable=True, empty=True)
    require(value["field"] in NATIVE_FIELDS and value["unit"] in NATIVE_UNITS and value["state"] in STATES,
            "native_observation_invalid")
    number(value["value"], nullable=True)
    require((value["value"] is not None) == (value["state"] == "available"), "native_value_state_conflict")
    evidence(value["evidence"])
    strings(value["requirement_ids"])
    if value["location"] is not None:
        location(value["location"])
    require(value["location"] is not None or bool(value["evidence"]), "native_source_missing")
    if value["uncertainty"] is not None:
        uncertainty = value["uncertainty"]
        shape(uncertainty, {"kind", "lower", "upper", "value", "method"}, "native_uncertainty_invalid")
        require(uncertainty["kind"] in ("standard_error", "interval", "native_other"), "native_uncertainty_invalid")
        text(uncertainty["method"])
        for key in ("lower", "upper", "value"):
            number(uncertainty[key], nullable=True)
        require(uncertainty["lower"] is None or uncertainty["upper"] is None or
                uncertainty["lower"] <= uncertainty["upper"], "native_uncertainty_invalid")
    if value["field"] == "branch_length":
        require(value["unit"] in BRANCH_UNITS, "native_unit_conflict")
    elif value["field"] == "branch_support_native":
        require(value["unit"] in ("percent", "fraction", "native_statistic", "native_unknown"), "native_unit_conflict")


def quantity(value, *, population, unit, method, numerator=None, denominator=None,
             state="missing", origin="derived", evidence_rows=(), requirements=()):
    number(value, nullable=True)
    number(numerator, nullable=True)
    number(denominator, nullable=True)
    return {"value": value, "state": "available" if value is not None else state,
            "unit": unit, "origin": origin, "numerator": numerator, "denominator": denominator,
            "population_ref": population, "method": method, "evidence": deepcopy(list(evidence_rows)),
            "requirement_ids": list(requirements)}


def ratio(numerator, denominator, *, population, method, unit="fraction", state="missing", requirements=()):
    value = numerator / denominator if numerator is not None and denominator not in (None, 0) else None
    return quantity(value, population=population, unit=unit, method=method, numerator=numerator,
                    denominator=denominator, state=state, requirements=requirements)


def unavailable_state(completeness):
    return "truncated" if completeness == "truncated" else "missing"


def requirement(population, reason, *, source_refs=(), role=None, kind=None):
    require(reason in REQUIREMENT_REASONS, "requirement_reason_unknown")
    expected_kind, expected_role = REQUIREMENT_REASONS[reason]
    require(kind in (None, expected_kind) and role in (None, expected_role), "requirement_meaning_conflict")
    return {"requirement_id": population + "/" + reason, "kind": expected_kind, "role": expected_role,
            "source_refs": list(dict.fromkeys(source_refs)), "reason_code": reason}


def diagnostic(code, *, path="", evidence_refs=()):
    return {"code": "phylogeny_" + code, "phase": "association", "path": path,
            "severity": "qualification", "evidence_refs": list(dict.fromkeys(evidence_refs))}


LITERAL_CONSERVATION_VERSION = "literal_site_conservation_v1"
LITERAL_CONSERVATION_CONVENTION = "modal_literal_all_rows_first_source_row_v1"
_QUANTITY_KEYS = {"value", "state", "unit", "origin", "numerator", "denominator",
                  "population_ref", "method", "evidence", "requirement_ids"}


def validate_literal_site_conservation_components(value, *, alignment, population):
    """Check the closed new convention without recounting source characters.

    This checks shape and supplied scope, not custody or native production.
    Existing shared quantities supply the counts and fraction arithmetic.
    """
    alignment_population(population, alignment)
    shape(value, {"version", "convention", "alignment_id", "population_id",
        "ordered_source_row_indices", "member_count", "site_count", "threshold", "display", "sites"},
        "literal_conservation_shape_invalid")
    require(value["version"] == LITERAL_CONSERVATION_VERSION
        and value["convention"] == LITERAL_CONSERVATION_CONVENTION,
        "literal_conservation_convention_invalid")
    unique_indices(value["ordered_source_row_indices"])
    require(value["alignment_id"] == alignment["alignment_id"]
        and value["population_id"] == population["population_id"]
        and value["ordered_source_row_indices"] == sorted(population["row_indices"]),
        "literal_conservation_population_conflict")
    require(value["threshold"] == {"comparison": "strict_greater_than", "value": 0.8,
        "basis": "unrounded_binary64_ratio"} and type(value["threshold"]["value"]) is float,
        "literal_conservation_threshold_invalid")
    require(value["display"] == {"decimal_places": 2, "rounding": "binary64_fixed_2_ties_to_even"}
        and type(value["display"]["decimal_places"]) is int, "literal_conservation_display_invalid")

    def checked_quantity(row, unit, method, *, integer_value=False):
        shape(row, _QUANTITY_KEYS, "literal_conservation_quantity_invalid")
        for field in ("value", "numerator", "denominator"):
            number(row[field], nullable=True)
        require(row["population_ref"] == population["population_id"] and row["unit"] == unit
            and row["method"] == method and row["origin"] == "derived"
            and row["state"] in STATES and (row["value"] is not None) == (row["state"] == "available"),
            "literal_conservation_quantity_invalid")
        if integer_value:
            integer(row["value"], nullable=True)
        evidence(row["evidence"])
        strings(row["requirement_ids"])

    checked_quantity(value["member_count"], "rows", "selected_row_count", integer_value=True)
    checked_quantity(value["site_count"], "columns", "selected_column_count", integer_value=True)
    sequence(value["sites"], stored=True)
    require([row.get("column_0based") for row in value["sites"] if type(row) is dict]
        == population["columns_0based"] and all(type(row) is dict for row in value["sites"]),
        "literal_conservation_column_conflict")
    for row in value["sites"]:
        shape(row, {"column_0based", "symbol_counts", "modal_symbol", "modal_first_source_row_index",
            "modal_count", "majority_fraction", "strict_gt_0_8", "displayed_2dp_fraction"},
            "literal_conservation_site_invalid")
        integer(row["column_0based"])
        sequence(row["symbol_counts"], stored=True)
        symbols = []
        for counted in row["symbol_counts"]:
            shape(counted, {"symbol", "count"}, "literal_conservation_symbol_invalid")
            require(type(counted["symbol"]) is str and len(counted["symbol"]) == 1,
                "literal_conservation_symbol_invalid")
            integer(counted["count"], minimum=1)
            symbols.append(counted["symbol"])
        require(symbols == sorted(set(symbols)), "literal_conservation_symbol_invalid")
        symbol, first = row["modal_symbol"], row["modal_first_source_row_index"]
        require(symbol is None or type(symbol) is str and len(symbol) == 1,
            "literal_conservation_symbol_invalid")
        integer(first, nullable=True)
        require((symbol is None) == (first is None) and (first is None or
            first in value["ordered_source_row_indices"] and
            row["column_0based"] < len(alignment["rows"][first]["sequence"]) and
            alignment["rows"][first]["sequence"][row["column_0based"]] == symbol),
            "literal_conservation_modal_identity_conflict")
        checked_quantity(row["modal_count"], "characters", "literal_modal_symbol_count", integer_value=True)
        checked_quantity(row["majority_fraction"], "fraction", "literal_modal_all_rows_fraction")
        checked_quantity(row["displayed_2dp_fraction"], "fraction", "literal_modal_fraction_fixed_2")
        require(row["strict_gt_0_8"] is None or type(row["strict_gt_0_8"]) is bool,
            "literal_conservation_threshold_invalid")
        for field in ("majority_fraction", "displayed_2dp_fraction"):
            require(row[field]["value"] is None or 0 <= row[field]["value"] <= 1,
                "literal_conservation_fraction_invalid")
    return deepcopy(value)
