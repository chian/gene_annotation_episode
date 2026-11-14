"""Saved association checks and native views; no source parsing or rescoring.

Immutable original-operation snapshots supply numerical truth. These functions
check closed meanings and copy retained source/derived quantities; they never
decode images, acquire source bytes, invoke the reader/calculator or fit a model.
"""
from copy import deepcopy
import hashlib
import json
import math

from .domain import canonical
from .literature_experimental_contracts import ExperimentalContractError
from .literature_binding_interaction_inputs import (
    VERSION as INPUT_VERSION, OUTPUT_VERSION, ROLES, ID_FIELDS, CONTEXT_FIELDS,
    MEASUREMENT_STATUSES, SCALAR_STATUSES, UNCERTAINTY_REASONS,
    ROLE_UNAVAILABLE_REASONS, CALCULATION_INPUT_STATUSES,
)

VERSION = "binding_interaction_saved_validation_v1"
RAW_COMPONENTS = ("parameter_rr", "parameter_rt", "parameter_tr", "parameter_tt")
COMPONENTS = (*RAW_COMPONENTS, "reference_subject_ratio", "test_subject_ratio", "interaction_ratio", "log_interaction")
MODEL_COMPONENTS = ("log_interaction_variance", "log_interaction_standard_uncertainty", "signed_profile_log_ratio", "signed_index")
FORMULA_CODES = {name: "binding_interaction_" + name for name in COMPONENTS}
CALCULATION_REASONS = (
    *("missing_operand:" + r for r in ROLES), *("unreported_operand:" + r for r in ROLES),
    "reused_source_token", "reused_physical_fit", "ligand_roles_not_distinct", "subject_roles_not_distinct",
    "opposing_reported_limits", "numerical_representation_range", "common_conditions_claim_conflicts_with_canonical_ids",
    *(name + "_" + status for name in ("within_reference_subject", "within_test_subject", "ligand_correspondence",
        "parameter_definition", "separate_assays") for status in ("unknown", "conflicting")),
    *("canonical_" + name + "_" + status for name in ("subject", "construct", "state", "parameter_definition", "readout",
        "normalization", "ligand") for status in ("unknown", "conflicting")),
    *("common_conditions_" + status for status in ("unknown", "not_matched", "conflicting")),
)
UNAVAILABLE_REASONS = (*CALCULATION_REASONS, *CALCULATION_INPUT_STATUSES[1:],
    *("source_" + status for status in MEASUREMENT_STATUSES))


def _fail(field):
    raise ExperimentalContractError("binding_interaction_saved_mismatch", field)


def _same(left, right, field):
    try:
        equal = canonical(left) == canonical(right)
    except (ValueError, TypeError, OverflowError):
        equal = False
    if not equal:
        _fail(field)


def _keys(value, keys, field):
    if type(value) is not dict or set(value) != set(keys):
        _fail(field)


def _number(value, field, nullable=True):
    if value is None and nullable:
        return
    if type(value) not in (int, float) or not math.isfinite(value):
        _fail(field)


