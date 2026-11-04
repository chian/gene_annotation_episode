"""Literal AlphaFold prediction metadata and explicitly advertised file choices.

These helpers neither acquire data nor establish Source authority. The caller
authenticates original metadata bytes before selecting an advertised file.
Native field names and model/version meanings remain uninterpreted.
"""
from copy import deepcopy
import hashlib
import json
import math
import re
from urllib.parse import quote, urlsplit

from jsonschema import Draft202012Validator, validators

from .acquisition import SourceSnapshot
from .data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt
from .protein_structure_contracts import validate_file_identity


SERVICE = "alphafold"
PREDICTION_ROOT = "https://alphafold.ebi.ac.uk/api/prediction/"
FILE_FORMATS = {"pdb_3x_text": "pdb", "pdbx_mmcif_text": "cif"}
OFFICIAL_FILE_HOSTS = ("alphafold.ebi.ac.uk", "www.alphafold.ebi.ac.uk")
_SOURCE = {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$",
    "format": "reference", "x-reference-namespace": "source"}
_ARTIFACT = {"type": "string", "pattern": "^artifact_[a-f0-9]{64}$",
    "format": "reference", "x-reference-namespace": "artifact"}
_COUNT = {"type": "integer", "minimum": 0}
_POINTER = {"type": "string", "pattern": "^(?:/(?:[^~]|~[01])*)*$"}


