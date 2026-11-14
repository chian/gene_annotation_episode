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


OPERATIONS = ("analyze_protease_kinetics",)
SELECTOR_VERSION = "molecular_sequence_result_selector_v1"
PLAN_VERSION = "molecular_sequence_result_worker_plan_v1"
RESULT_VERSION = "molecular_sequence_result_worker_result_v1"
PROJECTION_VERSION = "molecular_sequence_private_projection_v1"
PUBLIC_VERSION = "molecular_sequence_selected_values_v1"
PROTEASE_SELECTOR_VERSION = "molecular_sequence_result_selector_v5"
PROTEASE_PROJECTION_VERSION = "molecular_sequence_private_projection_v4"
PROTEASE_PUBLIC_VERSION = "molecular_sequence_selected_values_v4"
PROTEASE_CONTEXT_VERSION = "protease_kinetics_public_context_v1"
_LEGACY_PROFILE = "legacy_v1"
_PROTEASE_PROFILE = "protease_kinetics_v5"
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
SCHEMAS = {"analyze_protease_kinetics": ("protease_kinetics_sheet_v1", ("protease_kinetics_components_v1", "protease_kinetics_components_v2"))}
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
    fields = {"summary": (), "protease_fit": (), "protease_curve": ("substrate_ordinal",),
        "protease_quantity": ("quantity",), "protease_covariance": ("parameter_i", "parameter_j")}
    require(value["kind"] in fields)
    closed(value, ("kind", *fields[value["kind"]]))
    for key in fields[value["kind"]]:
        require(value[key] in QUANTITIES if key == "quantity" else type(value[key]) is int and value[key] >= 0)
        if key in ("parameter_i", "parameter_j"):
            require(value[key] in (0, 1))
    return deepcopy(value)


def field_table(operation, identity, *, profile=_LEGACY_PROFILE):
    """Map semantic names to exact stored paths/types/populations; no formula."""
    require(profile in (_LEGACY_PROFILE, _PROTEASE_PROFILE) and operation in OPERATIONS)
    row_id(identity)
    kind = identity["kind"]
    table = {}
    def add(name, path, typ="count", unit="unknown", population="retained_rows", denominators=()):
        table[name] = (path, typ, unit, population, tuple(denominators))
    if operation in OPERATIONS:
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
    require(value["operation"] in OPERATIONS)
    if value["version"] == SELECTOR_VERSION:
        return _LEGACY_PROFILE
    require(value["version"] == PROTEASE_SELECTOR_VERSION)
    return _PROTEASE_PROFILE


def _public_profile(value):
    require(type(value) is dict and value.get("operation") in OPERATIONS)
    if value.get("schema") == PUBLIC_VERSION:
        return _LEGACY_PROFILE
    require(value.get("schema") == PROTEASE_PUBLIC_VERSION)
    return _PROTEASE_PROFILE


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
    if typ == "number": return type(value) is int or type(value) is float and math.isfinite(value)
    if typ in ("count", "int"): return type(value) is int and (typ == "int" or value >= 0)
    if typ == "bool": return type(value) is bool
    if typ == "text": return type(value) is str
    if type(typ) is str and typ.startswith("protease_"):
        return _valid_protease_literal(value, typ)
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
                    "number", sources[role])
                operand_kind = "denominator"
                operand_unit = None
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
    public = dict(schema={_LEGACY_PROFILE: PUBLIC_VERSION, _PROTEASE_PROFILE: PROTEASE_PUBLIC_VERSION}[profile], operation=operation, source_kind="original_stored" if selection["mode"] == MODES[0] else "selected_saved_calculation",
        source_sheet_ref=None if sources["sheet"]["file"] is None else sources["sheet"]["file"]["artifact_ref"],
        source_components_ref=None if sources["components"]["file"] is None else sources["components"]["file"]["artifact_ref"],
        source_states={role: sources[role]["state"] for role in ("sheet", "components")}, components_schema=schema,
        original_attempt_association="unavailable" if association is None else association["state"], rows=rows, failures=issues)
    if profile == _PROTEASE_PROFILE: public["context"] = _protease_context(sheet, components, sources)
    return dict(schema={_LEGACY_PROFILE: PROJECTION_VERSION, _PROTEASE_PROFILE: PROTEASE_PROJECTION_VERSION}[profile], selector=selection, source_files=sources, association=deepcopy(association),
        calculation=deepcopy(calculation), public=public)