def _text(value, field, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or not value.strip():
        _fail(field)


def _enum(value, values, field):
    if value not in values or value is not None and type(value) is not str:
        _fail(field)


def _measurement(value, field):
    if value is None:
        return
    _keys(value, ("value", "relation", "reported_spread"), field)
    _number(value["value"], field)
    _number(value["reported_spread"], field)
    _enum(value["relation"], ("eq", "lt", "le", "gt", "ge", "unreported"), field)
    if value["relation"] == "unreported":
        if value["value"] is not None or value["reported_spread"] is not None:
            _fail(field)
    elif value["value"] is None or value["value"] <= 0:
        _fail(field)
    if value["reported_spread"] is not None and (value["reported_spread"] < 0 or value["relation"] != "eq"):
        _fail(field)


def _witness(selected, result, field):
    _keys(result, ("witness", "artifact_ref", "canonical_locator", "authentication", "interpretation_attribution", "error"), field)
    _same(selected, result["witness"], field)
    _same(result["interpretation_attribution"], "investigating_episode_interpretation", field)
    _text(result["artifact_ref"], field, True)
    if result["error"] is not None:
        _keys(result["error"], ("code", "field"), field)
        return
    if selected["kind"] == "text":
        _same(result["authentication"], "exact_utf8_byte_span", field)
        if (type(selected["start"]) is not int or type(selected["end"]) is not int
                or selected["start"] < 0 or len(selected["quote"].encode()) != selected["end"] - selected["start"]):
            _fail(field)
        _same(result["canonical_locator"], None, field)
    else:
        _same(result["authentication"], "image_bytes_and_geometry_only", field)
        located = result["canonical_locator"]
        _keys(located, ("original_source_ref", "original_artifact_ref", "image_region"), field)
        for name in ("original_source_ref", "original_artifact_ref"):
            _text(located[name], field)
        box = located["image_region"]
        if (type(box) is not list or len(box) != 4 or any(type(n) is not int or n < 0 for n in box)
                or box[0] >= box[2] or box[1] >= box[3]):
            _fail(field)


def _literal(selected, result, field):
    _keys(result, ("status", "declared_status", "candidates", "fragments", "interpretation_attribution"), field)
    _same(result["interpretation_attribution"], "investigating_episode_interpretation", field)
    if selected is None:
        _same({k: result[k] for k in ("status", "declared_status", "candidates", "fragments")},
            {"status": "not_selected", "declared_status": None, "candidates": [], "fragments": []}, field)
        return
    _same(result["declared_status"], selected["status"], field)
    for name in ("candidates", "fragments"):
        if len(selected[name]) != len(result[name]):
            _fail(field)
        for left, right in zip(selected[name], result[name]):
            _witness(left, right, field)
    failed = any(w["error"] for name in ("candidates", "fragments") for w in result[name])
    _same(result["status"], "source_unavailable" if failed else selected["status"], field)


def _meaning(selected, result, field):
    _keys(result, ("value", "witnesses", "status", "interpretation_attribution"), field)
    _same(result["value"], selected["value"], field)
    _same(result["interpretation_attribution"], "investigating_episode_interpretation", field)
    if len(result["witnesses"]) != len(selected["witnesses"]):
        _fail(field)
    for a, b in zip(selected["witnesses"], result["witnesses"]):
        _witness(a, b, field)
    _same(result["status"], "source_unavailable" if any(w["error"] for w in result["witnesses"]) else "interpreted", field)


def _scalar(selected, result, field):
    _keys(result, ("literal", "status", "value", "relation", "approximate", "percent", "raw_number", "qualification_origin", "error"), field)
    _literal(selected, result["literal"], field)
    _enum(result["status"], SCALAR_STATUSES, field)
    _number(result["value"], field)
    _enum(result["relation"], (None, "eq", "lt", "le", "gt", "ge"), field)
    _enum(result["qualification_origin"], (None, "selected_literal", "retained_text_context"), field)
    if type(result["approximate"]) is not bool or type(result["percent"]) is not bool:
        _fail(field)
    _text(result["raw_number"], field, True)


def _digest(value, unicode=False):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=not unicode, allow_nan=False).encode()).hexdigest()


def _locator(witness):
    if witness is None or witness["error"]:
        return None
    selected = witness["witness"]
    if selected["kind"] == "image":
        location = witness["canonical_locator"]
        return {"source_ref": location["original_source_ref"], "artifact_ref": location["original_artifact_ref"],
            "kind": "image_region", "region": location["image_region"]}
    return {"source_ref": selected["source_ref"], "artifact_ref": witness["artifact_ref"], "kind": "utf8_span",
        "start": selected["start"], "end": selected["end"]}


def _uncertainty(value, field):
    if value is None:
        return
    _keys(value, ("statistic", "basis", "interval", "confidence_level", "exact_count", "minimum_count", "repetition_basis"), field)
    _enum(value["statistic"], ("sd", "sem", "confidence_interval", "unspecified", "unreported"), field)
    _enum(value["basis"], ("fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown"), field)
    _enum(value["repetition_basis"], ("biological_preparations", "technical_measurements", "assay_occasions", "unspecified"), field)
    for name in ("exact_count", "minimum_count"):
        if value[name] is not None and (type(value[name]) is not int or value[name] < 1):
            _fail(field)
    if value["interval"] is not None:
        if type(value["interval"]) is not list or len(value["interval"]) != 2:
            _fail(field)
        for endpoint in value["interval"]:
            _number(endpoint, field)
        a, b = value["interval"]
        if a is not None and b is not None and a > b:
            _fail(field)
    _number(value["confidence_level"], field)
    if value["confidence_level"] is not None and not 0 < value["confidence_level"] < 1:
        _fail(field)
    if value["statistic"] != "confidence_interval" and (value["interval"] is not None or value["confidence_level"] is not None):
        _fail(field)


