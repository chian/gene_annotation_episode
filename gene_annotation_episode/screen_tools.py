"""One explicit SCREEN getmaxZScoresQuery acquisition, without analysis.

Query examples: https://console.wenglab.org/docs/queries/ccres and
https://console.wenglab.org/docs/queries/ccre-genesdetails. Nullable result
structure is also declared by the official SCREEN3.0 generated client.
Coordinate basis, release, completeness and gene-link semantics are not
inferred from acquired values. Credentials belong to PublicClients only.
"""
import base64
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
import math

from .acquisition import AcquisitionError, SourceSnapshot
from .data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt
from .domain import ContractError


TOOL = "public.screen"
ROOT = "https://screen.api.wenglab.org/graphql"
REQUEST_VERSION = "screen_acquisition_request_v1"
MAX_BYTES = 8 * 1024 ** 2
FIELDS = ("accession", "chromosome", "start", "stop", "ccre_group",
    "atac_max_zscore", "ctcf_max_zscore", "dnase_max_zscore",
    "h3k27ac_max_zscore", "h3k4me3_max_zscore", "nearestgenes")
FAILURE_CODES = (
    "screen_arguments_invalid", "screen_timeout_invalid", "screen_snapshot_invalid", "screen_receipt_invalid",
    "screen_selected_request_mismatch", "screen_transport_invalid", "screen_transfer_policy_mismatch",
    "screen_http_status_unavailable", "screen_http_not_successful", "screen_partial_response",
    "screen_capture_incomplete", "screen_capture_identity_mismatch", "screen_content_encoding_unsupported",
    "screen_native_representation_invalid", "screen_graphql_errors", "screen_native_result_unavailable",
    "screen_credential_unavailable", "screen_credential_invalid", "screen_credential_resolution_failed",
    "provider_authentication_echo_rejected", "provider_authenticated_request_failed",
    "provider_connection_failed", "provider_request_timeout", "adapter_execution_failed",
    "invalid_tool_input", "representation_error", "data_acquisition_publication_incomplete",
    "data_acquisition_failed",
)


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


_TEXT = {"type": "string", "minLength": 1, "maxLength": 4096}
_COORDINATE = _object({"chromosome": deepcopy(_TEXT), "start": {"type": "integer"}, "end": {"type": "integer"}})
ARGUMENTS_SCHEMA = _object({"assembly": deepcopy(_TEXT),
    "accessions": {"type": ["array", "null"], "items": deepcopy(_TEXT), "minItems": 1},
    "coordinates": {"type": ["array", "null"], "items": _COORDINATE, "minItems": 1},
    "fields": {"type": "array", "items": {"enum": list(FIELDS)}, "minItems": 1, "uniqueItems": True},
    "max_bytes": {"type": "integer", "minimum": 1, "maximum": MAX_BYTES}})
ARGUMENTS_SCHEMA["oneOf"] = [
    {"properties": {"accessions": {"type": "array"}, "coordinates": {"type": "null"}}},
    {"properties": {"accessions": {"type": "null"}, "coordinates": {"type": "array"}}},
]


