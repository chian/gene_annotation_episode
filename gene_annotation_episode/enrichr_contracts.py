"""One retained Enrichr table and literal saved views of its native cells.

Parsing preserves submitted literals, original response bytes and row positions.
No function submits a request or calculates an enrichment statistic. Deterministic
byte/sheet validation establishes internal consistency, not source permissions,
server identity, a measured universe or correctness of the provider's statistics.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import math
import re


REQUEST_VERSION = "enrichr_request_v1"
SELECTOR_VERSION = "enrichr_selector_v1"
SHEET_VERSION = "enrichr_response_sheet_v1"
COMPONENTS_VERSION = "enrichr_components_v1"
TABLE_SOURCE = "execution_enrichr_tables"
ROW_SOURCE = "execution_enrichr_rows"
PROTOCOLS = ("standard_enrichr_v1", "speedrichr_v1")
PROFILES = ("documented_odds_v1", "gget_z_label_v1", "uninterpreted")
FIELD_POSITIONS = {"rank": 0, "term": 1, "p_value": 2, "statistic_3": 3,
    "combined_score": 4, "overlap": 5, "adjusted_p_value": 6,
    "old_p_value": 7, "old_adjusted_p_value": 8}
QUALIFICATIONS = ("response_incomplete", "invalid_utf8", "invalid_json",
    "duplicate_json_key", "response_not_object", "library_missing", "library_null",
    "library_not_array", "nonstandard_numeric_token", "malformed_row",
    "unexpected_native_width", "legacy_columns_absent", "extra_columns_retained",
    "invalid_rank", "invalid_term", "invalid_overlap", "invalid_probability",
    "native_nonfinite", "numeric_underflow", "numeric_overflow",
    "profile_width_conflict", "profile_value_conflict", "interface_definition_conflict",
    "declared_documentation_interpretation", "statistic_uninterpreted")


def _obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}


def _enum(values, *, nullable=False):
    return {"type": ["string", "null"] if nullable else "string",
        "enum": [*values, None] if nullable else list(values)}


_ENTRY = {"type": "string", "minLength": 1, "pattern": r"^[^\r\n]+$"}
_GENES = {"type": "array", "items": _ENTRY, "minItems": 1}
ENRICHR_REQUEST_SCHEMA = _obj({
    "version": {"type": "string", "const": REQUEST_VERSION},
    "protocol_profile": _enum(PROTOCOLS),
    "library": deepcopy(_ENTRY), "genes": deepcopy(_GENES),
    "identifier_policy": {"type": "string", "const": "literal_no_mapping"},
    "species_context": {"type": ["string", "null"]},
    "description": {"type": "string"},
    "background": _obj({"policy": _enum(("service_native", "supplied")),
        "genes": {"type": ["array", "null"], "items": deepcopy(_ENTRY), "minItems": 1}}),
    "native_statistic_profile": _enum(PROFILES),
})
ENRICHR_SELECTOR_SCHEMA = _obj({
    "version": {"type": "string", "const": SELECTOR_VERSION},
    "offset": {"type": "integer", "minimum": 0},
    "limit": {"type": "integer", "minimum": 0},
})


def _copy(value):
    def check(item):
        if item is None or type(item) in (bool, int):
            return
        if type(item) is str:
            item.encode("utf-8")
            return
        if type(item) is float:
            if math.isfinite(item):
                return
            raise ValueError("nonfinite_json_number")
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for key, child in item.items():
                key.encode("utf-8")
                check(child)
            return
        raise ValueError("not_json_data")
    try:
        check(value)
        content = json.dumps(value, allow_nan=False, ensure_ascii=False)
        content.encode("utf-8")
        return json.loads(content)
    except (TypeError, ValueError, OverflowError, UnicodeError, RecursionError) as error:
        raise ValueError("enrichr_finite_json_required") from error


def _same(left, right):
    return json.dumps(left, sort_keys=True, ensure_ascii=False, allow_nan=False) == json.dumps(
        right, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _keys(value, expected, code):
    _require(type(value) is dict and set(value) == set(expected), code)


def _entry(value):
    return type(value) is str and bool(value) and "\r" not in value and "\n" not in value


def validate_enrichr_request(value):
    value = _copy(value)
    _keys(value, ENRICHR_REQUEST_SCHEMA["properties"], "enrichr_request_invalid")
    _require(value["version"] == REQUEST_VERSION and value["protocol_profile"] in PROTOCOLS
        and value["native_statistic_profile"] in PROFILES
        and value["identifier_policy"] == "literal_no_mapping"
        and _entry(value["library"]) and type(value["description"]) is str
        and (value["species_context"] is None or type(value["species_context"]) is str)
        and type(value["genes"]) is list and len(value["genes"]) > 0
        and all(_entry(item) for item in value["genes"]),
        "enrichr_request_invalid")
    background = value["background"]
    _keys(background, ("policy", "genes"), "enrichr_background_invalid")
    _require((background["policy"] == "service_native" and background["genes"] is None)
        or (background["policy"] == "supplied" and type(background["genes"]) is list and len(background["genes"]) > 0
            and all(_entry(item) for item in background["genes"])), "enrichr_background_invalid")
    _require(background["policy"] != "supplied" or value["protocol_profile"] == "speedrichr_v1",
        "enrichr_background_protocol_conflict")
    return value


def validate_enrichr_selector(value):
    value = _copy(value)
    _keys(value, ENRICHR_SELECTOR_SCHEMA["properties"], "enrichr_selector_invalid")
    _require(value["version"] == SELECTOR_VERSION and all(type(value[name]) is int
        and value[name] >= 0 for name in ("offset", "limit")), "enrichr_selector_invalid")
    return value


@dataclass(frozen=True)
class _Number:
    lexeme: str


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_json_key")
        key.encode("utf-8")
        value[key] = item
    return value


def _kind(value):
    if isinstance(value, _Number):
        return "number"
    return {str: "string", bool: "boolean", list: "array", dict: "object",
        type(None): "null"}[type(value)]


def _pointer(value):
    return "/" + value.replace("~", "~0").replace("/", "~1")


def _number_value(token):
    """One projection of a retained native token; no statistical calculation."""
    text = token.lexeme
    if text in ("NaN", "Infinity", "-Infinity"):
        return {"NaN": "nan", "Infinity": "positive_infinity",
            "-Infinity": "negative_infinity"}[text], None
    try:
        decimal = Decimal(text)
        if not any(character in text for character in ".eE"):
            return "finite", int(text)
        number = float(text)
        if not math.isfinite(number):
            return "overflow", None
        if number == 0 and decimal != 0:
            return "underflow", None
        return "finite", number
    except (ValueError, OverflowError, InvalidOperation):
        return "overflow", None


def _atom(value, *, position, pointer):
    kind = _kind(value)
    number_state, number_value = _number_value(value) if kind == "number" else (None, None)
    return {"position": position, "pointer": pointer, "kind": kind,
        "number_lexeme": value.lexeme if kind == "number" else None,
        "number_state": number_state, "number_value": number_value,
        "string_value": value if kind == "string" else None,
        "boolean_value": value if kind == "boolean" else None}


def _metric(atoms, position, *, probability=False, rank=False):
    result = {"position": position, "pointer": None, "state": "missing", "value": None,
        "number_lexeme": None, "reason": "native_field_absent",
        "unit": "ordinal_1_based" if rank else "dimensionless"}
    if position >= len(atoms):
        return result
    atom = atoms[position]
    result["pointer"] = atom["pointer"]
    if atom["kind"] == "null":
        return {**result, "state": "null", "reason": "native_null"}
    if atom["kind"] != "number":
        return {**result, "state": "invalid", "reason": "expected_native_number"}
    text, state = atom["number_lexeme"], atom["number_state"]
    result["number_lexeme"] = text
    if state in ("nan", "positive_infinity", "negative_infinity"):
        return {**result, "state": "nonfinite", "reason": state}
    if state in ("overflow", "underflow"):
        return {**result, "state": "unrepresentable", "reason": "numeric_" + state}
    if probability and not Decimal(0) <= Decimal(text) <= Decimal(1):
        return {**result, "state": "invalid", "reason": "probability_out_of_range"}
    if rank and (any(character in text for character in ".eE") or Decimal(text) < 1):
        return {**result, "state": "invalid", "reason": "expected_positive_integer"}
    return {**result, "state": "present", "value": atom["number_value"], "reason": None}


def _literal(value, *, ordinal, pointer):
    kind = _kind(value)
    return {"ordinal": ordinal, "pointer": pointer, "kind": kind,
        "state": "present" if kind == "string" else "null" if kind == "null" else "invalid",
        "value": value if kind == "string" else None}


def _term(values, pointer):
    if len(values) <= 1:
        return {"ordinal": 1, "pointer": None, "kind": "absent", "state": "missing", "value": None}
    return _literal(values[1], ordinal=1, pointer=pointer + "/1")


def _overlap(values, pointer):
    result = {"state": "missing", "pointer": None, "native_kind": "absent",
        "returned_entry_count": None, "entries": []}
    if len(values) <= 5:
        return result
    value = values[5]
    result.update(pointer=pointer + "/5", native_kind=_kind(value))
    if value is None:
        return {**result, "state": "null"}
    if type(value) is not list:
        return {**result, "state": "invalid"}
    return {**result, "state": "present", "returned_entry_count": len(value),
        "entries": [_literal(item, ordinal=i, pointer=pointer + "/5/" + str(i))
            for i, item in enumerate(value)]}


def _interpret_slot(profile, width, atom):
    declared = {"documented_odds_v1": "odds_ratio", "gget_z_label_v1": "z_score",
        "uninterpreted": None}[profile]
    result = {"profile": profile, "declared_meaning": declared, "meaning": "unknown",
        "claimed_client_label": "z_score" if profile == "gget_z_label_v1" else None,
        "basis": "documentation" if profile == "documented_odds_v1" else
            "client_label" if profile == "gget_z_label_v1" else "uninterpreted",
        "server_version_verified": False, "qualification_codes": []}
    if profile == "uninterpreted":
        result["qualification_codes"].append("statistic_uninterpreted")
        return result
    if width != 9:
        result["qualification_codes"].append("profile_width_conflict")
    if profile == "gget_z_label_v1":
        result["qualification_codes"].append("interface_definition_conflict")
        return result
    negative = (atom is not None and atom["kind"] == "number"
        and atom["number_state"] == "finite" and atom["number_value"] < 0)
    if negative:
        result["qualification_codes"].append("profile_value_conflict")
    if not result["qualification_codes"]:
        result.update(meaning="odds_ratio", qualification_codes=["declared_documentation_interpretation"])
    return result


def _row(value, ordinal, table_pointer, profile):
    pointer, kind = table_pointer + "/" + str(ordinal), _kind(value)
    values = value if kind == "array" else []
    atoms = [_atom(item, position=i, pointer=pointer + "/" + str(i))
        for i, item in enumerate(values)]
    result = {"ordinal": ordinal, "pointer": pointer, "native_kind": kind,
        "native_width": len(values) if kind == "array" else None,
        "native_row_value": _atom(value, position=ordinal, pointer=pointer), "native_cells": atoms,
        "term": _term(values, pointer), "overlap": _overlap(values, pointer),
        "statistics": {name: _metric(atoms, position, probability="p_value" in name, rank=name == "rank")
            for name, position in FIELD_POSITIONS.items() if name not in ("term", "overlap")},
        "statistic_3_interpretation": _interpret_slot(profile,
            len(values) if kind == "array" else None, atoms[3] if len(atoms) > 3 else None),
        "qualification_codes": []}
    codes = result["qualification_codes"]
    if kind != "array":
        codes.append("malformed_row")
    elif len(values) not in (7, 9):
        codes.append("unexpected_native_width")
    if kind == "array" and len(values) == 7:
        codes.append("legacy_columns_absent")
    if len(values) > 9:
        codes.append("extra_columns_retained")
    if result["statistics"]["rank"]["state"] != "present":
        codes.append("invalid_rank")
    if result["term"]["state"] != "present":
        codes.append("invalid_term")
    if result["overlap"]["state"] != "present" or any(
            item["state"] != "present" for item in result["overlap"]["entries"]):
        codes.append("invalid_overlap")
    if any(cell["reason"] == "probability_out_of_range" for cell in result["statistics"].values()):
        codes.append("invalid_probability")
    for state, code in (("nan", "native_nonfinite"), ("positive_infinity", "native_nonfinite"),
            ("negative_infinity", "native_nonfinite"), ("underflow", "numeric_underflow"),
            ("overflow", "numeric_overflow")):
        if any(atom["number_state"] == state for atom in atoms) and code not in codes:
            codes.append(code)
    codes.extend(result["statistic_3_interpretation"]["qualification_codes"])
    return result


def _population():
    return {name: {"state": "unknown", "value": None} for name in
        ("effective_universe", "mapped_genes", "testing_family_size", "server_version")}


def _parse(content, request, response_complete, media_type):
    response = {"complete": response_complete, "media_type": media_type,
        "raw_base64": base64.b64encode(content).decode("ascii"), "state": "decoded", "failure_code": None}
    table = {"state": "unavailable", "pointer": None, "native_kind": "absent",
        "native_value": None, "returned_row_count": None, "rows": []}
    codes = [] if response_complete else ["response_incomplete"]
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        response.update(state="invalid_utf8", failure_code="invalid_utf8")
        codes.append("invalid_utf8")
        decoded = None
    else:
        try:
            decoded = json.loads(text, parse_int=_Number, parse_float=_Number,
                parse_constant=_Number, object_pairs_hook=_unique_object)
            # Escaped lone surrogates are not valid UTF-8 scientific literals.
            def check_strings(item):
                if type(item) is str:
                    item.encode("utf-8")
                elif isinstance(item, _Number) and item.lexeme in ("NaN", "Infinity", "-Infinity"):
                    if "nonstandard_numeric_token" not in codes:
                        codes.append("nonstandard_numeric_token")
                elif type(item) is list:
                    for child in item:
                        check_strings(child)
                elif type(item) is dict:
                    for child in item.values():
                        check_strings(child)
            check_strings(decoded)
        except (ValueError, UnicodeError, RecursionError) as error:
            code = "duplicate_json_key" if str(error) == "duplicate_json_key" else "invalid_json"
            response.update(state="invalid_json", failure_code=code)
            codes.append(code)
            decoded = None
    if response["state"] == "decoded":
        if type(decoded) is not dict:
            table.update(state="invalid", pointer="", native_kind=_kind(decoded),
                native_value=_atom(decoded, position=0, pointer=""))
            codes.append("response_not_object")
        elif request["library"] not in decoded:
            table["state"] = "missing"
            codes.append("library_missing")
        else:
            value = decoded[request["library"]]
            table.update(pointer=_pointer(request["library"]), native_kind=_kind(value),
                native_value=_atom(value, position=0, pointer=_pointer(request["library"])))
            if value is None:
                table["state"] = "null"
                codes.append("library_null")
            elif type(value) is not list:
                table["state"] = "invalid"
                codes.append("library_not_array")
            else:
                table.update(state="rows" if value else "empty", returned_row_count=len(value),
                    rows=[_row(row, i, table["pointer"], request["native_statistic_profile"])
                        for i, row in enumerate(value)])
    return {"version": SHEET_VERSION, "request": request, "response": response,
        "table": table, "population": _population(), "qualification_codes": codes}


def parse_enrichr_response(content: bytes, *, request: dict, response_complete: bool,
                          media_type: str | None = None):
    _require(type(content) is bytes and type(response_complete) is bool
        and (media_type is None or type(media_type) is str), "enrichr_response_operands_invalid")
    request = validate_enrichr_request(request)
    if media_type is not None:
        _copy(media_type)
    return _parse(content, request, response_complete, media_type)


def validate_enrichr_sheet(value):
    """Check exact retained-byte interpretation, without granting source authority."""
    value = _copy(value)
    _keys(value, ("version", "request", "response", "table", "population", "qualification_codes"),
        "enrichr_sheet_invalid")
    _require(value["version"] == SHEET_VERSION, "enrichr_sheet_invalid")
    request = validate_enrichr_request(value["request"])
    response = value["response"]
    _keys(response, ("complete", "media_type", "raw_base64", "state", "failure_code"),
        "enrichr_sheet_invalid")
    _require(type(response["complete"]) is bool and type(response["raw_base64"]) is str
        and (response["media_type"] is None or type(response["media_type"]) is str), "enrichr_sheet_invalid")
    try:
        raw = base64.b64decode(response["raw_base64"], validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("enrichr_sheet_raw_bytes_invalid") from error
    expected = _parse(raw, request, response["complete"], response["media_type"])
    _require(_same(value, expected), "enrichr_sheet_consistency_conflict")
    return value


def _components(sheet, selector):
    count = sheet["table"]["returned_row_count"]
    offset, limit = selector["offset"], selector["limit"]
    known = count is not None
    rows = deepcopy(sheet["table"]["rows"][offset:offset + limit]) if known else []
    end = min(count, offset + len(rows)) if known else None
    return {"version": COMPONENTS_VERSION, "sheet": sheet, "selector": selector,
        "window": {"state": "known" if known else "unavailable", "offset": offset, "limit": limit,
            "selected_row_count": len(rows) if known else None,
            "selected_ordinals": [row["ordinal"] for row in rows],
            "has_more_captured_rows": end < count if known else None,
            "next_offset": end if known and limit > 0 and end < count else None,
            "all_captured_rows_selected": len(rows) == count if known else None}, "rows": rows}


def calculate_enrichr_components(sheet, *, selector):
    """Select retained rows only; native p/adjusted-p/score values are never recomputed."""
    return _components(validate_enrichr_sheet(sheet), validate_enrichr_selector(selector))


def project_enrichr_return(components, *, source_ref):
    _require(type(source_ref) is str and re.fullmatch(r"source_[a-f0-9]{24,64}", source_ref) is not None,
        "enrichr_return_source_invalid")
    value = _copy(components)
    _keys(value, ("version", "sheet", "selector", "window", "rows"), "enrichr_components_invalid")
    expected = _components(validate_enrichr_sheet(value["sheet"]), validate_enrichr_selector(value["selector"]))
    _require(_same(value, expected), "enrichr_components_consistency_conflict")
    sheet, window = value["sheet"], value["window"]
    request, response, table = sheet["request"], sheet["response"], sheet["table"]
    summary = {"version": "enrichr_table_return_v1", "source_ref": source_ref,
        "library": request["library"], "protocol_profile": request["protocol_profile"],
        "species_context": request["species_context"], "identifier_policy": request["identifier_policy"],
        "background_policy": request["background"]["policy"],
        "native_statistic_profile": request["native_statistic_profile"],
        "response_state": response["state"], "response_complete": response["complete"],
        "table_state": table["state"], "captured_returned_row_count": table["returned_row_count"],
        "window": deepcopy(window), "population": deepcopy(sheet["population"]),
        "qualification_codes": deepcopy(sheet["qualification_codes"])}
    return {TABLE_SOURCE: [summary], ROW_SOURCE: [{"version": "enrichr_row_return_v1",
        "source_ref": source_ref, **deepcopy(row)} for row in value["rows"]]}


def enrichr_fact_sources():
    """Closed literal fact shapes; an API owner must separately authenticate custody."""
    text = {"type": "string"}
    nullable_text = {"type": ["string", "null"]}
    nullable_number = {"type": ["number", "null"]}
    nullable_integer = {"type": ["integer", "null"], "minimum": 0}
    integer = {"type": "integer", "minimum": 0}
    boolean = {"type": ["boolean", "null"]}
    kinds = ("absent", "null", "number", "string", "boolean", "array", "object")
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    codes = {"type": "array", "uniqueItems": True, "items": _enum(QUALIFICATIONS)}
    atom = _obj({"position": integer, "pointer": text, "kind": _enum(kinds[1:]),
        "number_lexeme": nullable_text, "number_state": _enum(("finite", "nan", "positive_infinity",
            "negative_infinity", "underflow", "overflow"), nullable=True),
        "number_value": nullable_number, "string_value": nullable_text, "boolean_value": boolean})
    metric = _obj({"position": integer, "pointer": nullable_text,
        "state": _enum(("missing", "null", "invalid", "nonfinite", "unrepresentable", "present")),
        "value": nullable_number, "number_lexeme": nullable_text,
        "reason": _enum(("native_field_absent", "native_null", "expected_native_number", "nan",
            "positive_infinity", "negative_infinity", "probability_out_of_range",
            "expected_positive_integer", "numeric_overflow", "numeric_underflow"), nullable=True),
        "unit": _enum(("ordinal_1_based", "dimensionless"))})
    literal = _obj({"ordinal": integer, "pointer": nullable_text, "kind": _enum(kinds),
        "state": _enum(("missing", "null", "invalid", "present")), "value": nullable_text})
    overlap = _obj({"state": _enum(("missing", "null", "invalid", "present")),
        "pointer": nullable_text, "native_kind": _enum(kinds), "returned_entry_count": nullable_integer,
        "entries": {"type": "array", "items": literal}})
    interpretation = _obj({"profile": _enum(PROFILES),
        "declared_meaning": _enum(("odds_ratio", "z_score"), nullable=True),
        "meaning": _enum(("unknown", "odds_ratio")), "claimed_client_label": _enum(("z_score",), nullable=True),
        "basis": _enum(("documentation", "client_label", "uninterpreted")),
        "server_version_verified": {"type": "boolean", "const": False}, "qualification_codes": codes})
    population = _obj({name: _obj({"state": {"type": "string", "const": "unknown"},
        "value": {"type": "null"}}) for name in _population()})
    window = _obj({"state": _enum(("known", "unavailable")), "offset": integer, "limit": integer,
        "selected_row_count": nullable_integer, "selected_ordinals": {"type": "array", "items": integer},
        "has_more_captured_rows": boolean, "next_offset": nullable_integer,
        "all_captured_rows_selected": boolean})
    table = _obj({"version": {"type": "string", "const": "enrichr_table_return_v1"},
        "source_ref": source, "library": text, "protocol_profile": _enum(PROTOCOLS),
        "species_context": nullable_text, "identifier_policy": {"type": "string", "const": "literal_no_mapping"},
        "background_policy": _enum(("service_native", "supplied")), "native_statistic_profile": _enum(PROFILES),
        "response_state": _enum(("decoded", "invalid_utf8", "invalid_json")),
        "response_complete": {"type": "boolean"},
        "table_state": _enum(("unavailable", "invalid", "missing", "null", "rows", "empty")),
        "captured_returned_row_count": nullable_integer, "window": window, "population": population,
        "qualification_codes": codes})
    row = _obj({"version": {"type": "string", "const": "enrichr_row_return_v1"}, "source_ref": source,
        "ordinal": integer, "pointer": text, "native_kind": _enum(kinds[1:]), "native_width": nullable_integer,
        "native_row_value": atom, "native_cells": {"type": "array", "items": atom}, "term": literal, "overlap": overlap,
        "statistics": _obj({name: metric for name in FIELD_POSITIONS if name not in ("term", "overlap")}),
        "statistic_3_interpretation": interpretation, "qualification_codes": codes})
    return {name: {"type": "array", "meaning": meaning,
        "report_schema": {"type": "array", "items": shape, "x-source": name}}
        for name, shape, meaning in ((TABLE_SOURCE, table,
            "Captured Enrichr response and selected local row window; effective universe, mapped genes, testing-family size and server version remain unknown."),
            (ROW_SOURCE, row,
            "Literal native Enrichr rows at their original ordinals, with qualified numeric cells and explicitly declared statistic interpretation; no confidence or recomputed enrichment statistic."))}
