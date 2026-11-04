"""Pure controlled views of the existing supplied-data disorder authority.

These contracts read no Files and execute neither a predictor nor a calculator.
Canonical data digests identify supplied JSON, not an authenticated producing
attempt. Only the enclosing Return's actual Source is a semantic reference.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from jsonschema import Draft202012Validator, validators

from . import molecular_sequence_result_contracts as stored
from . import protein_disorder_measurements as core
from .domain import canonical


TOOL = "predict_protein_disorder_regions"
SELECTION_VERSION = "protein_disorder_selection_v1"
PACKET_VERSION = "ordinary_protein_disorder_values_v1"
VALUES_VERSION = "protein_disorder_selected_values_v1"
SOURCE_VERSION = "ordinary_protein_disorder_result_v1"
FACT_SOURCE = "protein_disorder_outcomes"
SHEET_VERSION = core.SHEET_SCHEMA
COMPONENTS_VERSION = core.COMPONENTS_SCHEMA
CALCULATOR_ID = "protein_disorder_measurements.calculate_disorder_components"
ENDPOINT = "https://iupred2a.elte.hu/iupred2a"
_SOURCE = re.compile(r"source_[0-9a-f]{24,64}")
_STATES = ("stored_value", "stored_null", "path_missing", "invalid_type")
_STRICT = validators.extend(Draft202012Validator, type_checker=
    Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _checker, value: type(value) is int))


def _require(condition, code="contract_invalid"):
    if not condition:
        raise ValueError("protein_disorder_" + code)


def _copy(value):
    try:
        return stored.copy_json(value)
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("protein_disorder_finite_json_required") from error


def _obj(properties, required=None):
    return dict(type="object", properties=properties,
        required=list(properties) if required is None else required, additionalProperties=False)


def _nullable(schema):
    return {"anyOf": [deepcopy(schema), {"type": "null"}]}


_TEXT = {"type": "string"}
_COUNT = {"type": "integer", "minimum": 0}
_NUMBER = {"type": "number"}
_BOOL = {"type": "boolean"}
_LITERAL = {"$ref": "#/$defs/DisorderLiteral"}
_DEFS = {"DisorderLiteral": {"anyOf": [
    {"type": ["string", "number", "boolean", "null"]},
    {"type": "array", "items": deepcopy(_LITERAL)},
    {"type": "object", "additionalProperties": deepcopy(_LITERAL)}]}}
_ISSUE = dict(type="object", properties={"code": _TEXT, "field": _TEXT},
    required=["code", "field"], additionalProperties=deepcopy(_LITERAL))
_SCORE = _obj({"token": _TEXT, "kind": {"enum": ["finite", "nan", "positive_infinity",
    "negative_infinity", "unparseable"]}, "finite_value": _nullable(_NUMBER)})
_SCORE.update(**{"if": {"properties": {"kind": {"const": "finite"}}},
    "then": {"properties": {"finite_value": _NUMBER}},
    "else": {"properties": {"finite_value": {"type": "null"}}}})
_SPAN = _obj({"subject_ref": _TEXT, "start": _COUNT, "end": _COUNT,
    "unit": _TEXT, "strand": {"enum": ["+", "-"]}})
_INTERVAL = {"type": "array", "prefixItems": [_COUNT, _COUNT], "items": False,
    "minItems": 2, "maxItems": 2}
_TYPES = {
    "number": _NUMBER, "count": _COUNT, "int": {"type": "integer"}, "bool": _BOOL,
    "text": _TEXT, "interval": _INTERVAL,
    "ordinals": {"type": "array", "items": _COUNT},
    "strings": {"type": "array", "items": _TEXT},
    "intervals": {"type": "array", "items": _INTERVAL},
    "spans": {"type": "array", "items": _SPAN},
    "issues": {"type": "array", "items": _ISSUE},
    "score_kind": deepcopy(_SCORE["properties"]["kind"]),
}
_SUM = ("/summary/descriptive_score_sum", "number", "dimensionless_score_sum", "numerator")
_MEAN_N = ("/summary/descriptive_mean_denominator_rows", "count", "rows", "denominator")
_COVERED = ("/summary/unique_usable_input_position_count", "count", "positions", "numerator")
_INPUT_N = ("/summary/input_coverage_denominator_symbols", "count", "ASCII_letters", "denominator")
_HITS = ("/source_equivalent/thresholded_row_count", "count", "rows", "numerator")
_PARSED_N = ("/source_equivalent/parsed_row_denominator", "count", "rows", "denominator")
_SUMMARY_FIELDS = {
    "original_symbol_count": ("count", "original_characters", ()),
    "cleaned_symbol_count": ("count", "ASCII_letters", ()),
    "removed_character_count": ("count", "original_characters", ()),
    "retained_data_row_count": ("count", "data_rows", ()),
    "source_parsed_row_count": ("count", "parsed_row_occurrences", ()),
    "usable_row_occurrence_count": ("count", "usable_row_occurrences", ()),
    "descriptive_score_sum": ("number", "dimensionless_score_sum", ()),
    "descriptive_mean_denominator_rows": ("count", "usable_row_occurrences", ()),
    "descriptive_mean_score": ("number", "dimensionless_predictor_score", (_SUM, _MEAN_N)),
    "unique_usable_input_positions_1based": ("ordinals", "one_based_cleaned_input_positions", ()),
    "unique_usable_input_position_count": ("count", "unique_cleaned_input_positions", ()),
    "input_coverage_denominator_symbols": ("count", "ASCII_letters", ()),
    "unique_input_coverage": ("number", "dimensionless_fraction", (_COVERED, _INPUT_N)),
    "duplicate_native_position_count": ("count", "native_position_labels", ()),
    "duplicate_native_position_occurrence_count": ("count", "parsed_row_occurrences", ()),
    "native_summary_stage_reached_by_source_equivalent": ("bool", None, ()),
    "scientific_service_execution_verified": ("bool", None, ()),
}
_RESIDUE_FIELDS = {
    "position_1based": ("native_values/position_1based", "int", "native_one_based_position_label"),
    "position_token": ("native_values/position_token", "text", None),
    "residue_token": ("native_values/residue_token", "text", "native_residue_token"),
    "score_value": ("native_values/score/finite_value", "number", "dimensionless_predictor_score"),
    "score_token": ("native_values/score/token", "text", None),
    "score_kind": ("native_values/score/kind", "score_kind", None),
    "raw_record": ("raw_record", "text", None),
    "raw_tokens": ("raw_tokens", "strings", None),
    "source_parse_accepted": ("source_parse_accepted", "bool", None),
    "source_parser_index": ("source_parser_index", "count", "zero_based_parsed_row_ordinal"),
    "native_csv_flag": ("native_csv_flag", "text", None),
    "reported_csv_flag_at_ordinal": ("reported_csv_flag_at_ordinal", "text", None),
    "issues": ("issues", "issues", None),
    **{name: ("cells/" + name, typ, unit) for name, typ, unit in (
        ("native_threshold_comparison", "bool", None), ("input_correspondence", "bool", None),
        ("exact_case_match", "bool", None), ("ascii_case_compatible", "bool", None),
        ("cleaned_interval", "interval", "zero_based_half_open_cleaned_characters"),
        ("original_character_interval", "interval", "zero_based_half_open_original_characters"),
        ("source_intervals", "spans", "supplied_source_coordinate_units"),
        ("duplicate_native_position", "bool", None), ("conflicting_native_position", "bool", None),
        ("position_order_increasing", "bool", None), ("usable_for_descriptive_mean", "bool", None),
        ("native_csv_flag_matches_comparison", "bool", None), ("score_in_unit_interval", "bool", None),
        ("position_within_cleaned_input", "bool", None))},
}
_REGION_FIELDS = {
    "start_1based": ("int", "native_one_based_inclusive_position_label"),
    "end_1based": ("int", "native_one_based_inclusive_position_label"),
    "length_residues": ("count", "residues"),
    "member_row_ordinals": ("ordinals", "original_data_row_ordinals"),
    "all_members_correspond_to_input": ("bool", None),
    "all_members_usable_for_descriptive_mean": ("bool", None),
    "cleaned_interval": ("interval", "zero_based_half_open_cleaned_characters"),
    "original_character_intervals": ("intervals", "zero_based_half_open_original_characters"),
    "source_intervals": ("spans", "supplied_source_coordinate_units"),
}


def _identity(value):
    value = _copy(value)
    _require(type(value) is dict and value.get("kind") in ("summary", "residue", "region"), "row_identity_invalid")
    kind = value["kind"]
    key = None if kind == "summary" else "row_ordinal" if kind == "residue" else "region_ordinal"
    _require(set(value) == ({"kind"} if key is None else {"kind", key}), "row_identity_invalid")
    _require(key is None or type(value[key]) is int and value[key] >= 0, "row_identity_invalid")
    return value


def disorder_field_table(identity):
    """Finite paths into unchanged Components; no numerical interpretation."""
    identity = _identity(identity)
    kind = identity["kind"]
    if kind == "summary":
        result = {name: dict(pointer="/summary/" + name, type=typ, unit=unit,
            population="supplied_global_population", operands=[list(item) for item in operands])
            for name, (typ, unit, operands) in _SUMMARY_FIELDS.items()}
        result.update({name: dict(pointer="/source_equivalent/" + field, type=typ, unit=unit,
            population="source_accepted_row_occurrences", operands=[list(item) for item in operands])
            for name, field, typ, unit, operands in (
                ("source_stage", "stage", "text", None, ()),
                ("parsed_row_denominator", "parsed_row_denominator", "count", "parsed_row_occurrences", ()),
                ("thresholded_row_count", "thresholded_row_count", "count", "parsed_row_occurrences", ()),
                ("disordered_percentage", "disordered_percentage", "number", "percent_of_parsed_rows", (_HITS, _PARSED_N)),
                ("expected_percentage_display", "expected_percentage_display", "text", "native_percent_display", ()),
                ("region_count", "region_count", "count", "multi_residue_runs", ()))})
        return result
    if kind == "residue":
        base = "/rows/" + str(identity["row_ordinal"]) + "/"
        return {name: dict(pointer=base + suffix, type=typ, unit=unit,
            population="original_data_row_occurrence", operands=[])
            for name, (suffix, typ, unit) in _RESIDUE_FIELDS.items()}
    base = "/source_equivalent/regions/" + str(identity["region_ordinal"]) + "/"
    return {name: dict(pointer=base + name, type=typ, unit=unit,
        population="source_ordered_multi_residue_run", operands=[])
        for name, (typ, unit) in _REGION_FIELDS.items()}


def _selection_schema():
    variants = []
    for kind, key in (("summary", None), ("residue", "row_ordinal"), ("region", "region_ordinal")):
        identity = dict(kind=kind, **({} if key is None else {key: 0}))
        variants.append(_obj({"row_id": _obj({"kind": {"const": kind}, **({} if key is None else {key: _COUNT})}),
            "fields": {"type": "array", "minItems": 1, "uniqueItems": True,
                "items": {"enum": list(disorder_field_table(identity))}}}))
    return _obj({"version": {"const": SELECTION_VERSION}, "rows": {"type": "array", "items": {"anyOf": variants}}})


SELECTION_SCHEMA = _selection_schema()
ARGUMENT_SCHEMA = {"anyOf": [_obj({"mode": {"const": "predict"}, "protein_sequence": _TEXT,
    "threshold": _nullable(_NUMBER), "max_bytes": {"type": "integer", "minimum": 1},
    "selection": SELECTION_SCHEMA}), *[_obj({"mode": {"const": mode},
        "result_ref": {"type": "string", "pattern": "^source_[0-9a-f]{24,64}$"},
        "selection": SELECTION_SCHEMA}) for mode in ("calculate_saved", "read_stored")]]}


def _document(schema):
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": deepcopy(_DEFS), **deepcopy(schema)}


def _shape(value, schema):
    value = _copy(value)
    try:
        _STRICT(_document(schema)).validate(value)
    except Exception as error:
        raise ValueError("protein_disorder_closed_shape_required") from error
    return value


def validate_disorder_selection(selection):
    """Keep supplied row/field order and repeated requested identities."""
    return _shape(selection, SELECTION_SCHEMA)


def validate_ordinary_disorder_arguments(arguments):
    """Only explicit ordinary predict, saved calculation or selected read."""
    return _shape(arguments, ARGUMENT_SCHEMA)


def _summary_schema():
    return _obj({name: {"const": False} if name == "scientific_service_execution_verified" else
        deepcopy(_BOOL) if typ == "bool" else _nullable(_TYPES[typ])
        for name, (typ, _unit, _operands) in _SUMMARY_FIELDS.items()})


def _source_equivalent_schema():
    return _obj({"stage": {"enum": ["population_unknown", "early_no_parsed_rows", "source_request_error",
        "log_early_return_conflict", "threshold_unknown", "source_equivalent_postprocessing", "retained_partial_csv_arithmetic"]},
        "parsed_row_denominator": _nullable(_COUNT), "thresholded_row_count": _nullable(_COUNT),
        "disordered_percentage": _nullable(_NUMBER), "expected_percentage_display": _nullable(_TEXT),
        "region_count": _nullable(_COUNT)})


def _source_profile_schema():
    return {"const": dict(callable=TOOL, module_sha256=core.SOURCE_SHA256,
        callable_sha256=core.CALLABLE_SHA256, identity_kind="declared_not_execution_receipt",
        algorithm_location="remote_IUPred2A_service", request=dict(url=ENDPOINT, iupred2="long", anchor2="no"),
        source_default_threshold_not_inserted=0.5)}


def _native_log_schema():
    claims = []
    for kind, values in (("parsed_count", _obj({"count": _nullable(_COUNT)})),
            ("region_count", _obj({"count": _nullable(_COUNT)})),
            ("threshold", _obj({"threshold": _SCORE})),
            ("disordered", _obj({"count": _nullable(_COUNT), "percentage": _SCORE}))):
        claims.append(_obj({"kind": {"const": kind}, "line_ordinal": _COUNT,
            "native_line": _TEXT, "values": values}))
    selected = _obj({"parsed_count": _nullable(_obj({"count": _nullable(_COUNT)})),
        "region_count": _nullable(_obj({"count": _nullable(_COUNT)})),
        "threshold": _nullable(_obj({"threshold": _SCORE})),
        "disordered": _nullable(_obj({"count": _nullable(_COUNT), "percentage": _SCORE}))})
    fields = {"supplied": _BOOL, "kind": {"enum": ["missing", "no_valid_data", "request_error", "summary"]},
        "occurrences": {"type": "array", "items": {"anyOf": claims}},
        "regions": {"type": "array", "items": _obj({"row_ordinal": _COUNT, "line_ordinal": _COUNT,
            "native_line": _TEXT, **{key: _nullable({"type": "integer"}) for key in
                ("start_1based", "end_1based", "length_residues")}})},
        "selected": {"anyOf": [_obj({}), selected]},
        "unrecognized_lines": {"type": "array", "items": _obj({"line_ordinal": _COUNT, "native_line": _TEXT})},
        "no_regions_marker_count": _nullable(_COUNT), "issues": _TYPES["issues"],
        "summary_structure_present": _BOOL}
    return _obj(fields, required=[name for name in fields if name != "summary_structure_present"])


def _context_schema():
    return _obj({"input": _obj({"protein_sequence": _nullable(_TEXT),
            "input_ref": _nullable({"type": "string", "minLength": 1}), "input_mapping": _LITERAL}),
        "parameters": _obj({"threshold": _nullable(_NUMBER), "native_outcome": {"enum": ["completed", "partial", "failed"]}}),
        "source_profile": _source_profile_schema(),
        "cleaning": _obj({"expression": {"const": "ASCII-letter selection preserving original case"},
            "cleaned_sequence": _nullable(_TEXT), "original_character_indices": _nullable(_TYPES["ordinals"]),
            **{name: _nullable(_COUNT) for name in ("original_symbol_count", "cleaned_symbol_count", "removed_character_count")}}),
        "mapping": _obj({"supplied": _LITERAL,
            "available": _BOOL, "reason": _nullable(_TEXT)}),
        "status": {"enum": ["complete", "partial", "failed"]}, "authority": {"enum": [None, "response", "csv"]},
        "summary": _summary_schema(), "source_equivalent": _source_equivalent_schema(),
        "native_log": _native_log_schema(),
        "log_checks": _obj({name: _nullable(_BOOL) for name in ("parsed_count_matches", "threshold_matches",
            "thresholded_count_matches", "percentage_display_matches", "regions_match")}),
        "response_csv_join": _obj({"state": {"enum": ["not_supplied", "compatible", "conflict"]},
            "rows": {"type": "array", "items": _obj({"response_row_ordinal": _COUNT,
                "csv_row_ordinal": _nullable(_COUNT), "compatible": _BOOL})}, "counts_match": _nullable(_BOOL)}),
        "original_composition": _nullable({"type": "object", "additionalProperties": _LITERAL}),
        "cleaned_composition": _nullable({"type": "object", "additionalProperties": _LITERAL}),
        "definitions": {"const": core._definitions()}, "issues": _TYPES["issues"]})


def _cell_schema(typ, unit):
    return _obj({"value_state": {"enum": list(_STATES)}, "value": _nullable(_TYPES[typ]),
        "source_pointer": _TEXT, "unit": {"const": unit}})


def _selected_row_schema():
    variants = []
    for identity in ({"kind": "summary"}, {"kind": "residue", "row_ordinal": 0},
            {"kind": "region", "region_ordinal": 0}):
        identity_schema = _obj({key: {"const": value} if key == "kind" else _COUNT for key, value in identity.items()})
        for name, specification in disorder_field_table(identity).items():
            operands = []
            for path, typ, unit, role in specification["operands"]:
                item = _cell_schema(typ, unit)
                item["properties"]["source_pointer"] = {"const": path}
                item["properties"]["role"] = {"const": role}
                item["required"].append("role")
                operands.append(item)
            row = _cell_schema(specification["type"], specification["unit"])
            row["properties"]["source_pointer"] = ({"const": specification["pointer"]} if identity["kind"] == "summary" else
                {"type": "string", "pattern": "^" + re.escape(specification["pointer"]).replace("/0/", "/(0|[1-9][0-9]*)/") + "$"})
            row["properties"].update(row_id=identity_schema, field={"const": name},
                population={"const": specification["population"]}, operands={"type": "array",
                    **({"prefixItems": operands} if operands else {}),
                    "items": False, "minItems": len(operands), "maxItems": len(operands)},
                scientific_qualifiers=_qualifier_schema(identity["kind"]))
            row["required"].extend(("row_id", "field", "population", "operands", "scientific_qualifiers"))
            variants.append(row)
    return {"anyOf": variants}


def _packet_schema():
    return _obj({"version": {"const": PACKET_VERSION}, "selection": SELECTION_SCHEMA,
        "values": _obj({"schema": {"const": VALUES_VERSION},
            "data_identity": _obj({"sheet_schema": {"const": SHEET_VERSION},
                "components_schema": {"const": COMPONENTS_VERSION},
                "sheet_canonical_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "components_canonical_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}),
            "context": _context_schema(), "rows": {"type": "array", "items": _selected_row_schema()}})})


def _valid(value, typ):
    if typ in ("number", "count", "int", "bool", "text", "interval", "ordinals"):
        return stored.valid_type(value, typ)
    return _STRICT(_document(_TYPES[typ])).is_valid(value)


def _record_schema():
    cells = {name: _nullable(_TYPES[typ]) for name, (suffix, typ, _unit) in _RESIDUE_FIELDS.items()
        if suffix.startswith("cells/")}
    for name in ("duplicate_native_position", "conflicting_native_position", "usable_for_descriptive_mean"):
        cells[name] = _BOOL
    required_cells = [name for name in cells if name not in ("score_in_unit_interval", "position_within_cleaned_input")]
    fields = dict(row_ordinal=_COUNT, line_start_1based={"type": "integer", "minimum": 1},
        line_end_1based={"type": "integer", "minimum": 1}, raw_record=_TEXT,
        raw_tokens=_nullable(_TYPES["strings"]), native_values=_nullable(_obj({
            "position_token": _TEXT, "position_1based": _nullable({"type": "integer"}),
            "residue_token": _TEXT, "score": _SCORE})), native_csv_flag=_nullable(_TEXT),
        issues=_TYPES["issues"], source_parse_accepted=_BOOL, source_parser_index=_nullable(_COUNT),
        cells=_obj(cells, required_cells), reported_csv_flag_at_ordinal=_nullable(_TEXT))
    return _obj(fields, [name for name in fields if name != "reported_csv_flag_at_ordinal"])


def _region_schema():
    fields = {name: _nullable(_TYPES[typ]) if name in ("cleaned_interval", "original_character_intervals", "source_intervals")
        else deepcopy(_TYPES[typ]) for name, (typ, _unit) in _REGION_FIELDS.items()}
    fields["region_ordinal"] = _COUNT
    return _obj(fields)


def _qualifier_schema(kind):
    if kind == "summary":
        return _obj({"kind": {"const": kind}})
    if kind == "residue":
        fields = _record_schema()["properties"]
        body = _obj({**{name: deepcopy(fields[name]) for name in
            ("row_ordinal", "source_parse_accepted", "source_parser_index", "cells", "issues")},
            "native_score_kind": _nullable(_TYPES["score_kind"])})
    else:
        fields = _region_schema()["properties"]
        body = _obj({name: deepcopy(fields[name]) for name in ("region_ordinal", "member_row_ordinals",
            "all_members_correspond_to_input", "all_members_usable_for_descriptive_mean")})
    return _obj({"kind": {"const": kind}, "state": {"enum": ["present", "path_missing", "stored_null"]},
        "value": _nullable(body)})


def _qualifiers(components, identity):
    kind = identity["kind"]
    if kind == "summary": return dict(kind=kind)
    path = "/rows/" + str(identity["row_ordinal"]) if kind == "residue" else (
        "/source_equivalent/regions/" + str(identity["region_ordinal"]))
    row = stored.pointer(components, path)
    if row is stored.MISSING:
        null_regions = kind == "region" and stored.pointer(components, "/source_equivalent/regions") is None
        return dict(kind=kind, state="stored_null" if null_regions else "path_missing", value=None)
    keys = ("row_ordinal", "source_parse_accepted", "source_parser_index", "cells", "issues") if kind == "residue" else (
        "region_ordinal", "member_row_ordinals", "all_members_correspond_to_input", "all_members_usable_for_descriptive_mean")
    value = {key: deepcopy(row[key]) for key in keys}
    if kind == "residue":
        value["native_score_kind"] = None if row["native_values"] is None else row["native_values"]["score"]["kind"]
    return dict(kind=kind, state="present", value=value)


def _validate_context(context):
    """Join repeated supplied populations and qualifiers without scoring."""
    context = _shape(context, _context_schema())
    summary, cleaning = context["summary"], context["cleaning"]
    for name in ("original_symbol_count", "cleaned_symbol_count", "removed_character_count"):
        _require(summary[name] == cleaning[name], "input_population_conflict")
    original, cleaned, indices = context["input"]["protein_sequence"], cleaning["cleaned_sequence"], cleaning["original_character_indices"]
    _require((original is None) == (cleaned is None), "input_availability_conflict")
    _require(cleaning["original_symbol_count"] == (None if original is None else len(original)), "input_extent_conflict")
    _require(cleaning["cleaned_symbol_count"] == (None if cleaned is None else len(cleaned)), "cleaned_extent_conflict")
    _require((indices is None) == (cleaned is None) and (indices is None or len(indices) == len(cleaned)
        and indices == sorted(set(indices)) and all(index < len(original) for index in indices)), "cleaning_index_conflict")
    _require(summary["input_coverage_denominator_symbols"] == cleaning["cleaned_symbol_count"], "input_population_conflict")
    _require(summary["usable_row_occurrence_count"] == summary["descriptive_mean_denominator_rows"], "descriptive_population_conflict")
    positions = summary["unique_usable_input_positions_1based"]
    _require(summary["unique_usable_input_position_count"] == (None if positions is None else len(positions))
        and (positions is None or len(positions) == len(set(positions))), "unique_population_conflict")
    _require(summary["source_parsed_row_count"] == context["source_equivalent"]["parsed_row_denominator"], "parsed_population_conflict")
    _require(context["input"]["input_mapping"] == context["mapping"]["supplied"], "mapping_identity_conflict")
    _require(not context["mapping"]["available"] or type(context["mapping"]["supplied"]) is dict
        and context["mapping"]["reason"] is None, "mapping_state_conflict")
    log = context["native_log"]
    _require((log["kind"] == "missing") == (not log["supplied"]), "log_state_conflict")
    _require(not log["supplied"] or "summary_structure_present" in log, "log_state_conflict")
    return context


def _cell(document, path, typ, unit):
    value = stored.pointer(document, path)
    state = "path_missing" if value is stored.MISSING else "stored_null" if value is None else (
        "stored_value" if _valid(value, typ) else "invalid_type")
    return dict(value_state=state, value=deepcopy(value) if state == "stored_value" else None,
        source_pointer=path, unit=unit)


def _component_linkage(sheet, components):
    """Check duplicated observations/identities without re-parsing or scoring."""
    sheet, components = _copy(sheet), _copy(components)
    _require(type(sheet) is dict and set(sheet) == {"schema", "inputs", "source_profile", "cleaning",
        "original_composition_sheet", "cleaned_composition_sheet", "mapping", "response", "csv", "log",
        "authority", "response_csv_join", "rows", "log_checks", "status", "issues"}
        and sheet.get("schema") == SHEET_VERSION, "sheet_required")
    _require(type(components) is dict and set(components) == {"schema", "status", "authority", "rows",
        "source_equivalent", "native_log", "log_checks", "response_csv_join", "original_composition",
        "cleaned_composition", "summary", "definitions", "issues"}
        and components["schema"] == COMPONENTS_VERSION, "components_required")
    _require(type(sheet.get("inputs")) is dict and set(sheet["inputs"]) == {"native_csv", "protein_sequence",
        "threshold", "native_response", "native_log", "native_outcome", "input_ref", "input_mapping"}, "sheet_inputs_required")
    _shape(sheet["inputs"], _obj({**{key: _nullable(_TEXT) for key in
        ("native_csv", "protein_sequence", "native_response", "native_log", "input_ref")},
        "threshold": _nullable(_NUMBER), "native_outcome": {"enum": ["completed", "partial", "failed"]},
        "input_mapping": _LITERAL}))
    _require(type(components["source_equivalent"]) is dict
        and set(components["source_equivalent"]) == {*_source_equivalent_schema()["properties"], "regions"},
        "source_equivalent_shape_invalid")
    for key, original in (("rows", "rows"), ("status", "status"), ("authority", "authority"),
            ("native_log", "log"), ("log_checks", "log_checks"),
            ("response_csv_join", "response_csv_join"), ("issues", "issues")):
        _require(canonical(components[key]) == canonical(sheet.get(original)), "sheet_components_conflict")
    _shape(components["rows"], {"type": "array", "items": _record_schema()})
    _require(type(components["rows"]) is list and all(type(row) is dict and row.get("row_ordinal") == index
        and type(row.get("row_ordinal")) is int for index, row in enumerate(components["rows"])), "row_ordinal_conflict")
    _require(all(row["line_end_1based"] >= row["line_start_1based"] for row in components["rows"]), "row_line_conflict")
    regions = components["source_equivalent"].get("regions")
    _shape(regions, _nullable({"type": "array", "items": _region_schema()}))
    _require(regions is None or type(regions) is list and all(type(row) is dict
        and type(row.get("region_ordinal")) is int and row["region_ordinal"] == index
        for index, row in enumerate(regions)), "region_ordinal_conflict")
    context = dict(input={key: deepcopy(sheet["inputs"][key]) for key in ("protein_sequence", "input_ref", "input_mapping")},
        parameters={key: deepcopy(sheet["inputs"][key]) for key in ("threshold", "native_outcome")},
        source_profile=deepcopy(sheet.get("source_profile")), cleaning=deepcopy(sheet.get("cleaning")),
        mapping=deepcopy(sheet.get("mapping")), **{key: deepcopy(components[key]) for key in (
            "status", "authority", "summary", "native_log", "log_checks", "response_csv_join",
            "original_composition", "cleaned_composition", "definitions", "issues")},
        source_equivalent={key: deepcopy(value) for key, value in components["source_equivalent"].items() if key != "regions"})
    _validate_context(context)
    _require(context["summary"]["retained_data_row_count"] == (None if context["authority"] is None else len(components["rows"])), "row_population_conflict")
    _require(context["source_equivalent"]["region_count"] == (None if regions is None else len(regions)), "region_population_conflict")
    _require(context["summary"]["scientific_service_execution_verified"] is False, "calculator_attestation_conflict")
    return sheet, components, context


def ordinary_disorder_packet(*, arguments, sheet, components):
    """Select supplied stored cells; never construct CSV/logs or call the owner."""
    arguments = validate_ordinary_disorder_arguments(arguments)
    sheet, components, context = _component_linkage(sheet, components)
    if arguments["mode"] == "predict":
        _require(canonical(sheet["inputs"]["protein_sequence"]) == canonical(arguments["protein_sequence"])
            and canonical(sheet["inputs"]["threshold"]) == canonical(arguments["threshold"]), "predict_input_conflict")
        _require(sheet["inputs"]["input_ref"] is None and sheet["inputs"]["input_mapping"] is None,
            "inline_input_provenance_conflict")
    rows = []
    for request in arguments["selection"]["rows"]:
        identity = request["row_id"]
        table = disorder_field_table(identity)
        for name in request["fields"]:
            spec = table[name]
            operands = [dict(**_cell(components, path, typ, unit), role=role)
                for path, typ, unit, role in spec["operands"]]
            rows.append(dict(row_id=deepcopy(identity), field=name, **_cell(components,
                spec["pointer"], spec["type"], spec["unit"]), population=spec["population"], operands=operands,
                scientific_qualifiers=_qualifiers(components, identity)))
    identity = dict(sheet_schema=SHEET_VERSION, components_schema=COMPONENTS_VERSION,
        sheet_canonical_sha256=hashlib.sha256(canonical(sheet).encode()).hexdigest(),
        components_canonical_sha256=hashlib.sha256(canonical(components).encode()).hexdigest())
    return validate_ordinary_disorder_packet(dict(version=PACKET_VERSION, selection=arguments["selection"],
        values=dict(schema=VALUES_VERSION, data_identity=identity, context=context, rows=rows)))


def _validate_cell(cell, *, path, typ, unit):
    _require(cell["source_pointer"] == path and cell["unit"] == unit, "cell_identity_conflict")
    state, value = cell["value_state"], cell["value"]
    _require((state == "stored_value") == (value is not None), "cell_state_conflict")
    _require(state != "stored_value" or _valid(value, typ), "cell_type_conflict")


def validate_ordinary_disorder_packet(value):
    """Validate shapes, requested paths and supplied operand joins only."""
    value = _shape(value, _packet_schema())
    rows, context = value["values"]["rows"], value["values"]["context"]
    _validate_context(context)
    expected = [(request["row_id"], field) for request in value["selection"]["rows"] for field in request["fields"]]
    _require([(row["row_id"], row["field"]) for row in rows] == expected, "selection_row_conflict")
    _require(context["summary"]["scientific_service_execution_verified"] is False, "calculator_attestation_conflict")
    qualifier_copies = {}
    for row in rows:
        spec = disorder_field_table(row["row_id"])[row["field"]]
        _validate_cell(row, path=spec["pointer"], typ=spec["type"], unit=spec["unit"])
        _require(row["population"] == spec["population"] and len(row["operands"]) == len(spec["operands"]), "operand_identity_conflict")
        for operand, (path, typ, unit, role) in zip(row["operands"], spec["operands"]):
            _validate_cell(operand, path=path, typ=typ, unit=unit)
            _require(operand["role"] == role, "operand_identity_conflict")
            # Every denominator operand is also present in the full context.
            expected_cell = _cell(context, path, typ, unit)
            _require({key: operand[key] for key in expected_cell} == expected_cell, "context_operand_conflict")
        if row["row_id"]["kind"] == "summary":
            expected_cell = _cell(context, spec["pointer"], spec["type"], spec["unit"])
            _require({key: row[key] for key in expected_cell} == expected_cell, "context_value_conflict")
        else:
            qualifiers = row["scientific_qualifiers"]
            identity = canonical(row["row_id"])
            _require(identity not in qualifier_copies or qualifier_copies[identity] == canonical(qualifiers), "qualifier_copy_conflict")
            qualifier_copies[identity] = canonical(qualifiers)
            _require((qualifiers["state"] == "present") == (qualifiers["value"] is not None), "qualifier_state_conflict")
            _require(qualifiers["state"] == "present" or row["value_state"] == "path_missing", "qualifier_availability_conflict")
            if qualifiers["value"] is not None:
                key = "row_ordinal" if row["row_id"]["kind"] == "residue" else "region_ordinal"
                _require(qualifiers["value"][key] == row["row_id"][key], "qualifier_identity_conflict")
                if row["row_id"]["kind"] == "residue":
                    relative = "/" + "/".join(spec["pointer"].split("/")[3:])
                    if relative.startswith("/cells/") or relative in ("/source_parse_accepted", "/source_parser_index", "/issues"):
                        expected_cell = _cell(qualifiers["value"], relative, spec["type"], spec["unit"])
                        _require(row["value_state"] == expected_cell["value_state"]
                            and row["value"] == expected_cell["value"], "qualifier_value_conflict")
                    if row["field"] == "score_kind":
                        _require(row["value"] == qualifiers["value"]["native_score_kind"], "qualifier_value_conflict")
                    if row["field"] == "score_value":
                        kind = qualifiers["value"]["native_score_kind"]
                        _require(row["value_state"] == ("path_missing" if kind is None else
                            "stored_value" if kind == "finite" else "stored_null"), "score_kind_conflict")
    return value


def project_ordinary_disorder_return(packet, source_ref):
    packet = validate_ordinary_disorder_packet(packet)
    return validate_ordinary_disorder_return(dict(source_ref=source_ref, **packet))


def validate_ordinary_disorder_return(value):
    value = _copy(value)
    _require(type(value) is dict and type(value.get("source_ref")) is str
        and _SOURCE.fullmatch(value["source_ref"]) is not None, "source_required")
    validate_ordinary_disorder_packet({key: item for key, item in value.items() if key != "source_ref"})
    return value


def protein_disorder_result_schema(kind="Return"):
    """Detached schemas; only the top Return Source has reference semantics."""
    if kind == "Selection": return _document(SELECTION_SCHEMA)
    if kind == "Arguments": return _document(ARGUMENT_SCHEMA)
    body = _packet_schema()
    if kind == "Return":
        body["properties"]["source_ref"] = {"type": "string", "pattern": "^source_[0-9a-f]{24,64}$",
            "format": "reference", "x-reference-namespace": "source"}
        body["required"].append("source_ref")
    else:
        _require(kind == "Packet", "schema_kind_invalid")
    return _document(body)


def ordinary_disorder_fact_sources():
    item = protein_disorder_result_schema("Return")
    meaning = ("Selected supplied IUPred2A-style long-mode disorder outputs, with separate parsed-row, "
        "finite descriptive-row and unique-input coverage populations. Scores are dimensionless predictor "
        "outputs, not calibrated function confidence. Source declarations and supplied-data calculations "
        "do not authenticate service execution. Nested provenance grants no Files or references.")
    schema = {key: item[key] for key in ("$schema", "$defs")}
    schema.update(type="array", items={key: child for key, child in item.items() if key not in ("$schema", "$defs")},
        **{"x-source": FACT_SOURCE})
    return {FACT_SOURCE: dict(type="array", report_schema=schema, description=meaning, meaning=meaning)}


__all__ = ["TOOL", "SELECTION_VERSION", "PACKET_VERSION", "VALUES_VERSION", "SOURCE_VERSION", "FACT_SOURCE",
    "SHEET_VERSION", "COMPONENTS_VERSION", "CALCULATOR_ID", "ENDPOINT", "SELECTION_SCHEMA", "ARGUMENT_SCHEMA",
    "validate_disorder_selection", "disorder_field_table", "validate_ordinary_disorder_arguments",
    "ordinary_disorder_packet", "validate_ordinary_disorder_packet", "project_ordinary_disorder_return",
    "validate_ordinary_disorder_return", "protein_disorder_result_schema", "ordinary_disorder_fact_sources"]
