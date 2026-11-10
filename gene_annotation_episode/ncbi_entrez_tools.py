"""One ordinary molecular Entrez retrieval step for later analysis.

The existing ToolRegistry owns the selected action, HTTP execution, publication
transaction and saved operation. This adapter returns acquisition receipts and
original data handles, never a scientific answer or an analysis summary.
"""
from copy import deepcopy
from dataclasses import replace
import json

from .acquisition import AcquisitionError, SourceSnapshot
from . import ncbi_entrez_acquisition as native


TOOL = native.TOOL
_SOURCE = {"type": "string", "pattern": "^source_[a-f0-9]{24,64}$",
    "format": "reference", "x-reference-namespace": "source"}
_DATA = {"type": "string", "pattern": "^artifact_[a-f0-9]{64}$",
    "format": "reference", "x-reference-namespace": "artifact"}


def ncbi_entrez_receipt_schema():
    properties = {"acquired": {"type": "boolean"},
        "source_ref": {"anyOf": [deepcopy(_SOURCE), {"type": "null"}]},
        "data_ref": {"anyOf": [deepcopy(_DATA), {"type": "null"}]},
        "failure_code": {"type": ["string", "null"]}}
    return {"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False}


def ncbi_entrez_tool_contract():
    return {"resources": "api", "description":
        "Retrieve one explicitly selected molecular NCBI Entrez response for later analysis; "
        "return an acquisition receipt and original data handles.",
        "input_schema": deepcopy(native.ARGUMENTS_SCHEMA), "instructions":
        "Retrieval STEP: use the supplied search, summary or fetch request exactly as selected. "
        "The database is protein, nuccore, gene, taxonomy, assembly, gds, sra or snp; the literal query "
        "or ordered IDs, supported native format, search window and byte limit are explicit operands. "
        "For snp, only search and summary are supported; summary IDs are supplied decimal Entrez UIDs. "
        "Execute one request without redirects, retries, page traversal or follow-up requests. "
        "Retain the original native response bytes and their Source provenance for future analysis. "
        "Return only acquired, source_ref, data_ref and failure_code. On acquisition, data_ref is the "
        "original response File, explicitly delivered with its Source. Empty successful queries are "
        "data. Native duplicates, literal number tokens, annotation qualifications and unknown units "
        "remain in that data and do not become acceptance thresholds. On failure, retain any actual "
        "Source and captured prefix, return data_ref=null and preserve the failure code. Use "
        "source.read on that Source with representation=original to inspect a native error; "
        "search hits can coexist with an errorlist and a querytranslation that omitted requested terms. "
        "Choose any revised query as a separate request. Request "
        "controls and diagnostics remain private. This step supplies no analysis, numerical summary, "
        "target annotation or stored gene/reaction/sequence mapping."}


def request_ncbi_entrez(client, arguments):
    """Execute one fixed request through the existing bounded HTTP transport."""
    arguments = native.validate_entrez_arguments(arguments)
    spec = native.entrez_request_spec(arguments)
    try:
        snapshot = client._http(spec["service"], spec["url"], spec["params"], spec["media_type"],
            max_bytes=spec["max_bytes"], timeout_seconds=client.timeout,
            follow_redirects=spec["follow_redirects"])
    except AcquisitionError as error:
        if error.snapshot is not None:
            error.snapshot = _selected_snapshot(error.snapshot, arguments, spec)
        raise
    return _selected_snapshot(snapshot, arguments, spec)


def _selected_snapshot(snapshot, arguments, spec):
    """Normalize only an exact actual native request; preserve contradictions."""
    try:
        matched = (isinstance(snapshot, SourceSnapshot) and type(snapshot.request) is dict
            and json.dumps(snapshot.request, sort_keys=True, allow_nan=False)
                == json.dumps(spec["params"], sort_keys=True, allow_nan=False))
    except (ValueError, TypeError, OverflowError):
        matched = False
    if not matched:
        # The ordinary publisher retains this original capture before the pure
        # selected-request association rejects it. Never relabel its request.
        return snapshot
    return replace(snapshot, request=deepcopy(arguments), media_type=spec["media_type"])


def _snp_response_identity_failure(value):
    """Confirm only observed Entrez UID roles, without rewriting rs identifiers.

    Empty returned inventories are data. Missing or contradictory inventories
    cannot establish a returned document population or a requested identity.
    Native SNP fields and associations are retained without interpretation.
    """
    population = value["population"]
    identifiers = population["returned_id_order_native"]
    if (population["returned_record_count"] is None or identifiers is None
            or any(type(identifier) is not str or not identifier.isascii() or not identifier.isdecimal()
                for identifier in identifiers)):
        return "ncbi_entrez_native_response_identity_missing"
    if value["requested"]["operation"] == "summary":
        codes = {issue["code"] for issue in value["issues"]}
        if "native_record_uid_conflict" in codes:
            return "ncbi_entrez_selected_record_identity_conflict"
        if "native_uid_membership_conflict" in codes or native.entrez_selected_identity_state(value) == "unavailable":
            return "ncbi_entrez_native_response_identity_missing"
    return None


def _retrieval_failure(value, snapshot):
    """Validate response identity/capture, independently of analysis qualities."""
    response = value["response"]
    status = response["http_status"]
    if status is None:
        return "ncbi_entrez_http_status_unknown"
    if not 200 <= status < 300:
        return "ncbi_entrez_http_not_success"
    headers = snapshot.transport.get("headers")
    header_names = [name for name, _ in response["header_items"]]
    if type(headers) is dict:
        header_names.extend(name for name in headers if type(name) is str)
    if status == 206 or any(name.lower() == "content-range" for name in header_names):
        return "ncbi_entrez_unrequested_range_response"
    if response["capture_failure"] is not None:
        return response["capture_failure"]
    if (response["body_complete"] is not True
            or response["reported_retained_bytes"] != response["retained_bytes"]
            or response["observed_bytes"] != response["retained_bytes"]):
        return "ncbi_entrez_capture_not_complete"
    if value["native_response_state"] == "error":
        return "ncbi_entrez_native_error_response"
    if value["parse_state"] == "unavailable" or value["native_document"] is None:
        return "ncbi_entrez_native_format_unavailable"
    document = value["native_document"]
    if document["kind"] == "json":
        name = "esearchresult" if value["requested"]["operation"] == "search" else "result"
        # Duplicated native containers and other native qualifications remain
        # data; no first/last winner or numerical interpretation is selected.
        if not any(node.get("kind") == "object" for _, node in native._members(document["value"], name)):
            return "ncbi_entrez_native_response_identity_missing"
    elif document["kind"] == "xml":
        expected = {"gene": "Entrezgene-Set", "taxonomy": "TaxaSet", "sra": "EXPERIMENT_PACKAGE_SET"}[
            value["requested"]["database"]]
        if document["value"]["root"]["tag"] != expected:
            return "ncbi_entrez_native_response_identity_conflict"
        if value["requested"]["database"] == "sra":
            state = native.entrez_selected_identity_state(value)
            if state == "mismatch":
                return "ncbi_entrez_selected_record_identity_conflict"
            if state != "matched":
                return "ncbi_entrez_native_response_identity_missing"
    if value["requested"]["database"] == "snp":
        failure = _snp_response_identity_failure(value)
        if failure is not None:
            return failure
    if native.entrez_selected_identity_state(value) == 'mismatch':
        return 'ncbi_entrez_selected_record_identity_conflict'
    return None


def publish_ncbi_entrez_request(registry, arguments, snapshot):
    """Retain the actual response first, then deliver only its acquisition receipt."""
    if not isinstance(snapshot, SourceSnapshot) or type(snapshot.content) is not bytes:
        return {"acquired": False, "source_ref": None, "data_ref": None,
            "failure_code": "ncbi_entrez_snapshot_conflict"}, []
    source = registry._source(TOOL, None, snapshot=snapshot, accession=None)
    try:
        value = native.entrez_result(snapshot, arguments=arguments, source_ref=source["id"],
            artifact_ref=source["artifact_ref"])
        failure = _retrieval_failure(value, snapshot)
    except ValueError as error:
        failure = str(error)
    receipt = {"acquired": failure is None, "source_ref": source["id"],
        "data_ref": source["artifact_ref"] if failure is None else None, "failure_code": failure}
    # The data File is an explicit successful delivery, not a dependency grant
    # obtained by traversing the Source or its private request metadata.
    return receipt, [source["id"], *([source["artifact_ref"]] if failure is None else [])]


__all__ = ["TOOL", "ncbi_entrez_tool_contract", "ncbi_entrez_receipt_schema",
    "request_ncbi_entrez", "publish_ncbi_entrez_request"]
