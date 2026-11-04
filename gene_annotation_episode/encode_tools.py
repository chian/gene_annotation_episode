"""Explicit ENCODE metadata or advertised-file acquisition in the calling episode.

Contracts are based on the official ENCODE-DCC encoded and snovault-search
source, not a claim about a pinned deployed portal version. Search has an
explicit limit; report additionally has an explicit native from offset. File
transfer selects a received File object's literal cloud_metadata.url. No query
generation, first match, page following, redirect following or analysis occurs.
"""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import base64
import hashlib
import json
import math
import re
from urllib.parse import urlencode, urlsplit

from .acquisition import AcquisitionError, SourceSnapshot
from .data_acquisition_receipts import acquisition_receipt_schema, validate_acquisition_receipt
from .domain import ContractError, canonical, identity
from .episode_return_records import EpisodeReturnRecords


TOOL = "public.encode"
ROOT = "https://www.encodeproject.org"
REQUEST_VERSION = "encode_acquisition_request_v1"
SELECTION_VERSION = "encode_advertised_file_selection_v1"
MAX_METADATA_BYTES = 8 * 1024 ** 2
MAX_FILE_BYTES = 1024 ** 3
MAX_LIMIT = 100
_SOURCE = re.compile(r"source_[a-f0-9]{24,64}\Z", re.ASCII)
_PATH = re.compile(r"/[A-Za-z][A-Za-z0-9_-]*/[A-Za-z0-9][A-Za-z0-9_.~-]*/\Z", re.ASCII)
_TYPE = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z", re.ASCII)
_FIELD = re.compile(r"[A-Za-z_@][A-Za-z0-9_@]*(?:\.[A-Za-z0-9_@]+)*!?\Z", re.ASCII)
_HEX = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)
_MD5 = re.compile(r"[a-fA-F0-9]{32}\Z", re.ASCII)
_RESERVED = {"type", "searchTerm", "from", "limit", "frame", "format", "field", "sort", "mode"}
FAILURE_CODES = (
    "encode_arguments_invalid", "encode_receipt_invalid", "encode_timeout_invalid", "encode_snapshot_invalid",
    "encode_selected_request_mismatch", "encode_transport_invalid", "encode_transfer_policy_mismatch",
    "encode_http_status_unavailable", "encode_http_not_successful", "encode_partial_response",
    "encode_capture_incomplete", "encode_capture_identity_mismatch", "encode_content_encoding_unsupported",
    "encode_native_representation_invalid", "encode_search_result_invalid", "encode_object_identity_conflict",
    "encode_file_size_conflict", "encode_file_md5_conflict", "encode_file_metadata_invalid",
    "encode_file_selection_required", "encode_file_selection_conflict", "encode_received_input_authority_required",
    "encode_metadata_not_received", "encode_metadata_bytes_not_received", "encode_metadata_producer_conflict",
    "encode_metadata_source_invalid", "encode_metadata_source_identity_conflict", "encode_metadata_artifact_identity_conflict",
    "encode_metadata_control_invalid", "encode_metadata_not_acquired", "encode_saved_outcome_conflict",
    "encode_saved_request_conflict", "encode_saved_source_conflict", "encode_saved_response_conflict",
    "provider_connection_failed", "provider_request_timeout", "adapter_execution_failed", "invalid_tool_input",
    "representation_error", "data_acquisition_publication_incomplete", "data_acquisition_failed",
)


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _query_schema(operation):
    properties = {"operation": {"const": operation},
        "object_type": {"type": "string", "pattern": r"^[A-Za-z][A-Za-z0-9_]*$", "maxLength": 128},
        "filters": {"type": "array", "maxItems": 100, "items": _object({
            "field": {"type": "string", "maxLength": 256},
            "value": {"type": "string", "minLength": 1, "maxLength": 4096}})},
        "search_term": {"type": ["string", "null"], "minLength": 1, "maxLength": 4096},
        "frame": {"enum": ["object", "embedded"]},
        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT},
        "max_bytes": {"type": "integer", "minimum": 1, "maximum": MAX_METADATA_BYTES}}
    if operation == "report":
        properties["offset_0based"] = {"type": "integer", "minimum": 0}
    return _object(properties)


