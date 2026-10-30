"""Finite requests for saved proteome measurements, without scientific calculation.

The schemas select existing numerical cells. They do not define another scoring
language. References name exact saved pointers; episode custody remains with the
return binding. Package schemas are loaded by their existing contract modules.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re
from urllib.parse import quote, unquote

from .bvbrc_proteome_native_contracts import _plain_json, _Validator
from .bvbrc_proteome_sheet_contracts import proteome_sheet_schema


class ProteomeFactError(ValueError):
    def __init__(self, code: str, path: str = ""):
        self.code = "proteome_projection_" + code
        self.path = path
        super().__init__(self.code)


def require(condition, code, path=""):
    if not condition:
        raise ProteomeFactError(code, path)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def obj(**properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def arr(items):
    return {"type": "array", "items": items}


def enum(*values):
    return {"enum": list(values)}


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


TEXT = {"type": "string", "minLength": 1}
UINT = {"type": "integer", "minimum": 0}
NUMBER = {"type": "number"}
TRACK = {"type": "string", "pattern": r"^comp_genome_[1-9][0-9]*$"}
ASSOCIATION = {"type": "string", "pattern": r"^comp_genome_[1-9][0-9]*/row/(0|[1-9][0-9]*)$"}
ASSOCIATION_METRICS = ("first_hsp_alignment_identity_percent", "subject_endpoint_difference_percent")
SUMMARY_NAMES = ("first_hsp_identity_summary", "subject_endpoint_difference_summary")
SUMMARY_COUNTS = ("value_count", "omitted_count", "null_count", "blank_count", "invalid_count", "layout_uncertain_count")
SUMMARY_VALUES = ("sum", "mean", "minimum", "maximum")
INVENTORY_METRICS = ("observed_header_count", "complete_record_count", "valid_complete_record_count")
RATIO_METRICS = ("observed_reference_fraction", "complete_published_reference_fraction",
                 "observed_selected_reference_fraction", "complete_selected_reference_fraction")
TRACK_METHODS = {
    "source_association_record_count": "source_association_count",
    "published_association_record_count": "published_association_count",
    "reference_input_record_count": "qualified_executed_count",
    "comparison_input_record_count": "qualified_executed_count",
    "no_published_reference_count": "qualified_executed_count",
    "observed_bound_reference_count": "bound_occurrence_count",
    "observed_bound_subject_count": "bound_occurrence_count",
    "unresolved_reference_association_count": "bound_occurrence_count",
    "unresolved_subject_association_count": "bound_occurrence_count",
    "multiple_reference_subject_count": "bound_pair_dependence_count",
    "excess_bound_pair_count": "bound_pair_dependence_count",
    "observed_selected_reference_count": "postfilter_selection_count",
    "demonstrated_subject_sequence_group_count": "full_sequence_group_count",
    "unresolved_subject_sequence_count": "full_sequence_group_count",
    "native_bi_count": "native_category_count",
    "native_uni_count": "native_category_count",
    "native_other_category_count": "native_category_count",
    "native_missing_category_count": "native_category_count",
}
REFERENCE_KINDS = ("population", "source_field", "join", "parameter", "requirement", "qualification", "field")
AVAILABILITY = enum("available", "unavailable", "incompatible", "invalid")
_SHEET_DEFS = proteome_sheet_schema("NativeSheet")["$defs"]
_COMPONENT_DEFS = proteome_sheet_schema("NativeComponents")["$defs"]
CELL_STATES = tuple(_COMPONENT_DEFS["ScalarCell"]["properties"]["state"]["enum"])
P_REASONS = tuple(_SHEET_DEFS["PReason"]["enum"])
SCOPE_SCHEMA = _SHEET_DEFS["Scope"]


SELECTORS = {
    "measurement": {"oneOf": [
        obj(kind={"const": "measurement"}, target={"const": "association"},
            association_key=ASSOCIATION, metric=enum(*ASSOCIATION_METRICS)),
        obj(kind={"const": "measurement"}, target={"const": "track_count"},
            track_key=TRACK, metric=enum(*TRACK_METHODS)),
        obj(kind={"const": "measurement"}, target={"const": "summary"},
            track_key=TRACK, summary=enum(*SUMMARY_NAMES), metric=enum(*SUMMARY_COUNTS, *SUMMARY_VALUES)),
        obj(kind={"const": "measurement"}, target={"const": "selection_count"},
            track_key=TRACK, metric=enum("pass", "fail", "unknown")),
        obj(kind={"const": "measurement"}, target={"const": "inventory_count"},
            inventory_key=TEXT, metric=enum(*INVENTORY_METRICS)),
    ]},
    "ratio": obj(kind={"const": "ratio"}, track_key=TRACK, metric=enum(*RATIO_METRICS)),
    "population": {"oneOf": [
        obj(kind={"const": "population"}, target={"const": "track"}, track_key=TRACK),
        obj(kind={"const": "population"}, target={"const": "summary"}, track_key=TRACK, summary=enum(*SUMMARY_NAMES)),
        obj(kind={"const": "population"}, target={"const": "inventory"}, inventory_key=TEXT),
    ]},
    "association": obj(kind={"const": "association"}, association_key=ASSOCIATION),
    "selection": obj(kind={"const": "selection"}, association_key=ASSOCIATION),
    "requirements": obj(kind={"const": "requirements"}, scope={"const": "all"}),
    "qualifications": obj(kind={"const": "qualifications"}, scope={"const": "all"}),
    "request_status": obj(kind={"const": "request_status"}, field=TEXT),
}


def _validate(schema, value, code):
    try:
        _plain_json(value)
    except ValueError as error:
        raise ProteomeFactError(code, getattr(error, "path", "")) from error
    error = next(_Validator(schema).iter_errors(value), None)
    if error is not None:
        pointer = "".join("/" + str(k).replace("~", "~0").replace("/", "~1") for k in error.absolute_path)
        raise ProteomeFactError(code, pointer)


def validate_selector(value):
    _validate({"oneOf": list(SELECTORS.values())}, value, "selector_invalid")
    # JSON Schema '$' can match before a terminal newline. These are exact keys.
    if "track_key" in value:
        require(re.fullmatch(r"comp_genome_[1-9][0-9]*", value["track_key"]) is not None, "selector_invalid")
    if "association_key" in value:
        require(re.fullmatch(r"comp_genome_[1-9][0-9]*/row/(0|[1-9][0-9]*)", value["association_key"]) is not None,
                "selector_invalid")
    return deepcopy(value)


def encode_reference(kind, analysis_id, pointer):
    require(type(kind) is str and kind in REFERENCE_KINDS, "reference_kind_invalid")
    require(type(analysis_id) is str and bool(analysis_id) and type(pointer) is str and pointer.startswith("/"),
            "reference_invalid")
    require(re.search(r"~(?![01])", pointer) is None, "reference_invalid")
    try:
        return "bvbrc_proteome_" + kind + ":" + quote(analysis_id, safe="") + "/" + quote(pointer, safe="")
    except UnicodeError as error:
        raise ProteomeFactError("reference_invalid") from error


def decode_reference(reference):
    require(type(reference) is str and reference.startswith("bvbrc_proteome_"), "reference_invalid")
    prefix, colon, tail = reference.partition(":")
    require(bool(colon) and tail.count("/") == 1, "reference_invalid")
    kind = prefix[len("bvbrc_proteome_"):]
    try:
        analysis_id, pointer = (unquote(part, errors="strict") for part in tail.split("/"))
    except UnicodeError as error:
        raise ProteomeFactError("reference_invalid") from error
    require(encode_reference(kind, analysis_id, pointer) == reference, "reference_noncanonical")
    return kind, analysis_id, pointer


def reference_schema(kind):
    require(kind in REFERENCE_KINDS, "reference_kind_invalid")
    return {"type": "string", "pattern": "^bvbrc_proteome_" + kind + ":[^/]+/[^/]+$"}


def fact_schemas(*, binding_codes=None, binding_input_kinds=None):
    """Return detached schemas with the provider's explicit finite code sets."""
    if binding_codes is None or binding_input_kinds is None:
        from .bvbrc_proteome_bundle_contracts import BINDING_CODES, BINDING_INPUT_KINDS
        binding_codes = BINDING_CODES if binding_codes is None else binding_codes
        binding_input_kinds = BINDING_INPUT_KINDS.values() if binding_input_kinds is None else binding_input_kinds
    codes = sorted(set(P_REASONS) | set(_SHEET_DEFS["Diagnostic"]["properties"]["code"]["enum"]) | set(binding_codes))
    inputs = sorted(set(_SHEET_DEFS["Requirement"]["properties"]["required_input"]["enum"])
                    | set(_SHEET_DEFS["PRequirement"]["properties"]["required_input"]["enum"]) | set(binding_input_kinds))
    refs = {kind: arr(reference_schema(kind)) for kind in REFERENCE_KINDS}
    tails = dict(qualification_refs=refs["qualification"], requirement_refs=refs["requirement"])
    cell_fields = dict(reason_codes=arr(enum(*P_REASONS)), source_field_refs=refs["source_field"])
    cell = {"oneOf": [obj(state={"const": "value"}, value=NUMBER, **cell_fields),
                      obj(state=enum(*(state for state in CELL_STATES if state != "value")),
                          value={"type": "null"}, **cell_fields)]}
    measurement = obj(availability=AVAILABILITY,
        quantity=enum(*dict.fromkeys((*ASSOCIATION_METRICS, *TRACK_METHODS, *SUMMARY_COUNTS, *SUMMARY_VALUES,
                                     "pass", "fail", "unknown", *INVENTORY_METRICS))),
        cell=cell, unit=enum("count", "fraction", "percent"),
        origin=enum("derived_native_descriptive", "observed_supplied_inventory"),
        population_ref=nullable(reference_schema("population")),
        method=enum(*dict.fromkeys((*TRACK_METHODS.values(), "legacy_first_hsp_percent", "legacy_subject_endpoint_percent",
                                   "rounded_native_summary", "native_cell_presence_count", "supplied_inventory_count"))),
        uncertainty={"type": "null"}, native_rounding_quantum=nullable(NUMBER), **tails)
    ratio = obj(availability=AVAILABILITY, quantity=enum(*RATIO_METRICS), numerator=cell, denominator=cell,
        fraction=cell, unit={"const": "fraction"}, population_ref=nullable(reference_schema("population")),
        denominator_kind={"const": "qualified_executed_reference_occurrences"}, uncertainty={"type": "null"}, **tails)
    population = obj(availability=AVAILABILITY,
        population_kind=enum("selected_track_input_associations", "usable_rounded_native_cells", "supplied_fasta_occurrences"),
        track_key=nullable(TRACK), inventory_key=nullable(TEXT),
        source_scope=nullable(enum("complete_document", "complete_prefix_only", "partial_or_unknown_artifact", "invalid_document")),
        materialization=nullable(enum("published_association", "table_field_block", "unknown")),
        association_keys=arr(ASSOCIATION), record_ordinals=arr(UINT),
        membership_meaning=enum("input_population", "exact_used_cells", "supplied_records"),
        native_source_refs=arr(TEXT), **tails)
    association = obj(availability=AVAILABILITY, association_key=ASSOCIATION, track_key=TRACK,
        reference_row_ordinal=UINT, reference_identifier=nullable(TEXT), subject_identifier=nullable(TEXT),
        native_category=nullable(enum("bi (<->)", "uni (->)", "unrecognized")),
        category_presence=nullable(enum("value", "omitted", "explicit_null", "blank", "invalid")),
        reference_join_ref=nullable(reference_schema("join")), subject_join_ref=nullable(reference_schema("join")),
        metadata_join_refs=refs["join"], source_field_refs=refs["source_field"], **tails)
    selection = obj(availability=AVAILABILITY, association_key=ASSOCIATION, selection=nullable(enum("pass", "fail", "unknown")),
        failed_conditions=arr(enum("identity", "subject_endpoint_difference", "category")),
        unknown_conditions=arr(enum("identity", "subject_endpoint_difference", "category")),
        parameter_ref=nullable(reference_schema("parameter")), population_ref=nullable(reference_schema("population")), **tails)
    requirement = obj(requirement_ref=reference_schema("requirement"), code=enum(*codes),
        required_input=enum(*inputs), scope=SCOPE_SCHEMA, source_field_refs=refs["source_field"])
    qualification = obj(qualification_ref=reference_schema("qualification"), code=enum(*codes),
        scope=SCOPE_SCHEMA, source_field_refs=refs["source_field"])
    return deepcopy(dict(measurement=measurement, ratio=ratio, population=population, association=association,
        selection=selection, requirements=obj(availability={"const": "available"}, requirements=arr(requirement)),
        qualifications=obj(availability={"const": "available"}, qualifications=arr(qualification)),
        request_status=obj(availability={"const": "available"}, field=TEXT, state=AVAILABILITY, **tails)))


