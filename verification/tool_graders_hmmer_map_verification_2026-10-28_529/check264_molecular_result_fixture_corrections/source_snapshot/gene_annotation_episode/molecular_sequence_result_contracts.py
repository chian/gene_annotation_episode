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


OPERATIONS = ("annotate_open_reading_frames", "align_sequences", "find_n_glycosylation_motifs",
    "predict_o_glycosylation_hotspots", "analyze_protease_kinetics")
SELECTOR_VERSION = "molecular_sequence_result_selector_v1"
PLAN_VERSION = "molecular_sequence_result_worker_plan_v1"
RESULT_VERSION = "molecular_sequence_result_worker_result_v1"
PROJECTION_VERSION = "molecular_sequence_private_projection_v1"
PUBLIC_VERSION = "molecular_sequence_selected_values_v1"
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
PLACEMENT_SUMMARY = ("target_length_symbols", "requested_primer_occurrence_count", "native_group_count", "known_native_hit_list_count",
    "retained_native_hit_occurrence_count", "usable_saved_hit_count", "plus_hit_count", "minus_hit_count", "strand_known_hit_count",
    "source_compatible_hit_count", "mismatch_count_sum", "mismatch_count_denominator_hits")
GLYCO_SUMMARY = ("original_symbol_count", "processed_symbol_count", "native_reported_sequence_length", "native_reported_total_count",
    "retained_printed_row_count", "usable_checked_row_count", "malformed_row_count", "native_reported_remaining_count",
    "unretained_reported_row_count", "native_total_operand_upper_bound", "native_log_complete", "native_report_complete",
    "scan_exhaustiveness_verified", "native_count_rows_compatible", "native_metadata_matches_operands", "native_total_within_operand_upper_bound")


def field_table(operation, identity):
    """Map semantic names to exact stored paths/types/populations; no formula."""
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
    return table


def validate_molecular_sequence_result_selector(value):
    value = copy_json(value)
    closed(value, ("version", "mode", "operation", "saved_sheet_ref", "rows", "return_files"))
    require(value["version"] == SELECTOR_VERSION and value["mode"] in MODES and value["operation"] in OPERATIONS)
    require(value["saved_sheet_ref"] is None if value["mode"] == "original_attempt" else reference(value["saved_sheet_ref"]))
    require(type(value["rows"]) is list and type(value["return_files"]) is list and all(role in FILE_ROLES for role in value["return_files"])
        and len(set(value["return_files"])) == len(value["return_files"]))
    seen = set()
    for row in value["rows"]:
        closed(row, ("row_id", "fields")); row_id(row["row_id"])
        key = canonical(row["row_id"]); require(key not in seen); seen.add(key)
        fields = row["fields"]; table = field_table(value["operation"], row["row_id"])
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
    if typ == "number": return type(value) is int or type(value) is float and math.isfinite(value)
    if typ in ("count", "int"): return type(value) is int and (typ == "int" or value >= 0)
    if typ == "bool": return type(value) is bool
    if typ == "text": return type(value) is str
    if typ == "interval": return type(value) is list and len(value) == 2 and all(type(v) is int and v >= 0 for v in value) and value[0] <= value[1]
    if typ == "frame": return type(value) is int and value in (-3, -2, -1, 1, 2, 3)
    if typ == "strand": return value in ("+", "-") and type(value) is str
    if typ == "compatibility": return type(value) is str and value in ("compatible", "incompatible", "unknown")
    if type(typ) is tuple: return type(value) is str and value in typ
    if typ == "ordinals": return type(value) is list and all(type(v) is int and v >= 0 for v in value)
    if typ == "fit_codes": return type(value) is list and all(type(v) is str and v in FIT_CODES for v in value)
    return False


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


