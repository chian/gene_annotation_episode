"""One explicit JASPAR page or versioned matrix acquisition for later analysis.

Official contracts: https://jaspar.elixir.no/api/v1/docs/ and
https://jaspar.elixir.no/docs/. Discovery and exact retrieval are separate
choices. This adapter never follows a page, chooses a first match, transforms
a matrix, or establishes which database release the current API represents.
"""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
from urllib.parse import quote, urlencode

from .acquisition import AcquisitionError, SourceSnapshot
from .domain import ContractError
from .data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt


TOOL = "public.jaspar"
ROOT = "https://jaspar.elixir.no/api/v1/matrix/"
REQUEST_VERSION = "jaspar_acquisition_request_v1"
MAX_BYTES = 8 * 1024 ** 2
MAX_PAGE_SIZE = 100
FILTERS = ("search", "name", "collection", "tax_group", "tax_id", "tf_class", "tf_family", "data_type")
# This is a safe path-component syntax, not an enumeration of JASPAR prefixes.
_MATRIX_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.~-]*\.[0-9]+\Z", re.ASCII)
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z", re.ASCII)
_SOURCE = re.compile(r"source_[a-f0-9]{24,64}\Z", re.ASCII)
_ARTIFACT = re.compile(r"artifact_[a-f0-9]{64}\Z", re.ASCII)
FAILURE_CODES = (
    "jaspar_arguments_invalid", "jaspar_timeout_invalid", "jaspar_snapshot_invalid", "jaspar_receipt_invalid",
    "jaspar_selected_request_mismatch", "jaspar_transport_invalid", "jaspar_transfer_policy_mismatch",
    "jaspar_http_status_unavailable", "jaspar_http_not_successful", "jaspar_partial_response",
    "jaspar_capture_incomplete", "jaspar_capture_identity_mismatch", "jaspar_content_encoding_unsupported",
    "jaspar_native_representation_invalid", "jaspar_discovery_page_invalid",
    "jaspar_matrix_identity_missing", "jaspar_matrix_identity_conflict",
    # These are the existing ordinary getter's no-response/outer failure codes.
    "provider_connection_failed", "provider_request_timeout", "adapter_execution_failed",
    "invalid_tool_input", "representation_error", "data_acquisition_publication_incomplete",
    "data_acquisition_failed",
)


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


_LIMIT = {"type": "integer", "minimum": 1, "maximum": MAX_BYTES}
ARGUMENTS_SCHEMA = {"oneOf": [
    _object({"operation": {"const": "discover"},
        "filters": {"type": "object", "properties": {
            key: {"type": "string", "minLength": 1, "maxLength": 4096} for key in FILTERS},
            "additionalProperties": False},
        "version_mode": {"enum": ["provider_default", "latest"]},
        "page": {"type": "integer", "minimum": 1},
        "page_size": {"type": "integer", "minimum": 1, "maximum": MAX_PAGE_SIZE},
        "max_bytes": deepcopy(_LIMIT)}),
    _object({"operation": {"const": "matrix"},
        "matrix_id": {"type": "string", "maxLength": 256,
            "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.~-]*\.[0-9]+$"},
        "representation": {"enum": ["json", "pfm"]}, "max_bytes": deepcopy(_LIMIT)}),
]}


def _text(value):
    if type(value) is not str or not value or any(ord(character) < 32 or ord(character) == 127 for character in value):
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def _matrix_id(value):
    return type(value) is str and len(value) <= 256 and _MATRIX_ID.fullmatch(value) is not None


def validate_jaspar_arguments(arguments):
    def require(condition):
        if not condition:
            raise ContractError("jaspar_arguments_invalid")
    require(type(arguments) is dict)
    operation = arguments.get("operation")
    require(type(operation) is str and operation in {"discover", "matrix"})
    fields = ({"operation", "filters", "version_mode", "page", "page_size", "max_bytes"}
        if operation == "discover" else {"operation", "matrix_id", "representation", "max_bytes"})
    require(set(arguments) == fields)
    require(type(arguments["max_bytes"]) is int and 1 <= arguments["max_bytes"] <= MAX_BYTES)
    if operation == "discover":
        filters = arguments["filters"]
        require(type(filters) is dict and set(filters) <= set(FILTERS))
        require(all(_text(value) and len(value) <= 4096 for value in filters.values()))
        require(type(arguments["version_mode"]) is str and arguments["version_mode"] in {"provider_default", "latest"})
        require(type(arguments["page"]) is int and arguments["page"] >= 1)
        require(type(arguments["page_size"]) is int and 1 <= arguments["page_size"] <= MAX_PAGE_SIZE)
    else:
        require(_matrix_id(arguments["matrix_id"]))
        require(type(arguments["representation"]) is str and arguments["representation"] in {"json", "pfm"})
    return deepcopy(arguments)