def _object(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _owned(schema):
    resource = deepcopy(schema)
    resource["$id"] = "urn:gene-annotation:alphafold:" + hashlib.sha256(
        json.dumps(resource, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    document = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
        "$defs": deepcopy(resource.get("$defs", {})), "allOf": [resource]}
    document["$id"] = "urn:gene-annotation:alphafold:" + hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return document


ALPHAFOLD_PREDICTION_ARGUMENTS_SCHEMA = _object(dict(
    identifier={"type": "string", "pattern": "^[A-Za-z0-9_-]+$"},
    max_bytes={"type": "integer", "minimum": 1}))
ALPHAFOLD_FILE_ARGUMENTS_SCHEMA = _object(dict(metadata_source_ref=deepcopy(_SOURCE),
    url_pointer=deepcopy(_POINTER), file_format={"enum": list(FILE_FORMATS)},
    max_bytes={"type": "integer", "minimum": 1}))
ALPHAFOLD_FILE_ASSOCIATION_SCHEMA = _object(dict(
    version={"const": "alphafold_advertised_file_association_v1"},
    metadata_source_ref=deepcopy(_SOURCE), metadata_artifact_ref=deepcopy(_ARTIFACT),
    url_pointer=deepcopy(_POINTER), advertised_url={"type": "string"},
    file_format={"enum": list(FILE_FORMATS)}))
_JSON = {"anyOf": [{"type": "null"}, {"type": "boolean"}, {"type": "number"}, {"type": "string"},
    {"type": "array", "items": {"$ref": "#/$defs/NativeJSON"}},
    {"type": "object", "additionalProperties": {"$ref": "#/$defs/NativeJSON"}}]}
_RESPONSE = _object(dict(http_status={"type": ["integer", "null"], "minimum": 100, "maximum": 599},
    content_type={"type": ["string", "null"]}, body_complete={"type": ["boolean", "null"]},
    retained_bytes=deepcopy(_COUNT), observed_body_bytes={"type": ["integer", "null"], "minimum": 0},
    declared_body_bytes={"type": ["integer", "null"], "minimum": 0}))
_ISSUES = dict(type="array", uniqueItems=True, items=_object(dict(
    code={"enum": ["invalid_native_json", "http_not_success", "response_incomplete", "transport_metadata_unavailable"]},
    pointer=deepcopy(_POINTER))))
_FILE = _object(dict(artifact_ref=deepcopy(_ARTIFACT), sha256={"type": "string", "pattern": "^[a-f0-9]{64}$"},
    byte_length=deepcopy(_COUNT), format={"enum": list(FILE_FORMATS)}))
ALPHAFOLD_PREDICTION_RESULT_SCHEMA = _owned({"$defs": {"NativeJSON": _JSON}, **_object(dict(
    version={"const": "alphafold_prediction_result_v1"}, source_ref=deepcopy(_SOURCE),
    raw_artifact_ref=deepcopy(_ARTIFACT), requested=deepcopy(ALPHAFOLD_PREDICTION_ARGUMENTS_SCHEMA),
    response=deepcopy(_RESPONSE), parse_state={"enum": ["object", "array", "scalar", "native_null", "decode_failed"]},
    native_json={"$ref": "#/$defs/NativeJSON"}, issues=deepcopy(_ISSUES)))})
ALPHAFOLD_PREDICTION_VALUE_SCHEMA = _owned({"$defs": {"NativeJSON": _JSON}, **_object(dict(
    version={"const": "alphafold_prediction_value_v1"}, raw_artifact_ref=deepcopy(_ARTIFACT),
    requested=deepcopy(ALPHAFOLD_PREDICTION_ARGUMENTS_SCHEMA), response=deepcopy(_RESPONSE),
    parse_state={"enum": ["object", "array", "scalar", "native_null", "decode_failed"]},
    native_json={"$ref": "#/$defs/NativeJSON"}, issues=deepcopy(_ISSUES)))})
ALPHAFOLD_FAILURE_CODES = (
    "invalid_tool_input", "data_acquisition_failed", "data_acquisition_publication_incomplete",
    "alphafold_request_conflict", "alphafold_http_not_success", "alphafold_response_incomplete",
    "alphafold_transport_metadata_unavailable", "alphafold_invalid_native_json",
    "alphafold_prediction_identity_conflict", "alphafold_prediction_identity_unavailable",
    "alphafold_file_metadata_not_received", "alphafold_file_selection_conflict",
    "alphafold_saved_outcome_conflict",
)
ALPHAFOLD_FILE_RESULT_SCHEMA = _object(dict(version={"const": "alphafold_file_result_v1"},
    source_ref=deepcopy(_SOURCE), file=deepcopy(_FILE), requested=deepcopy(ALPHAFOLD_FILE_ARGUMENTS_SCHEMA),
    response=deepcopy(_RESPONSE), association=deepcopy(ALPHAFOLD_FILE_ASSOCIATION_SCHEMA),
    observed_identity=_object(dict(native_model_id={"type": "null"}, state={"const": "not_parsed"})),
    issues=deepcopy(_ISSUES)))
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER
    .redefine("integer", lambda _, value: type(value) is int)
    .redefine("number", lambda _, value: type(value) is int or type(value) is float and math.isfinite(value)))


def _require(condition, code="alphafold_value_invalid"):
    if not condition:
        raise ValueError(code)


def _exact_reference(value, namespace):
    pattern = {"source": r"source_[a-f0-9]{24,64}", "artifact": r"artifact_[a-f0-9]{64}"}[namespace]
    _require(re.fullmatch(pattern, value, re.ASCII) is not None)


def _plain(value):
    if type(value) is dict:
        _require(all(type(key) is str for key in value))
        for key, child in value.items():
            key.encode("utf-8")
            _plain(child)
    elif type(value) is list:
        for child in value:
            _plain(child)
    elif type(value) is float:
        _require(math.isfinite(value))
    else:
        _require(type(value) in (str, int, bool, type(None)))
    if type(value) is str:
        value.encode("utf-8")


def _validated(value, schema):
    try:
        _plain(value)
        _require(_STRICT(schema).is_valid(value))
    except (TypeError, KeyError, IndexError, OverflowError, RecursionError, UnicodeError) as error:
        raise ValueError("alphafold_value_invalid") from error
    return deepcopy(value)


def validate_alphafold_prediction_arguments(arguments):
    value = _validated(arguments, ALPHAFOLD_PREDICTION_ARGUMENTS_SCHEMA)
    _require(re.fullmatch(r"[A-Za-z0-9_-]+", value["identifier"], re.ASCII) is not None)
    return value


def validate_alphafold_file_arguments(arguments):
    value = _validated(arguments, ALPHAFOLD_FILE_ARGUMENTS_SCHEMA)
    _exact_reference(value["metadata_source_ref"], "source")
    _require(re.fullmatch(r"(?:/(?:[^~]|~[01])*)*", value["url_pointer"]) is not None)
    return value


def alphafold_prediction_url(identifier):
    validate_alphafold_prediction_arguments(dict(identifier=identifier, max_bytes=1))
    return PREDICTION_ROOT + quote(identifier, safe="")


def _decode(raw):
    _require(type(raw) is bytes, "alphafold_metadata_bytes_required")
    def pairs(items):
        result = {}
        for name, value in items:
            _require(name not in result, "invalid_native_json")
            result[name] = value
        return result
    def nonfinite(value):
        raise ValueError("invalid_native_json")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
    _plain(value)
    return value


def _advertised_file_url(url, file_format):
    _require(type(url) is str, "alphafold_advertised_file_url_invalid")
    _require(not any(character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in url) and "\\" not in url, "alphafold_advertised_file_url_invalid")
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == "https" and parsed.hostname in OFFICIAL_FILE_HOSTS
            and parsed.username is None and parsed.password is None and parsed.port in (None, 443)
            and not parsed.fragment and re.fullmatch(r"/files/[A-Za-z0-9_.-]+\." + FILE_FORMATS[file_format],
                parsed.path, re.ASCII) is not None)
    except (ValueError, KeyError) as error:
        raise ValueError("alphafold_advertised_file_url_invalid") from error
    _require(valid, "alphafold_advertised_file_url_invalid")
    return url