ARGUMENTS_SCHEMA = {"oneOf": [_query_schema("search"), _query_schema("report"),
    _object({"operation": {"const": "object"}, "object_path": {"type": "string", "maxLength": 512,
        "pattern": r"^/[A-Za-z][A-Za-z0-9_-]*/[A-Za-z0-9][A-Za-z0-9_.~-]*/$"},
        "frame": {"enum": ["object", "embedded"]},
        "max_bytes": {"type": "integer", "minimum": 1, "maximum": MAX_METADATA_BYTES}}),
    _object({"operation": {"const": "file"}, "metadata_source_ref": {"type": "string", "format": "reference",
        "x-reference-namespace": "source", "pattern": r"^source_[a-f0-9]{24,64}$"},
        "file_pointer": {"type": "string", "maxLength": 4096},
        "file_id": {"type": "string", "pattern": r"^/files/[A-Za-z0-9][A-Za-z0-9_.~-]*/$"},
        "max_bytes": {"type": "integer", "minimum": 1, "maximum": MAX_FILE_BYTES}})]}


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _text(value):
    if type(value) is not str or not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    try:
        value.encode("utf-8")
    except UnicodeError:
        return False
    return True


def _path(value):
    return (type(value) is str and len(value) <= 512 and _PATH.fullmatch(value) is not None
        and value.split("/")[2] not in {".", ".."})


def _pointer_parts(value):
    _require(type(value) is str and len(value) <= 4096 and (value == "" or value.startswith("/")), "encode_arguments_invalid")
    parts = []
    for part in value.split("/")[1:]:
        _require(re.search(r"~(?![01])", part) is None, "encode_arguments_invalid")
        parts.append(part.replace("~1", "/").replace("~0", "~"))
    return parts


def validate_encode_arguments(arguments):
    require = lambda condition: _require(condition, "encode_arguments_invalid")
    require(type(arguments) is dict)
    operation = arguments.get("operation")
    require(type(operation) is str and operation in {"search", "report", "object", "file"})
    if operation in {"search", "report"}:
        fields = {"operation", "object_type", "filters", "search_term", "frame", "limit", "max_bytes"}
        require(set(arguments) == fields | ({"offset_0based"} if operation == "report" else set()))
        require(type(arguments["object_type"]) is str and len(arguments["object_type"]) <= 128
            and _TYPE.fullmatch(arguments["object_type"]) is not None)
        require(type(arguments["filters"]) is list and len(arguments["filters"]) <= 100)
        for item in arguments["filters"]:
            require(type(item) is dict and set(item) == {"field", "value"})
            require(type(item["field"]) is str and len(item["field"]) <= 256
                and _FIELD.fullmatch(item["field"]) is not None and item["field"].rstrip("!") not in _RESERVED)
            require(_text(item["value"]) and len(item["value"]) <= 4096)
        require(arguments["search_term"] is None or _text(arguments["search_term"]) and len(arguments["search_term"]) <= 4096)
        require(type(arguments["limit"]) is int and 1 <= arguments["limit"] <= MAX_LIMIT)
        if operation == "report":
            require(type(arguments["offset_0based"]) is int and arguments["offset_0based"] >= 0)
    elif operation == "object":
        require(set(arguments) == {"operation", "object_path", "frame", "max_bytes"} and _path(arguments["object_path"]))
    else:
        require(set(arguments) == {"operation", "metadata_source_ref", "file_pointer", "file_id", "max_bytes"})
        require(type(arguments["metadata_source_ref"]) is str and _SOURCE.fullmatch(arguments["metadata_source_ref"]) is not None)
        _pointer_parts(arguments["file_pointer"])
        require(_path(arguments["file_id"]) and arguments["file_id"].startswith("/files/"))
    if operation != "file":
        require(type(arguments["frame"]) is str and arguments["frame"] in {"object", "embedded"})
    require(type(arguments["max_bytes"]) is int and 1 <= arguments["max_bytes"] <= (
        MAX_FILE_BYTES if operation == "file" else MAX_METADATA_BYTES))
    return deepcopy(arguments)