def jaspar_request_spec(arguments):
    value = validate_jaspar_arguments(arguments)
    if value["operation"] == "discover":
        params = {key: value["filters"][key] for key in FILTERS if key in value["filters"]}
        params.update(page=value["page"], page_size=value["page_size"], format="json")
        if value["version_mode"] == "latest":
            params["version"] = "latest"
        url, representation = ROOT, "json"
    else:
        url = ROOT + quote(value["matrix_id"], safe="") + "/"
        representation = value["representation"]
        params = {"format": representation}
    return {"service": "jaspar", "url": url, "params": params,
        "media_type": "application/json" if representation == "json" else "application/octet-stream",
        # The official PFM format link establishes the representation query;
        # it does not establish a MIME value. Retain the actual header instead.
        "accept": "application/json" if representation == "json" else "*/*",
        "max_bytes": value["max_bytes"], "follow_redirects": False}


def jaspar_receipt_schema():
    """The same four-field DTO also fits the existing closed return grammar."""
    return acquisition_receipt_schema(failure_codes=FAILURE_CODES)


def validate_jaspar_receipt(value):
    return validate_acquisition_receipt(value, failure_codes=FAILURE_CODES, invalid_code="jaspar_receipt_invalid")


def jaspar_tool_contract():
    return {"name": TOOL, "resources": "api", "description":
        "Retrieve one explicitly selected JASPAR discovery page or versioned matrix for future analysis.",
        "input_schema": deepcopy(ARGUMENTS_SCHEMA), "instructions":
        "Use discover for one explicit page of native metadata; supply filters, page, page_size and "
        "version_mode. provider_default omits the native version query; latest sends version=latest. "
        "Choose an exact versioned matrix_id explicitly, then use matrix with JSON or raw PFM representation. "
        "Names can identify several matrices. Each call makes one request, without following pages, "
        "choosing a first match or fetching another representation. Set max_bytes to the explicit "
        "response limit, up to the 8 MiB adapter cap. The receipt contains only acquired, source_ref, "
        "data_ref and failure_code. Success delivers the Source and original data File; captured failure "
        "retains its Source and prefix without delivering a data File. Native ordered results, pagination, "
        "metadata and matrix tokens remain in the data. Matrix revision is explicit; database release "
        "remains unknown. This getter performs no matrix transformation, site scoring or biological analysis."}


def _timeout(client):
    value = getattr(client, "timeout", None)
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ContractError("jaspar_timeout_invalid")
    return value


