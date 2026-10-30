"""Pure point-liftover records; shape and consistency confer no custody.

PyLiftover performs the conversion. This module retains its complete supplied
observation, interprets native tuples once, and calculates only explicitly
defined population/selection components. It neither opens a chain nor imports
PyLiftover, acquires data, chooses a mapping, or authenticates a producer.
"""
from copy import deepcopy
import hashlib
import json
import math
import re


REQUEST_VERSION = "liftover_point_request_v1"
OBSERVATION_VERSION = "liftover_point_observation_v1"
SHEET_VERSION = "liftover_point_sheet_v1"
COMPONENTS_VERSION = "liftover_point_components_v1"
RETURN_VERSION = "liftover_point_return_v1"
FACT_SOURCE = "liftover_point_mappings"
CALL_SCOPE = "retained_convert_coordinate_call"
CHAIN_FORMATS = ("ucsc_chain", "ucsc_chain_gzip")
CALL_STATES = ("not_started", "returned", "raised", "uncertain")
POINT_STATES = ("not_started", "conversion_failed", "execution_unconfirmed", "result_unavailable",
    "chromosome_not_in_chain", "unmapped_under_selected_chain", "unique", "multiple",
    "native_result_invalid", "native_rows_invalid")
ISSUES = ("native_result_type_invalid", "native_tuple_type_invalid", "native_tuple_width_invalid",
    "native_target_chromosome_invalid", "native_target_position_invalid", "native_target_strand_invalid",
    "native_chain_score_invalid")
FAILURES = {
    "input_unavailable": "input", "input_identity_conflict": "input",
    "chain_read_failed": "chain_read", "chain_parse_failed": "chain_parse",
    "coordinate_conversion_failed": "convert_coordinate",
    "native_result_capture_failed": "capture", "native_result_unavailable": "capture",
    "execution_unconfirmed": "execution",
}
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_SOURCE = re.compile(r"source_[a-f0-9]{24,64}\Z")
_NATIVE_FIELDS = ("target_chromosome", "target_position_0based", "target_strand", "native_chain_score")


def _require(condition, code="liftover_invalid_record"):
    if not condition:
        raise ValueError(code)


def _copy(value):
    """Preserve JSON scalar types; native tuples become ordered JSON arrays."""
    kind = type(value)
    if value is None or kind in (bool, int):
        return value
    if kind is str:
        value.encode("utf-8")
        return value
    if kind is float:
        _require(math.isfinite(value), "liftover_finite_json_required")
        return value
    if kind in (list, tuple):
        return [_copy(item) for item in value]
    if kind is dict:
        _require(all(type(key) is str for key in value), "liftover_string_keys_required")
        return {_copy(key): _copy(item) for key, item in value.items()}
    raise ValueError("liftover_finite_json_required")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _same(left, right):
    return _canonical(left) == _canonical(right)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()))


def _text(value):
    return type(value) is str and bool(value) and not any(char in value for char in "\0\r\n")


def _integer(value, minimum=None):
    return type(value) is int and (minimum is None or value >= minimum)