def _https(value):
    if not _text(value):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None
            and parsed.password is None and not parsed.fragment and parsed.port in {None, 443}
            and not any(char.isspace() for char in value) and "\\" not in value)
    except ValueError:
        return False


def encode_request_spec(arguments, *, selection=None):
    value = validate_encode_arguments(arguments)
    operation = value["operation"]
    if operation in {"search", "report"}:
        params = [("type", value["object_type"]), *[(item["field"], item["value"]) for item in value["filters"]]]
        if value["search_term"] is not None:
            params.append(("searchTerm", value["search_term"]))
        params.extend([("limit", value["limit"]), ("frame", value["frame"]), ("format", "json")])
        if operation == "report":
            params.append(("from", value["offset_0based"]))
        url = ROOT + "/" + operation + "/"
    elif operation == "object":
        url, params = ROOT + value["object_path"], [("frame", value["frame"]), ("format", "json")]
    else:
        _require(type(selection) is dict and selection.get("version") == SELECTION_VERSION
            and _same(selection.get("arguments"), value) and type(selection.get("association")) is dict
            and selection["association"].get("file_id") == value["file_id"]
            and _https(selection["association"].get("advertised_url")), "encode_file_selection_required")
        url, params = selection["association"]["advertised_url"], {}
    return {"service": "encode", "url": url, "params": params,
        "media_type": "application/octet-stream" if operation == "file" else "application/json",
        "accept": "*/*" if operation == "file" else "application/json",
        "max_bytes": value["max_bytes"], "follow_redirects": False}


def encode_receipt_schema():
    return acquisition_receipt_schema(failure_codes=FAILURE_CODES)


def validate_encode_receipt(value):
    return validate_acquisition_receipt(value, failure_codes=FAILURE_CODES, invalid_code="encode_receipt_invalid")


def encode_tool_contract():
    return {"name": TOOL, "resources": "api", "description":
        "Retrieve explicitly selected ENCODE metadata or one advertised data file for future analysis.",
        "input_schema": deepcopy(ARGUMENTS_SCHEMA), "instructions":
        "Select search for a bounded native result slice, report for an explicit offset_0based and limit, "
        "or object for an exact canonical object_path. Supply the exact object_type, literal ordered "
        "filters, search_term or null, frame and max_bytes. Search has no offset; report sends from. "
        "Native metadata retains assay, biosample, replicate, library and file associations. Select file "
        "only from an explicitly received metadata Source: file_pointer identifies the exact native "
        "File object and file_id must equal its @id. This variant transfers only its advertised "
        "cloud_metadata.url; missing links and portal redirects do not trigger another request. "
        "Each call performs one bounded GET, without choosing a first match, following pages, redirects "
        "or fallback requests. Metadata is limited to 8 MiB; files to the explicit limit up to 1 GiB. "
        "Return only acquired, source_ref, data_ref and failure_code. Success delivers the Source and "
        "original data File; captured failure retains its Source and prefix without delivering a File. "
        "An authenticated complete empty search is acquired data. Preserve original bytes, native "
        "pagination, unknown release and qualifications for future analysis. This getter performs no analysis."}


def _same(left, right):
    try:
        return canonical(left) == canonical(right)
    except (ValueError, TypeError, OverflowError, RecursionError):
        return False


def _timeout_value(value):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    _require(valid, "encode_timeout_invalid")
    return value


def _timeout(client):
    return _timeout_value(getattr(client, "timeout", None))


def _address(spec):
    return spec["url"] + ("?" + urlencode(spec["params"], doseq=True) if spec["params"] else "")


def request_encode(client, arguments, *, selection=None):
    value = validate_encode_arguments(arguments)
    spec = encode_request_spec(value, selection=selection)
    try:
        snapshot = client._http(**spec, timeout_seconds=_timeout(client))
    except AcquisitionError as error:
        if not isinstance(error.snapshot, SourceSnapshot) or type(error.snapshot.content) is not bytes:
            raise
        snapshot = error.snapshot
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes, "encode_snapshot_invalid")
    return replace(snapshot, request={"version": REQUEST_VERSION, "arguments": value,
        "native_service": snapshot.service, "native_request": deepcopy(snapshot.request), "selection": deepcopy(selection)})