def validate_alphafold_file_association(value, *, arguments=None):
    value = _validated(value, ALPHAFOLD_FILE_ASSOCIATION_SCHEMA)
    _exact_reference(value["metadata_source_ref"], "source")
    _exact_reference(value["metadata_artifact_ref"], "artifact")
    _advertised_file_url(value["advertised_url"], value["file_format"])
    _require(re.fullmatch(r"(?:/(?:[^~]|~[01])*)*", value["url_pointer"]) is not None)
    if arguments is not None:
        arguments = validate_alphafold_file_arguments(arguments)
        _require(all(value[key] == arguments[key] for key in ("metadata_source_ref", "url_pointer", "file_format")),
            "alphafold_file_association_conflict")
    return value


def alphafold_advertised_file_url(native_json, *, arguments):
    """Select a literal URL from an already authenticated decoded native value."""
    arguments = validate_alphafold_file_arguments(arguments)
    try:
        _plain(native_json)
        selected = native_json
        pointer = arguments["url_pointer"]
        for token in ([] if pointer == "" else pointer[1:].split("/")):
            token = token.replace("~1", "/").replace("~0", "~")
            if type(selected) is dict:
                _require(token in selected, "alphafold_url_pointer_unresolved")
                selected = selected[token]
            elif type(selected) is list:
                _require(re.fullmatch(r"0|[1-9][0-9]*", token, re.ASCII) is not None,
                    "alphafold_url_pointer_unresolved")
                index = int(token)
                _require(index < len(selected), "alphafold_url_pointer_unresolved")
                selected = selected[index]
            else:
                raise ValueError("alphafold_url_pointer_unresolved")
        return _advertised_file_url(selected, arguments["file_format"])
    except (UnicodeError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("alphafold_metadata_invalid") from error


def resolve_alphafold_file_selection(metadata_raw, *, arguments):
    """Select one literal URL; the caller must authenticate these original bytes."""
    arguments = validate_alphafold_file_arguments(arguments)
    try:
        native = _decode(metadata_raw)
    except (UnicodeError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError("alphafold_metadata_invalid") from error
    url = alphafold_advertised_file_url(native, arguments=arguments)
    association = validate_alphafold_file_association(dict(version="alphafold_advertised_file_association_v1",
        metadata_source_ref=arguments["metadata_source_ref"],
        metadata_artifact_ref="artifact_" + hashlib.sha256(metadata_raw).hexdigest(),
        url_pointer=arguments["url_pointer"], advertised_url=url, file_format=arguments["file_format"]), arguments=arguments)
    return dict(url=url, association=association)


def _issue(code, pointer):
    return dict(code=code, pointer=pointer)


def _response(snapshot, arguments, url, validator):
    _require(isinstance(snapshot, SourceSnapshot) and snapshot.service == SERVICE
        and type(snapshot.content) is bytes and snapshot.url == url
        and type(snapshot.request) is dict and validator(snapshot.request) == arguments,
        "alphafold_snapshot_request_conflict")
    _require(len(snapshot.content) <= arguments["max_bytes"], "alphafold_snapshot_byte_limit_conflict")
    metadata = snapshot.transport
    _require(type(metadata) is dict, "alphafold_transport_invalid")
    request = metadata.get("request")
    _require(type(request) is dict and request.get("method") == "GET" and request.get("url") == url,
        "alphafold_snapshot_request_conflict")
    return _response_metadata(metadata, len(snapshot.content), arguments["max_bytes"])


def _response_metadata(metadata, retained_bytes, max_bytes):
    """The same response qualification for live bytes and authenticated controls."""
    _require(type(metadata) is dict, "alphafold_transport_invalid")
    issues = []
    headers = metadata.get("headers")
    content_type = headers.get("content-type") if type(headers) is dict else None
    if content_type is not None and type(content_type) is not str:
        content_type = None
        issues.append(_issue("transport_metadata_unavailable", "/response/content_type"))
    status = metadata.get("status")
    if type(status) is not int or not 100 <= status <= 599:
        status = None
        issues.append(_issue("transport_metadata_unavailable", "/response/http_status"))
    elif not 200 <= status < 300:
        issues.append(_issue("http_not_success", "/response/http_status"))
    complete = metadata.get("body_complete")
    if type(complete) is not bool:
        complete = None
        issues.append(_issue("transport_metadata_unavailable", "/response/body_complete"))
    if complete is not True:
        issues.append(_issue("response_incomplete", "/response/body_complete"))
    counts = {}
    for field in ("observed_body_bytes", "declared_body_bytes"):
        value = metadata.get(field)
        if value is not None and (type(value) is not int or value < 0):
            value = None
            issues.append(_issue("transport_metadata_unavailable", "/response/" + field))
        counts[field] = value
    for original, pointer, expected in (("retained_body_bytes", "/response/retained_bytes", retained_bytes),
            ("response_byte_limit", "/requested/max_bytes", max_bytes)):
        if type(metadata.get(original)) is not int or metadata[original] != expected:
            issues.append(_issue("transport_metadata_unavailable", pointer))
    return dict(http_status=status, content_type=content_type, body_complete=complete,
        retained_bytes=retained_bytes, **counts), issues


def _artifact(snapshot, artifact_ref):
    _require(artifact_ref == "artifact_" + hashlib.sha256(snapshot.content).hexdigest(),
        "alphafold_artifact_identity_conflict")
    return artifact_ref


def alphafold_prediction_result(snapshot, *, arguments, source_ref, artifact_ref):
    return alphafold_prediction_result_from_value(alphafold_prediction_value(snapshot,
        arguments=arguments, artifact_ref=artifact_ref), source_ref=source_ref)


def alphafold_prediction_value(snapshot, *, arguments, artifact_ref):
    """Validate one literal reply without manufacturing a producing Source."""
    arguments = validate_alphafold_prediction_arguments(arguments)
    response, issues = _response(snapshot, arguments, alphafold_prediction_url(arguments["identifier"]),
        validate_alphafold_prediction_arguments)
    artifact_ref = _artifact(snapshot, artifact_ref)
    try:
        native = _decode(snapshot.content)
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
        native, state = None, "decode_failed"
        issues.append(_issue("invalid_native_json", "/native_json"))
    else:
        state = ("object" if type(native) is dict else "array" if type(native) is list else
            "native_null" if native is None else "scalar")
    return validate_alphafold_prediction_value(dict(version="alphafold_prediction_value_v1",
        raw_artifact_ref=artifact_ref, requested=arguments, response=response,
        parse_state=state, native_json=native, issues=issues))


def alphafold_prediction_result_from_value(value, *, source_ref):
    value = validate_alphafold_prediction_value(value)
    return validate_alphafold_prediction_result({**value,
        "version": "alphafold_prediction_result_v1", "source_ref": source_ref})


def alphafold_file_result(snapshot, *, arguments, association, source_ref, artifact_ref):
    arguments = validate_alphafold_file_arguments(arguments)
    association = validate_alphafold_file_association(association, arguments=arguments)
    response, issues = _response(snapshot, arguments, association["advertised_url"], validate_alphafold_file_arguments)
    artifact_ref = _artifact(snapshot, artifact_ref)
    file = dict(artifact_ref=artifact_ref, sha256=hashlib.sha256(snapshot.content).hexdigest(),
        byte_length=len(snapshot.content), format=arguments["file_format"])
    validate_file_identity(file)
    return validate_alphafold_file_result(dict(version="alphafold_file_result_v1", source_ref=source_ref,
        file=file, requested=arguments, response=response, association=association,
        observed_identity=dict(native_model_id=None, state="not_parsed"), issues=issues))


def _validate_response_issues(value):
    response, issues = value["response"], value["issues"]
    _require(response["retained_bytes"] <= value["requested"]["max_bytes"])
    pairs = {(row["code"], row["pointer"]) for row in issues}
    status = response["http_status"]
    _require((("http_not_success", "/response/http_status") in pairs)
        == (status is not None and not 200 <= status < 300))
    _require((("response_incomplete", "/response/body_complete") in pairs)
        == (response["body_complete"] is not True))
    for field in ("http_status", "body_complete"):
        if response[field] is None:
            _require(("transport_metadata_unavailable", "/response/" + field) in pairs)
    allowed = {("http_not_success", "/response/http_status"), ("response_incomplete", "/response/body_complete"),
        ("invalid_native_json", "/native_json"), ("transport_metadata_unavailable", "/requested/max_bytes")}
    allowed.update(("transport_metadata_unavailable", "/response/" + field) for field in response)
    _require(pairs <= allowed)
    for code, pointer in pairs:
        if code == "transport_metadata_unavailable" and pointer not in ("/requested/max_bytes", "/response/retained_bytes"):
            _require(response[pointer.rsplit("/", 1)[1]] is None)


def validate_alphafold_prediction_result(value):
    value = _validated(value, ALPHAFOLD_PREDICTION_RESULT_SCHEMA)
    _exact_reference(value["source_ref"], "source")
    _validate_prediction_content(value)
    return value


def validate_alphafold_prediction_value(value):
    value = _validated(value, ALPHAFOLD_PREDICTION_VALUE_SCHEMA)
    _validate_prediction_content(value)
    return value


def _validate_prediction_content(value):
    _exact_reference(value["raw_artifact_ref"], "artifact")
    validate_alphafold_prediction_arguments(value["requested"])
    _validate_response_issues(value)
    native, state = value["native_json"], value["parse_state"]
    expected = ("object" if type(native) is dict else "array" if type(native) is list else
        "native_null" if native is None else "scalar")
    _require(state == expected or state == "decode_failed" and native is None)
    _require(any(row["code"] == "invalid_native_json" for row in value["issues"]) == (state == "decode_failed"))


def validate_alphafold_file_result(value):
    value = _validated(value, ALPHAFOLD_FILE_RESULT_SCHEMA)
    _exact_reference(value["source_ref"], "source")
    validate_alphafold_file_arguments(value["requested"])
    validate_alphafold_file_association(value["association"], arguments=value["requested"])
    validate_file_identity(value["file"])
    _validate_response_issues(value)
    _require(value["file"]["format"] == value["requested"]["file_format"]
        and value["file"]["byte_length"] == value["response"]["retained_bytes"]
        and value["file"]["artifact_ref"] == "artifact_" + value["file"]["sha256"])
    _require(not any(row["code"] == "invalid_native_json" for row in value["issues"]))
    return value


def alphafold_receipt_schema():
    return acquisition_receipt_schema(failure_codes=ALPHAFOLD_FAILURE_CODES)


def validate_alphafold_receipt(value):
    return validate_acquisition_receipt(value, failure_codes=ALPHAFOLD_FAILURE_CODES,
        invalid_code="alphafold_receipt_invalid")


def failed_alphafold_receipt(code, *, source_ref=None):
    return validate_alphafold_receipt(dict(acquired=False, source_ref=source_ref,
        data_ref=None, failure_code=code))


def _response_failure(value):
    codes = {row["code"] for row in value["issues"]}
    for code in ("http_not_success", "transport_metadata_unavailable", "response_incomplete", "invalid_native_json"):
        if code in codes:
            return "alphafold_" + code
    response = value["response"]
    if any(response[key] is not None and response[key] != response["retained_bytes"]
            for key in ("observed_body_bytes", "declared_body_bytes")):
        return "alphafold_response_incomplete"
    return None


def alphafold_prediction_identity(value):
    """Confirm every original row's explicit UniProt identity, never select a model.

    The official prediction API is keyed on UniProt accession. entryId and
    modelEntityId are documented renamed aliases, not alternate request keys.
    """
    value = validate_alphafold_prediction_value(value)
    rows, requested = value["native_json"], value["requested"]["identifier"]
    if type(rows) is not list or not rows:
        return "unavailable"
    unavailable = False
    for row in rows:
        if type(row) is not dict:
            unavailable = True
            continue
        accession = row.get("uniprotAccession")
        if type(accession) is not str or not accession:
            unavailable = True
        elif accession != requested:
            return "conflict"
        # Optional renamed fields can be unavailable independently of the
        # explicit UniProt accession. Only observed non-null aliases can
        # contradict one another; their absence/null is not such a conflict.
        aliases = [row[key] for key in ("entryId", "modelEntityId") if row.get(key) is not None]
        if any(type(alias) is not str or not alias for alias in aliases):
            unavailable = True
        elif len(aliases) == 2 and aliases[0] != aliases[1]:
            return "conflict"
    return "unavailable" if unavailable else "confirmed"


def alphafold_prediction_receipt(value, *, source_ref):
    value = validate_alphafold_prediction_value(value)
    failure = _response_failure(value)
    if failure is None:
        state = alphafold_prediction_identity(value)
        failure = None if state == "confirmed" else "alphafold_prediction_identity_" + state
    if failure is not None:
        return failed_alphafold_receipt(failure, source_ref=source_ref)
    return validate_alphafold_receipt(dict(acquired=True, source_ref=source_ref,
        data_ref=value["raw_artifact_ref"], failure_code=None))


def alphafold_file_receipt(value):
    value = validate_alphafold_file_result(value)
    failure = _response_failure(value)
    if failure is not None:
        return failed_alphafold_receipt(failure, source_ref=value["source_ref"])
    return validate_alphafold_receipt(dict(acquired=True, source_ref=value["source_ref"],
        data_ref=value["file"]["artifact_ref"], failure_code=None))


__all__ = ["SERVICE", "PREDICTION_ROOT", "FILE_FORMATS", "OFFICIAL_FILE_HOSTS",
    "ALPHAFOLD_PREDICTION_ARGUMENTS_SCHEMA", "ALPHAFOLD_FILE_ARGUMENTS_SCHEMA",
    "ALPHAFOLD_FILE_ASSOCIATION_SCHEMA", "ALPHAFOLD_PREDICTION_RESULT_SCHEMA", "ALPHAFOLD_FILE_RESULT_SCHEMA",
    "validate_alphafold_prediction_arguments", "validate_alphafold_file_arguments", "alphafold_prediction_url",
    "resolve_alphafold_file_selection", "alphafold_advertised_file_url", "validate_alphafold_file_association",
    "alphafold_prediction_result", "alphafold_file_result",
    "validate_alphafold_prediction_result", "validate_alphafold_file_result",
    "ALPHAFOLD_PREDICTION_VALUE_SCHEMA", "ALPHAFOLD_FAILURE_CODES", "alphafold_receipt_schema",
    "validate_alphafold_receipt", "failed_alphafold_receipt", "alphafold_prediction_value",
    "validate_alphafold_prediction_value", "alphafold_prediction_result_from_value",
    "alphafold_prediction_identity", "alphafold_prediction_receipt", "alphafold_file_receipt"]