def _raw_cell(row, source_kind):
    measure = row["measurement"]
    numeric = measure["canonical_measurement"]
    native = measure["native_measurement"]
    relation = numeric["relation"] if numeric else native["relation"] if native else "none"
    available = numeric is not None and numeric["relation"] != "unreported"
    status = ("reported_limit" if available and relation != "eq" else "populated" if available else
        "conflicting" if measure["parse_status"] == "conflicting" else "unavailable")
    return {"value": numeric["value"] if available and relation == "eq" else None,
        "threshold": numeric["value"] if available and relation != "eq" else None,
        "relation": relation, "unit": "nM" if numeric is not None else None, "status": status,
        "origin": "synthetic" if source_kind == "synthetic_fixture" else "visual_transcription",
        "unavailable_reason": None if available else "source_" + measure["parse_status"],
        "calculation_unavailable_reason": None,
        "bound_kind": "printed_limit" if available and relation != "eq" else None}


def native_cells(extraction, calculation):
    """Copy retained raw results and actual saved derived cells; no arithmetic."""
    cells = {name: _raw_cell(extraction["roles"][role], extraction["source_kind"]) for name, role in zip(RAW_COMPONENTS, ROLES)}
    for name in COMPONENTS[4:]:
        cell = calculation["cells"][name] if calculation is not None else None
        reason = cell["reason"] if cell is not None else extraction["calculation_input_status"]
        cells[name] = {"value": cell["value"] if cell else None, "threshold": cell["threshold"] if cell else None,
            "relation": cell["relation"] if cell and cell["relation"] is not None else "none", "unit": "dimensionless",
            "status": "populated" if cell and cell["status"] == "computed" else
                "reported_limit" if cell and cell["status"] == "reported_limit_arithmetic" else "unavailable",
            "origin": "derived", "unavailable_reason": reason,
            "calculation_unavailable_reason": cell["reason"] if cell else None,
            "bound_kind": "reported_limit_arithmetic" if cell and cell["status"] == "reported_limit_arithmetic" else None}
    return cells