def select_stored_molecular_sequence_values(*, operation, sheet, components, selection, source_files, association=None, calculation=None):
    selection = validate_molecular_sequence_result_selector(selection)
    require(operation == selection["operation"])
    closed(source_files, FILE_ROLES)
    sources = {role: validate_file_state(value) for role, value in source_files.items()}
    schema = None if components is None else components.get("schema")
    require(components is None or type(components) is dict and schema in SCHEMAS[operation][1], "molecular_sequence_component_schema")
    require(sheet is None or type(sheet) is dict and sheet.get("schema") == SCHEMAS[operation][0], "molecular_sequence_sheet_schema")
    rows, issues = [], []
    for request in selection["rows"]:
        identity, table = request["row_id"], field_table(operation, request["row_id"])
        qualifiers = _qualifiers(operation, identity, sheet, components, sources)
        for name in request["fields"]:
            path, typ, unit, population, denominator_paths = table[name]
            cell = stored(components, path, typ, sources["components"])
            if unit == "stored_quantity_unit": unit = pointer(components, "/physical_components/" + identity["quantity"] + "/unit")
            elif unit == "stored_variance_unit": unit = pointer(components, "/physical_components/" + identity["quantity"] + "/uncertainty/variance_unit")
            elif unit in ("stored_vmax_unit", "stored_km_unit"): unit = pointer(components, "/fit_components/" + ("km" if unit == "stored_km_unit" else "vmax") + "/unit")
            elif unit == "stored_parameter_units_product": unit = "unknown"  # Raw matrix kept; no multiplication of labels inferred.
            unit = unit if type(unit) is str else None
            denominators = []
            for denominator_path in denominator_paths:
                role = "sheet" if denominator_path.startswith(("/assay_context/", "/measurements/")) else "components"
                operand = stored(sheet if role == "sheet" else components, denominator_path, "number", sources[role])
                operand_kind = "numerator" if denominator_path.endswith(("/numerator", "/st_count", "/retained_length_sum_nt")) else "denominator"
                operand_unit = "nt_symbols" if denominator_path.endswith("/retained_length_sum_nt") else "rows" if denominator_path.endswith("/retained_length_denominator_rows") else "symbols" if "/mismatch_fraction/" in denominator_path or denominator_path.endswith(("/st_count", "/window_denominator_symbols")) else None
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
    public = dict(schema=PUBLIC_VERSION, operation=operation, source_kind="original_stored" if selection["mode"] == MODES[0] else "selected_saved_calculation",
        source_sheet_ref=None if sources["sheet"]["file"] is None else sources["sheet"]["file"]["artifact_ref"],
        source_components_ref=None if sources["components"]["file"] is None else sources["components"]["file"]["artifact_ref"],
        source_states={role: sources[role]["state"] for role in ("sheet", "components")}, components_schema=schema,
        original_attempt_association="unavailable" if association is None else association["state"], rows=rows, failures=issues)
    return dict(schema=PROJECTION_VERSION, selector=selection, source_files=sources, association=deepcopy(association),
        calculation=deepcopy(calculation), public=public)


