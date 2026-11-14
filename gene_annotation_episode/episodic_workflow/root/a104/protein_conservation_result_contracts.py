"""Pure ordinary views of retained alignment rows and literal conservation.

The neutral alignment and calculation contracts remain the scientific owners.
These DTOs neither run them nor authenticate a producer, File, Source or label
association. Only the outer Return Source is a semantic reference.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator, validators

from . import phylogeny_calculation_contracts as c
from . import phylogeny_format_contracts as f


TOOL = "analyze_protein_conservation"
SOURCE_VERSION = "ordinary_protein_conservation_result_v1"
PACKET_VERSION = "ordinary_protein_conservation_values_v1"
SELECTION_VERSION = "protein_conservation_selection_v1"
FACT_SOURCE = "protein_conservation_outcomes"
_SOURCE = r"^source_[0-9a-f]{24,64}$"
_ARTIFACT = r"^artifact_[0-9a-f]{64}$"
_COMPLETENESS = list(c.COMPLETENESS)
_CAPTURE_STATES = ["complete", "partial", "truncated", "missing", "unknown"]
_THRESHOLD = {"comparison": "strict_greater_than", "value": 0.8,
              "basis": "unrounded_binary64_ratio"}
_DISPLAY = {"decimal_places": 2, "rounding": "binary64_fixed_2_ties_to_even"}
_ALIGNMENT_KEYS = ("alignment_id", "artifact", "format", "layout", "id_rule", "encoding",
    "declared_row_count", "declared_column_count", "observed_row_count",
    "observed_column_count", "completeness")


def _require(condition, code):
    if not condition:
        raise ValueError("protein_conservation_" + code)


def _copy(value, seen=None):
    """Detach JSON without coercing native types or accepting cycles/NaN."""
    kind = type(value)
    if value is None or kind in (str, bool, int):
        return value
    if kind is float:
        _require(math.isfinite(value), "json_invalid")
        return value
    _require(kind in (dict, list), "json_invalid")
    seen = set() if seen is None else seen
    _require(id(value) not in seen, "json_invalid")
    seen.add(id(value))
    try:
        if kind is list:
            return [_copy(item, seen) for item in value]
        _require(all(type(key) is str for key in value), "json_invalid")
        return {key: _copy(item, seen) for key, item in value.items()}
    finally:
        seen.remove(id(value))


def _obj(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _ref(name):
    return {"$ref": "#/$defs/" + name}


def _nullable(schema):
    return {"anyOf": [{"type": "null"}, schema]}


def _array(items, *, unique=False):
    result = {"type": "array", "items": items}
    if unique:
        result["uniqueItems"] = True
    return result


def _definitions():
    text = {"type": "string", "minLength": 1}
    string = {"type": "string"}
    integer = {"type": "integer", "minimum": 0}
    indices = _array(integer, unique=True)
    strings = _array(text, unique=True)
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    artifact = _obj({"raw_artifact_ref": text, "source_ref": text, "sha256": sha})
    location = _obj({"artifact": _ref("Artifact"),
        "byte_start_0based": _nullable(integer), "byte_end_0based_exclusive": _nullable(integer),
        "line_start_1based": _nullable({"type": "integer", "minimum": 1}),
        "line_end_1based_inclusive": _nullable({"type": "integer", "minimum": 1}),
        "xml_path": _nullable(text)})
    evidence = _array(_obj({"content": _obj({"source_ref": text,
        "artifact_field": {"enum": ["artifact_ref", "text_ref", "stdout_ref", "stderr_ref"]},
        "artifact_ref": text, "sha256": sha, "byte_count": integer}), "pointer": string}))
    population = _obj({"population_id": text, "alignment_id": text,
        "row_indices": indices, "columns_0based": indices,
        "completeness": {"enum": _COMPLETENESS}, "evidence": evidence})
    request_common = {"label": text, "completeness": {"enum": _COMPLETENESS}}
    population_request = {"oneOf": [
        _obj({"kind": {"const": "all_output_rows_and_columns"}, **request_common}),
        _obj({"kind": {"const": "explicit_output_indices"}, **request_common,
            "row_indices": indices, "columns_0based": indices})]}
    selection = _obj({"version": {"const": SELECTION_VERSION},
        "native_rows": _obj({"row_indices": _nullable(indices), "offset": integer, "limit": integer}),
        "sites": _obj({"columns_0based": _nullable(indices), "offset": integer, "limit": integer})})
    input_selection = _obj({"namespace": {"enum": ["artifact", "source"]},
        "reference": {"type": "string", "pattern":
            "^(artifact_[0-9a-f]{64}|source_[0-9a-f]{24,64})$"}, "format": {"const": "fasta"}})
    file = _obj({"artifact_ref": {"type": "string", "pattern": _ARTIFACT},
        "sha256": sha, "size_bytes": integer, "format": {"const": "fasta"}})
    capture = _obj({"state": {"enum": _CAPTURE_STATES},
        "retained_size_bytes": _nullable(integer), "original_size_bytes": _nullable(integer)})
    input_record = _obj({"selection": _ref("InputSelection"), "file": _ref("File"),
        "source_ref": _nullable({"type": "string", "pattern": _SOURCE}), "capture": _ref("Capture"),
        "records_state": {"enum": ["available", "partial", "unavailable"]},
        "records": _array(_obj({"record_ordinal": integer, "byte_start": integer, "byte_end": integer,
            "header": string, "status": {"enum": ["available", "incompatible"]}, "issues": strings})),
        "issues": strings})
    native_execution = _obj({"state": {"enum": ["completed", "failed", "unknown", "not_attempted"]},
        "returncode": _nullable({"type": "integer"}), "reported_version": _nullable(text),
        "alphabet": _obj({"state": {"enum": ["reported", "unknown"]}, "value": _nullable(text)}),
        "output_capture": _ref("Capture"),
        "parser_status": {"enum": ["ok", "partial", "invalid", "not_parsed"]}})
    alignment = _obj({"alignment_id": text, "artifact": _ref("Artifact"),
        "format": {"const": "aligned_fasta"}, "layout": {"const": "fasta"},
        "id_rule": {"const": "first_whitespace_token"}, "encoding": {"enum": ["ascii", "utf-8"]},
        "declared_row_count": {"type": "null"}, "declared_column_count": {"type": "null"},
        "observed_row_count": integer, "observed_column_count": _nullable(integer),
        "completeness": {"enum": _COMPLETENESS}})
    native_row = _obj({"row_index": integer, "raw_header": string, "member_label": string,
        "sequence": string,
        "source_location": _ref("Location")})
    quantity = _obj({"value": _nullable({"type": "number"}), "state": {"enum": list(c.STATES)},
        "unit": text, "origin": {"const": "derived"},
        "numerator": _nullable({"type": "number"}), "denominator": _nullable({"type": "number"}),
        "population_ref": text, "method": text, "evidence": evidence, "requirement_ids": strings})
    def quantity_for(unit, method, *, integer_value=False, fraction=False):
        result = deepcopy(quantity)
        result["properties"]["unit"] = {"const": unit}
        result["properties"]["method"] = {"const": method}
        number = {"type": "integer", "minimum": 0} if integer_value else {"type": "number"}
        if fraction:
            number.update(minimum=0, maximum=1)
        result["properties"]["value"] = _nullable(number)
        return result
    site = _obj({"column_0based": integer,
        "symbol_counts": _array(_obj({"symbol": {"type": "string", "minLength": 1, "maxLength": 1},
            "count": {"type": "integer", "minimum": 1}})),
        "modal_symbol": _nullable({"type": "string", "minLength": 1, "maxLength": 1}),
        "modal_first_source_row_index": _nullable(integer),
        "modal_count": quantity_for("characters", "literal_modal_symbol_count", integer_value=True),
        "majority_fraction": quantity_for("fraction", "literal_modal_all_rows_fraction", fraction=True),
        "strict_gt_0_8": _nullable({"type": "boolean"}),
        "displayed_2dp_fraction": quantity_for("fraction", "literal_modal_fraction_fixed_2", fraction=True)})
    associations = _obj({"state": {"enum": ["available", "partial", "unavailable"]},
        "rows": _array(_obj({"output_row_index": integer, "input_record_ordinals": indices,
            "state": {"enum": ["unique_label_match", "ambiguous_label_match", "unmatched_output_label",
                "unavailable_input_records"]}})),
        "unmatched_input_record_ordinals": _nullable(indices)})
    issue = _obj({"code": text, "phase": text, "path": string,
        "severity": {"enum": ["error", "qualification"]}, "evidence_refs": strings})
    context = _obj({"input": _nullable(_ref("Input")), "native_execution": _ref("NativeExecution"),
        "alignment": _nullable(_ref("Alignment")), "population_request": _ref("PopulationRequest"),
        "population_resolution": _obj({"state": {"enum": ["resolved", "unresolved"]}, "reason_codes": strings}),
        "population": _nullable(_ref("Population")),
        "components_version": _nullable({"const": c.LITERAL_CONSERVATION_VERSION}),
        "convention": {"const": c.LITERAL_CONSERVATION_CONVENTION},
        "threshold": {"const": _THRESHOLD}, "display": {"const": _DISPLAY},
        "ordered_source_row_indices": _nullable(indices),
        "member_count": _nullable(quantity_for("rows", "selected_row_count", integer_value=True)),
        "site_count": _nullable(quantity_for("columns", "selected_column_count", integer_value=True)),
        "row_associations": _ref("Associations"),
        "issues": _array(issue)})
    count = _obj({"retained_record_count": _nullable(integer), "selected_record_count": _nullable(integer),
        "returned_record_count": integer, "omitted_record_count": _nullable(integer)})
    value = _obj({"version": {"const": PACKET_VERSION}, "selection": _ref("Selection"),
        "context": _ref("Context"), "native_rows": _array(_ref("NativeRow")),
        "sites": _array(_ref("Site")), "accounting": _obj({"native_rows": _ref("Accounting"),
            "sites": _ref("Accounting")})})
    returned = deepcopy(value)
    returned["properties"]["source_ref"] = {"type": "string", "pattern": _SOURCE,
        "format": "reference", "x-reference-namespace": "source"}
    returned["required"].append("source_ref")
    arguments = {"oneOf": [
        _obj({"mode": {"const": "run_native"}, "input": _ref("InputSelection"),
            "population_request": _ref("PopulationRequest"), "selection": _ref("Selection")}),
        _obj({"mode": {"const": "calculate_saved"}, "result_ref": {"type": "string", "pattern": _SOURCE},
            "population_request": _ref("PopulationRequest"), "selection": _ref("Selection")}),
        _obj({"mode": {"const": "read_stored"}, "result_ref": {"type": "string", "pattern": _SOURCE},
            "selection": _ref("Selection")})]}
    return {"Artifact": artifact, "Location": location, "Population": population,
        "PopulationRequest": population_request, "Selection": selection, "InputSelection": input_selection,
        "File": file, "Capture": capture, "Input": input_record, "NativeExecution": native_execution,
        "Alignment": alignment, "NativeRow": native_row, "Quantity": quantity, "Site": site,
        "Associations": associations, "Context": context, "Accounting": count,
        "Value": value, "Return": returned, "Arguments": arguments}


_DEFINITIONS = _definitions()
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _checker, value: type(value) is int)
    .redefine("number", lambda _checker, value: type(value) is int or
        type(value) is float and math.isfinite(value))
    .redefine("array", lambda _checker, value: type(value) is list)
    .redefine("object", lambda _checker, value: type(value) is dict))


def conservation_result_schema(kind="Value"):
    """Return a detached schema; only Return.source_ref grants a Source."""
    _require(kind in ("Value", "Return", "Selection", "PopulationRequest", "Arguments"), "schema_kind_invalid")
    needed, pending = {}, [kind]
    while pending:
        name = pending.pop()
        if name in needed:
            continue
        needed[name] = deepcopy(_DEFINITIONS[name])
        def visit(node):
            if type(node) is dict:
                if "$ref" in node:
                    pending.append(node["$ref"].split("/")[-1])
                for child in node.values():
                    visit(child)
            elif type(node) is list:
                for child in node:
                    visit(child)
        visit(needed[name])
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": needed,
            "$ref": "#/$defs/" + kind}


def _validated(value, kind):
    value = _copy(value)
    _require(_STRICT(conservation_result_schema(kind)).is_valid(value), kind.lower() + "_invalid")
    return value


def _node(value, name):
    value = _copy(value)
    _require(_STRICT({"$defs": _DEFINITIONS, "$ref": "#/$defs/" + name}).is_valid(value),
        name.lower() + "_invalid")
    return value


def validate_conservation_selection(value):
    return _validated(value, "Selection")


def validate_conservation_arguments(value):
    value = _validated(value, "Arguments")
    if value["mode"] == "run_native":
        item = value["input"]
        pattern = _SOURCE if item["namespace"] == "source" else _ARTIFACT
        _require(re.fullmatch(pattern, item["reference"]) is not None, "input_namespace_conflict")
    else:
        _require(re.fullmatch(_SOURCE, value["result_ref"]) is not None, "result_source_invalid")
    return value


def bind_conservation_population(population_request, *, alignment, evidence):
    """Bind supplied scope to retained identity; do not infer its completeness.

    All-output means this retained output matrix, not all original input
    members. Capture/process qualifications remain separate. Evidence is
    supplied by the host; this helper authenticates neither it nor any Source.
    """
    request = _validated(population_request, "PopulationRequest")
    evidence = _copy(evidence)
    c.evidence(evidence)
    if alignment is None:
        return {"population": None, "resolution": {"state": "unresolved",
            "reason_codes": ["alignment_unavailable"]}}
    alignment = f.validate_alignment_document(_copy(alignment))
    _require(alignment["format"] == "aligned_fasta", "alignment_format_invalid")
    if request["kind"] == "all_output_rows_and_columns":
        columns = alignment["observed_column_count"]
        if columns is None:
            return {"population": None, "resolution": {"state": "unresolved",
                "reason_codes": ["output_column_dimension_unresolved"]}}
        rows, columns = list(range(len(alignment["rows"]))), list(range(columns))
    else:
        rows, columns = request["row_indices"], request["columns_0based"]
    population = {"population_id": request["label"], "alignment_id": alignment["alignment_id"],
        "row_indices": deepcopy(rows), "columns_0based": deepcopy(columns),
        "completeness": request["completeness"], "evidence": evidence}
    c.alignment_population(population, alignment)
    return {"population": population, "resolution": {"state": "resolved", "reason_codes": []}}


def _capture(value):
    retained, original = value["retained_size_bytes"], value["original_size_bytes"]
    _require(retained is None or original is None or retained <= original, "capture_extent_conflict")
    if value["state"] == "complete":
        _require(retained is not None and (original is None or retained == original), "capture_extent_conflict")
    if value["state"] == "missing":
        _require(retained is None, "capture_extent_conflict")


def _input(value):
    if value is None:
        return
    file, selected = value["file"], value["selection"]
    _require(file["artifact_ref"] == "artifact_" + file["sha256"], "input_file_conflict")
    expected = value["source_ref"] if selected["namespace"] == "source" else file["artifact_ref"]
    _require(selected["reference"] == expected, "input_selection_conflict")
    _require(selected["namespace"] != "artifact" or value["source_ref"] is None,
        "input_source_role_conflict")
    _require(value["source_ref"] is None or re.fullmatch(_SOURCE, value["source_ref"]) is not None,
        "input_source_invalid")
    _capture(value["capture"])
    _require(value["capture"]["retained_size_bytes"] == file["size_bytes"]
        and value["capture"]["state"] != "missing", "input_capture_conflict")
    records = value["records"]
    _require([row["record_ordinal"] for row in records] == list(range(len(records))), "input_records_conflict")
    previous_end = 0
    for row in records:
        _require(previous_end <= row["byte_start"] < row["byte_end"] <= file["size_bytes"],
            "input_record_extent_conflict")
        previous_end = row["byte_end"]
        _require(row["status"] != "available" or bool(_label(row["header"])), "input_records_conflict")
    if value["records_state"] == "unavailable":
        _require(records == [], "input_records_conflict")
    elif value["records_state"] == "available":
        _require(all(row["status"] == "available" for row in records), "input_records_conflict")


def _execution(value, alignment):
    _capture(value["output_capture"])
    if value["state"] == "completed":
        _require(value["returncode"] == 0, "native_state_conflict")
    elif value["state"] == "failed":
        _require(value["returncode"] is None or value["returncode"] != 0, "native_state_conflict")
    elif value["state"] == "not_attempted":
        _require(value["returncode"] is None, "native_state_conflict")
    _require((value["alphabet"]["value"] is not None) == (value["alphabet"]["state"] == "reported"),
        "native_alphabet_conflict")
    if alignment is None:
        _require(value["parser_status"] in ("invalid", "not_parsed"), "parser_state_conflict")
    else:
        _require(value["parser_status"] != "not_parsed", "parser_state_conflict")
        if value["parser_status"] == "ok":
            _require(alignment["completeness"] == "complete", "parser_state_conflict")
        elif value["parser_status"] == "partial":
            _require(alignment["completeness"] == "partial" and alignment["observed_row_count"] > 0,
                "parser_state_conflict")
        elif value["parser_status"] == "invalid":
            _require(alignment["completeness"] == "partial" and alignment["observed_row_count"] == 0,
                "parser_state_conflict")


def _label(header):
    tokens = header.split()
    return tokens[0] if tokens else ""


def _associations(value, input_record, alignment_rows, *, full_rows, output_available):
    records = [] if input_record is None else input_record["records"]
    complete = input_record is not None and input_record["records_state"] == "available"
    available = output_available and (complete or any(row["status"] == "available" for row in records))
    by_label = {}
    for row in records:
        if row["status"] == "available":
            by_label.setdefault(row["header"], []).append(row["record_ordinal"])
    rows = value["rows"]
    indices = [row["output_row_index"] for row in rows]
    _require(len(set(indices)) == len(indices), "association_rows_conflict")
    if full_rows is not None:
        _require(indices == [row["row_index"] for row in full_rows], "association_rows_conflict")
        alignment_rows = full_rows
    known = {row["row_index"]: row for row in alignment_rows}
    labels = [row["raw_header"] for row in alignment_rows]
    seen_inputs = set()
    for row in rows:
        candidates = row["input_record_ordinals"]
        _require(all(i < len(records) for i in candidates), "association_input_conflict")
        if not available:
            _require(candidates == [] and row["state"] == "unavailable_input_records",
                "association_state_conflict")
        else:
            _require(all(records[i]["status"] == "available" for i in candidates), "association_input_conflict")
            _require(row["state"] in (("unmatched_output_label",) if not candidates and complete else
                ("unavailable_input_records",) if not candidates else
                ("ambiguous_label_match",) if len(candidates) > 1 or not complete else
                ("unique_label_match", "ambiguous_label_match")), "association_state_conflict")
        if available and row["output_row_index"] in known:
            label = known[row["output_row_index"]]["raw_header"]
            _require(candidates == by_label.get(label, []), "association_label_conflict")
            if not candidates:
                expected = "unmatched_output_label" if complete else "unavailable_input_records"
            elif len(candidates) > 1 or labels.count(label) > 1 or not complete:
                expected = "ambiguous_label_match"
            else:
                expected = "unique_label_match"
            # Public selection can hide duplicate output siblings; ambiguity
            # may therefore be retained even when this view has one row.
            _require(row["state"] == expected or full_rows is None
                and expected == "unique_label_match" and row["state"] == "ambiguous_label_match",
                "association_state_conflict")
        seen_inputs.update(candidates)
    if not available:
        _require(value["state"] == "unavailable" and value["unmatched_input_record_ordinals"] is None,
            "association_state_conflict")
    else:
        expected = [i for i in range(len(records)) if i not in seen_inputs] if complete else None
        _require(value["unmatched_input_record_ordinals"] == expected, "association_unmatched_conflict")
        expected_state = "available" if complete else "partial"
        _require(value["state"] == expected_state, "association_state_conflict")


def _quantity(value, *, population, unit, method, integer=False):
    _require(value["population_ref"] == population and value["unit"] == unit
        and value["method"] == method and value["origin"] == "derived"
        and (value["value"] is not None) == (value["state"] == "available"), "quantity_conflict")
    if integer:
        _require(value["value"] is None or type(value["value"]) is int and value["value"] >= 0,
            "quantity_conflict")
    c.evidence(value["evidence"])


def _site(value, context):
    population = context["population"]
    _require(population is not None and value["column_0based"] in population["columns_0based"],
        "site_population_conflict")
    symbols = [row["symbol"] for row in value["symbol_counts"]]
    _require(symbols == sorted(set(symbols)), "site_symbols_conflict")
    first, symbol = value["modal_first_source_row_index"], value["modal_symbol"]
    _require((first is None) == (symbol is None) and (first is None or
        first in context["ordered_source_row_indices"]), "site_modal_conflict")
    for name, unit, method, integer in (("modal_count", "characters", "literal_modal_symbol_count", True),
            ("majority_fraction", "fraction", "literal_modal_all_rows_fraction", False),
            ("displayed_2dp_fraction", "fraction", "literal_modal_fraction_fixed_2", False)):
        _quantity(value[name], population=population["population_id"], unit=unit, method=method, integer=integer)
    for name in ("majority_fraction", "displayed_2dp_fraction"):
        _require(value[name]["value"] is None or 0 <= value[name]["value"] <= 1, "site_fraction_conflict")


def _view_indices(available, selected, key):
    indices = selected[key]
    if available is None:
        return [] if indices == [] else None
    if indices is None:
        return available
    _require(all(index in available for index in indices), "selection_outside_retained_values")
    return indices


def _accounting(available, selected, returned):
    return {"retained_record_count": None if available is None else len(available),
        "selected_record_count": None if selected is None else len(selected),
        "returned_record_count": len(returned),
        "omitted_record_count": None if selected is None else len(selected) - len(returned)}


def _page(indices, selection):
    return [] if indices is None else indices[selection["offset"]:selection["offset"] + selection["limit"]]


def _validate_value(value):
    context = value["context"]
    metadata, population = context["alignment"], context["population"]
    _input(context["input"])
    _execution(context["native_execution"], metadata)
    _require(type(context["threshold"]["value"]) is float
        and type(context["display"]["decimal_places"]) is int, "definitions_invalid")
    if metadata is not None:
        f._artifact(metadata["artifact"])
        _require(metadata["alignment_id"] == metadata["artifact"]["raw_artifact_ref"] + "#alignment",
            "alignment_identity_conflict")
        if metadata["observed_row_count"] == 0 and metadata["observed_column_count"] is not None:
            _require(metadata["observed_column_count"] == 0 and metadata["completeness"] == "complete",
                "alignment_dimension_conflict")
        if metadata["completeness"] == "complete":
            _require(metadata["observed_column_count"] is not None, "alignment_dimension_conflict")
    resolved = context["population_resolution"]
    request = context["population_request"]
    if population is None:
        expected = "alignment_unavailable" if metadata is None else "output_column_dimension_unresolved"
        _require(resolved == {"state": "unresolved", "reason_codes": [expected]}
            and (metadata is None or request["kind"] == "all_output_rows_and_columns"
                and metadata["observed_column_count"] is None), "population_resolution_conflict")
    else:
        _require(metadata is not None and resolved == {"state": "resolved", "reason_codes": []}
            and population["population_id"] == request["label"]
            and population["alignment_id"] == metadata["alignment_id"]
            and population["completeness"] == request["completeness"], "population_identity_conflict")
        c.evidence(population["evidence"])
        _require(all(index < metadata["observed_row_count"] for index in population["row_indices"]),
            "population_rows_conflict")
        if request["kind"] == "all_output_rows_and_columns":
            _require(metadata["observed_column_count"] is not None and population["row_indices"] ==
                list(range(metadata["observed_row_count"])) and population["columns_0based"] ==
                list(range(metadata["observed_column_count"])), "population_scope_conflict")
        else:
            _require(population["row_indices"] == request["row_indices"]
                and population["columns_0based"] == request["columns_0based"], "population_scope_conflict")
        bound = metadata["observed_column_count"]
        if bound is None:
            bound = metadata["declared_column_count"]
        _require(bound is None or all(index < bound for index in population["columns_0based"]),
            "population_columns_conflict")
    components_present = context["components_version"] is not None
    quantities = [context["ordered_source_row_indices"], context["member_count"], context["site_count"]]
    _require(all(item is not None for item in quantities) if components_present else
        all(item is None for item in quantities), "components_presence_conflict")
    if components_present:
        _require(population is not None and context["ordered_source_row_indices"] == sorted(population["row_indices"]),
            "components_population_conflict")
        _quantity(context["member_count"], population=population["population_id"],
            unit="rows", method="selected_row_count", integer=True)
        _quantity(context["site_count"], population=population["population_id"],
            unit="columns", method="selected_column_count", integer=True)
    for row in value["native_rows"]:
        _require(metadata is not None and row["row_index"] < metadata["observed_row_count"]
            and row["member_label"] == _label(row["raw_header"]), "native_row_identity_conflict")
        f._location(row["source_location"], artifact=metadata["artifact"])
        _require(metadata["encoding"] != "ascii" or row["raw_header"].isascii(), "native_row_encoding_conflict")
        _require(metadata["encoding"] != "ascii" or row["sequence"].isascii(), "native_row_encoding_conflict")
        _require(metadata["completeness"] != "complete" or bool(row["member_label"]), "native_row_identity_conflict")
        if metadata["observed_column_count"] is not None:
            _require(len(row["sequence"]) == metadata["observed_column_count"], "native_row_dimension_conflict")
    associations = context["row_associations"]
    _require([row["output_row_index"] for row in associations["rows"]] ==
        ([] if metadata is None else list(range(metadata["observed_row_count"]))), "association_rows_conflict")
    _associations(associations, context["input"], value["native_rows"], full_rows=None,
        output_available=metadata is not None)
    for row in value["sites"]:
        _require(components_present, "components_presence_conflict")
        _site(row, context)
        for native in value["native_rows"]:
            if native["row_index"] == row["modal_first_source_row_index"]:
                column = row["column_0based"]
                _require(column < len(native["sequence"]) and native["sequence"][column] == row["modal_symbol"],
                    "site_modal_identity_conflict")
    row_available = None if metadata is None else list(range(metadata["observed_row_count"]))
    site_available = population["columns_0based"] if components_present else None
    for name, available, key, actual in (("native_rows", row_available, "row_indices",
            [row["row_index"] for row in value["native_rows"]]),
            ("sites", site_available, "columns_0based", [row["column_0based"] for row in value["sites"]])):
        selected = _view_indices(available, value["selection"][name], key)
        _require(actual == _page(selected, value["selection"][name]), "selected_order_conflict")
        _require(value["accounting"][name] == _accounting(available, selected, actual), "accounting_conflict")
    return value


def conservation_public_value(*, alignment, population_request, population, components,
        input_record, native_execution, associations, selection, issues):
    """Copy supplied native/scientific values; never parse, count or calculate."""
    selection = validate_conservation_selection(selection)
    input_record = None if input_record is None else _node(input_record, "Input")
    _input(input_record)
    native_execution = _node(native_execution, "NativeExecution")
    associations = _node(associations, "Associations")
    population = None if population is None else _node(population, "Population")
    alignment = None if alignment is None else f.validate_alignment_document(_copy(alignment))
    if alignment is not None:
        _require(alignment["format"] == "aligned_fasta", "alignment_format_invalid")
    bound = bind_conservation_population(population_request, alignment=alignment,
        evidence=[] if population is None else population["evidence"])
    _require(bound["population"] == population, "population_binding_conflict")
    if components is not None:
        _require(alignment is not None and population is not None, "components_population_conflict")
        components = c.validate_literal_site_conservation_components(_copy(components),
            alignment=alignment, population=population)
    all_rows = [] if alignment is None else alignment["rows"]
    _associations(associations, input_record, [], full_rows=all_rows, output_available=alignment is not None)
    row_available = None if alignment is None else list(range(len(all_rows)))
    site_available = None if components is None else [row["column_0based"] for row in components["sites"]]
    selected_rows = _view_indices(row_available, selection["native_rows"], "row_indices")
    selected_sites = _view_indices(site_available, selection["sites"], "columns_0based")
    native_rows = [deepcopy(all_rows[i]) for i in _page(selected_rows, selection["native_rows"])]
    by_column = {} if components is None else {row["column_0based"]: row for row in components["sites"]}
    sites = [deepcopy(by_column[i]) for i in _page(selected_sites, selection["sites"])]
    context = {"input": _copy(input_record), "native_execution": _copy(native_execution),
        "alignment": None if alignment is None else {key: deepcopy(alignment[key]) for key in _ALIGNMENT_KEYS},
        "population_request": _copy(population_request), "population_resolution": bound["resolution"],
        "population": _copy(population), "components_version": None if components is None else components["version"],
        "convention": c.LITERAL_CONSERVATION_CONVENTION, "threshold": deepcopy(_THRESHOLD), "display": deepcopy(_DISPLAY),
        "ordered_source_row_indices": None if components is None else components["ordered_source_row_indices"],
        "member_count": None if components is None else components["member_count"],
        "site_count": None if components is None else components["site_count"],
        "row_associations": _copy(associations), "issues": _copy(issues)}
    return validate_conservation_public_value({"version": PACKET_VERSION, "selection": selection,
        "context": context, "native_rows": native_rows, "sites": sites,
        "accounting": {"native_rows": _accounting(row_available, selected_rows, native_rows),
            "sites": _accounting(site_available, selected_sites, sites)}})


def validate_conservation_public_value(value):
    return _validate_value(_validated(value, "Value"))


def project_conservation_return(value, *, source_ref):
    value = validate_conservation_public_value(value)
    value["source_ref"] = source_ref
    return validate_conservation_return(value)


def validate_conservation_return(value):
    value = _validated(value, "Return")
    _require(re.fullmatch(_SOURCE, value["source_ref"]) is not None, "return_source_invalid")
    _validate_value({key: item for key, item in value.items() if key != "source_ref"})
    return value


def conservation_fact_sources():
    schema = conservation_result_schema("Return")
    report = {"type": "array", "items": _ref("Return"), "$defs": schema["$defs"], "x-source": FACT_SOURCE}
    identity = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    report["$id"] = "urn:protein-conservation-facts:" + identity
    return {FACT_SOURCE: {"type": "array", "report_schema": report}}


__all__ = ["TOOL", "SOURCE_VERSION", "PACKET_VERSION", "SELECTION_VERSION", "FACT_SOURCE",
    "validate_conservation_arguments", "validate_conservation_selection", "bind_conservation_population",
    "conservation_public_value", "validate_conservation_public_value", "project_conservation_return",
    "validate_conservation_return", "conservation_result_schema", "conservation_fact_sources"]