def _association_failure(snapshot, value, *, timeout, selection=None):
    spec = encode_request_spec(value, selection=selection)
    address = _address(spec)
    expected = {"version": REQUEST_VERSION, "arguments": value,
        "native_service": "encode", "native_request": spec["params"], "selection": selection}
    if snapshot.service != "encode" or snapshot.url not in {spec["url"], address} or not _same(snapshot.request, expected):
        return "encode_selected_request_mismatch"
    transport = snapshot.transport
    if type(transport) is not dict or not _same(transport, transport):
        return "encode_transport_invalid"
    request = transport.get("request")
    if (type(request) is not dict or request.get("method") != "GET" or request.get("url") != address
            or any(key in request for key in ("body_base64", "body_sha256"))
            or transport.get("effective_url", address) != address):
        return "encode_selected_request_mismatch"
    headers = request.get("headers")
    if (type(headers) is not dict or any(type(key) is not str for key in headers)
            or [item for key, item in headers.items() if key.lower() == "accept"] != [spec["accept"]]):
        return "encode_selected_request_mismatch"
    policy = transport.get("request_policy")
    if (type(policy) is not dict or policy.get("automatic_redirects") is not False
            or not _same(policy.get("timeout_seconds"), timeout)
            or type(transport.get("response_byte_limit")) is not int
            or transport["response_byte_limit"] != value["max_bytes"]):
        return "encode_transfer_policy_mismatch"
    pairs = transport.get("header_items")
    if (type(pairs) not in (list, tuple) or any(type(pair) not in (list, tuple) or len(pair) != 2
            or any(type(item) is not str for item in pair) for pair in pairs)):
        return "encode_transport_invalid"
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
    return json.loads(content.decode("utf-8"), object_pairs_hook=members,
        parse_float=Decimal, parse_constant=constant)


def _empty_search(snapshot, value):
    if value["operation"] not in {"search", "report"}:
        return False
    try:
        document = _document(snapshot.content)
        return (type(document) is dict and document.get("@graph") == []
            and type(document.get("total")) is int and document["total"] == 0
            and document.get("notification") == "No results found"
            and type(document.get("@type")) is list
            and ("Report" if value["operation"] == "report" else "Search") in document["@type"])
    except (ValueError, UnicodeError, RecursionError):
        return False


def _transfer_failure(snapshot, value, *, retained_size=None):
    transport = snapshot.transport
    status = transport.get("status")
    if type(status) is not int:
        return "encode_http_status_unavailable"
    if status == 206 or any(key.lower() == "content-range" for key, _ in transport["header_items"]):
        return "encode_partial_response"
    if status != 200 and not (status == 404 and _empty_search(snapshot, value)):
        return "encode_http_not_successful"
    if (transport.get("body_complete") is not True or transport.get("body_capture_failure") is not None
            or transport.get("body_capture_error") is not None):
        return "encode_capture_incomplete"
    size = len(snapshot.content) if retained_size is None else retained_size
    if (type(size) is not int or size < 0 or retained_size is not None and value["operation"] != "file"
            or size > value["max_bytes"] or any(type(transport.get(key)) is not int or transport[key] != size
            for key in ("retained_body_bytes", "observed_body_bytes"))):
        return "encode_capture_identity_mismatch"
    declared = transport.get("declared_body_bytes")
    if declared is not None and (type(declared) is not int or declared != size):
        return "encode_capture_identity_mismatch"
    encodings = [item.strip().lower() for key, item in transport["header_items"] if key.lower() == "content-encoding"]
    if encodings not in ([], ["identity"]):
        return "encode_content_encoding_unsupported"
    if value["operation"] != "file" and any(key.lower() == "content-type" and item.split(";", 1)[0].strip().lower() == "text/html"
            for key, item in transport["header_items"]):
        return "encode_native_representation_invalid"
    return None