def requested_form_schema(selections, *, binding_codes=None, binding_input_kinds=None):
    require(type(selections) is dict and all(type(name) is str and name for name in selections), "form_invalid")
    checked = {name: validate_selector(value) for name, value in selections.items()}
    for value in checked.values():
        if value["kind"] == "request_status":
            require(value["field"] in checked and checked[value["field"]]["kind"] != "request_status",
                    "status_target_invalid")
    schemas = fact_schemas(binding_codes=binding_codes, binding_input_kinds=binding_input_kinds)
    return obj(**{name: {**schemas[value["kind"]], "x-bvbrc-proteome": value} for name, value in checked.items()})


def validate_requested_form(value, *, binding_codes=None, binding_input_kinds=None):
    require(type(value) is dict and set(value) == {"type", "properties", "required", "additionalProperties"}, "form_invalid")
    props, required = value["properties"], value["required"]
    require(type(props) is dict and type(required) is list and all(type(name) is str for name in required), "form_invalid")
    require(len(required) == len(set(required)) and set(required) == set(props), "form_required_conflict")
    require(all(type(v) is dict and "x-bvbrc-proteome" in v for v in props.values()), "form_invalid")
    expected = requested_form_schema({name: schema["x-bvbrc-proteome"] for name, schema in props.items()},
        binding_codes=binding_codes, binding_input_kinds=binding_input_kinds)
    expected["required"] = list(required)
    try:
        _plain_json(value)
    except ValueError as error:
        raise ProteomeFactError("form_invalid") from error
    require(canonical(value) == canonical(expected), "form_noncanonical")
    return deepcopy(value)


__all__ = ["ProteomeFactError", "validate_selector", "encode_reference", "decode_reference",
           "reference_schema", "fact_schemas", "requested_form_schema", "validate_requested_form"]