def validate_molecular_sequence_projection(value):
    closed(value, ("schema", "selector", "source_files", "association", "calculation", "public"))
    require(value["schema"] == PROJECTION_VERSION)
    selector = validate_molecular_sequence_result_selector(value["selector"])
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
        closed(value, ("schema", "operation", "source_kind", "source_sheet_ref", "source_components_ref", "source_states",
            "components_schema", "original_attempt_association", "rows", "failures"))
        require(value["schema"] == PUBLIC_VERSION and value["operation"] in OPERATIONS and value["source_kind"] in ("original_stored", "selected_saved_calculation"))
        require(value["original_attempt_association"] in ("verified", "unavailable", "conflict"))
        require(all(value[k] is None or reference(value[k]) for k in ("source_sheet_ref", "source_components_ref")))
        closed(value["source_states"], ("sheet", "components")); require(all(s in FILE_STATES for s in value["source_states"].values()))
        require(allow_unretained or "produced_unretained" not in value["source_states"].values())
        require(value["components_schema"] is None or value["components_schema"] in SCHEMAS[value["operation"]][1])
        require(type(value["rows"]) is list and type(value["failures"]) is list)
        for row in value["rows"]:
            closed(row, ("row_id", "field", "value_state", "value", "source_ref", "source_pointer", "source_state", "unit", "population_id", "denominators", "scientific_qualifiers"))
            table = field_table(value["operation"], row["row_id"]); require(row["field"] in table)
            path, typ, _unit, population, _denominators = table[row["field"]]
            require(row["source_pointer"] == path and row["population_id"] == population)
            _validate_stored({k: row[k] for k in ("value_state", "value", "source_ref", "source_pointer", "source_state")})
            require(row["source_ref"] == value["source_components_ref"] and row["source_state"] == value["source_states"]["components"])
            require(row["value_state"] != "stored_value" or valid_type(row["value"], typ))
            require(row["unit"] is None or type(row["unit"]) is str)
            require(type(row["denominators"]) is list)
            require([r["source_pointer"] for r in row["denominators"]] == list(_denominators))
            for denominator in row["denominators"]:
                closed(denominator, ("value_state", "value", "source_ref", "source_pointer", "source_state", "kind", "unit", "unit_sources"))
                _validate_stored({k: denominator[k] for k in ("value_state", "value", "source_ref", "source_pointer", "source_state")})
                require(denominator["value_state"] != "stored_value" or valid_type(denominator["value"], "number"))
                require(denominator["kind"] in ("numerator", "denominator", "calibration_response", "enzyme_concentration", "product_per_cleavage")
                    and (denominator["unit"] is None or type(denominator["unit"]) is str) and type(denominator["unit_sources"]) is list)
                for unit_source in denominator["unit_sources"]:
                    _validate_stored(unit_source)
                    require(unit_source["value_state"] != "stored_value" or valid_type(unit_source["value"], "text"))
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
        for issue in value["failures"]: validate_failure(issue)
    return rows


def validate_molecular_sequence_result_worker_plan(value):
    if type(value) is dict and value.get("version") == "molecular_sequence_result_worker_plan_v2":
        return validate_supplied_worker_plan(value)
    closed(value, ("version", "directory", "selector", "source_files", "inputs", "association", "received_sheet_receipt_file", "software", "selected_environment", "policy"))
    require(value["version"] == PLAN_VERSION and type(value["directory"]) is str and value["directory"].startswith("/"))
    require(value["policy"] == {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None})
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


