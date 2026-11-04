"""Pure retained GEO SOFT parsing; no download URL is established here.

All table cells remain native strings. Entity/table order, duplicate records,
metadata and probe/platform relationships remain inspectable without pivots or
an inferred expression scale, sample grouping, organism or target annotation.
"""
from copy import deepcopy
import hashlib
import json
import re
import zlib

from jsonschema import Draft202012Validator, ValidationError, validators


VERSION = "geo_retained_soft_result_v1"
MAX_DECODED_BYTES = 8 * 1024 * 1024
_SOURCE_RE = re.compile(r"source_[a-f0-9]{24,64}\Z")
_ARTIFACT_RE = re.compile(r"artifact_[a-f0-9]{64}\Z")


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _array(items):
    return {"type": "array", "items": items}


def _nullable(node):
    return {"anyOf": [node, {"type": "null"}]}


_TEXT = {"type": "string"}
_INT = {"type": "integer", "minimum": 0}
_BOOL = {"type": "boolean"}
_LINE = {"line_number": {"type": "integer", "minimum": 1}, "byte_start": _INT, "byte_end": _INT}
_ATTRIBUTE = _object({**_LINE, "name": _TEXT, "value": _TEXT})
_ROW = _object({**_LINE, "cells": _array(_TEXT)})
_TABLE = _object({"ordinal": _INT, "begin_line": _INT, "end_line": _nullable(_INT),
    "begin_marker": _TEXT, "end_marker": _nullable(_TEXT),
    "header": _nullable(_ROW), "rows": _array(_ROW), "probe_identifier_column": _nullable(_INT),
    "native_closed": _BOOL})
_ENTITY = _object({"ordinal": _INT, "entity_type": _TEXT, "identifier": _TEXT, **_LINE,
    "attributes": _array(_ATTRIBUTE), "column_descriptions": _array(_ATTRIBUTE),
    "tables": _array(_TABLE), "unparsed_lines": _array(_object({**_LINE, "text": _TEXT}))})
_RELATION = _object({"from_entity_ordinal": _INT, "from_identifier": _TEXT,
    "native_relation": _TEXT, "to_entity_type": _TEXT, "to_identifier": _TEXT,
    "target_entity_ordinals": _array(_INT), "native_locator": _TEXT})
_ISSUE = _object({"code": _TEXT, "native_locator": _nullable(_TEXT)})
_RESULT = _object({"version": {"const": VERSION},
    "source_ref": {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$", "format": "reference", "x-reference-namespace": "source"},
    "raw_artifact_ref": {"type": "string", "pattern": "^artifact_[a-f0-9]{64}$", "format": "reference", "x-reference-namespace": "artifact"},
    "text_encoding": {"const": "utf-8"}, "byte_coordinate_system": {"const": "decoded_utf8_bytes"},
    "capture": _object({"retained_raw_bytes": _INT, "body_complete": _nullable(_BOOL)}),
    "decoding": _object({"content_encoding": {"enum": ["identity", "gzip"]},
        "decoded_byte_limit": {"type": "integer", "minimum": 1, "maximum": MAX_DECODED_BYTES},
        "retained_decoded_bytes": _INT, "decoded_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}, "decoded_complete": _BOOL,
        "decoded_limit_reached": _BOOL, "observed_decoded_bytes_lower_bound": _INT,
        "total_decoded_bytes": _nullable(_INT), "completed_gzip_members": _nullable(_INT),
        "error": _nullable(_TEXT)}),
    "native_text": _nullable(_TEXT), "parse_state": {"enum": ["soft", "unavailable"]},
    "representation_state": {"enum": ["complete", "partial", "unavailable"]},
    "native_parse_complete": _BOOL, "matching_population_coverage": {"const": "unknown"},
    "entity_count": _nullable(_INT), "entities": _array(_ENTITY), "relations": _array(_RELATION),
    "unassigned_lines": _array(_object({**_LINE, "text": _TEXT})), "issues": _array(_ISSUE)})
_STRICT = validators.extend(Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _, value: type(value) is int))


def _require(condition, code):
    if not condition:
        raise ValueError("geo_soft_" + code)


def geo_result_schema():
    return deepcopy(_RESULT)


def _issue(code, locator=None):
    return dict(code=code, native_locator=locator)