def _text(value):
    if (type(value) is not str or not 1 <= len(value) <= 4096
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def validate_screen_arguments(arguments):
    def require(condition):
        if not condition:
            raise ContractError("screen_arguments_invalid")
    require(type(arguments) is dict and set(arguments) == {"assembly", "accessions", "coordinates", "fields", "max_bytes"})
    require(_text(arguments["assembly"]))
    require(type(arguments["max_bytes"]) is int and 1 <= arguments["max_bytes"] <= MAX_BYTES)
    require(type(arguments["fields"]) is list and bool(arguments["fields"]))
    require(all(type(field) is str and field in FIELDS for field in arguments["fields"]))
    require(len(arguments["fields"]) == len(set(arguments["fields"])))
    accessions, coordinates = arguments["accessions"], arguments["coordinates"]
    require((accessions is None) != (coordinates is None))
    if accessions is not None:
        require(type(accessions) is list and bool(accessions) and all(_text(item) for item in accessions))
    else:
        require(type(coordinates) is list and bool(coordinates))
        for row in coordinates:
            require(type(row) is dict and set(row) == {"chromosome", "start", "end"})
            require(_text(row["chromosome"]) and type(row["start"]) is int and type(row["end"]) is int)
    return deepcopy(arguments)


def screen_request_spec(arguments):
    value = validate_screen_arguments(arguments)
    literal = lambda item: json.dumps(item, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    if value["accessions"] is not None:
        selector = "accession: " + literal(value["accessions"])
    else:
        selector = "coordinates: [" + ",".join("{start: " + str(row["start"]) + ",end: "
            + str(row["end"]) + ",chromosome: " + literal(row["chromosome"]) + "}"
            for row in value["coordinates"]) + "]"
    fields = ["nearestgenes { distance gene }" if field == "nearestgenes" else field for field in value["fields"]]
    query = "query { getmaxZScoresQuery(assembly: " + literal(value["assembly"]) + ", " + selector + ") { " + " ".join(fields) + " } }"
    body = literal({"query": query}).encode("ascii")
    return {"service": "screen", "url": ROOT, "params": {}, "media_type": "application/json",
        "body": body, "content_type": "application/json", "accept": "application/json",
        "max_bytes": value["max_bytes"], "follow_redirects": False}


def screen_receipt_schema():
    return acquisition_receipt_schema(failure_codes=FAILURE_CODES)


def validate_screen_receipt(value):
    return validate_acquisition_receipt(value, failure_codes=FAILURE_CODES, invalid_code="screen_receipt_invalid")


def screen_tool_contract():
    return {"name": TOOL, "resources": "api", "description":
        "Acquire explicitly selected SCREEN cCRE locations, native maximum z-scores and nearby-gene data for later analysis.",
        "input_schema": deepcopy(ARGUMENTS_SCHEMA), "instructions":
        "Supply assembly and exactly one ordered selector: accessions or coordinates, with the other null. "
        "Coordinates contain the native chromosome, start and end literals; their coordinate basis is not inferred. "
        "Select an ordered fields list from the advertised fields. nearestgenes requests native distance and gene fields; "
        "nearby genes are not established regulatory targets. Each call sends one getmaxZScoresQuery request without "
        "pagination, discovery, automatic selection, redirects or another query. Set max_bytes explicitly, up to 8 MiB. "
        "The host supplies any required key privately. The receipt contains only acquired, source_ref, data_ref and "
        "failure_code. Success delivers the Source and unchanged native JSON File, including native order and nulls; "
        "an empty list is data. Captured failures retain their Source without a data File. Release, total population, "
        "pagination completeness, coordinate conventions and distance conventions remain unestablished. "
        "This getter performs no analysis or scientific scoring."}


def _timeout(client):
    value = getattr(client, "timeout", None)
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ContractError("screen_timeout_invalid")
    return value


def _equal(first, second):
    try:
        return json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(second, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False


def request_screen(client, arguments):
    value = validate_screen_arguments(arguments)
    spec = screen_request_spec(value)
    timeout = _timeout(client)
    token = client._screen_bearer_token()
    conflict = False
    try:
        snapshot = client._http(**spec, timeout_seconds=timeout, bearer_token=token)
    except AcquisitionError as error:
        if not isinstance(error.snapshot, SourceSnapshot) or type(error.snapshot.content) is not bytes:
            raise
        snapshot = error.snapshot
    except ValueError as error:
        if str(error) not in {"http_bearer_request_conflict", "invalid_http_bearer_token"}:
            raise
        conflict = True
    if conflict:
        raise AcquisitionError("provider_authentication_echo_rejected", phase="http_request")
    if not isinstance(snapshot, SourceSnapshot) or type(snapshot.content) is not bytes:
        raise AcquisitionError("screen_snapshot_invalid", phase="http_response")
    return replace(snapshot, request={"version": REQUEST_VERSION, "arguments": value,
        "native_request": deepcopy(snapshot.request)})


def _association_failure(snapshot, value, *, timeout):
    spec = screen_request_spec(value)
    expected = {"version": REQUEST_VERSION, "arguments": value, "native_request": {}}
    if snapshot.service != "screen" or snapshot.url != ROOT or not _equal(snapshot.request, expected):
        return "screen_selected_request_mismatch"
    transport = snapshot.transport
    if type(transport) is not dict or not _equal(transport, transport):
        return "screen_transport_invalid"
    request = transport.get("request")
    if (type(request) is not dict or request.get("method") != "POST" or request.get("url") != ROOT
            or transport.get("effective_url", ROOT) != ROOT
            or request.get("body_base64") != base64.b64encode(spec["body"]).decode("ascii")
            or request.get("body_sha256") != hashlib.sha256(spec["body"]).hexdigest()
            or not _equal(request.get("authentication"), {"scheme": "Bearer", "credential_value_retained": False})):
        return "screen_selected_request_mismatch"
    headers = request.get("headers")
    if (type(headers) is not dict or any(type(key) is not str for key in headers)
            or any(key.lower() == "authorization" for key in headers)
            or [item for key, item in headers.items() if key.lower() == "accept"] != [spec["accept"]]
            or [item for key, item in headers.items() if key.lower() == "content-type"] != [spec["content_type"]]):
        return "screen_selected_request_mismatch"
    policy = transport.get("request_policy")
    if (type(policy) is not dict or policy.get("automatic_redirects") is not False
            or not _equal(policy.get("timeout_seconds"), timeout)
            or type(transport.get("response_byte_limit")) is not int
            or transport["response_byte_limit"] != value["max_bytes"]):
        return "screen_transfer_policy_mismatch"
    pairs = transport.get("header_items")
    if (type(pairs) not in (list, tuple) or any(type(pair) not in (list, tuple) or len(pair) != 2
            or any(type(item) is not str for item in pair) for pair in pairs)):
        return "screen_transport_invalid"
    return None


def _transfer_failure(snapshot, value):
    transport = snapshot.transport
    status = transport.get("status")
    if type(status) is not int:
        return "screen_http_status_unavailable"
    if status == 206 or any(key.lower() == "content-range" for key, _ in transport["header_items"]):
        return "screen_partial_response"
    if status != 200:
        return "screen_http_not_successful"
    if (transport.get("body_complete") is not True or transport.get("body_capture_failure") is not None
            or transport.get("body_capture_error") is not None):
        return "screen_capture_incomplete"
    size = len(snapshot.content)
    if (size > value["max_bytes"] or any(type(transport.get(key)) is not int or transport[key] != size
            for key in ("retained_body_bytes", "observed_body_bytes"))):
        return "screen_capture_identity_mismatch"
    declared = transport.get("declared_body_bytes")
    if declared is not None and (type(declared) is not int or declared != size):
        return "screen_capture_identity_mismatch"
    encodings = [item.strip().lower() for key, item in transport["header_items"] if key.lower() == "content-encoding"]
    if encodings not in ([], ["identity"]):
        return "screen_content_encoding_unsupported"
    if any(key.lower() == "content-type" and item.split(";", 1)[0].strip().lower() == "text/html"
            for key, item in transport["header_items"]):
        return "screen_native_representation_invalid"
    return None


def _document(content):
    def members(pairs):
        value = {}
        for key, child in pairs:
            if key in value:
                raise ValueError("duplicate_native_member")
            value[key] = child
        return value
    def constant(value):
        raise ValueError("nonfinite_native_number")
    return json.loads(content.decode("utf-8"), object_pairs_hook=members, parse_float=Decimal, parse_constant=constant)


def _number(value):
    return type(value) is int or type(value) is Decimal and value.is_finite()


def _field(field, value):
    if field in {"accession", "ccre_group"}:
        return type(value) is str
    if value is None:
        return True
    if field == "chromosome":
        return type(value) is str
    if field == "nearestgenes":
        return type(value) is list and all(row is None or type(row) is dict
            and {"distance", "gene"} <= set(row) and _number(row["distance"]) and type(row["gene"]) is str for row in value)
    return _number(value)


def _representation_failure(content, value):
    try:
        document = _document(content)
        if type(document) is not dict:
            return "screen_native_representation_invalid"
        if "errors" in document:
            if type(document["errors"]) is not list:
                return "screen_native_representation_invalid"
            if document["errors"]:
                return "screen_graphql_errors"
        data = document.get("data")
        if type(data) is not dict or "getmaxZScoresQuery" not in data:
            return "screen_native_representation_invalid"
        rows = data["getmaxZScoresQuery"]
        if rows is None:
            return "screen_native_result_unavailable"
        if type(rows) is not list:
            return "screen_native_representation_invalid"
        for row in rows:
            if row is not None and (type(row) is not dict or not set(value["fields"]) <= set(row)
                    or any(not _field(field, row[field]) for field in value["fields"])):
                return "screen_native_representation_invalid"
        return None
    except (ValueError, UnicodeError, OverflowError, RecursionError):
        return "screen_native_representation_invalid"


def publish_screen_request(registry, arguments, snapshot):
    """Use the registry's existing publication transaction and Source owner."""
    value = validate_screen_arguments(arguments)
    if not isinstance(snapshot, SourceSnapshot) or type(snapshot.content) is not bytes:
        raise ContractError("screen_snapshot_invalid")
    try:
        failure = (_association_failure(snapshot, value, timeout=_timeout(registry.clients))
            or _transfer_failure(snapshot, value) or _representation_failure(snapshot.content, value))
    except Exception:
        registry._source(TOOL, None, snapshot=snapshot, accession=None)
        raise
    source = registry._source(TOOL, None, snapshot=snapshot, accession=None)
    if source.get("artifact_ref") != "artifact_" + hashlib.sha256(snapshot.content).hexdigest():
        raise ContractError("screen_capture_identity_mismatch")
    receipt = validate_screen_receipt({"acquired": failure is None, "source_ref": source["id"],
        "data_ref": source["artifact_ref"] if failure is None else None, "failure_code": failure})
    return receipt, [source["id"], source["artifact_ref"]] if receipt["acquired"] else [source["id"]]


__all__ = ["TOOL", "ROOT", "REQUEST_VERSION", "MAX_BYTES", "FIELDS", "FAILURE_CODES", "ARGUMENTS_SCHEMA",
    "validate_screen_arguments", "screen_request_spec", "screen_tool_contract", "request_screen",
    "publish_screen_request", "screen_receipt_schema", "validate_screen_receipt"]