def validate_saved_binding_interaction(selection, extraction, calculation, cells):
    """Validate saved source associations, not source syntax or scientific math."""
    try:
        _keys(extraction, ("version", "source_ref", "source_kind", "selection", "parameter_kind", "images", "roles", "relationships",
            "geometry_overlaps", "calculation_input_status", "calculation_inputs", "source_refs", "source_representations",
            "implementation_dependencies", "interpretation_attribution"), "extraction")
        _same(selection, extraction["selection"], "selection")
        _same(selection["version"], INPUT_VERSION, "selection.version")
        _same(extraction["version"], OUTPUT_VERSION, "extraction.version")
        for name in ("source_ref", "source_kind"):
            _same(extraction[name], selection[name], name)
        _meaning(selection["parameter_kind"], extraction["parameter_kind"], "parameter_kind")
        _enum(extraction["calculation_input_status"], CALCULATION_INPUT_STATUSES, "input_status")
        _keys(extraction["roles"], ROLES, "roles")
        for role in ROLES:
            selected, row = selection["roles"][role], extraction["roles"][role]
            _keys(row, ("selection_status", "parameter_kind", "definitions", "physical_fit", "measurement", "uncertainty",
                "calculation_operand", "unavailable_reasons"), role)
            _same(row["selection_status"], "not_selected" if selected is None else "selected", role)
            if any(reason not in ROLE_UNAVAILABLE_REASONS for reason in row["unavailable_reasons"]):
                _fail(role)
            measure = row["measurement"]
            _keys(measure, ("parse_status", "canonical_locator", "source_cell_id", "expression", "unit", "native_measurement",
                "canonical_measurement", "candidate_measurements", "error"), role)
            _enum(measure["parse_status"], MEASUREMENT_STATUSES, role)
            measurement_selection = selected["measurement"] if selected else None
            for name in ("expression", "unit"):
                _literal(measurement_selection[name] if measurement_selection else None, measure[name], role)
            _measurement(measure["native_measurement"], role)
            _measurement(measure["canonical_measurement"], role)
            if measure["canonical_locator"] is None:
                _same(measure["source_cell_id"], None, role)
            else:
                _same(measure["source_cell_id"], "binding_source_cell_" + _digest(measure["canonical_locator"], True), role)
            if len(measure["candidate_measurements"]) != len(measure["expression"]["candidates"]) and measure["canonical_locator"] is not None and measure["parse_status"] != "source_unavailable":
                _fail(role)
            if measure["canonical_measurement"] is not None:
                if measure["native_measurement"] is None:
                    _fail(role)
                _same(measure["native_measurement"]["relation"], measure["canonical_measurement"]["relation"], role)
            for index, candidate in enumerate(measure["candidate_measurements"]):
                _keys(candidate, ("candidate_index", "witness", "native", "canonical", "canonical_unit", "error"), role)
                _same(candidate["candidate_index"], index, role)
                _same(candidate["witness"], measure["expression"]["candidates"][index], role)
                _measurement(candidate["native"], role)
                _measurement(candidate["canonical"], role)
                _same(candidate["canonical_unit"], "nM" if candidate["canonical"] is not None else None, role)
            if measure["parse_status"] in ("parsed", "reported_unavailable"):
                _same(measure["expression"]["status"], "exact", role)
                _same(measure["native_measurement"], measure["candidate_measurements"][0]["native"], role)
                _same(measure["canonical_measurement"], measure["candidate_measurements"][0]["canonical"], role)
                actual = measure["native_measurement"]
                _same(measure["parse_status"], "reported_unavailable" if actual["relation"] == "unreported" else "parsed", role)
            if selected is None:
                _same(row["parameter_kind"], None, role)
                _same(row["definitions"], None, role)
                _same(row["calculation_operand"], None, role)
                continue
            _meaning(selected["parameter_kind"], row["parameter_kind"], role)
            _keys(row["definitions"], ID_FIELDS, role)
            for name, definition in row["definitions"].items():
                original = selected["definitions"][name]
                _keys(definition, ("status", "label", "witnesses", "canonical_witness", "canonical_id", "interpretation_attribution"), role)
                _same(original["label"], definition["label"], role)
                _enum(definition["status"], ("known", "unknown", "conflicting", "source_unavailable"), role)
                if len(original["witnesses"]) != len(definition["witnesses"]):
                    _fail(role)
                for a, b in zip(original["witnesses"], definition["witnesses"]):
                    _witness(a, b, role)
                if original["canonical_witness"] is None:
                    _same(definition["canonical_witness"], None, role)
                else:
                    _witness(original["canonical_witness"], definition["canonical_witness"], role)
                failed = any(w["error"] for w in definition["witnesses"]) or bool(definition["canonical_witness"] and definition["canonical_witness"]["error"])
                _same(definition["status"], "source_unavailable" if failed else original["status"], role)
                expected_id = "binding_meaning_" + _digest({"dimension": name, "source": _locator(definition["canonical_witness"])}, True) if definition["status"] == "known" else None
                _same(definition["canonical_id"], expected_id, role)
            physical, nominated = row["physical_fit"], selected["physical_fit"]
            _keys(physical, ("status", "canonical_witness", "witnesses", "physical_fit_id", "interpretation_attribution"), role)
            if nominated is None:
                _same((physical["status"], physical["canonical_witness"], physical["witnesses"], physical["physical_fit_id"]), ("unknown", None, [], None), role)
            else:
                _witness(nominated["canonical_witness"], physical["canonical_witness"], role)
                if len(nominated["witnesses"]) != len(physical["witnesses"]):
                    _fail(role)
                for a, b in zip(nominated["witnesses"], physical["witnesses"]):
                    _witness(a, b, role)
                failed = physical["canonical_witness"]["error"] or any(w["error"] for w in physical["witnesses"])
                _same(physical["status"], "source_unavailable" if failed else "known", role)
                _same(physical["physical_fit_id"], None if failed else "binding_physical_fit_" + _digest(_locator(physical["canonical_witness"]), True), role)
            unc = row["uncertainty"]
            _keys(unc, ("selection_status", "meanings", "interval", "confidence_level", "exact_count", "minimum_count",
                "reported_spread_status", "canonical", "unavailable_reasons"), role)
            if any(reason not in UNCERTAINTY_REASONS for reason in unc["unavailable_reasons"]):
                _fail(role)
            original_unc = selected["uncertainty"]
            _same(unc["selection_status"], "selected" if original_unc is not None else "not_selected", role)
            _uncertainty(unc["canonical"], role)
            if unc["canonical"] is not None:
                _same(unc["canonical"]["statistic"], unc["meanings"]["statistic"]["value"], role)
            if original_unc is not None:
                for name in ("statistic", "basis", "repetition_basis"):
                    _meaning(original_unc[name], unc["meanings"][name], role)
            for name in ("confidence_level", "exact_count", "minimum_count"):
                _scalar(original_unc[name] if original_unc else None, unc[name], role)
            interval = unc["interval"]
            if interval is not None:
                _keys(interval, ("lower", "upper", "unit_relationship", "unit", "canonical_values", "canonical_unit", "canonical_status"), role)
                original_interval = original_unc["interval"]
                _meaning(original_interval["unit_relationship"], interval["unit_relationship"], role)
                _literal(original_interval["unit"], interval["unit"], role)
                for name in ("lower", "upper"):
                    _scalar(original_interval[name], interval[name], role)
            if unc["canonical"] is not None:
                for name in ("exact_count", "minimum_count"):
                    value = unc["canonical"][name]
                    if value is not None:
                        _same(value, unc[name]["value"], role)
                if unc["canonical"]["interval"] is not None:
                    _same(unc["canonical"]["interval"], interval["canonical_values"], role)
            operand = row["calculation_operand"]
            if operand is not None:
                numeric = measure["canonical_measurement"]
                if numeric is None:
                    _fail(role)
                for name in ("value", "relation", "reported_spread"):
                    _same(operand[name], numeric[name], role)
                _same(operand["context"], {name: row["definitions"][name]["label"] for name in CONTEXT_FIELDS}, role)
                _same(operand["canonical_ids"], {name: row["definitions"][name]["canonical_id"] for name in ID_FIELDS}, role)
                _same(operand["uncertainty"], unc["canonical"], role)
                _same(operand["physical_fit_id"], row["physical_fit"]["physical_fit_id"], role)
                located = measure["canonical_locator"]
                _same(operand["source"], {"source_ref": located["original_source_ref"], "artifact_ref": located["original_artifact_ref"],
                    "kind": "image_region", "region": located["image_region"]}, role)
                _same(operand["expression"], measure["expression"]["candidates"][0]["witness"]["quote"], role)
                _same(operand["origin"], "synthetic" if extraction["source_kind"] == "synthetic_fixture" else "visual_transcription", role)
                _same(row["parameter_kind"]["value"], extraction["parameter_kind"]["value"], role)
        expected_status = ("common_parameter_kind_source_unavailable" if extraction["parameter_kind"]["status"] != "interpreted" else
            "common_parameter_kind_" + extraction["parameter_kind"]["value"] if extraction["parameter_kind"]["value"] in ("unknown", "conflicting") else "ready")
        _same(extraction["calculation_input_status"], expected_status, "input_status")
        for name in ("within_reference_subject", "within_test_subject", "ligand_correspondence", "parameter_definition", "separate_assays", "common_conditions"):
            original = selection["relationships"][name]
            _meaning({"value": original["status"], "witnesses": original["witnesses"]}, extraction["relationships"][name], name)
        ready = extraction["calculation_input_status"] == "ready"
        if not ready:
            _same(extraction["calculation_inputs"], None, "inputs")
            _same(calculation, None, "calculation")
        else:
            inputs = extraction["calculation_inputs"]
            _same(inputs["operands"], {r: extraction["roles"][r]["calculation_operand"] for r in ROLES}, "inputs.operands")
            _same(inputs["parameter_kind"], extraction["parameter_kind"]["value"], "kind")
            _same(calculation["inputs"], inputs, "calculation.inputs")
            _same(calculation["model"], None, "calculation.model")
            _same(inputs["version"], "binding_interaction_inputs_v1", "inputs.version")
            _same(inputs["unit"], "nM", "inputs.unit")
            _same(inputs["comparison_scope"], selection["comparison_scope"], "comparison_scope")
            _same(inputs["relationships"], {name: {"status": v["value"] if v["status"] == "interpreted" else "unknown",
                "sources": [_locator(w) for w in v["witnesses"] if _locator(w) is not None]}
                for name, v in extraction["relationships"].items()}, "relationships")
            _keys(calculation, ("version", "parameter_kind", "unit", "inputs", "operand_keys", "physical_fit_ids", "model", "cells", "qualifications"), "calculation")
            _same(calculation["version"], "binding_interaction_sheet_v1", "calculation.version")
            _same(calculation["parameter_kind"], inputs["parameter_kind"], "calculation.kind")
            _same(calculation["unit"], "nM", "calculation.unit")
            _same(calculation["operand_keys"], {role: None if operand is None else _digest({"parameter_kind": inputs["parameter_kind"],
                "unit": "nM", "operand": operand}) for role, operand in inputs["operands"].items()}, "operand_keys")
            _same(calculation["physical_fit_ids"], {role: None if operand is None else operand["physical_fit_id"]
                for role, operand in inputs["operands"].items()}, "physical_fit_ids")
            _keys(calculation["cells"], (*COMPONENTS, *MODEL_COMPONENTS), "calculation.cells")
            for name, cell in calculation["cells"].items():
                _keys(cell, ("operands", "formula", "unit", "value", "threshold", "relation", "status", "reason"), name)
                _number(cell["value"], name)
                _number(cell["threshold"], name)
                _enum(cell["status"], ("reported", "reported_limit", "computed", "reported_limit_arithmetic", "unavailable"), name)
                _enum(cell["relation"], (None, "eq", "lt", "le", "gt", "ge"), name)
                if name in COMPONENTS[4:] and cell["reason"] is not None:
                    _enum(cell["reason"], CALCULATION_REASONS, name)
                if cell["status"] in ("reported", "computed") and (cell["value"] is None or cell["relation"] != "eq" or cell["threshold"] is not None):
                    _fail(name)
                if cell["status"] in ("reported_limit", "reported_limit_arithmetic") and (cell["threshold"] is None or cell["relation"] not in ("lt", "le", "gt", "ge") or cell["value"] is not None):
                    _fail(name)
                if cell["value"] is not None and cell["threshold"] is not None:
                    _fail(name)
                if cell["status"] == "unavailable" and (cell["reason"] is None or cell["value"] is not None or cell["threshold"] is not None):
                    _fail(name)
                if cell["status"] != "unavailable" and cell["reason"] is not None:
                    _fail(name)
            for name in MODEL_COMPONENTS:
                _same(calculation["cells"][name]["value"], None, name)
                _same(calculation["cells"][name]["status"], "unavailable", name)
            for name, role in zip(RAW_COMPONENTS, ROLES):
                operand, cell = inputs["operands"][role], calculation["cells"][name]
                _same(cell["operands"], [role], name)
                _same(cell["formula"], "reported parameter", name)
                _same(cell["unit"], "nM", name)
                if operand is None or operand["relation"] == "unreported":
                    _same(cell["status"], "unavailable", name)
                    _same(cell["reason"], ("missing_operand:" if operand is None else "unreported_operand:") + role, name)
                else:
                    expected = {"value": operand["value"] if operand["relation"] == "eq" else None,
                        "threshold": operand["value"] if operand["relation"] != "eq" else None, "relation": operand["relation"],
                        "status": "reported" if operand["relation"] == "eq" else "reported_limit", "reason": None}
                    _same({k: cell[k] for k in expected}, expected, name)
            for name, indices, coefficients in (("reference_subject_ratio", (0, 1), (-1, 1)),
                    ("test_subject_ratio", (2, 3), (-1, 1)), ("interaction_ratio", (0, 1, 2, 3), (-1, 1, 1, -1)),
                    ("log_interaction", (0, 1, 2, 3), (-1, 1, 1, -1))):
                cell = calculation["cells"][name]
                _same(cell["operands"], [ROLES[i] for i in indices], name)
                _same(cell["formula"], {"expression": "sum(c_i * ln(p_i))" if name == "log_interaction" else "product(p_i ** c_i)",
                    "coefficients": list(coefficients)}, name)
                _same(cell["unit"], "dimensionless", name)
                if cell["reason"] and cell["reason"].startswith(("missing_operand:", "unreported_operand:")):
                    reason, role = cell["reason"].split(":", 1)
                    operand = inputs["operands"][role]
                    if (reason == "missing_operand" and operand is not None or
                            reason == "unreported_operand" and (operand is None or operand["relation"] != "unreported")):
                        _fail(name)
        _same(cells, native_cells(extraction, calculation), "native_cells")
        return deepcopy(extraction), deepcopy(calculation)
    except (KeyError, TypeError, ValueError, OverflowError, UnicodeError) as error:
        if isinstance(error, ExperimentalContractError):
            raise
        raise ExperimentalContractError("binding_interaction_saved_mismatch", "saved") from error


__all__ = ["VERSION", "RAW_COMPONENTS", "COMPONENTS", "MODEL_COMPONENTS", "FORMULA_CODES", "CALCULATION_REASONS",
    "UNAVAILABLE_REASONS", "native_cells", "validate_saved_binding_interaction"]