def molecular_sequence_fact_sources():
    """Closed private definitions; no public episode/catalog is registered."""
    def obj(properties):
        return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}
    def nullable(schema): return {"anyOf": [schema, {"type": "null"}]}
    def arr(schema): return {"type": "array", "items": schema}
    ref = {"type": "string", "pattern": "^artifact_[0-9a-f]{64}$", "format": "reference", "x-reference-namespace": "artifact"}
    text = {"type": "string"}
    scalar = {"anyOf": [{"type": "number"}, {"type": "boolean"}, text, {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer", "minimum": 0}}]}
    def typed(typ):
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
    def id_schema(identity):
        return obj({key: {"type": "string", "const": value} if key == "kind" else
            {"type": "string", "enum": list(QUANTITIES)} if key == "quantity" else
            {"type": "integer", "minimum": 0, **({"maximum": 1} if key in ("parameter_i", "parameter_j") else {})}
            for key, value in identity.items()})
    failure_schema = obj({"code": {"type": "string", "enum": list(FAILURES)}, "stage": {"type": "string", "enum": list(STAGES)},
        "role": nullable({"type": "string", "enum": list(FILE_ROLES)}), "row_id": nullable({"anyOf": [id_schema(i) for i in identifiers]}),
        "source_ref": nullable(ref), "source_pointer": nullable({"type": "string", "pattern": "^/"}), "diagnostic_ref": nullable(ref)})
    projections = []
    for operation in OPERATIONS:
        variants = []
        for identity in identifiers:
            table = field_table(operation, identity)
            if not table: continue
            specs = {}; unavailable = {role: empty_file_state() for role in FILE_ROLES}
            qualifier = _qualifiers(operation, identity, None, {"schema": SCHEMAS[operation][1][-1]}, unavailable, specs)
            reason_union = tuple(dict.fromkeys((*REASONS["protease_kinetics_components_v1"], *REASONS["protease_kinetics_components_v2"])))
            qualifier_schema = obj({"schema": {"type": "string", "const": qualifier["schema"]},
                "operation": {"type": "string", "const": operation}, "component_schema": nullable({"type": "string", "enum": list(SCHEMAS[operation][1])}),
                "states": obj({name: stored_schema(reason_union if "reason" in name and operation == OPERATIONS[4] else spec[1]) for name, spec in specs.items()}),
                "interpretation": {"type": "string", "const": qualifier["interpretation"]}})
            denominator = stored_schema("number")
            denominator["properties"].update(kind={"type": "string", "enum": ["numerator", "denominator", "calibration_response", "enzyme_concentration", "product_per_cleavage"]},
                unit=nullable(text), unit_sources=arr(stored_schema("text")))
            denominator["required"] = list(denominator["properties"])
            cell = obj({"row_id": id_schema(identity), "field": {"type": "string", "enum": list(table)},
                **stored_schema("number")["properties"], "unit": nullable(text), "population_id": {"type": "string", "enum": list(dict.fromkeys(spec[3] for spec in table.values()))},
                "denominators": arr(denominator), "scientific_qualifiers": qualifier_schema})
            cell["properties"]["value"] = nullable(scalar)
            cell["allOf"] = [{"if": {"properties": {"field": {"const": name}}}, "then": {"properties": {"value": nullable(typed(spec[1]))}}} for name, spec in table.items()]
            variants.append(cell)
        projections.append(obj({"schema": {"type": "string", "const": PUBLIC_VERSION}, "operation": {"type": "string", "const": operation},
            "source_kind": {"type": "string", "enum": ["original_stored", "selected_saved_calculation"]}, "source_sheet_ref": nullable(ref), "source_components_ref": nullable(ref),
            "source_states": obj({role: {"type": "string", "enum": [s for s in FILE_STATES if s != "produced_unretained"]} for role in ("sheet", "components")}),
            "components_schema": nullable({"type": "string", "enum": list(SCHEMAS[operation][1])}),
            "original_attempt_association": {"type": "string", "enum": ["verified", "unavailable", "conflict"]}, "rows": arr({"anyOf": variants}), "failures": arr(failure_schema)}))
    saved_schema = obj({"operation": {"type": "string", "enum": list(OPERATIONS)}, "role": {"type": "string", "enum": list(FILE_ROLES)},
        "artifact_ref": ref, "source_kind": {"type": "string", "enum": ["original_stored", "selected_saved_calculation"]}, "source_sheet_ref": nullable(ref),
        "components_schema": nullable({"type": "string", "enum": list(dict.fromkeys(schema for values in SCHEMAS.values() for schema in values[1]))})})
    return {source: {"report_schema": {**arr(item), "x-source": source}, "description": description} for source, item, description in (
        (PROJECTION_SOURCE, {"anyOf": projections}, "Selected stored molecular values with their original scientific qualification"),
        (SAVED_SOURCE, saved_schema, "Explicit selected retained molecular artifact references"),
        (FAILURE_SOURCE, failure_schema, "Attributable molecular result availability failures"))}


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
    policy = value["policy"]; closed(policy, ("memory_bytes", "scratch_bytes", "wall_seconds"))
    require(type(policy["memory_bytes"]) is int and 0 < policy["memory_bytes"] <= 21474836480
        and type(policy["scratch_bytes"]) is int and 0 < policy["scratch_bytes"] <= 4294967296)
    wall = policy["wall_seconds"]
    require(wall is None or type(wall) in (int, float) and math.isfinite(wall) and wall > 0)
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
