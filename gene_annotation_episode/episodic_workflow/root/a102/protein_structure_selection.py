"""Pure result selection shared by protein commissioning and result collection."""
from __future__ import annotations

from copy import deepcopy
import math

from jsonschema import Draft202012Validator, validators

from .execution_contracts import digest
from .native_protein_structure_contracts import ScientificRequest, validate_protein_structure_request
from .protein_structure_contracts import (
    same, validate_calculation_parameters, validate_saved_sheet_descriptor,
)
from .protein_structure_result_views import (
    ProteinResultSelector, protein_structure_fact_sources,
    validate_protein_structure_projection_selection,
)


_COMPARISON_FAMILIES = frozenset(("comparison_summary", "transform", "site_measurements",
    "correspondence", "structure_coordinates", "native_uncertainty"))


def _require(condition, code="invalid_schema"):
    if not condition:
        raise ValueError(code)


def _json_value(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        _require(math.isfinite(value))
    elif type(value) is list:
        for item in value:
            _json_value(item)
    elif type(value) is dict:
        _require(all(type(key) is str for key in value))
        for item in value.values():
            _json_value(item)
    else:
        raise ValueError("invalid_schema")


def _references(value):
    if type(value) is dict:
        if "$ref" in value:
            reference = value["$ref"]
            _require(type(reference) is str and reference.startswith("#/$defs/"))
            yield reference.removeprefix("#/$defs/")
        for child in value.values():
            yield from _references(child)
    elif type(value) is list:
        for child in value:
            yield from _references(child)


def _schema():
    # D1 is the single authority for selector fields and their shared types.
    definitions = protein_structure_fact_sources()[
        "execution_protein_structure_projections"]["report_schema"]["$defs"]
    needed, pending = {}, ["ProteinResultSelector"]
    while pending:
        name = pending.pop()
        if name not in needed:
            needed[name] = definitions[name]
            pending.extend(_references(definitions[name]))
    body = {"$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": {name: needed[name] for name in sorted(needed)},
        "$ref": "#/$defs/ProteinResultSelector"}
    body["$id"] = "urn:gene-annotation:protein-structure:schema:" + digest(body)
    return body


_SCHEMA = _schema()
_VALIDATOR = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _checker, value: type(value) is int)
    .redefine("number", lambda _checker, value: type(value) in (int, float)
        and (type(value) is int or math.isfinite(value))))(_SCHEMA)


def protein_structure_result_selector_schema() -> dict:
    return deepcopy(_SCHEMA)


def validate_protein_structure_result_selector(value: ProteinResultSelector, *,
        request: ScientificRequest | None = None) -> ProteinResultSelector:
    try:
        _json_value(value)
        _require(_VALIDATOR.is_valid(value))
        selected = deepcopy(value)
        if selected["saved_sheet"] is not None:
            validate_saved_sheet_descriptor(selected["saved_sheet"])
        if selected["parameters"] is not None:
            validate_calculation_parameters(selected["parameters"])
        for projection in selected["projections"]:
            validate_protein_structure_projection_selection(projection)
        ids = [projection["projection_id"] for projection in selected["projections"]]
        _require(len(ids) == len(set(ids)), "duplicate_selection")
        saved = selected["acquisition"] == "retained_sheet_only"
        if saved:
            _require(selected["saved_sheet"] is not None and selected["parameters"] is not None)
            _require("recalculate" in selected["saved_sheet"]["allowed_uses"], "saved_sheet_not_received")
            operation = "compare"
        else:
            _require(selected["saved_sheet"] is None)
            operation = None
        if request is not None:
            original = validate_protein_structure_request(request)
            if saved:
                _require(original["operation"] == "compare", "original_commission_mismatch")
                _require(selected["saved_sheet"]["original_mode"] == original["parameters"]["mode"],
                    "original_commission_mismatch")
            operation = original["operation"]
            if operation == "compare":
                if not saved:
                    _require(selected["parameters"] is None or same(selected["parameters"], original["parameters"]),
                        "original_commission_mismatch")
                transform = (selected["parameters"] or original["parameters"])["declared_transform"]
                if transform is not None:
                    _require(all(same(transform[side + "_selection"], original[side + "_selection"])
                        for side in ("fixed", "moving")), "invalid_transform")
        if operation is not None:
            families = ({"structure_inventory"} if operation == "inspect" else
                {"extracted_sequence", "native_uncertainty"} if operation == "extract_sequence" else
                _COMPARISON_FAMILIES)
            _require(all(projection["family"] in families for projection in selected["projections"]))
            if operation != "compare":
                _require(not saved and selected["parameters"] is None and not selected["return_saved_sheet"])
            if operation != "extract_sequence":
                _require(not selected["sequence_allowed_uses"])
            for projection in selected["projections"]:
                if projection["family"] == "native_uncertainty":
                    permitted_roles = {"single"} if operation == "extract_sequence" else {"fixed", "moving"}
                    _require(projection["members"]["structure_role"] in permitted_roles, "conflicting_identity")
        return selected
    except (OverflowError, RecursionError) as error:
        raise ValueError("invalid_schema") from error
