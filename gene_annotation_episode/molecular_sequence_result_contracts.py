"""Private molecular result controls and strictly selected stored public values.

Pointers select literal retained cells. This module never invokes a numerical
calculator or infers a missing value, population, calibration or source call.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .execution_contracts import canonical, digest
from .native_file_capture import _identity as file_identity, _declaration as file_declaration
from .sequence_mapping import path_length


OPERATIONS = ("annotate_open_reading_frames", "align_sequences", "find_n_glycosylation_motifs",
    "predict_o_glycosylation_hotspots", "analyze_protease_kinetics")
SELECTOR_VERSION = "molecular_sequence_result_selector_v1"
PLAN_VERSION = "molecular_sequence_result_worker_plan_v1"
RESULT_VERSION = "molecular_sequence_result_worker_result_v1"
PROJECTION_VERSION = "molecular_sequence_private_projection_v1"
PUBLIC_VERSION = "molecular_sequence_selected_values_v1"
N_SELECTOR_VERSION = "molecular_sequence_result_selector_v3"
N_PROJECTION_VERSION = "molecular_sequence_private_projection_v2"
N_PUBLIC_VERSION = "molecular_sequence_selected_values_v2"
O_SELECTOR_VERSION = "molecular_sequence_result_selector_v4"
O_PROJECTION_VERSION = "molecular_sequence_private_projection_v3"
O_PUBLIC_VERSION = "molecular_sequence_selected_values_v3"
PROTEASE_SELECTOR_VERSION = "molecular_sequence_result_selector_v5"
PROTEASE_PROJECTION_VERSION = "molecular_sequence_private_projection_v4"
PROTEASE_PUBLIC_VERSION = "molecular_sequence_selected_values_v4"
PROTEASE_CONTEXT_VERSION = "protease_kinetics_public_context_v1"
PLACEMENT_SELECTOR_VERSION = "molecular_sequence_result_selector_v6"
PLACEMENT_PROJECTION_VERSION = "molecular_sequence_private_projection_v5"
PLACEMENT_PUBLIC_VERSION = "molecular_sequence_selected_values_v5"
PLACEMENT_MAX_NESTING = 32
_LEGACY_PROFILE = "legacy_v1"
_N_PROFILE = "n_glycosylation_v3"
_O_PROFILE = "o_glycosylation_v4"
_PROTEASE_PROFILE = "protease_kinetics_v5"
_PLACEMENT_PROFILE = "primer_placement_v6"
MODES = ("original_attempt", "saved_sheet_calculation")
FILE_ROLES = ("sheet", "components", "capture", "native_results", "native_plot")
FILE_STATES = ("retained", "retained_undeclared", "retention_failed", "producer_absent",
    "producer_unavailable", "identity_conflict", "unavailable", "not_requested", "produced_unretained")
VALUE_STATES = ("stored_value", "stored_null", "path_missing", "source_unavailable", "invalid_type")
PROJECTION_SOURCE = "molecular_sequence_selected_values"
SAVED_SOURCE = "molecular_sequence_retained_files"
FAILURE_SOURCE = "molecular_sequence_result_failures"
FACT_SOURCES = (PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE)
OUTPUTS = ("projection", "calculated_components", "diagnostics")
SCHEMAS = {
    OPERATIONS[0]: ("orf_measurement_sheet_v1", ("orf_measurement_components_v1",)),
    OPERATIONS[1]: ("primer_placement_sheet_v1", ("primer_placement_components_v1",)),
    OPERATIONS[2]: ("glycosylation_measurement_sheet_v1", ("glycosylation_measurement_components_v1",)),
    OPERATIONS[3]: ("glycosylation_measurement_sheet_v1", ("glycosylation_measurement_components_v1",)),
    OPERATIONS[4]: ("protease_kinetics_sheet_v1", ("protease_kinetics_components_v1", "protease_kinetics_components_v2")),
}
QUANTITIES = ("product_vmax", "product_formation_per_enzyme_concentration", "apparent_turnover", "kcat",
    "apparent_catalytic_efficiency", "catalytic_efficiency")
STAGES = ("authority", "capture", "load", "selection", "calculation", "worker", "publication", "replay")
FAILURES = ("scientific_binding_unavailable", "original_attempt_conflict", "writer_not_closed", "artifact_unavailable",
    "retention_failed", "producer_absent", "producer_unavailable", "artifact_identity_conflict", "declaration_unavailable",
    "schema_invalid", "selected_path_missing", "selected_type_invalid", "calculation_failed", "worker_unavailable",
    "worker_failed", "worker_uncertain", "publication_failed", "received_sheet_not_known", "stored_source_conflict")
FIT_CODES = ("native_call_raised_after_observed_values", "native_source_returned_error_string",
    "observer_has_separately_recorded_failures", "native_implementation_verification_incomplete",
    "native_fit_population_incompatible", "negative_substrate_concentration")
REASONS_COMMON = ("native_fit_parameters_unavailable", "native_fit_population_incompatible", "negative_substrate_concentration",
    "native_implementation_verification_incomplete", "calibration_not_supplied", "calibration_applicability_unknown",
    "calibration_applicability_conflicting", "calibration_applicability_unsupported", "calibration_curve_population_conflict",
    "compatible_declared_units_required", "positive_enzyme_concentration_required", "product_per_cleavage_unknown",
    "active_site_concentration_basis_unestablished", "positive_km_required", "physical_calculation_numerical_range",
    "nonfinite_or_unrepresentable_calculation", "native_covariance_unavailable", "native_covariance_nonfinite",
    "propagated_variance_numerical_range", "not_supplied_or_estimated", "calibration_enzyme_and_joint_relationships_unknown",
    "native_rate_vector_unavailable", "native_substrate_vector_unavailable", "insufficient_residual_population",
    "residual_summary_unavailable", "zero_model_denominator", "native_vector_slot_has_no_measured_curve", "model_numerical_range")
REASONS = {"protease_kinetics_components_v1": (*REASONS_COMMON, "native_covariance_asymmetric", "native_covariance_indefinite"),
    "protease_kinetics_components_v2": (*REASONS_COMMON, "native_covariance_symmetric_part_indefinite",
        "propagated_variance_negative", "propagated_variance_overflow", "propagated_variance_positive_underflow",
        "physical_ratio_overflow", "physical_ratio_positive_underflow")}


def require(condition, code="molecular_sequence_result_contract"):
    if not condition:
        raise ValueError(code)


def closed(value, fields):
    require(type(value) is dict and set(value) == set(fields))


def copy_json(value):
    return json.loads(canonical(value))


def reference(value):
    return type(value) is str and re.fullmatch("artifact_[0-9a-f]{64}", value) is not None


def failure(code, stage, *, role=None, row_id=None, source_ref=None, source_pointer=None, diagnostic_ref=None):
    value = dict(code=code, stage=stage, role=role, row_id=deepcopy(row_id), source_ref=source_ref,
        source_pointer=source_pointer, diagnostic_ref=diagnostic_ref)
    return validate_failure(value)


def validate_failure(value):
    closed(value, ("code", "stage", "role", "row_id", "source_ref", "source_pointer", "diagnostic_ref"))
    require(value["code"] in FAILURES and value["stage"] in STAGES and value["role"] in (*FILE_ROLES, None))
    require(all(value[k] is None or reference(value[k]) for k in ("source_ref", "diagnostic_ref")))
    require(value["source_pointer"] is None or type(value["source_pointer"]) is str and value["source_pointer"].startswith("/"))
    if value["row_id"] is not None:
        row_id(value["row_id"])
    return copy_json(value)


def empty_file_state(state="unavailable", *, declared=None, issue=None):
    return dict(state=state, file=None, declared=deepcopy(declared), observed_identity=None, failure=issue)


def validate_file_state(value):
    closed(value, ("state", "file", "declared", "observed_identity", "failure"))
    require(value["state"] in FILE_STATES)
    require((value["file"] is not None) == (value["state"] in ("retained", "retained_undeclared")))
    if value["file"] is not None:
        file_identity(value["file"])
    if value["declared"] is not None:
        file_declaration(value["declared"])
    if value["observed_identity"] is not None:
        closed(value["observed_identity"], ("sha256", "size_bytes"))
        require(type(value["observed_identity"]["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", value["observed_identity"]["sha256"]) is not None
            and type(value["observed_identity"]["size_bytes"]) is int and value["observed_identity"]["size_bytes"] >= 0)
    if value["state"] == "producer_absent":
        require(value["declared"] is not None and value["declared"]["state"] == "absent")
    if value["file"] is not None:
        require(value["observed_identity"] == {k: value["file"][k] for k in ("sha256", "size_bytes")})
    if value["failure"] is not None:
        validate_failure(value["failure"])
    return copy_json(value)


def row_id(value):
    require(type(value) is dict and type(value.get("kind")) is str)
    fields = {"summary": (), "orf": ("row_index",), "placement_group": ("group_ordinal",),
        "placement_hit": ("group_ordinal", "native_hit_ordinal"),
        "placement_mismatch": ("group_ordinal", "native_hit_ordinal", "native_mismatch_ordinal"),
        "glycosylation_site": ("row_ordinal",), "protease_fit": (), "protease_curve": ("substrate_ordinal",),
        "protease_quantity": ("quantity",), "protease_covariance": ("parameter_i", "parameter_j")}
    require(value["kind"] in fields)
    closed(value, ("kind", *fields[value["kind"]]))
    for key in fields[value["kind"]]:
        require(value[key] in QUANTITIES if key == "quantity" else type(value[key]) is int and value[key] >= 0)
        if key in ("parameter_i", "parameter_j"):
            require(value[key] in (0, 1))
    return deepcopy(value)


ORF_SUMMARY = ("input_length_nt", "reported_row_count", "usable_saved_row_count", "forward_row_count", "reverse_row_count",
    "strand_known_row_count", "retained_length_sum_nt", "retained_length_denominator_rows", "mean_retained_orf_length_nt",
    "source_definition_compatible_row_count", "translation_compatible_row_count")
_ORF_NATIVE_FIELDS = ("sequence", "aa_sequence", "start", "end", "strand", "frame")
PLACEMENT_SUMMARY = ("target_length_symbols", "requested_primer_occurrence_count", "native_group_count", "known_native_hit_list_count",
    "retained_native_hit_occurrence_count", "usable_saved_hit_count", "plus_hit_count", "minus_hit_count", "strand_known_hit_count",
    "source_compatible_hit_count", "mismatch_count_sum", "mismatch_count_denominator_hits")
GLYCO_SUMMARY = ("original_symbol_count", "processed_symbol_count", "native_reported_sequence_length", "native_reported_total_count",
    "retained_printed_row_count", "usable_checked_row_count", "malformed_row_count", "native_reported_remaining_count",
    "unretained_reported_row_count", "native_total_operand_upper_bound", "native_log_complete", "native_report_complete",
    "scan_exhaustiveness_verified", "native_count_rows_compatible", "native_metadata_matches_operands", "native_total_within_operand_upper_bound")


def field_table(operation, identity, *, profile=_LEGACY_PROFILE):
    """Map semantic names to exact stored paths/types/populations; no formula."""
    require(profile == _LEGACY_PROFILE or profile == _N_PROFILE and operation == OPERATIONS[2]
        or profile == _O_PROFILE and operation == OPERATIONS[3]
        or profile == _PROTEASE_PROFILE and operation == OPERATIONS[4]
        or profile == _PLACEMENT_PROFILE and operation == OPERATIONS[1])
    row_id(identity)
    kind = identity["kind"]
    table = {}
    def add(name, path, typ="count", unit="unknown", population="retained_rows", denominators=()):
        table[name] = (path, typ, unit, population, tuple(denominators))
    if operation == OPERATIONS[0]:
        if kind == "summary":
            for name in ORF_SUMMARY:
                add(name, "/summary/" + name, "number" if name == "mean_retained_orf_length_nt" else "count",
                    "nt_symbols_per_row" if name == "mean_retained_orf_length_nt" else "nt_symbols" if name in
                    ("input_length_nt", "retained_length_sum_nt") else "rows", "orf_retained_strings" if name in
                    ("mean_retained_orf_length_nt", "retained_length_sum_nt", "retained_length_denominator_rows") else "orf_retained_rows",
                    ("/summary/retained_length_sum_nt", "/summary/retained_length_denominator_rows") if name == "mean_retained_orf_length_nt" else ())
        elif kind == "orf":
            base = "/rows/" + str(identity["row_index"])
            for name, typ, unit in (("interval", "interval", "zero_based_input_nt_symbol_indices"), ("frame", "frame", "frame"),
                    ("strand", "strand", "orientation"), ("interval_length_nt", "count", "nt"),
                    ("nucleotide_symbol_count", "count", "nt_symbols"), ("protein_symbol_count", "count", "product_symbols"),
                    ("source_definition", "compatibility", "state")):
                add(name, base + "/" + name, typ, unit, "orf_retained_row")
            for name, typ, unit in (("state", "compatibility", "state"), ("termination_codon_index", "count", "zero_based_codon_index"),
                    ("untranslated_suffix_nt", "count", "nt_symbols"), ("omitted_stop_codon_count", "count", "codons")):
                add("translation." + name, base + "/translation/" + name, typ, unit, "orf_retained_row")
            add("native_row", base + "/native_row", "orf_native_row", "native_field_units", "orf_retained_row")
            for name in ("orf_source_path", "protein_source_path", "omitted_stop_source_path"):
                add(name, base + "/" + name, "orf_source_path", "per_segment_nt_or_symbol", "orf_retained_row")
    elif operation == OPERATIONS[1]:
        if kind == "summary":
            for name in PLACEMENT_SUMMARY:
                add(name, "/summary/" + name, unit="symbols" if name == "target_length_symbols" else "mismatched_symbols" if
                    name == "mismatch_count_sum" else "groups" if name == "native_group_count" else "lists" if name == "known_native_hit_list_count" else "occurrences", population="placement_retained_hit_occurrences",
                    denominators=("/summary/mismatch_count_denominator_hits",) if name == "mismatch_count_sum" else ())
        elif kind in ("placement_group", "placement_hit", "placement_mismatch"):
            base = "/groups/" + str(identity["group_ordinal"])
            if kind == "placement_group":
                for name in ("primer_length_symbols", "native_primer_length_symbols", "candidate_windows_per_orientation", "candidate_oriented_windows", "reported_hit_count"):
                    add(name, base + "/" + name, unit="symbols" if "length" in name else "windows" if "windows" in name else "occurrences",
                        population="placement_structural_candidate_windows" if "windows" in name else "placement_primer_occurrence")
            else:
                base += "/hits/" + str(identity["native_hit_ordinal"])
                if kind == "placement_hit":
                    for name, typ, unit in (("target_interval", "interval", "zero_based_target_symbol_indices"), ("strand", "strand", "orientation"),
                            ("native_mismatch_entry_count", "count", "entries"), ("compared_symbol_count", "count", "symbols"),
                            ("identical_symbol_count", "count", "symbols"), ("mismatch_count", "count", "symbols"),
                            ("mismatch_list_matches_full_operands", "bool", "boolean")):
                        add(name, base + "/" + name, typ, unit, "placement_one_full_primer_window")
                    for name in ("numerator", "denominator", "value"):
                        add("mismatch_fraction." + name, base + "/mismatch_fraction/" + name,
                            "number" if name == "value" else "count", "fraction" if name == "value" else "symbols",
                            "placement_one_full_primer_window", (base + "/mismatch_fraction/numerator", base + "/mismatch_fraction/denominator"))
                else:
                    base += "/mismatches/" + str(identity["native_mismatch_ordinal"])
                    for name in ("oriented_primer_position", "original_primer_position", "target_position", "symbols_match_full_operands"):
                        add(name, base + "/" + name, "bool" if name == "symbols_match_full_operands" else "count",
                            "boolean" if name == "symbols_match_full_operands" else "zero_based_symbol_position", "placement_native_mismatch_occurrence")
    elif operation in OPERATIONS[2:4]:
        if kind == "summary":
            for name in GLYCO_SUMMARY:
                boolean = name in GLYCO_SUMMARY[10:]
                add(name, "/summary/" + name, "bool" if boolean else "count", "boolean" if boolean else
                    "symbols" if "symbol" in name or "sequence_length" in name else "rows", "glyco_retained_printed_rows")
        elif kind == "glycosylation_site":
            base = "/rows/" + str(identity["row_ordinal"])
            for name, path, typ, unit in (("position_1based", "/native_values/position_1based", "count", "one_based_processed_symbol_position"),
                    ("line_number", "/line_number", "count", "one_based_log_line"), ("processed_interval", "/cells/processed_interval", "interval", "zero_based_processed_symbol_indices"),
                    ("source_compatible", "/source_compatible", "bool", "boolean")):
                add(name, base + path, typ, unit, "glyco_retained_printed_row")
            if operation == OPERATIONS[3]:
                for name, path, typ, unit in (("native_st_fraction", "/native_values/st_fraction", "number", "fraction"),
                        ("st_count", "/cells/st_count", "count", "symbols"), ("window_denominator_symbols", "/cells/window_denominator_symbols", "count", "symbols"),
                        ("calculated_st_fraction", "/cells/calculated_st_fraction", "number", "fraction"), ("source_rounded_st_fraction", "/cells/source_rounded_st_fraction", "number", "fraction")):
                    add(name, base + path, typ, unit, "glyco_reported_clipped_window", (base + "/cells/st_count", base + "/cells/window_denominator_symbols"))
    elif operation == OPERATIONS[4]:
        if kind == "summary":
            for name in ("time_point_count", "substrate_count", "supplied_curve_count", "requested_initial_point_count", "actual_initial_point_count"):
                add(name, "/population/" + name, unit="curves" if name == "supplied_curve_count" else "substrate_rows" if name == "substrate_count" else "time_points", population="protease_original_substrate_rows")
        elif kind == "protease_fit":
            for name, path, typ, unit in (("vmax", "/vmax/value", "number", "stored_vmax_unit"), ("km", "/km/value", "number", "stored_km_unit"),
                    ("residual_sum_squares", "/residual_sum_squares", "number", "squared_signal_rate"),
                    ("residual_degrees_of_freedom", "/residual_degrees_of_freedom", "count", "degrees_of_freedom"),
                    ("native_n_minus_parameter_count_diagnostic", "/native_n_minus_parameter_count_diagnostic", "int", "diagnostic_rows_minus_parameters")):
                add(name, "/fit_components" + path, typ, unit, "protease_original_substrate_rows")
        elif kind == "protease_covariance":
            add("reported_matrix_entry", f'/fit_components/covariance/{identity["parameter_i"]}/{identity["parameter_j"]}',
                "number", "stored_parameter_units_product", "protease_native_parameter_matrix")
        elif kind == "protease_curve":
            base = "/fit_components/model_rows/" + str(identity["substrate_ordinal"])
            for name in ("native_fit_vector_value", "observed_signal_slope", "prediction", "residual"):
                add(name, base + "/" + name, "number", "stored_vmax_unit", "protease_original_substrate_row")
        elif kind == "protease_quantity":
            base = "/physical_components/" + identity["quantity"]
            operands = ["/assay_context/calibration/response_per_product_concentration"]
            if identity["quantity"] != "product_vmax": operands.append("/measurements/enzyme_concentration")
            if identity["quantity"] not in ("product_vmax", "product_formation_per_enzyme_concentration"): operands.append("/assay_context/product_per_cleavage")
            if identity["quantity"] in ("apparent_catalytic_efficiency", "catalytic_efficiency"): operands.append("/fit_components/km/value")
            for name, suffix in (("value", "/value"), ("variance", "/uncertainty/variance"), ("standard_uncertainty", "/uncertainty/standard_uncertainty")):
                add(name, base + suffix, "number", "stored_quantity_unit" if name != "variance" else "stored_variance_unit",
                    "protease_fit_conditional_on_supplied_context", operands)
    if profile == _PLACEMENT_PROFILE:
        base = "/groups/" + str(identity.get("group_ordinal", 0))
        if kind == "placement_group":
            add("native_group", base + "/native_group", "placement_native_json", "native_field_units", "placement_retained_group_slots")
            for name, unit in (("primer_occurrence_ordinal", "zero_based_supplied_primer_occurrence"),
                    ("native_group_ordinal", "zero_based_native_group_ordinal")):
                add(name, base + "/" + name, "count", unit, "placement_retained_group_slots")
            add("native_sequence_matches_occurrence", base + "/native_sequence_matches_occurrence", "bool", "boolean", "placement_retained_group_slots")
        elif kind in ("placement_hit", "placement_mismatch"):
            base += "/hits/" + str(identity["native_hit_ordinal"])
            if kind == "placement_hit":
                add("native_hit", base + "/native_hit", "placement_native_json", "native_field_units", "placement_native_hit_occurrence")
                for name in ("oriented_source_primer", "target_window"):
                    add(name, base + "/" + name, "text", "processed_symbols", "placement_one_full_primer_window")
                for name in ("target_mapping", "primer_mapping"):
                    add(name, base + "/" + name, "placement_mapping", "per_segment_nt_or_symbol", "placement_one_full_primer_window")
            else:
                base += "/mismatches/" + str(identity["native_mismatch_ordinal"])
                add("native_triple", base + "/native_triple", "placement_native_json", "native_field_units", "placement_native_mismatch_occurrence")
                for name in ("target_source_intervals", "primer_source_intervals"):
                    add(name, base + "/" + name, "placement_source_path", "per_segment_nt_or_symbol", "placement_native_mismatch_occurrence")
    if profile == _N_PROFILE:
        if kind == "summary":
            populations = {
                "original_symbol_count": "n_glyco_original_operand_symbols",
                "processed_symbol_count": "n_glyco_processed_operand_symbols",
                "native_reported_sequence_length": "n_glyco_processed_operand_symbols",
                "native_reported_total_count": "n_glyco_native_reported_sites",
                "retained_printed_row_count": "n_glyco_retained_printed_rows",
                "usable_checked_row_count": "n_glyco_retained_printed_rows",
                "malformed_row_count": "n_glyco_retained_printed_rows",
                "native_reported_remaining_count": "n_glyco_unprinted_reported_rows",
                "unretained_reported_row_count": "n_glyco_unprinted_reported_rows",
                "native_total_operand_upper_bound": "n_glyco_processed_structural_bound"}
            for name, spec in list(table.items()):
                table[name] = (*spec[:3], populations.get(name, "n_glyco_native_report_qualifications"), spec[4])
            add("source_profile_layout_compatible", "/summary/source_profile_layout_compatible", "bool", "boolean",
                "n_glyco_native_report_qualifications")
        elif kind == "glycosylation_site":
            for name, spec in list(table.items()):
                table[name] = (*spec[:3], "n_glyco_retained_printed_row", spec[4])
            base = "/rows/" + str(identity["row_ordinal"])
            for name, path, typ, unit in (
                    ("motif", "/native_values/motif", "text", "literal_native_symbols"),
                    ("source_intervals", "/cells/source_intervals", "n_glycosylation_source_path", "per_segment_nt_aa_or_symbol"),
                    ("native_line", "/native_line", "text", "literal_native_log_line"),
                    ("operand_symbols", "/cells/operand_symbols", "text", "processed_symbols"),
                    ("order_compatible", "/cells/order_compatible", "bool", "boolean"),
                    ("printed_symbols_match_operand", "/cells/printed_symbols_match_operand", "bool", "boolean"),
                    ("literal_sequon", "/cells/literal_sequon", "bool", "boolean")):
                add(name, base + path, typ, unit, "n_glyco_retained_printed_row")
    if profile == _O_PROFILE:
        if kind == "summary":
            populations = {
                "original_symbol_count": "o_glyco_original_operand_symbols",
                "processed_symbol_count": "o_glyco_processed_operand_symbols",
                "native_reported_sequence_length": "o_glyco_processed_operand_symbols",
                "native_reported_total_count": "o_glyco_native_reported_sites",
                "retained_printed_row_count": "o_glyco_retained_printed_rows",
                "usable_checked_row_count": "o_glyco_retained_printed_rows",
                "malformed_row_count": "o_glyco_retained_printed_rows",
                "native_reported_remaining_count": "o_glyco_unprinted_reported_rows",
                "unretained_reported_row_count": "o_glyco_unprinted_reported_rows",
                "native_total_operand_upper_bound": "o_glyco_processed_st_centers"}
            for name, spec in list(table.items()):
                unit = "st_centers" if name == "native_total_operand_upper_bound" else "sites" if name == "native_reported_total_count" else spec[2]
                table[name] = (*spec[:2], unit, populations.get(name, "o_glyco_native_report_qualifications"), ())
            add("source_profile_layout_compatible", "/summary/source_profile_layout_compatible", "bool", "boolean",
                "o_glyco_native_report_qualifications")
        elif kind == "glycosylation_site":
            base = "/rows/" + str(identity["row_ordinal"])
            ratios = ("native_st_fraction", "calculated_st_fraction", "source_rounded_st_fraction")
            for name, spec in list(table.items()):
                window = name in (*ratios, "st_count", "window_denominator_symbols")
                unit = "st_symbols" if name == "st_count" else "processed_symbols" if name == "window_denominator_symbols" else spec[2]
                table[name] = (*spec[:2], unit, "o_glyco_reported_window" if window else "o_glyco_retained_printed_row",
                    (base + "/cells/st_count", base + "/cells/window_denominator_symbols") if name in ratios else ())
            for name, path, typ, unit, population in (
                    ("row_ordinal", "/row_ordinal", "count", "zero_based_row_ordinal", "o_glyco_retained_printed_row"),
                    ("residue", "/native_values/residue", "text", "literal_native_symbols", "o_glyco_retained_printed_row"),
                    ("native_st_fraction_token", "/native_values/st_fraction_token", "text", "literal_native_number_token", "o_glyco_reported_window"),
                    ("window_start_1based", "/native_values/window_start_1based", "count", "one_based_processed_symbol_position", "o_glyco_reported_window"),
                    ("window_end_1based", "/native_values/window_end_1based", "count", "one_based_inclusive_processed_symbol_position", "o_glyco_reported_window"),
                    ("source_intervals", "/cells/source_intervals", "o_glycosylation_source_path", "per_segment_nt_aa_or_symbol", "o_glyco_retained_printed_row"),
                    ("native_line", "/native_line", "text", "literal_native_log_line", "o_glyco_retained_printed_row"),
                    ("operand_symbols", "/cells/operand_symbols", "text", "processed_symbols", "o_glyco_retained_printed_row"),
                    ("order_compatible", "/cells/order_compatible", "bool", "boolean", "o_glyco_retained_printed_row"),
                    ("printed_symbols_match_operand", "/cells/printed_symbols_match_operand", "bool", "boolean", "o_glyco_retained_printed_row"),
                    ("st_center", "/cells/st_center", "bool", "boolean", "o_glyco_retained_printed_row"),
                    ("native_window_interval", "/cells/native_window_interval", "interval", "zero_based_half_open_processed_symbol_indices", "o_glyco_reported_window"),
                    ("expected_clipped_window_interval", "/cells/expected_clipped_window_interval", "interval", "zero_based_half_open_processed_symbol_indices", "o_glyco_expected_source_clipped_window"),
                    ("window_source_intervals", "/cells/window_source_intervals", "o_glycosylation_source_path", "per_segment_nt_aa_or_symbol", "o_glyco_reported_window"),
                    ("window_symbols", "/cells/window_symbols", "text", "processed_symbols", "o_glyco_reported_window"),
                    ("window_symbol_counts", "/cells/window_symbol_counts", "o_glyco_symbol_counts", "processed_symbols", "o_glyco_reported_window"),
                    ("window_matches_source_clipping", "/cells/window_matches_source_clipping", "bool", "boolean", "o_glyco_reported_window"),
                    ("following_proline", "/cells/following_proline", "bool", "boolean", "o_glyco_immediate_following_processed_symbol"),
                    ("following_proline_allowed", "/cells/following_proline_allowed", "bool", "boolean", "o_glyco_immediate_following_processed_symbol"),
                    ("unrounded_threshold_satisfied", "/cells/unrounded_threshold_satisfied", "bool", "boolean", "o_glyco_reported_window"),
                    ("printed_fraction_matches_calculation", "/cells/printed_fraction_matches_calculation", "bool", "boolean", "o_glyco_reported_window")):
                add(name, base + path, typ, unit, population)
    if profile == _PROTEASE_PROFILE:
        if kind == "summary":
            populations = dict(time_point_count="protease_supplied_time_coordinates",
                substrate_count="protease_original_substrate_rows",
                supplied_curve_count="protease_supplied_fluorescence_curve_rows",
                requested_initial_point_count="protease_native_requested_initial_window",
                actual_initial_point_count="protease_actual_sliced_time_indices")
            for name, spec in list(table.items()):
                table[name] = (*spec[:3], populations[name], spec[4])
        elif kind == "protease_covariance":
            spec = table["reported_matrix_entry"]
            table["reported_matrix_entry"] = (spec[0], "protease_native_literal", *spec[2:])
    return table


def _selector_profile(value):
    if value["version"] == SELECTOR_VERSION:
        return _LEGACY_PROFILE
    if value["version"] == N_SELECTOR_VERSION and value["operation"] == OPERATIONS[2]:
        return _N_PROFILE
    if value["version"] == PROTEASE_SELECTOR_VERSION and value["operation"] == OPERATIONS[4]:
        return _PROTEASE_PROFILE
    if value["version"] == PLACEMENT_SELECTOR_VERSION and value["operation"] == OPERATIONS[1]:
        return _PLACEMENT_PROFILE
    require(value["version"] == O_SELECTOR_VERSION and value["operation"] == OPERATIONS[3])
    return _O_PROFILE


def _public_profile(value):
    require(type(value) is dict)
    if value.get("schema") == PUBLIC_VERSION:
        require(value.get("operation") in OPERATIONS)
        return _LEGACY_PROFILE
    if value.get("schema") == N_PUBLIC_VERSION and value.get("operation") == OPERATIONS[2]:
        return _N_PROFILE
    if value.get("schema") == PROTEASE_PUBLIC_VERSION and value.get("operation") == OPERATIONS[4]:
        return _PROTEASE_PROFILE
    if value.get("schema") == PLACEMENT_PUBLIC_VERSION and value.get("operation") == OPERATIONS[1]:
        return _PLACEMENT_PROFILE
    require(value.get("schema") == O_PUBLIC_VERSION and value.get("operation") == OPERATIONS[3])
    return _O_PROFILE


def validate_molecular_sequence_result_selector(value):
    value = copy_json(value)
    closed(value, ("version", "mode", "operation", "saved_sheet_ref", "rows", "return_files"))
    profile = _selector_profile(value)
    require(value["mode"] in MODES and value["operation"] in OPERATIONS)
    require(value["saved_sheet_ref"] is None if value["mode"] == "original_attempt" else reference(value["saved_sheet_ref"]))
    require(type(value["rows"]) is list and type(value["return_files"]) is list and all(role in FILE_ROLES for role in value["return_files"])
        and len(set(value["return_files"])) == len(value["return_files"]))
    seen = set()
    for row in value["rows"]:
        closed(row, ("row_id", "fields")); row_id(row["row_id"])
        key = canonical(row["row_id"]); require(key not in seen); seen.add(key)
        fields = row["fields"]; table = field_table(value["operation"], row["row_id"], profile=profile)
        require(type(fields) is list and bool(fields) and all(type(f) is str and f in table for f in fields) and len(fields) == len(set(fields)))
    return value


MISSING = object()


def pointer(document, path):
    current = document
    for part in path.split("/")[1:]:
        key = part.replace("~1", "/").replace("~0", "~")
        if type(current) is dict and key in current:
            current = current[key]
        elif type(current) is list and re.fullmatch("0|[1-9][0-9]*", key) and int(key) < len(current):
            current = current[int(key)]
        else:
            return MISSING
    return current


def valid_type(value, typ):
    if typ in ("placement_native_json", "placement_mapping", "placement_source_path"):
        return _valid_placement_literal(value, typ)
    if typ == "number": return type(value) is int or type(value) is float and math.isfinite(value)
    if typ in ("count", "int"): return type(value) is int and (typ == "int" or value >= 0)
    if typ == "bool": return type(value) is bool
    if typ == "text": return type(value) is str
    if typ == "interval": return type(value) is list and len(value) == 2 and all(type(v) is int and v >= 0 for v in value) and value[0] <= value[1]
    if typ == "frame": return type(value) is int and value in (-3, -2, -1, 1, 2, 3)
    if typ == "strand": return value in ("+", "-") and type(value) is str
    if typ == "compatibility": return type(value) is str and value in ("compatible", "incompatible", "unknown")
    if typ == "orf_native_row":
        if type(value) is list and len(value) == len(_ORF_NATIVE_FIELDS):
            fields = value
        elif type(value) is dict and set(value) == set(_ORF_NATIVE_FIELDS):
            fields = [value[name] for name in _ORF_NATIVE_FIELDS]
        else:
            return False
        # These are literal native fields, not another interval, alphabet or
        # translation check. Native coordinate conflicts remain inspectable.
        return (type(fields[0]) is str and type(fields[1]) is str
            and type(fields[2]) is int and type(fields[3]) is int
            and valid_type(fields[4], "strand") and valid_type(fields[5], "frame"))
    if typ == "orf_source_path":
        if type(value) is not list:
            return False
        # A saved empty traversal is distinct from unavailable (null). The
        # existing path validator requires a nonempty path, so handle only
        # this explicit empty case here; retain its ordered segments otherwise.
        if not value:
            return True
        try:
            path_length(value)
        except (ValueError, TypeError, KeyError):
            return False
        return all(row["unit"] in ("nt", "symbol") for row in value)
    if typ in ("n_glycosylation_source_path", "o_glycosylation_source_path"):
        try:
            path_length(value)
        except (ValueError, TypeError, KeyError):
            return False
        return True
    if type(typ) is str and typ.startswith(("n_glyco_", "o_glyco_")):
        return _valid_glyco_literal(value, typ)
    if type(typ) is str and typ.startswith("protease_"):
        return _valid_protease_literal(value, typ)
    if type(typ) is tuple: return type(value) is str and value in typ
    if typ == "ordinals": return type(value) is list and all(type(v) is int and v >= 0 for v in value)
    if typ == "fit_codes": return type(value) is list and all(type(v) is str and v in FIT_CODES for v in value)
    return False


def _valid_placement_literal(value, typ):
    """Validate copied cells, never interpret native literals or grant refs."""
    def native(item, depth=0):
        kind = type(item)
        if item is None or kind in (str, int, bool):
            return True
        if kind is float:
            return math.isfinite(item)
        if depth >= PLACEMENT_MAX_NESTING:
            return False
        if kind is list:
            return all(native(child, depth + 1) for child in item)
        if kind is dict:
            return all(type(key) is str and native(child, depth + 1) for key, child in item.items())
        return False
    if typ == "placement_native_json":
        return native(value)
    if typ == "placement_source_path":
        if type(value) is not list or any(type(row) is not dict or any(type(key) is not str for key in row) for row in value):
            return False
        if not value:
            return True
        try:
            path_length(value)
        except (ValueError, TypeError, KeyError):
            return False
        return all(row["unit"] in ("nt", "symbol") for row in value)
    if typ == "placement_mapping":
        if type(value) is not dict or set(value) != {"state", "intervals"}:
            return False
        if value["state"] == "available":
            return _valid_placement_literal(value["intervals"], "placement_source_path")
        return value["state"] in ("unavailable", "incompatible") and value["intervals"] is None
    return False


def _validate_placement_copy_inputs(value):
    """Reject non-JSON selected literals before canonical DTO copying can coerce."""
    if (type(value) is not dict or value.get("schema") != PLACEMENT_PUBLIC_VERSION
            or value.get("operation") != OPERATIONS[1] or type(value.get("rows")) is not list):
        return
    types = {"native_group": "placement_native_json", "native_hit": "placement_native_json",
        "native_triple": "placement_native_json", "target_mapping": "placement_mapping",
        "primer_mapping": "placement_mapping", "target_source_intervals": "placement_source_path",
        "primer_source_intervals": "placement_source_path"}
    for row in value["rows"]:
        if type(row) is dict and type(row.get("field")) is str and row["field"] in types and row.get("value_state") == "stored_value":
            require(valid_type(row.get("value"), types[row["field"]]), "molecular_sequence_placement_literal_invalid")


def stored(document, path, typ, source):
    file = source["file"]
    available = file is not None or source["state"] == "produced_unretained"
    value = pointer(document, path) if document is not None and available else MISSING
    state = "source_unavailable" if not available else "path_missing" if value is MISSING else "stored_null" if value is None else "stored_value" if valid_type(value, typ) else "invalid_type"
    return dict(value_state=state, value=deepcopy(value) if state == "stored_value" else None,
        source_ref=None if file is None else file["artifact_ref"], source_pointer=path, source_state=source["state"])


def _qualifiers(operation, identity, sheet, components, sources, specifications=None):
    result = {"schema": "molecular_sequence_scientific_qualifiers_v1", "operation": operation,
        "component_schema": None if components is None else components.get("schema"), "states": {}}
    def add(name, path, typ, role="components"):
        if specifications is not None: specifications[name] = (path, typ, role)
        result["states"][name] = stored(sheet if role == "sheet" else components, path, typ, sources[role])
    if operation in OPERATIONS[:2]:
        add("component_status", "/status", ("complete", "partial")); add("native_outcome", "/native_outcome", ("completed", "failed", "partial", "truncated", "unknown"))
    if operation == OPERATIONS[0]:
        result["interpretation"] = "literal_orf_retained_rows_not_gene_prediction"
        if identity["kind"] == "orf":
            base = "/rows/" + str(identity["row_index"])
            add("source_definition", base + "/source_definition", "compatibility"); add("translation_state", base + "/translation/state", "compatibility")
            add("early_ambiguity_termination", base + "/translation/early_ambiguity_termination", "bool")
        add("reported_row_count", "/summary/reported_row_count", "count"); add("usable_saved_row_count", "/summary/usable_saved_row_count", "count")
        add("retained_string_denominator", "/summary/retained_length_denominator_rows", "count")
    elif operation == OPERATIONS[1]:
        result["interpretation"] = "retained_literal_placements_not_exhaustiveness_or_pcr_prediction"
        if identity["kind"] in ("placement_hit", "placement_mismatch"):
            base = f'/groups/{identity["group_ordinal"]}/hits/{identity["native_hit_ordinal"]}'
            add("interpretation", base + "/interpretation", ("canonical_dna_window", "empty_primer_unsupported", "noncanonical_literal_only", "unavailable"))
            add("source_acceptance", base + "/source_acceptance", ("compatible", "incompatible", "unsupported", "unavailable"))
            add("mismatch_list_matches_full_operands", base + "/mismatch_list_matches_full_operands", "bool")
            for name in ("target", "primer"): add(name + "_mapping_state", base + "/" + name + "_mapping/state", ("available", "unavailable", "incompatible"))
        add("known_native_hit_list_count", "/summary/known_native_hit_list_count", "count")
        add("checked_mismatch_denominator_hits", "/summary/mismatch_count_denominator_hits", "count")
    elif operation in OPERATIONS[2:4]:
        result["interpretation"] = "literal_N_sequon_not_occupancy" if operation == OPERATIONS[2] else "source_ST_density_heuristic_not_occupancy_or_calibrated_probability"
        add("component_status", "/status", ("complete", "partial", "failed")); add("parameter_compatible", "/parameters/compatible", "bool")
        for name in ("native_log_complete", "native_report_complete", "scan_exhaustiveness_verified"): add(name, "/summary/" + name, "bool")
        if identity["kind"] == "glycosylation_site":
            base = "/rows/" + str(identity["row_ordinal"])
            add("source_compatible", base + "/source_compatible", "bool")
            for name in ("printed_symbols_match_operand", "window_matches_source_clipping", "following_proline_allowed", "unrounded_threshold_satisfied", "printed_fraction_matches_calculation"):
                if name == "printed_symbols_match_operand" or operation == OPERATIONS[3]: add(name, base + "/cells/" + name, "bool")
    else:
        result["interpretation"] = "observed_native_fit_and_separately_calibrated_physical_quantities"
        reasons = REASONS.get(result["component_schema"], REASONS_COMMON)
        for name, path, typ in (("native_return_outcome", "/native_return/outcome", ("completed", "source_error", "raised", "not_called")),
                ("fit_state", "/fit_components/state", ("present", "qualified", "unavailable")), ("fit_reason", "/fit_components/reason", reasons),
                ("fit_qualification_codes", "/fit_components/qualifications", "fit_codes"), ("complete_population_eligible", "/fit_components/complete_population_eligible", "bool"),
                ("negative_substrate_ordinals", "/population/negative_substrate_ordinals", "ordinals"),
                ("covariance_state", "/fit_components/covariance_state", ("present", "qualified", "unavailable")),
                ("covariance_reason", "/fit_components/covariance_reason", reasons),
                ("native_matrix_symmetry", "/fit_components/covariance_assessment/native_symmetry", ("exact", "asymmetric", "unavailable")),
                ("symmetric_part_PSD", "/fit_components/covariance_assessment/symmetric_part_positive_semidefinite", "bool"),
                ("statistical_covariance_validity", "/fit_components/covariance_assessment/statistical_covariance_validity", ("unestablished",))): add(name, path, typ)
        add("enzyme_basis", "/assay_context/enzyme_basis", ("unknown", "total_enzyme_concentration", "active_site_concentration"), "sheet")
        add("calibration_applicability", "/assay_context/calibration/applicability", ("supported", "unknown", "conflicting", "unsupported"), "sheet")
        if identity["kind"] == "protease_curve": add("curve_state", f'/fit_components/model_rows/{identity["substrate_ordinal"]}/curve_state', ("present", "curve_missing", "invalid_curve_shape", "invalid_curve_values"))
        if identity["kind"] in ("protease_quantity", "protease_fit"):
            bases = [("quantity", "/physical_components/" + identity["quantity"])] if identity["kind"] == "protease_quantity" else [(name, "/fit_components/" + name) for name in ("vmax", "km")]
            for prefix, base in bases:
                for name, suffix, typ in (("state", "/state", ("present", "unavailable")), ("reason", "/reason", reasons),
                        ("unit_state", "/unit_state", ("unknown", "declared_or_derived")), ("unit", "/unit", "text"),
                        ("uncertainty_state", "/uncertainty/state", ("present", "qualified", "unavailable")), ("uncertainty_reason", "/uncertainty/reason", reasons),
                        ("variance_status", "/uncertainty/variance_status", ("estimated", "qualified_reported_matrix_bilinear_estimate")),
                        ("uncertainty_scope", "/uncertainty/scope", ("fit_only_conditional_on_held_calibration_enzyme_and_stoichiometry",)),
                        ("total_uncertainty", "/uncertainty/total_uncertainty", "number"), ("total_uncertainty_reason", "/uncertainty/total_uncertainty_reason", reasons)):
                    add(prefix + "_" + name, base + suffix, typ)
    return result


_N_ISSUE_NAMES = (
    "unknown_parameter", "boolean_parameter_required", "native_integer_unrepresentable",
    "unrecognized_log_line", "duplicate_native_metadata", "original_operand_unknown",
    "supplied_protein_has_noncanonical_symbols", "invalid_supplied_mapping", "normalization_mapping_unavailable",
    "native_header_conflicts_with_operand_or_parameters", "native_total_exceeds_operand_upper_bound",
    "native_log_missing", "native_log_layout_or_count_incomplete", "native_outcome_incomplete",
    "malformed_native_site_row", "site_interval_outside_operand", "native_site_order_or_overlap_conflict",
    "native_site_order_unknown", "native_site_conflicts_with_operand_or_source_rule", "site_checks_unavailable")
_N_ISSUE_DETAILS = {"glycosylation_" + name: detail for name, detail in (
    ("invalid_supplied_mapping", "cause"), ("native_integer_unrepresentable", "native_token"),
    ("supplied_protein_has_noncanonical_symbols", "meaning"))}
_N_METADATA_FIELDS = {"sequence": "sequence_length", "total": "total_count", "remaining": "remaining_count"}
_N_COMPLETENESS_FIELDS = (
    "native_log_complete", "native_report_complete", "scan_exhaustiveness_verified",
    "source_profile_layout_compatible", "native_count_rows_compatible", "native_metadata_matches_operands",
    "native_total_operand_upper_bound", "native_total_within_operand_upper_bound")
_N_CONTEXT_SPEC = {
    "component_status": ("components", "/status", ("complete", "partial", "failed")),
    "parameters": {
        "supplied_allow_overlap": ("components", "/parameters/supplied/allow_overlap", "bool"),
        "source_default_allow_overlap": ("components", "/parameters/source_defaults/allow_overlap", "bool"),
        "requested_allow_overlap": ("components", "/parameters/requested_with_defaults/allow_overlap", "bool"),
        "effective_allow_overlap": ("components", "/parameters/effective/allow_overlap", "bool"),
        "defaulted_keys": ("components", "/parameters/defaulted_keys", "n_glyco_defaulted_keys"),
        "compatible": ("components", "/parameters/compatible", "bool")},
    "input": {
        "input_ref": ("sheet", "/inputs/input_ref", "text"),
        "original_operand_known": ("sheet", "/source_normalization/original_operand_known", "bool"),
        "native_outcome": ("sheet", "/inputs/native_outcome", ("completed", "partial", "failed"))},
    "mapping": {
        "available": ("sheet", "/mapping/available", "bool"),
        "reason": ("sheet", "/mapping/reason", ("not_supplied", "original_operand_unknown", "invalid_supplied_mapping", "unicode_uppercase_expansion")),
        "normalization_preserves_positions": ("sheet", "/mapping/normalization_preserves_positions", "bool")},
    "native": {
        "metadata_occurrences": ("sheet", "/native/metadata_occurrences", "n_glyco_metadata_occurrences"),
        "selected_metadata": ("sheet", "/native/selected_metadata", "n_glyco_selected_metadata")},
    "completeness": ("sheet", "/completeness", "n_glyco_completeness"),
    "component_issues": ("components", "/issues", "n_glyco_issues")}
_N_CONTEXT_VERSION = "n_glycosylation_public_context_v1"
_O_CONTEXT_VERSION = "o_glycosylation_public_context_v1"
_O_CONTEXT_SPEC = {
    **_N_CONTEXT_SPEC,
    "parameters": {
        **{prefix + "_" + name: ("components", "/parameters/" + path + "/" + name, typ)
            for prefix, path in (("supplied", "supplied"), ("source_default", "source_defaults"),
                ("requested", "requested_with_defaults"), ("effective", "effective"))
            for name, typ in (("window", "int"), ("min_st_fraction", "number"), ("disallow_proline_next", "bool"))},
        "defaulted_keys": ("components", "/parameters/defaulted_keys", "o_glyco_defaulted_keys"),
        "compatible": ("components", "/parameters/compatible", "bool")},
    "native": {
        "metadata_occurrences": ("sheet", "/native/metadata_occurrences", "o_glyco_metadata_occurrences"),
        "selected_metadata": ("sheet", "/native/selected_metadata", "o_glyco_selected_metadata")},
    "completeness": ("sheet", "/completeness", "o_glyco_completeness"),
    "component_issues": ("components", "/issues", "o_glyco_issues")}
_GLYCO_PROFILES = {
    _N_PROFILE: dict(context_version=_N_CONTEXT_VERSION, context_spec=_N_CONTEXT_SPEC, prefix="n_glyco_",
        defaulted_keys=("allow_overlap",), issue_names=_N_ISSUE_NAMES, issue_details=_N_ISSUE_DETAILS,
        issue_meanings={"glycosylation_supplied_protein_has_noncanonical_symbols":
            "literal source rules retained; no biological alphabet repair"},
        metadata_fields={kind: {field: ("count", True)} for kind, field in _N_METADATA_FIELDS.items()}),
    _O_PROFILE: dict(context_version=_O_CONTEXT_VERSION, context_spec=_O_CONTEXT_SPEC, prefix="o_glyco_",
        defaulted_keys=("window", "min_st_fraction", "disallow_proline_next"),
        issue_names=(*_N_ISSUE_NAMES, "integer_window_required", "numeric_threshold_required",
            "threshold_outside_documented_domain", "finite_native_number_required", "native_window_outside_operand"),
        issue_details={**_N_ISSUE_DETAILS, "glycosylation_finite_native_number_required": "native_token",
            "glycosylation_threshold_outside_documented_domain": "meaning"},
        issue_meanings={"glycosylation_supplied_protein_has_noncanonical_symbols":
            "literal source rules retained; no biological alphabet repair",
            "glycosylation_threshold_outside_documented_domain":
            "finite supplied source arithmetic retained; native source performs no domain rejection"},
        metadata_fields={"sequence": {"sequence_length": ("count", True), "window": ("count", True),
            "threshold_token": ("text", False), "threshold": ("number", True)},
            "total": {"total_count": ("count", True)}, "remaining": {"remaining_count": ("count", True)}})}


def _validate_glyco_issue(value, profile):
    spec = _GLYCO_PROFILES[profile]
    require(type(value) is dict and value.get("code") in tuple("glycosylation_" + name for name in spec["issue_names"]))
    detail = spec["issue_details"].get(value["code"])
    closed(value, ("code", "field", *((detail,) if detail else ())))
    require(type(value["field"]) is str and value["field"].startswith("/"))
    if detail:
        require(type(value[detail]) is str)
        if detail == "meaning":
            require(value[detail] == spec["issue_meanings"][value["code"]])


def _valid_glyco_literal(value, typ):
    profile = _N_PROFILE if typ.startswith("n_glyco_") else _O_PROFILE
    spec = _GLYCO_PROFILES[profile]
    kind = typ[len(spec["prefix"]):]
    try:
        if kind == "defaulted_keys":
            require(type(value) is list and all(type(key) is str and key in spec["defaulted_keys"] for key in value)
                and value == [key for key in spec["defaulted_keys"] if key in value])
        elif kind == "issues":
            require(type(value) is list)
            for issue in value: _validate_glyco_issue(issue, profile)
        elif kind in ("metadata_occurrences", "selected_metadata"):
            def metadata_values(kind, values):
                fields = spec["metadata_fields"][kind]
                closed(values, fields)
                for name, (typ, nullable) in fields.items():
                    require(values[name] is None and nullable or valid_type(values[name], typ))
            if kind == "metadata_occurrences":
                require(type(value) is list)
                for row in value:
                    closed(row, ("kind", "line_number", "native_line", "values"))
                    require(row["kind"] in spec["metadata_fields"] and type(row["line_number"]) is int
                        and row["line_number"] >= 1 and type(row["native_line"]) is str)
                    metadata_values(row["kind"], row["values"])
            else:
                closed(value, spec["metadata_fields"])
                for kind, values in value.items():
                    if values is not None: metadata_values(kind, values)
        elif kind == "completeness":
            closed(value, _N_COMPLETENESS_FIELDS)
            for name, item in value.items():
                if name == "native_total_operand_upper_bound": require(item is None or valid_type(item, "count"))
                elif name in ("native_metadata_matches_operands", "native_total_within_operand_upper_bound"):
                    require(item is None or type(item) is bool)
                else: require(type(item) is bool)
        elif kind == "symbol_counts" and profile == _O_PROFILE:
            require(type(value) is dict and all(type(key) is str and len(key) == 1
                and valid_type(count, "count") for key, count in value.items()))
        else:
            return False
    except (ValueError, TypeError, KeyError):
        return False
    return True


def _glyco_context(sheet, components, sources, profile):
    spec = _GLYCO_PROFILES[profile]
    def build(spec):
        if type(spec) is dict: return {key: build(child) for key, child in spec.items()}
        role, path, typ = spec
        return stored(sheet if role == "sheet" else components, path, typ, sources[role])
    result = dict(schema=spec["context_version"], **build(spec["context_spec"]))
    available = components is not None and (sources["components"]["file"] is not None
        or sources["components"]["state"] == "produced_unretained")
    if available and type(components.get("rows")) is list:
        require(all(type(row) is dict for row in components["rows"]))
    result["row_issues"] = None if not available or type(components.get("rows")) is not list else [
        dict(row_ordinal=row.get("row_ordinal"), issues=stored(components, f"/rows/{index}/issues", spec["prefix"] + "issues", sources["components"]))
        for index, row in enumerate(components["rows"])]
    return result


def _validate_glyco_context(value, public, profile):
    spec = _GLYCO_PROFILES[profile]
    closed(value, ("schema", *spec["context_spec"], "row_issues"))
    require(value["schema"] == spec["context_version"])
    def check(cell, spec):
        if type(spec) is dict:
            closed(cell, spec)
            for key, child in spec.items(): check(cell[key], child)
            return
        role, path, typ = spec
        _validate_stored(cell)
        require(cell["source_pointer"] == path and cell["source_ref"] == public["source_" + role + "_ref"]
            and cell["source_state"] == public["source_states"][role]
            and (cell["value_state"] != "stored_value" or valid_type(cell["value"], typ)))
    for key, item in spec["context_spec"].items(): check(value[key], item)
    require(value["row_issues"] is None or type(value["row_issues"]) is list)
    for index, row in enumerate(value["row_issues"] or []):
        closed(row, ("row_ordinal", "issues"))
        require(type(row["row_ordinal"]) is int and row["row_ordinal"] == index)
        check(row["issues"], ("components", f"/rows/{index}/issues", spec["prefix"] + "issues"))


_PROTEASE_ISSUE_CODES = ("one_dimensional_array_required", "curve_rows_required",
    "finite_binary64_measurement_required", "curve_missing", "invalid_curve_shape", "invalid_curve_values",
    "curve_substrate_population_mismatch", "distinct_initial_time_coordinates_unavailable",
    "empty_substrate_population", "negative_substrate_concentration")
_PROTEASE_CURVE_STATES = ("present", "curve_missing", "invalid_curve_shape", "invalid_curve_values")
_PROTEASE_COUNT_FIELDS = ("time_point_count", "substrate_count", "supplied_curve_count",
    "requested_initial_point_count", "actual_initial_point_count")


def _valid_protease_literal(value, typ):
    """Validate literal public operands, never calculate or authenticate custody."""
    try:
        copy_json(value)
        if typ == "protease_native_literal":
            return True
        if typ == "protease_unestimated":
            return False  # These source-owned quantities are always null, never estimated.
        if typ == "protease_observation_count":
            return type(value) is int and value in (0, 1)
        if typ == "protease_parameter_order":
            return type(value) is list and value == ["vmax", "km"]
        if typ == "protease_parameter_units":
            return type(value) is list and len(value) == 2 and all(item is None or type(item) is str for item in value)
        if typ in ("protease_texts", "protease_nullable_texts"):
            return type(value) is list and all(type(item) is str or
                typ == "protease_nullable_texts" and item is None for item in value)
        if typ == "protease_assay_context":
            from .protease_kinetics_measurements import _context
            return type(value) is dict and _context(value) == value
        if typ == "protease_qualifications":
            from .protease_kinetics_measurements import QUALIFICATIONS
            return type(value) is list and value == list(QUALIFICATIONS)
        if typ == "protease_issues":
            require(type(value) is list)
            for issue in value:
                closed(issue, ("code", "field"))
                require(issue["code"] in _PROTEASE_ISSUE_CODES and type(issue["field"]) is str
                    and issue["field"].startswith("/measurements/"))
            return True
        if typ == "protease_population":
            closed(value, (*_PROTEASE_COUNT_FIELDS, "rows", "complete_supplied_curve_population",
                "negative_substrate_ordinals", "replicate_independence_inferred"))
            require(all(item is None or type(item) is int and item >= 0 for item in
                (value[name] for name in _PROTEASE_COUNT_FIELDS)))
            require(type(value["complete_supplied_curve_population"]) is bool
                and value["replicate_independence_inferred"] is False
                and valid_type(value["negative_substrate_ordinals"], "ordinals") and type(value["rows"]) is list)
            for index, row in enumerate(value["rows"]):
                closed(row, ("substrate_ordinal", "curve_ordinal", "curve_state", "native_vector_ordinal",
                    "initial_window_indices", "replicate_id"))
                require(type(row["substrate_ordinal"]) is int and row["substrate_ordinal"] == index
                    and type(row["native_vector_ordinal"]) is int and row["native_vector_ordinal"] == index
                    and (row["curve_ordinal"] is None or type(row["curve_ordinal"]) is int and row["curve_ordinal"] >= 0)
                    and row["curve_state"] in _PROTEASE_CURVE_STATES
                    and valid_type(row["initial_window_indices"], "ordinals")
                    and (row["replicate_id"] is None or type(row["replicate_id"]) is str))
            return True
        if typ == "protease_covariance_assessment":
            closed(value, ("schema", "native_symmetry", "symmetric_part_positive_semidefinite",
                "assessment_arithmetic", "propagation_basis", "statistical_covariance_validity", "qualifications"))
            require(value["schema"] == "protease_covariance_assessment_v1"
                and value["native_symmetry"] in ("exact", "asymmetric", "unavailable")
                and (value["symmetric_part_positive_semidefinite"] is None
                    or type(value["symmetric_part_positive_semidefinite"]) is bool)
                and value["assessment_arithmetic"] == "exact_rational_retained_entries"
                and value["propagation_basis"] == "symmetric_bilinear_part_of_observed_native_matrix"
                and value["statistical_covariance_validity"] == "unestablished"
                and type(value["qualifications"]) is list and all(item ==
                    "asymmetric_reported_matrix_bilinear_estimate_not_verified_statistical_covariance"
                    for item in value["qualifications"]))
            require(value["qualifications"] == (["asymmetric_reported_matrix_bilinear_estimate_not_verified_statistical_covariance"]
                if value["native_symmetry"] == "asymmetric" else []))
            return True
    except (ValueError, TypeError, KeyError, OverflowError):
        return False
    return False


def _protease_quantity_context(base):
    """Only original qualification paths; numerical values stay in selected rows."""
    reason = REASONS["protease_kinetics_components_v2"]
    result = {name: ("components", base + "/" + name, typ) for name, typ in (
        ("state", ("present", "unavailable")), ("reason", reason), ("unit", "text"),
        ("unit_state", ("unknown", "declared_or_derived")),
        ("origin", ("native_fitted", "derived_saved_native_fit")), ("formula_id", "text"),
        ("input_fields", "protease_texts"))}
    result["uncertainty"] = {name: ("components", base + "/uncertainty/" + name, typ) for name, typ in (
        ("state", ("present", "qualified", "unavailable")), ("reason", reason), ("method", "text"),
        ("parameter_order", "protease_parameter_order"), ("variance_status", ("estimated", "qualified_reported_matrix_bilinear_estimate")),
        ("covariance_basis", ("symmetric_bilinear_part_of_observed_native_matrix",)),
        ("native_matrix_symmetry", ("exact", "asymmetric", "unavailable")),
        ("statistical_covariance_validity", ("unestablished",)), ("qualifications", "protease_texts"),
        ("scope", ("fit_only_conditional_on_held_calibration_enzyme_and_stoichiometry",)),
        ("total_uncertainty", "protease_unestimated"), ("total_uncertainty_reason", reason),
        ("standard_uncertainty_unit", "text"), ("variance_unit", "text"))}
    return result


_PROTEASE_CONTEXT_SPEC = {
    "assay": ("sheet", "/assay_context", "protease_assay_context"),
    "enzyme_concentration": ("sheet", "/measurements/enzyme_concentration", "number"),
    "method": {name: ("sheet", "/source_method/" + name, typ) for name, typ in (
        ("initial_window", "text"), ("slope_authority", "text"), ("fit_authority", "text"),
        ("parameter_order", "protease_parameter_order"), ("model", "text"), ("p0", "protease_texts"),
        ("bounds", "protease_native_literal"), ("other_fit_options", "text"),
        ("native_unit_claims", "protease_native_literal"))},
    "population": ("sheet", "/population", "protease_population"),
    "native": {
        "call_state": ("sheet", "/native_observation/native_call_state", ("not_started", "returned", "raised")),
        "outcome": ("sheet", "/native_observation/native_record/outcome", ("completed", "source_error", "raised", "not_called")),
        "result_kind": ("sheet", "/native_observation/native_record/result_kind", ("analysis_report", "source_error_string")),
        "observer_state": ("sheet", "/native_observation/observer/state", ("not_started", "observing", "captured", "unavailable", "failed")),
        "selected_call_count": ("sheet", "/native_observation/observer/selected_call_count", "protease_observation_count"),
        "selected_terminal_event_count": ("sheet", "/native_observation/observer/selected_terminal_event_count", "protease_observation_count"),
        "profile_restored": ("sheet", "/native_observation/observer/profile_restored", "bool")},
    "fit": {name: ("components", "/fit_components/" + name, typ) for name, typ in (
        ("state", ("present", "qualified", "unavailable")), ("reason", REASONS["protease_kinetics_components_v2"]),
        ("qualifications", "fit_codes"), ("complete_population_eligible", "bool"),
        ("parameter_order", "protease_parameter_order"), ("model_prediction_reason", REASONS["protease_kinetics_components_v2"]),
        ("residual_sum_squares", "number"), ("residual_degrees_of_freedom", "count"),
        ("native_n_minus_parameter_count_diagnostic", "int"),
        ("residual_degrees_of_freedom_reason", REASONS["protease_kinetics_components_v2"]))},
    "parameters": {name: _protease_quantity_context("/fit_components/" + name) for name in ("vmax", "km")},
    "covariance": {name: ("components", "/fit_components/" + path, typ) for name, path, typ in (
        ("raw_matrix", "covariance", "protease_native_literal"),
        ("parameter_order", "parameter_order", "protease_parameter_order"),
        ("parameter_units", "covariance_parameter_units", "protease_parameter_units"),
        ("state", "covariance_state", ("present", "qualified", "unavailable")),
        ("reason", "covariance_reason", REASONS["protease_kinetics_components_v2"]),
        ("assessment", "covariance_assessment", "protease_covariance_assessment"),
        ("native_diagonal_only_uncertainty", "native_diagonal_only_uncertainty", "protease_native_literal"))},
    "physical": {name: _protease_quantity_context("/physical_components/" + name) for name in QUANTITIES},
    "issues": ("sheet", "/issues", "protease_issues"),
    "qualifications": ("sheet", "/qualifications", "protease_qualifications"),
    "function_probability": ("components", "/function_probability", "protease_unestimated")}


def _protease_context(sheet, components, sources):
    def build(spec):
        if type(spec) is dict: return {key: build(child) for key, child in spec.items()}
        role, path, typ = spec
        return stored(sheet if role == "sheet" else components, path, typ, sources[role])
    return dict(schema=PROTEASE_CONTEXT_VERSION, **build(_PROTEASE_CONTEXT_SPEC))


def _validate_protease_context(value, public):
    closed(value, ("schema", *_PROTEASE_CONTEXT_SPEC))
    require(value["schema"] == PROTEASE_CONTEXT_VERSION)
    def check(cell, spec):
        if type(spec) is dict:
            closed(cell, spec)
            for key, child in spec.items(): check(cell[key], child)
            return
        role, path, typ = spec
        _validate_stored(cell)
        require(cell["source_pointer"] == path and cell["source_ref"] == public["source_" + role + "_ref"]
            and cell["source_state"] == public["source_states"][role]
            and (cell["value_state"] != "stored_value" or valid_type(cell["value"], typ)))
    for key, spec in _PROTEASE_CONTEXT_SPEC.items(): check(value[key], spec)


def _protease_operand_spec(path):
    if path.endswith("/response_per_product_concentration"):
        return "sheet", "calibration_response", None, ["/assay_context/calibration/" + key
            for key in ("signal_unit", "product_concentration_unit")]
    if path == "/measurements/enzyme_concentration":
        return "sheet", "enzyme_concentration", None, ["/assay_context/units/enzyme"]
    if path.endswith("/product_per_cleavage"):
        return "sheet", "product_per_cleavage", "product_per_cleavage", []
    require(path == "/fit_components/km/value")
    return "components", "denominator", None, ["/fit_components/km/unit"]


def _protease_selected_unit(row, context, declared):
    if declared == "stored_parameter_units_product": return "unknown"
    if declared in ("stored_vmax_unit", "stored_km_unit"):
        cell = context["parameters"]["vmax" if declared == "stored_vmax_unit" else "km"]["unit"]
    elif declared in ("stored_quantity_unit", "stored_variance_unit"):
        item = context["physical"][row["row_id"]["quantity"]]
        cell = item["unit"] if declared == "stored_quantity_unit" else item["uncertainty"]["variance_unit"]
    else: return declared
    return cell["value"] if cell["value_state"] == "stored_value" else None


def select_stored_molecular_sequence_values(*, operation, sheet, components, selection, source_files, association=None, calculation=None):
    selection = validate_molecular_sequence_result_selector(selection)
    profile = _selector_profile(selection)
    require(operation == selection["operation"])
    closed(source_files, FILE_ROLES)
    sources = {role: validate_file_state(value) for role, value in source_files.items()}
    schema = None if components is None else components.get("schema")
    require(components is None or type(components) is dict and schema in SCHEMAS[operation][1], "molecular_sequence_component_schema")
    require(sheet is None or type(sheet) is dict and sheet.get("schema") == SCHEMAS[operation][0], "molecular_sequence_sheet_schema")
    if profile == _PROTEASE_PROFILE:
        require(components is None or schema == "protease_kinetics_components_v2", "molecular_sequence_component_schema")
    if profile in _GLYCO_PROFILES:
        require(sheet is None or type(sheet.get("inputs")) is dict and sheet["inputs"].get("operation") == operation,
            "molecular_sequence_sheet_operation")
        require(components is None or components.get("operation") == operation,
            "molecular_sequence_component_operation")
    rows, issues = [], []
    for request in selection["rows"]:
        identity, table = request["row_id"], field_table(operation, request["row_id"], profile=profile)
        qualifiers = _qualifiers(operation, identity, sheet, components, sources)
        for name in request["fields"]:
            path, typ, unit, population, denominator_paths = table[name]
            cell = stored(components, path, typ, sources["components"])
            if unit == "stored_quantity_unit": unit = pointer(components, "/physical_components/" + identity["quantity"] + "/unit")
            elif unit == "stored_variance_unit": unit = pointer(components, "/physical_components/" + identity["quantity"] + "/uncertainty/variance_unit")
            elif unit in ("stored_vmax_unit", "stored_km_unit"): unit = pointer(components, "/fit_components/" + ("km" if unit == "stored_km_unit" else "vmax") + "/unit")
            elif unit == "stored_parameter_units_product": unit = "unknown"  # Raw matrix kept; no multiplication of labels inferred.
            unit = unit if type(unit) is str else None
            if (profile == _PROTEASE_PROFILE and table[name][2] in ("stored_quantity_unit", "stored_variance_unit", "stored_vmax_unit", "stored_km_unit")
                    and sources["components"]["file"] is None and sources["components"]["state"] != "produced_unretained"):
                unit = None
            denominators = []
            for denominator_path in denominator_paths:
                role = "sheet" if denominator_path.startswith(("/assay_context/", "/measurements/")) else "components"
                operand = stored(sheet if role == "sheet" else components, denominator_path,
                    "count" if profile in (_O_PROFILE, _PLACEMENT_PROFILE) else "number", sources[role])
                operand_kind = "numerator" if denominator_path.endswith(("/numerator", "/st_count", "/retained_length_sum_nt")) else "denominator"
                operand_unit = "nt_symbols" if denominator_path.endswith("/retained_length_sum_nt") else "rows" if denominator_path.endswith("/retained_length_denominator_rows") else "symbols" if "/mismatch_fraction/" in denominator_path or denominator_path.endswith(("/st_count", "/window_denominator_symbols")) else None
                if profile == _O_PROFILE:
                    operand_unit = "symbols"
                unit_sources = []
                if denominator_path.endswith("/response_per_product_concentration"):
                    operand_kind = "calibration_response"
                    unit_sources = [stored(sheet, "/assay_context/calibration/" + key, "text", sources["sheet"]) for key in ("signal_unit", "product_concentration_unit")]
                elif denominator_path == "/measurements/enzyme_concentration":
                    operand_kind = "enzyme_concentration"; unit_sources = [stored(sheet, "/assay_context/units/enzyme", "text", sources["sheet"])]
                elif denominator_path.endswith("/product_per_cleavage"):
                    operand_kind, operand_unit = "product_per_cleavage", "product_per_cleavage"
                elif denominator_path == "/fit_components/km/value":
                    unit_sources = [stored(components, "/fit_components/km/unit", "text", sources["components"])]
                denominators.append(dict(**operand, kind=operand_kind, unit=operand_unit, unit_sources=unit_sources))
            rows.append(dict(row_id=deepcopy(identity), field=name, **cell, unit=unit, population_id=population,
                denominators=denominators, scientific_qualifiers=deepcopy(qualifiers)))
            if cell["value_state"] in ("path_missing", "invalid_type"):
                issues.append(failure("selected_path_missing" if cell["value_state"] == "path_missing" else "selected_type_invalid",
                    "selection", role="components", row_id=identity, source_ref=cell["source_ref"], source_pointer=path))
    public = dict(schema={_LEGACY_PROFILE: PUBLIC_VERSION, _N_PROFILE: N_PUBLIC_VERSION, _O_PROFILE: O_PUBLIC_VERSION,
        _PROTEASE_PROFILE: PROTEASE_PUBLIC_VERSION, _PLACEMENT_PROFILE: PLACEMENT_PUBLIC_VERSION}[profile], operation=operation, source_kind="original_stored" if selection["mode"] == MODES[0] else "selected_saved_calculation",
        source_sheet_ref=None if sources["sheet"]["file"] is None else sources["sheet"]["file"]["artifact_ref"],
        source_components_ref=None if sources["components"]["file"] is None else sources["components"]["file"]["artifact_ref"],
        source_states={role: sources[role]["state"] for role in ("sheet", "components")}, components_schema=schema,
        original_attempt_association="unavailable" if association is None else association["state"], rows=rows, failures=issues)
    if profile in _GLYCO_PROFILES: public["context"] = _glyco_context(sheet, components, sources, profile)
    if profile == _PROTEASE_PROFILE: public["context"] = _protease_context(sheet, components, sources)
    return dict(schema={_LEGACY_PROFILE: PROJECTION_VERSION, _N_PROFILE: N_PROJECTION_VERSION, _O_PROFILE: O_PROJECTION_VERSION,
        _PROTEASE_PROFILE: PROTEASE_PROJECTION_VERSION, _PLACEMENT_PROFILE: PLACEMENT_PROJECTION_VERSION}[profile], selector=selection, source_files=sources, association=deepcopy(association),
        calculation=deepcopy(calculation), public=public)


def validate_molecular_sequence_projection(value):
    closed(value, ("schema", "selector", "source_files", "association", "calculation", "public"))
    selector = validate_molecular_sequence_result_selector(value["selector"])
    profile = _selector_profile(selector)
    require(value["schema"] == {_LEGACY_PROFILE: PROJECTION_VERSION, _N_PROFILE: N_PROJECTION_VERSION, _O_PROFILE: O_PROJECTION_VERSION,
        _PROTEASE_PROFILE: PROTEASE_PROJECTION_VERSION, _PLACEMENT_PROFILE: PLACEMENT_PROJECTION_VERSION}[profile]
        and _public_profile(value["public"]) == profile)
    closed(value["source_files"], FILE_ROLES)
    for source in value["source_files"].values(): validate_file_state(source)
    validate_molecular_sequence_fact_values(PROJECTION_SOURCE, [value["public"]], allow_unretained=True)
    require(value["public"]["operation"] == selector["operation"])
    for role in ("sheet", "components"):
        source = value["source_files"][role]
        require(value["public"]["source_states"][role] == source["state"] and value["public"]["source_" + role + "_ref"] ==
            (None if source["file"] is None else source["file"]["artifact_ref"]))
    expected = [(row["row_id"], field) for row in selector["rows"] for field in row["fields"]]
    require([(row["row_id"], row["field"]) for row in value["public"]["rows"]] == expected)
    return copy_json(value)


def _validate_stored(value):
    closed(value, ("value_state", "value", "source_ref", "source_pointer", "source_state"))
    require(value["value_state"] in VALUE_STATES and value["source_state"] in FILE_STATES)
    require(value["source_ref"] is None or reference(value["source_ref"]))
    require(type(value["source_pointer"]) is str and value["source_pointer"].startswith("/"))
    require(value["value_state"] == "stored_value" or value["value"] is None)
    require((value["source_ref"] is not None) == (value["source_state"] in ("retained", "retained_undeclared")))
    require(value["source_state"] in ("retained", "retained_undeclared", "produced_unretained") or value["value_state"] == "source_unavailable")


def validate_molecular_sequence_fact_values(source, rows, *, allow_unretained=False):
    if source == PROJECTION_SOURCE and type(rows) is list:
        for value in rows:
            _validate_placement_copy_inputs(value)
    rows = copy_json(rows)
    require(source in FACT_SOURCES and type(rows) is list)
    for value in rows:
        require(type(value) is dict)
        if source == FAILURE_SOURCE:
            require(value.get("version") != "molecular_sequence_supplied_failure_v1", "private_supplied_failure_not_public")
            if value.get("version") == "molecular_sequence_supplied_failure_v2": validate_supplied_failure(value)
            else: validate_failure(value)
            continue
        if source == SAVED_SOURCE:
            if value.get("version") == "molecular_sequence_retained_file_v2":
                validate_supplied_file_fact(value); continue
            closed(value, ("operation", "role", "artifact_ref", "source_kind", "source_sheet_ref", "components_schema"))
            require(value["operation"] in OPERATIONS and value["role"] in FILE_ROLES and reference(value["artifact_ref"]))
            require(value["source_kind"] in ("original_stored", "selected_saved_calculation") and
                (value["source_sheet_ref"] is None or reference(value["source_sheet_ref"])))
            require(value["components_schema"] is None or value["components_schema"] in SCHEMAS[value["operation"]][1])
            continue
        profile = _public_profile(value)
        closed(value, ("schema", "operation", "source_kind", "source_sheet_ref", "source_components_ref", "source_states",
            "components_schema", "original_attempt_association", "rows", "failures", *(("context",) if profile in (*_GLYCO_PROFILES, _PROTEASE_PROFILE) else ())))
        require(value["source_kind"] in ("original_stored", "selected_saved_calculation"))
        require(value["original_attempt_association"] in ("verified", "unavailable", "conflict"))
        require(all(value[k] is None or reference(value[k]) for k in ("source_sheet_ref", "source_components_ref")))
        closed(value["source_states"], ("sheet", "components")); require(all(s in FILE_STATES for s in value["source_states"].values()))
        require(allow_unretained or "produced_unretained" not in value["source_states"].values())
        require(value["components_schema"] is None or value["components_schema"] in SCHEMAS[value["operation"]][1])
        if profile == _PROTEASE_PROFILE:
            require(value["components_schema"] in (None, "protease_kinetics_components_v2"))
        require(type(value["rows"]) is list and type(value["failures"]) is list)
        if profile == _PROTEASE_PROFILE: _validate_protease_context(value["context"], value)
        if profile == _PLACEMENT_PROFILE:
            placement_mapping_states = {}
        for row in value["rows"]:
            closed(row, ("row_id", "field", "value_state", "value", "source_ref", "source_pointer", "source_state", "unit", "population_id", "denominators", "scientific_qualifiers"))
            table = field_table(value["operation"], row["row_id"], profile=profile); require(row["field"] in table)
            path, typ, _unit, population, _denominators = table[row["field"]]
            require(row["source_pointer"] == path and row["population_id"] == population)
            _validate_stored({k: row[k] for k in ("value_state", "value", "source_ref", "source_pointer", "source_state")})
            require(row["source_ref"] == value["source_components_ref"] and row["source_state"] == value["source_states"]["components"])
            require(row["value_state"] != "stored_value" or valid_type(row["value"], typ))
            require(row["unit"] is None or type(row["unit"]) is str)
            if typ in ("orf_native_row", "orf_source_path"):
                require(row["unit"] == _unit)
            if profile in _GLYCO_PROFILES: require(row["unit"] == _unit)
            if profile == _PLACEMENT_PROFILE:
                require(row["unit"] == _unit and (row["value_state"] != "stored_value" or row["value"] is not None))
            if profile == _PROTEASE_PROFILE:
                require(row["unit"] == _protease_selected_unit(row, value["context"], _unit))
            require(type(row["denominators"]) is list)
            require([r["source_pointer"] for r in row["denominators"]] == list(_denominators))
            for denominator in row["denominators"]:
                closed(denominator, ("value_state", "value", "source_ref", "source_pointer", "source_state", "kind", "unit", "unit_sources"))
                _validate_stored({k: denominator[k] for k in ("value_state", "value", "source_ref", "source_pointer", "source_state")})
                require(denominator["value_state"] != "stored_value" or valid_type(denominator["value"], "count" if profile in (_O_PROFILE, _PLACEMENT_PROFILE) else "number"))
                if profile == _PLACEMENT_PROFILE:
                    numerator = denominator["source_pointer"].endswith("/numerator")
                    require(denominator["source_ref"] == value["source_components_ref"]
                        and denominator["source_state"] == value["source_states"]["components"]
                        and denominator["kind"] == ("numerator" if numerator else "denominator")
                        and denominator["unit"] == ("symbols" if "/mismatch_fraction/" in denominator["source_pointer"] else None)
                        and denominator["unit_sources"] == [])
                if profile == _O_PROFILE:
                    numerator = denominator["source_pointer"].endswith("/st_count")
                    require(denominator["source_ref"] == value["source_components_ref"]
                        and denominator["source_state"] == value["source_states"]["components"]
                        and denominator["kind"] == ("numerator" if numerator else "denominator")
                        and denominator["unit"] == "symbols"
                        and denominator["unit_sources"] == [])
                if profile == _PROTEASE_PROFILE:
                    role, kind, unit, unit_paths = _protease_operand_spec(denominator["source_pointer"])
                    require(denominator["source_ref"] == value["source_" + role + "_ref"]
                        and denominator["source_state"] == value["source_states"][role]
                        and denominator["kind"] == kind and denominator["unit"] == unit
                        and type(denominator["unit_sources"]) is list
                        and all(type(item) is dict and "source_pointer" in item for item in denominator["unit_sources"])
                        and [item["source_pointer"] for item in denominator["unit_sources"]] == unit_paths)
                require(denominator["kind"] in ("numerator", "denominator", "calibration_response", "enzyme_concentration", "product_per_cleavage")
                    and (denominator["unit"] is None or type(denominator["unit"]) is str) and type(denominator["unit_sources"]) is list)
                for unit_source in denominator["unit_sources"]:
                    _validate_stored(unit_source)
                    require(unit_source["value_state"] != "stored_value" or valid_type(unit_source["value"], "text"))
                    if profile == _PROTEASE_PROFILE:
                        require(unit_source["source_ref"] == value["source_" + role + "_ref"]
                            and unit_source["source_state"] == value["source_states"][role])
            qualifier = row["scientific_qualifiers"]
            closed(qualifier, ("schema", "operation", "component_schema", "states", "interpretation"))
            require(qualifier["schema"] == "molecular_sequence_scientific_qualifiers_v1" and qualifier["operation"] == value["operation"]
                and qualifier["component_schema"] == value["components_schema"])
            # Exact names and value types are validated by reconstructing only
            # the qualifier shape with unavailable sources, never a calculator.
            unavailable = {role: empty_file_state() for role in FILE_ROLES}
            specifications = {}
            shape = _qualifiers(value["operation"], row["row_id"], None, {"schema": value["components_schema"]}, unavailable, specifications)
            require(qualifier["interpretation"] == shape["interpretation"] and type(qualifier["states"]) is dict
                and set(qualifier["states"]) == set(shape["states"]))
            for name, cell in qualifier["states"].items():
                _validate_stored(cell)
                path, typ, role = specifications[name]
                require(cell["source_pointer"] == path and cell["source_state"] == value["source_states"][role]
                    and cell["source_ref"] == value["source_" + role + "_ref"])
                require(cell["value_state"] != "stored_value" or valid_type(cell["value"], typ))
                if profile == _PROTEASE_PROFILE and name.endswith("_total_uncertainty"):
                    require(cell["value_state"] != "stored_value")
            if profile == _PLACEMENT_PROFILE and row["row_id"]["kind"] in ("placement_hit", "placement_mismatch"):
                for side in ("target", "primer"):
                    cell = qualifier["states"][side + "_mapping_state"]
                    key = (cell["source_ref"], cell["source_pointer"])
                    require(key not in placement_mapping_states or placement_mapping_states[key] == canonical(cell),
                        "molecular_sequence_placement_mapping_qualifier_conflict")
                    placement_mapping_states[key] = canonical(cell)
                if row["value_state"] == "stored_value":
                    side = row["field"].split("_", 1)[0]
                    if row["field"] in ("target_mapping", "primer_mapping", "target_source_intervals", "primer_source_intervals"):
                        cell = qualifier["states"][side + "_mapping_state"]
                        state = row["value"]["state"] if row["field"].endswith("_mapping") else "available"
                        require(cell["value_state"] == "stored_value" and cell["value"] == state,
                            "molecular_sequence_placement_mapping_association_conflict")
        for issue in value["failures"]: validate_failure(issue)
        if profile in _GLYCO_PROFILES: _validate_glyco_context(value["context"], value, profile)
    return rows


def validate_molecular_sequence_result_worker_plan(value):
    if type(value) is dict and value.get("version") == "molecular_sequence_result_worker_plan_v2":
        return validate_supplied_worker_plan(value)
    closed(value, ("version", "directory", "selector", "source_files", "inputs", "association", "received_sheet_receipt_file", "software", "selected_environment", "policy"))
    require(value["version"] == PLAN_VERSION and type(value["directory"]) is str and value["directory"].startswith("/"))
    require(value["policy"] == {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296})
    from .molecular_sequence_execution_contracts import _software, absolute_path, environment
    absolute_path(value["directory"])
    environment(value["selected_environment"])
    if value["software"] is None:
        require(value["selected_environment"] == {})
    else:
        _software(value["software"])
        require(value["selected_environment"].get("PYTHONHOME") == value["software"]["python_home"]
            and value["selected_environment"].get("PYTHONPATH") == ":".join(value["software"]["import_roots"]))
    selector = validate_molecular_sequence_result_selector(value["selector"])
    closed(value["source_files"], FILE_ROLES)
    for source in value["source_files"].values(): validate_file_state(source)
    require(type(value["inputs"]) is list and len({row["role"] for row in value["inputs"]}) == len(value["inputs"]))
    for row in value["inputs"]:
        closed(row, ("role", "file", "path")); require(row["role"] in FILE_ROLES); file_identity(row["file"])
        require(type(row["path"]) is str and row["path"].startswith("/") and value["source_files"][row["role"]]["file"] == row["file"])
        absolute_path(row["path"])
    require({row["role"] for row in value["inputs"]} == {role for role, source in value["source_files"].items() if source["file"] is not None})
    association = value["association"]
    closed(association, ("state", "reason", "proof_file", "original_identity"))
    require(association["state"] in ("verified", "unavailable", "conflict") and association["reason"] in (None, "scientific_binding_unavailable", "original_attempt_conflict"))
    if association["proof_file"] is not None: file_identity(association["proof_file"])
    if value["received_sheet_receipt_file"] is not None: file_identity(value["received_sheet_receipt_file"])
    if selector["mode"] == MODES[1]:
        require(value["received_sheet_receipt_file"] is not None and value["source_files"]["sheet"]["file"] is not None
            and value["source_files"]["sheet"]["file"]["artifact_ref"] == selector["saved_sheet_ref"])
        require(value["received_sheet_receipt_file"]["format"] == "molecular_sequence_received_sheet_v1"
            and [row["role"] for row in value["inputs"]] == ["sheet"]
            and all(source["file"] is None for role, source in value["source_files"].items() if role != "sheet"))
    return copy_json(value)


def validate_molecular_sequence_result_worker_result(value):
    if type(value) is dict and value.get("version") == "molecular_sequence_result_worker_result_v2":
        return validate_supplied_worker_result(value)
    closed(value, ("version", "plan_sha256", "selector", "outputs", "failures"))
    require(value["version"] == RESULT_VERSION and type(value["plan_sha256"]) is str and re.fullmatch("[0-9a-f]{64}", value["plan_sha256"]) is not None)
    validate_molecular_sequence_result_selector(value["selector"])
    require(type(value["outputs"]) is list and [r["role"] for r in value["outputs"]] == list(OUTPUTS))
    for row in value["outputs"]:
        closed(row, ("role", "declaration")); file_declaration(row["declaration"])
        require(row["declaration"]["relative_path"] == row["role"] + ".json" and row["declaration"]["format"] == "json")
    require(type(value["failures"]) is list)
    for issue in value["failures"]: validate_failure(issue)
    return copy_json(value)


def requested_molecular_sequence_sources(schema):
    require(type(schema) is dict and type(schema.get("properties")) is dict)
    return tuple(source for source in FACT_SOURCES if any(node.get("x-source") == source for node in schema["properties"].values()))


def select_molecular_sequence_return_facts(groups, *, schema):
    return {source: validate_molecular_sequence_fact_values(source, groups.get(source, [])) for source in requested_molecular_sequence_sources(schema)}


def _glyco_literal_schema(typ, *, obj, nullable, arr, typed):
    profile = _N_PROFILE if typ.startswith("n_glyco_") else _O_PROFILE
    spec = _GLYCO_PROFILES[profile]
    kind = typ[len(spec["prefix"]):]
    text = {"type": "string"}
    if kind == "defaulted_keys":
        if profile == _N_PROFILE:
            return {"type": "array", "maxItems": 1, "items": {"type": "string", "const": "allow_overlap"}}
        return {"type": "array", "maxItems": 3, "uniqueItems": True,
            "items": {"type": "string", "enum": list(spec["defaulted_keys"])}}
    if kind == "issues":
        variants = []
        for name in spec["issue_names"]:
            code = "glycosylation_" + name
            fields = {"code": {"type": "string", "const": code}, "field": {"type": "string", "pattern": "^/"}}
            detail = spec["issue_details"].get(code)
            if detail:
                fields[detail] = ({"type": "string", "const": spec["issue_meanings"][code]}
                    if detail == "meaning" else deepcopy(text))
            variants.append(obj(fields))
        return arr({"anyOf": variants})
    if kind in ("metadata_occurrences", "selected_metadata"):
        values = {name: obj({field: nullable(typed(typ)) if optional else typed(typ)
            for field, (typ, optional) in fields.items()}) for name, fields in spec["metadata_fields"].items()}
        if kind == "selected_metadata": return obj({kind: nullable(item) for kind, item in values.items()})
        return arr({"anyOf": [obj({"kind": {"type": "string", "const": kind},
            "line_number": {"type": "integer", "minimum": 1}, "native_line": deepcopy(text), "values": item})
            for kind, item in values.items()]})
    if kind == "completeness":
        return obj({name: nullable(typed("count")) if name == "native_total_operand_upper_bound" else
            nullable(typed("bool")) if name in ("native_metadata_matches_operands", "native_total_within_operand_upper_bound") else
            typed("bool") for name in _N_COMPLETENESS_FIELDS})
    if kind == "symbol_counts" and profile == _O_PROFILE:
        return {"type": "object", "propertyNames": {"type": "string", "minLength": 1, "maxLength": 1},
            "additionalProperties": typed("count")}
    require(False)


def _glyco_context_schema(profile, *, obj, nullable, arr, stored_schema):
    spec = _GLYCO_PROFILES[profile]
    def build(spec):
        if type(spec) is dict: return obj({key: build(child) for key, child in spec.items()})
        return stored_schema(spec[2])
    fields = {"schema": {"type": "string", "const": spec["context_version"]},
        **{key: build(item) for key, item in spec["context_spec"].items()}}
    fields["row_issues"] = nullable(arr(obj({"row_ordinal": {"type": "integer", "minimum": 0},
        "issues": stored_schema(spec["prefix"] + "issues")})))
    return obj(fields)


def _protease_literal_schema(typ, *, obj, nullable, arr):
    text = {"type": "string"}
    count = {"type": "integer", "minimum": 0}
    if typ == "protease_native_literal":
        return {"anyOf": [{"type": kind} for kind in ("null", "boolean", "number", "string", "array", "object")],
            "description": "Unchanged finite JSON native literal, including malformed matrix structure and explicit nonfinite tokens; not a finite measurement or verified statistical covariance."}
    if typ == "protease_unestimated":
        return {"type": "null", "description": "The existing scientific owner does not estimate this quantity."}
    if typ == "protease_observation_count": return {"type": "integer", "enum": [0, 1]}
    if typ == "protease_parameter_order": return {"type": "array", "const": ["vmax", "km"]}
    if typ == "protease_parameter_units": return {"type": "array", "minItems": 2, "maxItems": 2, "items": nullable(text)}
    if typ in ("protease_texts", "protease_nullable_texts"):
        return arr(nullable(text) if typ == "protease_nullable_texts" else text)
    if typ == "protease_qualifications":
        from .protease_kinetics_measurements import QUALIFICATIONS
        return {"type": "array", "const": list(QUALIFICATIONS)}
    if typ == "protease_issues":
        return arr(obj({"code": {"type": "string", "enum": list(_PROTEASE_ISSUE_CODES)},
            "field": {"type": "string", "pattern": "^/measurements/"}}))
    if typ == "protease_population":
        row = obj({"substrate_ordinal": count, "curve_ordinal": nullable(count),
            "curve_state": {"type": "string", "enum": list(_PROTEASE_CURVE_STATES)},
            "native_vector_ordinal": count, "initial_window_indices": arr(count), "replicate_id": nullable(text)})
        return obj({**{key: nullable(count) for key in _PROTEASE_COUNT_FIELDS}, "rows": arr(row),
            "complete_supplied_curve_population": {"type": "boolean"}, "negative_substrate_ordinals": arr(count),
            "replicate_independence_inferred": {"const": False, "type": "boolean"}})
    if typ == "protease_assay_context":
        calibration = obj({"schema": {"type": "string", "const": "protease_signal_calibration_v1"},
            "response_per_product_concentration": {"type": "number", "exclusiveMinimum": 0},
            "signal_unit": {"type": "string", "minLength": 1}, "product_concentration_unit": {"type": "string", "minLength": 1},
            "curve_ordinals": arr(count), "applicability": {"type": "string", "enum": ["supported", "unknown", "conflicting", "unsupported"]},
            "source_ref": {"type": "string", "minLength": 1}})
        return obj({**{key: nullable({"type": "string", "minLength": 1})
                for key in ("sample_key", "substrate_identity", "enzyme_identity")},
            "conditions": {}, "replicate_ids": nullable(arr(nullable({"type": "string", "minLength": 1}))),
            "units": obj({key: nullable({"type": "string", "minLength": 1}) for key in ("time", "signal", "substrate", "enzyme")}),
            "calibration": nullable(calibration), "enzyme_basis": {"type": "string", "enum": ["unknown", "total_enzyme_concentration", "active_site_concentration"]},
            "product_per_cleavage": nullable({"type": "number", "exclusiveMinimum": 0})})
    require(typ == "protease_covariance_assessment")
    return obj({"schema": {"type": "string", "const": "protease_covariance_assessment_v1"},
        "native_symmetry": {"type": "string", "enum": ["exact", "asymmetric", "unavailable"]},
        "symmetric_part_positive_semidefinite": nullable({"type": "boolean"}),
        "assessment_arithmetic": {"type": "string", "const": "exact_rational_retained_entries"},
        "propagation_basis": {"type": "string", "const": "symmetric_bilinear_part_of_observed_native_matrix"},
        "statistical_covariance_validity": {"type": "string", "const": "unestablished"},
        "qualifications": arr({"type": "string", "const": "asymmetric_reported_matrix_bilinear_estimate_not_verified_statistical_covariance"})})


def _protease_context_schema(*, obj, stored_schema):
    def build(spec):
        if type(spec) is dict: return obj({key: build(child) for key, child in spec.items()})
        role, path, typ = spec
        result = stored_schema(typ)
        result["properties"]["source_pointer"] = {"type": "string", "const": path}
        return result
    return obj({"schema": {"type": "string", "const": PROTEASE_CONTEXT_VERSION},
        **{key: build(spec) for key, spec in _PROTEASE_CONTEXT_SPEC.items()}})


def _placement_json_definitions():
    """One opaque native type with the same 32-container bound as its validator."""
    definitions = {}
    for remaining in range(PLACEMENT_MAX_NESTING + 1):
        name = "PrimerPlacementNativeJSON" if remaining == PLACEMENT_MAX_NESTING else "PrimerPlacementNativeJSONDepth" + str(remaining)
        scalar = {"type": ["null", "boolean", "number", "string"]}
        if remaining:
            child = {"$ref": "#/$defs/PrimerPlacementNativeJSONDepth" + str(remaining - 1)}
            definitions[name] = {"anyOf": [scalar, {"type": "array", "items": deepcopy(child)},
                {"type": "object", "propertyNames": {"type": "string"}, "additionalProperties": deepcopy(child)}]}
        else:
            definitions[name] = scalar
    return definitions


def molecular_sequence_fact_sources(*, profile=_LEGACY_PROFILE):
    """Closed private definitions; no public episode/catalog is registered."""
    require(profile in (_LEGACY_PROFILE, _N_PROFILE, _O_PROFILE, _PROTEASE_PROFILE, _PLACEMENT_PROFILE))
    def obj(properties):
        return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}
    def nullable(schema): return {"anyOf": [schema, {"type": "null"}]}
    def arr(schema): return {"type": "array", "items": schema}
    ref = {"type": "string", "pattern": "^artifact_[0-9a-f]{64}$", "format": "reference", "x-reference-namespace": "artifact"}
    text = {"type": "string"}
    scalar = {"anyOf": [{"type": "number"}, {"type": "boolean"}, text, {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer", "minimum": 0}}]}
    def typed(typ):
        if typ == "placement_native_json":
            return {"$ref": "#/$defs/PrimerPlacementNativeJSON"}
        if typ == "placement_source_path":
            return arr(obj({"subject_ref": {"type": "string", "minLength": 1},
                "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
                "unit": {"type": "string", "enum": ["nt", "symbol"]}, "strand": {"type": "string", "enum": ["+", "-"]}}))
        if typ == "placement_mapping":
            result = obj({"state": {"type": "string", "enum": ["available", "unavailable", "incompatible"]},
                "intervals": nullable(typed("placement_source_path"))})
            result["allOf"] = [{"if": {"properties": {"state": {"const": "available"}}},
                "then": {"properties": {"intervals": typed("placement_source_path")}},
                "else": {"properties": {"intervals": {"type": "null"}}}}]
            return result
        if type(typ) is tuple: return {"type": "string", "enum": list(typ)}
        if typ in ("count", "int"): return {"type": "integer", **({"minimum": 0} if typ == "count" else {})}
        if typ == "number": return {"type": "number"}
        if typ == "bool": return {"type": "boolean"}
        if typ == "ordinals": return arr({"type": "integer", "minimum": 0})
        if typ == "fit_codes": return arr({"type": "string", "enum": list(FIT_CODES)})
        if typ == "frame": return {"type": "integer", "enum": [-3, -2, -1, 1, 2, 3]}
        if typ == "strand": return {"type": "string", "enum": ["+", "-"]}
        if typ == "compatibility": return {"type": "string", "enum": ["compatible", "incompatible", "unknown"]}
        if typ == "interval": return {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer", "minimum": 0}}
        if typ == "orf_native_row":
            fields = {"sequence": text, "aa_sequence": text,
                "start": {"type": "integer"}, "end": {"type": "integer"},
                "strand": typed("strand"), "frame": typed("frame")}
            return {"anyOf": [{"type": "array", "minItems": 6, "maxItems": 6,
                    "prefixItems": [deepcopy(fields[name]) for name in _ORF_NATIVE_FIELDS], "items": False},
                    obj(deepcopy(fields))],
                "description": "Literal native sequence, aa_sequence, start, end, strand and frame in their original array or object representation. Start/end retain reported zero-based half-open input coordinates, including conflicts; source_definition and translation qualifiers remain separate. No symbols, coordinates or translation are reconstructed."}
        if typ == "orf_source_path":
            return {"type": "array", "items": obj({"subject_ref": {"type": "string", "minLength": 1},
                    "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
                    "unit": {"type": "string", "enum": ["nt", "symbol"]},
                    "strand": typed("strand")}),
                "description": "Unchanged ordered original-source traversal with nonempty zero-based half-open segments and their actual nt or unspecified-symbol units and orientations. Protein paths describe original nucleotide/symbol ancestry, not amino-acid coordinates. An empty array is a known empty traversal; stored null means unavailable or unverified mapping, never zero coverage."}
        if typ in ("n_glycosylation_source_path", "o_glycosylation_source_path"):
            return {"type": "array", "minItems": 1, "items": obj({"subject_ref": {"type": "string", "minLength": 1},
                "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
                "unit": {"type": "string", "enum": ["nt", "aa", "symbol"]}, "strand": typed("strand")})}
        if type(typ) is str and typ.startswith(("n_glyco_", "o_glyco_")):
            return _glyco_literal_schema(typ, obj=obj, nullable=nullable, arr=arr, typed=typed)
        if type(typ) is str and typ.startswith("protease_"):
            return _protease_literal_schema(typ, obj=obj, nullable=nullable, arr=arr)
        return text
    def stored_schema(typ):
        return obj({"value_state": {"type": "string", "enum": list(VALUE_STATES)}, "value": nullable(typed(typ)),
            "source_ref": nullable(ref), "source_pointer": {"type": "string", "pattern": "^/"},
            "source_state": {"type": "string", "enum": [s for s in FILE_STATES if s != "produced_unretained"]}})
    identifiers = [{"kind": "summary"}, {"kind": "orf", "row_index": 0}, {"kind": "placement_group", "group_ordinal": 0},
        {"kind": "placement_hit", "group_ordinal": 0, "native_hit_ordinal": 0},
        {"kind": "placement_mismatch", "group_ordinal": 0, "native_hit_ordinal": 0, "native_mismatch_ordinal": 0},
        {"kind": "glycosylation_site", "row_ordinal": 0}, {"kind": "protease_fit"}, {"kind": "protease_curve", "substrate_ordinal": 0},
        {"kind": "protease_quantity", "quantity": QUANTITIES[0]}, {"kind": "protease_covariance", "parameter_i": 0, "parameter_j": 0}]
    if profile == _PROTEASE_PROFILE:
        identifiers = [selected for identity in identifiers for selected in
            ([{"kind": "protease_quantity", "quantity": quantity} for quantity in QUANTITIES]
                if identity["kind"] == "protease_quantity" else [identity])]
    def id_schema(identity):
        return obj({key: {"type": "string", "const": value} if key == "kind" else
            ({"type": "string", "const": value} if profile == _PROTEASE_PROFILE else
                {"type": "string", "enum": list(QUANTITIES)}) if key == "quantity" else
            {"type": "integer", "minimum": 0, **({"maximum": 1} if key in ("parameter_i", "parameter_j") else {})}
            for key, value in identity.items()})
    failure_schema = obj({"code": {"type": "string", "enum": list(FAILURES)}, "stage": {"type": "string", "enum": list(STAGES)},
        "role": nullable({"type": "string", "enum": list(FILE_ROLES)}), "row_id": nullable({"anyOf": [id_schema(i) for i in identifiers]}),
        "source_ref": nullable(ref), "source_pointer": nullable({"type": "string", "pattern": "^/"}), "diagnostic_ref": nullable(ref)})
    projections = []
    for operation in ((OPERATIONS[2],) if profile == _N_PROFILE else (OPERATIONS[3],) if profile == _O_PROFILE
            else (OPERATIONS[4],) if profile == _PROTEASE_PROFILE else (OPERATIONS[1],) if profile == _PLACEMENT_PROFILE else OPERATIONS):
        variants = []
        for identity in identifiers:
            table = field_table(operation, identity, profile=profile)
            if not table: continue
            specs = {}; unavailable = {role: empty_file_state() for role in FILE_ROLES}
            qualifier = _qualifiers(operation, identity, None, {"schema": SCHEMAS[operation][1][-1]}, unavailable, specs)
            reason_union = tuple(dict.fromkeys((*REASONS["protease_kinetics_components_v1"], *REASONS["protease_kinetics_components_v2"])))
            qualifier_schema = obj({"schema": {"type": "string", "const": qualifier["schema"]},
                "operation": {"type": "string", "const": operation}, "component_schema": nullable({"type": "string", "enum": list(SCHEMAS[operation][1])}),
                "states": obj({name: stored_schema(reason_union if "reason" in name and operation == OPERATIONS[4] else spec[1]) for name, spec in specs.items()}),
                "interpretation": {"type": "string", "const": qualifier["interpretation"]}})
            denominator = stored_schema("count" if profile in (_O_PROFILE, _PLACEMENT_PROFILE) else "number")
            denominator["properties"].update(kind={"type": "string", "enum": ["numerator", "denominator", "calibration_response", "enzyme_concentration", "product_per_cleavage"]},
                unit=nullable(text), unit_sources=arr(stored_schema("text")))
            if profile == _O_PROFILE:
                denominator["properties"].update(kind={"type": "string", "enum": ["numerator", "denominator"]},
                    unit={"type": "string", "const": "symbols"}, unit_sources={"type": "array", "maxItems": 0, "items": False})
            if profile == _PLACEMENT_PROFILE:
                denominator["properties"].update(kind={"type": "string", "enum": ["numerator", "denominator"]},
                    unit_sources={"type": "array", "maxItems": 0, "items": False})
            denominator["required"] = list(denominator["properties"])
            cell = obj({"row_id": id_schema(identity), "field": {"type": "string", "enum": list(table)},
                **stored_schema("number")["properties"], "unit": nullable(text), "population_id": {"type": "string", "enum": list(dict.fromkeys(spec[3] for spec in table.values()))},
                "denominators": arr(denominator), "scientific_qualifiers": qualifier_schema})
            cell["properties"]["value"] = nullable(scalar)
            if operation == OPERATIONS[0] and identity["kind"] == "orf":
                # The old scalar union must not block these closed structured
                # values or admit arbitrary objects into another profile.
                cell["properties"]["value"] = nullable({"anyOf": [deepcopy(scalar),
                    typed("orf_native_row"), typed("orf_source_path")]})
            if profile == _N_PROFILE and identity["kind"] == "glycosylation_site":
                cell["properties"]["value"] = nullable({"anyOf": [deepcopy(scalar), typed("n_glycosylation_source_path")]})
            if profile == _O_PROFILE and identity["kind"] == "glycosylation_site":
                cell["properties"]["value"] = nullable({"anyOf": [deepcopy(scalar),
                    typed("o_glycosylation_source_path"), typed("o_glyco_symbol_counts")]})
            if profile == _PROTEASE_PROFILE and identity["kind"] == "protease_covariance":
                cell["properties"]["value"] = nullable(typed("protease_native_literal"))
            if profile == _PLACEMENT_PROFILE:
                cell["properties"]["value"] = typed("placement_native_json")
            cell["allOf"] = [{"if": {"properties": {"field": {"const": name}}}, "then": {"properties": {"value": nullable(typed(spec[1]))}}} for name, spec in table.items()]
            for branch, spec in zip(cell["allOf"], table.values()):
                if spec[1] in ("orf_native_row", "orf_source_path"):
                    branch["then"]["properties"]["unit"] = {"type": "string", "const": spec[2]}
                if profile in _GLYCO_PROFILES:
                    branch["then"]["properties"]["unit"] = {"type": "string", "const": spec[2]}
                if profile == _PLACEMENT_PROFILE:
                    branch["then"]["properties"]["unit"] = {"type": "string", "const": spec[2]}
                    if spec[1] in ("placement_mapping", "placement_source_path"):
                        side = spec[0].rsplit("/", 1)[-1].split("_", 1)[0]
                        conditions = []
                        for state in (("available", "unavailable", "incompatible") if spec[1] == "placement_mapping" else ("available",)):
                            condition = {"value_state": {"const": "stored_value"}}
                            if spec[1] == "placement_mapping":
                                condition["value"] = {"properties": {"state": {"const": state}}}
                            conditions.append({"if": {"properties": condition}, "then": {"properties": {
                                "scientific_qualifiers": {"properties": {"states": {"properties": {
                                    side + "_mapping_state": {"properties": {"value_state": {"const": "stored_value"},
                                        "value": {"const": state}}}}}}}}}})
                        branch["then"]["allOf"] = conditions
                    operands = []
                    for path in spec[4]:
                        operand = deepcopy(denominator)
                        numerator = path.endswith("/numerator")
                        operand["properties"].update(kind={"type": "string", "const": "numerator" if numerator else "denominator"},
                            unit={"const": "symbols" if "/mismatch_fraction/" in path else None})
                        operand["properties"]["source_pointer"] = ({"type": "string", "pattern":
                            r"^/groups/(0|[1-9][0-9]*)/hits/(0|[1-9][0-9]*)/mismatch_fraction/" + ("numerator" if numerator else "denominator") + "$"}
                            if "/mismatch_fraction/" in path else {"type": "string", "const": path})
                        operands.append(operand)
                    branch["then"]["properties"]["denominators"] = ({"type": "array", "minItems": len(operands),
                        "maxItems": len(operands), "prefixItems": operands, "items": False}
                        if operands else {"type": "array", "maxItems": 0, "items": False})
                if profile == _O_PROFILE:
                    operands = []
                    for path in spec[4]:
                        operand = deepcopy(denominator)
                        numerator = path.endswith("/st_count")
                        operand["properties"]["kind"] = {"type": "string", "const": "numerator" if numerator else "denominator"}
                        operand["properties"]["source_pointer"] = {"type": "string", "pattern":
                            r"^/rows/(0|[1-9][0-9]*)/cells/" + ("st_count" if numerator else "window_denominator_symbols") + "$"}
                        operands.append(operand)
                    branch["then"]["properties"]["denominators"] = ({"type": "array", "minItems": 2, "maxItems": 2,
                        "prefixItems": operands, "items": False} if operands else {"type": "array", "maxItems": 0, "items": False})
                if profile == _PROTEASE_PROFILE:
                    operands = []
                    for path in spec[4]:
                        _role, kind, unit, unit_paths = _protease_operand_spec(path)
                        operand = deepcopy(denominator)
                        operand["properties"].update(source_pointer={"type": "string", "const": path},
                            kind={"type": "string", "const": kind}, unit={"const": unit})
                        unit_sources = []
                        for unit_path in unit_paths:
                            unit_source = stored_schema("text")
                            unit_source["properties"]["source_pointer"] = {"type": "string", "const": unit_path}
                            unit_sources.append(unit_source)
                        operand["properties"]["unit_sources"] = ({"type": "array", "minItems": len(unit_sources),
                            "maxItems": len(unit_sources), "prefixItems": unit_sources, "items": False}
                            if unit_sources else {"type": "array", "maxItems": 0, "items": False})
                        operands.append(operand)
                    branch["then"]["properties"]["denominators"] = ({"type": "array", "minItems": len(operands),
                        "maxItems": len(operands), "prefixItems": operands, "items": False}
                        if operands else {"type": "array", "maxItems": 0, "items": False})
                    if not spec[2].startswith("stored_"):
                        branch["then"]["properties"]["unit"] = {"const": spec[2]}
            if profile == _PLACEMENT_PROFILE:
                cell["allOf"].append({"if": {"properties": {"value_state": {"const": "stored_value"}}},
                    "then": {"properties": {"value": {"not": {"type": "null"}}}},
                    "else": {"properties": {"value": {"type": "null"}}}})
            variants.append(cell)
        projection = obj({"schema": {"type": "string", "const": {_LEGACY_PROFILE: PUBLIC_VERSION, _N_PROFILE: N_PUBLIC_VERSION, _O_PROFILE: O_PUBLIC_VERSION,
            _PROTEASE_PROFILE: PROTEASE_PUBLIC_VERSION, _PLACEMENT_PROFILE: PLACEMENT_PUBLIC_VERSION}[profile]}, "operation": {"type": "string", "const": operation},
            "source_kind": {"type": "string", "enum": ["original_stored", "selected_saved_calculation"]}, "source_sheet_ref": nullable(ref), "source_components_ref": nullable(ref),
            "source_states": obj({role: {"type": "string", "enum": [s for s in FILE_STATES if s != "produced_unretained"]} for role in ("sheet", "components")}),
            "components_schema": nullable({"type": "string", "enum": list(SCHEMAS[operation][1])}),
            "original_attempt_association": {"type": "string", "enum": ["verified", "unavailable", "conflict"]}, "rows": arr({"anyOf": variants}), "failures": arr(failure_schema)})
        if profile in _GLYCO_PROFILES:
            projection["properties"]["context"] = _glyco_context_schema(profile, obj=obj, nullable=nullable, arr=arr, stored_schema=stored_schema)
            projection["required"].append("context")
        if profile == _PROTEASE_PROFILE:
            projection["properties"]["components_schema"] = nullable({"type": "string", "const": "protease_kinetics_components_v2"})
            projection["properties"]["context"] = _protease_context_schema(obj=obj, stored_schema=stored_schema)
            projection["required"].append("context")
        projections.append(projection)
    saved_schema = obj({"operation": {"type": "string", "enum": list(OPERATIONS)}, "role": {"type": "string", "enum": list(FILE_ROLES)},
        "artifact_ref": ref, "source_kind": {"type": "string", "enum": ["original_stored", "selected_saved_calculation"]}, "source_sheet_ref": nullable(ref),
        "components_schema": nullable({"type": "string", "enum": list(dict.fromkeys(schema for values in SCHEMAS.values() for schema in values[1]))})})
    result = {source: {"report_schema": {**arr(item), "x-source": source}, "description": description} for source, item, description in (
        (PROJECTION_SOURCE, {"anyOf": projections}, "Selected stored molecular values with their original scientific qualification"),
        (SAVED_SOURCE, saved_schema, "Explicit selected retained molecular artifact references"),
        (FAILURE_SOURCE, failure_schema, "Attributable molecular result availability failures"))}
    if profile == _PLACEMENT_PROFILE:
        result[PROJECTION_SOURCE]["report_schema"]["$defs"] = _placement_json_definitions()
    return result


# Explicit private supplied-data branch. Legacy profile/schema tables above
# retain their closed meanings; this metadata does not install a public tool.
SUPPLIED_OPERATION = "analyze_arsenic_speciation_hplc_icpms"
SUPPLIED_SELECTOR_VERSION = "molecular_sequence_result_selector_v2"
SUPPLIED_ASSIGNMENT_VERSION = "molecular_sequence_supplied_results_assignment_v1"
SUPPLIED_PLAN_VERSION = "molecular_sequence_result_worker_plan_v2"
SUPPLIED_RESULT_VERSION = "molecular_sequence_result_worker_result_v2"
CALCULATION_RECORD_VERSION = "molecular_sequence_calculation_record_v1"
SUPPLIED_OUTPUTS = ("sheet", "calculated_components", "diagnostics")
SUPPLIED_PROFILE = {
    "operation": SUPPLIED_OPERATION, "mode": "supplied_measurements",
    "sheet_tag_key": "version", "sheet_version": "calibrated_signal_sheet_v1",
    "components_tag_key": "version", "components_version": "calibrated_signal_components_v1",
    "selection_tag_key": "version", "selection_version": "calibrated_signal_selection_v1",
    "calculator_id": "calibrated_signal_calculations.calculate_calibrated_signal_components",
}
SUPPLIED_FAILURES = ("input_unavailable", "input_invalid", "selection_invalid", "stored_linkage_conflict",
    "retention_failed", "artifact_identity_conflict", "schema_invalid", "calculation_failed",
    "worker_unavailable", "worker_failed", "worker_uncertain", "environment_conflict")
SUPPLIED_FAILURE_POINTERS = ("", "/sheet", "/selection", "/samples", "/species", "/calibrations", "/association")
SUPPLIED_FAILURE_LOCATIONS = dict(zip(SUPPLIED_FAILURE_POINTERS,
    ("document_root", "embedded_sheet", "calculation_selection", "samples", "species", "calibrations", "association")))


def supplied_profile(operation):
    require(operation == SUPPLIED_OPERATION)
    return deepcopy(SUPPLIED_PROFILE)


def _supplied_selection(value):
    closed(value, ("reference", "namespace"))
    require(type(value["reference"]) is str and value["reference"]
        and not any(c in value["reference"] for c in "\0\n\r")
        and value["namespace"] in ("source", "artifact"))


def validate_molecular_sequence_supplied_selector(value):
    from .calibrated_signal_contracts import calibrated_signal_selection_schema
    from .domain import validate_schema
    value = copy_json(value)
    closed(value, ("version", "operation", "mode", "action", "input", "stored", "calculation_selection", "return_files"))
    require(value["version"] == SUPPLIED_SELECTOR_VERSION and value["operation"] == SUPPLIED_OPERATION
        and value["mode"] == "supplied_measurements" and value["action"] in ("calculate", "read_stored"))
    roles = value["return_files"]
    require(type(roles) is list and all(role in ("sheet", "components") for role in roles)
        and len(roles) == len(set(roles)))
    if value["action"] == "calculate":
        _supplied_selection(value["input"])
        require(value["stored"] is None)
        validate_schema(value["calculation_selection"], calibrated_signal_selection_schema())
    else:
        require(value["input"] is None and value["calculation_selection"] is None)
        closed(value["stored"], ("sheet", "components"))
        require(any(item is not None for item in value["stored"].values()))
        for item in value["stored"].values():
            if item is not None: _supplied_selection(item)
    return value


def supplied_execution_constraints(value):
    """Retain explicit caller allocation/environment; choose no replacement."""
    from .molecular_sequence_execution_contracts import environment
    value = copy_json(value)
    closed(value, ("policy", "environment"))
    policy = value["policy"]; closed(policy, ('memory_bytes', 'scratch_bytes'))
    require(type(policy["memory_bytes"]) is int and 0 < policy["memory_bytes"] <= 21474836480
        and type(policy["scratch_bytes"]) is int and 0 < policy["scratch_bytes"] <= 4294967296)
    environment(value["environment"])
    return value


def supplied_failure(code, stage, *, role=None, source_ref=None, source_pointer=None):
    return validate_supplied_failure(dict(version="molecular_sequence_supplied_failure_v1",
        operation=SUPPLIED_OPERATION, code=code, stage=stage, role=role,
        source_ref=source_ref, source_pointer=source_pointer))


def validate_supplied_failure(value):
    if type(value) is dict and value.get("version") == "molecular_sequence_supplied_failure_v2":
        closed(value, ("version", "operation", "code", "stage", "role", "source_ref", "source_location"))
        require(value["operation"] == SUPPLIED_OPERATION and value["code"] in SUPPLIED_FAILURES
            and value["stage"] in STAGES and value["role"] in (None, "sheet", "components")
            and (value["source_ref"] is None or reference(value["source_ref"]))
            and (value["source_location"] is None or value["source_location"] in SUPPLIED_FAILURE_LOCATIONS.values()))
        return copy_json(value)
    closed(value, ("version", "operation", "code", "stage", "role", "source_ref", "source_pointer"))
    require(value["version"] == "molecular_sequence_supplied_failure_v1" and value["operation"] == SUPPLIED_OPERATION
        and value["code"] in SUPPLIED_FAILURES and value["stage"] in STAGES
        and value["role"] in (None, "sheet", "components"))
    require(value["source_ref"] is None or reference(value["source_ref"]))
    require(value["source_pointer"] is None or value["source_pointer"] in SUPPLIED_FAILURE_POINTERS)
    return copy_json(value)


def supplied_failure_view(value):
    value = validate_supplied_failure(value)
    require(value["version"] == "molecular_sequence_supplied_failure_v1")
    pointer = value.pop("source_pointer")
    value.update(version="molecular_sequence_supplied_failure_v2",
        source_location=None if pointer is None else SUPPLIED_FAILURE_LOCATIONS[pointer])
    return validate_supplied_failure(value)


def validate_supplied_file_fact(value):
    closed(value, ("version", "operation", "role", "artifact_ref", "source_kind", "source_sheet_ref",
        "components_tag_key", "components_version", "validation_state", "calculation_origin", "linkage_state"))
    require(value["version"] == "molecular_sequence_retained_file_v2" and value["operation"] == SUPPLIED_OPERATION
        and value["role"] in ("sheet", "components") and reference(value["artifact_ref"])
        and value["source_kind"] in ("admitted_input", "selected_supplied_calculation", "admitted_stored")
        and (value["source_sheet_ref"] is None or reference(value["source_sheet_ref"]))
        and value["validation_state"] in ("valid", "invalid", "unavailable")
        and value["calculation_origin"] in ("selected_action_only", "selected_calculation_recorded", "admitted_stored_unverified")
        and value["linkage_state"] in ("not_assessed", "matched", "conflict", "sheet_unavailable", "components_unavailable"))
    require((value["components_tag_key"], value["components_version"]) in
        ((None, None), ("version", SUPPLIED_PROFILE["components_version"])))
    return copy_json(value)


def validate_supplied_worker_plan(value):
    from .molecular_sequence_execution_contracts import _software, absolute_path, environment
    value = copy_json(value)
    closed(value, ("version", "directory", "selector", "input_file", "input_path", "input_evidence_file",
        "software", "selected_environment", "policy"))
    require(value["version"] == SUPPLIED_PLAN_VERSION)
    selector = validate_molecular_sequence_supplied_selector(value["selector"])
    require(selector["action"] == "calculate")
    absolute_path(value["directory"]); absolute_path(value["input_path"])
    file_identity(value["input_file"]); file_identity(value["input_evidence_file"])
    require(value["input_file"]["format"] == "json"
        and value["input_evidence_file"]["format"] == "molecular_sequence_supplied_input_evidence_v1")
    environment(value["selected_environment"])
    supplied_execution_constraints({"policy": value["policy"], "environment": value["selected_environment"]})
    if value["software"] is None:
        require(value["selected_environment"] == {})  # Explicit engineering controls only.
    else:
        _software(value["software"])
        require(value["selected_environment"].get("PYTHONHOME") == value["software"]["python_home"]
            and value["selected_environment"].get("PYTHONPATH") == ":".join(value["software"]["import_roots"]))
    return value


def validate_supplied_worker_result(value):
    value = copy_json(value)
    closed(value, ("version", "plan_sha256", "selector", "outputs", "failures"))
    require(value["version"] == SUPPLIED_RESULT_VERSION and type(value["plan_sha256"]) is str
        and re.fullmatch("[0-9a-f]{64}", value["plan_sha256"]))
    validate_molecular_sequence_supplied_selector(value["selector"])
    require(type(value["outputs"]) is list and [row.get("role") for row in value["outputs"]] == list(SUPPLIED_OUTPUTS))
    for row in value["outputs"]:
        closed(row, ("role", "declaration")); file_declaration(row["declaration"])
        require(row["declaration"]["relative_path"] == row["role"] + ".json" and row["declaration"]["format"] == "json")
    require(type(value["failures"]) is list)
    for issue in value["failures"]:
        require(issue.get("version") == "molecular_sequence_supplied_failure_v1"); validate_supplied_failure(issue)
    return value


def validate_molecular_sequence_calculation_record(value):
    value = copy_json(value)
    closed(value, ("version", "operation", "kind", "input_evidence_files", "input_sheet_file", "selection",
        "software", "selected_environment", "policy", "worker_plan_file", "worker_result_file", "worker_diagnostics_file",
        "source_files", "worker_outputs", "calculation_state", "calculation_call_count", "origin_state", "linkage_state",
        "validation_states", "native_invocation", "acquired_population", "failures"))
    require(value["version"] == CALCULATION_RECORD_VERSION and value["operation"] == SUPPLIED_OPERATION
        and value["kind"] in ("selected_supplied_calculation", "admitted_stored_read")
        and value["native_invocation"] == "not_requested" and value["acquired_population"] is None)
    require(value["calculation_state"] in ("input_unavailable", "selection_invalid", "not_started", "completed",
        "calculation_failed", "worker_failed", "worker_uncertain", "stored_read")
        and value["origin_state"] in ("selected_action_only", "selected_calculation_recorded", "admitted_stored_unverified")
        and value["linkage_state"] in ("not_assessed", "matched", "conflict", "sheet_unavailable", "components_unavailable"))
    count = value["calculation_call_count"]
    require(count is None or type(count) is int and count in (0, 1))
    require(type(value["input_evidence_files"]) is dict and set(value["input_evidence_files"]) <= {"sheet", "components"})
    for file in value["input_evidence_files"].values(): file_identity(file)
    for key in ("input_sheet_file", "worker_plan_file", "worker_result_file", "worker_diagnostics_file"):
        if value[key] is not None: file_identity(value[key])
    closed(value["source_files"], FILE_ROLES)
    for file in value["source_files"].values(): validate_file_state(file)
    require(all(value["source_files"][role]["state"] == "not_requested" for role in ("capture", "native_results", "native_plot")))
    closed(value["worker_outputs"], ("sheet", "components"))
    for file in value["worker_outputs"].values(): validate_file_state(file)
    closed(value["validation_states"], ("sheet", "components"))
    require(all(state in ("valid", "invalid", "unavailable") for state in value["validation_states"].values()))
    require(type(value["failures"]) is list)
    for issue in value["failures"]:
        require(issue.get("version") == "molecular_sequence_supplied_failure_v1"); validate_supplied_failure(issue)
    if value["kind"] == "admitted_stored_read":
        require(count == 0 and value["origin_state"] == "admitted_stored_unverified" and value["selection"] is None
            and value["calculation_state"] == "stored_read" and value["software"] is None
            and value["selected_environment"] == {} and value["policy"] is None
            and all(value[key] is None for key in ("worker_plan_file", "worker_result_file", "worker_diagnostics_file")))
    else:
        require(value["origin_state"] != "admitted_stored_unverified")
        from .calibrated_signal_contracts import calibrated_signal_selection_schema
        from .domain import validate_schema
        validate_schema(value["selection"], calibrated_signal_selection_schema())
        supplied_execution_constraints({"policy": value["policy"], "environment": value["selected_environment"]})
        if value["software"] is not None:
            from .molecular_sequence_execution_contracts import _software
            _software(value["software"])
        if count == 1:
            require(value["worker_diagnostics_file"] is not None and value["origin_state"] == "selected_calculation_recorded")
        else: require(value["origin_state"] == "selected_action_only")
        if value["calculation_state"] == "completed": require(count == 1)
        if value["calculation_state"] == "worker_uncertain": require(count is None)
    return value


def supplied_file_fact_sources():
    """Ordinary private File/failure forms; no rich numerical source installed."""
    def obj(fields):
        return dict(type="object", properties=fields, required=list(fields), additionalProperties=False)
    def code(values, nullable=False):
        return dict(type=["string", "null"] if nullable else "string", enum=[*values, *([None] if nullable else [])])
    ref = dict(type="string", format="reference", **{"x-reference-namespace": "artifact"})
    file = obj({"version": code(("molecular_sequence_retained_file_v2",)), "operation": code((SUPPLIED_OPERATION,)),
        "role": code(("sheet", "components")), "artifact_ref": ref,
        "source_kind": code(("admitted_input", "selected_supplied_calculation", "admitted_stored")),
        "source_sheet_ref": {**ref, "type": ["string", "null"]}, "components_tag_key": code(("version",), True),
        "components_version": code((SUPPLIED_PROFILE["components_version"],), True),
        "validation_state": code(("valid", "invalid", "unavailable")),
        "calculation_origin": code(("selected_action_only", "selected_calculation_recorded", "admitted_stored_unverified")),
        "linkage_state": code(("not_assessed", "matched", "conflict", "sheet_unavailable", "components_unavailable"))})
    issue = obj({"version": code(("molecular_sequence_supplied_failure_v2",)), "operation": code((SUPPLIED_OPERATION,)),
        "code": code(SUPPLIED_FAILURES), "stage": code(STAGES), "role": code(("sheet", "components"), True),
        "source_ref": {**ref, "type": ["string", "null"]}, "source_location": code(tuple(SUPPLIED_FAILURE_LOCATIONS.values()), True)})
    return {source: {"report_schema": {"type": "array", "items": item, "x-source": source}, "description": description}
        for source, item, description in ((SAVED_SOURCE, file, "Requested admitted or calculated scientific Files"),
            (FAILURE_SOURCE, issue, "Attributable supplied-input or calculation failures"))}


# Ordinary custody is additive. None of the five private result profiles or
# their existing artifact-reference report contracts is changed by this port.
ORDINARY_ORF_TOOL = OPERATIONS[0]
ORDINARY_ORF_INTENT_VERSION = "molecular_sequence_ordinary_intent_v1"
ORDINARY_ORF_CUSTODY_VERSION = "ordinary_orf_publication_v1"
ORDINARY_ORF_PUBLIC_VERSION = "ordinary_orf_values_v1"
ORDINARY_ORF_SOURCE_VERSION = "ordinary_orf_result_v1"
ORDINARY_ORF_FACT_SOURCE = "orf_measurements"
ORDINARY_ORF_PACKET_FORMAT = "ordinary_orf_values_packet_v1"
ORDINARY_ORF_POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
ORDINARY_ORF_SAVED_INTENT_VERSION = "molecular_sequence_ordinary_saved_intent_v1"
ORDINARY_ORF_SAVED_CUSTODY_VERSION = "ordinary_orf_saved_publication_v1"
ORDINARY_ORF_CALCULATOR = "orf_measurements.calculate_orf_components"
ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS = (ORDINARY_ORF_TOOL, OPERATIONS[2], OPERATIONS[3], OPERATIONS[1])


def ordinary_molecular_sequence_profile(operation):
    """Detached finite carrier tags; native source identity remains native-owned."""
    require(operation in ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS)
    if operation == OPERATIONS[1]:
        from .primer_placement_result_contracts import profile
        return profile()
    glyco = operation in OPERATIONS[2:4]
    n = operation == OPERATIONS[2]
    stem = "ordinary_n_glycosylation" if n else "ordinary_o_glycosylation" if glyco else "ordinary_orf"
    return dict(operation=operation, fact_source="n_glycosylation_motif_outcomes" if n else "o_glycosylation_hotspot_outcomes" if glyco else ORDINARY_ORF_FACT_SOURCE,
        native_source="glyco" if glyco else "molecular",
        native_request_version="molecular_sequence_request_v2" if glyco else "molecular_sequence_request_v1",
        deployment_version="molecular_sequence_deployment_v2" if glyco else "molecular_sequence_deployment_v1",
        driver_request_version="molecular_sequence_driver_request_v1",
        native_argument_names=["allow_overlap"] if n else ["window", "min_st_fraction", "disallow_proline_next"] if glyco else ["min_length", "search_reverse", "filter_subsets"],
        molecule_model="protein" if glyco else "dna", operand_version=stem + "_sequence_operand_v1",
        prepared_version=stem + "_prepared_v1", execution_version=stem + "_execution_v1",
        binding_version=stem + "_attempt_binding_v1",
        binding_filename="ordinary-n-glycosylation-input-binding.json" if n else "ordinary-o-glycosylation-input-binding.json" if glyco else "ordinary-orf-input-binding.json",
        intent_version=stem + "_intent_v1" if glyco else ORDINARY_ORF_INTENT_VERSION,
        saved_intent_version=stem + "_saved_intent_v1" if glyco else ORDINARY_ORF_SAVED_INTENT_VERSION,
        custody_version=stem + "_publication_v1", saved_custody_version=stem + "_saved_publication_v1",
        public_version=stem + "_values_v1", source_version=stem + "_result_v1", packet_format=stem + "_values_packet_v1",
        publication_request_version=stem + "_publication_request_v1", saved_request_version=stem + "_saved_request_v1",
        read_receipt_version=stem + "_read_receipt_v1", calculation_started_version=stem + "_calculation_started_v1",
        calculation_result_version=stem + "_calculation_result_v1", calculation_diagnostic_version=stem + "_calculation_diagnostic_v1",
        calculator_id="glycosylation_measurements.calculate_glycosylation_components" if glyco else ORDINARY_ORF_CALCULATOR,
        selector_version=N_SELECTOR_VERSION if n else O_SELECTOR_VERSION if glyco else SELECTOR_VERSION,
        projection_version=N_PROJECTION_VERSION if n else O_PROJECTION_VERSION if glyco else PROJECTION_VERSION,
        selected_values_version=N_PUBLIC_VERSION if n else O_PUBLIC_VERSION if glyco else PUBLIC_VERSION)


def _ordinary_profile(operation, actual):
    require(actual in ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS and (operation is None or operation == actual))
    return ordinary_molecular_sequence_profile(actual)


def _ordinary_actual(value, *path):
    for key in path:
        if type(value) is not dict: return None
        value = value.get(key)
    return value


def validate_ordinary_orf_arguments(arguments):
    return validate_ordinary_molecular_sequence_arguments(ORDINARY_ORF_TOOL, arguments)


def ordinary_orf_intent_version(arguments):
    return ordinary_molecular_sequence_intent_version(ORDINARY_ORF_TOOL, arguments)


def ordinary_orf_selector(arguments):
    return ordinary_molecular_sequence_selector(ORDINARY_ORF_TOOL, arguments)


def validate_ordinary_orf_intent(value):
    return validate_ordinary_molecular_sequence_intent(value, operation=ORDINARY_ORF_TOOL)


def validate_ordinary_orf_execution(value):
    return validate_ordinary_molecular_sequence_execution(value, operation=ORDINARY_ORF_TOOL)


def ordinary_orf_packet(custody):
    return ordinary_molecular_sequence_packet(custody, operation=ORDINARY_ORF_TOOL)


def validate_ordinary_orf_packet(value):
    return validate_ordinary_molecular_sequence_packet(value, operation=ORDINARY_ORF_TOOL)


def validate_ordinary_orf_return(value):
    return validate_ordinary_molecular_sequence_return(value, operation=ORDINARY_ORF_TOOL)


def validate_ordinary_orf_custody(value):
    return validate_ordinary_molecular_sequence_custody(value, operation=ORDINARY_ORF_TOOL)


def validate_ordinary_orf_saved_custody(value):
    return validate_ordinary_molecular_sequence_saved_custody(value, operation=ORDINARY_ORF_TOOL)


def ordinary_orf_fact_sources():
    return ordinary_molecular_sequence_fact_sources(ORDINARY_ORF_TOOL)


def validate_ordinary_molecular_sequence_arguments(operation, arguments):
    """Preserve the original native request; saved views select a real Source."""
    profile = ordinary_molecular_sequence_profile(operation)
    if operation == OPERATIONS[1]:
        from .primer_placement_result_contracts import validate_arguments
        return validate_arguments(arguments)
    arguments = copy_json(arguments)
    require(type(arguments) is dict)
    if "mode" not in arguments:
        ordinary_molecular_sequence_selector(operation, arguments)
        return arguments
    closed(arguments, ("mode", "result_ref", "rows"))
    require(arguments["mode"] in ("read_stored", "calculate_saved")
        and type(arguments["result_ref"]) is str
        and re.fullmatch(r"source_[0-9a-f]{24}", arguments["result_ref"]) is not None)
    validate_molecular_sequence_result_selector(dict(version=profile["selector_version"], mode=MODES[0],
        operation=operation, saved_sheet_ref=None, rows=arguments["rows"], return_files=[]))
    return arguments


def ordinary_molecular_sequence_intent_version(operation, arguments):
    profile = ordinary_molecular_sequence_profile(operation)
    arguments = validate_ordinary_molecular_sequence_arguments(operation, arguments)
    if operation == OPERATIONS[1] and arguments["mode"] == "run_native":
        return profile["intent_version"]
    return profile["saved_intent_version"] if "mode" in arguments else profile["intent_version"]


def ordinary_molecular_sequence_selector(operation, arguments):
    profile = ordinary_molecular_sequence_profile(operation)
    arguments = copy_json(arguments)
    if operation == OPERATIONS[1]:
        from .primer_placement_result_contracts import selector, validate_arguments
        return selector(validate_arguments(arguments))
    if operation == OPERATIONS[2]:
        closed(arguments, ("subject_ref", "allow_overlap", "rows"))
        require(type(arguments["subject_ref"]) is str and bool(arguments["subject_ref"])
            and type(arguments["allow_overlap"]) is bool)
    elif operation == OPERATIONS[3]:
        closed(arguments, ("subject_ref", "window", "min_st_fraction", "disallow_proline_next", "rows"))
        require(type(arguments["subject_ref"]) is str and bool(arguments["subject_ref"])
            and type(arguments["window"]) is int and valid_type(arguments["min_st_fraction"], "number")
            and type(arguments["disallow_proline_next"]) is bool)
    else:
        closed(arguments, ("subject_ref", "min_length", "search_reverse", "filter_subsets", "rows"))
        require(type(arguments["subject_ref"]) is str and bool(arguments["subject_ref"])
            and type(arguments["min_length"]) is int and arguments["min_length"] >= 0
            and all(type(arguments[key]) is bool for key in ("search_reverse", "filter_subsets")))
    return validate_molecular_sequence_result_selector(dict(version=profile["selector_version"], mode=MODES[0],
        operation=operation, saved_sheet_ref=None, rows=arguments["rows"], return_files=[]))


def validate_ordinary_molecular_sequence_intent(value, *, operation=None):
    value = copy_json(value)
    closed(value, ("version", "run_id", "episode_id", "path", "scope", "assignment",
        "original_request_sha256", "operation_key", "tool_name", "arguments", "target"))
    profile = _ordinary_profile(operation, _ordinary_actual(value, "tool_name"))
    operation = profile["operation"]
    require(value["version"] == ordinary_molecular_sequence_intent_version(operation, value["arguments"]) and value["tool_name"] == operation
        and value["target"] is None and all(type(value[key]) is str and value[key]
            for key in ("run_id", "episode_id", "operation_key"))
        and type(value["original_request_sha256"]) is str
        and re.fullmatch("[0-9a-f]{64}", value["original_request_sha256"]) is not None
        and type(value["path"]) is list and type(value["scope"]) is dict and type(value["assignment"]) is dict)
    prefix = value["run_id"] + ":" + value["episode_id"] + ":"
    suffix = value["operation_key"][len(prefix):] if value["operation_key"].startswith(prefix) else ""
    require(suffix.isdecimal() and str(int(suffix)) == suffix)
    return value


def validate_ordinary_molecular_sequence_execution(value, *, operation=None):
    """Pure carrier validation; this supplies no selected-action authority."""
    from .molecular_sequence_execution_contracts import (
        file_pin, validate_molecular_sequence_selected_plan, validate_molecular_sequence_attempt_bundle)
    value = copy_json(value)
    closed(value, ("version", "plan", "handle", "plan_file", "binding_file", "driver_request_file",
        "terminal", "quiescent", "returncode", "metadata", "failure", "bundle", "declaration",
        "declarations", "metadata_failures", "output_byte_validation"))
    profile = _ordinary_profile(operation, _ordinary_actual(value, "plan", "selection", "operation"))
    operation = profile["operation"]
    require(value["version"] == profile["execution_version"] and value["terminal"] is True
        and value["quiescent"] is True and (value["returncode"] is None or type(value["returncode"]) is int)
        and value["output_byte_validation"] == "deferred_to_result_owner"
        and type(value["handle"]) is dict and type(value["metadata"]) is dict
        and value["metadata"].get("policy") == ORDINARY_ORF_POLICY)
    plan = validate_molecular_sequence_selected_plan(value["plan"],
        expected_payload_sha256=value["plan"]["selected_payload_sha256"])
    require(plan["selection"]["operation"] == operation and plan["selection"]["mode"] == "native"
        and plan["policy"] == ORDINARY_ORF_POLICY
        and plan["selection"]["driver_request"]["version"] == profile["driver_request_version"]
        and plan["selection"]["driver_request"]["selection"]["version"] == profile["native_request_version"])
    for key in ("plan_file", "binding_file", "driver_request_file"): file_pin(value[key])
    require(plan["selection"]["request_file"] == value["driver_request_file"])
    if value["failure"] is not None:
        closed(value["failure"], ("code", "phase", "diagnostic", "operational"))
        require(type(value["failure"]["code"]) is str
            and (value["failure"]["phase"] is None or type(value["failure"]["phase"]) is str)
            and all(value["failure"][key] is None or type(value["failure"][key]) is dict
                for key in ("diagnostic", "operational")))
    if value["bundle"] is not None: validate_molecular_sequence_attempt_bundle(value["bundle"], plan=plan)
    if value["declaration"] is not None:
        declaration = value["declaration"]
        closed(declaration, ("version", "mode", "operation", "request_file", "request_file_pin_verified", "attempt_identity",
            "native_call_state", "native_failure", "driver_failure", "files", "qualification"))
        require(declaration["version"] == "molecular_sequence_driver_declaration_v1" and declaration["mode"] == "native"
            and declaration["operation"] == operation and declaration["request_file_pin_verified"] is True
            and declaration["attempt_identity"] == plan["selection"]["driver_request"]["attempt_identity"]
            and declaration["request_file"] == {**plan["selection"]["request_file"], "path":
                plan["attempt_directory"] + "/inputs/driver-request.json"} and type(declaration["files"]) is dict)
    require(type(value["declarations"]) is dict and set(value["declarations"]) <= {"capture", "sheet", "components"})
    for row in value["declarations"].values(): file_declaration(row)
    require(type(value["metadata_failures"]) is list)
    for row in value["metadata_failures"]:
        closed(row, ("code", "role", "exception_type", "message"))
        require(type(row["code"]) is str and (row["role"] is None or row["role"] in ("capture", "sheet", "components"))
            and all(row[key] is None or type(row[key]) is str for key in ("exception_type", "message")))
    return value


def ordinary_molecular_sequence_packet(custody, *, operation=None):
    """Literal public packet; provenance IDs confer no artifact admission."""
    profile = _ordinary_profile(operation, _ordinary_actual(custody, "projection", "public", "operation"))
    if profile["operation"] == OPERATIONS[1]:
        from .primer_placement_result_contracts import packet
        return packet(custody)
    return dict(version=profile["public_version"],
        selection={"rows": deepcopy(custody["intent"]["arguments"]["rows"])},
        values=deepcopy(custody["projection"]["public"]),
        file_states={role: custody["source_files"][role]["state"] for role in ("capture", "sheet", "components")},
        failures=deepcopy(custody["failures"]))


def validate_ordinary_molecular_sequence_packet(value, *, operation=None):
    if type(value) is dict:
        _validate_placement_copy_inputs(value.get("values"))
    value = copy_json(value)
    if _ordinary_actual(value, "values", "operation") == OPERATIONS[1]:
        _ordinary_profile(operation, OPERATIONS[1])
        from .primer_placement_result_contracts import validate_packet
        return validate_packet(value)
    closed(value, ("version", "selection", "values", "file_states", "failures"))
    profile = _ordinary_profile(operation, _ordinary_actual(value, "values", "operation"))
    operation = profile["operation"]
    require(value["version"] == profile["public_version"])
    closed(value["selection"], ("rows",))
    selector = validate_molecular_sequence_result_selector(dict(version=profile["selector_version"], mode=MODES[0],
        operation=operation, saved_sheet_ref=None, rows=value["selection"]["rows"], return_files=[]))
    validate_molecular_sequence_fact_values(PROJECTION_SOURCE, [value["values"]])
    require(value["values"]["operation"] == operation and value["values"]["schema"] == profile["selected_values_version"])
    require([(row["row_id"], row["field"]) for row in value["values"]["rows"]] ==
        [(row["row_id"], field) for row in selector["rows"] for field in row["fields"]])
    closed(value["file_states"], ("capture", "sheet", "components"))
    require(all(state in FILE_STATES and state != "produced_unretained" for state in value["file_states"].values())
        and all(value["file_states"][role] == value["values"]["source_states"][role] for role in ("sheet", "components")))
    require(type(value["failures"]) is list)
    for row in value["failures"]: validate_failure(row)
    return value


def validate_ordinary_molecular_sequence_return(value, *, operation=None):
    if type(value) is dict:
        _validate_placement_copy_inputs(value.get("values"))
    value = copy_json(value)
    require(type(value) is dict)
    profile = _ordinary_profile(operation, _ordinary_actual(value, "values", "operation"))
    operation = profile["operation"]
    packet = {key: item for key, item in value.items() if key != "source_ref"}
    validate_ordinary_molecular_sequence_packet(packet, operation=operation)
    require(set(value) == {*packet, "source_ref"} and type(value.get("source_ref")) is str
        and re.fullmatch(r"source_[0-9a-f]{24}", value["source_ref"]) is not None)
    return value


def validate_ordinary_molecular_sequence_custody(value, *, operation=None):
    if type(value) is dict and type(value.get("projection")) is dict:
        _validate_placement_copy_inputs(value["projection"].get("public"))
    value = copy_json(value)
    closed(value, ("version", "intent", "request", "original", "source_files", "projection", "failures", "public_packet_file", "retrieved_at",
        *(("context",) if _ordinary_actual(value, "intent", "tool_name") == OPERATIONS[1] else ())))
    profile = _ordinary_profile(operation, _ordinary_actual(value, "intent", "tool_name"))
    operation = profile["operation"]
    require(value["version"] == profile["custody_version"])
    intent = validate_ordinary_molecular_sequence_intent(value["intent"], operation=operation)
    require(intent["version"] == profile["intent_version"])
    request = value["request"]
    closed(request, ("version", "arguments", "invocation", "input_binding_file"))
    require(request["version"] == profile["publication_request_version"] and request["arguments"] == intent["arguments"])
    invoke = request["invocation"]
    closed(invoke, ("run_id", "episode_id", "operation_key", "decision_index", "request_sha256", "scope"))
    require(all(invoke[key] == intent[key] for key in ("run_id", "episode_id", "operation_key", "scope"))
        and type(invoke["decision_index"]) is int and invoke["decision_index"] == int(intent["operation_key"].rsplit(":", 1)[1])
        and invoke["request_sha256"] == intent["original_request_sha256"])
    file_identity(request["input_binding_file"])
    require(request["input_binding_file"]["format"] == profile["binding_version"])
    original = value["original"]
    closed(original, ("identity", "plan_file", "driver_request_file", "native_handle_file", "native_request_file",
        "execution_file", "bundle_file", "declaration_file", "association_file"))
    for key in ("plan_file", "driver_request_file", "native_handle_file", "native_request_file", "execution_file", "association_file"):
        file_identity(original[key])
    for key in ("bundle_file", "declaration_file"):
        if original[key] is not None: file_identity(original[key])
    formats = dict(plan_file="molecular_sequence_selected_plan_v1", driver_request_file=profile["driver_request_version"],
        native_handle_file="durable_systemd_native_job_v2", native_request_file="native_local_job_request",
        execution_file=profile["execution_version"], association_file="molecular_sequence_ordinary_association_v1",
        bundle_file="molecular_sequence_attempt_bundle_v1", declaration_file="molecular_sequence_driver_declaration_v1")
    require(all(original[key] is None or original[key]["format"] == fmt for key, fmt in formats.items()))
    closed(original["identity"], ("run_id", "episode_id", "resource_id", "execution_id", "attempt_id", "operation_key", "assignment_sha256", "requested_job_sha256"))
    require(all(type(item) is str and item for item in original["identity"].values())
        and all(original["identity"][key] == intent[key] for key in ("run_id", "episode_id", "operation_key"))
        and original["identity"]["assignment_sha256"] == digest(intent["assignment"])
        and original["identity"]["attempt_id"] == digest(intent["operation_key"]))
    closed(value["source_files"], FILE_ROLES)
    for row in value["source_files"].values(): validate_file_state(row)
    require(all(value["source_files"][role] == empty_file_state("not_requested") for role in ("native_results", "native_plot")))
    projection = validate_molecular_sequence_projection(value["projection"])
    require(projection["selector"] == ordinary_molecular_sequence_selector(operation, intent["arguments"])
        and projection["source_files"] == value["source_files"]
        and projection["calculation"] == {"kind": "original_stored", "calculator_id": None}
        and projection["public"]["source_kind"] == "original_stored")
    require(projection["association"] == dict(state="verified", reason="ordinary_selected_action_and_closed_native_handle",
        proof_file=original["association_file"], original_identity=original["identity"]))
    validate_ordinary_molecular_sequence_packet(ordinary_molecular_sequence_packet(value, operation=operation), operation=operation)
    file_identity(value["public_packet_file"])
    require(value["public_packet_file"]["format"] == profile["packet_format"]
        and type(value["retrieved_at"]) is str and bool(value["retrieved_at"]))
    return value


def validate_ordinary_molecular_sequence_saved_custody(value, *, operation=None):
    """Pure saved-calculation shape; the owner authenticates all retained joins."""
    if type(value) is dict and type(value.get("projection")) is dict:
        _validate_placement_copy_inputs(value["projection"].get("public"))
    value = copy_json(value)
    closed(value, ("version", "intent", "request", "original_source", "source_files", "projection",
        "calculation", "failures", "public_packet_file", "retrieved_at",
        *(("context",) if _ordinary_actual(value, "intent", "tool_name") == OPERATIONS[1] else ())))
    profile = _ordinary_profile(operation, _ordinary_actual(value, "intent", "tool_name"))
    operation = profile["operation"]
    intent = validate_ordinary_molecular_sequence_intent(value["intent"], operation=operation)
    require(value["version"] == profile["saved_custody_version"]
        and intent["version"] == profile["saved_intent_version"]
        and intent["arguments"]["mode"] == "calculate_saved")
    request = value["request"]
    closed(request, ("version", "arguments", "invocation", "source_admission_file"))
    require(request["version"] == profile["saved_request_version"] and request["arguments"] == intent["arguments"])
    invoke = request["invocation"]
    closed(invoke, ("run_id", "episode_id", "operation_key", "decision_index", "request_sha256", "scope"))
    require(all(invoke[key] == intent[key] for key in ("run_id", "episode_id", "operation_key", "scope"))
        and type(invoke["decision_index"]) is int and invoke["decision_index"] == int(intent["operation_key"].rsplit(":", 1)[1])
        and invoke["request_sha256"] == intent["original_request_sha256"])
    file_identity(request["source_admission_file"])
    require(request["source_admission_file"]["format"] == "molecular_sequence_received_source_result_v1")
    original = value["original_source"]
    closed(original, ("source_ref", "record_sha256", "custody_file", "packet_file"))
    require(original["source_ref"] == intent["arguments"]["result_ref"]
        and type(original["record_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", original["record_sha256"]) is not None)
    for key in ("custody_file", "packet_file"): file_identity(original[key])
    closed(value["source_files"], FILE_ROLES)
    for row in value["source_files"].values(): validate_file_state(row)
    require(all(value["source_files"][role] == empty_file_state("not_requested")
        for role in ("capture", "native_results", "native_plot")))
    require(value["source_files"]["sheet"]["file"] is not None)
    calculation = value["calculation"]
    closed(calculation, ("calculator_id", "native_call_state", "state", "call_count", "started_file", "result_file", "diagnostic_file"))
    require(calculation["calculator_id"] == profile["calculator_id"] and calculation["native_call_state"] == "not_requested"
        and calculation["state"] in ("returned", "raised")
        and (calculation["call_count"] is None or type(calculation["call_count"]) is int and calculation["call_count"] == 1)
        and (calculation["state"] != "returned" or calculation["call_count"] == 1))
    for key in ("started_file", "result_file", "diagnostic_file"): file_identity(calculation[key])
    require(calculation["started_file"]["format"] == profile["calculation_started_version"]
        and calculation["result_file"]["format"] == profile["calculation_result_version"]
        and calculation["diagnostic_file"]["format"] == profile["calculation_diagnostic_version"])
    projection = validate_molecular_sequence_projection(value["projection"])
    require(projection["source_files"] == value["source_files"]
        and projection["selector"] == validate_molecular_sequence_result_selector(dict(version=profile["selector_version"],
            mode=MODES[1], operation=operation, saved_sheet_ref=value["source_files"]["sheet"]["file"]["artifact_ref"],
            rows=intent["arguments"]["rows"], return_files=[]))
        and projection["calculation"] == {"kind": "selected_saved_calculation", "calculator_id": profile["calculator_id"]})
    require(projection["public"]["source_kind"] == "selected_saved_calculation")
    validate_ordinary_molecular_sequence_packet(ordinary_molecular_sequence_packet(value, operation=operation), operation=operation)
    require(type(value["failures"]) is list)
    for row in value["failures"]: validate_failure(row)
    file_identity(value["public_packet_file"])
    require(value["public_packet_file"]["format"] == profile["packet_format"]
        and type(value["retrieved_at"]) is str and bool(value["retrieved_at"]))
    return value


def ordinary_molecular_sequence_fact_sources(operation):
    """One Source-owned view; private artifact IDs remain opaque strings."""
    profile = ordinary_molecular_sequence_profile(operation)
    if operation == OPERATIONS[1]:
        from .primer_placement_result_contracts import fact_sources
        return fact_sources()
    selection_profile = _N_PROFILE if operation == OPERATIONS[2] else _O_PROFILE if operation == OPERATIONS[3] else _LEGACY_PROFILE
    original = molecular_sequence_fact_sources(profile=selection_profile)
    projection = deepcopy(original[PROJECTION_SOURCE]["report_schema"]["items"]["anyOf"][0])
    issue = deepcopy(original[FAILURE_SOURCE]["report_schema"]["items"])
    def opaque_artifacts(node):
        if type(node) is dict:
            if node.get("x-reference-namespace") == "artifact":
                node.pop("format", None); node.pop("x-reference-namespace", None)
            for item in node.values(): opaque_artifacts(item)
        elif type(node) is list:
            for item in node: opaque_artifacts(item)
    opaque_artifacts(projection); opaque_artifacts(issue)
    def obj(fields):
        return dict(type="object", properties=fields, required=list(fields), additionalProperties=False)
    selector_variants = []
    for row_id_value in ({"kind": "summary"}, ({"kind": "glycosylation_site", "row_ordinal": 0} if operation in OPERATIONS[2:4] else {"kind": "orf", "row_index": 0})):
        identity = obj({key: {"const": value, "type": "string"} if key == "kind" else
            {"type": "integer", "minimum": 0} for key, value in row_id_value.items()})
        selector_variants.append(obj({"row_id": identity, "fields": {"type": "array", "minItems": 1,
            "uniqueItems": True, "items": {"type": "string", "enum": list(field_table(operation, row_id_value, profile=selection_profile))}}}))
    row_selector = {"anyOf": selector_variants}
    item = obj({"version": {"const": profile["public_version"], "type": "string"},
        "source_ref": {"type": "string", "pattern": "^source_[0-9a-f]{24}$", "format": "reference", "x-reference-namespace": "source"},
        "selection": obj({"rows": {"type": "array", "items": row_selector}}), "values": projection,
        "file_states": obj({role: {"type": "string", "enum": [s for s in FILE_STATES if s != "produced_unretained"]}
            for role in ("capture", "sheet", "components")}), "failures": {"type": "array", "items": issue}})
    description = "Explicit selected literal ORF values and original qualifications from an authenticated ordinary Source; artifact provenance strings grant no Files"
    if operation == OPERATIONS[2]:
        description = "Explicit selected literal N-glycosylation motif values, overlap provenance, source paths and original qualifications from an authenticated ordinary Source; artifact provenance strings grant no Files"
    elif operation == OPERATIONS[3]:
        description = "Explicit selected literal O-glycosylation S/T-density heuristic values, window and threshold provenance, source paths and original qualifications from an authenticated ordinary Source; not occupancy or calibrated probability; artifact provenance strings grant no Files"
    return {profile["fact_source"]: {"type": "array", "report_schema": {"type": "array", "items": item, "x-source": profile["fact_source"]},
        "description": description, "meaning": description}}
