"""Pure, source-preserving readers for retained BV-BRC Data responses.

The public reader verifies the persisted v2 request and actual transport before
decoding. The private payload decoder also supports explicitly selected legacy
array/header evidence; it never upgrades that evidence into a v2 acquisition.
Complete raw bytes remain the source of unselected fields and invalid objects.
There is no acquisition, retry, pagination, Store access or scientific score.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import math
import re
from urllib.parse import quote, urlencode, urlsplit

from .acquisition import SourceSnapshot
from .bvbrc_data_fields import FIELD_CONTRACT_VERSION, FIELD_REGISTRY
from .bvbrc_data_query import validate_data_query
from .bvbrc_data_schema import json_digest, schema, validate

__all__ = (
    "DATA_SHEET_SCHEMA", "DATA_PARSE_RESULT_SCHEMA", "COLLECTION_ROWS_SCHEMA",
    "NUMERIC_TEXT_GRAMMARS", "parse_data_snapshot", "extract_collection_rows", "validate_data_sheet",
)

DATA_SHEET_SCHEMA = schema("DataSheet")
DATA_PARSE_RESULT_SCHEMA = schema("ParseResult")
COLLECTION_ROWS_SCHEMA = schema("CollectionRowsExtraction")
NUMERIC_TEXT_GRAMMARS = {
    "nonnegative_decimal_integer": {
        "pattern": r"^[0-9]+$", "numeric_type": "integer", "minimum": 0},
    "finite_nonnegative_decimal_scientific": {
        "pattern": r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$",
        "numeric_type": "number", "minimum": 0},
}
_GRAMMARS = deepcopy(NUMERIC_TEXT_GRAMMARS)
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_RANGE = re.compile(r"items\s+([0-9]+)-([0-9]+)/([0-9]+|\*)", re.I)
_WARNING = "bvbrc_schema_observed_variant"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _escape(value):
    return value.replace("~", "~0").replace("/", "~1")


def _issue(code, phase="field", *, row=None, field=None, path=None, http=None):
    return {"code": code, "phase": phase, "row_index": row, "field": field,
            "native_path": path, "http_status": http}


@dataclass(frozen=True)
class _Number:
    """An original JSON token, distinct from both strings and Python numbers."""
    text: str

    @property
    def integer(self):
        return not any(char in self.text for char in ".eE")

    def project(self):
        try:
            if self.integer:
                return int(self.text)
            number = float(self.text)
            if not math.isfinite(number) or number == 0 and Decimal(self.text) != 0:
                return None
            return number
        except (ValueError, OverflowError, InvalidOperation):
            return None


def _reject_constant(_value):
    raise ValueError("non_json_number")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _decode_json(content):
    return json.loads(content, parse_int=_Number, parse_float=_Number,
                      parse_constant=_reject_constant, object_pairs_hook=_unique_object)


def _atom(value):
    result = dict(kind="null", string_value=None, number_value=None,
                  boolean_value=None, number_lexeme=None)
    if isinstance(value, _Number):
        result.update(kind="number", number_value=value.project(), number_lexeme=value.text)
    elif type(value) is str:
        result.update(kind="string", string_value=value)
    elif type(value) is bool:
        result.update(kind="boolean", boolean_value=value)
    elif value is not None:
        raise ValueError("unsupported_native_atom")
    return result


def _matches_atom(atom, spec):
    kind = atom["kind"]
    native_type = spec["solr_type"]
    if native_type in ("int", "long"):
        return kind == "number" and _Number(atom["number_lexeme"]).integer
    if native_type == "float":
        return kind == "number"
    if native_type == "boolean":
        return kind == "boolean"
    return kind == "string"


def _native_cell(raw, *, field, spec, row_key, path, selected=True):
    cell = {"cell_key": row_key + "/field/" + _escape(field), "field": field,
            "native_path": path, "presence": "absent", "native_shape": "absent",
            "atoms": [], "status": "missing", "field_schema_status": "not_evaluated",
            "issue_codes": []}
    if not selected:
        cell.update(presence="unselected", status="unselected")
        return cell
    if type(raw) is not dict or field not in raw:
        return cell
    value = raw[field]
    if value is None:
        cell.update(presence="null", native_shape="null")
        return cell
    cell.update(presence="present", status="valid", field_schema_status="match")
    cell["native_shape"] = "array" if type(value) is list else "object" if type(value) is dict else "scalar"
    values = value if type(value) is list else [value]
    # Invalid complex arrays remain at their original raw path. The additive
    # contract forbids flattening them or inserting fabricated null atoms.
    if any(type(item) in (dict, list) for item in values):
        cell.update(status="invalid", field_schema_status="mismatch",
                    issue_codes=["bvbrc_invalid_native_field"])
        return cell
    cell["atoms"] = [_atom(item) for item in values]
    exception = ("finite_json_number" in spec["observed_variants"]
                 and isinstance(value, _Number))
    compatible = (exception or (spec["multi_valued"] == (type(value) is list)
                  and all(_matches_atom(atom, spec) for atom in cell["atoms"])))
    if not compatible:
        cell.update(status="invalid", field_schema_status="mismatch")
        cell["issue_codes"].append("bvbrc_invalid_native_field")
    if exception:
        cell["field_schema_status"] = "observed_exception"
        cell["issue_codes"].append(_WARNING)
    if any(atom["kind"] == "number" and atom["number_value"] is None for atom in cell["atoms"]):
        if compatible:
            cell["status"] = "unrepresentable"
        cell["issue_codes"].append("bvbrc_unrepresentable_numeric_value")
    return cell


def _numeric_cell(cell, spec):
    result = {key: cell[key] for key in ("cell_key", "field", "native_path")}
    result.update(value=None, status="missing", reason="native_field_absent",
                  quantity_kind=spec["quantity_kind"], unit_code=spec["unit_code"],
                  unit_basis=spec["unit_basis"], unit_cell_keys=[], denominator_value=None,
                  denominator_basis="unknown", origin="unavailable", uncertainty_cell_keys=[],
                  issue_codes=list(cell["issue_codes"]))
    if cell["presence"] != "present":
        result["reason"] = {"absent": "native_field_absent", "null": "native_null",
                            "unselected": "not_selected"}[cell["presence"]]
        if cell["presence"] == "unselected":
            result["status"] = "unselected"
        return result
    if cell["status"] in ("invalid", "unrepresentable"):
        result.update(status="invalid", reason="unrepresentable_numeric_value"
                      if cell["status"] == "unrepresentable" else "native_value_invalid")
        return result
    if (cell["native_shape"] == "scalar" and len(cell["atoms"]) == 1
            and cell["atoms"][0]["kind"] == "number"):
        result.update(value=cell["atoms"][0]["number_value"], status="reported",
                      reason=None, origin="native_reported")
        return result
    grammar_name = spec["numeric_text_grammar"]
    if grammar_name is None:
        result.update(status="incompatible", reason="native_format_unverified")
        return result
    text = cell["atoms"][0]["string_value"] if cell["native_shape"] == "scalar" else None
    grammar = _GRAMMARS[grammar_name]
    if text is None or re.fullmatch(grammar["pattern"], text) is None:
        result.update(status="invalid", reason="native_value_invalid")
    else:
        try:
            value = int(text) if grammar["numeric_type"] == "integer" else float(text)
            decimal = Decimal(text)
            if decimal < 0:
                result.update(status="invalid", reason="native_value_invalid")
            elif (type(value) is float and (not math.isfinite(value)
                                           or value == 0 and decimal != 0)):
                result.update(status="invalid", reason="unrepresentable_numeric_value")
            else:
                result.update(value=value, status="parsed_numeric_text", reason=None,
                              origin="derived_from_native_text")
        except (ValueError, OverflowError, InvalidOperation):
            result.update(status="invalid", reason="unrepresentable_numeric_value")
    if result["status"] == "invalid":
        result["issue_codes"].append("bvbrc_unrepresentable_numeric_value"
                                     if result["reason"] == "unrepresentable_numeric_value"
                                     else "bvbrc_invalid_native_field")
    return result


def _row(raw, *, index, path, native_sha256, collection, fields):
    registry = FIELD_REGISTRY[collection]
    key = native_sha256 + "/row/" + str(index)
    cells, numbers, issues = [], [], []
    for field in fields:
        spec = registry["fields"][field]
        cell = _native_cell(raw, field=field, spec=spec, row_key=key,
                            path=path + "/" + _escape(field))
        cells.append(cell)
        numeric = _numeric_cell(cell, spec) if spec["numeric_projection"] else None
        if numeric is not None:
            numbers.append(numeric)
        codes = list(dict.fromkeys(cell["issue_codes"] + (numeric["issue_codes"] if numeric else [])))
        issues.extend(_issue(code, row=index, field=field, path=cell["native_path"]) for code in codes)
    native_id = raw.get(registry["unique_key"]) if type(raw) is dict else None
    if type(native_id) is not str or not native_id:
        native_id = None
        issues.append(_issue("bvbrc_missing_native_identity", row=index,
                             field=registry["unique_key"], path=path + "/" + registry["unique_key"]))
    if type(raw) is not dict:
        issues.append(_issue("bvbrc_invalid_native_field", row=index, path=path))
    invalid = any(issue["code"] != _WARNING for issue in issues)
    return {"row_key": key, "row_index": index, "native_path": path, "native_id": native_id,
            "status": "invalid" if type(raw) is not dict else "partial" if invalid else "valid",
            "cells": cells, "numerical_cells": numbers, "issues": issues}


def _header_items(transport):
    """Retain duplicate header occurrences; prefer the actual ordered capture."""
    source = transport.get("response", transport)
    items = source.get("header_items", source.get("headers", []))
    if isinstance(items, dict):
        items = list(items.items())
    result = []
    for item in items:
        name, value = (item.get("name"), item.get("value")) if type(item) is dict else item
        if type(name) is not str or type(value) is not str:
            raise ValueError("invalid_transport_headers")
        result.append({"name": name, "value": value})
    return result


def _header_values(headers, name):
    return [item["value"] for item in headers if item["name"].lower() == name]


def _transport_facts(snapshot):
    source = snapshot.transport.get("response", snapshot.transport)
    status = source.get("status")
    status = status if type(status) is int else None
    headers = _header_items(snapshot.transport)
    complete = source.get("body_complete") is True and not source.get("body_capture_error")
    lengths = _header_values(headers, "content-length")
    encoding = _header_values(headers, "content-encoding")
    if lengths and not encoding:
        complete = complete and all(value.isascii() and value.isdigit()
                                    and int(value) == len(snapshot.content) for value in lengths)
    return {"http_status": status, "body_complete": complete, "headers": headers,
            "failure_code": source.get("failure_code", snapshot.transport.get("failure_code")),
            "automatic_redirects": False, "native_query_time_ms": None}


def _failed(snapshot, failures):
    return validate("ParseResult", {"version": "bvbrc_data_parse_result_v1", "status": "failed",
                    "sheet": None, "failures": failures, "retained_native_sha256": snapshot.sha256})


def _prepared(prepared):
    """Check persisted relationships, without regenerating a native query.

    The host supplies the immutable actual prepared intent. Its custody proves
    the provenance of the frozen q literal; this parser neither recomputes that
    literal nor claims to establish host custody from a dictionary alone.
    """
    result = validate("PreparedQuery", prepared)
    original = validate_data_query(result["original_request"])
    effective, population, native = (result[key] for key in
                                    ("effective_request", "query_population", "native_request"))
    mode, collection, selector = original["mode"], original["collection"], result["page_selector"]
    unique = FIELD_REGISTRY[collection]["unique_key"]
    fields, sort, offset, limit = [], [], 0, 0
    field_selection = dict(requested_fields=original.get("fields"), defaulted_fields=[], custody_added_fields=[])
    sort_selection = dict(requested_sort=original.get("sort"), defaulted_sort=[], tie_breaker_added=None)
    if mode == "page":
        fields = list(original.get("fields", [unique]))
        if "fields" not in original:
            field_selection["defaulted_fields"] = [unique]
        if unique not in fields:
            fields.append(unique)
            field_selection["custody_added_fields"] = [unique]
        tie_breaker = {"field": unique, "direction": "asc"}
        sort = deepcopy(original.get("sort") or [tie_breaker])
        if not original.get("sort"):
            sort_selection["defaulted_sort"] = deepcopy(sort)
        elif unique not in {item["field"] for item in sort}:
            sort.append(tie_breaker)
            sort_selection["tie_breaker_added"] = tie_breaker
        offset, limit = original.get("offset", 0), original.get("limit", 25)
        if selector is not None:
            offset, limit = selector["offset"], selector["limit"]
    elif selector is not None:
        raise ValueError("bvbrc_response_request_mismatch")
    expected_effective = dict(version="bvbrc_data_effective_query_v2", collection=collection, mode=mode,
                              filters=original["filters"], fields=fields, sort=sort,
                              offset=offset, limit=limit, facet=original.get("facet"))
    if (_canonical(effective) != _canonical(expected_effective)
            or _canonical(result["field_selection"]) != _canonical(field_selection)
            or _canonical(result["sort_selection"]) != _canonical(sort_selection)
            or population["collection"] != collection
            or _canonical(population["filters"]) != _canonical(original["filters"])
            or population["population_key"] != json_digest({key: value for key, value in population.items() if key != "population_key"})):
        raise ValueError("bvbrc_response_request_mismatch")
    base = population["base_url"]
    parsed = urlsplit(base)
    if (parsed.scheme not in ("http", "https") or not parsed.netloc
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or base != base.rstrip("/")):
        raise ValueError("bvbrc_response_request_mismatch")
    parameters = native["query_parameters"]
    if not parameters or parameters[0]["name"] != "q" or not parameters[0]["value"]:
        raise ValueError("bvbrc_response_request_mismatch")
    expected_parameters = [("rows", str(limit)), ("start", str(offset))]
    if mode == "page":
        expected_parameters += [("fl", ",".join(fields)),
                                ("sort", ",".join(item["field"] + " " + item["direction"] for item in sort))]
    elif mode == "facet":
        facet = effective["facet"]
        expected_parameters += [("facet", "true"), ("facet.field", facet["field"]),
            ("facet.limit", str(facet["limit"])), ("facet.offset", str(facet["offset"])),
            ("facet.mincount", str(facet["min_count"])),
            ("facet.missing", "true" if facet["include_missing"] else "false"), ("facet.sort", facet["sort"])]
    if [(item["name"], item["value"]) for item in parameters[1:]] != expected_parameters:
        raise ValueError("bvbrc_response_request_mismatch")
    persisted_pairs = [(item["name"], item["value"]) for item in parameters]
    expected_url = base + "/" + collection + "/?" + urlencode(persisted_pairs, quote_via=quote, safe="")
    expected_headers = [{"name": "User-Agent", "value": "gene-annotation-episode/0.2"},
                        {"name": "Accept", "value": "application/solr+json"},
                        {"name": "Content-Type", "value": "application/solrquery+x-www-form-urlencoded"}]
    if native["url"] != expected_url or native["headers"] != expected_headers:
        raise ValueError("bvbrc_response_request_mismatch")
    return result


def _request_matches(snapshot, prepared):
    native = prepared["native_request"]
    actual = snapshot.transport.get("request", {})
    if (snapshot.url != native["url"] or actual.get("url") != native["url"]
            or actual.get("method") != native["method"] or actual.get("body") is not None
            or snapshot.transport.get("effective_url") != native["url"]
            or snapshot.transport.get("automatic_redirects") is not False):
        return False
    try:
        request = validate("EffectiveQuery", snapshot.request)
        if _canonical(request) != _canonical(prepared["effective_request"]):
            return False
        actual_headers = _header_items({"headers": actual.get("headers", [])})
        for item in native["headers"]:
            if _header_values(actual_headers, item["name"].lower()) != [item["value"]]:
                return False
        if any(item["name"].lower() in ("authorization", "proxy-authorization", "cookie")
               for item in actual_headers):
            return False
    except (TypeError, ValueError, KeyError):
        return False
    return True


def parse_data_snapshot(snapshot: SourceSnapshot, *, prepared: dict) -> dict:
    """Verify exact persisted v2 request/transport and populate a closed sheet.

    Invalid native output returns structured failures, with valid independent
    fields retained where possible. Invalid Python inputs are not coerced.
    Body completeness requires an explicit successful capture fact, never HTTP
    status alone. Validation checks the persisted relationships and actual
    transport without invoking the compiler or rebuilding the frozen q literal.
    """
    if not isinstance(snapshot, SourceSnapshot) or type(snapshot.content) is not bytes:
        raise ValueError("bvbrc_invalid_snapshot")
    if snapshot.service != "bvbrc_data":
        return _failed(snapshot, [_issue("bvbrc_response_service_mismatch", "transport")])
    try:
        prepared = _prepared(prepared)
        matches = _request_matches(snapshot, prepared)
    except (ValueError, TypeError, KeyError):
        matches = False
    if not matches:
        return _failed(snapshot, [_issue("bvbrc_response_request_mismatch", "transport")])
    if snapshot.media_type.split(";", 1)[0].strip().lower() != "application/solr+json":
        return _failed(snapshot, [_issue("bvbrc_unsupported_media_type", "format")])
    return _decode_native_payload(snapshot, prepared=prepared, qualified_request=True)


def _decode_native_payload(snapshot, *, prepared, qualified_request=False):
    """Explicit native-format decoder; legacy fixture use remains unqualified.

    ``prepared`` supplies explicit selected field/population meanings. Unless
    called after the public request check, request_matches=False remains in the
    sheet and query count is unavailable for v2 claims. No saved legacy receipt
    is modified by this offline decoder.
    """
    prepared = validate("PreparedQuery", prepared)
    effective = prepared["effective_request"]
    collection, mode = effective["collection"], effective["mode"]
    fields = effective["fields"]
    if any(field not in FIELD_REGISTRY[collection]["fields"] for field in fields):
        raise ValueError("bvbrc_unknown_field")
    try:
        transport = _transport_facts(snapshot)
    except (TypeError, ValueError, KeyError):
        return _failed(snapshot, [_issue("bvbrc_response_request_mismatch", "transport")])
    http_status = transport["http_status"]
    if http_status is None or not 200 <= http_status < 300:
        return _failed(snapshot, [_issue("bvbrc_provider_http_error", "transport", http=http_status)])
    issues = []
    if not qualified_request:
        issues.append(_issue("bvbrc_response_request_mismatch", "transport"))
    if not transport["body_complete"]:
        issues.append(_issue("bvbrc_response_body_incomplete", "transport"))
    media = snapshot.media_type.split(";", 1)[0].strip().lower()
    if media not in ("application/json", "application/solr+json"):
        return _failed(snapshot, issues + [_issue("bvbrc_unsupported_media_type", "format")])
    try:
        payload = _decode_json(snapshot.content)
    except (ValueError, UnicodeError, RecursionError):
        return _failed(snapshot, issues + [_issue("bvbrc_invalid_json_response", "format")])
    is_solr = media == "application/solr+json"
    profile = "solr_json_envelope_v1" if is_solr else "json_array_with_headers_v1"
    if (is_solr and (type(payload) is not dict or type(payload.get("response")) is not dict
                    or type(payload["response"].get("docs")) is not list)):
        code = "bvbrc_native_error" if type(payload) is dict and "error" in payload else "bvbrc_expected_solr_response"
        return _failed(snapshot, issues + [_issue(code, "format", path="/response")])
    if not is_solr and type(payload) is not list:
        return _failed(snapshot, issues + [_issue("bvbrc_expected_native_row_array", "format")])
    docs = payload["response"]["docs"] if is_solr else payload
    rows = [_row(raw, index=index, path=("/response/docs/" if is_solr else "/") + str(index),
                 native_sha256=snapshot.sha256, collection=collection, fields=fields)
            for index, raw in enumerate(docs)]
    for row in rows:
        issues.extend(row["issues"])
    population_issues, format_issues = [], []
    start, total, exact = None, None, None
    compiled = next((item["value"] for item in prepared["native_request"]["query_parameters"]
                     if item["name"] == "q"), None)
    echoed, filter_queries, partial, native_error = None, [], None, False
    location = None

    def population_issue(path, code="bvbrc_population_metadata_conflict"):
        population_issues.append(_issue(code, "population", path=path))

    def integer(value, path):
        if isinstance(value, _Number) and value.integer:
            projected = value.project()
            if projected is not None and projected >= 0:
                return projected
        population_issue(path, "bvbrc_invalid_native_field")
        return None

    if is_solr:
        response = payload["response"]
        start = integer(response.get("start"), "/response/start")
        total = integer(response.get("numFound"), "/response/numFound")
        location = "/response/numFound"
        if "numFoundExact" in response:
            if type(response["numFoundExact"]) is bool:
                exact = response["numFoundExact"]
            else:
                population_issue("/response/numFoundExact", "bvbrc_invalid_native_field")
        header = payload.get("responseHeader", {})
        if type(header) is not dict:
            format_issues.append(_issue("bvbrc_expected_solr_response", "format", path="/responseHeader"))
            header = {}
        if "error" in payload or "status" in header and (
                not isinstance(header["status"], _Number) or not header["status"].integer
                or header["status"].project() != 0):
            native_error = True
            format_issues.append(_issue("bvbrc_native_error", "format", path="/error" if "error" in payload else "/responseHeader/status"))
        if "QTime" in header:
            qtime = header["QTime"].project() if isinstance(header["QTime"], _Number) else None
            if qtime is not None and qtime >= 0:
                transport["native_query_time_ms"] = qtime
            else:
                format_issues.append(_issue("bvbrc_invalid_native_field", "format", path="/responseHeader/QTime"))
        for source, path in ((header, "/responseHeader"), (response, "/response"), (payload, "")):
            if "partialResults" in source:
                value = source["partialResults"]
                if type(value) is bool:
                    partial = (partial is True or value)
                else:
                    partial = True
                    format_issues.append(_issue("bvbrc_invalid_native_field", "format", path=path + "/partialResults"))
                if partial:
                    format_issues.append(_issue("bvbrc_native_partial_results", "format", path=path + "/partialResults"))
        params = header.get("params", {})
        if type(params) is not dict:
            population_issue("/responseHeader/params")
            params = {}
        if "q" in params:
            if type(params["q"]) is str:
                echoed = params["q"]
            if echoed != compiled:
                population_issue("/responseHeader/params/q")
        if "fq" in params:
            fq = params["fq"] if type(params["fq"]) is list else [params["fq"]]
            if all(type(value) is str for value in fq):
                filter_queries = fq
            if filter_queries != ["public:true"]:
                population_issue("/responseHeader/params/fq")
        for item in prepared["native_request"]["query_parameters"]:
            name = item["name"]
            if name in params and params[name] != item["value"]:
                population_issue("/responseHeader/params/" + _escape(name))
    ranges = _header_values(transport["headers"], "content-range")
    native_range = ranges[0] if ranges else None
    if any(value != native_range for value in ranges):
        population_issue("/headers/Content-Range")
    if native_range is not None:
        match = _RANGE.fullmatch(native_range)
        if match is None:
            population_issue("/headers/Content-Range")
        else:
            range_start, range_end = int(match[1]), int(match[2])
            range_total = int(match[3]) if match[3] != "*" else None
            if range_end != range_start + len(docs):
                population_issue("/headers/Content-Range")
            if start is not None and start != range_start or total is not None and range_total is not None and total != range_total:
                population_issue("/headers/Content-Range")
            if not is_solr:
                start, total, location = range_start, range_total, "/headers/Content-Range"
    if start is not None and start != effective["offset"]:
        population_issue("/response/start" if is_solr else "/headers/Content-Range")
    if docs and total is not None and start is not None and start + len(docs) > total:
        population_issue(location)
    if qualified_request and len(docs) > effective["limit"]:
        population_issue("/response/docs")
    content_types = _header_values(transport["headers"], "content-type")
    if any(value.split(";", 1)[0].strip().lower() != media for value in content_types):
        format_issues.append(_issue("bvbrc_unsupported_media_type", "format", path="/headers/Content-Type"))
    exactness = ("unknown" if total is None else "exact" if exact is True else
                 "inexact" if exact is False else "provider_reported")
    population_key = prepared["query_population"]["population_key"]
    population = {"population_key": population_key, "compiled_query": compiled,
                  "echoed_query": echoed, "echoed_filter_queries": filter_queries,
                  "reported_total": total, "native_num_found_exact": exact,
                  "exactness": exactness, "native_location": location}
    issues.extend(format_issues + population_issues)
    count_reason = ("incompatible_input" if not qualified_request else
                    "transport_incomplete" if not transport["body_complete"] else
                    "native_partial_results" if partial else
                    "native_value_invalid" if native_error or format_issues else
                    "population_conflict" if any(issue["code"] == "bvbrc_population_metadata_conflict" for issue in population_issues) else
                    "native_value_invalid" if population_issues else
                    "unknown_denominator" if total is None else None)
    count = {"population_key": population_key, "reported_value": total,
             "exactness": exactness, "availability": "available" if count_reason is None else "unavailable",
             "reason": count_reason, "native_location": location}
    response_complete = transport["body_complete"] and not format_issues and not population_issues and partial is not True
    valid_count = sum(row["status"] == "valid" for row in rows)
    page = {"mode": mode, "requested_offset": effective["offset"] if mode == "page" else None,
            "requested_limit": effective["limit"] if mode == "page" else None,
            "response_start": start, "native_content_range": native_range,
            "returned_row_count": len(docs), "valid_row_count": valid_count,
            "invalid_row_count": len(docs) - valid_count, "reported_total": total,
            "count_exactness": exactness, "response_complete": response_complete,
            "population_coverage": "unknown", "next_offset": None, "next_offset_basis": None}
    if mode == "page" and not population_issues:
        offset = effective["offset"]
        if (response_complete and exactness == "exact" and offset == 0
                and total == len(docs) and valid_count == len(docs)):
            page["population_coverage"] = "complete"
        elif total is not None and (offset > 0 or total > len(docs)):
            page["population_coverage"] = "subset"
        if docs and response_complete and (total is None or offset + len(docs) < total):
            page["next_offset"] = offset + len(docs)
            page["next_offset_basis"] = "total_unknown" if total is None else "reported_more"
    facets = []
    if mode == "facet":
        facet, facet_issues = _facets(payload, snapshot.sha256, transport["headers"],
                                    effective["facet"], population_key, is_solr=is_solr,
                                    complete=response_complete)
        if exact is True and total is not None:
            for bucket in facet["buckets"]:
                if bucket["count"] is not None and bucket["count"] > total:
                    conflict = _issue("bvbrc_population_metadata_conflict", "population",
                        field=effective["facet"]["field"], path=bucket["native_path"])
                    facet_issues.append(conflict)
            if facet_issues:
                facet["bucket_window_status"] = "invalid"
                facet["all_categories_complete"] = False
        facets.append(facet)
        issues.extend(facet_issues)
        conflicts = [issue for issue in facet_issues if issue["code"] == "bvbrc_population_metadata_conflict"]
        if conflicts:
            population_issues.extend(conflicts)
            count.update(availability="unavailable", reason="population_conflict")
            page["response_complete"] = False
            facet["all_categories_complete"] = False
    failures = [issue for issue in issues if issue["code"] != _WARNING]
    status = "partial" if failures else "complete"
    sheet = {"version": "bvbrc_data_sheet_v1", "collection": collection, "mode": mode,
             "custody": {"native_sha256": snapshot.sha256, "retrieved_at": snapshot.retrieved_at,
                         "requested_url": snapshot.url,
                         "effective_url": snapshot.transport.get("effective_url", snapshot.url),
                         "media_type": snapshot.media_type, "native_profile": profile,
                         "prepared_sha256": json_digest(prepared),
                         "field_contract_version": FIELD_CONTRACT_VERSION},
             "transport": transport,
             "qualification": {"service_matches": snapshot.service == "bvbrc_data",
                               "request_matches": qualified_request,
                               "transport_complete": transport["body_complete"], "http_success": True,
                               "format_valid": not format_issues,
                               "population_metadata_valid": not population_issues,
                               "native_partial_results": partial,
                               "requested_fields_valid": valid_count == len(docs), "status": status},
             "population": population, "selected_fields": fields, "page": page,
             "count": count, "rows": rows, "facets": facets, "issues": issues}
    return validate("ParseResult", {"version": "bvbrc_data_parse_result_v1", "status": status,
                    "sheet": sheet, "failures": failures, "retained_native_sha256": snapshot.sha256})


def _facets(payload, digest, headers, request, population_key, *, is_solr, complete):
    field = request["field"]
    location = ("/facet_counts" if is_solr else "/headers/facet_counts")
    issues = []
    header_values = _header_values(headers, "facet_counts")
    decoded_headers = []
    for raw in header_values:
        try:
            decoded_headers.append(_decode_json(raw))
        except (ValueError, UnicodeError, RecursionError):
            issues.append(_issue("bvbrc_invalid_facet_pairs", "format", field=field,
                                 path="/headers/facet_counts"))
    source = payload.get("facet_counts") if is_solr else decoded_headers[0] if decoded_headers else None
    if any(value != source for value in decoded_headers):
        issues.append(_issue("bvbrc_population_metadata_conflict", "population",
                             field=field, path="/headers/facet_counts"))
    pairs = None
    if type(source) is dict and type(source.get("facet_fields")) is dict:
        pairs = source["facet_fields"].get(field)
        for name in ("facet_queries", "facet_ranges", "facet_intervals", "facet_heatmaps"):
            if source.get(name) not in (None, {}):
                issues.append(_issue("bvbrc_invalid_facet_pairs", "format", field=field,
                                     path=location + "/" + name))
    location += "/facet_fields/" + _escape(field)
    if type(pairs) is not list:
        issues.append(_issue("bvbrc_invalid_facet_pairs", "format", field=field, path=location))
        pairs = []
    elif len(pairs) % 2:
        issues.append(_issue("bvbrc_invalid_facet_pairs", "format", field=field, path=location))
    buckets = []
    term_counts = {}
    for index in range(0, len(pairs), 2):
        if pairs[index] is None or type(pairs[index]) is str:
            term_counts[pairs[index]] = term_counts.get(pairs[index], 0) + 1
    for index in range(0, len(pairs), 2):
        native_term = pairs[index]
        term_valid = native_term is None or type(native_term) is str
        term = _atom(native_term) if term_valid else None
        native_count = pairs[index + 1] if index + 1 < len(pairs) else None
        count = native_count.project() if isinstance(native_count, _Number) and native_count.integer else None
        count_valid = count is not None and count >= 0
        bucket_issues = []
        path = location + "/" + str(index)
        if not term_valid or not count_valid:
            bucket_issues.append(_issue("bvbrc_invalid_facet_pairs", "format", field=field,
                                        path=path if not term_valid else location + "/" + str(index + 1)))
        if term_valid and (term_counts[native_term] > 1 or native_term is None and not request["include_missing"]):
            bucket_issues.append(_issue("bvbrc_invalid_facet_pairs", "format", field=field, path=path))
        key = digest + "/facet/" + _escape(field) + "/bucket/" + str(index // 2)
        buckets.append({"bucket_key": key, "term_cell_key": key + "/term", "native_path": path,
                        "term": term, "is_missing_bucket": native_term is None if term_valid else None,
                        "count": count if count_valid else None,
                        "status": "invalid" if bucket_issues else "valid", "issues": bucket_issues})
        issues.extend(bucket_issues)
    nonmissing = sum(bucket["is_missing_bucket"] is False for bucket in buckets)
    if nonmissing > request["limit"]:
        issues.append(_issue("bvbrc_population_metadata_conflict", "population", field=field, path=location))
    window = "invalid" if issues else "more_unknown" if nonmissing >= request["limit"] else "exhausted_window"
    return {"population_key": population_key, "request": deepcopy(request), "native_location": location,
            "buckets": buckets, "returned_nonmissing_bucket_count": nonmissing,
            "bucket_window_status": window,
            "all_categories_complete": bool(complete and not issues and window == "exhausted_window"
                and request["offset"] == 0 and request["min_count"] <= 1 and request["include_missing"]),
            "issues": issues}, issues


def _validated_sheet(value):
    """Validate D2 row/cell semantics without imposing host custody or joins."""
    sheet = validate("DataSheet", value)
    collection, digest = sheet["collection"], sheet["custody"]["native_sha256"]
    registry = FIELD_REGISTRY[collection]
    selected = sheet["selected_fields"]
    if any(field not in registry["fields"] for field in selected):
        raise ValueError("bvbrc_unknown_field")
    if sheet["page"]["mode"] != sheet["mode"]:
        raise ValueError("bvbrc_inconsistent_sheet_mode")
    if sheet["mode"] != "page" and (selected or sheet["page"]["requested_offset"] is not None
            or sheet["page"]["requested_limit"] is not None or sheet["page"]["next_offset"] is not None
            or sheet["page"]["population_coverage"] != "unknown"):
        raise ValueError("bvbrc_inconsistent_sheet_mode")
    for index, row in enumerate(sheet["rows"]):
        key = digest + "/row/" + str(index)
        if row["row_index"] != index or row["row_key"] != key:
            raise ValueError("bvbrc_invalid_row_identity")
        expected_path = ("/response/docs/" if sheet["custody"]["native_profile"] == "solr_json_envelope_v1" else "/") + str(index)
        if row["native_path"] != expected_path:
            raise ValueError("bvbrc_invalid_row_identity")
        if [cell["field"] for cell in row["cells"]] != selected:
            raise ValueError("bvbrc_invalid_selected_cells")
        for cell in row["cells"]:
            field = cell["field"]
            if cell["cell_key"] != key + "/field/" + _escape(field) or cell["native_path"] != row["native_path"] + "/" + _escape(field):
                raise ValueError("bvbrc_invalid_cell_identity")
            if cell["presence"] != "present" and cell["atoms"]:
                raise ValueError("bvbrc_invalid_native_atoms")
            if cell["native_shape"] == "scalar" and len(cell["atoms"]) != 1:
                raise ValueError("bvbrc_invalid_native_atoms")
            for atom in cell["atoms"]:
                kind = atom["kind"]
                expected_key = {"string": "string_value", "number": "number_value", "boolean": "boolean_value"}.get(kind)
                if any(atom[key] is not None for key in ("string_value", "number_value", "boolean_value") if key != expected_key):
                    raise ValueError("bvbrc_invalid_native_atoms")
                if kind == "number":
                    lexeme = atom["number_lexeme"]
                    projected = _Number(lexeme).project() if type(lexeme) is str else None
                    if (lexeme is None or _NUMBER.fullmatch(lexeme) is None
                            or projected != atom["number_value"]
                            or type(projected) is not type(atom["number_value"])):
                        raise ValueError("bvbrc_invalid_numeric_lexeme")
                    if atom["number_value"] is None and "bvbrc_unrepresentable_numeric_value" not in cell["issue_codes"]:
                        raise ValueError("bvbrc_unqualified_numeric_loss")
                elif atom["number_lexeme"] is not None or expected_key and atom[expected_key] is None:
                    raise ValueError("bvbrc_invalid_native_atoms")
            if cell["presence"] == "unselected":
                raise ValueError("bvbrc_unselected_acquired_cell")
            spec = registry["fields"][field]
            if cell["presence"] in ("absent", "null"):
                raw = {} if cell["presence"] == "absent" else {field: None}
            elif cell["native_shape"] == "object" or (cell["native_shape"] == "array"
                    and cell["status"] == "invalid" and not cell["atoms"]):
                # Unsupported complex values have only a raw-byte locator.
                if (cell["presence"] != "present" or cell["atoms"]
                        or cell["status"] != "invalid" or cell["field_schema_status"] != "mismatch"
                        or cell["issue_codes"] != ["bvbrc_invalid_native_field"]):
                    raise ValueError("bvbrc_invalid_native_atoms")
                continue
            elif cell["native_shape"] in ("scalar", "array"):
                values = [_Number(atom["number_lexeme"]) if atom["kind"] == "number" else
                          atom["string_value"] if atom["kind"] == "string" else
                          atom["boolean_value"] if atom["kind"] == "boolean" else None
                          for atom in cell["atoms"]]
                raw = {field: values if cell["native_shape"] == "array" else values[0]}
            else:
                raise ValueError("bvbrc_invalid_native_atoms")
            expected_cell = _native_cell(raw, field=field, spec=spec,
                                         row_key=key, path=cell["native_path"])
            if _canonical(cell) != _canonical(expected_cell):
                raise ValueError("bvbrc_inconsistent_native_cell")
        expected = [_numeric_cell(cell, registry["fields"][cell["field"]]) for cell in row["cells"]
                    if registry["fields"][cell["field"]]["numeric_projection"]]
        if _canonical(row["numerical_cells"]) != _canonical(expected):
            raise ValueError("bvbrc_inconsistent_numeric_cells")
        identity_cells = [cell for cell in row["cells"] if cell["field"] == registry["unique_key"]]
        if identity_cells:
            identity = identity_cells[0]
            native_id = (identity["atoms"][0]["string_value"] if identity["status"] == "valid"
                         and identity["native_shape"] == "scalar" and identity["atoms"]
                         and identity["atoms"][0]["kind"] == "string" else None)
            if row["native_id"] != (native_id or None):
                raise ValueError("bvbrc_inconsistent_native_identity")
        has_invalid = (row["native_id"] is None or any(cell["status"] in ("invalid", "unrepresentable")
                       for cell in row["cells"]) or any(cell["status"] == "invalid" for cell in expected))
        if (row["status"] == "valid") == has_invalid:
            raise ValueError("bvbrc_inconsistent_row_status")
    page = sheet["page"]
    valid = sum(row["status"] == "valid" for row in sheet["rows"])
    if (page["returned_row_count"] != len(sheet["rows"]) or page["valid_row_count"] != valid
            or page["invalid_row_count"] != len(sheet["rows"]) - valid):
        raise ValueError("bvbrc_inconsistent_page_counts")
    if sheet["qualification"]["requested_fields_valid"] != (valid == len(sheet["rows"])):
        raise ValueError("bvbrc_inconsistent_row_qualification")
    if len(sheet["facets"]) != (1 if sheet["mode"] == "facet" else 0):
        raise ValueError("bvbrc_inconsistent_facet_selection")
    for facet in sheet["facets"]:
        field = facet["request"]["field"]
        if field not in registry["fields"] or not registry["fields"][field]["facet_supported"]:
            raise ValueError("bvbrc_facet_field_not_supported")
        for index, bucket in enumerate(facet["buckets"]):
            key = digest + "/facet/" + _escape(field) + "/bucket/" + str(index)
            if (bucket["bucket_key"] != key or bucket["term_cell_key"] != key + "/term"
                    or bucket["native_path"] != facet["native_location"] + "/" + str(index * 2)):
                raise ValueError("bvbrc_invalid_bucket_identity")
            term = bucket["term"]
            if term is None:
                if bucket["status"] != "invalid" or bucket["is_missing_bucket"] is not None:
                    raise ValueError("bvbrc_invalid_facet_term")
            else:
                if term["kind"] not in ("string", "null"):
                    raise ValueError("bvbrc_invalid_facet_term")
                expected_term = _atom(term["string_value"] if term["kind"] == "string" else None)
                if term != expected_term or bucket["is_missing_bucket"] != (term["kind"] == "null"):
                    raise ValueError("bvbrc_invalid_facet_term")
            if bucket["status"] == "valid" and (bucket["count"] is None or bucket["issues"]):
                raise ValueError("bvbrc_invalid_facet_count")
        nonmissing = sum(bucket["is_missing_bucket"] is False for bucket in facet["buckets"])
        if facet["returned_nonmissing_bucket_count"] != nonmissing:
            raise ValueError("bvbrc_inconsistent_facet_counts")
        window = ("invalid" if facet["issues"] or any(bucket["status"] == "invalid" for bucket in facet["buckets"])
                  else "more_unknown" if nonmissing >= facet["request"]["limit"] else "exhausted_window")
        if facet["bucket_window_status"] != window:
            raise ValueError("bvbrc_inconsistent_facet_window")
        expected_complete = bool(page["response_complete"] and window == "exhausted_window"
            and facet["request"]["offset"] == 0 and facet["request"]["min_count"] <= 1
            and facet["request"]["include_missing"])
        if facet["all_categories_complete"] != expected_complete:
            raise ValueError("bvbrc_inconsistent_facet_completeness")
    return sheet


def extract_collection_rows(page_sheet: dict, *, fields: tuple[str, ...]) -> dict:
    """Select supplied cells for every retained row; preserve missing selection."""
    sheet = _validated_sheet(page_sheet)
    if sheet["mode"] != "page":
        raise ValueError("bvbrc_incompatible_input")
    registry = FIELD_REGISTRY[sheet["collection"]]
    if (type(fields) is not tuple or any(type(field) is not str for field in fields)
            or len(set(fields)) != len(fields)):
        raise ValueError("bvbrc_invalid_field_selection")
    if any(field not in registry["fields"] for field in fields):
        raise ValueError("bvbrc_unknown_field")
    rows = []
    for original in sheet["rows"]:
        row = deepcopy(original)
        cells = {cell["field"]: cell for cell in row["cells"]}
        row["cells"] = [cells[field] if field in cells else _native_cell({}, field=field,
            spec=registry["fields"][field], row_key=row["row_key"],
            path=row["native_path"] + "/" + _escape(field), selected=False) for field in fields]
        row["numerical_cells"] = [_numeric_cell(cell, registry["fields"][cell["field"]])
            for cell in row["cells"] if registry["fields"][cell["field"]]["numeric_projection"]]
        rows.append(row)
    return validate("CollectionRowsExtraction", {"version": "bvbrc_collection_rows_v1",
        "collection": sheet["collection"], "native_sha256": sheet["custody"]["native_sha256"],
        "requested_fields": list(fields), "rows": rows, "issues": sheet["issues"]})


def validate_data_sheet(value: dict) -> dict:
    """Return a detached saved sheet after finite/closed D2 semantic checks.

    Checks registered field membership, native row/cell identities and paths,
    scalar atom kinds/lexemes, numerical projections of those atoms, row/page
    counts and facet references/windows. Invalid input raises ValueError. Valid
    partial sheets and recorded population conflicts remain usable; calculators
    retain the corresponding unavailable reasons. This function reads no raw
    source, performs no acquisition, mutates no caller data and confers no host
    custody, source possession, biological join or episode admission.
    """
    return _validated_sheet(value)