def _decode_content(raw, content_encoding, limit):
    if content_encoding == "identity":
        truncated = len(raw) > limit
        return raw[:limit], dict(decoded_complete=not truncated, decoded_limit_reached=truncated,
            observed_decoded_bytes_lower_bound=len(raw), total_decoded_bytes=None if truncated else len(raw),
            completed_gzip_members=None, error=None)
    decoded, remaining, members = bytearray(), raw, 0
    inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
    error = None
    complete = False
    while remaining:
        block, remaining = remaining[:65536], remaining[65536:]
        try:
            decoded.extend(inflater.decompress(block, limit + 1 - len(decoded)))
        except zlib.error:
            error = "invalid_gzip"
            break
        if len(decoded) > limit:
            return bytes(decoded[:limit]), dict(decoded_complete=False, decoded_limit_reached=True,
                observed_decoded_bytes_lower_bound=len(decoded), total_decoded_bytes=None,
                completed_gzip_members=members, error=None)
        remaining = (inflater.unused_data if inflater.eof else inflater.unconsumed_tail) + remaining
        if inflater.eof:
            members += 1
            if not remaining:
                complete = True
                break
            inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
    if not complete and error is None:
        error = "incomplete_gzip"
    return bytes(decoded), dict(decoded_complete=complete, decoded_limit_reached=False,
        observed_decoded_bytes_lower_bound=len(decoded), total_decoded_bytes=len(decoded) if complete else None,
        completed_gzip_members=members, error=error)


def _lines(text):
    offset = 0
    complete_lines = (match.group() for match in re.finditer(r"[^\r\n]*(?:\r\n|\r|\n|$)", text) if match.start() != match.end())
    for number, complete_line in enumerate(complete_lines, 1):
        ending = "\r\n" if complete_line.endswith("\r\n") else complete_line[-1:] if complete_line.endswith(("\n", "\r")) else ""
        line = complete_line[:-len(ending)] if ending else complete_line
        end = offset + len(complete_line.encode("utf-8"))
        yield line, dict(line_number=number, byte_start=offset, byte_end=end)
        offset = end


def _entry(line):
    name, separator, value = line.partition("=")
    return (name.strip(), value) if separator else (line, None)


def _native_soft(text):
    entities, unassigned, issues = [], [], []
    entity, table = None, None
    for line, location in _lines(text):
        if line.startswith("^"):
            if table is not None:
                issues.append(_issue("native_table_not_closed", "/entities/" + str(entity["ordinal"]) + "/tables/" + str(table["ordinal"])))
                table = None
            kind, value = _entry(line[1:])
            if value is None:
                issues.append(_issue("native_entity_marker_invalid", "/native_text/line/" + str(location["line_number"])))
                unassigned.append(dict(location, text=line))
                entity = None
                continue
            entity = dict(ordinal=len(entities), entity_type=kind, identifier=value.strip(), **location,
                attributes=[], column_descriptions=[], tables=[], unparsed_lines=[])
            entities.append(entity)
            continue
        if entity is None:
            unassigned.append(dict(location, text=line))
            continue
        if line.startswith("!") and "=" not in line and line.lower().endswith("_table_begin"):
            if table is not None:
                issues.append(_issue("native_nested_table_begin", "/entities/" + str(entity["ordinal"])))
            table = dict(ordinal=len(entity["tables"]), begin_line=location["line_number"], end_line=None,
                begin_marker=line, end_marker=None,
                header=None, rows=[], probe_identifier_column=None, native_closed=False)
            entity["tables"].append(table)
            if line.lower() != "!" + entity["entity_type"].lower() + "_table_begin":
                issues.append(_issue("native_table_entity_context_conflict", "/entities/" + str(entity["ordinal"]) + "/tables/" + str(table["ordinal"])))
            continue
        if line.startswith("!") and "=" not in line and line.lower().endswith("_table_end"):
            if table is None:
                issues.append(_issue("native_table_end_without_begin", "/native_text/line/" + str(location["line_number"])))
                entity["unparsed_lines"].append(dict(location, text=line))
            else:
                if table["begin_marker"].lower()[:-len("_table_begin")] != line.lower()[:-len("_table_end")]:
                    issues.append(_issue("native_table_marker_conflict", "/native_text/line/" + str(location["line_number"])))
                table.update(end_line=location["line_number"], end_marker=line, native_closed=True)
                table = None
            continue
        if line.startswith(("!", "#")):
            name, value = _entry(line[1:])
            if value is None:
                entity["unparsed_lines"].append(dict(location, text=line))
                issues.append(_issue("native_metadata_line_invalid", "/native_text/line/" + str(location["line_number"])))
            else:
                entity["attributes" if line.startswith("!") else "column_descriptions"].append(dict(location, name=name, value=value))
            continue
        if table is None or not line:
            entity["unparsed_lines"].append(dict(location, text=line))
            continue
        row = dict(location, cells=line.split("\t"))
        if table["header"] is None:
            table["header"] = row
            native_context = table["begin_marker"].lower() == "!" + entity["entity_type"].lower() + "_table_begin"
            column = ("ID_REF" if entity["entity_type"] == "SAMPLE" else "ID" if entity["entity_type"] == "PLATFORM" else None) if native_context else None
            matches = [index for index, value in enumerate(row["cells"]) if value == column] if column else []
            if len(matches) == 1:
                table["probe_identifier_column"] = matches[0]
            elif len(matches) > 1:
                issues.append(_issue("native_probe_column_ambiguous", "/entities/"+str(entity["ordinal"])+"/tables/"+str(table["ordinal"])))
        else:
            table["rows"].append(row)
            if len(row["cells"]) != len(table["header"]["cells"]):
                issues.append(_issue("native_row_width_conflict", "/entities/"+str(entity["ordinal"])+"/tables/"+str(table["ordinal"])+"/rows/"+str(len(table["rows"])-1)))
    if table is not None:
        issues.append(_issue("native_table_not_closed", "/entities/" + str(entity["ordinal"]) + "/tables/" + str(table["ordinal"])))
    identities = {}
    for item in entities:
        identities.setdefault((item["entity_type"], item["identifier"]), []).append(item["ordinal"])
    for item in entities:
        if len(identities[(item["entity_type"], item["identifier"])]) > 1:
            issues.append(_issue("native_entity_identity_repeated", "/entities/"+str(item["ordinal"])))
        for index, selected in enumerate(item["tables"]):
            if selected["header"] is None:
                issues.append(_issue("native_table_header_missing", "/entities/"+str(item["ordinal"])+"/tables/"+str(index)))
    relations = []
    relationships = {("SERIES", "series_sample_id"): "SAMPLE", ("SERIES", "series_platform_id"): "PLATFORM",
        ("SAMPLE", "sample_platform_id"): "PLATFORM", ("SAMPLE", "sample_series_id"): "SERIES"}
    for item in entities:
        for index, attribute in enumerate(item["attributes"]):
            target = relationships.get((item["entity_type"], attribute["name"].lower()))
            if target is not None:
                identifier = attribute["value"].strip()
                relations.append(dict(from_entity_ordinal=item["ordinal"], from_identifier=item["identifier"],
                    native_relation=attribute["name"], to_entity_type=target, to_identifier=identifier,
                    target_entity_ordinals=list(identities.get((target, identifier), [])),
                    native_locator="/entities/"+str(item["ordinal"])+"/attributes/"+str(index)))
    return entities, relations, unassigned, issues