def _representation_failure(content, value, *, selection=None):
    if value["operation"] == "file":
        association = selection["association"]
        if association["file_size"] is not None and len(content) != association["file_size"]:
            return "encode_file_size_conflict"
        if association["md5sum"] is not None and hashlib.md5(content).hexdigest() != association["md5sum"].lower():
            return "encode_file_md5_conflict"
        return None
    try:
        document = _document(content)
        if value["operation"] in {"search", "report"}:
            if (type(document) is not dict or type(document.get("@graph")) is not list
                    or type(document.get("total")) is not int or document["total"] < 0
                    or len(document["@graph"]) > value["limit"] or len(document["@graph"]) > document["total"]
                    or any(type(row) is not dict or not _path(row.get("@id")) for row in document["@graph"])):
                return "encode_search_result_invalid"
            return None
        if type(document) is not dict or document.get("@id") != value["object_path"]:
            return "encode_object_identity_conflict"
        return None
    except (ValueError, UnicodeError, OverflowError, RecursionError):
        return "encode_native_representation_invalid"


def _artifact(store, reference, *, read=False):
    record = store.get(reference)
    _require(record.get("record_type") == "artifact" and record.get("id") == reference
        and type(record.get("sha256")) is str and _HEX.fullmatch(record["sha256"]) is not None
        and reference == "artifact_" + record["sha256"]
        and type(record.get("size")) is int and record["size"] >= 0, "encode_metadata_artifact_identity_conflict")
    raw = None
    if read:
        raw = store.get_artifact(reference)
        _require(type(raw) is bytes and len(raw) == record["size"]
            and hashlib.sha256(raw).hexdigest() == record["sha256"], "encode_metadata_artifact_identity_conflict")
    return record, raw


def _source(store, reference):
    source = store.get(reference)
    _require(source.get("record_type") == "source" and source.get("id") == reference
        and source.get("origin") == "external" and source.get("provider") == TOOL
        and source.get("version") is None, "encode_metadata_source_invalid")
    payload = {key: child for key, child in source.items() if key not in {"id", "record_type", "origin"}}
    _require(identity("source", {"origin": source["origin"], "record": payload}) == reference,
        "encode_metadata_source_identity_conflict")
    return source


def _pointer(document, pointer):
    value = document
    for part in _pointer_parts(pointer):
        if type(value) is dict and part in value:
            value = value[part]
        elif type(value) is list and re.fullmatch(r"0|[1-9][0-9]*", part) and int(part) < len(value):
            value = value[int(part)]
        else:
            raise ContractError("encode_file_metadata_invalid")
    return value


def _file_association(raw, arguments):
    try:
        file = _pointer(_document(raw), arguments["file_pointer"])
        require = lambda condition: _require(condition, "encode_file_metadata_invalid")
        require(type(file) is dict and file.get("@id") == arguments["file_id"])
        cloud = file.get("cloud_metadata")
        require(type(cloud) is dict and _https(cloud.get("url"))
            and file.get("restricted") is not True and file.get("no_file_available") is not True)
        size, md5 = file.get("file_size"), file.get("md5sum")
        require(size is None or type(size) is int and size >= 0)
        require(md5 is None or type(md5) is str and _MD5.fullmatch(md5) is not None)
        if "file_size" in cloud:
            require(type(cloud["file_size"]) is int and cloud["file_size"] >= 0
                and (size is None or cloud["file_size"] == size))
            size = cloud["file_size"]
        if "md5sum_base64" in cloud:
            require(type(cloud["md5sum_base64"]) is str)
            digest = base64.b64decode(cloud["md5sum_base64"], validate=True)
            require(len(digest) == 16 and base64.b64encode(digest).decode() == cloud["md5sum_base64"]
                and (md5 is None or digest.hex() == md5.lower()))
            md5 = digest.hex()
        return {"file_id": arguments["file_id"], "advertised_url": cloud["url"], "file_size": size, "md5sum": md5}
    except (ValueError, UnicodeError, OverflowError, RecursionError) as error:
        raise ContractError("encode_file_metadata_invalid") from error


