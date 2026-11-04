"""Closed literal Addgene metadata, separate from acquisition and authority.

The existing native schema owns every native row. Publication construction
checks the existing selected request and native metadata, then copies values.
Frozen validation checks the returned shape and field relationships only: it
does not read Files, parse native data, calculate lengths or authenticate a
Source. The receiving boundary must compare actual original facts separately.
"""
from copy import deepcopy
import re

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from . import addgene_sequence_native as native


FACT_SOURCE = "execution_addgene_sequence_facts"
FACT_VERSION = "addgene_sequence_fact_v1"
_SOURCE = re.compile(r"source_[0-9a-f]{24}\Z")
_FILE = re.compile(r"artifact_[0-9a-f]{64}\Z")
_INVALID_CODES = frozenset(("empty_literal", "invalid_literal", "incomplete_literal",
    "ambiguous_sequence_identity", "conflicting_sequence_literals"))


def _object(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


_PAGE = native.ADDGENE_SEQUENCE_PAGE_SCHEMA["properties"]
_NATIVE_ROW = _PAGE["records"]["items"]
_NULLABLE_ROW = {**deepcopy(_NATIVE_ROW), "type": ["object", "null"]}
_SELECTED_ROW = _object(dict(
    selection_ordinal={"type": "integer", "minimum": 0},
    record_ordinal={"type": "integer", "minimum": 0},
    status=deepcopy(_NATIVE_ROW["properties"]["sequence_status"]),
    issue_codes={"type": "array", "uniqueItems": True, "items": {"enum": [
        *_NATIVE_ROW["properties"]["issue_codes"]["items"]["enum"], "selected_record_unavailable"]}},
    # The existing Addgene publisher supplies no symbol count, including for
    # available literals. A later sequence-inspection action may measure it.
    symbol_count={"type": "null"},
    sequence_file_ref={"type": ["string", "null"], "format": "reference",
        "x-reference-namespace": "artifact", "pattern": r"^artifact_[0-9a-f]{64}$"},
    native_record=_NULLABLE_ROW,
))
ADDGENE_SEQUENCE_FACT_SCHEMA = _object(dict(
    version={"const": FACT_VERSION},
    source_ref={"type": "string", "format": "reference", "x-reference-namespace": "source",
        "pattern": r"^source_[0-9a-f]{24}$"},
    requested_id=deepcopy(_PAGE["requested_id"]),
    response_complete=deepcopy(_PAGE["response_complete"]),
    parse_status=deepcopy(_PAGE["parse_status"]),
    authentication_required=deepcopy(_PAGE["authentication_required"]),
    issues=deepcopy(_PAGE["issues"]),
    selected_rows={"type": "array", "items": _SELECTED_ROW},
))
ADDGENE_SEQUENCE_FACTS_SCHEMA = {"type": "array", "items": deepcopy(ADDGENE_SEQUENCE_FACT_SCHEMA),
    "x-source": FACT_SOURCE}


def _require(condition, code):
    if not condition:
        raise ValueError("addgene_sequence_fact_" + code)


def _copy(value, ancestors=()):
    """Detach the JSON-only metadata; this contract has no floating fields."""
    if value is None or type(value) in (int, bool):
        return value
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError as error:
            raise ValueError("addgene_sequence_fact_json_required") from error
        return value
    _require(id(value) not in ancestors, "json_required")
    if type(value) is list:
        return [_copy(item, (*ancestors, id(value))) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {_copy(key): _copy(item, (*ancestors, id(value))) for key, item in value.items()}
    raise ValueError("addgene_sequence_fact_json_required")


def _native_relationships(row, fact, issues):
    record = row["native_record"]
    ordinal = row["record_ordinal"]
    if record is None:
        _require(row["status"] == "unavailable" and row["sequence_file_ref"] is None
            and row["issue_codes"] == ["selected_record_unavailable"]
            and not any(owner == ordinal for _, owner in issues), "unavailable_relationship")
        return
    _require(record["record_ordinal"] == ordinal and row["status"] == record["sequence_status"]
        and row["issue_codes"] == record["issue_codes"]
        and set(record["issue_codes"]) == {code for code, owner in issues if owner == ordinal},
        "native_relationship")
    _require((record["source_completeness"], record["source_verification"])
        == native._CATEGORIES.get(record["section_id"], ("unknown", "unknown")), "category_relationship")
    positions = [locator["source_element_ordinal"] for locator in record["locators"]]
    _require(positions == sorted(positions), "locator_order")
    identities = []
    for locator in record["locators"]:
        identity = tuple(locator[key] for key in ("tag", "attribute", "value", "source_element_ordinal"))
        _require(identity not in identities, "locator_identity")
        identities.append(identity)
        if locator["attribute"] == "href":
            match = native._LINK.fullmatch(locator["value"])
            _require(locator["tag"] == "a" and match is not None
                and match[1] == record["sequence_id"], "locator_identity")
        else:
            _require(locator["tag"] == "textarea" and locator["attribute"] == "class"
                and "copy-from" in locator["value"].split(), "locator_identity")
    status = row["status"]
    text, sequence, header = (record[key] for key in ("native_sequence_text", "sequence", "native_header"))
    if status == "available":
        _require(sequence is not None and set(sequence) <= native._DNA and text is not None
            and not row["issue_codes"] and row["sequence_file_ref"] is not None, "available_relationship")
    else:
        _require(sequence is None and row["sequence_file_ref"] is None, "sequence_relationship")
        if status == "authentication_required":
            _require(fact["authentication_required"] and row["issue_codes"] == ["authentication_required"]
                and text is None and header is None, "authentication_relationship")
        elif status == "download_required":
            _require(not fact["authentication_required"] and record["sequence_id"] is not None
                and row["issue_codes"] == ["download_required"] and text is None and header is None,
                "download_relationship")
        elif status == "invalid":
            _require(text is not None and bool(row["issue_codes"])
                and set(row["issue_codes"]) <= _INVALID_CODES, "invalid_relationship")
        else:
            _require(text is None and header is None and bool(row["issue_codes"]), "unavailable_relationship")


def validate_addgene_sequence_fact(value):
    """Validate literal frozen metadata without parsing, hashing or reading it."""
    try:
        value = _copy(value)
        Draft202012Validator(ADDGENE_SEQUENCE_FACT_SCHEMA).validate(value)
    except (ValueError, TypeError, RecursionError, ValidationError) as error:
        raise ValueError("addgene_sequence_fact_schema_invalid") from error
    _require(_SOURCE.fullmatch(value["source_ref"]) is not None, "source_invalid")
    issues = {(row["code"], row["record_ordinal"]) for row in value["issues"]}
    _require((("response_incomplete", None) in issues) == (not value["response_complete"]), "response_relationship")
    _require((("authentication_required", None) in issues) == value["authentication_required"], "authentication_relationship")
    if value["parse_status"] == "complete":
        _require(value["response_complete"] and not value["issues"], "page_relationship")
    else:
        _require(bool(value["issues"]), "page_relationship")
    if value["parse_status"] == "invalid":
        _require(any(code in {"invalid_encoding", "invalid_html"} and owner is None for code, owner in issues)
            and all(row["native_record"] is None for row in value["selected_rows"]), "page_relationship")
    selected = []
    for ordinal, row in enumerate(value["selected_rows"]):
        _require(row["selection_ordinal"] == ordinal and row["record_ordinal"] not in selected, "selection_relationship")
        selected.append(row["record_ordinal"])
        _native_relationships(row, value, issues)
    present = sorted((row["native_record"] for row in value["selected_rows"]
        if row["native_record"] is not None), key=lambda row: row["record_ordinal"])
    first, locators = -1, set()
    for record in present:
        _require(record["locators"][0]["source_element_ordinal"] > first, "native_order_relationship")
        first = record["locators"][0]["source_element_ordinal"]
        for locator in record["locators"]:
            identity = tuple(locator[key] for key in ("tag", "attribute", "value", "source_element_ordinal"))
            _require(identity not in locators, "locator_identity")
            locators.add(identity)
    return value


def build_addgene_sequence_fact(publication):
    """Copy one Addgene publication; this does not establish its Store custody."""
    from . import sequence_support_publication as owner
    try:
        body = _copy(publication)
        owner._shape(body)
        _require(body["representation"] == "addgene_html"
            and body["request"]["operation"] == "get_plasmid_sequence"
            and body["request"].get("provider") == "addgene", "publication_required")
        parsed = native.validate_addgene_sequence_page(body["parsed"])
    except (ValueError, KeyError, TypeError, RecursionError) as error:
        raise ValueError("addgene_sequence_fact_publication_invalid") from error
    _require(type(body["native_source_ref"]) is str and _SOURCE.fullmatch(body["native_source_ref"]) is not None
        and type(body["native_artifact_ref"]) is str and _FILE.fullmatch(body["native_artifact_ref"]) is not None
        and parsed["source_ref"] == body["native_source_ref"]
        and parsed["requested_id"] == body["request"]["plasmid_id"]
        and body["reference_bindings"] == [] and body["extractions"] is None, "publication_identity")
    choices, rows = body["selector"]["record_ordinals"], body["sequence_bindings"]
    _require(len(rows) == len(choices), "publication_selection")
    records = {row["record_ordinal"]: row for row in parsed["records"]}
    selected, missing = [], []
    for ordinal, (index, binding) in enumerate(zip(choices, rows, strict=True)):
        record = records.get(index)
        sequence = record["sequence"] if record is not None else None
        expected_file = owner._artifact_id(sequence) if sequence is not None else None
        _require(binding == owner._sequence_row(ordinal, index, None, None, expected_file, None,
            record["sequence_status"] if record is not None else "unavailable",
            record["issue_codes"] if record is not None else ["selected_record_unavailable"]), "publication_binding")
        if record is None:
            missing.append(owner._error("selected_record_unavailable", index))
        selected.append(dict(selection_ordinal=ordinal, record_ordinal=index, status=binding["status"],
            issue_codes=deepcopy(binding["issue_codes"]), symbol_count=binding["symbol_count"],
            sequence_file_ref=binding["sequence_ref"], native_record=deepcopy(record)))
    expected_errors = owner._unique_errors([*[owner._error(row["code"], row["record_ordinal"])
        for row in parsed["issues"]], *missing])
    _require(body["projection_errors"] == expected_errors, "publication_issues")
    return validate_addgene_sequence_fact(dict(version=FACT_VERSION, source_ref=body["native_source_ref"],
        requested_id=parsed["requested_id"], response_complete=parsed["response_complete"],
        parse_status=parsed["parse_status"], authentication_required=parsed["authentication_required"],
        issues=deepcopy(parsed["issues"]), selected_rows=selected))


__all__ = ["FACT_SOURCE", "FACT_VERSION", "ADDGENE_SEQUENCE_FACT_SCHEMA", "ADDGENE_SEQUENCE_FACTS_SCHEMA",
    "build_addgene_sequence_fact", "validate_addgene_sequence_fact"]