def _equal(first, second):
    try:
        return json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(second, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False


def request_jaspar(client, arguments):
    value = validate_jaspar_arguments(arguments)
    spec = jaspar_request_spec(value)
    try:
        snapshot = client._http(**spec, timeout_seconds=_timeout(client))
    except AcquisitionError as error:
        if not isinstance(error.snapshot, SourceSnapshot) or type(error.snapshot.content) is not bytes:
            raise
        snapshot = error.snapshot
    if not isinstance(snapshot, SourceSnapshot) or type(snapshot.content) is not bytes:
        raise AcquisitionError("jaspar_snapshot_invalid", phase="http_response")
    # Preserve the supplied client's literal request too; publication rejects
    # contradictions rather than relabeling another response as this choice.
    return replace(snapshot, request={"version": REQUEST_VERSION, "arguments": value,
        "native_request": deepcopy(snapshot.request)})


def _association_failure(snapshot, value, *, timeout):
    spec = jaspar_request_spec(value)
    address = spec["url"] + "?" + urlencode(spec["params"])
    expected = {"version": REQUEST_VERSION, "arguments": value, "native_request": spec["params"]}
    if (snapshot.service != "jaspar" or snapshot.url not in {spec["url"], address}
            or not _equal(snapshot.request, expected)):
        return "jaspar_selected_request_mismatch"
    transport = snapshot.transport
    if type(transport) is not dict or not _equal(transport, transport):
        return "jaspar_transport_invalid"
    request = transport.get("request")
    if (type(request) is not dict or request.get("method") != "GET" or request.get("url") != address
            or any(key in request for key in ("body_base64", "body_sha256"))
            or transport.get("effective_url", address) != address):
        return "jaspar_selected_request_mismatch"
    headers = request.get("headers")
    if (type(headers) is not dict or any(type(key) is not str for key in headers)
            or [item for key, item in headers.items() if key.lower() == "accept"] != [spec["accept"]]):
        return "jaspar_selected_request_mismatch"
    policy = transport.get("request_policy")
    if (type(policy) is not dict or policy.get("automatic_redirects") is not False
            or not _equal(policy.get("timeout_seconds"), timeout)
            or type(transport.get("response_byte_limit")) is not int
            or transport["response_byte_limit"] != value["max_bytes"]):
        return "jaspar_transfer_policy_mismatch"
    pairs = transport.get("header_items")
    if (type(pairs) not in (list, tuple) or any(type(pair) not in (list, tuple) or len(pair) != 2
            or any(type(item) is not str for item in pair) for pair in pairs)):
        return "jaspar_transport_invalid"
    return None


def _transfer_failure(snapshot, value):
    transport = snapshot.transport
    status = transport.get("status")
    if type(status) is not int:
        return "jaspar_http_status_unavailable"
    if status == 206 or any(key.lower() == "content-range" for key, _ in transport["header_items"]):
        return "jaspar_partial_response"
    if status != 200:
        return "jaspar_http_not_successful"
    if (transport.get("body_complete") is not True or transport.get("body_capture_failure") is not None
            or transport.get("body_capture_error") is not None):
        return "jaspar_capture_incomplete"
    size = len(snapshot.content)
    if (size > value["max_bytes"] or any(type(transport.get(key)) is not int or transport[key] != size
            for key in ("retained_body_bytes", "observed_body_bytes"))):
        return "jaspar_capture_identity_mismatch"
    declared = transport.get("declared_body_bytes")
    if declared is not None and (type(declared) is not int or declared != size):
        return "jaspar_capture_identity_mismatch"
    encodings = [item.strip().lower() for key, item in transport["header_items"] if key.lower() == "content-encoding"]
    if encodings not in ([], ["identity"]):
        return "jaspar_content_encoding_unsupported"
    if any(key.lower() == "content-type" and item.split(";", 1)[0].strip().lower() == "text/html"
            for key, item in transport["header_items"]):
        return "jaspar_native_representation_invalid"
    return None


def _json_document(content):
    def members(pairs):
        value = {}
        for key, child in pairs:
            if key in value:
                raise ValueError("duplicate_native_member")
            value[key] = child
        return value
    def constant(value):
        raise ValueError("nonfinite_native_number")
    return json.loads(content.decode("utf-8"), object_pairs_hook=members,
        parse_float=Decimal, parse_constant=constant)


def _identity_failure(document, matrix_id):
    if type(document) is not dict or type(document.get("matrix_id")) is not str:
        return "jaspar_matrix_identity_missing"
    if document["matrix_id"] != matrix_id:
        return "jaspar_matrix_identity_conflict"
    base, revision = matrix_id.rsplit(".", 1)
    if "base_id" in document and document["base_id"] != base:
        return "jaspar_matrix_identity_conflict"
    if "version" in document:
        version = document["version"]
        if not (type(version) is str and version == revision or type(version) is int and str(version) == revision):
            return "jaspar_matrix_identity_conflict"
    return None


def _matrix_rows(rows):
    return (type(rows) is list and len(rows) == 4 and type(rows[0]) is list and bool(rows[0])
        and all(type(row) is list and len(row) == len(rows[0])
            and all(type(number) in (int, Decimal) and (type(number) is int or number.is_finite()) and number >= 0
                for number in row) for row in rows))


def _representation_failure(content, value):
    """Confirm native shape/identity only; retain all numbers as original bytes."""
    try:
        if value["operation"] == "matrix" and value["representation"] == "pfm":
            lines = [line.strip() for line in content.decode("utf-8").splitlines() if line.strip()]
            if not lines or not lines[0].startswith(">"):
                return "jaspar_matrix_identity_missing"
            if lines[0][1:].split(None, 1)[0:1] != [value["matrix_id"]]:
                return "jaspar_matrix_identity_conflict"
            if len(lines) != 5:
                return "jaspar_native_representation_invalid"
            rows = []
            for line in lines[1:]:
                tokens = line.split()
                if any(_NUMBER.fullmatch(token) is None for token in tokens):
                    return "jaspar_native_representation_invalid"
                rows.append([Decimal(token) for token in tokens])
            return None if _matrix_rows(rows) else "jaspar_native_representation_invalid"
        document = _json_document(content)
        if value["operation"] == "discover":
            if (type(document) is not dict or not {"count", "next", "previous", "results"} <= set(document)
                    or type(document["count"]) is not int or document["count"] < 0
                    or any(document[key] is not None and not _text(document[key]) for key in ("next", "previous"))
                    or type(document["results"]) is not list or len(document["results"]) > value["page_size"]):
                return "jaspar_discovery_page_invalid"
            for row in document["results"]:
                if (type(row) is not dict or not _matrix_id(row.get("matrix_id"))
                        or _identity_failure(row, row["matrix_id"]) is not None):
                    return "jaspar_discovery_page_invalid"
            return None
        failure = _identity_failure(document, value["matrix_id"])
        if failure is not None:
            return failure
        pfm = document.get("pfm")
        if type(pfm) is not dict or set(pfm) != {"A", "C", "G", "T"}:
            return "jaspar_native_representation_invalid"
        return None if _matrix_rows([pfm[base] for base in "ACGT"]) else "jaspar_native_representation_invalid"
    except (ValueError, UnicodeError, InvalidOperation, OverflowError, RecursionError):
        return "jaspar_native_representation_invalid"


def publish_jaspar_request(registry, arguments, snapshot):
    """Publish inside the existing registry's transaction/publication context."""
    value = validate_jaspar_arguments(arguments)
    if not isinstance(snapshot, SourceSnapshot) or type(snapshot.content) is not bytes:
        raise ContractError("jaspar_snapshot_invalid")
    publication_snapshot = snapshot
    try:
        association = _association_failure(snapshot, value, timeout=_timeout(registry.clients))
        if association is None:
            # The shared client keeps successful snapshot.url as the base URL;
            # only an authenticated actual GET can supply its full query URI.
            publication_snapshot = replace(snapshot, url=snapshot.transport["request"]["url"])
        failure = association or _transfer_failure(snapshot, value) or _representation_failure(snapshot.content, value)
    except Exception:
        # A late unexpected validation failure must still leave its real Source
        # available to the ordinary registry's existing partial-failure owner.
        registry._source(TOOL, None, snapshot=publication_snapshot, accession=None)
        raise
    source = registry._source(TOOL, None, snapshot=publication_snapshot,
        accession=value["matrix_id"] if failure is None and value["operation"] == "matrix" else None)
    if source.get("artifact_ref") != "artifact_" + hashlib.sha256(snapshot.content).hexdigest():
        raise ContractError("jaspar_capture_identity_mismatch")
    receipt = validate_jaspar_receipt({"acquired": failure is None, "source_ref": source["id"],
        "data_ref": source["artifact_ref"] if failure is None else None, "failure_code": failure})
    return receipt, [source["id"], source["artifact_ref"]] if receipt["acquired"] else [source["id"]]


__all__ = ["TOOL", "ARGUMENTS_SCHEMA", "MAX_BYTES", "MAX_PAGE_SIZE", "FAILURE_CODES",
    "validate_jaspar_arguments", "jaspar_request_spec", "jaspar_tool_contract", "jaspar_receipt_schema",
    "validate_jaspar_receipt", "request_jaspar", "publish_jaspar_request"]