def _metadata_operation(registry, source, *, expected=None):
    # Reuse the existing tool-name-parameterized operation/action/scope owner.
    # No ENCODE SQL authority or alternative completed-operation proof is added.
    from .alphafold_acquisition_host import _operation
    try:
        operation, arguments, outcome = _operation(registry, source["id"], TOOL, expected=expected)
        arguments = validate_encode_arguments(arguments)
        receipt = validate_encode_receipt(outcome.get("result"))
        _require(outcome.get("status") == "completed" and receipt["acquired"]
            and receipt["source_ref"] == source["id"] and receipt["data_ref"] == source["artifact_ref"]
            and outcome.get("record_refs") == [source["id"], source["artifact_ref"]]
            and arguments["operation"] in {"search", "report", "object"}, "encode_metadata_producer_conflict")
    except ContractError as error:
        raise ContractError("encode_metadata_producer_conflict") from error
    return operation, arguments


def _metadata(registry, arguments, *, raw=None):
    source = _source(registry.store, arguments["metadata_source_ref"])
    operation, original_arguments = _metadata_operation(registry, source)
    artifact, retained = _artifact(registry.store, source["artifact_ref"], read=raw is None)
    raw = retained if raw is None else raw
    _require(type(raw) is bytes and len(raw) == artifact["size"]
        and hashlib.sha256(raw).hexdigest() == artifact["sha256"], "encode_metadata_artifact_identity_conflict")
    control_metadata, control_raw = _artifact(registry.store, source["request_ref"], read=True)
    try:
        control = json.loads(control_raw)
        _require(control_raw == canonical(control).encode() and type(control) is dict
            and set(control) == {"request", "transport"}, "encode_metadata_control_invalid")
        request = control["request"]
        _require(type(request) is dict and request.get("version") == REQUEST_VERSION, "encode_metadata_control_invalid")
        original = validate_encode_arguments(request["arguments"])
        _require(_same(original, original_arguments), "encode_metadata_source_invalid")
        _require(type(control["transport"]) is dict and type(control["transport"].get("request_policy")) is dict,
            "encode_metadata_control_invalid")
        snapshot = SourceSnapshot(request.get("native_service"), source["uri"], request, source["retrieved_at"], raw,
            "application/json", control["transport"])
        original_timeout = _timeout_value(control["transport"].get("request_policy", {}).get("timeout_seconds"))
        _require(_association_failure(snapshot, original, timeout=original_timeout) is None
            and _transfer_failure(snapshot, original) is None
            and _representation_failure(raw, original) is None, "encode_metadata_not_acquired")
        association = _file_association(raw, arguments)
    except (KeyError, TypeError, ValueError, UnicodeError, OverflowError, RecursionError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError("encode_metadata_control_invalid") from error
    return {"version": SELECTION_VERSION, "arguments": deepcopy(arguments),
        "metadata_operation": operation,
        "metadata_source_sha256": hashlib.sha256(canonical(source).encode()).hexdigest(),
        "metadata_artifact_ref": artifact["id"], "metadata_size_bytes": artifact["size"],
        "metadata_request_ref": source["request_ref"], "metadata_request_sha256": control_metadata["sha256"],
        "association": association}


def _authority(registry, authority):
    _require(type(authority) is tuple and len(authority) == 2 and callable(authority[1]),
        "encode_received_input_authority_required")
    context, reader = authority
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="encode_").authenticate(context)
    return context, reader


def prepare_encode_request(registry, arguments, *, authority=None):
    """Resolve a selected received File object before any network request.

    The callback is the existing received-input reader used by AlphaFold:
    reader(context, ref, 'source', source_metadata_only=True), then the same
    reader with file_format='text'. Source admission precedes entity/control reads.
    """
    value = validate_encode_arguments(arguments)
    if value["operation"] != "file":
        return None
    context, reader = _authority(registry, authority)
    received = reader(context, value["metadata_source_ref"], "source", source_metadata_only=True)
    _require(type(received) is dict and received.get("failure") is None and received.get("input") is not None,
        "encode_metadata_not_received")
    source = _source(registry.store, value["metadata_source_ref"])
    _require(_same(received["input"]["witness"]["record"], source), "encode_metadata_source_identity_conflict")
    received_file, path = reader(context, source["id"], "source", file_format="text")
    _require(received_file.get("failure") is None and path is not None
        and received_file.get("input") is not None and received_file["input"]["byte_verification"] == "verified"
        and received_file["input"]["file"]["artifact_ref"] == source["artifact_ref"],
        "encode_metadata_bytes_not_received")
    return _metadata(registry, value, raw=path.read_bytes())