def validate_molecular_sequence_projection(value):
    closed(value, ("schema", "selector", "source_files", "association", "calculation", "public"))
    selector = validate_molecular_sequence_result_selector(value["selector"])
    profile = _selector_profile(selector)
    require(value["schema"] == {_LEGACY_PROFILE: PROJECTION_VERSION, _PROTEASE_PROFILE: PROTEASE_PROJECTION_VERSION}[profile]
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
    rows = copy_json(rows)
    require(source in FACT_SOURCES and type(rows) is list)
    for value in rows:
        require(type(value) is dict)
        if source == FAILURE_SOURCE:
            validate_failure(value)
            continue
        if source == SAVED_SOURCE:
            closed(value, ("operation", "role", "artifact_ref", "source_kind", "source_sheet_ref", "components_schema"))
            require(value["operation"] in OPERATIONS and value["role"] in FILE_ROLES and reference(value["artifact_ref"]))
            require(value["source_kind"] in ("original_stored", "selected_saved_calculation") and
                (value["source_sheet_ref"] is None or reference(value["source_sheet_ref"])))
            require(value["components_schema"] is None or value["components_schema"] in SCHEMAS[value["operation"]][1])
            continue
        profile = _public_profile(value)
        closed(value, ("schema", "operation", "source_kind", "source_sheet_ref", "source_components_ref", "source_states",
            "components_schema", "original_attempt_association", "rows", "failures", *(("context",) if profile == _PROTEASE_PROFILE else ())))
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
        for row in value["rows"]:
            closed(row, ("row_id", "field", "value_state", "value", "source_ref", "source_pointer", "source_state", "unit", "population_id", "denominators", "scientific_qualifiers"))
            table = field_table(value["operation"], row["row_id"], profile=profile); require(row["field"] in table)
            path, typ, _unit, population, _denominators = table[row["field"]]
            require(row["source_pointer"] == path and row["population_id"] == population)
            _validate_stored({k: row[k] for k in ("value_state", "value", "source_ref", "source_pointer", "source_state")})
            require(row["source_ref"] == value["source_components_ref"] and row["source_state"] == value["source_states"]["components"])
            require(row["value_state"] != "stored_value" or valid_type(row["value"], typ))
            require(row["unit"] is None or type(row["unit"]) is str)
            if profile == _PROTEASE_PROFILE:
                require(row["unit"] == _protease_selected_unit(row, value["context"], _unit))
            require(type(row["denominators"]) is list)
            require([r["source_pointer"] for r in row["denominators"]] == list(_denominators))
            for denominator in row["denominators"]:
                closed(denominator, ("value_state", "value", "source_ref", "source_pointer", "source_state", "kind", "unit", "unit_sources"))
                _validate_stored({k: denominator[k] for k in ("value_state", "value", "source_ref", "source_pointer", "source_state")})
                require(denominator["value_state"] != "stored_value" or valid_type(denominator["value"], "number"))
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
        for issue in value["failures"]: validate_failure(issue)
    return rows


def validate_molecular_sequence_result_worker_plan(value):
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


def molecular_sequence_fact_sources(*, profile=_LEGACY_PROFILE):
    """Closed private definitions; no public episode/catalog is registered."""
    require(profile in (_LEGACY_PROFILE, _PROTEASE_PROFILE))
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
        if type(typ) is str and typ.startswith("protease_"):
            return _protease_literal_schema(typ, obj=obj, nullable=nullable, arr=arr)
        return text
    def stored_schema(typ):
        return obj({"value_state": {"type": "string", "enum": list(VALUE_STATES)}, "value": nullable(typed(typ)),
            "source_ref": nullable(ref), "source_pointer": {"type": "string", "pattern": "^/"},
            "source_state": {"type": "string", "enum": [s for s in FILE_STATES if s != "produced_unretained"]}})
    identifiers = [{"kind": "summary"}, {"kind": "protease_fit"}, {"kind": "protease_curve", "substrate_ordinal": 0},
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
    for operation in OPERATIONS:
        variants = []
        for identity in identifiers:
            table = field_table(operation, identity, profile=profile)
            if not table: continue
            specs = {}; unavailable = {role: empty_file_state() for role in FILE_ROLES}
            qualifier = _qualifiers(operation, identity, None, {"schema": SCHEMAS[operation][1][-1]}, unavailable, specs)
            reason_union = tuple(dict.fromkeys((*REASONS["protease_kinetics_components_v1"], *REASONS["protease_kinetics_components_v2"])))
            qualifier_schema = obj({"schema": {"type": "string", "const": qualifier["schema"]},
                "operation": {"type": "string", "const": operation}, "component_schema": nullable({"type": "string", "enum": list(SCHEMAS[operation][1])}),
                "states": obj({name: stored_schema(reason_union if "reason" in name and operation == OPERATIONS[0] else spec[1]) for name, spec in specs.items()}),
                "interpretation": {"type": "string", "const": qualifier["interpretation"]}})
            denominator = stored_schema("number")
            denominator["properties"].update(kind={"type": "string", "enum": ["numerator", "denominator", "calibration_response", "enzyme_concentration", "product_per_cleavage"]},
                unit=nullable(text), unit_sources=arr(stored_schema("text")))
            denominator["required"] = list(denominator["properties"])
            cell = obj({"row_id": id_schema(identity), "field": {"type": "string", "enum": list(table)},
                **stored_schema("number")["properties"], "unit": nullable(text), "population_id": {"type": "string", "enum": list(dict.fromkeys(spec[3] for spec in table.values()))},
                "denominators": arr(denominator), "scientific_qualifiers": qualifier_schema})
            cell["properties"]["value"] = nullable(scalar)
            if profile == _PROTEASE_PROFILE and identity["kind"] == "protease_covariance":
                cell["properties"]["value"] = nullable(typed("protease_native_literal"))
            cell["allOf"] = [{"if": {"properties": {"field": {"const": name}}}, "then": {"properties": {"value": nullable(typed(spec[1]))}}} for name, spec in table.items()]
            for branch, spec in zip(cell["allOf"], table.values()):
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
            variants.append(cell)
        projection = obj({"schema": {"type": "string", "const": {_LEGACY_PROFILE: PUBLIC_VERSION, _PROTEASE_PROFILE: PROTEASE_PUBLIC_VERSION}[profile]}, "operation": {"type": "string", "const": operation},
            "source_kind": {"type": "string", "enum": ["original_stored", "selected_saved_calculation"]}, "source_sheet_ref": nullable(ref), "source_components_ref": nullable(ref),
            "source_states": obj({role: {"type": "string", "enum": [s for s in FILE_STATES if s != "produced_unretained"]} for role in ("sheet", "components")}),
            "components_schema": nullable({"type": "string", "enum": list(SCHEMAS[operation][1])}),
            "original_attempt_association": {"type": "string", "enum": ["verified", "unavailable", "conflict"]}, "rows": arr({"anyOf": variants}), "failures": arr(failure_schema)})
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
    return result