def _obj(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _enum(values):
    return {"enum": list(values)}


def _nullable(node):
    return {"anyOf": [node, {"type": "null"}]}


def _file_schema():
    return _obj(dict(artifact_ref={"type": "string", "pattern": "^artifact_[a-f0-9]{64}$"},
        sha256={"type": "string", "pattern": "^[a-f0-9]{64}$"}, size_bytes={"type": "integer", "minimum": 0},
        format=_enum(CHAIN_FORMATS)))


def _point_schema():
    return _obj(dict(chromosome={"type": "string", "minLength": 1,
        "description": "Exact supplied contig token; no prefix, alias, case or species normalization."},
        position_0based={"type": "integer", "minimum": 0,
            "description": "Zero-based nucleotide position relative to the forward source contig, on either strand."},
        strand=_enum(("+", "-"))))


def liftover_request_schema():
    """The initial contract has no unsupported assembly-label arguments."""
    return _obj(dict(version={"const": REQUEST_VERSION},
        chain=_obj(dict(file=_file_schema(), source_ref=_nullable({"type": "string", "pattern": "^source_[a-f0-9]{24,64}$"}))),
        point=_point_schema()))


def validate_liftover_request(value):
    value = _copy(value)
    _closed(value, "version chain point")
    _require(value["version"] == REQUEST_VERSION)
    chain = value["chain"]; _closed(chain, "file source_ref")
    file = chain["file"]; _closed(file, "artifact_ref sha256 size_bytes format")
    _require(type(file["sha256"]) is str and _SHA.fullmatch(file["sha256"])
        and file["artifact_ref"] == "artifact_" + file["sha256"]
        and _integer(file["size_bytes"], 0) and file["format"] in CHAIN_FORMATS)
    _require(chain["source_ref"] is None or type(chain["source_ref"]) is str
        and _SOURCE.fullmatch(chain["source_ref"]))
    point = value["point"]; _closed(point, "chromosome position_0based strand")
    _require(_text(point["chromosome"]) and _integer(point["position_0based"], 0)
        and point["strand"] in ("+", "-"))
    return value


def liftover_request_sha256(request):
    return hashlib.sha256(_canonical(validate_liftover_request(request)).encode("utf-8")).hexdigest()


def validate_liftover_observation(value, *, request):
    """Validate reported native-call relationships, not their authenticity.

    A known returned call with unavailable capture still has count one. An
    unconfirmed call has unknown count; neither means a measured empty result.
    Failures before conversion can have count zero even after chain parsing.
    """
    request = validate_liftover_request(request)
    value = _copy(value)
    _closed(value, "version request_sha256 chain_file software conversion_call_state conversion_call_count result_state native_result failure")
    _require(value["version"] == OBSERVATION_VERSION
        and value["request_sha256"] == liftover_request_sha256(request)
        and _same(value["chain_file"], request["chain"]["file"]), "liftover_observation_identity_conflict")
    software = value["software"]; _closed(software, "name version")
    _require(software["name"] == "pyliftover" and
        (software["version"] is None or _text(software["version"])))
    state, count = value["conversion_call_state"], value["conversion_call_count"]
    _require(state in CALL_STATES and (count is None or _integer(count, 0)))
    _require((state, count) in (("not_started", 0), ("returned", 1), ("raised", 1), ("uncertain", None)),
        "liftover_conversion_call_conflict")
    _require(value["result_state"] in ("captured", "unavailable"))
    failure = value["failure"]
    if failure is not None:
        _closed(failure, "stage code exception_type exception_message")
        _require(type(failure["code"]) is str and failure["code"] in FAILURES
            and failure["stage"] == FAILURES[failure["code"]])
        _require(all(failure[key] is None or type(failure[key]) is str
            for key in ("exception_type", "exception_message")))
    if value["result_state"] == "captured":
        _require(state == "returned" and failure is None, "liftover_captured_result_conflict")
    else:
        _require(value["native_result"] is None, "liftover_unavailable_result_conflict")
        if state == "raised":
            _require(failure is not None and failure["stage"] == "convert_coordinate")
        elif state == "not_started":
            _require(failure is None or failure["stage"] in ("input", "chain_read", "chain_parse"))
        elif state == "returned":
            _require(failure is not None and failure["stage"] == "capture")
        else:
            _require(failure is None or failure["stage"] in ("execution", "capture"))
    return value


def _interpret_native(observation):
    """One native tuple interpretation; invalid rows never shift ordinals."""
    rows, issues = [], []
    if observation["result_state"] != "captured" or observation["native_result"] is None:
        return "not_applicable", rows, issues
    native = observation["native_result"]
    if type(native) is not list:
        return "invalid", rows, [dict(code="native_result_type_invalid", row_ordinal=None)]
    predicates = (_text, lambda value: _integer(value, 0), lambda value: type(value) is str
        and value in ("+", "-"), _integer)
    codes = ("native_target_chromosome_invalid", "native_target_position_invalid",
        "native_target_strand_invalid", "native_chain_score_invalid")
    for ordinal, raw in enumerate(native):
        cells = dict.fromkeys(_NATIVE_FIELDS)
        errors = []
        if type(raw) is not list:
            errors.append("native_tuple_type_invalid")
        elif len(raw) != 4:
            errors.append("native_tuple_width_invalid")
        else:
            for name, value, predicate, code in zip(_NATIVE_FIELDS, raw, predicates, codes):
                if predicate(value):
                    cells[name] = deepcopy(value)
                else:
                    errors.append(code)
        rows.append(dict(ordinal=ordinal, state="invalid" if errors else "valid",
            **cells, qualification_codes=errors))
        issues.extend(dict(code=code, row_ordinal=ordinal) for code in errors)
    valid = sum(row["state"] == "valid" for row in rows)
    parsing = "complete" if not issues else "partial" if valid else "invalid"
    return parsing, rows, issues


def populate_liftover_sheet(request, *, native_observation):
    """Populate from the supplied original native result without converting."""
    request = validate_liftover_request(request)
    observation = validate_liftover_observation(native_observation, request=request)
    parsing, rows, issues = _interpret_native(observation)
    return dict(version=SHEET_VERSION, request=request, observation=observation,
        assembly_context=dict(source=dict(state="unavailable", label=None, reason="not_provided"),
            target=dict(state="unavailable", label=None, reason="not_provided")),
        parsing_state=parsing, rows=rows, issues=issues)


def validate_liftover_sheet(value):
    """Reject inconsistent saved copies; never repair a stored sheet."""
    value = _copy(value)
    _closed(value, "version request observation assembly_context parsing_state rows issues")
    expected = populate_liftover_sheet(value["request"], native_observation=value["observation"])
    _require(_same(value, expected), "liftover_saved_sheet_conflict")
    return value


def _population(sheet):
    """One full-native-population calculator, independent of row selection.

    requested_point_count is the one declared point, not successful work.
    native_row_count counts actual returned array entries, including malformed
    entries. mapping_count is exact only for a completely valid returned list;
    valid_mapping_count reports parsed valid occurrences without a completeness
    claim. None/unavailable results never become observed zero mappings.
    """
    observation = sheet["observation"]
    state = observation["conversion_call_state"]
    count = valid = mapping_count = None
    if state != "returned":
        point_state = dict(not_started="not_started", raised="conversion_failed", uncertain="execution_unconfirmed")[state]
    elif observation["result_state"] != "captured":
        point_state = "result_unavailable"
    elif observation["native_result"] is None:
        point_state = "chromosome_not_in_chain"
    elif type(observation["native_result"]) is not list:
        point_state = "native_result_invalid"
    else:
        count = len(sheet["rows"])
        valid = sum(row["state"] == "valid" for row in sheet["rows"])
        if sheet["parsing_state"] != "complete":
            point_state = "native_rows_invalid"
        else:
            mapping_count = count
            point_state = "unmapped_under_selected_chain" if count == 0 else "unique" if count == 1 else "multiple"
    return dict(requested_point_count=1, point_state=point_state, native_row_count=count,
        valid_mapping_count=valid, mapping_count=mapping_count, mapping_count_scope="full_native_return",
        conversion_call_scope=CALL_SCOPE, conversion_call_state=state,
        conversion_call_count=observation["conversion_call_count"])


def _components(sheet, mapping_ordinals):
    if mapping_ordinals is None:
        mapping_ordinals = list(range(len(sheet["rows"])))
    else:
        _require(type(mapping_ordinals) is list and all(_integer(i, 0) and i < len(sheet["rows"])
            for i in mapping_ordinals) and len(mapping_ordinals) == len(set(mapping_ordinals)),
            "liftover_mapping_ordinal_invalid")
    return dict(version=COMPONENTS_VERSION, sheet=deepcopy(sheet),
        selection=dict(mapping_ordinals=list(mapping_ordinals)), population=_population(sheet),
        rows=[deepcopy(sheet["rows"][i]) for i in mapping_ordinals])


def calculate_liftover_components(sheet, *, mapping_ordinals=None):
    """Calculate from saved data; selection never reclassifies multiplicity."""
    return _components(validate_liftover_sheet(sheet), mapping_ordinals)


def validate_liftover_components(value):
    value = _copy(value)
    _closed(value, "version sheet selection population rows")
    _closed(value["selection"], "mapping_ordinals")
    sheet = validate_liftover_sheet(value["sheet"])
    expected = _components(sheet, value["selection"]["mapping_ordinals"])
    _require(_same(value, expected), "liftover_saved_components_conflict")
    return value


def project_liftover_return(components, *, source_ref):
    """Return literal cells and Source identity, without output File grants."""
    components = validate_liftover_components(components)
    _require(type(source_ref) is str and _SOURCE.fullmatch(source_ref), "liftover_return_reference_invalid")
    sheet = components["sheet"]
    failure = sheet["observation"]["failure"]
    return dict(version=RETURN_VERSION, source_ref=source_ref, chain=deepcopy(sheet["request"]["chain"]),
        point=deepcopy(sheet["request"]["point"]), assembly_context=deepcopy(sheet["assembly_context"]),
        population=deepcopy(components["population"]), parsing_state=sheet["parsing_state"],
        selected_mapping_ordinals=deepcopy(components["selection"]["mapping_ordinals"]),
        rows=deepcopy(components["rows"]), issues=deepcopy(sheet["issues"]),
        failure=None if failure is None else dict(stage=failure["stage"], code=failure["code"],
            location_code="native_failure", occurrence=0))


def liftover_fact_sources():
    """An UNREGISTERED closed source-owned schema, not a commissioned tool."""
    text = {"type": "string"}
    integer = {"type": "integer"}
    count = {"type": "integer", "minimum": 0}
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    issue = _obj(dict(code=_enum(ISSUES), row_ordinal=_nullable(count)))
    unknown = _obj(dict(state={"const": "unavailable"}, label={"type": "null"}, reason={"const": "not_provided"}))
    row = _obj(dict(ordinal={**count, "description": "Original zero-based row index in the full native returned list."},
        state=_enum(("valid", "invalid")), target_chromosome=_nullable(text),
        target_position_0based={**_nullable(count), "description":
            "Literal zero-based nucleotide position relative to the forward target contig on either strand."},
        target_strand=_enum(("+", "-", None)),
        native_chain_score={**_nullable(integer), "description": "Literal native chain alignment score; no probability or uncertainty claim."},
        qualification_codes={"type": "array", "items": _enum(ISSUES)}))
    population = _obj(dict(requested_point_count={"type": "integer", "const": 1}, point_state=_enum(POINT_STATES),
        native_row_count=_nullable(count), valid_mapping_count=_nullable(count), mapping_count=_nullable(count),
        mapping_count_scope={"const": "full_native_return"}, conversion_call_scope={"const": CALL_SCOPE},
        conversion_call_state=_enum(CALL_STATES), conversion_call_count=_nullable({"type": "integer", "minimum": 0, "maximum": 1})))
    returned = _obj(dict(version={"const": RETURN_VERSION}, source_ref=source,
        chain=_obj(dict(file=_file_schema(), source_ref=_nullable(source))),
        point=_point_schema(), assembly_context=_obj(dict(source=unknown, target=deepcopy(unknown))),
        population=population, parsing_state=_enum(("not_applicable", "complete", "partial", "invalid")),
        selected_mapping_ordinals={"type": "array", "items": count, "uniqueItems": True},
        rows={"type": "array", "items": row}, issues={"type": "array", "items": issue},
        failure=_nullable(_obj(dict(stage=_enum(tuple(dict.fromkeys(FAILURES.values()))), code=_enum(FAILURES),
            location_code={"const": "native_failure"}, occurrence={"type": "integer", "const": 0})))))
    return {FACT_SOURCE: dict(type="array", meaning=(
        "Exact retained point-liftover mappings and full-native-population qualifications. Native tuple order, "
        "literal contigs, zero-based positions, strands and alignment scores are preserved. Unknown assembly labels "
        "and unknown/empty/failed results remain distinct; row selection is not a unique-mapping claim."),
        report_schema={"type": "array", "items": returned, "x-source": FACT_SOURCE})}


def validate_liftover_return(value, *, components):
    """Compare source-owned JSON to stored components; refs are shape-only here."""
    value = _copy(value)
    _require(type(value) is dict, "liftover_saved_return_conflict")
    expected = project_liftover_return(components, source_ref=value.get("source_ref"))
    _require(_same(value, expected), "liftover_saved_return_conflict")
    return value


__all__ = ["REQUEST_VERSION", "OBSERVATION_VERSION", "SHEET_VERSION", "COMPONENTS_VERSION", "RETURN_VERSION",
    "FACT_SOURCE", "CALL_SCOPE", "CHAIN_FORMATS", "liftover_request_schema", "validate_liftover_request",
    "liftover_request_sha256", "validate_liftover_observation", "populate_liftover_sheet", "validate_liftover_sheet",
    "calculate_liftover_components", "validate_liftover_components", "project_liftover_return",
    "liftover_fact_sources", "validate_liftover_return"]