def _selection(registry, arguments, selection):
    _require(type(selection) is dict and _same(selection, _metadata(registry, arguments)), "encode_file_selection_conflict")
    return deepcopy(selection)


def publish_encode_request(registry, arguments, snapshot, *, selection=None):
    value = validate_encode_arguments(arguments)
    _require(isinstance(snapshot, SourceSnapshot) and type(snapshot.content) is bytes, "encode_snapshot_invalid")
    publication_snapshot = snapshot
    try:
        if value["operation"] == "file":
            selection = _selection(registry, value, selection)
        else:
            _require(selection is None, "encode_file_selection_conflict")
        association = _association_failure(snapshot, value, timeout=_timeout(registry.clients), selection=selection)
        if association is None:
            publication_snapshot = replace(snapshot, url=snapshot.transport["request"]["url"])
        failure = (association or _transfer_failure(snapshot, value)
            or _representation_failure(snapshot.content, value, selection=selection))
    except Exception:
        registry._source(TOOL, None, snapshot=publication_snapshot, accession=None)
        raise
    parents, auxiliary = [], []
    if value["operation"] == "file" and association is None:
        parents = [value["metadata_source_ref"]]
        auxiliary = [registry.store.artifact(canonical(selection), "application/json")]
    source = registry._source(TOOL, None, snapshot=publication_snapshot, accession=None,
        parent_source_refs=parents, auxiliary_artifact_refs=auxiliary)
    _require(source.get("artifact_ref") == "artifact_" + hashlib.sha256(snapshot.content).hexdigest(),
        "encode_capture_identity_mismatch")
    receipt = validate_encode_receipt({"acquired": failure is None, "source_ref": source["id"],
        "data_ref": source["artifact_ref"] if failure is None else None, "failure_code": failure})
    return receipt, [source["id"], source["artifact_ref"]] if receipt["acquired"] else [source["id"]]


def _saved_selection(registry, arguments, selection):
    """Authenticate original selection metadata without reopening its entity."""
    fields = {"version", "arguments", "metadata_operation", "metadata_source_sha256", "metadata_artifact_ref", "metadata_size_bytes",
        "metadata_request_ref", "metadata_request_sha256", "association"}
    _require(type(selection) is dict and set(selection) == fields and selection["version"] == SELECTION_VERSION
        and _same(selection["arguments"], arguments), "encode_file_selection_conflict")
    source = _source(registry.store, arguments["metadata_source_ref"])
    expected = selection["metadata_operation"]
    _require(type(expected) is dict and set(expected) == {"operation_key", "operation_ref"}, "encode_file_selection_conflict")
    _metadata_operation(registry, source, expected=expected)
    artifact, _ = _artifact(registry.store, source["artifact_ref"])
    request, _ = _artifact(registry.store, source["request_ref"])
    _require(selection["metadata_source_sha256"] == hashlib.sha256(canonical(source).encode()).hexdigest()
        and selection["metadata_artifact_ref"] == artifact["id"]
        and type(selection["metadata_size_bytes"]) is int and selection["metadata_size_bytes"] == artifact["size"]
        and selection["metadata_request_ref"] == request["id"]
        and selection["metadata_request_sha256"] == request["sha256"], "encode_file_selection_conflict")
    association = selection["association"]
    _require(type(association) is dict and set(association) == {"file_id", "advertised_url", "file_size", "md5sum"}
        and association["file_id"] == arguments["file_id"] and _https(association["advertised_url"])
        and (association["file_size"] is None or type(association["file_size"]) is int and association["file_size"] >= 0)
        and (association["md5sum"] is None or type(association["md5sum"]) is str
            and _MD5.fullmatch(association["md5sum"]) is not None), "encode_file_selection_conflict")
    return deepcopy(selection)


