"""Pure ordinary arsenic returns over the existing calibrated-signal authority.

These contracts check supplied shapes and retained associations. They perform
no calculation, File read, experimental authentication or reference admission.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .calibrated_signal_contracts import (
    COMPONENTS_VERSION, QUALIFICATIONS, SELECTION_VERSION, SHEET_VERSION,
    calibrated_signal_components_schema, calibrated_signal_selection_schema, calibrated_signal_sheet_schema,
    copy_json, validate_calibrated_signal_components_shape,
    validate_calibrated_signal_selection, validate_calibrated_signal_sheet,
)
from .domain import ContractError, validate_schema
from .molecular_sequence_result_contracts import (
    FAILURE_SOURCE, FILE_STATES, SUPPLIED_OPERATION, supplied_failure_view,
    supplied_file_fact_sources, validate_supplied_failure,
)


TOOL = SUPPLIED_OPERATION
PACKET_VERSION = "ordinary_arsenic_speciation_values_v1"
SOURCE_VERSION = "ordinary_arsenic_speciation_result_v1"
VALUES_VERSION = "arsenic_speciation_selected_values_v1"
INPUT_VIEW_VERSION = "ordinary_arsenic_speciation_input_view_v1"
FACT_SOURCE = "arsenic_speciation_outcomes"
CALCULATOR_ID = "calibrated_signal_calculations.calculate_calibrated_signal_components"
FILE_ROLES = ("sheet", "components")
INPUT_ROLES = ("samples", "species", "calibrations", "association")
_SOURCE = re.compile(r"source_[0-9a-f]{24,64}")
_VALUE_FIELDS = ("population", "rows", "uncertainty_assessments", "unassigned_measurements", "qualifications")
_COUNTS = ("supplied_sample_count", "supplied_species_count", "selected_sample_count",
    "selected_species_count", "returned_row_count")
_CALCULATION_STATES = ("input_unavailable", "selection_invalid", "not_started", "completed",
    "calculation_failed", "worker_failed", "worker_uncertain")
_RETAINED = ("retained", "retained_undeclared")


def _require(condition, code="contract_invalid"):
    if not condition:
        raise ValueError("arsenic_speciation_" + code)


def _obj(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _nullable(schema):
    return {"anyOf": [deepcopy(schema), {"type": "null"}]}


def _shape(value, schema):
    value = copy_json(value)
    try:
        validate_schema(value, schema)
    except ContractError as error:
        raise ValueError("arsenic_speciation_closed_shape_required") from error
    return value


def _selection(value):
    return _shape(value, calibrated_signal_selection_schema())


def _reference_schema():
    return {"anyOf": [_obj({"namespace": {"const": namespace},
        "reference": {"type": "string", "pattern": pattern}}) for namespace, pattern in (
            ("source", "^source_[0-9a-f]{24,64}$"), ("artifact", "^artifact_[0-9a-f]{64}$"))]}


ARGUMENT_SCHEMA = {"anyOf": [
    _obj({"mode": {"const": "calculate"}, "input": _reference_schema(),
        "selection": calibrated_signal_selection_schema()}),
    _obj({"mode": {"const": "calculate_saved"},
        "result_ref": {"type": "string", "pattern": "^source_[0-9a-f]{24,64}$"},
        "selection": calibrated_signal_selection_schema()}),
    _obj({"mode": {"const": "read_stored"},
        "result_ref": {"type": "string", "pattern": "^source_[0-9a-f]{24,64}$"}}),
    _obj({"mode": {"const": "read_inputs"},
        "result_ref": {"type": "string", "pattern": "^source_[0-9a-f]{24,64}$"}})]}


def validate_ordinary_arsenic_arguments(arguments):
    """A literal read carries no replacement selection or scientific operands."""
    return _shape(arguments, ARGUMENT_SCHEMA)


def ordinary_arsenic_input_view_schema():
    """The existing complete Sheet is data; only its enclosing Source is semantic."""
    roles = {name: {"enum": ["present", "empty", "missing", "invalid", "unavailable"]
        if name != "association" else ["present", "missing", "invalid", "unavailable"]} for name in INPUT_ROLES}
    return _obj({"version": {"const": INPUT_VIEW_VERSION},
        "source_ref": {"type": "string", "pattern": "^source_[0-9a-f]{24,64}$",
            "format": "reference", "x-reference-namespace": "source"},
        "result_selection": calibrated_signal_selection_schema(),
        "input_state": {"enum": ["complete", "partial", "unavailable"]},
        "role_states": _obj(roles), "sheet": _nullable(calibrated_signal_sheet_schema()),
        "unavailable_reason": {"enum": [None, "validated_sheet_unavailable"]},
        "qualifications": {"const": deepcopy(QUALIFICATIONS)}})


def validate_ordinary_arsenic_input_view(value):
    """Validate literal supplied operands without associating or calculating them."""
    value = _shape(value, ordinary_arsenic_input_view_schema())
    valid = [state in ("present", "empty") for state in value["role_states"].values()]
    _require(value["input_state"] != "complete" or all(valid), "input_state_conflict")
    _require(value["input_state"] != "partial" or any(valid), "input_state_conflict")
    _require(value["input_state"] != "unavailable" or not any(valid), "input_state_conflict")
    if value["sheet"] is None:
        _require(value["input_state"] != "complete"
            and value["unavailable_reason"] == "validated_sheet_unavailable", "input_view_availability_conflict")
    else:
        sheet = validate_calibrated_signal_sheet(value["sheet"])
        roles = {name: "empty" if type(sheet[name]) is list and not sheet[name] else "present" for name in INPUT_ROLES}
        _require(value["input_state"] == "complete" and value["role_states"] == roles
            and value["unavailable_reason"] is None, "input_view_availability_conflict")
    # result_selection is the original producer's selection, including a
    # possible invalid selection. The full supplied Sheet is never filtered
    # or recalculated to turn that recorded request into another result.
    return value


def ordinary_arsenic_input_view(*, source_ref, result_selection, input_state, role_states, sheet):
    return validate_ordinary_arsenic_input_view(dict(version=INPUT_VIEW_VERSION, source_ref=source_ref,
        result_selection=deepcopy(result_selection), input_state=input_state, role_states=deepcopy(role_states),
        sheet=deepcopy(sheet), unavailable_reason="validated_sheet_unavailable" if sheet is None else None,
        qualifications=deepcopy(QUALIFICATIONS)))


def _values_schema():
    original = calibrated_signal_components_schema()["properties"]
    return _obj({"schema": {"const": VALUES_VERSION}, "components_version": {"const": COMPONENTS_VERSION},
        **{name: deepcopy(original[name]) for name in _VALUE_FIELDS}})


def _failure_schema():
    value = deepcopy(supplied_file_fact_sources()[FAILURE_SOURCE]["report_schema"]["items"])
    def opaque(node):
        if type(node) is dict:
            node.pop("format", None)
            node.pop("x-reference-namespace", None)
            for child in node.values(): opaque(child)
        elif type(node) is list:
            for child in node: opaque(child)
    opaque(value)
    return value


def _packet_schema():
    states = [state for state in FILE_STATES if state != "produced_unretained"]
    roles = {name: {"enum": ["present", "empty", "missing", "invalid", "unavailable"]
        if name != "association" else ["present", "missing", "invalid", "unavailable"]} for name in INPUT_ROLES}
    return _obj({"version": {"const": PACKET_VERSION}, "selection": calibrated_signal_selection_schema(),
        "context": _obj({"input_state": {"enum": ["complete", "partial", "unavailable"]},
            "role_states": _obj(roles), "calculation": _obj({"state": {"enum": list(_CALCULATION_STATES)},
                "call_count": {"enum": [None, 0, 1]}, "native_invocation": {"const": "not_requested"}}),
            "qualifications": {"const": deepcopy(QUALIFICATIONS)}}),
        "values": _nullable(_values_schema()),
        "file_states": _obj({name: {"enum": states} for name in FILE_ROLES}),
        "failures": {"type": "array", "items": _failure_schema()}})


def _validate_values(value, selection):
    """Check public identities/counts, never recompute scientific quantities."""
    population, rows = value["population"], value["rows"]
    _require(all(type(population[name]) is int and population[name] >= 0 for name in _COUNTS), "population_invalid")
    _require(population["selected_sample_count"] == len(selection["sample_ids"])
        and population["selected_species_count"] == len(selection["species_ids"])
        and population["returned_row_count"] == len(rows)
        and population["selected_sample_count"] <= population["supplied_sample_count"]
        and population["selected_species_count"] <= population["supplied_species_count"], "population_conflict")
    analysis = population["association_species_ids"]
    _require(len(analysis) == len(set(analysis)) and len(analysis) <= population["supplied_species_count"]
        and set(selection["species_ids"]) <= set(analysis), "association_population_conflict")
    identities, ordinals, samples, species, candidates, calibrations = [], [], {}, {}, {}, {}
    for row in rows:
        cells = [row[name] for name in ("linear_estimate", "aliquot_concentration", "original_sample_concentration")]
        cells.extend(item["estimate"] for item in row["censoring"])
        _require(all((cell["state"] == "unavailable") == (cell["value"] is None) for cell in cells),
            "quantity_availability_conflict")
        for item in row["censoring"]:
            estimate = row["aliquot_concentration" if item["concentration_basis"] == "aliquot" else "original_sample_concentration"]
            _require(item["estimate"] == estimate and (item["state"] == "below") == (item["reported_bound"] is not None),
                "censoring_linkage_conflict")
            bound = item["reported_bound"]
            if bound is not None:
                _require(bound["unit"] == estimate["unit"] and bound["quantity_basis"] == estimate["quantity_basis"]
                    and bound["upper_relation"] == item["selected_relation"], "censoring_basis_conflict")
        sample, target = row["sample_id"], row["species_id"]
        i, j = row["sample_ordinal"], row["species_ordinal"]
        _require(sample in selection["sample_ids"] and target in selection["species_ids"]
            and type(i) is int and 0 <= i < population["supplied_sample_count"]
            and type(j) is int and 0 <= j < population["supplied_species_count"], "row_identity_conflict")
        _require(sample not in samples or samples[sample] == i, "sample_ordinal_conflict")
        _require(target not in species or species[target] == j, "species_ordinal_conflict")
        samples[sample], species[target] = i, j
        identities.append((sample, target)); ordinals.append((i, j))
        association = row["association"]
        items = association["candidates"]
        ordered = [(item["measurement_id"], item["measurement_ordinal"]) for item in items]
        _require(all(type(index) is int and index == position for position, (_, index) in enumerate(ordered))
            and len({name for name, _ in ordered}) == len(ordered)
            and (sample not in candidates or candidates[sample] == ordered), "candidate_identity_conflict")
        candidates[sample] = ordered
        competing = association["competing_species_ids"]
        _require(len(competing) == len(set(competing)) and set(competing) <= set(analysis), "competitor_identity_conflict")
        if association["state"] == "assigned":
            index = association["measurement_ordinal"]
            _require(type(index) is int and 0 <= index < len(items)
                and association["measurement_id"] == items[index]["measurement_id"]
                and items[index]["eligible"] is True, "assigned_measurement_conflict")
        else:
            _require(association["measurement_id"] is None and association["measurement_ordinal"] is None,
                "unassigned_measurement_conflict")
        chosen = row["selected_calibration_ids"]
        _require(len(chosen) == len(set(chosen)) and set(chosen) <= set(selection["calibration_ids"])
            and (target not in calibrations or calibrations[target] == chosen)
            and row["calibration_id"] == (chosen[0] if len(chosen) == 1 else None), "calibration_identity_conflict")
        calibrations[target] = chosen
    expected = {(sample, target) for sample in selection["sample_ids"] for target in selection["species_ids"]}
    _require(len(identities) == len(set(identities)) and set(identities) == expected
        and ordinals == sorted(ordinals) and len(set(samples.values())) == len(samples)
        and len(set(species.values())) == len(species), "row_population_conflict")
    unassigned = value["unassigned_measurements"]
    names = [item["sample_id"] for item in unassigned]
    _require(len(names) == len(set(names)) and set(names) == set(selection["sample_ids"]), "unassigned_population_conflict")
    if samples:
        _require([samples[name] for name in names] == sorted(samples.values()), "unassigned_order_conflict")
    for item in unassigned:
        ids = item["measurement_ids"]
        _require(len(ids) == len(set(ids)), "unassigned_identity_conflict")
        if item["sample_id"] in candidates:
            original = [name for name, _ in candidates[item["sample_id"]]]
            _require(set(ids) <= set(original) and [name for name in original if name in ids] == ids,
                "unassigned_identity_conflict")


def _component_linkage(components, selection):
    value = validate_calibrated_signal_components_shape(components)
    sheet = validate_calibrated_signal_sheet(value["sheet"])
    validate_calibrated_signal_selection(value["selection"], sheet)
    _require(value["selection"] == selection, "selection_conflict")
    population = value["population"]
    _require(population["supplied_sample_count"] == len(sheet["samples"])
        and population["supplied_species_count"] == len(sheet["species"])
        and population["association_species_ids"] == sheet["association"]["analysis_species_ids"], "sheet_population_conflict")
    for row in value["rows"]:
        i, j = row["sample_ordinal"], row["species_ordinal"]
        _require(type(i) is int and 0 <= i < len(sheet["samples"])
            and type(j) is int and 0 <= j < len(sheet["species"]), "row_identity_conflict")
        sample, target = sheet["samples"][i], sheet["species"][j]
        _require(row["sample_id"] == sample["sample_id"] and row["species_id"] == target["species_id"]
            and row["representation"] == sample["representation"] and row["signal_kind"] == sample["signal_kind"],
            "sheet_row_conflict")
        _require([(item["measurement_id"], item["measurement_ordinal"]) for item in row["association"]["candidates"]]
            == [(item["measurement_id"], index) for index, item in enumerate(sample["measurements"])], "sheet_measurement_conflict")
        _require(row["selected_calibration_ids"] == [item["calibration_id"] for item in sheet["calibrations"]
            if item["calibration_id"] in selection["calibration_ids"] and item["species_id"] == target["species_id"]],
            "sheet_calibration_conflict")
    return value


def ordinary_arsenic_packet(*, arguments, input_state, role_states, components,
        calculation, file_states, failures):
    """Construct producer bytes before Source creation, without calculating.

    Literal read_stored returns its authenticated original packet unchanged;
    it does not build a producer packet with replacement selection metadata.
    """
    arguments = validate_ordinary_arsenic_arguments(arguments)
    _require(arguments["mode"] not in ("read_stored", "read_inputs"), "producer_mode_required")
    selected = _selection(arguments["selection"])
    public = None
    if components is not None:
        value = _component_linkage(components, selected)
        public = dict(schema=VALUES_VERSION, components_version=COMPONENTS_VERSION,
            **{name: deepcopy(value[name]) for name in _VALUE_FIELDS})
    issues = []
    failures = copy_json(failures)
    _require(type(failures) is list, "failures_invalid")
    for issue in failures:
        validated = validate_supplied_failure(issue)
        issues.append(supplied_failure_view(validated) if validated["version"] == "molecular_sequence_supplied_failure_v1" else validated)
    return validate_ordinary_arsenic_packet(dict(version=PACKET_VERSION, selection=selected,
        context=dict(input_state=input_state, role_states=role_states, calculation=calculation,
            qualifications=deepcopy(QUALIFICATIONS)), values=public, file_states=file_states, failures=issues))


def validate_ordinary_arsenic_packet(value):
    value = _shape(value, _packet_schema())
    selected = _selection(value["selection"])
    context, calculation = value["context"], value["context"]["calculation"]
    count = calculation["call_count"]
    _require(count is None or type(count) is int and count in (0, 1), "calculation_count_invalid")
    _require(calculation["state"] != "completed" or count == 1, "calculation_count_conflict")
    _require(calculation["state"] != "worker_uncertain" or count is None, "calculation_count_conflict")
    _require(calculation["state"] not in ("input_unavailable", "selection_invalid", "not_started") or count == 0,
        "calculation_count_conflict")
    valid = [state in ("present", "empty") for state in context["role_states"].values()]
    _require(context["input_state"] != "complete" or all(valid), "input_state_conflict")
    _require(context["input_state"] != "partial" or any(valid), "input_state_conflict")
    _require(context["input_state"] != "unavailable" or not any(valid), "input_state_conflict")
    if value["values"] is not None:
        _require(context["input_state"] == "complete" and count != 0
            and value["file_states"]["components"] in _RETAINED,
            "values_retention_conflict")
        _validate_values(value["values"], selected)
    for issue in value["failures"]:
        _require(issue["version"] == "molecular_sequence_supplied_failure_v2", "public_failure_required")
        validate_supplied_failure(issue)
    return value


def project_ordinary_arsenic_return(packet, source_ref):
    packet = validate_ordinary_arsenic_packet(packet)
    return validate_ordinary_arsenic_return(dict(source_ref=source_ref, **packet))


def validate_ordinary_arsenic_return(value):
    value = copy_json(value)
    _require(type(value) is dict and type(value.get("source_ref")) is str
        and _SOURCE.fullmatch(value["source_ref"]) is not None, "source_required")
    validate_ordinary_arsenic_packet({name: item for name, item in value.items() if name != "source_ref"})
    return value


def ordinary_arsenic_fact_sources():
    """Only the top actual Source is reference-bearing; provenance is opaque."""
    item = _packet_schema()
    item["properties"]["source_ref"] = {"type": "string", "pattern": "^source_[0-9a-f]{24,64}$",
        "format": "reference", "x-reference-namespace": "source"}
    item["required"].append("source_ref")
    meaning = ("Selected supplied retention-time/calibration calculations with explicit sample/species populations, "
        "units, quantity bases, censoring and unpropagated uncertainty. Retention-time association does not establish "
        "chemical identity or an instrument/native run. Nested provenance grants no Files or references.")
    return {FACT_SOURCE: dict(type="array", report_schema={"type": "array", "items": item,
        "x-source": FACT_SOURCE}, description=meaning, meaning=meaning)}


__all__ = ["TOOL", "PACKET_VERSION", "SOURCE_VERSION", "VALUES_VERSION", "INPUT_VIEW_VERSION", "FACT_SOURCE", "CALCULATOR_ID",
    "FILE_ROLES", "INPUT_ROLES", "SHEET_VERSION", "COMPONENTS_VERSION", "SELECTION_VERSION", "ARGUMENT_SCHEMA",
    "validate_ordinary_arsenic_arguments", "ordinary_arsenic_packet", "validate_ordinary_arsenic_packet",
    "project_ordinary_arsenic_return", "validate_ordinary_arsenic_return", "ordinary_arsenic_fact_sources",
    "ordinary_arsenic_input_view_schema", "ordinary_arsenic_input_view", "validate_ordinary_arsenic_input_view"]