def parse_geo_soft(raw, *, source_ref, artifact_ref, content_encoding, body_complete, max_decoded_bytes):
    _require(type(raw) is bytes and type(source_ref) is str and _SOURCE_RE.fullmatch(source_ref) is not None
        and type(artifact_ref) is str and _ARTIFACT_RE.fullmatch(artifact_ref) is not None, "input_invalid")
    _require(artifact_ref == "artifact_" + hashlib.sha256(raw).hexdigest(), "artifact_identity_conflict")
    _require(type(content_encoding) is str and content_encoding in {"identity", "gzip"}, "content_encoding_invalid")
    _require(body_complete is None or type(body_complete) is bool, "capture_state_invalid")
    _require(type(max_decoded_bytes) is int and 1 <= max_decoded_bytes <= MAX_DECODED_BYTES, "decoded_limit_invalid")
    decoded, state = _decode_content(raw, content_encoding, max_decoded_bytes)
    issues = []
    if body_complete is not True: issues.append(_issue("capture_not_complete"))
    if state["decoded_limit_reached"]: issues.append(_issue("decoded_byte_limit_reached"))
    if state["error"] is not None: issues.append(_issue(state["error"]))
    text, entities, relations, unassigned = None, [], [], []
    try:
        text = decoded.decode("utf-8")
    except UnicodeError:
        issues.append(_issue("invalid_native_utf8"))
    if text is not None:
        entities, relations, unassigned, parsing = _native_soft(text)
        issues += parsing
        if not entities: issues.append(_issue("native_entities_unavailable"))
    parsed = bool(entities)
    parse_complete = parsed and state["decoded_complete"] and not any(row["code"].startswith("native_") for row in issues)
    result = dict(version=VERSION, source_ref=source_ref, raw_artifact_ref=artifact_ref, text_encoding="utf-8",
        byte_coordinate_system="decoded_utf8_bytes",
        capture=dict(retained_raw_bytes=len(raw), body_complete=body_complete),
        decoding=dict(content_encoding=content_encoding, decoded_byte_limit=max_decoded_bytes,
            retained_decoded_bytes=len(decoded), decoded_sha256=hashlib.sha256(decoded).hexdigest(), **state),
        native_text=text, parse_state="soft" if parsed else "unavailable",
        representation_state="unavailable" if not parsed else "partial" if issues else "complete",
        native_parse_complete=parse_complete, matching_population_coverage="unknown",
        entity_count=len(entities) if parsed else None, entities=entities, relations=relations,
        unassigned_lines=unassigned, issues=issues)
    return validate_geo_result(result)