def authenticate_saved_encode_request(registry, arguments, *, authority, outcome):
    """Recheck a registry-authenticated file cache result under current admission.

    The ordinary ToolRegistry still authenticates the saved operation/key/scope.
    This finite callback owns its received metadata input and retained selection,
    never a second producer lookup, receipt, grant, entity read or request.
    """
    arguments = validate_encode_arguments(arguments)
    if arguments["operation"] != "file":
        return
    context, reader = _authority(registry, authority)
    received = reader(context, arguments["metadata_source_ref"], "source", source_metadata_only=True)
    _require(type(received) is dict and received.get("failure") is None and received.get("input") is not None,
        "encode_metadata_not_received")
    metadata_source = _source(registry.store, arguments["metadata_source_ref"])
    _require(_same(received["input"]["witness"]["record"], metadata_source), "encode_metadata_source_identity_conflict")
    _require(type(outcome) is dict, "encode_saved_outcome_conflict")
    result = validate_encode_receipt(outcome.get("result"))
    source_ref = result["source_ref"]
    if source_ref is None:
        _require(not result["acquired"] and outcome.get("record_refs") == []
            and outcome.get("status") in {"invalid", "unavailable", "failed"}, "encode_saved_outcome_conflict")
        return
    source = _source(registry.store, source_ref)
    artifact, _ = _artifact(registry.store, source["artifact_ref"])
    _require(outcome.get("record_refs") == [source_ref, *([artifact["id"]] if result["acquired"] else [])]
        and (outcome.get("status") == "completed" if result["acquired"] else outcome.get("status") in {"partial", "failed"})
        and (result["data_ref"] == artifact["id"] if result["acquired"] else result["data_ref"] is None),
        "encode_saved_outcome_conflict")
    _, raw = _artifact(registry.store, source["request_ref"], read=True)
    try:
        control = json.loads(raw)
        _require(raw == canonical(control).encode() and type(control) is dict
            and set(control) == {"request", "transport"}, "encode_saved_request_conflict")
        request = control["request"]
        _require(type(request) is dict and _same(request.get("arguments"), arguments), "encode_saved_request_conflict")
        selection = _saved_selection(registry, arguments, request.get("selection"))
        transport = control["transport"]
        _require(type(transport) is dict and type(transport.get("request_policy")) is dict,
            "encode_saved_request_conflict")
        timeout = _timeout_value(transport.get("request_policy", {}).get("timeout_seconds"))
        retained = SourceSnapshot(request.get("native_service"), source["uri"], request, source["retrieved_at"],
            b"", "application/octet-stream", transport)
        association = _association_failure(retained, arguments, timeout=timeout, selection=selection)
        auxiliary, parents = source.get("auxiliary_artifact_refs", []), source.get("parent_source_refs", [])
        if association is not None:
            _require(not result["acquired"] and result["failure_code"] == association
                and parents == [] and auxiliary == [], "encode_saved_source_conflict")
            return
        if result["failure_code"] == "data_acquisition_publication_incomplete" and parents == [] and auxiliary == []:
            return
        _require(parents == [arguments["metadata_source_ref"]] and type(auxiliary) is list and len(auxiliary) == 1,
            "encode_saved_source_conflict")
        _, witness_raw = _artifact(registry.store, auxiliary[0], read=True)
        _require(witness_raw == canonical(selection).encode(), "encode_file_selection_conflict")
        if result["acquired"]:
            _require(_transfer_failure(retained, arguments, retained_size=artifact["size"]) is None
                and (selection["association"]["file_size"] is None
                    or selection["association"]["file_size"] == artifact["size"]), "encode_saved_response_conflict")
    except (KeyError, TypeError, ValueError, UnicodeError, OverflowError, RecursionError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError("encode_saved_request_conflict") from error


__all__ = ["TOOL", "ROOT", "ARGUMENTS_SCHEMA", "MAX_METADATA_BYTES", "MAX_FILE_BYTES", "MAX_LIMIT", "FAILURE_CODES",
    "validate_encode_arguments", "encode_request_spec", "encode_tool_contract", "encode_receipt_schema",
    "validate_encode_receipt", "prepare_encode_request", "request_encode", "publish_encode_request",
    "authenticate_saved_encode_request"]