def validate_geo_result(value):
    try:
        value = deepcopy(value)
        json.dumps(value, allow_nan=False)
        _STRICT(_RESULT).validate(value)
    except (ValueError, TypeError, OverflowError, RecursionError, ValidationError) as error:
        raise ValueError("geo_soft_contract_invalid") from error
    _require(_SOURCE_RE.fullmatch(value["source_ref"]) is not None and _ARTIFACT_RE.fullmatch(value["raw_artifact_ref"]) is not None, "references_invalid")
    state = value["decoding"]
    _require(re.fullmatch(r"[a-f0-9]{64}", state["decoded_sha256"], re.ASCII) is not None, "decoded_identity_invalid")
    _require(state["retained_decoded_bytes"] <= state["decoded_byte_limit"]
        and state["observed_decoded_bytes_lower_bound"] >= state["retained_decoded_bytes"], "decoded_size_conflict")
    _require(not state["decoded_complete"] or not state["decoded_limit_reached"] and state["error"] is None
        and state["total_decoded_bytes"] == state["retained_decoded_bytes"], "decoded_state_conflict")
    _require(state["decoded_complete"] or state["total_decoded_bytes"] is None
        and (state["decoded_limit_reached"] or state["error"] is not None), "decoded_state_conflict")
    if state["decoded_limit_reached"]:
        _require(not state["decoded_complete"] and state["retained_decoded_bytes"] == state["decoded_byte_limit"]
            and state["observed_decoded_bytes_lower_bound"] > state["decoded_byte_limit"], "decoded_state_conflict")
    if state["content_encoding"] == "identity":
        _require(state["completed_gzip_members"] is None and state["error"] is None
            and state["observed_decoded_bytes_lower_bound"] == value["capture"]["retained_raw_bytes"], "identity_capture_conflict")
        if state["decoded_complete"]:
            _require(value["capture"]["retained_raw_bytes"] == state["retained_decoded_bytes"]
                and value["raw_artifact_ref"] == "artifact_" + state["decoded_sha256"], "identity_capture_conflict")
    else:
        _require(type(state["completed_gzip_members"]) is int
            and (not state["decoded_complete"] or state["completed_gzip_members"] >= 1), "gzip_state_conflict")
    expected_issues = []
    if value["capture"]["body_complete"] is not True: expected_issues.append(_issue("capture_not_complete"))
    if state["decoded_limit_reached"]: expected_issues.append(_issue("decoded_byte_limit_reached"))
    if state["error"] is not None: expected_issues.append(_issue(state["error"]))
    if value["native_text"] is not None:
        raw = value["native_text"].encode("utf-8")
        _require(len(raw) == state["retained_decoded_bytes"] and hashlib.sha256(raw).hexdigest() == state["decoded_sha256"], "native_text_identity_conflict")
        entities, relations, unassigned, parsing = _native_soft(value["native_text"])
        _require(value["entities"] == entities and value["relations"] == relations and value["unassigned_lines"] == unassigned
            and all(issue in value["issues"] for issue in parsing), "native_document_conflict")
        expected_issues += parsing
        if not entities: expected_issues.append(_issue("native_entities_unavailable"))
    else:
        _require(not value["entities"] and not value["relations"] and not value["unassigned_lines"], "native_document_conflict")
        _require(state["retained_decoded_bytes"] > 0, "native_text_identity_conflict")
        expected_issues.append(_issue("invalid_native_utf8"))
    _require(value["issues"] == expected_issues, "native_issue_conflict")
    parsed = bool(value["entities"])
    _require(value["entity_count"] == (len(value["entities"]) if parsed else None)
        and (value["parse_state"] == "soft") == parsed
        and value["representation_state"] == ("unavailable" if not parsed else "partial" if value["issues"] else "complete"), "representation_conflict")
    _require(value["native_parse_complete"] == (parsed and state["decoded_complete"]
        and not any(row["code"].startswith("native_") for row in value["issues"])), "native_parse_state_conflict")
    return value


__all__ = ["VERSION", "MAX_DECODED_BYTES", "parse_geo_soft", "validate_geo_result", "geo_result_schema"]
